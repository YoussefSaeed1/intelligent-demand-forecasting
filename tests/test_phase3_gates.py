"""Dependent experiments require all scientific gates, not just successful execution."""

import json

import pytest

from intelligent_demand.experiments.gates import require_gate


@pytest.mark.parametrize(
    "violation",
    [
        None,
        "executed_only",
        "no_reconciliation",
        "holdout_access",
        "hash_changed",
        "missing_test_gate",
        "failed_test_gate",
    ],
)
def test_dependent_workflow_rejects_incomplete_or_unsafe_gate(tmp_path, monkeypatch, violation):
    monkeypatch.setattr("intelligent_demand.experiments.gates.ROOT", tmp_path)
    path = tmp_path / "reports/forecasting/phase3b_gate.json"
    path.parent.mkdir(parents=True)
    checks = {
        name: {"status": "passed"}
        for name in (
            "pytest",
            "ruff",
            "pip_check",
            "forecast-plan",
            "forecast-models",
            "frozen_protocol",
            "source_hashes",
        )
    }
    record = {
        "status": "passed",
        "independent_reconciliation": True,
        "source_hashes_unchanged": True,
        "final_holdout_targets_accessed": False,
        "quality_checks": checks,
    }
    if violation == "executed_only":
        record["status"] = "executed"
    elif violation == "no_reconciliation":
        record["independent_reconciliation"] = False
    elif violation == "holdout_access":
        record["final_holdout_targets_accessed"] = True
    elif violation == "hash_changed":
        record["source_hashes_unchanged"] = False
    elif violation == "missing_test_gate":
        del checks["pytest"]
    elif violation == "failed_test_gate":
        checks["pytest"]["status"] = "failed"
    path.write_text(json.dumps(record), encoding="utf-8")
    if violation is None:
        assert require_gate("3b") == record
    else:
        with pytest.raises(ValueError, match="required gates"):
            require_gate("3b")
