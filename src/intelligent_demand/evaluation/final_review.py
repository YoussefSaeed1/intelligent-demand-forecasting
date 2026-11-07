"""Read-only pre-checkpoint review directly from persisted predictions and safe sources."""

import gc
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import pyarrow.parquet as pq

from intelligent_demand.evaluation.ml_audit import audit_ml_training
from intelligent_demand.evaluation.predictions import PREDICTION_SCHEMA
from intelligent_demand.evaluation.splits import load_splits
from intelligent_demand.experiments.benchmark import OUTPUT, ROOT, population, verify_sources
from intelligent_demand.experiments.config import identity, load_experiment_config
from intelligent_demand.experiments.data import ParquetSource
from intelligent_demand.experiments.gates import require_gate
from intelligent_demand.experiments.preparation import PreparedSource
from intelligent_demand.experiments.registry import ExperimentRegistry, atomic_json


def review_metrics(actual, prediction):
    """Rows are series, columns are the complete horizon; no production metric helper."""
    difference = np.asarray(prediction, dtype="float64") - np.asarray(actual, dtype="float64")
    absolute = np.abs(difference)
    count = difference.size
    actual_total = float(np.sum(actual, dtype="float64"))
    return {
        "macro_mae": float(np.mean(np.mean(absolute, axis=1))),
        "pooled_rmse": float(np.sqrt(np.sum(difference * difference) / count)),
        "pooled_wape_percent": 100 * float(np.sum(absolute)) / actual_total
        if actual_total
        else None,
        "observations": count,
        "actual_total": actual_total,
        "absolute_error_total": float(np.sum(absolute)),
        "squared_error_total": float(np.sum(difference * difference)),
    }


def source_actuals(source, fold, series):
    chunks = list(source.validation_targets(fold, series))
    frame = pd.concat(chunks, ignore_index=True).rename(columns={"date": "target_date"})
    frame["target_date"] = pd.to_datetime(frame.target_date)
    if (
        len(frame) != len(series) * 28
        or frame.duplicated(["series_id", "target_date"]).any()
        or not frame.target_date.between(str(fold.validation_start), str(fold.validation_end)).all()
        or not frame.series_id.isin(series).all()
    ):
        raise ValueError("Canonical validation grid is incomplete or malformed")
    return frame[["series_id", "target_date", "sales_units"]]


def prediction_grid(frame, actual, fold, series, state):
    frame["target_date"] = pd.to_datetime(frame.target_date)
    spec = state["specification"]
    if (
        len(frame) != len(series) * 28
        or frame.duplicated(["series_id", "target_date"]).any()
        or not frame.series_id.isin(series).all()
        or not frame.target_date.between(str(fold.validation_start), str(fold.validation_end)).all()
        or not frame.dataset_id.eq(fold.dataset_id).all()
        or not frame.model_id.eq(spec["model"]["identifier"]).all()
        or not frame.run_id.eq(state["run_id"]).all()
        or not pd.to_datetime(frame.forecast_origin).eq(pd.Timestamp(fold.origin)).all()
        or not frame.horizon_step.eq((frame.target_date - pd.Timestamp(fold.origin)).dt.days).all()
        or not np.isfinite(frame[["prediction", "raw_prediction"]]).all().all()
        or not np.array_equal(frame.prediction, np.maximum(frame.raw_prediction, 0))
        or not frame.was_clipped.eq(frame.raw_prediction.lt(0)).all()
    ):
        raise ValueError("Persisted predictions violate their complete origin-relative grid")
    joined = actual.merge(frame, on=["series_id", "target_date"], validate="one_to_one")
    joined = joined.sort_values(["series_id", "target_date"])
    if len(joined) != len(series) * 28 or tuple(joined.series_id.unique()) != tuple(series):
        raise ValueError("Canonical actual/prediction alignment failed")
    return joined


