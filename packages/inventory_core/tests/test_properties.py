"""S-03..S-08: conservation, cost reconciliation, determinism, lead time, no future visibility, bounds."""

import json

import numpy as np
import pytest
from conftest import synthetic_inputs

from inventory_service.planner import run_planner, scenario_from

BASE = dict(
    lead_days=7,
    review_days=1,
    buffer_days=3,
    initial_cover_days=7,
    holding_cost=1,
    shortage_cost=10,
    fixed_order_cost=1,
    variable_order_cost=0,
    terminal_cost=0,
    variability_multiplier=1,
)
DEMAND = np.random.default_rng(7).poisson(5, 28).astype(float)


def run(demand=DEMAND, **changes):
    return run_planner(synthetic_inputs(demand), scenario_from(BASE | changes))


@pytest.mark.parametrize(
    "changes",
    [{}, {"lead_days": 0}, {"lead_days": 14}, {"review_days": 7}, {"terminal_cost": 1, "variable_order_cost": 0.5}],
)
def test_conservation_and_cost_reconciliation(changes):
    for policy in run(**changes)["policies"]:
        s, days = policy["summary"], policy["daily"]
        for d in days:
            assert d["opening_stock"] + d["receipts"] - d["fulfilled"] == pytest.approx(d["closing_stock"])
            assert d["demand"] - d["fulfilled"] == pytest.approx(d["unmet"])
            assert d["inventory_position"] == pytest.approx(d["closing_stock"] + d["pipeline_after"])
        assert s["initial_on_hand"] + s["received_units"] - s["fulfilled_units"] == pytest.approx(s["final_on_hand"])
        assert s["placed_units"] - s["received_units"] == pytest.approx(s["final_pipeline"])
        assert s["holding_cost"] + s["shortage_cost"] + s["ordering_cost"] + s["terminal_cost"] == pytest.approx(
            s["total_cost"]
        )


def test_deterministic_and_shared_demand_path():
    first, second = run(), run()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    for policy in first["policies"]:
        assert [d["demand"] for d in policy["daily"]] == first["demand"]


@pytest.mark.parametrize("lead", [0, 3, 7, 14])
def test_order_on_day_t_arrives_on_day_t_plus_lead_plus_one(lead):
    for policy in run(lead_days=lead)["policies"]:
        orders = [d["order_quantity"] for d in policy["daily"]]
        receipts = [d["receipts"] for d in policy["daily"]]
        for day, quantity in enumerate(orders):
            if day + lead + 1 < 28:
                assert receipts[day + lead + 1] == pytest.approx(quantity)
        allowed = [d["review_allowed"] for d in policy["daily"]]
        assert not any(allowed[day] for day in range(28) if day + lead + 1 >= 28)


@pytest.mark.parametrize("cutoff", [3, 10, 18])
def test_future_demand_cannot_change_earlier_orders(cutoff):
    perturbed = DEMAND.copy()
    perturbed[cutoff + 1 :] = perturbed[cutoff + 1 :] * 7 + 50
    a, b = run(DEMAND), run(perturbed)
    for pa, pb in zip(a["policies"], b["policies"], strict=True):
        orders_a = [d["order_quantity"] for d in pa["daily"][: cutoff + 1]]
        orders_b = [d["order_quantity"] for d in pb["daily"][: cutoff + 1]]
        assert orders_a == orders_b, pa["policy"]


@pytest.mark.parametrize(
    "changes",
    [
        {"lead_days": -1},
        {"review_days": 0},
        {"lead_days": 20, "review_days": 9},
        {"holding_cost": -1},
        {"buffer_days": float("nan")},
        {"lead_days": 2.5},
    ],
)
def test_engine_rejects_invalid_scenarios(changes):
    with pytest.raises((ValueError, TypeError)):
        scenario_from(BASE | changes)


def test_unknown_or_duplicate_policies_rejected():
    inputs, scenario = synthetic_inputs(DEMAND), scenario_from(BASE)
    for policies in ((), ("selected_ml", "selected_ml"), ("oracle",)):
        with pytest.raises(ValueError):
            run_planner(inputs, scenario, policies)
