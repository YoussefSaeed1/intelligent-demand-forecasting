from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from intelligent_demand.inventory.design import Scenario
from intelligent_demand.inventory.engine import ForecastWindow, order_quantity, simulate


def window(values):
    array = np.atleast_2d(np.asarray(values, dtype=float))
    return ForecastWindow(
        pd.Timestamp("2020-01-01").date(),
        tuple(pd.date_range("2020-01-02", periods=array.shape[1]).date),
        array,
    )


def test_hand_calculated_zero_lead_next_day_and_total_cost():
    scenario = Scenario(horizon=3, lead_days=0, buffer_days=0, initial_cover_days=0)
    result, events = simulate([[2, 2, 2]], [2], window([2, 2, 2]), scenario, "selected_ml")
    assert events.receipts.tolist() == [0, 2, 2]
    assert events.order_quantity.tolist() == [2, 2, 0]
    assert result.fulfilled_units.iloc[0] == 4 and result.unmet_units.iloc[0] == 2
    assert result.total_cost.iloc[0] == 22
    assert result.fill_rate.iloc[0] == pytest.approx(2 / 3)


def test_one_full_intervening_day_and_common_cutoff():
    scenario = Scenario(horizon=5, lead_days=1, buffer_days=0, initial_cover_days=0)
    result, events = simulate([[1] * 5], [1], window([1] * 5), scenario, "selected_ml")
    assert events.receipts.tolist() == [0, 0, 2, 0, 1]
    assert events.order_quantity.tolist() == [2, 0, 1, 0, 0]
    assert result.total_cost.iloc[0] == 23
    assert events.review_allowed.tolist() == [True, True, True, False, False]


def test_zero_demand_and_undefined_denominators():
    result, _ = simulate(
        [[0] * 7], [0], window([0] * 7), Scenario(horizon=7, lead_days=1), "fixed_reorder_point"
    )
    assert result.total_cost.iloc[0] == 0 and result.orders.iloc[0] == 0
    for name in ("fill_rate", "window_turnover", "average_order_quantity"):
        assert np.isnan(result[name].iloc[0])


def test_fixed_reorder_and_order_up_to_are_different_controls():
    scenario = Scenario(horizon=7, lead_days=2, buffer_days=1)
    mean = np.array([2.0, 2.0])
    ip = np.array([8.0, 9.0])
    assert order_quantity("fixed_reorder_point", ip, mean, None, None, scenario).tolist() == [2, 0]
    forecast = window([[5] * 7, [5] * 7])
    assert order_quantity(
        "selected_ml", ip, mean, forecast, forecast.dates[0], scenario
    ).tolist() == [9, 8]


@pytest.mark.parametrize("kind", ["constant", "seasonal", "intermittent", "spike", "random"])
def test_independent_event_stock_flow_properties(kind):
    rng = np.random.default_rng(42)
    y = rng.integers(0, 9, (4, 28)).astype(float)
    if kind == "constant":
        y[:] = 3
    elif kind == "seasonal":
        y[:] = np.resize([1, 1, 1, 1, 1, 8, 8], 28)
    elif kind == "intermittent":
        y[:, np.arange(28) % 5 != 0] = 0
    elif kind == "spike":
        y[:] = 0
        y[:, 14] = 80
    scenario = Scenario(lead_days=3, initial_cover_days=7)
    result, events = simulate(
        y, np.full(4, 3.0), window(np.full((4, 28), 3)), scenario, "selected_ml"
    )
    for index, group in events.groupby("series_row", sort=True):
        np.testing.assert_allclose(
            group.opening_stock + group.receipts - group.fulfilled, group.closing_stock
        )
        np.testing.assert_allclose(group.demand, group.fulfilled + group.unmet)
        np.testing.assert_allclose(
            group.pipeline_opening - group.receipts + group.order_quantity, group.pipeline_after
        )
        assert result.total_cost.iloc[index] == pytest.approx(
            group.holding_cost.sum() + group.shortage_cost.sum() + group.ordering_cost.sum()
        )


def test_known_initial_receipts_and_terminal_pipeline_not_lost():
    scenario = Scenario(horizon=3, lead_days=0, initial_cover_days=0, terminal_cost=2)
    result, events = simulate(
        [[2, 2, 2]],
        [0],
        window([0, 0, 0]),
        scenario,
        "fixed_reorder_point",
        initial_due={0: [3], 10: [4]},
    )
    assert events.receipts.tolist() == [3, 0, 0]
    assert result.initial_pipeline.iloc[0] == 7 and result.final_pipeline.iloc[0] == 4
    assert result.terminal_cost.iloc[0] == 8


def test_multiple_outstanding_orders_and_zero_costs():
    scenario = Scenario(
        lead_days=3,
        buffer_days=0,
        holding_cost=0,
        shortage_cost=0,
        fixed_order_cost=0,
        initial_cover_days=7,
    )
    result, events = simulate([[2] * 28], [2], window([10] * 28), scenario, "selected_ml")
    assert (events.order_quantity.iloc[:3] > 0).all() and events.receipts.iloc[:4].sum() == 0
    assert result.total_cost.iloc[0] == 0


def test_future_actual_poison_cannot_change_an_earlier_decision():
    scenario = Scenario(lead_days=1, initial_cover_days=7)
    first = np.ones((1, 28))
    poisoned = first.copy()
    poisoned[:, 10:] = 9999
    a, events_a = simulate(first, [1], window([2] * 28), scenario, "selected_ml")
    b, events_b = simulate(poisoned, [1], window([2] * 28), scenario, "selected_ml")
    pd.testing.assert_frame_equal(events_a.iloc[:10], events_b.iloc[:10])
    assert a.demand_units.iloc[0] != b.demand_units.iloc[0]


def test_forecast_visibility_dates_and_horizon_are_strict():
    forecast = window([1] * 7)
    with pytest.raises(ValueError, match="coverage|covered"):
        forecast.protection_sum(forecast.dates[-1], 1)
    with pytest.raises(ValueError, match="precedes"):
        forecast.protection_sum("2019-12-31", 1)
    with pytest.raises(ValueError, match="consecutive"):
        ForecastWindow(
            forecast.origin,
            forecast.dates[:-1] + (pd.Timestamp("2020-02-01").date(),),
            forecast.values,
        )
    with pytest.raises(ValueError):
        window([1, np.nan, 1])
    with pytest.raises(ValueError):
        replace(Scenario(), fulfilment="backorders")


def test_identical_common_initial_state_and_reproducible_paths():
    scenario = Scenario(horizon=7, lead_days=1)
    y, forecast = [[2] * 7], window([4] * 7)
    a, ea = simulate(y, [2], forecast, scenario, "seasonal_naive")
    b, eb = simulate(y, [2], forecast, scenario, "selected_ml")
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(ea, eb)
