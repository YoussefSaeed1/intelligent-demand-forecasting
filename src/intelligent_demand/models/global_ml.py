"""Bounded global RF/CPU LightGBM with a true-origin recursive information state."""

import logging
import time

import joblib
import numpy as np
import pandas as pd

from intelligent_demand.experiments.preparation import panel_from_view
from intelligent_demand.experiments.registry import atomic_json
from intelligent_demand.features.recursive import (
    historical_price_context,
    observed_context,
    training_matrix,
)
from intelligent_demand.models.base import ModelInfo, ModelRegistry
from intelligent_demand.models.baselines import BaselineModel, baseline_values

ML_METHODS = ("random_forest", "lightgbm")
LOGGER = logging.getLogger(__name__)


class GlobalMLModel(BaselineModel):
    def __init__(self, method):
        if method not in ML_METHODS:
            raise ValueError("Unknown global ML model")
        super().__init__(method)

    def _fit(self, training_data, configuration):
        parameters = configuration["parameters"]
        if (
            parameters["schema_version"] != 1
            or parameters["strategy"] != "recursive_28"
            or parameters["feature_history_days"] != 56
            or type(parameters["feature_batch_rows"]) is not int
            or not 1 <= parameters["feature_batch_rows"] <= 65536
        ):
            raise ValueError("ML settings differ from the declared recursive feature contract")
        self.parameters = parameters
        self.series = tuple(training_data.series)
        started = time.perf_counter()
        x, y, encoder, manifest = training_matrix(
            training_data,
            configuration["maximum_training_rows"],
            configuration["random_seed"],
            configuration["feature_cache"],
            configuration["source_fingerprint"],
            parameters["feature_batch_rows"],
        )
        self.feature_preparation_seconds = time.perf_counter() - started
        self.encoder, self.manifest = encoder, manifest
        self.probe = np.asarray(x[: min(16, len(x))]).copy()
        started = time.perf_counter()
        if self.info.identifier == "random_forest":
            from sklearn.ensemble import RandomForestRegressor

            self.estimator = RandomForestRegressor(
                **parameters["random_forest"],
                random_state=configuration["random_seed"],
                n_jobs=configuration["max_threads"],
            )
            # sklearn's current NaN validation requires a writable buffer; never mutate the cache.
            self.estimator.fit(
                np.array(x, dtype="float32", order="C", copy=True), np.array(y, copy=True)
            )
            # Fixed summation order makes recursive point paths repeatable across calls.
            self.estimator.n_jobs = 1
        else:
            import lightgbm as lgb

            options = dict(parameters["lightgbm"])
            rounds = options.pop("num_boost_round")
            options.update(
                seed=configuration["random_seed"],
                num_threads=configuration["max_threads"],
                feature_fraction_seed=configuration["random_seed"],
                bagging_seed=configuration["random_seed"],
                data_random_seed=configuration["random_seed"],
            )
            dataset = lgb.Dataset(
                x,
                label=y,
                feature_name=encoder.names,
                categorical_feature=encoder.categorical_indexes,
                free_raw_data=True,
            )
            self.estimator = lgb.train(options, dataset, num_boost_round=rounds)
            self.estimator.free_dataset()
        self.estimator_fit_seconds = time.perf_counter() - started
        panel = panel_from_view(training_data)
        self.initial_history = np.asarray(panel.values[:, -56:], dtype=float).copy()
        self.observed = observed_context(self.initial_history)
        self.static = encoder.static_codes(panel.metadata)
        self.prices = (
            None
            if panel.prices is None
            else historical_price_context(
                panel.prices,
                np.arange(len(self.series)),
                np.full(len(self.series), len(panel.dates)),
            )
        )
        self.delivery = pd.DataFrame(
            {
                "series_id": self.series,
                "requested_method": self.info.identifier,
                "actual_method": self.info.identifier,
                "is_fallback": False,
                "reason": "native",
            }
        )
        self.max_threads = configuration["max_threads"]

    def _model_predict(self, matrix):
        self.encoder.validate(matrix)
        if self.info.identifier == "random_forest":
            return np.asarray(self.estimator.predict(matrix), dtype=float)
        return np.asarray(self.estimator.predict(matrix, num_threads=self.max_threads), dtype=float)

    def _predict(self, forecast_origin, horizon, available_features):
        history = self.initial_history.copy()
        self.forecasts = np.empty((len(self.series), 28), dtype=float)
        fallback, _, _ = baseline_values(history, "seasonal_naive")
        failed = np.zeros(len(self.series), dtype=bool)
        reasons = np.full(len(self.series), "native", dtype=object)
        for step in range(28):
            target = pd.Timestamp(forecast_origin) + pd.Timedelta(days=step + 1)
            features = self.encoder.matrix(
                history,
                pd.DatetimeIndex([target] * len(self.series)),
                self.static,
                self.observed,
                self.prices,
            )
            predicted = self._model_predict(features)
            if predicted.shape != (len(self.series),):
                raise ValueError("Global estimator returned the wrong population shape")
            invalid = ~np.isfinite(predicted)
            reasons[invalid & ~failed] = f"nonfinite_native_forecast_at_step_{step + 1}"
            failed |= invalid
            predicted[invalid] = fallback[invalid, step]
            self.forecasts[:, step] = predicted
            history = np.column_stack((history[:, 1:], np.maximum(predicted, 0)))
            if step % 7 == 0:
                LOGGER.info("%s: recursive horizon %s/28", self.info.identifier, step + 1)
        # Deliver one explicitly identified method for the entire failed series/window.
        self.forecasts[failed] = fallback[failed]
        self.delivery["actual_method"] = np.where(failed, "seasonal_naive", self.info.identifier)
        self.delivery["is_fallback"], self.delivery["reason"] = failed, reasons
        yield from super()._predict(forecast_origin, horizon, available_features)

    def metadata(self):
        return {
            **super().metadata(),
            "training_rows": self.manifest["training_rows"],
            "feature_count": len(self.encoder.names),
            "strategy": "recursive_28",
            "feature_preparation_seconds": self.feature_preparation_seconds,
            "estimator_fit_seconds": self.estimator_fit_seconds,
            "prediction_threads": 1
            if self.info.identifier == "random_forest"
            else self.max_threads,
            "feature_cache_contract": self.manifest["contract"],
        }

    def save_artifacts(self, directory):
        paths = super().save_artifacts(directory)
        if self.info.identifier == "random_forest":
            path = directory / "estimator.joblib"
            joblib.dump(self.estimator, path, compress=3)
            reloaded = joblib.load(path)
            restored = reloaded.predict(self.probe)
        else:
            import lightgbm as lgb

            path = directory / "estimator.txt"
            self.estimator.save_model(str(path))
            reloaded = lgb.Booster(model_file=str(path))
            restored = reloaded.predict(self.probe, num_threads=self.max_threads)
        np.testing.assert_allclose(
            self._model_predict(self.probe), restored, rtol=1e-12, atol=1e-12
        )
        paths["estimator"] = path
        features = directory / "feature_schema.json"
        atomic_json(features, self.encoder.metadata())
        paths["feature_schema"] = features
        proof = directory / "reload_validation.json"
        atomic_json(
            proof,
            {
                "passed": True,
                "probe_rows": len(self.probe),
                "rtol": 1e-12,
                "atol": 1e-12,
                "training_rows": self.manifest["training_rows"],
            },
        )
        paths["reload_validation"] = proof
        return paths


def ml_registry():
    registry = ModelRegistry()
    for method in ML_METHODS:
        registry.register(
            ModelInfo(method, "1", "global"), lambda method=method: GlobalMLModel(method)
        )
    return registry
