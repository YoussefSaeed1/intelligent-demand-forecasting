"""Single-series planner wrapper around the unchanged Phase 5 engine.

Reproduces `intelligent_demand.inventory.runner.run_case` exactly for one series: the same variability
transform, the same `ForecastWindow` construction, the selected-ML window passed to the fixed reorder point
(which ignores it, as in Phase 5), and the engine's own `Scenario` validation. No scientific arithmetic is
added here; this module only shapes inputs and outputs.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from intelligent_demand.inventory.design import POLICIES, Scenario
from intelligent_demand.inventory.engine import ForecastWindow, simulate

FORECAST_ROLES = ("selected_ml", "moving_average_28", "seasonal_naive")
SUMMARY_FIELDS = (
    "demand_units",
    "fulfilled_units",
    "unmet_units",
    "received_units",
    "placed_units",
    "holding_cost",
    "shortage_cost",
    "ordering_cost",
    "terminal_cost",
    "total_cost",
    "stockout_days",
    "orders",
    "initial_on_hand",
    "initial_pipeline",
    "final_on_hand",
    "final_pipeline",
    "fill_rate",
    "stockout_day_rate",
    "average_on_hand",
    "average_inventory_position",
    "average_order_quantity",
    "order_frequency",
    "window_turnover",
)
EVENT_FIELDS = (
    "opening_stock",
    "receipts",
    "demand",
    "fulfilled",
    "unmet",
    "closing_stock",
    "pipeline_after",
    "inventory_position",
    "order_quantity",
    "holding_cost",
    "shortage_cost",
    "ordering_cost",
    "review_allowed",
)


@dataclass(frozen=True)
class PlannerInputs:
    """Immutable evidence for one series and validation origin, loaded server-side only."""

    origin_date: str  # ISO date of the forecast origin
    validation_start: str  # origin + 1 day
    demand: np.ndarray  # 28 realised validation-window units (never supplied by a client)
    historical_mean56: float  # Phase 5 origin-bounded 56-day mean
    forecasts: dict  # role -> 28 saved fixed-origin forecast values


def scenario_from(parameters, identifier="custom"):
    """Build the engine Scenario; its own __post_init__ enforces timing and non-negativity."""
    return Scenario(identifier=identifier, **parameters)


def stressed_demand(demand, mean, multiplier):
    """Exactly the Phase 5 runner transform: max(0, mu + a * (y - mu)) when a != 1."""
    if multiplier == 1:
        return demand
    return np.maximum(0, mean[:, None] + multiplier * (demand - mean[:, None]))


def _clean(value):
    value = float(value)
    return None if np.isnan(value) else value


def run_planner(inputs: PlannerInputs, scenario: Scenario, policies=POLICIES):
    if not policies or len(set(policies)) != len(policies) or not set(policies) <= set(POLICIES):
        raise ValueError("Policies must be a non-empty set of known Phase 5 policies")
    demand = np.asarray(inputs.demand, dtype=float).reshape(1, 28)
    mean = np.asarray([inputs.historical_mean56], dtype=float)
    y = stressed_demand(demand, mean, scenario.variability_multiplier)
    dates = tuple(pd.date_range(inputs.validation_start, periods=28).date)
    results = []
    for policy in policies:
        forecast = np.asarray(
            inputs.forecasts["selected_ml" if policy == "fixed_reorder_point" else policy], dtype=float
        ).reshape(1, 28)
        window = ForecastWindow(inputs.origin_date, dates, forecast)
        summary, events = simulate(y, mean, window, scenario, policy, event_rows=[0])
        row = summary.iloc[0]
        results.append(
            {
                "policy": policy,
                "summary": {field: _clean(row[field]) for field in SUMMARY_FIELDS},
                "daily": [
                    {
                        "date": str(record["target_date"]),
                        **{f: (bool(record[f]) if f == "review_allowed" else _clean(record[f])) for f in EVENT_FIELDS},
                    }
                    for record in events.to_dict("records")
                ],
            }
        )
    return {"demand": [float(v) for v in y[0]], "dates": [str(d) for d in dates], "policies": results}
