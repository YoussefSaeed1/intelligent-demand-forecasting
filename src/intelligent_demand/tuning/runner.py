"""Sequential, budgeted four-origin random search with immutable case membership."""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import replace

import numpy as np
import psutil

from intelligent_demand.evaluation.splits import load_splits
from intelligent_demand.experiments.benchmark import OUTPUT as PHASE3_OUTPUT
from intelligent_demand.experiments.benchmark import population, verify_sources
from intelligent_demand.experiments.config import identity, load_experiment_config
from intelligent_demand.experiments.engine import (
    execute_validation,
    experiment_specification,
    provenance,
)
from intelligent_demand.experiments.ownership import CaseLock
from intelligent_demand.experiments.preparation import PreparedSource
from intelligent_demand.experiments.registry import (
    ExperimentRegistry,
    atomic_json,
    file_digest,
    utc_now,
)
from intelligent_demand.models.baselines import BASELINES, baseline_registry
from intelligent_demand.models.global_ml import ML_METHODS, ml_registry
from intelligent_demand.models.statistical import statistical_registry
from intelligent_demand.tuning.authority import ledger_events
from intelligent_demand.tuning.plan import OUTPUT, ROOT, load_plan, publish_once, require_phase

LOGGER = logging.getLogger(__name__)


def confirmed_stopped(pid):
    """Check an observed owned PID; elapsed time alone never authorises lock recovery."""
    try:
        psutil.Process(pid).wait(timeout=0)
        return True
    except psutil.NoSuchProcess:
        return True
    except psutil.TimeoutExpired:
        return False


def experiment_config():
    return replace(
        load_experiment_config(ROOT / "configs/forecasting.yaml"),
        registry_directory=OUTPUT / "registry",
    )


def scientific_files():
    # Reporting/final-assessment modules can be authored without altering validation fits.
    names = [
        "tuning/runner.py",
        "tuning/plan.py",
        "tuning/authority.py",
        "features/recursive.py",
        "models/global_ml.py",
        "models/statistical.py",
        "models/baselines.py",
        "models/base.py",
        "experiments/engine.py",
        "experiments/config.py",
        "experiments/data.py",
        "experiments/preparation.py",
        "experiments/registry.py",
        "evaluation/design.py",
        "evaluation/metrics.py",
        "evaluation/predictions.py",
        "evaluation/scoring.py",
        "evaluation/splits.py",
    ]
    return {
        f"src/intelligent_demand/{name}": file_digest(ROOT / "src/intelligent_demand" / name)
        for name in names
    }


def execution_contract():
    plan = load_plan()
    current = {"plan_sha256": plan["contract_sha256"], "scientific_code_sha256": scientific_files()}
    current["execution_sha256"] = identity(current)
    path = OUTPUT / "execution_contract.json"
    if path.exists():
        if json.loads(path.read_text()) != current:
            raise ValueError(
                "Validation execution code changed after search began; "
                "review provenance before resuming"
            )
    else:
        publish_once(path, current)
    return current


class Phase4Source(PreparedSource):
    """Reuse verified Phase 3 origin panels without copying or modifying them."""

    def _prepare(self, fold, population_ids):
        contract = {
            "version": 1,
            "source": self.fingerprint,
            "origin": str(fold.origin),
            "start": str(fold.train_start),
            "dataset": self.dataset_id,
            "population": identity(population_ids),
        }
        legacy = PHASE3_OUTPUT / "cache" / identity(contract) / "complete.json"
        if legacy.exists():
            reader = PreparedSource(
                self.path,
                self.dataset_id,
                self.metadata,
                PHASE3_OUTPUT / "cache",
                self.fingerprint,
                self.batch_rows,
            )
            return reader._prepare(fold, population_ids)
        return super()._prepare(fold, population_ids)


def registry_for(method):
    return (
        baseline_registry()
        if method in BASELINES
        else ml_registry()
        if method in ML_METHODS
        else statistical_registry()
    )


def case_by_id(case_id):
    plan = load_plan()
    matches = [r for r in plan["trials"] if r["trial_id"] == case_id]
    if len(matches) != 1:
        raise ValueError("Unknown case outside the immutable search allocation")
    return matches[0]


