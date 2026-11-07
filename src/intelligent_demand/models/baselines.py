"""Five deterministic origin-safe baseline methods, vectorised across independent series."""

import numpy as np
import pandas as pd

from intelligent_demand.experiments.preparation import panel_from_view
from intelligent_demand.experiments.registry import atomic_json
from intelligent_demand.models.base import ForecastModel, ModelInfo, ModelRegistry

BASELINES = ("naive", "seasonal_naive", "moving_average_28", "seasonal_moving_average", "zero")


def baseline_values(values, method, horizon=28):
    values = np.asarray(values, dtype="float64")
    if (
        values.ndim != 2
        or not values.shape[1]
        or not np.isfinite(values).all()
        or (values < 0).any()
    ):
        raise ValueError("Complete finite nonnegative training histories required")
    if method not in BASELINES or horizon != 28:
        raise ValueError("Known baseline and 28-day horizon required")
    required = {
        "naive": 1,
        "seasonal_naive": 7,
        "moving_average_28": 28,
        "seasonal_moving_average": 28,
        "zero": 1,
    }[method]
    fallback = values.shape[1] < required
    actual_method = ("seasonal_naive" if values.shape[1] >= 7 else "naive") if fallback else method
    if actual_method == "zero":
        output = np.zeros((len(values), 28))
    elif actual_method == "naive":
        output = np.repeat(values[:, -1:], 28, axis=1)
    elif actual_method == "seasonal_naive":
        output = np.tile(values[:, -7:], (1, 4))
    elif actual_method == "moving_average_28":
        output = np.repeat(values[:, -28:].mean(axis=1, keepdims=True), 28, axis=1)
    else:
        weekly = values[:, -28:].reshape(len(values), 4, 7).mean(axis=1)
        output = np.tile(weekly, (1, 4))
    return output, actual_method, fallback


class BaselineModel(ForecastModel):
    def __init__(self, method):
        super().__init__(ModelInfo(method, "1", "global"))

    def _fit(self, training_data, configuration):
        panel = panel_from_view(training_data)
        self.series = tuple(training_data.series)
        self.forecasts, actual, fallback = baseline_values(
            panel.values[:, -28:], self.info.identifier
        )
        self.delivery = pd.DataFrame(
            {
                "series_id": self.series,
                "requested_method": self.info.identifier,
                "actual_method": actual,
                "is_fallback": fallback,
                "reason": "insufficient_history" if fallback else "native",
            }
        )

    def _predict(self, forecast_origin, horizon, available_features):
        for start in range(0, len(self.series), 1000):
            series = self.series[start : start + 1000]
            frame = pd.MultiIndex.from_product(
                [series, pd.date_range(forecast_origin + pd.Timedelta(days=1), periods=28)],
                names=["series_id", "target_date"],
            ).to_frame(index=False)
            frame["prediction"] = self.forecasts[start : start + 1000].reshape(-1)
            frame["is_fallback"] = np.repeat(
                self.delivery.is_fallback.iloc[start : start + 1000].to_numpy(), 28
            )
            yield frame

    def save_artifacts(self, directory):
        path = directory / "delivery.parquet"
        self.delivery.to_parquet(path, index=False)
        configuration = directory / "method.json"
        atomic_json(
            configuration, {"method": self.info.identifier, "horizon": 28, "training_only": True}
        )
        return {"delivery": path, "method": configuration}


def baseline_registry():
    registry = ModelRegistry()
    for method in BASELINES:
        info = ModelInfo(method, "1", "global")
        registry.register(info, lambda method=method: BaselineModel(method))
    return registry
