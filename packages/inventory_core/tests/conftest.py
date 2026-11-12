import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
EXPORT = REPO / "artifacts/webapp/data"


def has_evidence():
    return (REPO / "artifacts/inventory/phase5/runs").is_dir() and (EXPORT / "validation_actuals.csv").is_file()


@pytest.fixture(scope="session")
def curated():
    """Curated export tables exactly as they are loaded into Postgres."""
    if not has_evidence():
        pytest.skip("Local Phase 5 evidence and the curated export are required")
    actuals = pd.read_csv(EXPORT / "validation_actuals.csv")
    forecasts = pd.read_csv(EXPORT / "forecasts.csv")
    means = pd.read_csv(EXPORT / "series_origin_mean56.csv")
    origins = pd.read_csv(EXPORT / "validation_origins.csv").set_index("OriginKey")
    return {
        "actuals": {k: g.sort_values("Date").Units.to_numpy() for k, g in actuals.groupby(["SeriesKey", "OriginKey"])},
        "forecasts": {
            k: g.sort_values("HorizonDay").Forecast.to_numpy()
            for k, g in forecasts.groupby(["SeriesKey", "OriginKey", "ModelKey"])
        },
        "means": means.set_index(["SeriesKey", "OriginKey"]).HistoricalMean56.to_dict(),
        "origins": origins,
    }


def planner_inputs(curated, series_key, origin_key):
    from inventory_service.planner import FORECAST_ROLES, PlannerInputs

    dataset = series_key.split("|")[0]
    origin = curated["origins"].loc[origin_key]
    return PlannerInputs(
        origin_date=origin.OriginDate,
        validation_start=origin.ValidationStart,
        demand=curated["actuals"][(series_key, origin_key)],
        historical_mean56=float(curated["means"][(series_key, origin_key)]),
        forecasts={r: curated["forecasts"][(series_key, origin_key, f"{dataset}|{r}")] for r in FORECAST_ROLES},
    )


@pytest.fixture(scope="session")
def phase5_cases():
    if not has_evidence():
        pytest.skip("Local Phase 5 evidence is required")
    cases = []
    for path in sorted((REPO / "artifacts/inventory/phase5/runs").glob("*/status.json")):
        cases.append(json.loads(path.read_text(encoding="utf-8")))
    assert len(cases) == 544
    return cases


def synthetic_inputs(demand=None, forecast=5.0, mean=5.0):
    from inventory_service.planner import PlannerInputs

    demand = np.full(28, 5.0) if demand is None else np.asarray(demand, dtype=float)
    return PlannerInputs(
        "2017-08-13",
        "2017-08-14",
        demand,
        mean,
        {r: np.full(28, forecast) for r in ("selected_ml", "moving_average_28", "seasonal_naive")},
    )
