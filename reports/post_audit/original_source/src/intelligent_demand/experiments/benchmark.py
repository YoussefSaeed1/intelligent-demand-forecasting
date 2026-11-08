"""Sequential, budgeted Phase 3 experiment execution and restartable local job records."""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import psutil
import yaml

from intelligent_demand.evaluation.splits import load_splits
from intelligent_demand.experiments.config import identity, load_experiment_config
from intelligent_demand.experiments.engine import execute_validation, provenance
from intelligent_demand.experiments.preparation import PreparedSource
from intelligent_demand.experiments.registry import ExperimentRegistry, atomic_json, file_digest
from intelligent_demand.models.baselines import BASELINES, baseline_registry

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts/experiments/phase3"
LOGGER = logging.getLogger(__name__)


def verify_sources(root=ROOT):
    """File-byte hashes are integrity checks, never analytical access to held-out labels."""
    reference = json.loads((root / "reports/data_quality/phase1_readiness.json").read_text())
    records = {}
    for dataset, gate in reference["quality_gates"].items():
        files = {
            root / "data/processed" / dataset / "daily_sales.parquet": gate["canonical_sha256"]
        }
        files.update(
            {
                root / "data/raw" / dataset / name: digest
                for name, digest in gate["source_sha256"].items()
            }
        )
        for path, expected in files.items():
            digest = file_digest(path)
            if digest != expected:
                raise ValueError(f"Verified dataset changed: {path.name}")
            records[path.relative_to(root).as_posix()] = digest
    return records


def population(dataset):
    # Saved initial-training-only EDA supplies fixed descriptors, never future outcomes.
    frame = pd.read_parquet(ROOT / f"reports/eda/tables/{dataset}/series.parquet")
    if (
        frame.series_id.duplicated().any()
        or len(frame) != {"store_item": 500, "m5": 30490}[dataset]
    ):
        raise ValueError("Population metadata does not match the verified dataset")
    return frame.sort_values("series_id").reset_index(drop=True)


def experiment_models(phase):
    if phase == "3b":
        return BASELINES, baseline_registry()
    if phase == "3c":
        from intelligent_demand.models.statistical import STATISTICAL, statistical_registry

        return STATISTICAL, statistical_registry()
    if phase == "3d":
        from intelligent_demand.models.global_ml import ML_METHODS, ml_registry

        return ML_METHODS, ml_registry()
    raise ValueError("This milestone is not yet enabled")


