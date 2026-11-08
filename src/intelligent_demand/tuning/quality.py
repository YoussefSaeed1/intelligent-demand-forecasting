"""Explicit Phase 4 quality gates; no completed process is assumed scientifically valid."""

import argparse
import json
import re
import subprocess
import sys

from intelligent_demand.evaluation.splits import load_splits
from intelligent_demand.experiments.benchmark import verify_sources
from intelligent_demand.experiments.registry import atomic_json, file_digest
from intelligent_demand.tuning.authority import ledger_events
from intelligent_demand.tuning.plan import (
    BASE_REVISION,
    OUTPUT,
    REPORTS,
    ROOT,
    freeze_plan,
    load_plan,
)


def technical_checks(phase):
    log = OUTPUT / f"{phase}_pytest.log"
    raw = log.read_bytes()
    text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    match = re.search(r"(\d+) passed in ([\d.]+)s", text)
    if not match or re.search(r"\b(?:FAILED|ERROR|deselected)\b", text):
        raise ValueError("A passing current complete Pytest log is required")
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    count = re.search(r"(\d+) tests? collected", collected.stdout)
    if count is None or count.group(1) != match.group(1):
        raise ValueError("Current full suite count differs from the passing log")
    checks = {
        "pytest": {
            "count": int(match.group(1)),
            "seconds": float(match.group(2)),
            "log_sha256": file_digest(log),
        }
    }
    for name, args in (
        ("ruff", ["ruff", "check", ".", "--no-cache"]),
        ("pip_check", ["pip", "check"]),
    ):
        result = subprocess.run(
            [sys.executable, "-m", *args], cwd=ROOT, text=True, capture_output=True, check=True
        )
        checks[name] = {"status": "passed", "output": result.stdout.strip()}
    git = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT)]
    subprocess.run(
        git + ["merge-base", "--is-ancestor", BASE_REVISION, "HEAD"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        git
        + [
            "diff",
            "--exit-code",
            BASE_REVISION,
            "--",
            "docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md",
            "reports/eda/proposed_splits.json",
        ],
        capture_output=True,
        check=True,
    )
    load_splits(ROOT / "reports/eda/proposed_splits.json")
    checks["protocol"] = {"status": "passed", "horizon": 28, "folds": 4}
    checks["sources"] = {"status": "passed", "files": len(verify_sources())}
    return checks


def finalise(phase):
    if phase == "4a":
        if any("targets_read" in row["event"] for row in ledger_events()):
            raise ValueError("Cannot design tuning after protected final targets were opened")
        plan = freeze_plan()
        record = {
            "phase": phase,
            "status": "passed",
            "plan_sha256": plan["contract_sha256"],
            "planned_tuning_configurations": sum(t["kind"] == "tuning" for t in plan["trials"]),
            "planned_reference_cases": sum(t["kind"] == "reference" for t in plan["trials"]),
            "source_hashes_unchanged": True,
            "holdout_targets_accessed": False,
        }
    else:
        record = json.loads((REPORTS / f"phase{phase}_gate.json").read_text())
        plan = load_plan()
        if record.get("status") != "passed" or record["plan_sha256"] != plan["contract_sha256"]:
            raise ValueError("Independent scientific audit must pass before technical finalisation")
    record["quality_checks"] = technical_checks(phase)
    record["quality_checks_passed"] = True
    atomic_json(REPORTS / f"phase{phase}_gate.json", record)
    print(
        json.dumps(
            {k: v for k, v in record.items() if k not in ("runs", "trials", "comparison")}, indent=2
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=["4a", "4b", "4c", "4d"])
    finalise(parser.parse_args().phase)
