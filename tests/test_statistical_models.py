"""Statistical recurrences, reference-library checks, fallbacks and origin isolation."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from statsmodels.tsa.holtwinters import ExponentialSmoothing, Holt, SimpleExpSmoothing
from test_baseline_models import synthetic_source

from intelligent_demand.experiments.sampling import choose_statistical_subset
from intelligent_demand.models.statistical import (
    LIGHTWEIGHT,
    STATISTICAL,
    StatisticalModel,
    arima_forecast,
    statistical_values,
)

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = yaml.safe_load((ROOT / "configs/statistical.yaml").read_text())


@pytest.mark.parametrize("method", ["ses", "holt", "holt_winters_additive"])
def test_regular_smoothing_matches_independent_statsmodels_reference(method):
    rng = np.random.default_rng(42)
    history = 20 + np.arange(100) * 0.1 + np.tile(np.arange(7), 15)[:100] + rng.uniform(0, 1, 100)
    predicted, actual, reason, states = statistical_values(history[None], method)
    if method == "ses":
        fitted = SimpleExpSmoothing(
            history[1:], initialization_method="known", initial_level=history[0]
        ).fit(smoothing_level=0.2, optimized=False)
    elif method == "holt":
        fitted = Holt(
            history[1:],
            initialization_method="known",
            initial_level=history[0],
            initial_trend=history[1] - history[0],
        ).fit(smoothing_level=0.2, smoothing_trend=0.05, optimized=False)
    else:
        first, second = history[:7].mean(), history[7:14].mean()
        season = ((history[:7] - first) + (history[7:14] - second)) / 2
        fitted = ExponentialSmoothing(
            history[14:],
            trend="add",
            damped_trend=True,
            seasonal="add",
            seasonal_periods=7,
            initialization_method="known",
            initial_level=second,
            initial_trend=(second - first) / 7,
            initial_seasonal=season,
        ).fit(
            smoothing_level=0.2,
            smoothing_trend=0.05,
            smoothing_seasonal=0.05,
            damping_trend=0.98,
            optimized=False,
            use_brute=False,
        )
    if method == "holt_winters_additive":
        # statsmodels 0.15.0 recycles an older final seasonal element in forecast().
        # Its retained level/trend/season states agree with the component equations.
        np.testing.assert_allclose(states.level.iloc[0], fitted.level[-1], atol=1e-12)
        np.testing.assert_allclose(states.trend.iloc[0], fitted.trend[-1], atol=1e-12)
        expected = (
            fitted.level[-1]
            + fitted.trend[-1] * np.cumsum(0.98 ** np.arange(1, 29))
            + np.tile(fitted.season[-7:], 4)
        )
    else:
        expected = fitted.forecast(28)
    np.testing.assert_allclose(predicted[0], expected, rtol=1e-11, atol=1e-11)
    assert actual[0] == method and reason[0] == "native"


def test_weekly_seasonal_state_wraps_correctly_at_horizons_seven_fourteen_twentyone_twenty_eight():
    history = np.tile(np.arange(10.0, 17.0), 10)[None]
    prediction, *_ = statistical_values(history, "holt_winters_additive")
    np.testing.assert_allclose(prediction, np.tile(history[:, -7:], (1, 4)), atol=1e-11)


@pytest.mark.parametrize("method,expected", [("croston", 0.8), ("sba", 0.72), ("tsb", 0.74088)])
def test_intermittent_formulas_match_hand_calculation(method, expected):
    predicted, actual, reason, _ = statistical_values(np.array([[0, 0, 2, 0, 0, 4, 0.0]]), method)
    np.testing.assert_allclose(predicted, expected, rtol=1e-12)
    assert actual[0] == method and reason[0] == "native"


def test_tsb_decays_on_observed_zeros_but_not_unobserved_future_steps():
    history = np.array([[0, 0, 2, 0, 0, 4.0]])
    first, *_ = statistical_values(history, "tsb")
    longer, *_ = statistical_values(np.concatenate([history, np.zeros((1, 9))], axis=1), "tsb")
    np.testing.assert_allclose(longer, first * 0.9**9)
    assert np.unique(longer).size == 1
    for method in ("croston", "sba"):
        before, *_ = statistical_values(history, method)
        after, *_ = statistical_values(np.concatenate([history, np.zeros((1, 9))], axis=1), method)
        np.testing.assert_array_equal(before, after)


@pytest.mark.parametrize("method", LIGHTWEIGHT)
def test_all_zero_and_single_positive_histories_have_explicit_delivery(method):
    history = np.zeros((2, 60))
    history[1, 1] = 5
    predicted, actual, reason, _ = statistical_values(history, method)
    assert not predicted[0].any() and actual[0] == "zero" and reason[0] == "all_zero_history"
    assert np.isfinite(predicted).all()
    if method in ("croston", "sba"):
        assert actual[1] == "seasonal_naive" and reason[1] == "insufficient_history"


@pytest.mark.parametrize("method", LIGHTWEIGHT)
def test_missing_or_negative_training_is_not_masked_by_a_statistical_fallback(method):
    for value in (np.nan, -1):
        history = np.ones((1, 60))
        history[0, 20] = value
        with pytest.raises(ValueError, match="Invalid training"):
            statistical_values(history, method)


@pytest.mark.parametrize("method", STATISTICAL)
def test_future_actual_mutations_cannot_change_statistical_forecasts(tmp_path, method):
    outputs = []
    for poison in (987654321, 123456789):
        source, fold = synthetic_source(tmp_path, poison=poison)
        view = source.at_origin(fold, ("s1", "s2"))
        model = StatisticalModel(method).fit(view, {"parameters": PARAMETERS})
        frame = pd.concat(
            model.predict(fold.origin, 28, view.calendar_features()), ignore_index=True
        )
        outputs.append(frame)
    pd.testing.assert_frame_equal(*outputs)


@pytest.mark.parametrize("method", ["arima_100", "sarima_100_100_7"])
def test_fixed_order_native_arima_produces_full_finite_horizon(method):
    history = 10 + np.random.default_rng(42).normal(size=180)
    prediction, parameters, _ = arima_forecast(history, method, PARAMETERS)
    assert prediction.shape == (28,)
    assert np.isfinite(prediction).all() and np.isfinite(parameters).all()


def test_convergence_failure_records_requested_and_delivered_method(tmp_path, monkeypatch):
    def fail(*args):
        raise RuntimeError("failed_convergence")

    monkeypatch.setattr("intelligent_demand.models.statistical.arima_forecast", fail)
    source, fold = synthetic_source(tmp_path)
    model = StatisticalModel("arima_100").fit(
        source.at_origin(fold, ("s1", "s2")), {"parameters": PARAMETERS}
    )
    assert model.delivery.requested_method.eq("arima_100").all()
    assert model.delivery.actual_method.tolist() == ["seasonal_naive", "zero"]
    assert model.delivery.is_fallback.all()
    assert "failed_convergence" in model.delivery.reason.iloc[0]
    target = tmp_path / "model"
    target.mkdir()
    outputs = model.save_artifacts(target)
    assert {"delivery", "training_states", "fixed_parameters"}.issubset(outputs)
    pd.testing.assert_frame_equal(pd.read_parquet(outputs["delivery"]), model.delivery)


def test_stratified_selection_is_reproducible_and_ignores_future_performance():
    records = []
    for pattern in (
        "smooth",
        "erratic",
        "intermittent",
        "lumpy",
        "all_zero",
        "insufficient_positive_history",
    ):
        for store in range(3):
            for item in range(4):
                records.append(
                    {
                        "series_id": f"{pattern}-{store}-{item}",
                        "pattern": pattern,
                        "store_id": str(store),
                        "item_id": str(item),
                        "sales_units": len(records),
                        "cat_id": str(item % 2),
                        "dept_id": str(item),
                    }
                )
    metadata = pd.DataFrame(records)
    selected = choose_statistical_subset(metadata, "m5")
    changed = metadata.copy()
    changed["validation_error"] = np.arange(len(changed))[::-1]
    second = choose_statistical_subset(changed, "m5")
    assert selected.series_id.tolist() == second.series_id.tolist()
    for column in ("pattern", "store_id", "cat_id", "dept_id"):
        assert set(selected[column]) == set(metadata[column])
    assert (
        selected.groupby(["pattern", "store_id"]).ngroups
        == metadata.groupby(["pattern", "store_id"]).ngroups
    )
