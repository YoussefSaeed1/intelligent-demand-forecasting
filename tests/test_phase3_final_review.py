"""Arithmetic checks for the separate pre-checkpoint persisted-prediction review."""

import numpy as np

from intelligent_demand.evaluation.final_review import review_metrics


def test_direct_review_macro_and_pooled_arithmetic_have_correct_units_and_weights():
    actual = np.array([[0.0, 2.0], [2.0, 0.0]])
    prediction = np.array([[1.0, 3.0], [4.0, 0.0]])
    result = review_metrics(actual, prediction)
    assert result["macro_mae"] == 1.0
    assert result["pooled_rmse"] == np.sqrt(1.5)
    assert result["pooled_wape_percent"] == 100
    assert result["absolute_error_total"] == 4
    assert result["squared_error_total"] == 6


def test_direct_review_zero_actual_total_retains_undefined_percentage():
    result = review_metrics(np.zeros((2, 28)), np.ones((2, 28)))
    assert result["macro_mae"] == result["pooled_rmse"] == 1
    assert result["pooled_wape_percent"] is None
    assert result["observations"] == 56
