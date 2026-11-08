"""Frozen final refits, pre-target sealing, and a single canonical holdout assessment."""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date

import numpy as np
import pandas as pd
import psutil
import pyarrow as pa
import pyarrow.dataset as ds

from intelligent_demand.evaluation.benchmark_audit import (
    assert_same,
    independent_summary,
    prediction_arrays,
    reconcile_series_metrics,
)
from intelligent_demand.evaluation.ml_audit import audit_ml_training
from intelligent_demand.evaluation.predictions import PredictionWriter
from intelligent_demand.evaluation.scoring import score_predictions
from intelligent_demand.experiments.benchmark import population, verify_sources
from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.ownership import CaseLock
from intelligent_demand.experiments.registry import atomic_json, file_digest, utc_now
from intelligent_demand.tuning.authority import (
    append_access,
    assert_training_unlocked,
    begin_canonical_access,
    final_fold,
    ledger_events,
    verified_bundle,
    verify_frozen,
)
from intelligent_demand.tuning.plan import OUTPUT, REPORTS, ROOT, load_plan, publish_once
from intelligent_demand.tuning.reconcile import (
    hierarchy_table,
    training_sampling_profile,
    training_scales_numpy,
)
from intelligent_demand.tuning.runner import Phase4Source, confirmed_stopped, registry_for
from intelligent_demand.tuning.selection import environment_versions


def source_path(dataset):
    return ROOT / f"data/processed/{dataset}/daily_sales.parquet"


def parquet_once(path, frame):
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.partial")
    try:
        frame.to_parquet(temporary, index=False)
        with temporary.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def assert_unopened():
    if any(e["event"] == "canonical_targets_read_started" for e in ledger_events()):
        raise ValueError("Final targets were already opened; forecasting/refitting is prohibited")


def verify_forecast(record):
    for value in record["files"].values():
        path = (OUTPUT / value["path"]).resolve()
        if not path.is_relative_to(OUTPUT.resolve()) or file_digest(path) != value["sha256"]:
            raise ValueError("Frozen final forecast/model artifact changed")
    if record["status"] != "forecasts_frozen":
        raise ValueError("Incomplete final forecast")
    return record


def forecast_worker(dataset, trial_id):
    # Fail before creating a lock/job or reading a model on the closed assessment.
    assert_unopened()
    if (dataset not in ("store_item", "m5") or not isinstance(trial_id, str)
            or not re.fullmatch(r"[a-z0-9_]{1,128}", trial_id)):
        raise ValueError("Invalid dataset or trial identifier")
    lock = OUTPUT / "worker_locks" / f"{dataset}_{trial_id}.json"
    with CaseLock(lock):
        return _forecast_worker_owned(dataset, trial_id)


