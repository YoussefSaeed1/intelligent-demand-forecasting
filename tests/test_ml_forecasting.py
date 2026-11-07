"""Leakage-adversarial feature, recursive-path and persisted-estimator tests."""

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from test_baseline_models import synthetic_source

from intelligent_demand.evaluation.ml_audit import audit_ml_training
from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.preparation import panel_from_view
from intelligent_demand.experiments.registry import atomic_json, file_digest
from intelligent_demand.features.recursive import (
    FeatureEncoder,
    historical_price_context,
    observed_context,
    training_matrix,
    training_positions,
)
from intelligent_demand.models.baselines import baseline_values
from intelligent_demand.models.global_ml import GlobalMLModel

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = yaml.safe_load((ROOT / "configs/ml.yaml").read_text())


def ml_source(tmp_path, dataset="store_item", poison=987654321):
    source, fold = synthetic_source(tmp_path, dataset=dataset, poison=poison)
    source.metadata = pd.DataFrame(
        {
            "series_id": ["s1", "s2"],
            "store_id": ["1", "2"],
            "item_id": ["1", "1"],
            "cat_id": ["cat", "cat"],
            "dept_id": ["dept", "dept"],
            "state_id": ["state", "state"],
            "sales_units": [9999999, 8888888],
            "pattern": ["future", "future"],
        }
    )
    return source, fold


def configuration(tmp_path, source):
    return {
        "parameters": PARAMETERS,
        "maximum_training_rows": 128,
        "random_seed": 42,
        "max_threads": 4,
        "feature_cache": str(tmp_path / "feature-cache"),
        "source_fingerprint": source.fingerprint,
    }


def test_shifted_lags_rolling_and_observed_statistics_match_hand_values():
    metadata = pd.DataFrame({"store_id": ["1"], "item_id": ["1"]})
    encoder = FeatureEncoder(metadata, "store_item", "2013-01-01")
    history = np.arange(1.0, 57.0)[None]
    x = encoder.matrix(history, pd.to_datetime(["2013-02-26"]), encoder.static_codes(metadata))[0]
    for lag in (1, 7, 14, 28, 56):
        assert x[encoder.names.index(f"lag_{lag}")] == 57 - lag
    assert x[encoder.names.index("rolling_mean7")] == 53
    assert x[encoder.names.index("rolling_mean28")] == 42.5
    assert np.isclose(x[encoder.names.index("rolling_std7")], 2.0)
    assert x[encoder.names.index("obs_adi56")] == 1
    assert x[encoder.names.index("obs_zero_fraction56")] == 0


def test_price_features_use_only_completed_historical_weeks_and_preserve_nulls():
    prices = np.arange(1.0, 101.0)[None]
    original = historical_price_context(prices, np.array([0]), np.array([60]))
    assert original[0, 0] == prices[0, 26:54].mean()
    changed = prices.copy()
    changed[:, 54:] = 1e9
    np.testing.assert_array_equal(
        original, historical_price_context(changed, np.array([0]), np.array([60]))
    )
    changed[:, 26:54] = np.nan
    missing = historical_price_context(changed, np.array([0]), np.array([60]))
    assert np.isnan(missing[0, 0]) and missing[0, 1] == 1
    changed[0, 30] = np.inf
    with pytest.raises(ValueError, match="Infinite"):
        historical_price_context(changed, np.array([0]), np.array([60]))


def test_target_derived_metadata_and_unavailable_covariates_cannot_enter_feature_schema():
    metadata = pd.DataFrame(
        {
            "store_id": ["1"],
            "item_id": ["1"],
            "sales_units": [123],
            "pattern": ["smooth"],
            "validation_error": [9],
        }
    )
    first = FeatureEncoder(metadata, "store_item", "2013-01-01")
    metadata[["sales_units", "validation_error"]] = 1e9
    metadata["pattern"] = "future_outcome"
    second = FeatureEncoder(metadata, "store_item", "2013-01-01")
    assert first.metadata() == second.metadata()
    assert not {"sales_units", "pattern", "validation_error", "snap", "event"} & set(first.names)


def test_all_zero_observed_activity_keeps_undefined_adi_and_cv2():
    state = observed_context(np.zeros((1, 56)))
    assert state[0, 0] == state[0, 1] == 1
    assert state[0, 2] == 0 and np.isnan(state[0, 3:5]).all() and state[0, 5] == 56


def test_bounded_training_sampling_is_seeded_and_covers_every_series():
    rows, dates = training_positions(4, 100, 40, 42)
    second = training_positions(4, 100, 40, 42)
    np.testing.assert_array_equal(rows, second[0])
    np.testing.assert_array_equal(dates, second[1])
    assert set(rows) == {0, 1, 2, 3} and len(rows) == 40
    assert dates.min() >= 56 and dates.max() < 100
    assert len(set(zip(rows, dates, strict=True))) == 40
    with pytest.raises(ValueError, match="every eligible series"):
        training_positions(4, 100, 3, 42)


@pytest.mark.parametrize("dataset", ["store_item", "m5"])
def test_supervised_cache_contains_only_shifted_origin_safe_examples(tmp_path, dataset):
    source, fold = ml_source(tmp_path, dataset)
    view = source.at_origin(fold, ("s1", "s2"))
    x, y, encoder, manifest = training_matrix(
        view, 128, 42, tmp_path / "features", source.fingerprint
    )
    assert len(x) == len(y) == 128
    assert pd.Timestamp(manifest["target_max"]).date() <= fold.origin
    assert pd.Timestamp(manifest["max_source_date"]) < pd.Timestamp(manifest["target_max"])
    assert x.dtype == y.dtype == np.float32
    assert not x.flags.writeable
    encoder.validate(x)
    cached = training_matrix(view, 128, 42, tmp_path / "features", source.fingerprint)
    np.testing.assert_allclose(x, cached[0], equal_nan=True)


