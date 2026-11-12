"""Deterministic lost-sales engine with a target-free replenishment interface."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from intelligent_demand.inventory.design import POLICIES, Scenario


def quantities(value, shape=None):
    array = np.asarray(value)
    if array.dtype.kind == "b":
        raise ValueError("Boolean quantities are invalid")
    array = np.asarray(value, dtype=float)
    if (
        (shape is not None and array.shape != shape)
        or not np.isfinite(array).all()
        or (array < 0).any()
    ):
        raise ValueError("Finite nonnegative matched quantities required")
    return array


@dataclass(frozen=True)
class ForecastWindow:
    origin: object
    dates: tuple
    values: np.ndarray

    def __post_init__(self):
        origin = pd.Timestamp(self.origin)
        if origin.tz is not None or origin != origin.normalize():
            raise ValueError("Naive daily forecast origin required")
        expected = tuple((origin + pd.Timedelta(days=i + 1)).date() for i in range(len(self.dates)))
        if tuple(self.dates) != expected or not 1 <= len(expected) <= 28:
            raise ValueError("Complete consecutive absolute forecast dates required")
        array = quantities(self.values)
        if array.ndim != 2 or array.shape[1] != len(expected):
            raise ValueError("Forecast series/date shape mismatch")
        array = array.copy()
        array.flags.writeable = False
        object.__setattr__(self, "values", array)
        object.__setattr__(self, "origin", origin.date())

    def protection_sum(self, decision_day, periods):
        day = pd.Timestamp(decision_day)
        if day.tz is not None or day != day.normalize() or day.date() < self.origin:
            raise ValueError("Decision precedes the forecast issue date")
        first = (day.date() - self.dates[0]).days + 1
        if (
            type(periods) is not int
            or periods < 1
            or first < 0
            or first + periods > len(self.dates)
        ):
            raise ValueError("Full protection period is not covered by remaining saved forecasts")
        return self.values[:, first : first + periods].sum(axis=1)


def order_quantity(policy, position, historical_mean, window, decision_day, scenario):
    """No realised future demand, residual arrays or retrospective groups are accepted."""
    if policy not in POLICIES:
        raise ValueError("Unknown inventory policy")
    mean = quantities(historical_mean)
    position = quantities(position, mean.shape)
    buffer = scenario.buffer_days * mean
    if policy == "fixed_reorder_point":
        reorder = mean * scenario.protection_days + buffer
        return np.where(position <= reorder, np.ceil(mean * scenario.review_days), 0)
    if window is None or len(window.values) != len(mean):
        raise ValueError("A matched origin-issued forecast is required")
    target = window.protection_sum(decision_day, scenario.protection_days) + buffer
    return np.ceil(np.maximum(0, target - position))


def ratio(numerator, denominator):
    return np.divide(
        numerator,
        denominator,
        out=np.full_like(numerator, np.nan, dtype=float),
        where=denominator > 0,
    )


def simulate(
    demand, historical_mean, window, scenario: Scenario, policy, event_rows=None, initial_due=None
):
    scenario.__post_init__()
    if policy not in POLICIES:
        raise ValueError("Unknown inventory policy")
    y = quantities(demand)
    if y.ndim != 2 or not len(y) or y.shape[1] != scenario.horizon:
        raise ValueError("Demand path must match the declared finite episode")
    n, horizon = y.shape
    mean = quantities(historical_mean, (n,))
    if window is None or window.values.shape != y.shape:
        raise ValueError("Matched saved horizon required, including common fixed-policy cutoff")
    initial = np.ceil(mean * scenario.initial_cover_days)
    stock = initial.copy()
    initial_due = {} if initial_due is None else initial_due
    if any(type(k) is not int or not 0 <= k <= horizon + 90 for k in initial_due):
        raise ValueError("Invalid pre-existing receipt date")
    last_day = max([horizon + scenario.lead_days + 1, *initial_due])
    due = np.zeros((n, last_day + 1))
    for day, amount in initial_due.items():
        due[:, day] = quantities(amount, (n,))
    pipeline = due.sum(axis=1)
    initial_pipeline = pipeline.copy()
    totals = {
        key: np.zeros(n)
        for key in (
            "demand_units",
            "fulfilled_units",
            "unmet_units",
            "received_units",
            "placed_units",
            "holding_cost",
            "shortage_cost",
            "ordering_cost",
            "stockout_days",
            "orders",
            "closing_stock_sum",
            "position_sum",
        )
    }
    rows = np.arange(n) if event_rows is None else np.asarray(event_rows, dtype=int)
    if ((rows < 0) | (rows >= n)).any() or len(np.unique(rows)) != len(rows):
        raise ValueError("Unique valid event sample indices required")
    events = []
    for day in range(horizon):
        opening, pipe_open = stock.copy(), pipeline.copy()
        received = due[:, day].copy()
        available = opening + received
        fulfilled = np.minimum(available, y[:, day])
        unmet = y[:, day] - fulfilled
        stock = available - fulfilled
        pipeline = pipeline - received
        allowed = day % scenario.review_days == 0 and day + scenario.protection_days < horizon
        target_date = window.dates[day]
        order = np.zeros(n)
        if allowed:
            order = order_quantity(policy, stock + pipeline, mean, window, target_date, scenario)
            due[:, day + scenario.lead_days + 1] += order
            pipeline = pipeline + order
        holding = scenario.holding_cost * stock
        shortage = scenario.shortage_cost * unmet
        ordering = scenario.fixed_order_cost * (order > 0) + scenario.variable_order_cost * order
        for difference in (
            opening + received - fulfilled - stock,
            y[:, day] - fulfilled - unmet,
            pipe_open - received + order - pipeline,
        ):
            if not np.allclose(difference, 0, atol=1e-8, rtol=0):
                raise ValueError("Daily inventory conservation failed")
        if (stock < -1e-9).any() or (pipeline < -1e-9).any() or (fulfilled > available).any():
            raise ValueError("Invalid stock, pipeline or fulfilment")
        for key, value in {
            "demand_units": y[:, day],
            "fulfilled_units": fulfilled,
            "unmet_units": unmet,
            "received_units": received,
            "placed_units": order,
            "holding_cost": holding,
            "shortage_cost": shortage,
            "ordering_cost": ordering,
            "stockout_days": unmet > 0,
            "orders": order > 0,
            "closing_stock_sum": stock,
            "position_sum": stock + pipeline,
        }.items():
            totals[key] += value
        if len(rows):
            event = {
                "series_row": rows,
                "day_index": day,
                "target_date": target_date,
                "opening_stock": opening[rows],
                "receipts": received[rows],
                "available_stock": available[rows],
                "demand": y[rows, day],
                "fulfilled": fulfilled[rows],
                "unmet": unmet[rows],
                "closing_stock": stock[rows],
                "pipeline_opening": pipe_open[rows],
                "pipeline_after": pipeline[rows],
                "inventory_position": (stock + pipeline)[rows],
                "order_quantity": order[rows],
                "holding_cost": holding[rows],
                "shortage_cost": shortage[rows],
                "ordering_cost": ordering[rows],
                "review_allowed": allowed,
            }
            events.append(pd.DataFrame(event))
    terminal = scenario.terminal_cost * (stock + pipeline)
    result = pd.DataFrame(totals)
    result["initial_on_hand"], result["initial_pipeline"] = initial, initial_pipeline
    result["final_on_hand"], result["final_pipeline"] = stock, pipeline
    result["terminal_cost"] = terminal
    result["total_cost"] = (
        result.holding_cost + result.shortage_cost + result.ordering_cost + terminal
    )
    result["fill_rate"] = ratio(result.fulfilled_units.to_numpy(), result.demand_units.to_numpy())
    result["stockout_day_rate"] = result.stockout_days / horizon
    result["average_on_hand"] = result.closing_stock_sum / horizon
    result["average_inventory_position"] = result.position_sum / horizon
    result["average_order_quantity"] = ratio(
        result.placed_units.to_numpy(), result.orders.to_numpy()
    )
    result["order_frequency"] = result.orders / horizon
    result["window_turnover"] = ratio(
        result.fulfilled_units.to_numpy(), result.average_on_hand.to_numpy()
    )
    for difference in (
        initial + result.received_units - result.fulfilled_units - stock,
        initial_pipeline + result.placed_units - result.received_units - pipeline,
    ):
        if not np.allclose(difference, 0, rtol=0, atol=1e-7):
            raise ValueError("Episode stock/pipeline conservation failed")
    return result, pd.concat(events, ignore_index=True) if events else pd.DataFrame()
