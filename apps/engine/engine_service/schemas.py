"""Strict request and response models. Bounds mirror configs/webapp.yaml (asserted by tests)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

Policy = Literal["selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point"]
SERIES_KEY = r"^(store_item|m5)\|[A-Za-z0-9_:\-]{1,40}$"
ORIGIN_KEY = r"^(store_item|m5)\|[1-4]$"

BOUNDS = {
    "lead_days": (0, 14),
    "review_days": (1, 7),
    "buffer_days": (0, 7),
    "initial_cover_days": (0, 14),
    "holding_cost": (0.1, 5),
    "shortage_cost": (1, 50),
    "fixed_order_cost": (0, 10),
    "variable_order_cost": (0, 1),
    "terminal_cost": (0, 1),
    "variability_multiplier": (0.5, 1.5),
}


class ScenarioParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    lead_days: StrictInt = Field(7, ge=0, le=14, alias="leadDays")
    review_days: StrictInt = Field(1, ge=1, le=7, alias="reviewDays")
    buffer_days: float = Field(3, ge=0, le=7, alias="bufferDays", allow_inf_nan=False)
    initial_cover_days: float = Field(7, ge=0, le=14, alias="initialCoverDays", allow_inf_nan=False)
    holding_cost: float = Field(1, ge=0.1, le=5, alias="holdingCost", allow_inf_nan=False)
    shortage_cost: float = Field(10, ge=1, le=50, alias="shortageCost", allow_inf_nan=False)
    fixed_order_cost: float = Field(1, ge=0, le=10, alias="fixedOrderCost", allow_inf_nan=False)
    variable_order_cost: float = Field(0, ge=0, le=1, alias="variableOrderCost", allow_inf_nan=False)
    terminal_cost: float = Field(0, ge=0, le=1, alias="terminalCost", allow_inf_nan=False)
    variability_multiplier: float = Field(1, ge=0.5, le=1.5, alias="variabilityMultiplier", allow_inf_nan=False)

    @model_validator(mode="after")
    def protection_within_horizon(self):
        if self.lead_days + self.review_days > 28:
            raise ValueError("leadDays + reviewDays must not exceed the 28-day forecast horizon")
        return self

    def engine_parameters(self):
        """Engine Scenario requires ints for timing and int/float for the rest."""
        values = self.model_dump()
        for key in (
            "buffer_days",
            "initial_cover_days",
            "holding_cost",
            "shortage_cost",
            "fixed_order_cost",
            "variable_order_cost",
            "terminal_cost",
            "variability_multiplier",
        ):
            number = float(values[key])
            values[key] = int(number) if number.is_integer() else number
        return values


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    series_key: str = Field(alias="seriesKey", pattern=SERIES_KEY)
    origin_key: str = Field(alias="originKey", pattern=ORIGIN_KEY)
    policies: list[Policy] = Field(min_length=1, max_length=4)
    scenario: ScenarioParameters = Field(default_factory=ScenarioParameters)
    request_id: str | None = Field(default=None, alias="requestId", max_length=64, pattern=r"^[A-Za-z0-9\-]+$")

    @model_validator(mode="after")
    def consistent(self):
        if len(set(self.policies)) != len(self.policies):
            raise ValueError("policies must be distinct")
        if self.series_key.split("|")[0] != self.origin_key.split("|")[0]:
            raise ValueError("series and origin belong to different datasets")
        return self
