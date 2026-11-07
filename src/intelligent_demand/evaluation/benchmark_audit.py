"""Independent NumPy reconciliation of persisted validation predictions and rankings."""

import argparse
import gc
import json
import time

import numpy as np
import pandas as pd
import psutil
import pyarrow.parquet as pq

from intelligent_demand.evaluation.predictions import PREDICTION_SCHEMA
from intelligent_demand.evaluation.splits import load_splits
from intelligent_demand.experiments.benchmark import OUTPUT, ROOT, population, verify_sources
from intelligent_demand.experiments.config import identity, load_experiment_config
from intelligent_demand.experiments.data import ParquetSource
from intelligent_demand.experiments.preparation import PreparedSource
from intelligent_demand.experiments.registry import ExperimentRegistry, atomic_json, file_digest

METRICS = ("mae", "rmse", "wape_percent", "bias_units", "bias_percent", "mase", "rmsse")


def defined_mean(values):
    values = np.asarray(values, dtype=float)
    finite = np.isfinite(values)
    return float(values[finite].mean()) if finite.any() else None


def independent_summary(actual, predicted, scales, fallback, clipped):
    """Separate arithmetic from the production Pandas scorer; rows=series, columns=days."""
    error = predicted - actual
    absolute = np.abs(error)
    actual_sum = actual.sum(axis=1)
    mae = absolute.mean(axis=1)
    rmse = np.sqrt(np.square(error).mean(axis=1))
    bias = error.mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        per_series = {
            "mae": mae,
            "rmse": rmse,
            "bias_units": bias,
            "wape_percent": np.where(
                actual_sum > 0, 100 * absolute.sum(axis=1) / actual_sum, np.nan
            ),
            "bias_percent": np.where(actual_sum > 0, 100 * error.sum(axis=1) / actual_sum, np.nan),
            "mase": mae / scales[:, 0],
            "rmsse": rmse / np.sqrt(scales[:, 1]),
        }
    total = float(actual.sum())
    pooled = {
        "mae": float(absolute.mean()),
        "rmse": float(np.sqrt(np.square(error).mean())),
        "bias_units": float(error.mean()),
        "wape_percent": 100 * float(absolute.sum()) / total if total else None,
        "bias_percent": 100 * float(error.sum()) / total if total else None,
    }
    counts = {name: int(np.isfinite(values).sum()) for name, values in per_series.items()}
    return {
        "macro": {name: defined_mean(values) for name, values in per_series.items()},
        "pooled": pooled,
        "coverage": {
            "observations": int(actual.size),
            "series": len(actual),
            "defined_series": counts,
            "undefined_series": {name: len(actual) - count for name, count in counts.items()},
            "fallback_observations": int(fallback.sum()),
            "clipped_observations": int(clipped.sum()),
        },
        "totals": {
            "actual": total,
            "absolute_error": float(absolute.sum()),
            "squared_error": float(np.square(error).sum()),
            "error": float(error.sum()),
        },
        "per_series": per_series,
    }


def assert_same(expected, actual, context="metrics"):
    if isinstance(expected, dict):
        for key, value in expected.items():
            assert_same(value, actual[key], f"{context}.{key}")
    elif expected is None:
        if actual is not None:
            raise ValueError(f"Undefined value lost at {context}")
    elif not np.isclose(expected, actual, rtol=1e-9, atol=1e-10):
        raise ValueError(f"Independent reconciliation failed at {context}")


def reconcile_series_metrics(independent, saved, series):
    table = pd.DataFrame(saved)
    if len(table) != len(series) or tuple(table.series_id) != tuple(series):
        raise ValueError("Per-series metric coverage/order differs")
    for metric in METRICS:
        values = pd.to_numeric(table[metric], errors="raise").to_numpy(dtype="float64")
        if not np.allclose(independent[metric], values, rtol=1e-9, atol=1e-10, equal_nan=True):
            raise ValueError(f"Independent per-series metric reconciliation failed: {metric}")


