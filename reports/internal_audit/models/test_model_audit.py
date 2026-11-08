"""Independent synthetic audit fixtures; no real forecasts or targets are regenerated."""

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

from intelligent_demand.evaluation.splits import load_splits
from intelligent_demand.experiments.preparation import PreparedSource
from intelligent_demand.experiments.registry import file_digest
from intelligent_demand.features.recursive import FeatureEncoder
from intelligent_demand.models.baselines import BASELINES, baseline_values
from intelligent_demand.models.global_ml import GlobalMLModel
from intelligent_demand.models.statistical import arima_forecast, statistical_values

ROOT = Path(__file__).resolve().parents[3]


def smoothing_reference(history, method):
    """Independent closed-form SES/Croston/SBA/TSB and error-state Holt/HW."""
    values = np.asarray(history, dtype=float)
    alpha, beta, gamma, phi, occurrence = 0.2, 0.05, 0.05, 0.98, 0.1
    if method == "ses":
        n = len(values)
        return np.repeat(
            (1 - alpha) ** (n - 1) * values[0]
            + sum(alpha * (1 - alpha) ** (n - 1 - j) * values[j] for j in range(1, n)),
            28,
        )
    if method == "holt":
        state = np.array([values[0], values[1] - values[0]])
        transition = np.array([[1 - alpha, 1 - alpha], [-alpha * beta, 1 - alpha * beta]])
        loading = np.array([alpha, alpha * beta])
        for observed in values[1:]:
            state = transition @ state + loading * observed
        return state[0] + np.arange(1, 29) * state[1]
    if method == "holt_winters_additive":
        first = sum(values[:7]) / 7
        second = sum(values[7:14]) / 7
        level, trend = second, (second - first) / 7
        seasonal = [(values[j] - first + values[j + 7] - second) / 2 for j in range(7)]
        for index in range(14, len(values)):
            slot = index % 7
            error = values[index] - (level + phi * trend + seasonal[slot])
            level += phi * trend + alpha * error
            trend = phi * trend + beta * alpha * error
            seasonal[slot] += gamma * error
        return np.array([
            level + sum(phi ** j for j in range(1, h + 1)) * trend
            + seasonal[(len(values) + h - 1) % 7]
            for h in range(1, 29)
        ])
    positive = np.flatnonzero(values > 0)
    if not len(positive):
        return np.zeros(28)
    amplitudes = values[positive]
    intervals = np.diff(np.r_[-1, positive])
    n = len(positive)
    size = (1 - alpha) ** (n - 1) * amplitudes[0] + sum(
        alpha * (1 - alpha) ** (n - 1 - j) * amplitudes[j] for j in range(1, n)
    )
    interval = (1 - alpha) ** (n - 1) * intervals[0] + sum(
        alpha * (1 - alpha) ** (n - 1 - j) * intervals[j] for j in range(1, n)
    )
    if method == "tsb":
        start, end = positive[0], len(values) - 1
        probability = (1 - occurrence) ** (end - start) / (start + 1) + sum(
            occurrence * (1 - occurrence) ** (end - j) * (values[j] > 0)
            for j in range(start + 1, end + 1)
        )
        level = probability * size
    else:
        level = size / interval * (1 - alpha / 2 if method == "sba" else 1)
    return np.repeat(level, 28)


@pytest.mark.parametrize(
    "method", ["ses", "holt", "holt_winters_additive", "croston", "sba", "tsb"]
)
def test_against_independent_reference_on_random_histories(method):
    rng = np.random.default_rng(127)
    for length in [14, 15, 20, 27, 28, 29, 70, 101]:
        for intermittent in [False, True]:
            values = rng.integers(1, 30, length).astype(float)
            if intermittent:
                values[rng.uniform(size=length) < 0.7] = 0
                values[[3, -2]] = [2, 7]
            actual, delivered, _, _ = statistical_values(values[None], method)
            assert delivered[0] == method
            np.testing.assert_allclose(
                actual[0], smoothing_reference(values, method), rtol=1e-11, atol=1e-11
            )


@pytest.mark.parametrize("method", BASELINES)
def test_baselines_against_independent_day_index_arithmetic(method):
    rng = np.random.default_rng(51)
    values = rng.integers(0, 100, (3, 83)).astype(float)
    actual, _, fallback = baseline_values(values, method)
    expected = []
    for row in values:
        if method == "naive":
            prediction = [row[-1]] * 28
        elif method == "zero":
            prediction = [0.0] * 28
        elif method == "moving_average_28":
            prediction = [sum(row[-28:]) / 28] * 28
        elif method == "seasonal_naive":
            prediction = [row[len(row) - 7 + h % 7] for h in range(28)]
        else:
            prediction = [sum(row[len(row) - 28 + h % 7 + 7 * k] for k in range(4)) / 4
                          for h in range(28)]
        expected.append(prediction)
    assert not fallback
    np.testing.assert_allclose(actual, expected, rtol=0, atol=0)


