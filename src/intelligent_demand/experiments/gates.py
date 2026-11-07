"""Explicit scientific milestone gates; a completed process alone is insufficient."""

import argparse
import json
import re
import subprocess
import sys

from intelligent_demand.experiments.benchmark import OUTPUT, ROOT, verify_sources
from intelligent_demand.experiments.registry import atomic_json, file_digest


def require_gate(phase):
    path = ROOT / f"reports/forecasting/phase{phase}_gate.json"
    record = json.loads(path.read_text())
    if (
        record.get("status") != "passed"
        or not record.get("independent_reconciliation")
        or not record.get("source_hashes_unchanged")
        or record.get("final_holdout_targets_accessed") is not False
        or not {
            "pytest",
            "ruff",
            "pip_check",
            "forecast-plan",
            "forecast-models",
            "frozen_protocol",
            "source_hashes",
        }.issubset(record.get("quality_checks", {}))
        or any(check["status"] != "passed" for check in record["quality_checks"].values())
    ):
        raise ValueError(f"Phase {phase} has not passed all required gates")
    return record


def finalise(phase):
    path = ROOT / f"reports/forecasting/phase{phase}_gate.json"
    record = json.loads(path.read_text())
    if record.get("status") != "passed" or not record.get("independent_reconciliation"):
        raise ValueError("Independent persisted-file audit must pass first")
    test_log = OUTPUT / f"{phase}_pytest.log"
    text = test_log.read_text(encoding="utf-8-sig")
    match = re.search(r"(\d+) passed(?:, [\d ]+deselected)? in ([\d.]+)s", text)
    if not match or re.search(r"\b(?:FAILED|ERROR|failed,|errors? in|deselected)\b", text):
        raise ValueError("A passing complete test-suite log is required")
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    count = re.search(r"(\d+) tests? collected", collected.stdout)
    if count is None or int(count.group(1)) != int(match.group(1)):
        raise ValueError("Test log does not cover the current complete test suite")
    checks = {
        "pytest": {
            "status": "passed",
            "count": int(match.group(1)),
            "seconds": float(match.group(2)),
            "log_sha256": file_digest(test_log),
        }
    }
    for name, arguments in (
        ("ruff", ["ruff", "check", ".", "--no-cache"]),
        ("pip_check", ["pip", "check"]),
    ):
        result = subprocess.run(
            [sys.executable, "-m", *arguments], cwd=ROOT, text=True, capture_output=True, check=True
        )
        checks[name] = {"status": "passed", "output": result.stdout.strip()}
    for command in ("forecast-plan", "forecast-models"):
        result = subprocess.run(
            [sys.executable, "-m", "intelligent_demand", command],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        output = json.loads(result.stdout)
        if output["models_executed"] != 0:
            raise ValueError("Read-only CLI unexpectedly executed a model")
        checks[command] = {"status": "passed", "models_executed": 0}
    git = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT)]
    subprocess.run(
        git
        + [
            "diff",
            "--exit-code",
            "23c1ddeaca0cf6cced2bdf161904f8fb114d4646",
            "--",
            "docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md",
            "reports/eda/proposed_splits.json",
        ],
        capture_output=True,
        check=True,
    )
    checks["frozen_protocol"] = {"status": "passed"}
    checks["source_hashes"] = {"status": "passed", "files": len(verify_sources())}
    record["quality_checks"] = checks
    atomic_json(path, record)
    require_gate(phase)
    print(json.dumps({"phase": phase, "status": "passed", "quality_checks": checks}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=["3b", "3c", "3d", "3e"])
    finalise(parser.parse_args().phase)
