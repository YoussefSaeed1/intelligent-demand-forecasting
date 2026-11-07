"""Independent arithmetic and poison-target tests for real baseline implementations."""

from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from intelligent_demand.evaluation.benchmark_audit import independent_summary, prediction_arrays
from intelligent_demand.evaluation.predictions import PREDICTION_SCHEMA, PredictionWriter
from intelligent_demand.evaluation.scoring import training_scales
from intelligent_demand.evaluation.splits import load_splits
from intelligent_demand.experiments.data import ParquetSource
from intelligent_demand.experiments.preparation import PreparedSource, panel_from_view
from intelligent_demand.experiments.registry import file_digest
from intelligent_demand.models.base import ModelInfo
from intelligent_demand.models.baselines import BASELINES, BaselineModel, baseline_values

ROOT = Path(__file__).resolve().parents[1]


def synthetic_source(
    tmp_path, dataset="store_item", poison=987654321, duplicate=False, validation_complete=False
):
    fold = load_splits(ROOT / "reports/eda/proposed_splits.json")[dataset][0]
    dates = pd.date_range(fold.train_start, fold.origin)
    parts = []
    for key, units in (("s1", np.arange(len(dates)) % 17), ("s2", np.zeros(len(dates)))):
        part = pd.DataFrame({"series_id": key, "date": dates, "sales_units": units})
        part["dataset_id"] = dataset
        parts.append(part)
        future = pd.DataFrame(
            {
                "series_id": [key, key],
                "date": pd.to_datetime([fold.validation_start, fold.holdout_start]),
                "sales_units": [poison, poison],
                "dataset_id": dataset,
            }
        )
        if validation_complete:
            future = pd.DataFrame(
                {
                    "series_id": key,
                    "date": pd.to_datetime([*fold.dates, fold.holdout_start]),
                    "sales_units": [9.0] * 28 + [poison],
                    "dataset_id": dataset,
                }
            )
        parts.append(future)
    frame = pd.concat(parts, ignore_index=True)
    if duplicate:
        frame = pd.concat([frame, frame.iloc[:1]], ignore_index=True)
    frame["unit_price"] = 2.5
    schema = pa.schema(
        [
            ("series_id", pa.string()),
            ("date", pa.date32()),
            ("sales_units", pa.float64()),
            ("dataset_id", pa.string()),
            ("unit_price", pa.float64()),
        ]
    )
    path = tmp_path / f"{dataset}-{poison}.parquet"
    pq.write_table(pa.Table.from_pandas(frame, schema=schema, preserve_index=False), path)
    metadata = pd.DataFrame({"series_id": ["s1", "s2"]})
    source = PreparedSource(path, dataset, metadata, tmp_path / "cache", file_digest(path), 109)
    return source, fold


@pytest.mark.parametrize("method", BASELINES)
def test_baseline_formula_exactly_matches_declared_arithmetic(method):
    values = np.arange(1, 57, dtype=float).reshape(2, 28)
    predictions, actual, fallback = baseline_values(values, method)
    assert predictions.shape == (2, 28)
    assert not fallback and actual == method
    if method == "naive":
        expected = np.repeat(values[:, -1:], 28, axis=1)
    elif method == "seasonal_naive":
        expected = np.tile(values[:, -7:], (1, 4))
    elif method == "moving_average_28":
        expected = np.repeat(values.mean(axis=1, keepdims=True), 28, axis=1)
    elif method == "seasonal_moving_average":
        pattern = np.array([[np.mean(row[day::7]) for day in range(7)] for row in values])
        expected = np.tile(pattern, (1, 4))
    else:
        expected = np.zeros((2, 28))
    np.testing.assert_array_equal(predictions, expected)


@pytest.mark.parametrize("method", BASELINES)
@pytest.mark.parametrize("length", [1, 6, 7, 27, 28])
def test_short_histories_have_explicit_fallback_and_all_zero_is_valid(method, length):
    predictions, actual, fallback = baseline_values(np.zeros((2, length)), method)
    assert not predictions.any()
    assert np.isfinite(predictions).all()
    required = (
        28
        if method in ("moving_average_28", "seasonal_moving_average")
        else (7 if method == "seasonal_naive" else 1)
    )
    assert fallback == (length < required)
    assert actual == (("seasonal_naive" if length >= 7 else "naive") if fallback else method)


@pytest.mark.parametrize("dataset", ["store_item", "m5"])
def test_prepared_panel_and_scales_match_origin_bounded_stream(tmp_path, dataset):
    source, fold = synthetic_source(tmp_path, dataset)
    view = source.at_origin(fold, ("s1", "s2"))
    panel = panel_from_view(view)
    assert panel.dates[-1].date() == fold.origin
    assert panel.values.max() <= 16
    with pytest.raises(ValueError):
        panel.values[0, 0] = 10
    expected = training_scales(view.history(), fold, ("s1", "s2"))
    actual = source.scales(fold, ("s1", "s2"))
    for column in ("scale_absolute", "scale_squared"):
        np.testing.assert_allclose(actual[column], expected[column], equal_nan=True, rtol=1e-12)
    assert np.isnan(actual.scale_absolute.iloc[1])
    assert file_digest(source.path) == source.fingerprint
    with pytest.raises(ValueError):
        source.panel(fold, ("unknown",))


