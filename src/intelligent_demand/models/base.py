"""Practical model contract and empty-by-default registration; no forecasting methods."""

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

from intelligent_demand.experiments.config import canonical_json
from intelligent_demand.experiments.data import OriginData, validate_future_features


@dataclass(frozen=True)
class ModelInfo:
    identifier: str
    version: str
    scope: str

    def __post_init__(self):
        if (
            not isinstance(self.identifier, str)
            or not self.identifier.strip()
            or not isinstance(self.version, str)
            or not self.version.strip()
            or self.scope not in ("local", "global")
        ):
            raise ValueError("Model identifier, version and local/global scope required")


class ForecastModel(ABC):
    """Fresh-instance lifecycle; concrete forecasting implementations belong to later phases."""

    def __init__(self, info: ModelInfo):
        self.info = info
        self._origin = None
        self._configuration = None
        self._dataset_id = None
        self._fold = None
        self._series = None

    def fit(self, training_data: OriginData, configuration: dict):
        if not isinstance(training_data, OriginData):
            raise ValueError("Model fitting requires an origin-bounded data capability")
        training_data.__post_init__()
        if self._origin is not None:
            raise ValueError("A fresh model is required for every origin")
        snapshot = canonical_json(configuration)
        self._fit(training_data, json.loads(snapshot))
        self._origin = training_data.fold.origin
        self._dataset_id = training_data.fold.dataset_id
        self._fold, self._series = training_data.fold, training_data.series
        self._configuration = snapshot
        return self

    def predict(self, forecast_origin, horizon, available_features):
        if self._origin is None or forecast_origin != self._origin or horizon != 28:
            raise ValueError("Fit this origin first; exactly 28 daily steps are required")
        features = validate_future_features(
            available_features,
            self._fold,
            self._series,
            available_features.attrs.get("availability", {}),
        )
        return self._predict(forecast_origin, horizon, features)

    def metadata(self):
        return {
            **asdict(self.info),
            "forecast_origin": str(self._origin),
            "dataset_id": self._dataset_id,
            "configuration_json": self._configuration,
        }

    def save_artifacts(self, directory):
        """Optional local artefacts; returned files must stay inside the attempt directory."""
        return {}

    @abstractmethod
    def _fit(self, training_data, configuration):
        """Consume only origin-visible training data; fit all preprocessing inside this hook."""

    @abstractmethod
    def _predict(self, forecast_origin, horizon, available_features):
        """Return frames with series_id, target_date, prediction and optional is_fallback."""


class ModelRegistry:
    def __init__(self):
        self._factories = {}

    def register(self, info: ModelInfo, factory):
        key = (info.identifier, info.version)
        if key in self._factories or not callable(factory):
            raise ValueError("Duplicate model registration or noncallable factory")
        self._factories[key] = (info, factory)

    def create(self, identifier, version):
        info, factory = self._factories[(identifier, version)]
        model = factory()
        if not isinstance(model, ForecastModel) or model.info != info or model._origin is not None:
            raise ValueError("Factory must return a fresh matching ForecastModel")
        return model

    def registered(self):
        return [asdict(value[0]) for _, value in sorted(self._factories.items())]