def job_path(case_id, fold):
    return OUTPUT / "jobs" / f"{case_id}_f{fold}.json"


def worker(case_id, number):
    if ledger_events():
        raise ValueError("Optimisation is prohibited after final assessment access began")
    if (not isinstance(case_id, str) or not re.fullmatch(r"[a-z0-9_]{1,128}", case_id)
            or type(number) is not int or not 1 <= number <= 4):
        raise ValueError("Invalid optimisation worker case")
    with CaseLock(OUTPUT / "worker_locks" / f"{case_id}_f{number}.json"):
        return _worker_owned(case_id, number)


def _worker_owned(case_id, number):
    require_phase("4a")
    if ledger_events():
        raise ValueError("Optimisation is prohibited after final assessment access began")
    plan = load_plan()
    execution = execution_contract()
    case = case_by_id(case_id)
    config = experiment_config()
    dataset, method = case["dataset"], case["model"]
    fold = load_splits(config.split_manifest)[dataset][number - 1]
    metadata = population(dataset)
    series = tuple(metadata.series_id)
    fingerprint = plan["source_sha256"][f"data/processed/{dataset}/daily_sales.parquet"]
    source = Phase4Source(
        ROOT / f"data/processed/{dataset}/daily_sales.parquet",
        dataset,
        metadata,
        OUTPUT / "cache",
        fingerprint,
        config.batch_rows,
    )
    models = registry_for(method)
    info = models.create(method, "1").info
    parameters = {
        "phase": "4b",
        "trial_id": case_id,
        "plan_sha256": plan["contract_sha256"],
        "parameters": case["parameters"],
        "source_fingerprint": fingerprint,
        "maximum_training_rows": plan["settings"]["training_rows"][dataset],
        "feature_cache": str(OUTPUT / "feature_cache"),
        "availability": "price_free",
        "execution_sha256": execution["execution_sha256"],
    }
    registry = ExperimentRegistry(config.registry_directory)
    job = job_path(case_id, number)
    signature = identity({"case": case, "fold": number, "execution": execution})
    if job.exists():
        pointer = json.loads(job.read_text())
        if pointer["signature"] != signature:
            raise ValueError("Job signature changed")
        state = registry.read(pointer["run_id"])
        code = state["specification"]["code"]
        run_id = state["run_id"]
    else:
        from importlib.metadata import version

        code = provenance(ROOT)
        code["package_versions"].update(
            {n: version(n) for n in ("lightgbm", "scikit-learn", "statsmodels", "psutil")}
        )
        spec = experiment_specification(
            config,
            fold,
            info,
            parameters,
            series,
            fingerprint,
            code,
            dict(zip(metadata.series_id, metadata.pattern, strict=True)),
            load_splits(config.split_manifest)[dataset][0].origin,
        )
        run_id = registry.create(spec)
        publish_once(
            job, {"run_id": run_id, "signature": signature, "case_id": case_id, "fold": number}
        )
        state = registry.read(run_id)
    reused = state["status"] == "completed"
    result = execute_validation(
        config=config,
        fold=fold,
        source=source,
        series=series,
        models=models,
        model_info=info,
        model_config=parameters,
        registry=registry,
        source_fingerprint=fingerprint,
        code_metadata=code,
        run_id=run_id,
        resume=True,
        classes=dict(zip(metadata.series_id, metadata.pattern, strict=True)),
        class_as_of=load_splits(config.split_manifest)[dataset][0].origin,
    )
    peak = getattr(psutil.Process().memory_info(), "peak_wset", None)
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "case_id": case_id,
                "fold": number,
                "reused": reused,
                "os_peak_working_set_bytes": peak,
            }
        ),
        flush=True,
    )