def sampling_review(panel, state, directory):
    # Reconcile every feature/label independently; this does not fit a model.
    feature_audit = audit_ml_training(state, directory, panel)
    spec = state["specification"]
    model_meta = json.loads((directory / state["outputs"]["model_metadata"]["path"]).read_text())[0]
    contract = model_meta["feature_cache_contract"]
    cache = Path(spec["model_configuration"]["feature_cache"]) / identity(contract)
    manifest = json.loads((cache / "complete.json").read_text())
    pairs = np.load(cache / manifest["names"]["positions"], mmap_mode="r")
    labels = np.load(cache / manifest["names"]["labels"], mmap_mode="r")
    count = len(labels) // len(panel.metadata)
    boundaries = np.linspace(56, len(panel.dates), count + 1, dtype=int)
    rng = np.random.default_rng(spec["random_seed"])
    expected_targets = rng.integers(
        boundaries[:-1], boundaries[1:], size=(len(panel.metadata), count)
    ).ravel()
    if not np.array_equal(
        pairs[:, 0], np.repeat(np.arange(len(panel.metadata)), count)
    ) or not np.array_equal(pairs[:, 1], expected_targets):
        raise ValueError("Persisted sample does not reproduce its declared seed/time strata")
    metadata = panel.metadata
    dates = panel.dates.take(pairs[:, 1])
    class_counts = metadata.pattern.value_counts().to_dict()
    zero_history_rows = 0
    for start in range(0, len(pairs), 8192):
        rows, targets = pairs[start : start + 8192].T
        history = panel.values[rows[:, None], targets[:, None] - np.arange(56, 0, -1)]
        zero_history_rows += int(np.all(history == 0, axis=1).sum())
    historical_zero_series = sum(
        int(np.all(panel.values[start : start + 128] == 0, axis=1).sum())
        for start in range(0, len(metadata), 128)
    )
    return {
        **feature_audit,
        "seed_reproduced_exactly": True,
        "per_series": count,
        "target_min": str(dates.min().date()),
        "target_max": str(dates.max().date()),
        "forecast_origin": spec["fold"]["origin"],
        "eligible_label_dates": len(panel.dates) - 56,
        "distinct_label_dates_sampled": int(dates.nunique()),
        "fraction_of_eligible_labels_percent": 100 * count / (len(panel.dates) - 56),
        "monthly_label_counts": dict(Counter(dates.strftime("%Y-%m"))),
        "stores": int(metadata.store_id.nunique()),
        "products": int(metadata.item_id.nunique()),
        "class_series": {str(k): int(v) for k, v in class_counts.items()},
        "class_training_rows": {str(k): int(v) * count for k, v in class_counts.items()},
        "zero_labels": int(np.count_nonzero(labels == 0)),
        "zero_label_percent": 100 * float(np.mean(labels == 0)),
        "all_zero_56_day_histories": zero_history_rows,
        "all_zero_entire_training_series": historical_zero_series,
        "rows_from_all_zero_entire_series": historical_zero_series * count,
        "negative_labels": int(np.count_nonzero(labels < 0)),
    }


def review_price_availability():
    """Prove completed source weeks, without claiming unavailable publication evidence."""
    calendar = pd.read_csv(ROOT / "data/raw/m5/calendar.csv", usecols=["date", "wm_yr_wk"])
    calendar["date"] = pd.to_datetime(calendar.date)
    ends = calendar.groupby("wm_yr_wk").date.max()
    end_for_date = calendar.set_index("date").wm_yr_wk.map(ends)
    results = []
    for fold in load_splits(ROOT / "reports/eda/proposed_splits.json")["m5"]:
        dates = pd.date_range(pd.Timestamp(fold.train_start) + pd.Timedelta(days=56), fold.origin)
        week_ends = pd.DatetimeIndex(end_for_date.reindex(dates - pd.Timedelta(days=7)))
        latest = pd.Timestamp(fold.origin) - pd.Timedelta(days=6)
        if not week_ends.notna().all() or not (week_ends < dates).all():
            raise ValueError("Historical price includes an incomplete source week")
        if end_for_date.loc[latest] > pd.Timestamp(fold.origin):
            raise ValueError("Inference price snapshot includes an incomplete source week")
        results.append(
            {
                "fold": fold.number,
                "eligible_dates_checked": len(dates),
                "all_price_source_weeks_end_before_target": True,
                "origin": str(fold.origin),
                "latest_inference_price_record": str(latest.date()),
                "source_week_end": str(end_for_date.loc[latest].date()),
                "actual_publication_timestamp_verified": False,
            }
        )
    result = {
        "status": "conditional_benchmark_assumption",
        "checks": results,
        "limitation": (
            "Completed source weeks are verified; actual publication latency and "
            "live operational availability remain unverified."
        ),
    }
    atomic_json(ROOT / "reports/forecasting/phase3_price_availability_review.json", result)
    return result


