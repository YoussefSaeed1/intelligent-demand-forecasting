"""Independent NumPy audits of complete Phase 4 validation prediction grids."""

import argparse
import gc
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psutil

from intelligent_demand.evaluation.benchmark_audit import (
    assert_same,
    independent_summary,
    prediction_arrays,
    reconcile_series_metrics,
    validation_array,
)
from intelligent_demand.evaluation.ml_audit import audit_ml_training
from intelligent_demand.evaluation.splits import load_splits
from intelligent_demand.experiments.benchmark import population, verify_sources
from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.data import ParquetSource
from intelligent_demand.experiments.registry import ExperimentRegistry, atomic_json
from intelligent_demand.tuning.authority import ledger_events
from intelligent_demand.tuning.plan import OUTPUT, REPORTS, ROOT, load_plan, require_phase
from intelligent_demand.tuning.runner import (
    Phase4Source,
    execution_contract,
    experiment_config,
    refresh_case,
)


def training_scales_numpy(panel):
    result = np.empty((len(panel.metadata), 2), dtype=float)
    for start in range(0, len(result), 128):
        values = panel.values[start : start + 128].astype(float)
        difference = values[:, 7:] - values[:, :-7]
        result[start : start + len(values), 0] = np.abs(difference).sum(axis=1) / (
            len(panel.dates) - 7
        )
        result[start : start + len(values), 1] = np.square(difference).sum(axis=1) / (
            len(panel.dates) - 7
        )
    result[result == 0] = np.nan
    return result