def _forecast_worker_owned(dataset, trial_id):
    frozen = verify_frozen()
    if environment_versions() != frozen["package_versions"]:
        raise ValueError("Final environment differs from the pre-holdout freeze")
    assert_unopened()
    definition = frozen["datasets"][dataset]
    case = next(e for e in definition["evaluations"] if e["trial_id"] == trial_id)
    fold = final_fold(dataset)
    assert_training_unlocked(fold)
    job = OUTPUT / "final_jobs" / f"{trial_id}.json"
    if job.exists():
        previous = json.loads(job.read_text())
        if previous["status"] == "forecasts_frozen":
            result = verify_forecast(previous)
            print(
                json.dumps({"trial_id": trial_id, "reused": True, "run_id": result["run_id"]}),
                flush=True,
            )
            return
        if previous["status"] == "running" and not confirmed_stopped(previous["owner_pid"]):
            raise ValueError("A live final worker already owns this case")
    attempts = OUTPUT / "final_forecasts" / dataset / trial_id
    if attempts.exists() and len(list(attempts.iterdir())) >= 2:
        raise ValueError("Final refit attempt limit exhausted; preserve failures")
    run_id = uuid.uuid4().hex
    directory = OUTPUT / "final_forecasts" / dataset / trial_id / run_id
    directory.mkdir(parents=True)
    state = {
        "status": "running",
        "run_id": run_id,
        "dataset": dataset,
        "trial_id": trial_id,
        "selection_sha256": frozen["manifest_sha256"],
        "owner_pid": os.getpid(),
        "started_at_utc": utc_now(),
    }
    job.parent.mkdir(exist_ok=True)
    atomic_json(job, state)
    atomic_json(directory / "state.json", state)
    started = time.perf_counter()
    try:
        metadata = population(dataset)
        series = tuple(metadata.series_id)
        if (
            identity(list(series)) != definition["series_sha256"]
            or len(series) != definition["series_count"]
        ):
            raise ValueError("Final population differs from the frozen plan")
        path = source_path(dataset)
        fingerprint = frozen["source_sha256"][f"data/processed/{dataset}/daily_sales.parquet"]
        if file_digest(path) != fingerprint:
            raise ValueError("Final source fingerprint changed")
        source = Phase4Source(path, dataset, metadata, OUTPUT / "cache", fingerprint)
        panel = source.panel(fold, series)
        scales = source.scales(fold, series)
        independent_scales = training_scales_numpy(panel)
        np.testing.assert_allclose(
            scales[["scale_absolute", "scale_squared"]].to_numpy(),
            independent_scales,
            rtol=1e-12,
            atol=1e-12,
            equal_nan=True,
        )
        parquet_once(directory / "scales.parquet", scales)
        with (directory / "independent_scales.npy").open("xb") as stream:
            np.save(stream, independent_scales)
            stream.flush()
            os.fsync(stream.fileno())
        configuration = {
            "phase": "4c",
            "parameters": case["parameters"],
            "random_seed": case["seed"],
            "max_threads": 4,
            "maximum_training_rows": definition["maximum_training_rows"],
            "feature_cache": str(OUTPUT / "feature_cache"),
            "source_fingerprint": fingerprint,
            "plan_sha256": frozen["plan_sha256"],
            "selection_sha256": frozen["manifest_sha256"],
        }
        models = registry_for(case["model"])
        model = models.create(case["model"], "1")
        view = source.at_origin(fold, series)
        stage = time.perf_counter()
        model.fit(view, configuration)
        fit_seconds = time.perf_counter() - stage
        writer = PredictionWriter(
            directory / "predictions.parquet", fold, series, model.info, run_id
        )
        stage = time.perf_counter()
        try:
            for batch in model.predict(fold.origin, 28, view.calendar_features()):
                writer.write(batch)
            writer.finish()
        finally:
            writer.close()
        prediction_seconds = time.perf_counter() - stage
        model_dir = directory / "models" / "0"
        model_dir.mkdir(parents=True)
        files = {
            "predictions": directory / "predictions.parquet",
            "scales": directory / "scales.parquet",
            "independent_scales": directory / "independent_scales.npy",
        }
        for key, value in model.save_artifacts(model_dir).items():
            value = value.resolve()
            if not value.is_relative_to(model_dir.resolve()):
                raise ValueError("Model artifact escaped its final run")
            files[f"model_0_{key}"] = value
        atomic_json(directory / "model_metadata.json", [model.metadata()])
        files["model_metadata"] = directory / "model_metadata.json"
        spec = {
            "dataset_id": dataset,
            "fold": {k: str(v) if isinstance(v, date) else v for k, v in asdict(fold).items()},
            "model": asdict(model.info),
            "model_configuration": configuration,
            "random_seed": case["seed"],
            "source_fingerprint": fingerprint,
        }
        training_audit = None
        if case["model"] in ("random_forest", "lightgbm"):
            audit_state = {
                "specification": spec,
                "outputs": {k: {"path": str(p.relative_to(directory))} for k, p in files.items()},
            }
            training_audit = audit_ml_training(audit_state, directory, panel)
            training_audit["sampling_profile"] = training_sampling_profile(
                audit_state, directory, panel
            )
        proof = {
            "independent_training_scales_reconciled": True,
            "training_only_max_date": str(fold.origin),
            "feature_audit": training_audit,
            "holdout_targets_accessed": False,
        }
        atomic_json(directory / "pre_target_audit.json", proof)
        files["pre_target_audit"] = directory / "pre_target_audit.json"
        if file_digest(path) != fingerprint:
            raise ValueError("Source changed during final refit")
        record = {
            **state,
            "status": "forecasts_frozen",
            "role": case["role"],
            "model": case["model"],
            "specification": spec,
            "frozen_at_utc": utc_now(),
            "fit_seconds": fit_seconds,
            "prediction_seconds": prediction_seconds,
            "worker_seconds": time.perf_counter() - started,
            "files": {
                k: {"path": p.relative_to(OUTPUT).as_posix(), "sha256": file_digest(p)}
                for k, p in files.items()
            },
            "os_peak_working_set_bytes": getattr(psutil.Process().memory_info(), "peak_wset", None),
        }
        publish_once(directory / "frozen_forecast.json", record)
        atomic_json(directory / "state.json", record)
        atomic_json(job, record)
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "trial_id": trial_id,
                    "reused": False,
                    "worker_seconds": record["worker_seconds"],
                    "os_peak_working_set_bytes": record["os_peak_working_set_bytes"],
                }
            ),
            flush=True,
        )
    except BaseException as exc:
        failure = {
            **state,
            "status": "interrupted"
            if isinstance(exc, (KeyboardInterrupt, SystemExit))
            else "failed",
            "error_type": type(exc).__name__,
            "ended_at_utc": utc_now(),
        }
        atomic_json(directory / "state.json", failure)
        atomic_json(job, failure)
        raise