def validation_array(source, fold, series):
    result = np.full((len(series), 28), np.nan, dtype=float)
    index, rows = pd.Index(series), 0
    for batch in source.validation_targets(fold, series):
        codes = index.get_indexer(batch.series_id)
        steps = (
            pd.to_datetime(batch.date) - pd.Timestamp(fold.validation_start)
        ).dt.days.to_numpy()
        flat = codes * 28 + steps
        if (codes < 0).any() or (steps < 0).any() or (steps >= 28).any():
            raise ValueError("Actual keys outside validation grid")
        if len(np.unique(flat)) != len(flat) or not np.isnan(result[codes, steps]).all():
            raise ValueError("Duplicated actual keys")
        result[codes, steps] = batch.sales_units.to_numpy()
        rows += len(batch)
    if rows != result.size or not np.isfinite(result).all() or (result < 0).any():
        raise ValueError("Incomplete or invalid validation actuals")
    return result


def prediction_arrays(path, state, fold, series):
    if not pq.read_schema(path).equals(PREDICTION_SCHEMA):
        raise ValueError("Persisted prediction schema differs from the canonical contract")
    frame = pd.read_parquet(path)
    spec = state["specification"]
    if len(frame) != len(series) * 28:
        raise ValueError("Prediction count differs from full declared grid")
    for column, expected in (
        ("dataset_id", fold.dataset_id),
        ("model_id", spec["model"]["identifier"]),
        ("model_version", spec["model"]["version"]),
        ("run_id", state["run_id"]),
    ):
        if not frame[column].eq(expected).all():
            raise ValueError("Prediction metadata differs from its registered run")
    if not pd.to_datetime(frame.forecast_origin).eq(pd.Timestamp(fold.origin)).all():
        raise ValueError("Forecast origin mismatch")
    codes = pd.Index(series).get_indexer(frame.series_id)
    targets = pd.to_datetime(frame.target_date)
    steps = (targets - pd.Timestamp(fold.validation_start)).dt.days.to_numpy()
    if not targets.eq(targets.dt.normalize()).all() or targets.dt.tz is not None:
        raise ValueError("Invalid target date representation")
    if (codes < 0).any() or (steps < 0).any() or (steps >= 28).any():
        raise ValueError("Out-of-window predictions")
    if (
        len(np.unique(codes * 28 + steps)) != len(frame)
        or not frame.horizon_step.eq(steps + 1).all()
    ):
        raise ValueError("Duplicate or misaligned prediction keys")
    predicted, fallback, clipped = (
        np.empty((len(series), 28), dtype=dtype) for dtype in (float, bool, bool)
    )
    if not np.isfinite(frame[["prediction", "raw_prediction"]]).all().all():
        raise ValueError("Nonfinite forecasts")
    if not np.array_equal(frame.prediction, frame.raw_prediction.clip(lower=0)):
        raise ValueError("Clipping policy mismatch")
    for column in ("is_fallback", "was_clipped"):
        if frame[column].dtype != bool or frame[column].isna().any():
            raise ValueError("Invalid coverage flags")
    if not frame.was_clipped.eq(frame.raw_prediction.lt(0)).all():
        raise ValueError("Clipping flag mismatch")
    predicted[codes, steps] = frame.prediction
    fallback[codes, steps] = frame.is_fallback
    clipped[codes, steps] = frame.was_clipped
    return predicted, fallback, clipped