def worker(phase, dataset, fold_number, method):
    if phase in ("3c", "3d"):
        from intelligent_demand.experiments.gates import require_gate

        require_gate("3b" if phase == "3c" else "3c")
    settings = yaml.safe_load((ROOT / "configs/phase3.yaml").read_text())
    config = load_experiment_config(ROOT / "configs/forecasting.yaml")
    fold = load_splits(config.split_manifest)[dataset][fold_number - 1]
    meta = population(dataset)
    if phase == "3c":
        from intelligent_demand.experiments.sampling import frozen_statistical_subset
        from intelligent_demand.models.statistical import EXPENSIVE

        if method in EXPENSIVE:
            meta = frozen_statistical_subset(
                ROOT, OUTPUT, meta, dataset, load_splits(config.split_manifest)[dataset][0].origin
            )
    series = tuple(meta.series_id)
    reference = json.loads((ROOT / "reports/data_quality/phase1_readiness.json").read_text())
    fingerprint = reference["quality_gates"][dataset]["canonical_sha256"]
    source = PreparedSource(
        ROOT / f"data/processed/{dataset}/daily_sales.parquet",
        dataset,
        meta,
        OUTPUT / "cache",
        fingerprint,
        config.batch_rows,
    )
    methods, models = experiment_models(phase)
    if method not in methods:
        raise ValueError("Method is outside this milestone")
    info = models.create(method, "1").info
    code = provenance(ROOT)
    packages = ("statsmodels", "scikit-learn", "psutil")
    from importlib.metadata import version

    code["package_versions"].update({name: version(name) for name in packages})
    parameters = {
        "phase": phase,
        "initial_configuration": 1,
        "resource_budget": {
            "threads": settings["threads"],
            "rss_limit_mb": settings["worker_rss_limit_mb"],
        },
    }
    model_path = ROOT / "src/intelligent_demand/models/baselines.py"
    if phase == "3c":
        model_path = ROOT / "src/intelligent_demand/models/statistical.py"
        parameters["parameters"] = yaml.safe_load((ROOT / "configs/statistical.yaml").read_text())
    if phase == "3d":
        model_path = ROOT / "src/intelligent_demand/models/global_ml.py"
        parameters["parameters"] = yaml.safe_load((ROOT / "configs/ml.yaml").read_text())
        parameters["maximum_training_rows"] = settings[f"training_rows_{dataset}"]
        parameters["feature_cache"] = str(OUTPUT / "feature_cache")
        parameters["source_fingerprint"] = fingerprint
        code["package_versions"]["lightgbm"] = version("lightgbm")
    signature = {
        "dataset": dataset,
        "fold": fold.number,
        "model": method,
        "configuration": parameters,
        "source": fingerprint,
        "model_code": file_digest(model_path),
        "evaluation_code": {
            k: v
            for k, v in code["code_sha256"].items()
            if k
            in {
                "evaluation/__init__.py",
                "evaluation/design.py",
                "evaluation/metrics.py",
                "evaluation/predictions.py",
                "evaluation/scoring.py",
                "evaluation/splits.py",
            }
        },
        "protocol": file_digest(config.split_manifest),
    }
    if phase == "3c":
        signature["population"] = identity(sorted(series))
        signature["adapter_base"] = file_digest(ROOT / "src/intelligent_demand/models/baselines.py")
    if phase == "3d":
        signature["population"] = identity(sorted(series))
        signature["feature_code"] = file_digest(
            ROOT / "src/intelligent_demand/features/recursive.py"
        )
    job_id = identity(signature)
    job_path = OUTPUT / "jobs" / f"{job_id}.json"
    job_path.parent.mkdir(parents=True, exist_ok=True)
    registry = ExperimentRegistry(config.registry_directory)
    if job_path.exists():
        job = json.loads(job_path.read_text())
        run_id = job["run_id"]
        state = registry.read(run_id)
        if state["status"] == "completed":
            registry.completed(run_id)
            if file_digest(source.path) != fingerprint:
                raise ValueError("Current source differs from completed result")
            spec = state["specification"]
            if (
                spec["series_sha256"] != identity(sorted(series))
                or spec["classes_sha256"]
                != identity(dict(zip(meta.series_id, meta.pattern, strict=True)))
                or spec["settings"] != config.metadata()
                or spec["model_configuration"] != parameters
            ):
                raise ValueError(
                    "Current population, classes or settings differ from completed result"
                )
            LOGGER.info("Reusing verified completed %s %s fold %s", dataset, method, fold_number)
            print(json.dumps({"run_id": run_id, "job_id": job_id, "reused": True}), flush=True)
            return
    else:
        from intelligent_demand.experiments.engine import experiment_specification

        classes = dict(zip(meta.series_id, meta.pattern, strict=True))
        spec = experiment_specification(
            config,
            fold,
            info,
            parameters,
            series,
            fingerprint,
            code,
            classes,
            load_splits(config.split_manifest)[dataset][0].origin,
        )
        run_id = registry.create(spec)
        atomic_json(job_path, {"signature": signature, "run_id": run_id, "phase": phase})
    # Preserve the original provenance on restart; same method/evaluation signature is mandatory.
    saved_spec = registry.read(run_id)["specification"]
    code = saved_spec["code"]
    started = time.perf_counter()
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
        classes=dict(zip(meta.series_id, meta.pattern, strict=True)),
        class_as_of=load_splits(config.split_manifest)[dataset][0].origin,
    )
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "job_id": job_id,
                "elapsed_seconds": time.perf_counter() - started,
                "reused": False,
                "os_peak_working_set_bytes": getattr(
                    psutil.Process().memory_info(), "peak_wset", None
                ),
            }
        ),
        flush=True,
    )