@contextmanager
def forecast_lock():
    path = OUTPUT / "final_forecast.lock"
    with path.open("x") as stream:
        stream.write(str(os.getpid()))
    try:
        yield
    finally:
        path.unlink()


def forecast_all():
    assert_unopened()
    with forecast_lock():
        _forecast_all()


def _forecast_all():
    frozen = verify_frozen()
    assert_unopened()
    if (OUTPUT / "search.lock").exists():
        raise ValueError("Search supervisor still owns execution")
    if (OUTPUT / "sealed_predictions.json").exists():
        verified_bundle()
        print("Reused verified immutable final forecast bundle")
        return
    if verify_sources() != frozen["source_sha256"]:
        raise ValueError("Source hashes changed before final refits")
    resources = load_plan()["settings"]["resources"]
    env = {
        **os.environ,
        "OMP_NUM_THREADS": "4",
        "OPENBLAS_NUM_THREADS": "4",
        "MKL_NUM_THREADS": "4",
        "PYTHONUNBUFFERED": "1",
    }
    records = []
    for dataset, definition in frozen["datasets"].items():
        for case in definition["evaluations"]:
            trial_id = case["trial_id"]
            pointer = OUTPUT / "final_jobs" / f"{trial_id}.json"
            if pointer.exists() and json.loads(pointer.read_text())["status"] == "forecasts_frozen":
                records.append(verify_forecast(json.loads(pointer.read_text())))
                continue
            if psutil.virtual_memory().available < resources["minimum_available_mib"] * 2**20:
                raise MemoryError("Insufficient available memory for final refit")
            log = OUTPUT / f"final_{trial_id}.log"
            print(f"FINAL REFIT {dataset} {trial_id}; targets still locked", flush=True)
            started = time.monotonic()
            peak = 0
            last_report = 0
            reason = None
            with log.open("a", encoding="utf-8") as stream:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "intelligent_demand.tuning.final",
                        "worker",
                        "--dataset",
                        dataset,
                        "--case",
                        trial_id,
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
                try:
                    while process.poll() is None:
                        try:
                            task = psutil.Process(process.pid)
                            children = task.children(recursive=True)
                            rss = task.memory_info().rss + sum(
                                c.memory_info().rss for c in children
                            )
                            peak = max(peak, rss)
                            elapsed = time.monotonic() - started
                            if rss > resources["worker_rss_mib"] * 2**20:
                                reason = "memory_budget_exceeded"
                            if elapsed > resources["worker_timeout_seconds"]:
                                reason = "runtime_budget_exceeded"
                            if elapsed - last_report >= 15:
                                print(
                                    f"FINAL RUNNING {trial_id}: {elapsed:.0f}s / "
                                    f"{rss / 2**20:.0f} MiB",
                                    flush=True,
                                )
                                last_report = elapsed
                            if reason:
                                for child in children:
                                    child.terminate()
                                process.terminate()
                                process.wait(timeout=30)
                                break
                        except psutil.NoSuchProcess:
                            pass
                        time.sleep(0.5)
                except BaseException:
                    if process.poll() is None:
                        task = psutil.Process(process.pid)
                        for child in task.children(recursive=True):
                            child.terminate()
                        process.terminate()
                        process.wait(timeout=30)
                    raise
            resource = {
                "trial_id": trial_id,
                "dataset": dataset,
                "elapsed_seconds": time.monotonic() - started,
                "peak_worker_rss_bytes": peak,
                "reason": reason,
                "exit_code": process.returncode,
            }
            atomic_json(OUTPUT / f"final_{trial_id}_resource.json", resource)
            if process.returncode != 0 or reason:
                if pointer.exists():
                    failed = json.loads(pointer.read_text())
                    if failed["status"] == "running" and confirmed_stopped(failed["owner_pid"]):
                        atomic_json(
                            pointer,
                            {
                                **failed,
                                "status": "interrupted",
                                "reason": reason or "stopped_worker",
                            },
                        )
                raise RuntimeError(
                    "Final refit stopped before target access; preserve and diagnose its log"
                )
            record = verify_forecast(json.loads(pointer.read_text()))
            records.append(record)
            print(
                f"FINAL SEALED {trial_id}: {resource['elapsed_seconds']:.1f}s; no targets read",
                flush=True,
            )
    bundle = {
        "selection_sha256": frozen["manifest_sha256"],
        "sealed_at_utc": utc_now(),
        "forecasts": records,
        "holdout_targets_accessed": False,
    }
    bundle["bundle_sha256"] = identity(bundle)
    publish_once(OUTPUT / "sealed_predictions.json", bundle)
    verified_bundle()
    print(
        json.dumps(
            {
                "status": "all_forecasts_sealed",
                "bundle_sha256": bundle["bundle_sha256"],
                "models": len(records),
            },
            indent=2,
        )
    )