def audit_phase(phase, methods=None):
    started = time.perf_counter()
    config = load_experiment_config(ROOT / "configs/forecasting.yaml")
    registry = ExperimentRegistry(config.registry_directory)
    before = verify_sources()
    if phase == "3e":
        from intelligent_demand.experiments.gates import require_gate

        records = [row for p in ("3b", "3c", "3d") for row in require_gate(p)["runs"]]
    else:
        records = json.loads((OUTPUT / f"{phase}_execution.json").read_text())["runs"]
    states = [registry.completed(run_id) for run_id in dict.fromkeys(r["run_id"] for r in records)]
    if phase in ("3c", "3e"):
        from intelligent_demand.experiments.gates import require_gate
        from intelligent_demand.experiments.projection import project_completed
        from intelligent_demand.experiments.sampling import frozen_statistical_subset

        parents = (
            require_gate("3b")["runs"]
            if phase == "3c"
            else [
                row
                for p in ("3c", "3d")
                for row in require_gate(p)["runs"]
                if row.get("scope", "full") == "full"
            ]
        )
        for dataset in ("store_item", "m5"):
            folds = load_splits(config.split_manifest)[dataset]
            selected = frozen_statistical_subset(
                ROOT, OUTPUT, population(dataset), dataset, folds[0].origin
            )
            for fold in folds:
                print(
                    f"PROJECTING {dataset} fold {fold.number}: matched frozen population",
                    flush=True,
                )
                source = PreparedSource(
                    ROOT / f"data/processed/{dataset}/daily_sales.parquet",
                    dataset,
                    selected,
                    OUTPUT / "cache",
                    before[f"data/processed/{dataset}/daily_sales.parquet"],
                )
                for parent in parents:
                    if parent["dataset"] == dataset and parent["fold"] == fold.number:
                        projected = project_completed(
                            registry, parent["run_id"], fold, selected, source, OUTPUT
                        )
                        states.append(projected)
                print(f"PROJECTED {dataset} fold {fold.number}", flush=True)
                del source
                gc.collect()
    grouped = {}
    for state in states:
        spec = state["specification"]
        grouped.setdefault(
            (spec["dataset_id"], spec["fold"]["number"], spec["series_sha256"]), []
        ).append(state)
    if {(dataset, number) for dataset, number, _ in grouped} != {
        (dataset, fold) for dataset in ("store_item", "m5") for fold in range(1, 5)
    }:
        raise ValueError("Milestone requires all eight dataset/origin windows")
    audits, hierarchy = [], []
    hierarchy_parts = OUTPUT / f"{phase}_hierarchy_parts"
    hierarchy_parts.mkdir(exist_ok=True)
    current_parts = []
    for (dataset, number, population_sha), cohort in grouped.items():
        registry.comparison_candidates([state["run_id"] for state in cohort])
        meta = population(dataset)
        fold = load_splits(config.split_manifest)[dataset][number - 1]
        scope = "full"
        if population_sha != identity(sorted(meta.series_id)):
            if phase not in ("3c", "3e"):
                raise ValueError("Unexpected non-full population")
            from intelligent_demand.experiments.sampling import frozen_statistical_subset

            meta = frozen_statistical_subset(
                ROOT, OUTPUT, meta, dataset, load_splits(config.split_manifest)[dataset][0].origin
            )
            scope = "statistical_subset"
        series = tuple(meta.series_id)
        expected = methods
        if phase == "3d":
            from intelligent_demand.models.global_ml import ML_METHODS

            expected = ML_METHODS
        if phase == "3c":
            from intelligent_demand.models.baselines import BASELINES
            from intelligent_demand.models.statistical import EXPENSIVE, LIGHTWEIGHT

            expected = LIGHTWEIGHT if scope == "full" else (*EXPENSIVE, *BASELINES)
        if phase == "3e":
            from intelligent_demand.models.baselines import BASELINES
            from intelligent_demand.models.global_ml import ML_METHODS
            from intelligent_demand.models.statistical import EXPENSIVE, LIGHTWEIGHT

            expected = (*BASELINES, *LIGHTWEIGHT, *ML_METHODS)
            if scope == "statistical_subset":
                expected = (*expected, *EXPENSIVE)
        if len(cohort) != len({s["specification"]["model"]["identifier"] for s in cohort}):
            raise ValueError("Duplicate requested model in comparison cohort")
        if expected is not None and {
            state["specification"]["model"]["identifier"] for state in cohort
        } != set(expected):
            raise ValueError("Required model family is incomplete on its declared population")
        fingerprint = before[f"data/processed/{dataset}/daily_sales.parquet"]
        prepared = PreparedSource(
            ROOT / f"data/processed/{dataset}/daily_sales.parquet",
            dataset,
            meta,
            OUTPUT / "cache",
            fingerprint,
        )
        panel = prepared.panel(fold, series)
        # Independently derive denominators rather than trusting persisted scales or score JSON.
        scales = np.empty((len(series), 2), dtype=float)
        for start in range(0, len(series), 128):
            block = panel.values[start : start + 128].astype(float)
            lagged_difference = np.diff(np.stack([block[:, :-7], block[:, 7:]], axis=0), axis=0)[0]
            scales[start : start + len(block), 0] = np.abs(lagged_difference).sum(axis=1) / (
                len(panel.dates) - 7
            )
            scales[start : start + len(block), 1] = np.square(lagged_difference).sum(axis=1) / (
                len(panel.dates) - 7
            )
        scales[scales == 0] = np.nan
        actual = validation_array(ParquetSource(prepared.path, dataset), fold, series)
        for state in cohort:
            model = state["specification"]["model"]["identifier"]
            if state["specification"]["series_sha256"] != identity(sorted(series)):
                raise ValueError("Declared evaluation population differs")
            directory = registry.directory(state["run_id"])
            training_audit = None
            if phase == "3d" or (
                phase == "3e" and model in ("random_forest", "lightgbm") and scope == "full"
            ):
                from intelligent_demand.evaluation.ml_audit import audit_ml_training

                training_audit = audit_ml_training(state, directory, panel)
            predicted, fallback, clipped = prediction_arrays(
                directory / state["outputs"]["predictions"]["path"], state, fold, series
            )
            delivery_key = "model_0_delivery"
            if delivery_key not in state["outputs"]:
                raise ValueError("Missing requested/actual-method delivery evidence")
            delivery = pd.read_parquet(directory / state["outputs"][delivery_key]["path"])
            delivery = delivery.sort_values("series_id").reset_index(drop=True)
            if (
                tuple(delivery.series_id) != series
                or not delivery.requested_method.eq(model).all()
                or delivery.actual_method.isna().any()
                or delivery.reason.isna().any()
                or not np.array_equal(
                    fallback, np.repeat(delivery.is_fallback.to_numpy()[:, None], 28, axis=1)
                )
            ):
                raise ValueError("Delivery method/coverage evidence differs from predictions")
            saved = json.loads((directory / state["outputs"]["metrics"]["path"]).read_text())
            summary = independent_summary(actual, predicted, scales, fallback, clipped)
            native = ~fallback.any(axis=1)
            native_summary = None
            if native.any():
                native_summary = independent_summary(
                    actual[native],
                    predicted[native],
                    scales[native],
                    fallback[native],
                    clipped[native],
                )
                native_summary.pop("per_series")
            elif phase in ("3c", "3d", "3e"):
                raise ValueError("An experiment has no native forecasts; do not rank it as fitted")
            for section in ("macro", "pooled", "coverage"):
                assert_same(summary[section], saved["all"][section])
            reconcile_series_metrics(summary["per_series"], saved["all"]["per_series"], series)
            for step in range(28):
                one = independent_summary(
                    actual[:, step : step + 1],
                    predicted[:, step : step + 1],
                    scales,
                    fallback[:, step : step + 1],
                    clipped[:, step : step + 1],
                )
                for section in ("macro", "pooled", "coverage"):
                    assert_same(one[section], saved["by_horizon"][str(step + 1)][section])
            for pattern in meta.pattern.unique():
                select = meta.pattern.eq(pattern).to_numpy()
                group = independent_summary(
                    actual[select],
                    predicted[select],
                    scales[select],
                    fallback[select],
                    clipped[select],
                )
                for section in ("macro", "pooled", "coverage"):
                    assert_same(group[section], saved["by_demand_class"][pattern][section])
            for column in ("store_id", "item_id", "cat_id", "dept_id", "state_id"):
                if column not in meta:
                    continue
                for label, indexes in meta.groupby(column, observed=True).groups.items():
                    indexes = np.asarray(indexes)
                    group = independent_summary(
                        actual[indexes],
                        predicted[indexes],
                        scales[indexes],
                        fallback[indexes],
                        clipped[indexes],
                    )
                    hierarchy.append(
                        {
                            "dataset": dataset,
                            "fold": number,
                            "model": model,
                            "scope": scope,
                            "group_type": column,
                            "group": str(label),
                            **{f"macro_{k}": v for k, v in group["macro"].items()},
                            **{f"pooled_{k}": v for k, v in group["pooled"].items()},
                            "series": len(indexes),
                            "observations": int(actual[indexes].size),
                            **{
                                f"defined_{k}": v
                                for k, v in group["coverage"]["defined_series"].items()
                            },
                            **{
                                f"undefined_{k}": v
                                for k, v in group["coverage"]["undefined_series"].items()
                            },
                            "fallback_observations": group["coverage"]["fallback_observations"],
                        }
                    )
            summary.pop("per_series")
            part = hierarchy_parts / f"{state['run_id']}.parquet"
            partial_part = part.with_suffix(".partial")
            pd.DataFrame(hierarchy).to_parquet(partial_part, index=False)
            partial_part.replace(part)
            current_parts.append(part)
            hierarchy.clear()
            error_evidence = None
            if phase in ("3d", "3e"):
                error_directory = OUTPUT / "errors"
                error_directory.mkdir(exist_ok=True)
                path = error_directory / f"{state['run_id']}.parquet"
                temporary = path.with_suffix(".partial")
                error_frame = pd.DataFrame(
                    {
                        "dataset": dataset,
                        "scope": scope,
                        "model": model,
                        "run_id": state["run_id"],
                        "fold": number,
                        "series_id": np.repeat(series, 28),
                        "target_date": np.tile(
                            pd.date_range(fold.validation_start, periods=28), len(series)
                        ),
                        "horizon_step": np.tile(np.arange(1, 29, dtype="int8"), len(series)),
                        "actual": actual.ravel(),
                        "prediction": predicted.ravel(),
                        "error": (predicted - actual).ravel(),
                        "is_fallback": fallback.ravel(),
                        "was_clipped": clipped.ravel(),
                    }
                )
                error_frame.to_parquet(temporary, index=False)
                temporary.replace(path)
                error_evidence = {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": file_digest(path),
                }
                del error_frame
            audits.append(
                {
                    "dataset": dataset,
                    "fold": number,
                    "model": model,
                    "scope": scope,
                    "run_id": state["run_id"],
                    "status": "passed",
                    "duplicate_keys": 0,
                    "native": native_summary,
                    "ml_training": training_audit,
                    "errors": error_evidence,
                    "actual_method_series": {
                        str(k): int(v) for k, v in delivery.actual_method.value_counts().items()
                    },
                    "fallback_reason_series": {
                        str(k): int(v)
                        for k, v in delivery.loc[delivery.is_fallback, "reason"]
                        .value_counts()
                        .items()
                    },
                    **summary,
                }
            )
            print(
                f"AUDITED {dataset} fold {number} {model}: {actual.size:,} predictions", flush=True
            )
        del prepared, panel, actual, predicted
        gc.collect()
    if verify_sources() != before:
        raise ValueError("Source hashes changed during independent audit")
    destination = OUTPUT / f"{phase}_hierarchy_metrics.parquet"
    temporary = destination.with_suffix(".partial")
    with pq.ParquetWriter(temporary, pq.read_schema(current_parts[0])) as writer:
        for part in current_parts:
            for batch in pq.ParquetFile(part).iter_batches(batch_size=8192):
                writer.write_batch(batch)
    temporary.replace(destination)
    output = ROOT / "reports/forecasting"
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(
        output / f"phase{phase}_gate.json",
        {
            "status": "passed",
            "phase": phase,
            "source_hashes_unchanged": True,
            "final_holdout_targets_accessed": False,
            "independent_reconciliation": True,
            "runs": audits,
            "audit_seconds": time.perf_counter() - started,
            "audit_os_peak_working_set_bytes": getattr(
                psutil.Process().memory_info(), "peak_wset", None
            ),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", default="3b")
    args = parser.parse_args()
    from intelligent_demand.models.baselines import BASELINES

    audit_phase(args.phase, BASELINES if args.phase == "3b" else None)


if __name__ == "__main__":
    main()
