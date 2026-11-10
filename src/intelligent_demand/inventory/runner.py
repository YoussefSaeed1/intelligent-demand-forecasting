"""Budgeted inventory episodes; completed attempt hashes gate all later reports."""

import argparse
import gc
import json
import os
import shutil
import time
import uuid
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import psutil
import pyarrow as pa
import pyarrow.parquet as pq

from intelligent_demand.experiments.ownership import CaseLock
from intelligent_demand.experiments.registry import atomic_json
from intelligent_demand.inventory.design import POLICIES, Scenario
from intelligent_demand.inventory.engine import ForecastWindow, simulate
from intelligent_demand.inventory.inputs import load_cohort
from intelligent_demand.inventory.plan import OUTPUT, REPORTS, ROOT, file_record, plan, read
from intelligent_demand.preservation.backup import sha256, write_new
from intelligent_demand.preservation.verify import identity


def execution():
    p = plan()
    gate = read(REPORTS / "phase5b_gate.json")
    if gate["status"] != "passed" or gate["plan_sha256"] != p["sha256"]:
        raise ValueError("Phase 5B gate required")
    files = [
        file_record(path)
        for path in sorted((ROOT / "src/intelligent_demand/inventory").glob("*.py"))
        if path.name not in ("report.py", "audit.py")
    ]
    contract = {"plan_sha256": p["sha256"], "code": files}
    contract["sha256"] = identity(contract)
    path = OUTPUT / "execution.json"
    if path.exists():
        if read(path) != contract:
            raise ValueError("Simulation code changed after execution freeze")
    else:
        write_new(path, contract)
    return contract


def case_key(cohort, scenario, policy, contract):
    return identity(
        {
            "dataset": cohort["dataset"],
            "fold": cohort["fold"]["number"],
            "scenario": scenario.identifier,
            "policy": policy,
            "execution": contract["sha256"],
        }
    )[:32]


def completed(directory):
    status = read(directory / "status.json")
    if status["status"] != "completed":
        raise ValueError("Incomplete inventory experiment cannot enter a comparison")
    for item in status["files"].values():
        if sha256(ROOT / item["path"]) != item["sha256"]:
            raise ValueError("Completed inventory output changed")
    return status


def run_case(cohort, data, scenario, policy, contract, guard):
    metadata, actual, mean, predictions, coverage = data
    key = case_key(cohort, scenario, policy, contract)
    directory = OUTPUT / "runs" / key
    with CaseLock(OUTPUT / "locks" / f"{key}.json"):
        if (directory / "status.json").exists():
            previous = read(directory / "status.json")
            if previous["status"] == "completed":
                return completed(directory)
            attempts = previous["attempts"]
            if len(attempts) >= 2:
                raise ValueError("Two attempts exhausted; retain failures and investigate")
        else:
            attempts = []
        attempt = uuid.uuid4().hex
        target = directory / "attempts" / attempt
        target.mkdir(parents=True, exist_ok=False)
        state = {
            "status": "running",
            "case_id": key,
            "attempts": [*attempts, attempt],
            "dataset": cohort["dataset"],
            "fold": cohort["fold"],
            "scenario": scenario.metadata(),
            "policy": policy,
            "plan_sha256": contract["plan_sha256"],
            "execution_sha256": contract["sha256"],
            "owner_pid": os.getpid(),
            "started_at_utc": datetime.now(UTC).isoformat(),
            "forecast_source": None
            if policy == "fixed_reorder_point"
            else cohort["sources"][policy],
            "source_fallback_observations": 0
            if policy == "fixed_reorder_point"
            else coverage[policy],
        }
        atomic_json(directory / "status.json", state)
        atomic_json(target / "state.json", state)
        summary_writer = event_writer = None
        began, event_count, count = time.perf_counter(), 0, 0
        try:
            batch = plan()["settings"]["resources"]["batch_series"]
            forecast = predictions["selected_ml" if policy == "fixed_reorder_point" else policy]
            for first in range(0, len(metadata), batch):
                guard()
                last = min(first + batch, len(metadata))
                block = metadata.iloc[first:last].reset_index(drop=True)
                y = actual[first:last]
                if scenario.variability_multiplier != 1:
                    y = np.maximum(
                        0,
                        mean[first:last, None]
                        + scenario.variability_multiplier * (y - mean[first:last, None]),
                    )
                dates = tuple(pd.date_range(cohort["fold"]["validation_start"], periods=28).date)
                window = ForecastWindow(cohort["fold"]["origin"], dates, forecast[first:last])
                event_rows = (
                    None
                    if scenario.identifier == "base"
                    else np.flatnonzero(block.series_id.isin(cohort["representatives"]).to_numpy())
                )
                summary, events = simulate(
                    y, mean[first:last], window, scenario, policy, event_rows
                )
                for field in (
                    "series_id",
                    "store_id",
                    "item_id",
                    "pattern",
                    "dept_id",
                    "origin_sample_all_zero",
                    "retrospective_final_training_all_zero",
                ):
                    if field in block:
                        summary[field] = block[field].to_numpy()
                summary["historical_mean56"] = mean[first:last]
                summary["forecast_mae"] = (
                    np.nan
                    if policy == "fixed_reorder_point"
                    else np.abs(forecast[first:last] - y).mean(axis=1)
                )
                table = pa.Table.from_pandas(summary, preserve_index=False)
                if summary_writer is None:
                    summary_writer = pq.ParquetWriter(
                        target / "series.partial", table.schema, compression="zstd"
                    )
                summary_writer.write_table(table)
                count += len(summary)
                if len(events):
                    events["series_id"] = block.series_id.to_numpy()[events.series_row.to_numpy()]
                    events = events.drop(columns="series_row")
                    table = pa.Table.from_pandas(events, preserve_index=False)
                    if event_writer is None:
                        event_writer = pq.ParquetWriter(
                            target / "events.partial", table.schema, compression="zstd"
                        )
                    event_writer.write_table(table)
                    event_count += len(events)
            summary_writer.close()
            summary_writer = None
            event_writer.close()
            event_writer = None
            expected = (
                len(metadata) * 28
                if scenario.identifier == "base"
                else len(cohort["representatives"]) * 28
            )
            if count != len(metadata) or event_count != expected:
                raise ValueError("Published inventory population/event coverage differs")
            for name in ("series", "events"):
                (target / f"{name}.partial").rename(target / f"{name}.parquet")
            state.update(
                status="completed",
                series=count,
                event_rows=event_count,
                elapsed_seconds=time.perf_counter() - began,
                peak_working_set_bytes=psutil.Process().memory_info().peak_wset,
                files={
                    name: file_record(target / f"{name}.parquet") for name in ("series", "events")
                },
            )
            atomic_json(target / "state.json", state)
            atomic_json(directory / "status.json", state)
            return state
        except BaseException as exc:
            state.update(
                status="interrupted"
                if isinstance(exc, (KeyboardInterrupt, SystemExit))
                else "failed",
                error_type=type(exc).__name__,
            )
            atomic_json(target / "state.json", state)
            atomic_json(directory / "status.json", state)
            raise
        finally:
            if summary_writer is not None:
                summary_writer.close()
            if event_writer is not None:
                event_writer.close()