def read_canonical_targets_once(dataset):
    begin_canonical_access(dataset)
    frozen = verify_frozen()
    definition = frozen["datasets"][dataset]
    fold = final_fold(dataset)
    metadata = population(dataset)
    series = tuple(metadata.series_id)
    expression = (
        (ds.field("dataset_id") == dataset)
        & (ds.field("date") >= pa.scalar(fold.validation_start, pa.date32()))
        & (ds.field("date") <= pa.scalar(fold.validation_end, pa.date32()))
        & ds.field("series_id").isin(series)
    )
    scanner = ds.dataset(source_path(dataset), format="parquet").scanner(
        columns=["dataset_id", "series_id", "date", "sales_units"],
        filter=expression,
        batch_size=65536,
        use_threads=False,
    )
    parts = []
    count = 0
    for batch in scanner.to_batches():
        if batch.num_rows:
            parts.append(batch.to_pandas(date_as_object=False))
            count += batch.num_rows
            if count > definition["series_count"] * 28:
                raise ValueError("Holdout read exceeds its frozen grid")
    if not parts:
        raise ValueError("No final target rows")
    actual = pd.concat(parts, ignore_index=True).rename(
        columns={"date": "target_date", "sales_units": "actual"}
    )
    actual["target_date"] = pd.to_datetime(actual.target_date)
    if (
        len(actual) != definition["series_count"] * 28
        or actual.duplicated(["series_id", "target_date"]).any()
        or not actual.series_id.isin(series).all()
        or not actual.dataset_id.eq(dataset).all()
        or not np.isfinite(actual.actual).all()
        or (actual.actual < 0).any()
        or not actual.target_date.between(
            str(fold.validation_start), str(fold.validation_end)
        ).all()
    ):
        raise ValueError("Final actual grid is malformed; preserve access history and stop")
    directory = OUTPUT / "final_actuals"
    directory.mkdir(exist_ok=True)
    path = directory / f"{dataset}.parquet"
    parquet_once(path, actual)
    publish_once(
        directory / f"{dataset}.json",
        {
            "path": path.relative_to(OUTPUT).as_posix(),
            "sha256": file_digest(path),
            "rows": len(actual),
            "selection_sha256": frozen["manifest_sha256"],
            "source_fingerprint": frozen["source_sha256"][
                f"data/processed/{dataset}/daily_sales.parquet"
            ],
        },
    )
    append_access(
        "canonical_targets_read_completed",
        dataset,
        {"actual_sha256": file_digest(path), "rows": len(actual)},
    )
    return actual


