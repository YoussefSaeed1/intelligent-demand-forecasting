"""Reproduce pre-fix validation preparation races only on archived, mocked workers."""

import argparse
import importlib.util
import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--receipt", type=Path, required=True)
args = parser.parse_args()
if args.receipt.exists():
    raise FileExistsError("Never overwrite a reproduction receipt")
records = []
for name, relative, parameters in (
    ("old_benchmark", "experiments/benchmark.py", ("3b", "m5", 1, "naive")),
    ("old_runner", "tuning/runner.py", ("m5_synthetic", 1)),
):
    path = ROOT / "reports/post_audit/original_source/src/intelligent_demand" / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(dir=ROOT / "artifacts/test_runs") as temp:
        with pytest.MonkeyPatch.context() as patch:
            scratch = Path(temp)
            (scratch / "configs").mkdir()
            (scratch / "configs/phase3.yaml").write_text("{}")
            patch.setattr(module, "ROOT", scratch)
            patch.setattr(module, "load_splits", lambda _: {"m5": [SimpleNamespace()]})
            config = SimpleNamespace(split_manifest=scratch / "unused.json")
            if name == "old_benchmark":
                patch.setattr(module, "load_experiment_config", lambda _, value=config: value)
            else:
                patch.setattr(module, "require_phase", lambda _: None)
                patch.setattr(module, "ledger_events", lambda: [])
                patch.setattr(module, "load_plan", lambda: {})
                patch.setattr(module, "execution_contract", lambda: {})
                patch.setattr(module, "case_by_id", lambda _: {"dataset": "m5", "model": "naive"})
                patch.setattr(module, "experiment_config", lambda value=config: value)
            barrier, entered = threading.Barrier(2), []

            def stop_before_data(_, seen=entered, gate=barrier):
                seen.append(threading.get_ident())
                gate.wait(timeout=10)
                raise RuntimeError("synthetic stop before source/model access")

            patch.setattr(module, "population", stop_before_data)
            with ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(module.worker, *parameters) for _ in range(2)]
                for future in futures:
                    with pytest.raises(RuntimeError, match="synthetic stop"):
                        future.result(timeout=15)
            assert len(set(entered)) == 2
            records.append({"module": relative, "original_concurrent_preparation_entries": 2,
                            "archived_code_reproduction": True, "source_or_model_reads": 0})
with args.receipt.open("x", encoding="utf-8") as stream:
    json.dump(records, stream, indent=2)
    stream.write("\n")
print(json.dumps(records, indent=2))
