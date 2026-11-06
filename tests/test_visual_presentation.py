"""Analytical denominators used by the added visualisations; no forecasting tests."""

import numpy as np
import pandas as pd

from intelligent_demand.exploration.presentation import department_summary, tail_probabilities
from intelligent_demand.exploration.visual_review import inventory


def test_department_rates_divide_by_series_exposure_not_raw_totals():
    series = pd.DataFrame({"dept_id": ["A", "A", "B"]})
    daily = pd.DataFrame({"group": ["A", "B"], "sales_units": [10, 8]})
    result = department_summary(daily, series)
    assert result.units_per_series_day.tolist() == [5, 8]
    assert result.series.tolist() == [2, 1]
    assert daily.columns.tolist() == ["group", "sales_units"]


def test_exact_histogram_survival_includes_zeros_and_rare_maximum():
    histogram = pd.DataFrame({"units": [10, 0, 2], "observations": [1, 6, 3]})
    result = tail_probabilities(histogram)
    assert result.units.tolist() == [0, 2, 10]
    np.testing.assert_allclose(result.at_least_probability, [1, 0.4, 0.1])
    assert result.at_least_probability.is_monotonic_decreasing
    assert histogram.units.tolist() == [10, 0, 2]


def test_complete_unique_enhanced_figure_catalogue():
    records = inventory()
    assert len(records) == len({record["stem"] for record in records}) == 29
    for stem in (
        "m5_snap",
        "m5_departments",
        "m5_classification",
        "store_item_extremes",
        "m5_extremes",
    ):
        assert any(record["stem"] == stem for record in records)