def saved_actuals(dataset, purpose):
    if purpose not in ("independent_metric_audit", "final_report"):
        raise ValueError("Saved final actuals may only support the frozen assessment audit/report")
    verified_bundle()
    manifest = json.loads((OUTPUT / "final_actuals" / f"{dataset}.json").read_text())
    frozen = verify_frozen()
    receipts = [
        e
        for e in ledger_events()
        if e["dataset"] == dataset and e["event"] == "canonical_targets_read_completed"
    ]
    if (
        len(receipts) != 1
        or receipts[0]["details"]["actual_sha256"] != manifest["sha256"]
        or manifest["selection_sha256"] != frozen["manifest_sha256"]
        or manifest["rows"] != frozen["datasets"][dataset]["series_count"] * 28
    ):
        raise ValueError("Saved actuals differ from the canonical-read ledger receipt")
    path = (OUTPUT / manifest["path"]).resolve()
    if not path.is_relative_to(OUTPUT.resolve()) or file_digest(path) != manifest["sha256"]:
        raise ValueError("Final assessment actual snapshot changed")
    append_access(
        "saved_assessment_actuals_read", dataset, {"purpose": purpose, "sha256": manifest["sha256"]}
    )
    return pd.read_parquet(path)


def verify_pre_target_bundle():
    """Check complete prediction grids and delivery evidence without loading any targets."""
    frozen = verify_frozen()
    if environment_versions() != frozen["package_versions"]:
        raise ValueError("Final environment differs from the pre-holdout freeze")
    bundle = verified_bundle()
    expected = [(d, c["trial_id"]) for d, v in frozen["datasets"].items() for c in v["evaluations"]]
    if len(bundle["forecasts"]) != len(expected):
        raise ValueError("Final bundle has duplicate or missing cases")
    if not frozen["created_at_utc"] <= bundle["sealed_at_utc"]:
        raise ValueError("Final bundle predates the model freeze")
    for record in bundle["forecasts"]:
        verify_forecast(record)
        dataset = record["dataset"]
        definition = frozen["datasets"][dataset]
        case = next(c for c in definition["evaluations"] if c["trial_id"] == record["trial_id"])
        if (
            record["model"] != case["model"]
            or record["role"] != case["role"]
            or record["selection_sha256"] != frozen["manifest_sha256"]
            or record["specification"]["model_configuration"]["parameters"] != case["parameters"]
            or not frozen["created_at_utc"] <= record["frozen_at_utc"] <= bundle["sealed_at_utc"]
        ):
            raise ValueError("Final forecast does not match its frozen configuration")
        metadata = population(dataset)
        series = tuple(metadata.series_id)
        predicted, fallback, _ = prediction_arrays(
            OUTPUT / record["files"]["predictions"]["path"],
            {"run_id": record["run_id"], "specification": record["specification"]},
            final_fold(dataset),
            series,
        )
        proof = json.loads((OUTPUT / record["files"]["pre_target_audit"]["path"]).read_text())
        if (
            proof["holdout_targets_accessed"] is not False
            or proof["independent_training_scales_reconciled"] is not True
            or proof["training_only_max_date"] != definition["origin"]
        ):
            raise ValueError("Pre-target training audit is incomplete")
        delivery = pd.read_parquet(
            OUTPUT / record["files"]["model_0_delivery"]["path"]
        ).sort_values("series_id")
        if (
            tuple(delivery.series_id) != series
            or not delivery.requested_method.eq(case["model"]).all()
            or not delivery.loc[~delivery.is_fallback, "actual_method"].eq(case["model"]).all()
            or delivery.reason.isna().any()
            or not np.array_equal(
                fallback, np.repeat(delivery.is_fallback.to_numpy()[:, None], 28, axis=1)
            )
            or fallback.all()
            or not np.isfinite(predicted).all()
        ):
            raise ValueError("Final native/fallback delivery is invalid")
    return bundle


