"""Guards for the post-audit documentation overlay and the descriptive reconciliation helper."""

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from intelligent_demand.preservation import phase5_post_audit as phase5

ROOT = Path(__file__).resolve().parents[1]


def overlay(tmp_path, logical, original_copy):
    path = tmp_path / "overlay.json"
    path.write_text(
        json.dumps({"files": {logical: {"current_sha256": "0" * 64, "original_copy": original_copy,
                                         "original_sha256": "0" * 64}}}),
        encoding="utf-8",
    )
    return path


def test_overlay_allow_list_excludes_scientific_and_simulation_files():
    forbidden = ("src/", "configs/", "artifacts/", "tests/")
    assert not any(name.startswith(forbidden) for name in phase5.OVERLAY_ALLOWED)
    assert "configs/inventory.yaml" not in phase5.OVERLAY_ALLOWED
    assert all(
        name.endswith((".md", ".html")) or name == ".gitattributes"
        for name in phase5.OVERLAY_ALLOWED
    )


@pytest.mark.parametrize(
    "logical", ["src/intelligent_demand/inventory/engine.py", "configs/inventory.yaml"]
)
def test_verifier_rejects_overlay_for_code_or_configuration(tmp_path, logical):
    archive = phase5.ARCHIVE_PREFIXES[1] + logical
    with pytest.raises(ValueError, match="Unexpected source overlay"):
        phase5.verify(tmp_path, overlay(tmp_path, logical, archive))


def test_verifier_requires_declared_archive_directory(tmp_path):
    with pytest.raises(ValueError, match="declared archive directory"):
        phase5.verify(tmp_path, overlay(tmp_path, "README.md", "README.md"))


def test_reconcile_helper_pools_units_and_weights_series():
    spec = importlib.util.spec_from_file_location(
        "post_audit_reconcile", ROOT / "reports/inventory/post_audit_reconcile.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    frame = pd.DataFrame(
        {
            "dataset": ["a", "a"], "policy": ["p", "p"], "series": [1, 3],
            "total_cost": [10.0, 90.0], "demand_units": [5.0, 15.0],
            "fulfilled_units": [5.0, 10.0], "average_on_hand_sum": [2.0, 6.0],
            "stockout_days": [0, 4], "forecast_mae_mean": [1.0, 3.0],
        }
    )
    result = module.pooled(frame, ["dataset", "policy"]).loc[("a", "p")]
    assert result.mean_cost == pytest.approx(25.0)  # series weighted, not mean of means (50)
    assert result.pooled_fill == pytest.approx(0.75)  # units pooled, not mean of rates
    assert result.cost_per_demand_unit == pytest.approx(5.0)
