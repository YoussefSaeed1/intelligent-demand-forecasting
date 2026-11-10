"""Read-only validation adapters; no canonical final-target reader or model fitting."""

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

from intelligent_demand.inventory.plan import ROOT, read
from intelligent_demand.preservation.backup import sha256
from intelligent_demand.preservation.paths import EvidenceResolver
from intelligent_demand.preservation.verify import identity


def checked(item):
    return EvidenceResolver(ROOT).resolve(item["path"], item["sha256"])


def align(frame, metadata, start, field):
    rows = pd.Index(metadata.series_id).get_indexer(frame.series_id)
    dates = pd.to_datetime(frame.target_date)
    days = (dates - pd.Timestamp(start)).dt.days.to_numpy()
    if (
        len(frame) != len(metadata) * 28
        or (rows < 0).any()
        or ((days < 0) | (days >= 28)).any()
        or dates.dt.tz is not None
        or not dates.eq(dates.dt.normalize()).all()
        or len(np.unique(rows * 28 + days)) != len(frame)
    ):
        raise ValueError("Input must cover unique complete matched series/date keys")
    result = np.empty((len(metadata), 28))
    result[rows, days] = frame[field].to_numpy()
    if not np.isfinite(result).all() or (result < 0).any():
        raise ValueError("Invalid demand or forecast values")
    return result, rows, days


def sample_zero_mask(directory, metadata_record, spec, count):
    metadata = read(Path(directory) / metadata_record["path"])[0]
    cache = EvidenceResolver(ROOT, ROOT).resolve(spec["model_configuration"]["feature_cache"])
    cache = cache / identity(metadata["feature_cache_contract"])
    complete = read(cache / "complete.json")
    path = cache / complete["names"]["labels"]
    if sha256(path) != complete["files"][path.name]:
        raise ValueError("Original sample label hash changed")
    labels = np.load(path, mmap_mode="r")
    positions = np.load(cache / complete["names"]["positions"], mmap_mode="r")
    per = len(labels) // count
    if len(labels) != per * count or not np.array_equal(
        positions[:, 0], np.repeat(np.arange(count), per)
    ):
        raise ValueError("Sample population order differs")
    return (labels.reshape(count, per) == 0).all(axis=1)


def load_cohort(cohort):
    dataset, fold = cohort["dataset"], cohort["fold"]
    expected = read(ROOT / "reports/eda/proposed_splits.json")[dataset]
    definition = expected["validation_folds"][fold["number"] - 1]
    if (
        not 1 <= fold["number"] <= 4
        or any(
            fold[k] != definition[k]
            for k in ("train_start", "origin", "validation_start", "validation_end")
        )
        or fold["validation_end"] >= expected["test_start"]
    ):
        raise ValueError("Only the four original validation windows are permitted")
    metadata = pd.read_parquet(checked(cohort["metadata"]))
    metadata = metadata.sort_values("series_id").reset_index(drop=True)
    cached = read(checked(cohort["training_cache"]))
    if cached["contract"]["origin"] != fold["origin"]:
        raise ValueError("Calibration history crosses origin")
    cache = (ROOT / cohort["training_cache"]["path"]).parent
    values_path = cache / cached["values"]
    if sha256(values_path) != cached["files"][cached["values"]]:
        raise ValueError("Origin-bound calibration cache changed")
    values = np.load(values_path, mmap_mode="r")
    if values.shape != (
        len(metadata),
        (pd.Timestamp(fold["origin"]) - pd.Timestamp(fold["train_start"])).days + 1,
    ):
        raise ValueError("Training cache date/series coverage differs")
    mean = values[:, -56:].astype(float).mean(axis=1)
    del values
    expression = (ds.field("date") >= pa.scalar(pd.Timestamp(fold["validation_start"]).date())) & (
        ds.field("date") <= pa.scalar(pd.Timestamp(fold["validation_end"]).date())
    )
    frame = (
        ds.dataset(ROOT / f"data/processed/{dataset}/daily_sales.parquet")
        .to_table(
            columns=["dataset_id", "series_id", "date", "sales_units"],
            filter=expression,
            use_threads=False,
        )
        .to_pandas()
        .rename(columns={"date": "target_date"})
    )
    if not frame.dataset_id.eq(dataset).all():
        raise ValueError("Demand namespace differs")
    actual, _, _ = align(frame, metadata, fold["validation_start"], "sales_units")
    forecasts, coverage = {}, {}
    sparse = np.zeros(len(metadata), dtype=bool)
    for label, record in cohort["sources"].items():
        frame = pd.read_parquet(checked(record["predictions"]))
        if (
            not frame.run_id.eq(record["run_id"]).all()
            or not frame.model_id.eq(record["model"]).all()
            or not frame.dataset_id.eq(dataset).all()
            or not pd.to_datetime(frame.forecast_origin).eq(pd.Timestamp(fold["origin"])).all()
        ):
            raise ValueError("Forecast provenance/origin mismatch")
        forecasts[label], _, days = align(frame, metadata, fold["validation_start"], "prediction")
        if not frame.horizon_step.eq(days + 1).all() or frame.is_fallback.dtype != bool:
            raise ValueError("Forecast horizon/fallback schema mismatch")
        coverage[label] = int(frame.is_fallback.sum())
        if dataset == "m5" and label == "selected_ml":
            directory = (ROOT / record["specification"]["path"]).parent
            state = read(directory / "status.json")
            sparse = sample_zero_mask(
                directory,
                state["outputs"]["model_metadata"],
                read(checked(record["specification"])),
                len(metadata),
            )
    retrospective = np.zeros(len(metadata), dtype=bool)
    if dataset == "m5":
        base = ROOT / "artifacts/experiments/phase4"
        record = next(
            r
            for r in read(base / "sealed_predictions.json")["forecasts"]
            if r["dataset"] == dataset and r["role"] == "selected"
        )
        retrospective = sample_zero_mask(
            base, record["files"]["model_metadata"], record["specification"], len(metadata)
        )
    metadata["origin_sample_all_zero"] = sparse
    metadata["retrospective_final_training_all_zero"] = retrospective
    return metadata, actual, mean, forecasts, coverage