def supervise(phase, datasets, limit_models=None, folds=(1, 2, 3, 4)):
    if phase == "3d":
        from intelligent_demand.experiments.gates import require_gate

        require_gate("3c")
    if phase == "3c":
        from intelligent_demand.experiments.gates import require_gate
        from intelligent_demand.experiments.sampling import frozen_statistical_subset

        require_gate("3b")
        configuration = load_experiment_config(ROOT / "configs/forecasting.yaml")
        for dataset in datasets:
            selected = frozen_statistical_subset(
                ROOT,
                OUTPUT,
                population(dataset),
                dataset,
                load_splits(configuration.split_manifest)[dataset][0].origin,
            )
            print(f"FROZEN {dataset} statistical subset: {len(selected)} series", flush=True)
    settings = yaml.safe_load((ROOT / "configs/phase3.yaml").read_text())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    before = verify_sources()
    atomic_json(OUTPUT / f"{phase}_source_hashes_before.json", before)
    methods, _ = experiment_models(phase)
    methods = list(methods) if limit_models is None else limit_models
    environment = {
        **os.environ,
        "OMP_NUM_THREADS": str(settings["threads"]),
        "OPENBLAS_NUM_THREADS": str(settings["threads"]),
        "MKL_NUM_THREADS": str(settings["threads"]),
        "PYTHONUNBUFFERED": "1",
    }
    records = []
    for dataset in datasets:
        for fold in folds:
            for method in methods:
                if psutil.virtual_memory().available < settings["minimum_available_mb"] * 2**20:
                    raise MemoryError("Insufficient free memory to safely start the next worker")
                tag = f"{phase}_{dataset}_f{fold}_{method}"
                log = OUTPUT / f"{tag}.log"
                print(f"START {tag}", flush=True)
                started, peak = time.monotonic(), 0
                with log.open("a", encoding="utf-8") as stream:
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "intelligent_demand.experiments.benchmark",
                            "worker",
                            "--phase",
                            phase,
                            "--dataset",
                            dataset,
                            "--fold",
                            str(fold),
                            "--model",
                            method,
                        ],
                        cwd=ROOT,
                        env=environment,
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                    )
                    reason = None
                    while process.poll() is None:
                        try:
                            task = psutil.Process(process.pid)
                            rss = task.memory_info().rss
                            rss += sum(
                                child.memory_info().rss for child in task.children(recursive=True)
                            )
                            peak = max(peak, rss)
                            if rss > settings["worker_rss_limit_mb"] * 2**20:
                                reason = "memory_budget_exceeded"
                            timeout_key = {
                                "3b": "baseline_timeout_seconds",
                                "3c": "statistical_timeout_seconds",
                                "3d": "ml_timeout_seconds",
                            }[phase]
                            if time.monotonic() - started > settings[timeout_key]:
                                reason = "runtime_budget_exceeded"
                            if reason:
                                for child in task.children(recursive=True):
                                    child.terminate()
                                process.terminate()
                                process.wait(timeout=30)
                                break
                        except psutil.NoSuchProcess:
                            pass
                        time.sleep(0.5)
                status = "completed" if process.returncode == 0 and reason is None else "incomplete"
                if status == "incomplete":
                    # Recover only our own process after observing its exit.
                    registry = ExperimentRegistry(
                        load_experiment_config(ROOT / "configs/forecasting.yaml").registry_directory
                    )
                    for status_file in registry.root.glob("*/status.json"):
                        saved = json.loads(status_file.read_text())
                        if (
                            saved.get("status") == "running"
                            and saved.get("owner_pid") == process.pid
                        ):
                            registry.recover_interrupted(
                                saved["run_id"],
                                expected_owner_token=saved["owner_token"],
                                owner_confirmed_stopped=True,
                            )
                record = {
                    "tag": tag,
                    "status": status,
                    "exit_code": process.returncode,
                    "elapsed_seconds": time.monotonic() - started,
                    "peak_worker_rss_bytes": peak,
                    "reason": reason,
                    "log": log.relative_to(ROOT).as_posix(),
                }
                if status == "completed":
                    lines = log.read_text(encoding="utf-8").splitlines()
                    record.update(
                        json.loads(
                            next(line for line in reversed(lines) if line.startswith('{"run_id"'))
                        )
                    )
                    if record.get("os_peak_working_set_bytes"):
                        record["peak_worker_rss_bytes"] = max(
                            record["peak_worker_rss_bytes"], record["os_peak_working_set_bytes"]
                        )
                resource_path = OUTPUT / f"{tag}_resource.json"
                if record.get("reused") and resource_path.exists():
                    original = json.loads(resource_path.read_text())
                    if (
                        original.get("status") == "completed"
                        and original.get("run_id") == record["run_id"]
                    ):
                        original["reused_on_last_invocation"] = True
                        record = original
                atomic_json(resource_path, record)
                records.append(record)
                print(
                    f"{status.upper()} {tag}: {record['elapsed_seconds']:.1f}s, "
                    f"peak {record['peak_worker_rss_bytes'] / 2**20:.1f} MiB",
                    flush=True,
                )
                if status != "completed":
                    raise RuntimeError(f"Milestone stopped at {tag}; inspect its preserved log")
    if verify_sources() != before:
        raise ValueError("Source hashes changed during milestone")
    atomic_json(
        OUTPUT / f"{phase}_execution.json",
        {"phase": phase, "status": "executed", "source_hashes_unchanged": True, "runs": records},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "worker", "verify-sources"])
    parser.add_argument("--phase", default="3b")
    parser.add_argument("--dataset", choices=["all", "store_item", "m5"], default="all")
    parser.add_argument("--fold", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--model")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.action == "verify-sources":
        print(json.dumps(verify_sources(), indent=2))
    elif args.action == "worker":
        if args.dataset == "all" or args.fold is None or args.model is None:
            parser.error("Worker requires one dataset/fold/model")
        worker(args.phase, args.dataset, args.fold, args.model)
    else:
        supervise(
            args.phase,
            ["store_item", "m5"] if args.dataset == "all" else [args.dataset],
            [args.model] if args.model else None,
            [args.fold] if args.fold else [1, 2, 3, 4],
        )


if __name__ == "__main__":
    main()