@pytest.mark.parametrize("method", BASELINES)
def test_future_actual_mutation_cannot_change_baseline_predictions(tmp_path, method):
    first, fold = synthetic_source(tmp_path, poison=987654321)
    second, _ = synthetic_source(tmp_path, poison=123456789)
    results = []
    for source in (first, second):
        view = source.at_origin(fold, ("s1", "s2"))
        model = BaselineModel(method).fit(view, {})
        results.append(
            pd.concat(model.predict(fold.origin, 28, view.calendar_features()), ignore_index=True)
        )
    pd.testing.assert_frame_equal(*results)
    assert len(results[0]) == 56
    assert not results[0].duplicated(["series_id", "target_date"]).any()
    assert results[0].target_date.max().date() == fold.validation_end


def test_panel_cache_rejects_duplicate_observations(tmp_path):
    source, fold = synthetic_source(tmp_path, duplicate=True)
    with pytest.raises(ValueError, match="Duplicate"):
        source.panel(fold, ("s1", "s2"))


def test_prepared_cache_is_reused_and_tampering_is_rejected(tmp_path):
    source, fold = synthetic_source(tmp_path)
    expected = source.panel(fold, ("s1", "s2")).values.copy()
    second = PreparedSource(
        source.path, source.dataset_id, source.metadata, source.cache_root, source.fingerprint
    )
    np.testing.assert_array_equal(second.panel(fold, ("s1", "s2")).values, expected)
    path = next(source.cache_root.rglob("values-*.npy"))
    with path.open("ab") as stream:
        stream.write(b"tamper")
    third = PreparedSource(
        source.path, source.dataset_id, source.metadata, source.cache_root, source.fingerprint
    )
    with pytest.raises(ValueError, match="checksum"):
        third.panel(fold, ("s1", "s2"))


def test_nonprepared_capability_can_support_baseline_adapters(tmp_path):
    source, fold = synthetic_source(tmp_path)
    plain = ParquetSource(source.path, source.dataset_id)
    model = BaselineModel("naive").fit(plain.at_origin(fold, ("s1", "s2")), {})
    assert model.forecasts.shape == (2, 28)
    assert fold.validation_start == fold.origin + timedelta(days=1)


def test_independent_reconciliation_distinguishes_pooled_and_macro_metrics():
    actual = np.array([[1.0, 1.0], [0.0, 0.0]])
    predicted = np.array([[1.0, 3.0], [1.0, 1.0]])
    summary = independent_summary(
        actual,
        predicted,
        np.array([[1.0, 1.0], [np.nan, np.nan]]),
        np.zeros((2, 2), bool),
        np.zeros((2, 2), bool),
    )
    assert summary["pooled"]["mae"] == summary["macro"]["mae"] == 1
    assert summary["pooled"]["wape_percent"] == 200
    assert summary["macro"]["wape_percent"] == 100
    assert summary["coverage"]["undefined_series"]["mase"] == 1
    assert not np.isclose(summary["macro"]["rmse"], summary["pooled"]["rmse"])


@pytest.mark.parametrize("mutation", [None, "duplicate", "date", "step", "raw", "clipping", "run"])
def test_independent_persisted_prediction_audit_detects_corruption(tmp_path, mutation):
    source, fold = synthetic_source(tmp_path)
    path = tmp_path / "predictions.parquet"
    info = ModelInfo("fixture", "1", "global")
    frame = pd.MultiIndex.from_product(
        [["s1", "s2"], pd.to_datetime(fold.dates)], names=["series_id", "target_date"]
    ).to_frame(index=False)
    frame["prediction"] = np.arange(56, dtype=float) - 3
    writer = PredictionWriter(path, fold, ("s1", "s2"), info, "fixture-run")
    writer.write(frame)
    writer.finish()
    state = {
        "run_id": "fixture-run",
        "specification": {"model": {"identifier": "fixture", "version": "1"}},
    }
    if mutation is None:
        predicted, fallback, clipped = prediction_arrays(path, state, fold, ("s1", "s2"))
        np.testing.assert_array_equal(predicted.ravel(), np.maximum(np.arange(56) - 3, 0))
        assert not fallback.any() and clipped.sum() == 3
        return
    saved = pd.read_parquet(path)
    if mutation == "duplicate":
        saved.loc[1, "target_date"] = saved.loc[0, "target_date"]
    elif mutation == "date":
        saved.loc[0, "target_date"] = pd.Timestamp(fold.holdout_start)
    elif mutation == "step":
        saved.loc[0, "horizon_step"] = 28
    elif mutation == "raw":
        saved.loc[0, "raw_prediction"] = 10.0
    elif mutation == "clipping":
        saved.loc[0, "was_clipped"] = False
    else:
        saved.loc[0, "run_id"] = "different"
    pq.write_table(
        pa.Table.from_pandas(saved, schema=PREDICTION_SCHEMA, preserve_index=False), path
    )
    with pytest.raises(ValueError):
        prediction_arrays(path, state, fold, ("s1", "s2"))
