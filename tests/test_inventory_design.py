from dataclasses import replace
from pathlib import Path

import pytest

from intelligent_demand.inventory.design import Scenario, load_design


def test_declared_matrix_and_protection_period():
    _, scenarios = load_design(Path("configs/inventory.yaml"))
    assert len(scenarios) == 17
    assert max(s.protection_days for s in scenarios) <= 28
    assert len({s.identifier for s in scenarios}) == 17


@pytest.mark.parametrize("change", [
    {"lead_days": -1}, {"review_days": 0}, {"lead_days": 28}, {"lead_days": True},
    {"holding_cost": -1}, {"shortage_cost": float("nan")}, {"buffer_days": float("inf")},
    {"fulfilment": "backorders"}, {"identifier": "../escape"}, {"initial_cover_days": True},
])
def test_rejects_unsupported_or_ambiguous_assumptions(change):
    with pytest.raises(ValueError):
        replace(Scenario(), **change)


def test_zero_lead_means_next_day_not_same_day_availability():
    assert Scenario(lead_days=0, review_days=1).protection_days == 1