def run_review():
    started = time.perf_counter()
    before = verify_sources()
    config = load_experiment_config(ROOT / "configs/forecasting.yaml")
    folds = load_splits(config.split_manifest)
    registry = ExperimentRegistry(config.registry_directory)
    gate = require_gate("3e")
    states = [registry.completed(row["run_id"]) for row in gate["runs"]]
    grouped = {}
    for state in states:
        s = state["specification"]
        grouped.setdefault((s["dataset_id"], s["fold"]["number"], s["series_sha256"]), []).append(
            state
        )
    records, samples, paired = [], [], []
    for (dataset, number, pop_hash), cohort in grouped.items():
        registry.comparison_candidates([state["run_id"] for state in cohort])
        metadata = population(dataset)
        scope = "full"
        if pop_hash != identity(list(metadata.series_id)):
            selection = json.loads((OUTPUT / f"{dataset}_statistical_subset.json").read_text())
            metadata = metadata.set_index("series_id").loc[selection["series_ids"]].reset_index()
            scope = "statistical_subset"
        series = tuple(metadata.series_id)
        if identity(list(series)) != pop_hash or len(cohort) != (13 if scope == "full" else 15):
            raise ValueError("Incomplete or incompatible model/population comparison")
        fold = folds[dataset][number - 1]
        source = ParquetSource(ROOT / f"data/processed/{dataset}/daily_sales.parquet", dataset)
        actuals = source_actuals(source, fold, series)
        comparison = {}
        prepared = None
        for state in cohort:
            spec, directory = state["specification"], registry.directory(state["run_id"])
            method = spec["model"]["identifier"]
            prediction_path = directory / state["outputs"]["predictions"]["path"]
            if not pq.read_schema(prediction_path).equals(PREDICTION_SCHEMA):
                raise ValueError("Persisted prediction schema differs from the canonical schema")
            frame = pd.read_parquet(prediction_path)
            joined = prediction_grid(frame, actuals, fold, series, state)
            actual = joined.sales_units.to_numpy().reshape(len(series), 28)
            prediction = joined.prediction.to_numpy().reshape(len(series), 28)
            metrics = review_metrics(actual, prediction)
            saved = json.loads((directory / state["outputs"]["metrics"]["path"]).read_text())
            for value, expected in (
                (metrics["macro_mae"], saved["all"]["macro"]["mae"]),
                (metrics["pooled_rmse"], saved["all"]["pooled"]["rmse"]),
                (metrics["pooled_wape_percent"], saved["all"]["pooled"]["wape_percent"]),
            ):
                if not np.isclose(value, expected, rtol=1e-10, atol=1e-10):
                    raise ValueError("Direct-prediction recalculation disagrees with saved scores")
            delivery = pd.read_parquet(directory / state["outputs"]["model_0_delivery"]["path"])
            delivery = delivery.sort_values("series_id")
            fallback = joined.is_fallback.to_numpy().reshape(len(series), 28)
            if (
                tuple(delivery.series_id) != series
                or not delivery.requested_method.eq(method).all()
                or not np.array_equal(
                    fallback, np.repeat(delivery.is_fallback.to_numpy()[:, None], 28, axis=1)
                )
                or not delivery.loc[~delivery.is_fallback, "actual_method"].eq(method).all()
                or delivery.loc[delivery.is_fallback, "reason"].eq("native").any()
            ):
                raise ValueError("Requested/native/fallback classifications differ")
            if spec.get("derived_from"):
                parent = registry.completed(spec["derived_from"]["run_id"])
                parent_path = (
                    registry.directory(parent["run_id"]) / parent["outputs"]["predictions"]["path"]
                )
                parent_frame = pd.read_parquet(
                    parent_path, filters=[("series_id", "in", list(series))]
                )
                parent_frame["target_date"] = pd.to_datetime(parent_frame.target_date)
                columns = [
                    "series_id",
                    "target_date",
                    "prediction",
                    "raw_prediction",
                    "is_fallback",
                    "was_clipped",
                ]
                pd.testing.assert_frame_equal(
                    frame[columns].sort_values(columns[:2]).reset_index(drop=True),
                    parent_frame[columns].sort_values(columns[:2]).reset_index(drop=True),
                    check_exact=True,
                )
            if method in ("random_forest", "lightgbm") and scope == "full":
                if prepared is None:
                    prepared = PreparedSource(
                        source.path, dataset, metadata, OUTPUT / "cache", spec["source_fingerprint"]
                    )
                sample = sampling_review(prepared.panel(fold, series), state, directory)
                samples.append({"dataset": dataset, "fold": number, "model": method, **sample})
            per_series_mae = np.abs(prediction - actual).mean(axis=1)
            comparison[method] = per_series_mae
            records.append(
                {
                    "dataset": dataset,
                    "scope": scope,
                    "fold": number,
                    "origin": str(fold.origin),
                    "model": method,
                    "run_id": state["run_id"],
                    "series": len(series),
                    **metrics,
                    "fallback_series": int(delivery.is_fallback.sum()),
                    "actual_methods": {
                        str(k): int(v) for k, v in delivery.actual_method.value_counts().items()
                    },
                    "fallback_reasons": {
                        str(k): int(v)
                        for k, v in delivery.loc[delivery.is_fallback, "reason"]
                        .value_counts()
                        .items()
                    },
                    "clipped_predictions": int(joined.was_clipped.sum()),
                    "duplicate_prediction_keys": 0,
                }
            )
            del frame, joined, actual, prediction
        if dataset == "m5" and scope == "full":
            differences = comparison["random_forest"] - comparison["moving_average_28"]
            paired.append(
                {
                    "fold": number,
                    "origin": str(fold.origin),
                    "rf_macro_mae": float(comparison["random_forest"].mean()),
                    "ma28_macro_mae": float(comparison["moving_average_28"].mean()),
                    "rf_minus_ma28": float(differences.mean()),
                    "rf_better_series": int(np.count_nonzero(differences < 0)),
                    "ma28_better_series": int(np.count_nonzero(differences > 0)),
                    "ties": int(np.count_nonzero(differences == 0)),
                    "median_series_mae_difference": float(np.median(differences)),
                }
            )
        print(f"REVIEWED {dataset} fold {number} {scope}: {len(cohort)} models", flush=True)
        del prepared, actuals, comparison
        gc.collect()
        if psutil.Process().memory_info().rss > 2048 * 2**20:
            raise MemoryError("Review exceeded its 2 GiB memory budget")
    summaries = []
    for (dataset, scope, method), group in pd.DataFrame(records).groupby(
        ["dataset", "scope", "model"]
    ):
        if len(group) != 4 or set(group.fold) != {1, 2, 3, 4}:
            raise ValueError("Comparison needs four origins")
        n = group.observations.sum()
        summaries.append(
            {
                "dataset": dataset,
                "scope": scope,
                "model": method,
                "four_origin_macro_mae": float(group.macro_mae.mean()),
                "pooled_rmse": float(np.sqrt(group.squared_error_total.sum() / n)),
                "pooled_wape_percent": 100
                * float(group.absolute_error_total.sum() / group.actual_total.sum()),
                "forecast_records": int(n),
            }
        )
    if verify_sources() != before:
        raise ValueError("Raw/canonical hashes changed during review")
    output = {
        "status": "passed",
        "method": (
            "direct persisted prediction to canonical validation join; "
            "independent arithmetic; no refitting"
        ),
        "evaluations": len(records),
        "forecast_records": sum(r["observations"] for r in records),
        "fold_metrics": records,
        "model_comparisons": summaries,
        "m5_rf_vs_ma28_by_origin": paired,
        "ml_training_samples": samples,
        "source_sha256": before,
        "holdout_targets_used": False,
        "price_availability": review_price_availability(),
        "seconds": time.perf_counter() - started,
        "peak_os_working_set_bytes": getattr(psutil.Process().memory_info(), "peak_wset", None),
    }
    atomic_json(ROOT / "reports/forecasting/phase3_integrity_review.json", output)
    print(
        json.dumps(
            {
                "status": "passed",
                "evaluations": len(records),
                "forecast_records": output["forecast_records"],
                "m5_rf_vs_ma28_by_origin": paired,
                "seconds": output["seconds"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    run_review()