def training_sampling_profile(state, directory, panel):
    """Independently reproduce seeded time strata and describe actual retained labels."""
    metadata = json.loads((directory / state["outputs"]["model_metadata"]["path"]).read_text())[0]
    config = state["specification"]["model_configuration"]
    cache = Path(config["feature_cache"]) / identity(metadata["feature_cache_contract"])
    manifest = json.loads((cache / "complete.json").read_text())
    positions = np.load(cache / manifest["names"]["positions"], mmap_mode="r")
    labels = np.load(cache / manifest["names"]["labels"], mmap_mode="r")
    count = min(len(panel.dates) - 56, config["maximum_training_rows"] // len(panel.metadata))
    boundaries = np.linspace(56, len(panel.dates), count + 1, dtype=int)
    expected = np.random.default_rng(state["specification"]["random_seed"]).integers(
        boundaries[:-1], boundaries[1:], size=(len(panel.metadata), count)
    )
    if not np.array_equal(positions[:, 0], np.repeat(np.arange(len(panel.metadata)), count)):
        raise ValueError("Sampling does not retain equal coverage of every series")
    if not np.array_equal(positions[:, 1], expected.ravel()):
        raise ValueError("Sampling does not reproduce the frozen seeded time strata")
    targets = positions[:, 1]
    return {
        "status": "passed",
        "seeded_strata_reproduced": True,
        "labels": len(labels),
        "labels_per_series": count,
        "series": len(panel.metadata),
        "stores": int(panel.metadata.store_id.nunique()),
        "products": int(panel.metadata.item_id.nunique()),
        "classes_series": {
            str(k): int(v) for k, v in panel.metadata.pattern.value_counts().items()
        },
        "zero_labels": int(np.count_nonzero(labels == 0)),
        "zero_label_percent": float(100 * np.mean(labels == 0)),
        "negative_labels": int(np.count_nonzero(labels < 0)),
        "earliest_label": str(panel.dates[int(targets.min())].date()),
        "latest_label": str(panel.dates[int(targets.max())].date()),
        "eligible_label_fraction": len(labels) / (len(panel.metadata) * (len(panel.dates) - 56)),
        "temporal_quartile_labels": np.histogram(
            targets, bins=np.linspace(56, len(panel.dates), 5)
        )[0].tolist(),
    }


def hierarchy_table(actual, predicted, scales, fallback, clipped, metadata):
    """Grouped leaf errors, not aggregate-node forecasting errors or official WRMSSE."""
    metrics = independent_summary(actual, predicted, scales, fallback, clipped)
    difference = predicted - actual
    table = pd.DataFrame(metrics["per_series"])
    table["actual"] = actual.sum(axis=1)
    table["absolute_error"] = np.abs(difference).sum(axis=1)
    table["squared_error"] = np.square(difference).sum(axis=1)
    table["error"] = difference.sum(axis=1)
    table["fallback_observations"] = fallback.sum(axis=1)
    table["clipped_observations"] = clipped.sum(axis=1)
    parts = []
    for field in ("store_id", "item_id", "cat_id", "dept_id", "state_id"):
        if field not in metadata:
            continue
        working = table.assign(group=metadata[field].astype(str).to_numpy())
        grouped = working.groupby("group", sort=True)
        totals = grouped[
            [
                "actual",
                "absolute_error",
                "squared_error",
                "error",
                "fallback_observations",
                "clipped_observations",
            ]
        ].sum()
        count = grouped.size()
        observations = count * actual.shape[1]
        denominator = totals.actual.where(totals.actual.gt(0))
        result = pd.DataFrame(
            {
                "group_type": field,
                "series": count,
                "observations": observations,
                "pooled_mae": totals.absolute_error / observations,
                "pooled_rmse": np.sqrt(totals.squared_error / observations),
                "pooled_wape_percent": 100 * totals.absolute_error / denominator,
                "pooled_bias_units": totals.error / observations,
                "fallback_observations": totals.fallback_observations,
                "clipped_observations": totals.clipped_observations,
            }
        )
        names = list(metrics["per_series"])
        means, defined = grouped[names].mean(), grouped[names].count()
        for metric in names:
            result[f"macro_{metric}"] = means[metric]
            result[f"defined_{metric}"] = defined[metric]
            result[f"undefined_{metric}"] = count - defined[metric]
        parts.append(result.reset_index())
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def audit_validation(readonly=False):
    require_phase("4a")
    if ledger_events() and not readonly:
        raise ValueError("Cannot audit/select validation candidates after final access")
    plan = load_plan()
    execution_contract()
    config = experiment_config()
    registry = ExperimentRegistry(config.registry_directory)
    before = verify_sources()
    started = time.perf_counter()
    trial_records = [refresh_case(case) for case in plan["trials"]]
    if any(case["status"] != "completed" for case in trial_records):
        raise ValueError("All allocated cases must be accounted for before selecting final models")
    audits = []
    semantic_caches = set()
    audited_training = []
    for dataset in ("store_item", "m5"):
        metadata = population(dataset)
        series = tuple(metadata.series_id)
        fingerprint = plan["source_sha256"][f"data/processed/{dataset}/daily_sales.parquet"]
        for fold in load_splits(config.split_manifest)[dataset]:
            source = Phase4Source(
                ROOT / f"data/processed/{dataset}/daily_sales.parquet",
                dataset,
                metadata,
                OUTPUT / "cache",
                fingerprint,
            )
            panel = source.panel(fold, series)
            scales = training_scales_numpy(panel)
            actual = validation_array(ParquetSource(source.path, dataset), fold, series)
            cohort = []
            for case in trial_records:
                if case["dataset"] != dataset:
                    continue
                run_id = case["runs"][fold.number - 1]
                state = registry.completed(run_id)
                cohort.append(run_id)
                directory = registry.directory(run_id)
                predicted, fallback, clipped = prediction_arrays(
                    directory / state["outputs"]["predictions"]["path"], state, fold, series
                )
                summary = independent_summary(actual, predicted, scales, fallback, clipped)
                saved = json.loads((directory / state["outputs"]["metrics"]["path"]).read_text())
                for section in ("macro", "pooled", "coverage"):
                    assert_same(summary[section], saved["all"][section])
                reconcile_series_metrics(summary["per_series"], saved["all"]["per_series"], series)
                for step in range(28):
                    group = independent_summary(
                        actual[:, step : step + 1],
                        predicted[:, step : step + 1],
                        scales,
                        fallback[:, step : step + 1],
                        clipped[:, step : step + 1],
                    )
                    for section in ("macro", "pooled", "coverage"):
                        assert_same(group[section], saved["by_horizon"][str(step + 1)][section])
                for pattern in metadata.pattern.unique():
                    mask = metadata.pattern.eq(pattern).to_numpy()
                    group = independent_summary(
                        actual[mask], predicted[mask], scales[mask], fallback[mask], clipped[mask]
                    )
                    for section in ("macro", "pooled", "coverage"):
                        assert_same(group[section], saved["by_demand_class"][pattern][section])
                delivery = pd.read_parquet(
                    directory / state["outputs"]["model_0_delivery"]["path"]
                ).sort_values("series_id")
                if (
                    tuple(delivery.series_id) != series
                    or not delivery.requested_method.eq(case["model"]).all()
                    or not np.array_equal(
                        fallback, np.repeat(delivery.is_fallback.to_numpy()[:, None], 28, axis=1)
                    )
                    or not delivery.loc[~delivery.is_fallback, "actual_method"]
                    .eq(case["model"])
                    .all()
                    or fallback.all()
                ):
                    raise ValueError("Native/fallback classification is incomplete or invalid")
                if case["model"] in ("random_forest", "lightgbm"):
                    model_metadata = json.loads(
                        (directory / state["outputs"]["model_metadata"]["path"]).read_text()
                    )[0]
                    cache_id = identity(model_metadata["feature_cache_contract"])
                    proof = json.loads(
                        (
                            directory / state["outputs"]["model_0_reload_validation"]["path"]
                        ).read_text()
                    )
                    if proof["passed"] is not True or proof["probe_rows"] != 16:
                        raise ValueError("Fitted model reload evidence failed")
                    if cache_id not in semantic_caches:
                        checked = audit_ml_training(state, directory, panel)
                        checked["sampling_profile"] = training_sampling_profile(
                            state, directory, panel
                        )
                        audited_training.append(
                            {
                                "dataset": dataset,
                                "fold": fold.number,
                                "cache_id": cache_id,
                                **checked,
                            }
                        )
                        semantic_caches.add(cache_id)
                    schema = json.loads(
                        (directory / state["outputs"]["model_0_feature_schema"]["path"]).read_text()
                    )
                    if any(
                        "price" in name or "event" in name or "snap" in name
                        for name in schema["feature_names"]
                    ):
                        raise ValueError("Unavailable covariate entered Phase 4 ML")
                parts = OUTPUT / "validation_hierarchy"
                parts.mkdir(exist_ok=True)
                if not readonly:
                    hierarchy_table(
                        actual, predicted, scales, fallback, clipped, metadata
                    ).to_parquet(parts / f"{case['trial_id']}_f{fold.number}.parquet", index=False)
                summary.pop("per_series")
                audits.append(
                    {
                        "dataset": dataset,
                        "fold": fold.number,
                        "trial_id": case["trial_id"],
                        "model": case["model"],
                        "run_id": run_id,
                        "status": "passed",
                        "duplicate_keys": 0,
                        "fallback_reasons": {
                            str(k): int(v)
                            for k, v in delivery.loc[delivery.is_fallback, "reason"]
                            .value_counts()
                            .items()
                        },
                        **summary,
                    }
                )
                print(
                    f"AUDITED {case['trial_id']} fold {fold.number}: {actual.size:,} forecasts",
                    flush=True,
                )
            registry.comparison_candidates(cohort)
            del panel, source, actual, predicted
            gc.collect()
    leaderboard = []
    for case in trial_records:
        rows = [r for r in audits if r["trial_id"] == case["trial_id"]]
        if len(rows) != 4 or {r["fold"] for r in rows} != {1, 2, 3, 4}:
            raise ValueError("Incomplete four-origin audited case")
        primary = float(np.mean([r["macro"]["mae"] for r in rows]))
        if not np.isclose(primary, case["primary_score"], rtol=1e-12, atol=1e-12):
            raise ValueError("Trial primary objective does not reconcile")
        n = sum(r["coverage"]["observations"] for r in rows)
        a = sum(r["totals"]["actual"] for r in rows)
        resources = [
            json.loads((OUTPUT / "resources" / f"{case['trial_id']}_f{number}.json").read_text())
            for number in (1, 2, 3, 4)
        ]
        leaderboard.append(
            {
                **case,
                "primary_score": primary,
                "observations": n,
                "pooled_rmse": float(np.sqrt(sum(r["totals"]["squared_error"] for r in rows) / n)),
                "pooled_wape_percent": 100 * sum(r["totals"]["absolute_error"] for r in rows) / a,
                "bias_units": sum(r["totals"]["error"] for r in rows) / n,
                "macro_mase": float(np.mean([r["macro"]["mase"] for r in rows])),
                "macro_rmsse": float(np.mean([r["macro"]["rmsse"] for r in rows])),
                "fallback_observations": sum(r["coverage"]["fallback_observations"] for r in rows),
                "worker_seconds": sum(r["elapsed_seconds"] for r in resources),
                "peak_rss_mib": max(r["peak_worker_rss_bytes"] for r in resources) / 2**20,
            }
        )
    if before != verify_sources():
        raise ValueError("Source hashes changed during validation audit")
    record = {
        "phase": "4b",
        "status": "passed",
        "plan_sha256": plan["contract_sha256"],
        "source_hashes_unchanged": True,
        "holdout_targets_accessed": False,
        "quality_checks_passed": False,
        "trials": leaderboard,
        "runs": audits,
        "unique_training_caches_semantically_audited": audited_training,
        "audit_seconds": time.perf_counter() - started,
        "audit_peak_working_set_bytes": getattr(psutil.Process().memory_info(), "peak_wset", None),
    }
    if readonly:
        saved = json.loads((REPORTS / "phase4b_gate.json").read_text())
        if saved["trials"] != leaderboard or saved["runs"] != audits:
            raise ValueError("Saved validation evidence differs from independent recalculation")
    else:
        atomic_json(REPORTS / "phase4b_gate.json", record)
        atomic_json(OUTPUT / "trial_leaderboard.json", leaderboard)
    print(
        json.dumps(
            {
                "phase": "4b",
                "scientific_gate": "passed",
                "trials": len(leaderboard),
                "fold_runs": len(audits),
                "forecasts": sum(r["coverage"]["observations"] for r in audits),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-saved",
        action="store_true",
        help="Verify validation evidence without rewriting its gate or rankings",
    )
    audit_validation(readonly=parser.parse_args().verify_saved)