def refresh_case(case):
    registry = ExperimentRegistry(experiment_config().registry_directory)
    states = []
    for number in (1, 2, 3, 4):
        path = job_path(case["trial_id"], number)
        if path.exists():
            states.append(registry.read(json.loads(path.read_text())["run_id"]))
    status = "pending"
    if any(s["status"] == "running" for s in states):
        status = "running"
    elif any(s["status"] == "failed" for s in states):
        status = "failed"
    elif any(s["status"] == "interrupted" for s in states):
        status = "interrupted"
    elif len(states) == 4 and all(s["status"] == "completed" for s in states):
        status = "completed"
    record = {
        **case,
        "status": status,
        "runs": [s["run_id"] for s in states],
        "updated_at": utc_now(),
    }
    if status == "completed":
        scores = []
        for state in states:
            state = registry.completed(state["run_id"])
            path = registry.directory(state["run_id"]) / state["outputs"]["metrics"]["path"]
            score = json.loads(path.read_text())["all"]["macro"]["mae"]
            if not np.isfinite(score):
                raise ValueError("Undefined primary score")
            scores.append(score)
        record["primary_score"] = float(np.mean(scores))
        record["fold_mae"] = scores
    target = OUTPUT / "trials" / f"{case['trial_id']}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(target, record)
    return record


