"""Fixed-configuration statistical forecasts with explicit per-series delivery provenance."""

import logging
import warnings

import numpy as np
import pandas as pd

from intelligent_demand.experiments.preparation import panel_from_view
from intelligent_demand.experiments.registry import atomic_json
from intelligent_demand.models.base import ModelInfo, ModelRegistry
from intelligent_demand.models.baselines import BaselineModel, baseline_values

LIGHTWEIGHT = ("ses", "holt", "holt_winters_additive", "croston", "sba", "tsb")
EXPENSIVE = ("arima_100", "sarima_100_100_7")
STATISTICAL = (*LIGHTWEIGHT, *EXPENSIVE)
LOGGER = logging.getLogger(__name__)


def statistical_values(
    values, method, alpha=0.2, beta=0.05, gamma=0.05, phi=0.98, occurrence_beta=0.1
):
    """Daily updates use observed training only; no held-out zero updates for multi-step TSB."""
    original = np.asarray(values)
    if original.ndim != 2 or not original.shape[1] or method not in LIGHTWEIGHT:
        raise ValueError("Known lightweight method and nonempty training matrix required")
    if not np.isfinite(original).all() or (original < 0).any():
        raise ValueError("Invalid training observations cannot be hidden by a fallback")
    if not (
        0 < alpha < 1
        and 0 <= beta <= alpha
        and 0 <= gamma <= 1 - alpha
        and 0 < phi <= 1
        and 0 < occurrence_beta < 1
    ):
        raise ValueError("Invalid fixed smoothing parameters")
    # Time-major contiguous storage avoids strided per-period access over 30,490 histories.
    y = np.ascontiguousarray(original.T, dtype="float64")
    periods, n = y.shape
    positive_count = (y > 0).sum(axis=0)
    prediction, _, _ = baseline_values(original[:, -28:], "seasonal_naive")
    actual_method = np.full(n, method, dtype=object)
    reason = np.full(n, "native", dtype=object)
    zero = positive_count == 0
    required = 14 if method == "holt_winters_additive" else (2 if method == "holt" else 1)
    insufficient = np.full(n, periods < required)
    if method in ("croston", "sba"):
        insufficient |= (positive_count < 2) & ~zero
    actual_method[insufficient] = "seasonal_naive" if periods >= 7 else "naive"
    reason[insufficient] = "insufficient_history"
    state = {"series_position": np.arange(n), "positive_count": positive_count}
    if periods >= required:
        if method == "ses":
            level = y[0].copy()
            for observed in y[1:]:
                level = alpha * observed + (1 - alpha) * level
            prediction = np.repeat(level[:, None], 28, axis=1)
            state["level"] = level
        elif method == "holt":
            level, trend = y[0].copy(), y[1] - y[0]
            for observed in y[1:]:
                previous = level
                level = alpha * observed + (1 - alpha) * (level + trend)
                trend = beta * (level - previous) + (1 - beta) * trend
            prediction = level[:, None] + trend[:, None] * np.arange(1, 29)
            state.update(level=level, trend=trend)
        elif method == "holt_winters_additive":
            first, second = y[:7].mean(axis=0), y[7:14].mean(axis=0)
            level, trend = second.copy(), (second - first) / 7
            seasonal = ((y[:7] - first) + (y[7:14] - second)) / 2
            for t, observed in enumerate(y[14:]):
                index = t % 7
                old_level = level
                previous = old_level + phi * trend
                old_season = seasonal[index].copy()
                level = alpha * (observed - old_season) + (1 - alpha) * previous
                trend = beta * (level - old_level) + (1 - beta) * phi * trend
                seasonal[index] = gamma * (observed - previous) + (1 - gamma) * old_season
            damped_steps = np.cumsum(phi ** np.arange(1, 29))
            seasonal_indexes = ((periods - 14) + np.arange(28)) % 7
            prediction = (
                level[:, None] + trend[:, None] * damped_steps + seasonal[seasonal_indexes].T
            )
            state.update(level=level, trend=trend)
            state.update({f"season_{i}": seasonal[i] for i in range(7)})
        else:
            size, interval, probability = np.zeros(n), np.ones(n), np.zeros(n)
            last_positive = np.full(n, -1, dtype=int)
            for t, observed in enumerate(y):
                positive = observed > 0
                initialised = last_positive >= 0
                first = positive & ~initialised
                update = positive & initialised
                if method == "tsb":
                    probability[initialised] += occurrence_beta * (
                        positive[initialised].astype(float) - probability[initialised]
                    )
                    probability[first] = 1 / (t + 1)
                size[first], interval[first] = observed[first], t + 1
                size[update] += alpha * (observed[update] - size[update])
                interval[update] += alpha * ((t - last_positive[update]) - interval[update])
                last_positive[positive] = t
            level = size * probability if method == "tsb" else size / interval
            if method == "sba":
                level *= 1 - alpha / 2
            prediction = np.repeat(level[:, None], 28, axis=1)
            state.update(size=size, interval=interval, probability=probability)
    fallback, _, _ = baseline_values(original[:, -28:], "seasonal_naive")
    prediction[insufficient] = fallback[insufficient]
    prediction[zero], actual_method[zero], reason[zero] = 0, "zero", "all_zero_history"
    invalid = ~np.isfinite(prediction).all(axis=1)
    prediction[invalid], actual_method[invalid], reason[invalid] = (
        fallback[invalid],
        "seasonal_naive" if periods >= 7 else "naive",
        "nonfinite_forecast",
    )
    return prediction, actual_method, reason, pd.DataFrame(state)