def assess_once():
    assert_unopened()
    bundle = verify_pre_target_bundle()
    assert_unopened()
    publish_once(
        OUTPUT / "assessment_started.json",
        {"bundle_sha256": bundle["bundle_sha256"], "started_at_utc": utc_now()},
    )
    frozen = verify_frozen()
    results = []
    started = time.perf_counter()
    try:
        for dataset in frozen["datasets"]:
            actual = read_canonical_targets_once(dataset)
            fold = final_fold(dataset)
            metadata = population(dataset)
            series = tuple(metadata.series_id)
            classes = dict(zip(metadata.series_id, metadata.pattern, strict=True))
            for record in bundle["forecasts"]:
                if record["dataset"] != dataset:
                    continue
                predicted = pd.read_parquet(OUTPUT / record["files"]["predictions"]["path"])
                scales = pd.read_parquet(OUTPUT / record["files"]["scales"]["path"])
                metrics = score_predictions(
                    actual,
                    predicted,
                    scales,
                    fold,
                    series,
                    classes,
                    date.fromisoformat(frozen["datasets"][dataset]["class_as_of"]),
                )
                path = OUTPUT / "final_metrics" / f"{record['trial_id']}.json"
                publish_once(path, metrics)
                results.append(
                    {
                        "dataset": dataset,
                        "trial_id": record["trial_id"],
                        "role": record["role"],
                        "model": record["model"],
                        "run_id": record["run_id"],
                        "metrics": {
                            "path": path.relative_to(OUTPUT).as_posix(),
                            "sha256": file_digest(path),
                        },
                    }
                )
                print(
                    f"FINAL SCORED {record['trial_id']}: MAE {metrics['all']['macro']['mae']:.9f}",
                    flush=True,
                )
            append_access(
                "dataset_assessment_completed",
                dataset,
                {"models": sum(r["dataset"] == dataset for r in results)},
            )
        if verify_sources() != frozen["source_sha256"]:
            raise ValueError("Source changed during final assessment")
        result = {
            "status": "completed",
            "evaluation_kind": "final_holdout",
            "selection_sha256": frozen["manifest_sha256"],
            "bundle_sha256": bundle["bundle_sha256"],
            "completed_at_utc": utc_now(),
            "assessment_seconds": time.perf_counter() - started,
            "assessment_peak_working_set_bytes": getattr(
                psutil.Process().memory_info(), "peak_wset", None
            ),
            "results": results,
        }
        publish_once(OUTPUT / "final_evaluation.json", result)
        append_access(
            "final_assessment_completed",
            details={
                "models": len(results),
                "evaluation_sha256": file_digest(OUTPUT / "final_evaluation.json"),
            },
        )
    except BaseException as exc:
        append_access(
            "final_assessment_failed",
            details={"error_type": type(exc).__name__, "completed_models": len(results)},
        )
        raise