def run(action):
    p, contract = plan(), execution()
    if action != "smoke" and read(REPORTS / "phase5_smoke.json")["status"] != "passed":
        raise ValueError("Bounded smoke gate required")
    if action == "sensitivity" and read(REPORTS / "phase5c_gate.json")["status"] != "passed":
        raise ValueError("Independent base comparison gate required before sensitivity")
    resources = p["settings"]["resources"]
    began = time.perf_counter()
    if shutil.disk_usage(ROOT).free < resources["minimum_free_disk_gib"] * 1024**3:
        raise ValueError("Insufficient free space for bounded experiment budget")

    def guard():
        if time.perf_counter() - began > resources["max_wall_seconds"]:
            raise TimeoutError("Declared inventory execution time budget exhausted")
        if psutil.Process().memory_info().peak_wset > resources["max_worker_rss_mib"] * 1024**2:
            raise MemoryError("Declared inventory process memory budget exceeded")

    records = []
    for cohort in p["cohorts"]:
        if action == "smoke" and cohort["fold"]["number"] != 1:
            continue
        data = load_cohort(cohort)
        guard()
        if action == "smoke":
            n = min(32, len(data[0]))
            metadata, y, mean, forecasts, _ = data
            for policy in POLICIES:
                dates = tuple(pd.date_range(cohort["fold"]["validation_start"], periods=28).date)
                forecast = forecasts["selected_ml" if policy == "fixed_reorder_point" else policy][
                    :n
                ]
                summary, events = simulate(
                    y[:n],
                    mean[:n],
                    ForecastWindow(cohort["fold"]["origin"], dates, forecast),
                    Scenario(**p["scenarios"][0]),
                    policy,
                )
                if len(summary) != n or len(events) != n * 28:
                    raise ValueError("Smoke population mismatch")
            records.append({"dataset": cohort["dataset"], "series": n, "policies": 4})
        else:
            for settings in p["scenarios"]:
                scenario = Scenario(**settings)
                if (action == "base") != (scenario.identifier == "base"):
                    continue
                for policy in POLICIES:
                    result = run_case(cohort, data, scenario, policy, contract, guard)
                    records.append(result["case_id"])
                    print(
                        f"COMPLETE {cohort['dataset']} fold{cohort['fold']['number']} "
                        f"{scenario.identifier} {policy}: {result['series']:,}",
                        flush=True,
                    )
            size = sum(path.stat().st_size for path in OUTPUT.rglob("*") if path.is_file())
            if size > resources["max_output_gib"] * 1024**3:
                raise OSError("Declared output budget exceeded; preserve completed cases")
        del data
        gc.collect()
    record = {
        "status": "passed",
        "action": action,
        "cases": records,
        "elapsed_seconds": time.perf_counter() - began,
        "peak_working_set_bytes": psutil.Process().memory_info().peak_wset,
        "execution_sha256": contract["sha256"],
        "final_holdout_used": False,
    }
    path = REPORTS / (
        "phase5_smoke.json" if action == "smoke" else f"phase5_{action}_execution.json"
    )
    if path.exists():
        if read(path)["execution_sha256"] != contract["sha256"]:
            raise ValueError("Execution receipt belongs to another contract")
    else:
        write_new(path, record)
    print(json.dumps({k: v for k, v in record.items() if k != "cases"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["smoke", "base", "sensitivity"])
    args = parser.parse_args()
    with CaseLock(OUTPUT / "controller.lock"):
        run(args.action)