def synthetic_source(directory, dataset, poison):
    fold = load_splits(ROOT / "reports/eda/proposed_splits.json")[dataset][0]
    dates = pd.date_range(fold.train_start, fold.validation_end)
    rows = []
    for number, series in enumerate(["a", "b"]):
        sales = (np.arange(len(dates)) % (7 + number)).astype(float)
        sales[dates.date > fold.origin] = poison
        rows.append(pd.DataFrame({"dataset_id": dataset, "series_id": series,
                                  "date": dates.date, "sales_units": sales,
                                  "unit_price": poison if dataset == "m5" else 2.0}))
    frame = pd.concat(rows, ignore_index=True)
    path = directory / "synthetic.parquet"
    schema = pa.schema([("dataset_id", pa.string()), ("series_id", pa.string()),
                        ("date", pa.date32()), ("sales_units", pa.float64()),
                        ("unit_price", pa.float64())])
    pq.write_table(pa.Table.from_pandas(frame, schema=schema, preserve_index=False), path)
    metadata = pd.DataFrame({"series_id": ["a", "b"], "store_id": ["1", "2"],
                             "item_id": ["1", "1"], "cat_id": ["c", "c"],
                             "dept_id": ["d", "d"], "state_id": ["s", "s"]})
    return PreparedSource(path, dataset, metadata, directory / "panel", file_digest(path)), fold


@pytest.mark.parametrize("dataset", ["store_item", "m5"])
@pytest.mark.parametrize("method", ["random_forest", "lightgbm"])
def test_new_synthetic_future_poison_and_price_free_training_invariance(tmp_path, dataset, method):
    parameters = yaml.safe_load((ROOT / "configs/ml.yaml").read_text())
    parameters["use_historical_prices"] = False
    parameters["random_forest"].update(n_estimators=8, min_samples_leaf=1)
    parameters["lightgbm"].update(num_boost_round=8, min_data_in_leaf=1)
    outcomes = []
    for number, poison in enumerate([73.0, 9876543.0]):
        directory = tmp_path / str(number)
        directory.mkdir()
        source, fold = synthetic_source(directory, dataset, poison)
        view = source.at_origin(fold, ("a", "b"))
        config = {"parameters": copy.deepcopy(parameters), "maximum_training_rows": 128,
                  "random_seed": 42, "max_threads": 1,
                  "feature_cache": str(directory / "features"),
                  "source_fingerprint": source.fingerprint}
        model = GlobalMLModel(method).fit(view, config)
        prediction = pd.concat(model.predict(fold.origin, 28, view.calendar_features()))
        assert not any("price" in name for name in model.encoder.names)
        assert not {"snap", "event", "actual", "target"}.intersection(model.encoder.names)
        assert prediction.groupby("series_id").size().eq(28).all()
        outcomes.append(prediction.reset_index(drop=True))
    pd.testing.assert_frame_equal(*outcomes, rtol=0, atol=0)


def test_static_encoding_ignores_target_derived_metadata_and_known_calendar():
    metadata = pd.DataFrame({"store_id": ["1", "2"], "item_id": ["3", "4"],
                             "sales_units": [10, 20], "pattern": ["smooth", "intermittent"]})
    first = FeatureEncoder(metadata, "store_item", "2013-01-01", False)
    metadata["sales_units"] = np.inf
    metadata["pattern"] = "poison"
    second = FeatureEncoder(metadata, "store_item", "2013-01-01", False)
    assert json.dumps(first.metadata(), sort_keys=True) == json.dumps(
        second.metadata(), sort_keys=True
    )


@pytest.mark.parametrize("method", ["arima_100", "sarima_100_100_7"])
def test_arima_wrapper_order_intercept_horizon_and_convergence(monkeypatch, method):
    """Independent wrapper audit only; does not certify native optimizer mathematics."""
    calls = {}

    class Fitted:
        params = np.array([0.8, 1.2])
        mle_retvals = {"converged": True}

        def forecast(self, horizon):
            calls["horizon"] = horizon
            return np.arange(horizon, dtype=float)

    class Native:
        def __init__(self, history, **kwargs):
            calls["observations"] = np.array(history, copy=True)
            calls["constructor"] = kwargs

        def fit(self, **kwargs):
            calls["fit"] = kwargs
            return Fitted()

    monkeypatch.setattr("statsmodels.tsa.statespace.sarimax.SARIMAX", Native)
    configuration = yaml.safe_load((ROOT / "configs/statistical.yaml").read_text())
    history = np.arange(90, dtype=float)
    result, parameters, _ = arima_forecast(history, method, configuration)
    assert calls["constructor"]["order"] == (1, 0, 0)
    assert calls["constructor"]["seasonal_order"] == (
        (0, 0, 0, 0) if method == "arima_100" else (1, 0, 0, 7)
    )
    assert calls["constructor"]["trend"] == "c"
    assert calls["fit"]["maxiter"] == 80 and calls["horizon"] == 28
    np.testing.assert_array_equal(calls["observations"], history)
    np.testing.assert_array_equal(result, np.arange(28))
    assert parameters == [0.8, 1.2]
    Fitted.mle_retvals = {"converged": False}
    with pytest.raises(RuntimeError, match="failed_convergence"):
        arima_forecast(history, method, configuration)
