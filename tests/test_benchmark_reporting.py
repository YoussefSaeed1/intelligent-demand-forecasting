"""Comparisons keep populations separate and reconstruct pooled metrics from totals."""

import numpy as np
import pandas as pd
import pytest

from intelligent_demand.evaluation.benchmark_audit import METRICS, reconcile_series_metrics
from intelligent_demand.reporting.benchmark_report import aggregate


def test_benchmark_aggregation_separates_scope_and_uses_pooled_error_totals():
    rows = []
    for scope in ("full", "statistical_subset"):
        for fold, error in enumerate((1.0, 3.0, 1.0, 3.0), start=1):
            actual = error * 28 if scope == "full" else 0.0
            rows.append(
                {
                    "dataset": "fixture",
                    "scope": scope,
                    "model": "fixture",
                    "fold": fold,
                    "series": 1,
                    "observations": 28,
                    "actual": actual,
                    "absolute_error": error * 28,
                    "squared_error": error**2 * 28,
                    "error": error * 28,
                    "macro_mae": error,
                    "macro_rmse": error,
                    "macro_mase": error / 2,
                    "macro_rmsse": error / 2,
                    "fallback": 0,
                    "clipped": 0,
                }
            )
    result = aggregate(pd.DataFrame(rows)).set_index("scope")
    assert len(result) == 2
    assert result.loc["full", "macro_mae"] == 2
    assert result.loc["full", "mean_fold_macro_rmse"] == 2
    assert np.isclose(result.loc["full", "pooled_rmse"], np.sqrt(5))
    assert result.loc["full", "pooled_wape_percent"] == 100
    assert np.isnan(result.loc["statistical_subset", "pooled_wape_percent"])
    assert result.loc["full", "observations"] == 112


@pytest.mark.parametrize("corruption", ["value", "null", "order"])
def test_vectorised_audit_still_checks_every_series_value_and_undefined_scale(corruption):
    expected = {metric: np.array([1.0, np.nan]) for metric in METRICS}
    records = [
        {"series_id": "s1", **{metric: 1.0 for metric in METRICS}},
        {"series_id": "s2", **{metric: None for metric in METRICS}},
    ]
    reconcile_series_metrics(expected, records, ("s1", "s2"))
    if corruption == "value":
        records[0]["mae"] = 2.0
    elif corruption == "null":
        records[1]["mase"] = 0.0
    else:
        records.reverse()
    with pytest.raises(ValueError):
        reconcile_series_metrics(expected, records, ("s1", "s2"))
