"""Strict, versioned hypothetical inventory assumptions; no model or target access."""

from dataclasses import asdict, dataclass
from math import isfinite

import yaml

POLICIES = ("fixed_reorder_point", "moving_average_28", "seasonal_naive", "selected_ml")


@dataclass(frozen=True)
class Scenario:
    identifier: str = "base"
    horizon: int = 28
    lead_days: int = 7
    review_days: int = 1
    buffer_days: float = 3
    initial_cover_days: float = 7
    holding_cost: float = 1
    shortage_cost: float = 10
    fixed_order_cost: float = 1
    variable_order_cost: float = 0
    terminal_cost: float = 0
    variability_multiplier: float = 1
    fulfilment: str = "lost_sales"

    def __post_init__(self):
        if (type(self.horizon) is not int or not 1 <= self.horizon <= 28
                or type(self.lead_days) is not int or self.lead_days < 0
                or type(self.review_days) is not int or self.review_days < 1
                or self.protection_days > self.horizon or self.fulfilment != "lost_sales"):
            raise ValueError("Unsupported horizon, timing or fulfilment assumption")
        if not self.identifier or not self.identifier.replace("_", "").isalnum():
            raise ValueError("Safe nonempty scenario identifier required")
        for key in ("buffer_days", "initial_cover_days", "holding_cost", "shortage_cost",
                    "fixed_order_cost", "variable_order_cost", "terminal_cost",
                    "variability_multiplier"):
            value = getattr(self, key)
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError(f"Finite nonnegative hypothetical quantity required: {key}")

    @property
    def protection_days(self):
        return self.lead_days + self.review_days

    def metadata(self):
        return asdict(self)


def load_design(path):
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (set(value) != {"schema_version", "horizon", "seed", "fulfilment", "policies",
                       "base", "variants", "resources", "events"}
            or value["schema_version"] != 1 or value["horizon"] != 28
            or value["seed"] != 42 or tuple(value["policies"]) != POLICIES
            or value["events"] != "base_full_other_representatives"):
        raise ValueError("Inventory configuration differs from its explicit contract")
    resources = value["resources"]
    if resources["workers"] != 1 or resources["batch_series"] > 4096:
        raise ValueError("Bounded single-worker execution required")
    if any(type(v) is not int or v < 1 for v in resources.values()):
        raise ValueError("Positive integer resource limits required")
    scenarios = [Scenario(**value["base"], fulfilment=value["fulfilment"])]
    for name, override in value["variants"].items():
        scenarios.append(Scenario(identifier=name, **(value["base"] | override),
                                  fulfilment=value["fulfilment"]))
    if len({s.identifier for s in scenarios}) != len(scenarios):
        raise ValueError("Duplicate scenario identifiers")
    return value, tuple(scenarios)
