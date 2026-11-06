"""Offline analytical invariants; fixture results are not empirical forecasting scores."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from intelligent_demand.evaluation.design import chronological_plan
from intelligent_demand.evaluation.metrics import forecast_metrics, scaling_denominators
from intelligent_demand.exploration.pipeline import _hist_quantile, load_settings
from intelligent_demand.exploration.statistics import (
    classify_patterns,
    panel_statistics,
    price_activity,
    weekday_bootstrap,
)
from intelligent_demand.exploration.validation import reconcile_training_sources


def test_adi_cv2_zeros_and_leading_zero_sensitivity():
    result = panel_statistics(np.array([[0, 0, 2, 0, 4, 0]], dtype=float)).iloc[0]
    assert result.positive_count == 2
    assert result.adi == 3
    assert result.cv2_positive == pytest.approx(2 / 9)
    assert result.zero_percent == pytest.approx(100 * 4 / 6)
    assert result.active_span_days == 4
    assert result.active_span_adi == 2
    assert result.pattern == "intermittent"
    assert result.sales_units == 6


def test_undefined_and_constant_series_are_explicit():
    result = panel_statistics(np.array([[0, 0, 0, 0], [0, 0, 2, 0], [2, 2, 2, 2]], dtype=float))
    assert result.pattern.tolist() == ["all_zero", "insufficient_positive_history", "smooth"]
    assert np.isnan(result.adi.iloc[0]) and np.isnan(result.cv2_positive.iloc[1])
    assert result.cv2_positive.iloc[2] == 0
    assert np.isnan(result.corr_lag_1.iloc[2])


def test_classification_threshold_equality_enters_high_group():
    labels = classify_patterns(
        np.array([1.31, 1.31, 1.32, 1.32]), np.array([0.48, 0.49, 0.48, 0.49]), np.full(4, 3)
    )
    assert labels.tolist() == ["smooth", "erratic", "intermittent", "lumpy"]


@pytest.mark.parametrize("values", [np.array([1, 2]), np.array([[1, -1]]), np.array([[np.nan, 1]])])
def test_invalid_panels_rejected(values):
    with pytest.raises(ValueError):
        panel_statistics(values)


def test_price_activity_partition_and_positive_zero_reconciliation():
    values = np.array([[0, 0, 2, 0, 3, 0], [0, 0, 0, 0, 0, 0]], dtype=float)
    frame, totals = price_activity(np.ones_like(values, dtype=bool), values)
    assert frame.iloc[0].missing_before_first_positive == 2
    assert frame.iloc[0].missing_between_first_last_positive == 3
    assert frame.iloc[0].missing_after_last_positive == 1
    assert frame.iloc[1].missing_no_positive_in_eda == 6
    assert totals["missing_prices"] == 12
    assert totals["missing_with_positive_sales"] == 2
    assert totals["missing_with_zero_sales"] == 10


def test_price_mask_shape_checked():
    with pytest.raises(ValueError):
        price_activity(np.zeros((1, 2), bool), np.zeros((1, 3)))


@pytest.mark.parametrize(
    "end,cutoff,test_start",
    [
        (date(2017, 12, 31), "2017-08-13", "2017-12-04"),
        (date(2016, 5, 22), "2016-01-03", "2016-04-25"),
    ],
)
def test_split_boundaries_and_nonoverlap(end, cutoff, test_start):
    plan = chronological_plan(date(2011, 1, 1), end)
    assert plan["eda_end"] == cutoff
    assert plan["test_start"] == test_start
    previous = date.fromisoformat(cutoff)
    for fold in plan["validation_folds"]:
        first, last = map(date.fromisoformat, [fold["validation_start"], fold["validation_end"]])
        assert first == previous + timedelta(days=1)
        assert (last - first).days == 27
        assert date.fromisoformat(fold["origin"]) == first - timedelta(days=1)
        previous = last
    assert date.fromisoformat(test_start) == previous + timedelta(days=1)
    assert (end - date.fromisoformat(test_start)).days == 27


def test_calendar_leap_day_is_retained():
    plan = chronological_plan(date(2011, 1, 29), date(2016, 5, 22))
    assert plan["validation_folds"][2]["validation_start"] == "2016-02-29"


def test_short_history_rejected():
    with pytest.raises(ValueError):
        chronological_plan(date(2020, 1, 1), date(2020, 12, 31))


def test_metric_definitions_and_training_only_scales():
    result = forecast_metrics(np.array([0, 2]), np.array([1, 1]), np.array([1, 2, 3, 4]), season=1)
    assert result == {
        "mae": 1.0,
        "rmse": 1.0,
        "bias_units": 0.0,
        "wape_percent": 100.0,
        "bias_percent": 0.0,
        "mase": 1.0,
        "rmsse": 1.0,
    }
    assert scaling_denominators(np.array([2, 4, 6, 8]), 1) == (2.0, 4.0)


def test_zero_actual_and_constant_training_do_not_use_epsilon():
    result = forecast_metrics(np.zeros(2), np.array([0.0, 1.0]), np.zeros(10))
    assert result["wape_percent"] is None and result["bias_percent"] is None
    assert result["mase"] is None and result["rmsse"] is None
    assert result["mae"] == 0.5 and result["bias_units"] == 0.5
    assert scaling_denominators(np.array([1, 2]), 7) == (None, None)


@pytest.mark.parametrize("actual,predicted", [([], []), ([1], [1, 2]), ([np.nan], [0])])
def test_invalid_forecast_inputs_rejected(actual, predicted):
    with pytest.raises(ValueError):
        forecast_metrics(actual, predicted)


def test_weekday_normalisation_and_bootstrap_are_reproducible():
    dates = pd.date_range("2020-01-06", periods=56)
    daily = pd.DataFrame({"date": dates, "sales_units": np.tile(np.arange(1, 8), 8)})
    first = weekday_bootstrap(daily, 42, 50, 4)
    second = weekday_bootstrap(daily, 42, 50, 4)
    pd.testing.assert_frame_equal(first, second)
    np.testing.assert_allclose(first.mean_within_week_ratio, np.arange(1, 8) / 4)
    np.testing.assert_allclose(first.ci_low, first.ci_high)
    assert first.complete_weeks.eq(8).all()


def test_empirical_histogram_quantiles_and_weighted_total():
    hist = np.array([2, 3, 5])
    assert _hist_quantile(hist, 0.5) == 1
    assert _hist_quantile(hist, 0.9) == 2
    assert int(np.dot(np.arange(3), hist)) == 13


def test_invalid_analysis_configuration(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("horizon_days: 0\n")
    with pytest.raises(ValueError, match="horizon_days"):
        load_settings(path)


@pytest.mark.parametrize("corrupt_expected", [False, True])
def test_independent_csv_reconciliation_excludes_reserved_targets(tmp_path, corrupt_expected):
    from types import SimpleNamespace

    for name in ("store_item", "m5"):
        (tmp_path / name).mkdir()
    (tmp_path / "store_item/train.csv").write_text(
        "date,sales\n2020-01-01,2\n2020-01-02,0\n2020-01-03,99999\n"
    )
    (tmp_path / "m5/calendar.csv").write_text(
        "date,d\n2020-01-01,d_1\n2020-01-02,d_2\n2020-01-03,d_3\n"
    )
    (tmp_path / "m5/sales_train_evaluation.csv").write_text("d_1,d_2,d_3\n0,4,99999\n0,3,99999\n")
    plan = {"eda_start": "2020-01-01", "eda_end": "2020-01-02"}
    results = {
        "store_item": {
            "split_plan": plan,
            "eda_rows": 2,
            "eda_sales_units": 2,
            "eda_zero_count": 1,
        },
        "m5": {"split_plan": plan, "eda_rows": 4, "eda_sales_units": 7, "eda_zero_count": 2},
    }
    config = SimpleNamespace(paths={"raw": tmp_path})
    if corrupt_expected:
        results["m5"]["eda_sales_units"] = 8
        with pytest.raises(ValueError, match="independent source training totals disagree"):
            reconcile_training_sources(config, results)
    else:
        checks = reconcile_training_sources(config, results)
        assert checks["store_item"]["sales_units"] == 2
        assert checks["m5"] == {"rows": 4, "sales_units": 7, "zero_count": 2}
