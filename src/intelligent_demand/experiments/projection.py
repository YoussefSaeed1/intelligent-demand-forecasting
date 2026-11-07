"""Matched-subset evaluation of immutable completed forecasts, without refitting models."""

import json
import time

import pandas as pd

from intelligent_demand.evaluation.predictions import PredictionWriter
from intelligent_demand.evaluation.scoring import score_predictions
from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.registry import atomic_json, file_digest
from intelligent_demand.models.base import ModelInfo


def project_completed(registry, parent_run_id, fold, metadata, source, output):
    parent = registry.completed(parent_run_id)
    parent_spec = parent["specification"]
    series = tuple(sorted(metadata.series_id))
    if (
        not series
        or len(set(series)) != len(series)
        or parent_spec["dataset_id"] != fold.dataset_id
        or parent_spec["fold"]["origin"] != str(fold.origin)
        or file_digest(source.path) != parent_spec["source_fingerprint"]
    ):
        raise ValueError("Projection requires the same source and origin with a unique subset")
    spec = json.loads(json.dumps(parent_spec))
    spec["series_count"], spec["series_sha256"] = len(series), identity(list(series))
    classes = dict(zip(metadata.series_id, metadata.pattern, strict=True))
    spec["classes_sha256"] = identity(classes)
    spec["model_configuration"]["evaluation_projection"] = "frozen_training_stratified_subset"
    spec["model_configuration"]["parent_run_id"] = parent_run_id
    spec["derived_from"] = {
        "run_id": parent_run_id,
        "prediction_sha256": parent["outputs"]["predictions"]["sha256"],
        "models_refitted": False,
    }
    path = output / "projections" / f"{identity(spec)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        run_id = json.loads(path.read_text())["run_id"]
        if registry.read(run_id)["status"] == "completed":
            return registry.completed(run_id)
    else:
        run_id = registry.create(spec)
        atomic_json(path, {"run_id": run_id, "parent_run_id": parent_run_id})
    with registry.attempt(run_id, spec, resume=True) as attempt:
        started = time.perf_counter()
        directory = registry.directory(parent_run_id)
        frame = pd.read_parquet(
            directory / parent["outputs"]["predictions"]["path"],
            filters=[("series_id", "in", list(series))],
        )
        predicted = frame[["series_id", "target_date", "raw_prediction", "is_fallback"]].rename(
            columns={"raw_prediction": "prediction"}
        )
        writer = PredictionWriter(
            attempt / "predictions.parquet", fold, series, ModelInfo(**spec["model"]), run_id
        )
        try:
            writer.write(predicted)
            writer.finish()
        finally:
            writer.close()
        delivery = pd.read_parquet(
            directory / parent["outputs"]["model_0_delivery"]["path"],
            filters=[("series_id", "in", list(series))],
        )
        if set(delivery.series_id) != set(series) or delivery.series_id.duplicated().any():
            raise ValueError("Projection population is outside the parent result")
        delivery.to_parquet(attempt / "delivery.parquet", index=False)
        # Actuals remain unavailable until the derived prediction file is sealed.
        actual = pd.concat(source.validation_targets(fold, series), ignore_index=True).rename(
            columns={"date": "target_date", "sales_units": "actual"}
        )
        scales = source.scales(fold, series)
        scored = score_predictions(
            actual,
            pd.read_parquet(attempt / "predictions.parquet"),
            scales,
            fold,
            series,
            classes,
            pd.Timestamp(spec["class_as_of"]).date(),
        )
        scored["elapsed_seconds"] = time.perf_counter() - started
        atomic_json(attempt / "metrics.json", scored)
        atomic_json(
            attempt / "model_metadata.json",
            [
                {
                    "derived_from": spec["derived_from"],
                    "model": spec["model"],
                    "models_refitted": False,
                }
            ],
        )
        atomic_json(
            attempt / "lineage.json",
            {**spec["derived_from"], "subset_sha256": spec["series_sha256"]},
        )
        registry.completed(parent_run_id)
        registry.complete(
            run_id,
            attempt,
            {
                "predictions": attempt / "predictions.parquet",
                "metrics": attempt / "metrics.json",
                "model_metadata": attempt / "model_metadata.json",
                "model_0_delivery": attempt / "delivery.parquet",
                "projection_lineage": attempt / "lineage.json",
            },
        )
    return registry.completed(run_id)