def search(smoke=False, retry=False):
    require_phase("4a")
    if ledger_events():
        raise ValueError("Search cannot run after final assessment access")
    plan = load_plan()
    execution_contract()
    resources = plan["settings"]["resources"]
    if shutil.disk_usage(ROOT).free < resources["minimum_free_disk_gib"] * 2**30:
        raise OSError("Insufficient free disk for search")
    lock = OUTPUT / "search.lock"
    with lock.open("x") as stream:
        stream.write(json.dumps({"pid": os.getpid(), "started": utc_now()}))
    active = None
    owned_pids = set()
    try:
        for entry in plan["trials"]:
            refresh_case(entry)
        cases = plan["trials"]
        if smoke:
            cases = [c for c in cases if c["kind"] == "tuning" and c["trial_id"].endswith("_00")]
        environment = {
            **os.environ,
            "OMP_NUM_THREADS": "4",
            "MKL_NUM_THREADS": "4",
            "OPENBLAS_NUM_THREADS": "4",
            "PYTHONUNBUFFERED": "1",
        }
        registry = ExperimentRegistry(experiment_config().registry_directory)
        for case in cases:
            for number in [1] if smoke else [1, 2, 3, 4]:
                case_id = case["trial_id"]
                job = job_path(case_id, number)
                resource_file = OUTPUT / "resources" / f"{case_id}_f{number}.json"
                resource_file.parent.mkdir(parents=True, exist_ok=True)
                if job.exists():
                    current = registry.read(json.loads(job.read_text())["run_id"])
                    if current["status"] == "completed":
                        registry.completed(current["run_id"])
                        print(f"REUSED {case_id} fold {number}", flush=True)
                        continue
                    if not retry:
                        raise RuntimeError("Incomplete prior job; diagnose before explicit retry")
                    if len(current["attempts"]) >= resources["maximum_attempts_per_fold"]:
                        raise RuntimeError("Declared retry budget exhausted")
                elapsed = sum(
                    json.loads(p.read_text())["elapsed_seconds"]
                    for p in (OUTPUT / "resources").glob("*.json")
                )
                if elapsed >= resources["search_wall_seconds"]:
                    raise TimeoutError("Predeclared active search budget exhausted")
                if psutil.virtual_memory().available < resources["minimum_available_mib"] * 2**20:
                    raise MemoryError("Insufficient available memory to start the next worker")
                print(f"START {case_id} fold {number}", flush=True)
                log = OUTPUT / f"{case_id}_f{number}.log"
                started, peak, last_report = time.monotonic(), 0, 0
                with log.open("a", encoding="utf-8") as stream:
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "intelligent_demand.tuning.runner",
                            "worker",
                            "--case",
                            case_id,
                            "--fold",
                            str(number),
                        ],
                        cwd=ROOT,
                        env=environment,
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                    )
                    active = process
                    owned_pids = {process.pid}
                    reason = None
                    while process.poll() is None:
                        try:
                            task = psutil.Process(process.pid)
                            children = task.children(recursive=True)
                            owned_pids.update(child.pid for child in children)
                            rss = task.memory_info().rss + sum(
                                c.memory_info().rss for c in children
                            )
                            peak = max(peak, rss)
                            cost = time.monotonic() - started
                            if rss > resources["worker_rss_mib"] * 2**20:
                                reason = "memory_budget_exceeded"
                            if (
                                cost > resources["worker_timeout_seconds"]
                                or elapsed + cost > resources["search_wall_seconds"]
                            ):
                                reason = "runtime_budget_exceeded"
                            if cost - last_report >= 15:
                                print(
                                    f"RUNNING {case_id} f{number}: "
                                    f"{cost:.0f}s / {rss / 2**20:.0f} MiB",
                                    flush=True,
                                )
                                last_report = cost
                            if reason:
                                for child in task.children(recursive=True):
                                    child.terminate()
                                process.terminate()
                                process.wait(timeout=30)
                                break
                        except psutil.NoSuchProcess:
                            pass
                        time.sleep(0.5)
                record = {
                    "case_id": case_id,
                    "fold": number,
                    "elapsed_seconds": time.monotonic() - started,
                    "peak_worker_rss_bytes": peak,
                    "exit_code": process.returncode,
                    "reason": reason,
                    "status": "completed"
                    if process.returncode == 0 and reason is None
                    else "incomplete",
                }
                if record["status"] == "completed":
                    result = json.loads(
                        next(
                            line
                            for line in reversed(log.read_text().splitlines())
                            if line.startswith('{"run_id"')
                        )
                    )
                    record.update(result)
                    record["peak_worker_rss_bytes"] = max(
                        peak, result.get("os_peak_working_set_bytes") or 0
                    )
                else:
                    for status_file in registry.root.glob("*/status.json"):
                        s = json.loads(status_file.read_text())
                        if (
                            s.get("status") == "running"
                            and s.get("owner_pid") in owned_pids
                            and confirmed_stopped(s["owner_pid"])
                        ):
                            registry.recover_interrupted(
                                s["run_id"],
                                expected_owner_token=s["owner_token"],
                                owner_confirmed_stopped=True,
                            )
                if resource_file.exists():
                    previous = json.loads(resource_file.read_text())
                    record["elapsed_seconds"] += previous["elapsed_seconds"]
                    record["prior_attempts"] = previous.get("prior_attempts", []) + [previous]
                atomic_json(resource_file, record)
                active = None
                refresh_case(case)
                print(
                    f"{record['status'].upper()} {case_id} f{number}: "
                    f"{record['elapsed_seconds']:.1f}s, "
                    f"peak {record['peak_worker_rss_bytes'] / 2**20:.1f} MiB",
                    flush=True,
                )
                if record["status"] != "completed":
                    raise RuntimeError("Stopped affected workflow; inspect preserved job log")
            refresh_case(case)
        if not smoke:
            records = [refresh_case(case) for case in plan["trials"]]
            atomic_json(
                OUTPUT / "search_execution.json",
                {
                    "plan_sha256": plan["contract_sha256"],
                    "status": "executed",
                    "trials": records,
                    "sources": verify_sources(),
                },
            )
    except BaseException:
        if active is not None:
            if active.poll() is None:
                try:
                    task = psutil.Process(active.pid)
                    for child in task.children(recursive=True):
                        child.terminate()
                    active.terminate()
                    active.wait(timeout=30)
                except psutil.NoSuchProcess:
                    active.wait(timeout=30)
            for status_file in registry.root.glob("*/status.json"):
                saved = json.loads(status_file.read_text())
                if (
                    saved.get("status") == "running"
                    and saved.get("owner_pid") in owned_pids
                    and confirmed_stopped(saved["owner_pid"])
                ):
                    registry.recover_interrupted(
                        saved["run_id"],
                        expected_owner_token=saved["owner_token"],
                        owner_confirmed_stopped=True,
                    )
            interrupted = {
                "case_id": case_id,
                "fold": number,
                "status": "interrupted",
                "elapsed_seconds": time.monotonic() - started,
                "peak_worker_rss_bytes": peak,
                "exit_code": active.returncode,
                "reason": "supervisor_interrupted",
            }
            if resource_file.exists():
                interrupted["elapsed_seconds"] += json.loads(resource_file.read_text())[
                    "elapsed_seconds"
                ]
            atomic_json(resource_file, interrupted)
            refresh_case(case)
        raise
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["search", "worker"])
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--case")
    parser.add_argument("--fold", type=int, choices=[1, 2, 3, 4])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.action == "worker":
        if args.case is None or args.fold is None:
            parser.error("Worker requires case/fold")
        worker(args.case, args.fold)
    else:
        search(args.smoke, args.retry)