@pytest.mark.parametrize("method", ["random_forest", "lightgbm"])
@pytest.mark.parametrize("dataset", ["store_item", "m5"])
def test_global_model_future_actual_poison_invariance_and_native_persistence(
    tmp_path, method, dataset
):
    outputs = []
    for poison in (987654321, 123456789):
        source, fold = ml_source(tmp_path, dataset, poison)
        view = source.at_origin(fold, ("s1", "s2"))
        model = GlobalMLModel(method).fit(view, configuration(tmp_path, source))
        frame = pd.concat(
            model.predict(fold.origin, 28, view.calendar_features()), ignore_index=True
        )
        again = pd.concat(
            model.predict(fold.origin, 28, view.calendar_features()), ignore_index=True
        )
        pd.testing.assert_frame_equal(frame, again, rtol=1e-12, atol=1e-12)
        outputs.append(frame)
    pd.testing.assert_frame_equal(*outputs, rtol=1e-12, atol=1e-12)
    directory = tmp_path / f"saved-{method}"
    directory.mkdir()
    saved = model.save_artifacts(directory)
    assert saved["estimator"].exists() and saved["reload_validation"].exists()
    assert len(frame) == 56 and np.isfinite(frame.prediction).all()


def test_recursive_lags_use_predictions_and_observed_activity_remains_frozen(tmp_path, monkeypatch):
    source, fold = ml_source(tmp_path)
    view = source.at_origin(fold, ("s1", "s2"))
    model = GlobalMLModel("random_forest").fit(view, configuration(tmp_path, source))
    trace = []

    def predict(matrix):
        trace.append(matrix.copy())
        return matrix[:, model.encoder.names.index("lag_1")].astype(float) + 1

    monkeypatch.setattr(model, "_model_predict", predict)
    frame = pd.concat(model.predict(fold.origin, 28, view.calendar_features()), ignore_index=True)
    np.testing.assert_array_equal(frame.query("series_id == 's2'").prediction, np.arange(1.0, 29.0))
    assert trace[7][1, model.encoder.names.index("lag_7")] == 1
    assert trace[14][1, model.encoder.names.index("lag_14")] == 1
    assert trace[27][1, model.encoder.names.index("lag_28")] == 0
    assert all(row[1, model.encoder.names.index("obs_zero_fraction28")] == 1 for row in trace)


def test_nonfinite_global_forecast_falls_back_for_entire_series_window(tmp_path, monkeypatch):
    source, fold = ml_source(tmp_path)
    view = source.at_origin(fold, ("s1", "s2"))
    model = GlobalMLModel("random_forest").fit(view, configuration(tmp_path, source))
    steps = [0]

    def predict(matrix):
        steps[0] += 1
        result = matrix[:, 0].astype(float) + 1
        if steps[0] == 3:
            result[0] = np.nan
        return result

    monkeypatch.setattr(model, "_model_predict", predict)
    frame = pd.concat(model.predict(fold.origin, 28, view.calendar_features()), ignore_index=True)
    expected, _, _ = baseline_values(model.initial_history, "seasonal_naive")
    np.testing.assert_array_equal(frame.query("series_id == 's1'").prediction, expected[0])
    assert frame.query("series_id == 's1'").is_fallback.all()
    assert model.delivery.actual_method.iloc[0] == "seasonal_naive"
    assert "step_3" in model.delivery.reason.iloc[0]


@pytest.mark.parametrize("dataset", ["store_item", "m5"])
@pytest.mark.parametrize("corruption", [None, "labels", "features", "positions"])
def test_independent_ml_audit_rejects_semantic_corruption_even_with_updated_hashes(
    tmp_path, dataset, corruption
):
    source, fold = ml_source(tmp_path, dataset)
    view = source.at_origin(fold, ("s1", "s2"))
    config = configuration(tmp_path, source)
    model = GlobalMLModel("lightgbm").fit(view, config)
    directory = tmp_path / "persisted"
    directory.mkdir()
    paths = model.save_artifacts(directory)
    atomic_json(directory / "metadata.json", [model.metadata()])
    state = {
        "specification": {
            "model_configuration": config,
            "random_seed": 42,
            "source_fingerprint": source.fingerprint,
            "dataset_id": dataset,
            "fold": json.loads(json.dumps(asdict(fold), default=str)),
        },
        "outputs": {
            **{f"model_0_{k}": {"path": p.name} for k, p in paths.items()},
            "model_metadata": {"path": "metadata.json"},
        },
    }
    if corruption:
        cache = Path(config["feature_cache"]) / identity(model.manifest["contract"])
        manifest = model.manifest
        name = manifest["names"][corruption]
        array = np.load(cache / name, mmap_mode="r+")
        if corruption == "positions":
            array[0, 1] = len(panel_from_view(view).dates)
        elif corruption == "features":
            array[0, 0] += 123
        else:
            array[0] += 123
        array.flush()
        del array
        manifest["files"][name] = file_digest(cache / name)
        atomic_json(cache / "complete.json", manifest)
        with pytest.raises(ValueError, match="historical|features|feature|labels"):
            audit_ml_training(state, directory, panel_from_view(view))
    else:
        result = audit_ml_training(state, directory, panel_from_view(view))
        assert result["source_labels_and_all_features_reconciled"]
        assert result["training_rows"] == 128