def arima_forecast(history, method, configuration):
    """Fixed order maximum-likelihood estimation, not order search or hyperparameter tuning."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    if method not in EXPENSIVE:
        raise ValueError("Known ARIMA-family method required")
    order = tuple(
        configuration["arima_order"] if method == "arima_100" else configuration["sarima_order"]
    )
    seasonal = (
        (0, 0, 0, 0) if method == "arima_100" else tuple(configuration["sarima_seasonal_order"])
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = SARIMAX(
            np.asarray(history, dtype=float),
            order=order,
            seasonal_order=seasonal,
            trend="c",
            enforce_stationarity=True,
            enforce_invertibility=True,
            missing="raise",
        )
        fitted = model.fit(
            method="lbfgs",
            maxiter=configuration["maximum_likelihood_iterations"],
            disp=False,
            cov_type="none",
        )
        if not fitted.mle_retvals.get("converged", False):
            raise RuntimeError("failed_convergence")
        result = np.asarray(fitted.forecast(28), dtype=float)
    if (
        result.shape != (28,)
        or not np.isfinite(result).all()
        or not np.isfinite(fitted.params).all()
    ):
        raise FloatingPointError("nonfinite_native_result")
    if np.max(np.abs(result)) > 1e6 * max(1, float(np.max(history))):
        raise FloatingPointError("explosive_native_result")
    return result, fitted.params.tolist(), sorted({type(w.message).__name__ for w in caught})


class StatisticalModel(BaselineModel):
    def __init__(self, method):
        if method not in STATISTICAL:
            raise ValueError("Unknown statistical method")
        super().__init__(method)

    def _fit(self, training_data, configuration):
        panel = panel_from_view(training_data)
        self.series = tuple(training_data.series)
        parameters = configuration["parameters"]
        if (
            parameters["arima_order"] != [1, 0, 0]
            or parameters["sarima_order"] != [1, 0, 0]
            or parameters["sarima_seasonal_order"] != [1, 0, 0, 7]
            or type(parameters["maximum_likelihood_iterations"]) is not int
            or not 1 <= parameters["maximum_likelihood_iterations"] <= 200
            or parameters["season"] != 7
        ):
            raise ValueError("Statistical configuration differs from its declared model contract")
        self.parameters = parameters
        method = self.info.identifier
        if method in LIGHTWEIGHT:
            self.forecasts, actual, reason, self.states = statistical_values(
                panel.values,
                method,
                parameters["alpha"],
                parameters["trend_beta"],
                parameters["seasonal_gamma"],
                parameters["damping_phi"],
                parameters["occurrence_beta"],
            )
            warning_types = [""] * len(self.series)
        else:
            self.forecasts, _, _ = baseline_values(panel.values[:, -28:], "seasonal_naive")
            actual = np.full(len(self.series), method, dtype=object)
            reason = np.full(len(self.series), "native", dtype=object)
            states, warning_types = [], []
            for i, history in enumerate(panel.values):
                positive = int((history > 0).sum())
                params, warning = None, []
                if positive == 0:
                    self.forecasts[i], actual[i], reason[i] = 0, "zero", "all_zero_history"
                elif len(history) < 56 or positive < 2:
                    actual[i], reason[i] = "seasonal_naive", "insufficient_history"
                else:
                    try:
                        self.forecasts[i], params, warning = arima_forecast(
                            history, method, parameters
                        )
                    except (
                        ValueError,
                        RuntimeError,
                        FloatingPointError,
                        np.linalg.LinAlgError,
                    ) as exc:
                        actual[i], reason[i] = "seasonal_naive", type(exc).__name__ + ":" + str(exc)
                warning_types.append(",".join(warning))
                states.append(
                    {"series_position": i, "positive_count": positive, "parameters": params}
                )
                if i % 20 == 0:
                    LOGGER.info("%s: %s/%s series fitted", method, i + 1, len(self.series))
            self.states = pd.DataFrame(states)
        self.delivery = pd.DataFrame(
            {
                "series_id": self.series,
                "requested_method": method,
                "actual_method": actual,
                "is_fallback": actual != method,
                "reason": reason,
                "warning_types": warning_types,
            }
        )
        self.states["series_id"] = self.series

    def save_artifacts(self, directory):
        paths = super().save_artifacts(directory)
        path = directory / "training_states.parquet"
        self.states.to_parquet(path, index=False)
        paths["training_states"] = path
        configuration = directory / "fixed_parameters.json"
        atomic_json(configuration, self.parameters)
        paths["fixed_parameters"] = configuration
        return paths


def statistical_registry():
    registry = ModelRegistry()
    for method in STATISTICAL:
        registry.register(
            ModelInfo(method, "1", "global"), lambda method=method: StatisticalModel(method)
        )
    return registry