def audit_final(readonly=False):
    frozen = verify_frozen()
    bundle = verified_bundle()
    evaluation = json.loads((OUTPUT / "final_evaluation.json").read_text())
    if (
        evaluation["status"] != "completed"
        or evaluation["selection_sha256"] != frozen["manifest_sha256"]
        or evaluation["bundle_sha256"] != bundle["bundle_sha256"]
        or evaluation["evaluation_kind"] != "final_holdout"
    ):
        raise ValueError("Final assessment is incomplete")
    events = ledger_events()
    receipts = [e for e in events if e["event"] == "final_assessment_completed"]
    if len(receipts) != 1 or receipts[0]["details"]["evaluation_sha256"] != file_digest(
        OUTPUT / "final_evaluation.json"
    ):
        raise ValueError("Final evaluation differs from its completed ledger receipt")
    expected = {
        (r["dataset"], r["trial_id"], r["run_id"], r["model"], r["role"])
        for r in bundle["forecasts"]
    }
    delivered = {
        (r["dataset"], r["trial_id"], r["run_id"], r["model"], r["role"])
        for r in evaluation["results"]
    }
    if expected != delivered or len(evaluation["results"]) != len(expected):
        raise ValueError("Final assessment differs from the exact predeclared cases")
    for event in events:
        if event["event"] == "canonical_targets_read_started" and (
            event["timestamp_utc"] < bundle["sealed_at_utc"]
            or event["details"]["bundle_sha256"] != bundle["bundle_sha256"]
        ):
            raise ValueError("Holdout access preceded complete forecast sealing")
    for dataset in frozen["datasets"]:
        for event in (
            "canonical_targets_read_started",
            "canonical_targets_read_completed",
            "dataset_assessment_completed",
        ):
            if sum(e["dataset"] == dataset and e["event"] == event for e in events) != 1:
                raise ValueError("Final canonical-access/assessment ledger is not one-time")
    if any(e["event"] == "final_assessment_failed" for e in events):
        raise ValueError("Post-access failure is recorded; do not conceal it")
    audits = []
    for dataset in frozen["datasets"]:
        actual = saved_actuals(dataset, "independent_metric_audit")
        fold = final_fold(dataset)
        metadata = population(dataset)
        series = tuple(metadata.series_id)
        actual = actual.sort_values(["series_id", "target_date"])
        y = actual.actual.to_numpy().reshape(len(series), 28)
        for record in bundle["forecasts"]:
            if record["dataset"] != dataset:
                continue
            result = next(r for r in evaluation["results"] if r["trial_id"] == record["trial_id"])
            path = OUTPUT / result["metrics"]["path"]
            if file_digest(path) != result["metrics"]["sha256"]:
                raise ValueError("Final metric artifact changed")
            metrics = json.loads(path.read_text())
            predicted, fallback, clipped = prediction_arrays(
                OUTPUT / record["files"]["predictions"]["path"],
                {"run_id": record["run_id"], "specification": record["specification"]},
                fold,
                series,
            )
            scales = pd.read_parquet(OUTPUT / record["files"]["scales"]["path"])
            q = scales[["scale_absolute", "scale_squared"]].to_numpy()
            np.testing.assert_allclose(
                q,
                np.load(OUTPUT / record["files"]["independent_scales"]["path"]),
                rtol=1e-12,
                atol=1e-12,
                equal_nan=True,
            )
            summary = independent_summary(y, predicted, q, fallback, clipped)
            for section in ("macro", "pooled", "coverage"):
                assert_same(summary[section], metrics["all"][section])
            reconcile_series_metrics(summary["per_series"], metrics["all"]["per_series"], series)
            for step in range(28):
                one = independent_summary(
                    y[:, step : step + 1],
                    predicted[:, step : step + 1],
                    q,
                    fallback[:, step : step + 1],
                    clipped[:, step : step + 1],
                )
                for section in ("macro", "pooled", "coverage"):
                    assert_same(one[section], metrics["by_horizon"][str(step + 1)][section])
            for pattern in metadata.pattern.unique():
                mask = metadata.pattern.eq(pattern).to_numpy()
                group = independent_summary(
                    y[mask], predicted[mask], q[mask], fallback[mask], clipped[mask]
                )
                for section in ("macro", "pooled", "coverage"):
                    assert_same(group[section], metrics["by_demand_class"][pattern][section])
            delivery = pd.read_parquet(
                OUTPUT / record["files"]["model_0_delivery"]["path"]
            ).sort_values("series_id")
            if tuple(delivery.series_id) != series or not np.array_equal(
                fallback, np.repeat(delivery.is_fallback.to_numpy()[:, None], 28, axis=1)
            ):
                raise ValueError("Final fallback delivery classification mismatch")
            hierarchy = OUTPUT / "final_hierarchy"
            hierarchy.mkdir(exist_ok=True)
            if not readonly:
                hierarchy_table(y, predicted, q, fallback, clipped, metadata).to_parquet(
                    hierarchy / f"{record['trial_id']}.parquet", index=False
                )
            summary.pop("per_series")
            audits.append(
                {
                    "dataset": dataset,
                    "trial_id": record["trial_id"],
                    "model": record["model"],
                    "role": record["role"],
                    "run_id": record["run_id"],
                    "duplicate_keys": 0,
                    "status": "passed",
                    **summary,
                }
            )
    if verify_sources() != frozen["source_sha256"]:
        raise ValueError("Source fingerprints changed")
    gate = {
        "phase": "4c",
        "status": "passed",
        "evaluation_kind": "final_holdout",
        "plan_sha256": frozen["plan_sha256"],
        "selection_sha256": frozen["manifest_sha256"],
        "bundle_sha256": bundle["bundle_sha256"],
        "source_hashes_unchanged": True,
        "holdout_targets_accessed": True,
        "canonical_reads_per_dataset": 1,
        "quality_checks_passed": False,
        "runs": audits,
    }
    if readonly:
        saved = json.loads((REPORTS / "phase4c_gate.json").read_text())
        if saved["runs"] != audits or saved["bundle_sha256"] != bundle["bundle_sha256"]:
            raise ValueError("Saved final assessment differs from independent recomputation")
    else:
        atomic_json(REPORTS / "phase4c_gate.json", gate)
    print(
        json.dumps(
            {"status": "passed", "models": len(audits), "canonical_reads_per_dataset": 1}, indent=2
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["forecast", "worker", "assess", "audit", "verify"])
    parser.add_argument("--dataset", choices=["store_item", "m5"])
    parser.add_argument("--case")
    parser.add_argument(
        "--verify-saved",
        action="store_true",
        help="Audit saved final metrics without changing the quality gate",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.action == "forecast":
        forecast_all()
    elif args.action == "worker":
        if args.dataset is None or args.case is None:
            parser.error("Worker requires dataset/case")
        forecast_worker(args.dataset, args.case)
    elif args.action == "assess":
        assess_once()
    elif args.action == "audit":
        audit_final(readonly=args.verify_saved)
    else:
        print(
            json.dumps(
                {
                    "status": "verified",
                    "bundle_sha256": verify_pre_target_bundle()["bundle_sha256"],
                },
                indent=2,
            )
        )
