"""Synthetic-only infrastructure contracts; no forecasting method or real benchmark."""

import json
from dataclasses import asdict, replace
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

from intelligent_demand.evaluation.metrics import scaling_denominators
from intelligent_demand.evaluation.predictions import PredictionWriter, validate_prediction_frame
from intelligent_demand.evaluation.scoring import score_predictions, training_scales
from intelligent_demand.evaluation.splits import load_splits
from intelligent_demand.experiments.config import (
    canonical_json,
    identity,
    load_experiment_config,
)
from intelligent_demand.experiments.data import (
    Availability,
    LeakageError,
    OriginData,
    ParquetSource,
    validate_future_features,
    validate_training_feature_lineage,
)
from intelligent_demand.experiments.engine import execute_validation, experiment_specification
from intelligent_demand.experiments.registry import ExperimentRegistry, atomic_json, file_digest
from intelligent_demand.models.base import ForecastModel, ModelInfo, ModelRegistry

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reports/eda/proposed_splits.json"


@pytest.fixture
def fold():
    return load_splits(MANIFEST)["store_item"][0]


@pytest.fixture
def config(tmp_path):
    return replace(
        load_experiment_config(ROOT / "configs/forecasting.yaml"),
        registry_directory=tmp_path / "runs",
        batch_rows=137,
    )


@pytest.fixture
def source(tmp_path, fold):
    dates = pd.date_range(fold.train_start, fold.validation_end)
    parts = []
    for number, key in enumerate(("s1", "s2")):
        parts.append(
            pd.DataFrame(
                {
                    "dataset_id": "store_item",
                    "series_id": key,
                    "date": dates,
                    "sales_units": np.arange(len(dates)) % 9 if number == 0 else 0.0,
                    "unit_price": 2.0,
                    "store_id": str(number + 1),
                    "item_id": "1",
                    "category_id": "fixture",
                    "is_observed": True,
                }
            )
        )
    frame = pd.concat(parts, ignore_index=True)
    poison = frame.iloc[[0]].copy()
    poison["date"], poison["sales_units"] = pd.Timestamp(fold.holdout_start), 987654321.0
    frame = pd.concat([frame, poison], ignore_index=True)
    path = tmp_path / "fixture.parquet"
    schema = pa.Schema.from_pandas(frame, preserve_index=False).set(
        2, pa.field("date", pa.date32())
    )
    pq.write_table(
        pa.Table.from_pandas(frame, schema=schema, preserve_index=False), path, row_group_size=257
    )
    return ParquetSource(path, "store_item", batch_rows=113)


def forecast_fixture(fold, series=("s1", "s2"), value=1.0):
    work = pd.MultiIndex.from_product(
        [series, pd.to_datetime(fold.dates)], names=["series_id", "target_date"]
    ).to_frame(index=False)
    work["prediction"] = value
    return work


def evaluation_fixture(fold):
    predicted = forecast_fixture(fold)
    predicted["dataset_id"] = fold.dataset_id
    actual = predicted.drop(columns="prediction").copy()
    actual["actual"] = np.where(actual.series_id.eq("s1"), 2.0, 0.0)
    scales = pd.DataFrame(
        {"series_id": ["s1", "s2"], "scale_absolute": [2.0, np.nan], "scale_squared": [4.0, np.nan]}
    )
    scales["dataset_id"] = fold.dataset_id
    scales["training_start"] = fold.train_start
    scales["training_end"] = fold.origin
    scales["season_days"] = 7
    return actual, predicted, scales


def test_saved_split_manifest_exact_dates_and_leap_day():
    plans = load_splits(MANIFEST)
    assert len(plans["store_item"]) == len(plans["m5"]) == 4
    for name, folds in plans.items():
        for first, second in zip(folds, folds[1:], strict=False):
            assert first.validation_end + timedelta(days=1) == second.validation_start
        for item in folds:
            assert item.horizon == len(item.dates) == 28
            assert item.validation_end < item.holdout_start
            assert item.dates[0] == item.origin + timedelta(days=1)
        assert folds[-1].validation_end + timedelta(days=1) == folds[-1].holdout_start
        assert folds[-1].holdout_start == (
            date(2017, 12, 4) if name == "store_item" else date(2016, 4, 25)
        )
    assert plans["m5"][2].validation_start == date(2016, 2, 29)


@pytest.mark.parametrize("change", ["origin", "holdout", "dataset", "horizon"])
def test_split_manifest_rejects_protocol_drift(tmp_path, change):
    raw = json.loads(MANIFEST.read_text())
    if change == "origin":
        raw["m5"]["validation_folds"][0]["origin"] = "2016-01-04"
    elif change == "holdout":
        raw["store_item"]["test_start"] = "2017-12-05"
    elif change == "dataset":
        raw.pop("m5")
    else:
        raw["m5"]["horizon_days"] = 27
    path = tmp_path / "splits.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_splits(path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("horizon_days", 27),
        ("season_days", 1),
        ("batch_rows", 0),
        ("max_workers", 3),
        ("max_threads", 8),
        ("random_seed", True),
        ("nonnegative_predictions", False),
        ("schema_version", 2),
        ("extra", 1),
        ("registry_directory", "../escape"),
    ],
)
def test_experiment_config_rejects_invalid_or_unapproved_settings(tmp_path, field, value):
    raw = yaml.safe_load((ROOT / "configs/forecasting.yaml").read_text())
    raw[field] = value
    path = tmp_path / "configs/bad.yaml"
    path.parent.mkdir()
    path.write_text(yaml.safe_dump(raw))
    manifest = tmp_path / "reports/eda/proposed_splits.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(MANIFEST.read_text())
    with pytest.raises(ValueError):
        load_experiment_config(path)


def test_origin_projection_batches_and_poison_holdout_is_invisible(source, fold):
    view = source.at_origin(fold, ("s1", "s2"))
    batches = list(view.history())
    assert max(map(len, batches)) <= 113
    frame = pd.concat(batches)
    assert set(frame.columns) == {"dataset_id", "series_id", "date", "sales_units"}
    assert frame.date.max() == pd.Timestamp(fold.origin)
    assert frame.sales_units.max() < 987654321
    assert len(frame) == 2 * ((fold.origin - fold.train_start).days + 1)
    assert set(view.static_metadata().series_id) == {"s1", "s2"}


def test_future_target_access_fails_before_any_scan(source, fold, monkeypatch):
    view = source.at_origin(fold, ("s1",))
    monkeypatch.setattr(
        source, "_read", lambda *a, **k: pytest.fail("Future request reached scanner")
    )
    with pytest.raises(LeakageError):
        view.history(end=fold.origin + timedelta(days=1))
    with pytest.raises(LeakageError):
        view.history(columns=["actual"])
    with pytest.raises(LeakageError):
        view.for_series("unknown")


def test_source_refuses_even_direct_holdout_window(source, fold):
    with pytest.raises(LeakageError):
        list(source._read(fold, fold.holdout_start, fold.holdout_start, ["sales_units"], ("s1",)))


def test_calendar_is_complete_origin_safe_and_does_not_contain_sales(source, fold):
    view = source.at_origin(fold, ("s1", "s2"))
    features = view.calendar_features()
    assert len(features) == 56
    assert features.horizon_step.min() == 1 and features.horizon_step.max() == 28
    assert not set(features) & {"sales_units", "actual", "unit_price"}
    assert features.weekday.between(0, 6).all()


@pytest.mark.parametrize(
    "violation",
    [
        "actual",
        "unknown_price",
        "late_publication",
        "observed_future",
        "missing_key",
        "duplicate",
        "extra_series",
    ],
)
def test_future_covariate_leakage_and_bad_joins_fail(source, fold, violation):
    features = source.at_origin(fold, ("s1",)).calendar_features()
    rules = features.attrs["availability"].copy()
    if violation == "actual":
        features["actual"] = 1
    elif violation in ("unknown_price", "late_publication", "observed_future"):
        features["unit_price"] = 2
        if violation != "unknown_price":
            rules["unit_price"] = Availability(
                "known_future" if violation == "late_publication" else "observed",
                fold.origin + timedelta(days=1) if violation == "late_publication" else fold.origin,
                "fixture evidence",
            )
    elif violation == "missing_key":
        features = features.iloc[:-1]
    elif violation == "duplicate":
        features = pd.concat([features.iloc[:1], features.iloc[:-1]])
    else:
        features.loc[0, "series_id"] = "extra"
    with pytest.raises(LeakageError):
        validate_future_features(features, fold, ("s1",), rules)


def test_explicit_published_covariates_require_evidence(source, fold):
    features = source.at_origin(fold, ("s1",)).calendar_features()
    features["planned_event"] = "known"
    rules = features.attrs["availability"] | {
        "planned_event": Availability("known_future", fold.origin, "Published schedule fixture")
    }
    assert "planned_event" in validate_future_features(features, fold, ("s1",), rules)
    rules["planned_event"] = Availability("known_future", fold.origin, "")
    with pytest.raises(LeakageError):
        validate_future_features(features, fold, ("s1",), rules)


def test_streaming_scales_match_array_definition_and_zero_history(source, fold):
    view = source.at_origin(fold, ("s1", "s2"))
    scales = training_scales(view.history(), fold, view.series).set_index("series_id")
    history = pd.concat(view.for_series("s1").history())
    expected = scaling_denominators(history.sales_units.to_numpy(), 7)
    assert scales.loc["s1", "scale_absolute"] == pytest.approx(expected[0])
    assert scales.loc["s1", "scale_squared"] == pytest.approx(expected[1])
    assert scales.loc["s2", ["scale_absolute", "scale_squared"]].isna().all()


@pytest.mark.parametrize("violation", ["future", "gap", "reorder", "negative"])
def test_scaling_rejects_leakage_and_incomplete_training(source, fold, violation):
    history = pd.concat(source.at_origin(fold, ("s1",)).history(), ignore_index=True)
    if violation == "future":
        history.loc[len(history) - 1, "date"] = pd.Timestamp(fold.origin + timedelta(days=1))
    elif violation == "gap":
        history = history.iloc[1:]
    elif violation == "reorder":
        history = history.iloc[::-1]
    else:
        history.loc[0, "sales_units"] = -1
    with pytest.raises(ValueError):
        training_scales([history], fold, ("s1",))


@pytest.mark.parametrize("season", [0, True, 1.5])
def test_scale_season_must_be_positive_integer(season):
    with pytest.raises(ValueError):
        scaling_denominators(np.arange(10), season)


def test_metrics_macro_pooled_and_undefined_coverage(fold):
    actual, predicted, scales = evaluation_fixture(fold)
    result = score_predictions(
        actual,
        predicted,
        scales,
        fold,
        ("s1", "s2"),
        {"s1": "smooth", "s2": "all_zero"},
        fold.origin,
    )
    assert result["all"]["pooled"]["mae"] == 1
    assert result["all"]["pooled"]["rmse"] == 1
    assert result["all"]["pooled"]["wape_percent"] == 100
    assert result["all"]["macro"]["wape_percent"] == 50
    assert result["all"]["macro"]["mase"] == 0.5
    assert result["all"]["coverage"]["undefined_series"]["mase"] == 1
    assert len(result["by_horizon"]) == 28 and len(result["by_demand_class"]) == 2
    assert result["by_demand_class"]["all_zero"]["pooled"]["wape_percent"] is None
    canonical_json(result)


def test_macro_rmse_is_not_pooled_root(fold):
    actual, predicted, scales = evaluation_fixture(fold)
    predicted["prediction"] = 0.0
    result = score_predictions(actual, predicted, scales, fold, ("s1", "s2"))
    assert result["all"]["macro"]["rmse"] == 1
    assert result["all"]["pooled"]["rmse"] == pytest.approx(np.sqrt(2))


@pytest.mark.parametrize(
    "violation", ["missing", "extra", "duplicate", "nan", "dataset", "holdout", "origin", "step"]
)
def test_prediction_alignment_rejects_incompatible_population(fold, violation):
    actual, predicted, scales = evaluation_fixture(fold)
    if violation == "missing":
        predicted = predicted.iloc[:-1]
    elif violation == "extra":
        predicted.loc[0, "series_id"] = "extra"
    elif violation == "duplicate":
        predicted.loc[1, "target_date"] = predicted.target_date.iloc[0]
    elif violation == "nan":
        predicted.loc[0, "prediction"] = np.nan
    elif violation == "dataset":
        predicted.loc[0, "dataset_id"] = "m5"
    elif violation == "holdout":
        actual.loc[0, "target_date"] = pd.Timestamp(fold.holdout_start)
    elif violation == "origin":
        predicted["forecast_origin"] = pd.Timestamp(fold.origin + timedelta(days=1))
    else:
        predicted["horizon_step"] = 99
    with pytest.raises(ValueError):
        score_predictions(actual, predicted, scales, fold, ("s1", "s2"))


def test_class_labels_cannot_come_from_future_or_missing_series(fold):
    actual, predicted, scales = evaluation_fixture(fold)
    with pytest.raises(ValueError):
        score_predictions(
            actual,
            predicted,
            scales,
            fold,
            ("s1", "s2"),
            {"s1": "smooth", "s2": "smooth"},
            fold.origin + timedelta(days=1),
        )


def test_prediction_publication_is_complete_and_retains_raw_clipping(tmp_path, fold):
    info = ModelInfo("fixture", "1", "global")
    writer = PredictionWriter(tmp_path / "predictions.parquet", fold, ("s1", "s2"), info, "run", 11)
    writer.write(forecast_fixture(fold, value=-2))
    assert not writer.path.exists()
    assert writer.finish()["rows"] == 56
    output = pd.read_parquet(writer.path)
    assert output.prediction.eq(0).all() and output.raw_prediction.eq(-2).all()
    assert output.was_clipped.all() and output.horizon_step.max() == 28
    with pytest.raises(FileExistsError):
        PredictionWriter(writer.path, fold, ("s1", "s2"), info, "run")


def test_partial_predictions_are_not_published_and_duplicates_cross_batches_fail(tmp_path, fold):
    writer = PredictionWriter(
        tmp_path / "predictions.parquet", fold, ("s1",), ModelInfo("fixture", "1", "local"), "run"
    )
    one = forecast_fixture(fold, ("s1",)).iloc[:1]
    writer.write(one)
    with pytest.raises(ValueError, match="Duplicate"):
        writer.write(one)
    with pytest.raises(ValueError, match="Incomplete"):
        writer.finish()
    assert writer.partial.exists() and not writer.path.exists()


class FixtureModel(ForecastModel):
    """Prewritten test output only: this class does not learn a forecasting method."""

    def __init__(self, info, calls, failure=None):
        super().__init__(info)
        self.calls, self.failure = calls, failure

    def _fit(self, training_data, configuration):
        self.calls.append(("fit_hook", training_data.fold.origin, training_data.series))
        if self.failure is not None:
            raise self.failure

    def _predict(self, forecast_origin, horizon, available_features):
        self.calls.append(("predict_hook", forecast_origin))
        result = available_features[["series_id", "target_date"]].copy()
        result["prediction"] = 1.0  # Fixed fixture payload, not a fitted forecasting rule.
        return result


def fixture_models(scope="global", failure=None):
    info, calls, models = ModelInfo("fixture_only", "test", scope), [], ModelRegistry()
    models.register(info, lambda: FixtureModel(info, calls, failure))
    return info, calls, models


def test_model_interface_requires_fresh_origin_and_future_feature_gate(source, fold):
    info, calls, models = fixture_models()
    assert not ModelRegistry().registered()
    with pytest.raises(TypeError):
        ForecastModel(info)
    view = source.at_origin(fold, ("s1",))
    model = models.create(info.identifier, info.version)
    with pytest.raises(ValueError):
        model.predict(fold.origin, 28, view.calendar_features())
    model.fit(view, {"seed": 42})
    with pytest.raises(ValueError):
        model.fit(view, {})
    features = view.calendar_features()
    features["actual"] = 100
    with pytest.raises(LeakageError):
        model.predict(fold.origin, 28, features)
    with pytest.raises(ValueError):
        model.predict(fold.origin, 1, view.calendar_features())
    with pytest.raises(ValueError):
        models.register(info, lambda: model)
    assert model.metadata()["configuration_json"] == '{"seed":42}'


@pytest.mark.parametrize("scope,fit_calls", [("global", 1), ("local", 2)])
def test_fixture_only_engine_seals_predictions_before_targets(
    source, fold, config, monkeypatch, scope, fit_calls
):
    info, calls, models = fixture_models(scope)
    registry = ExperimentRegistry(config.registry_directory)
    original = source.validation_targets

    def guarded_targets(*args):
        assert len(list(config.registry_directory.rglob("predictions.parquet"))) == 1
        return original(*args)

    monkeypatch.setattr(source, "validation_targets", guarded_targets)
    kwargs = dict(
        config=config,
        fold=fold,
        source=source,
        series=("s1", "s2"),
        models=models,
        model_info=info,
        model_config={},
        registry=registry,
        source_fingerprint=file_digest(source.path),
        code_metadata={"git_revision": "f" * 40},
    )
    result = execute_validation(**kwargs)
    assert result["status"] == "completed"
    assert sum(row[0] == "fit_hook" for row in calls) == fit_calls
    before = len(calls)
    assert execute_validation(**kwargs, run_id=result["run_id"])["status"] == "completed"
    assert len(calls) == before
    assert len(list(config.registry_directory.rglob("predictions.parquet"))) == 1


@pytest.mark.parametrize(
    "failure,status", [(ValueError("fixture"), "failed"), (KeyboardInterrupt(), "interrupted")]
)
def test_failed_interrupted_runs_restart_new_attempt_without_partial_reuse(
    source, fold, config, failure, status
):
    info, calls, models = fixture_models(failure=failure)
    registry = ExperimentRegistry(config.registry_directory)
    kwargs = dict(
        config=config,
        fold=fold,
        source=source,
        series=("s1", "s2"),
        models=models,
        model_info=info,
        model_config={},
        registry=registry,
        source_fingerprint=file_digest(source.path),
        code_metadata={"git_revision": "f" * 40},
    )
    with pytest.raises(type(failure)):
        execute_validation(**kwargs)
    run_id = next(config.registry_directory.iterdir()).name
    state = registry.read(run_id)
    assert state["status"] == status
    assert list(config.registry_directory.rglob("*.part"))
    with pytest.raises(ValueError):
        registry.completed(run_id)
    _, _, healthy = fixture_models()
    kwargs["models"] = healthy
    completed = execute_validation(**kwargs, run_id=run_id, resume=True)
    assert completed["status"] == "completed" and len(completed["attempts"]) == 2
    assert len(list(config.registry_directory.rglob("*.part"))) == 1


def test_registry_pending_specification_identity_and_lock_protection(tmp_path):
    registry = ExperimentRegistry(tmp_path / "registry")
    specification = {"dataset": "fixture", "seed": 42}
    run_id = registry.create(specification)
    assert registry.read(run_id)["status"] == "pending"
    assert identity({"b": 2, "a": 1}) == identity({"a": 1, "b": 2})
    with registry.attempt(run_id, specification):
        with pytest.raises(RuntimeError):
            with registry.attempt(run_id, specification):
                pytest.fail("Concurrent attempt acquired an owned lock")
        with pytest.raises(ValueError):
            registry.recover_interrupted(run_id, expected_owner_token="wrong")
        # Complete a fixture transaction with small text files; no real experiment outputs.
        state = registry.read(run_id)
        attempt = registry.directory(run_id) / "attempts" / state["attempt_id"]
        outputs = {}
        for name in ("predictions", "metrics", "model_metadata"):
            file = attempt / (name + ".json")
            atomic_json(file, {"git_revision": "f" * 40})
            outputs[name] = file
        registry.complete(run_id, attempt, outputs)
    assert registry.completed(run_id)["status"] == "completed"
    outputs["metrics"].write_text("changed")
    with pytest.raises(ValueError):
        registry.completed(run_id)


def test_registry_does_not_resume_changed_spec_or_accept_path_escape(tmp_path):
    registry = ExperimentRegistry(tmp_path / "registry")
    run_id = registry.create({"seed": 42})
    with pytest.raises(ValueError):
        with registry.attempt(run_id, {"seed": 43}, resume=True):
            pytest.fail("Changed specification resumed")
    with pytest.raises(ValueError):
        registry.directory("../escape")


def test_deterministic_experiment_specification(config, fold):
    info = ModelInfo("fixture", "1", "global")
    first = experiment_specification(
        config, fold, info, {"a": 1, "b": 2}, ("s2", "s1"), "a" * 64, {"git_revision": "f" * 40}
    )
    second = experiment_specification(
        config, fold, info, {"b": 2, "a": 1}, ("s1", "s2"), "a" * 64, {"git_revision": "f" * 40}
    )
    assert identity(first) == identity(second)


def test_readonly_cli_smoke_plan_models_and_no_implicit_training(monkeypatch, capsys):
    from intelligent_demand.__main__ import main

    for command in ("forecast-plan", "forecast-models"):
        monkeypatch.setattr(
            "sys.argv",
            [
                "demand-check",
                "--config",
                str(ROOT / "configs/default.yaml"),
                command,
                "--settings",
                str(ROOT / "configs/forecasting.yaml"),
            ],
        )
        main()
        value = json.loads(capsys.readouterr().out)
        assert value["models_executed"] == 0
        if command == "forecast-plan":
            assert all(len(folds) == 4 for folds in value["validation_folds"].values())
        else:
            assert value["registered_models"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("training_end", date(2017, 12, 31)),
        ("training_start", date(2014, 1, 1)),
        ("season_days", 1),
        ("dataset_id", "m5"),
    ],
)
def test_metric_scales_require_matching_training_window_provenance(fold, field, value):
    actual, predicted, scales = evaluation_fixture(fold)
    scales[field] = value
    with pytest.raises(ValueError, match="Scaling window"):
        score_predictions(actual, predicted, scales, fold, ("s1", "s2"))


def test_no_repeated_per_series_payload_in_horizon_and_class_summaries(fold):
    actual, predicted, scales = evaluation_fixture(fold)
    scored = score_predictions(actual, predicted, scales, fold, ("s1", "s2"))
    assert len(scored["all"]["per_series"]) == 2
    assert all("per_series" not in value for value in scored["by_horizon"].values())
    assert all("per_series" not in value for value in scored["by_demand_class"].values())


def test_resume_rejects_changed_fingerprint_before_calling_model(source, fold, config):
    info, calls, models = fixture_models()
    registry = ExperimentRegistry(config.registry_directory)
    with pytest.raises(ValueError, match="fingerprint"):
        execute_validation(
            config=config,
            fold=fold,
            source=source,
            series=("s1", "s2"),
            models=models,
            model_info=info,
            model_config={},
            registry=registry,
            source_fingerprint="a" * 64,
            code_metadata={"git_revision": "f" * 40},
        )
    assert calls == []
    state = registry.read(next(config.registry_directory.iterdir()).name)
    assert state["status"] == "failed"


def test_hard_kill_recovery_requires_explicit_matching_stopped_owner(tmp_path):
    registry = ExperimentRegistry(tmp_path / "registry")
    run_id = registry.create({"fixture": "abandoned attempt"})
    directory = registry.directory(run_id)
    state = registry.read(run_id)
    state.pop("specification")
    state.update(status="running", owner_token="fixture-dead-owner", owner_pid=99999999)
    atomic_json(directory / "status.json", state)
    atomic_json(directory / "execution.lock", {"token": "fixture-dead-owner", "pid": 99999999})
    with pytest.raises(ValueError):
        registry.recover_interrupted(run_id, expected_owner_token="fixture-dead-owner")
    with pytest.raises(ValueError):
        registry.recover_interrupted(
            run_id, expected_owner_token="wrong", owner_confirmed_stopped=True
        )
    registry.recover_interrupted(
        run_id, expected_owner_token="fixture-dead-owner", owner_confirmed_stopped=True
    )
    assert registry.read(run_id)["status"] == "interrupted"
    assert not (directory / "execution.lock").exists()


def test_model_factory_rejects_reused_fitted_model(source, fold):
    info, calls, models = fixture_models()
    fitted = models.create(info.identifier, info.version).fit(source.at_origin(fold, ("s1",)), {})
    other = ModelRegistry()
    other.register(info, lambda: fitted)
    with pytest.raises(ValueError, match="fresh"):
        other.create(info.identifier, info.version)


def test_model_seed_cannot_silently_override_experiment_policy(source, fold, config):
    info, calls, models = fixture_models()
    with pytest.raises(ValueError, match="override"):
        execute_validation(
            config=config,
            fold=fold,
            source=source,
            series=("s1", "s2"),
            models=models,
            model_info=info,
            model_config={"random_seed": 999},
            registry=ExperimentRegistry(config.registry_directory),
            source_fingerprint=file_digest(source.path),
            code_metadata={},
        )
    assert not config.registry_directory.exists() and calls == []


def test_missing_code_provenance_cannot_create_experiment(config, fold):
    with pytest.raises(ValueError, match="provenance"):
        experiment_specification(
            config, fold, ModelInfo("fixture", "1", "global"), {}, ("s1",), "a" * 64, {}
        )


def test_model_fit_cannot_bypass_origin_capability_with_raw_dataframe():
    info, calls, models = fixture_models()
    model = models.create(info.identifier, info.version)
    with pytest.raises(ValueError, match="capability"):
        model.fit(pd.DataFrame({"actual": [123]}), {})
    assert calls == []


def test_completed_result_is_not_reused_against_changed_source(source, fold, config):
    info, calls, models = fixture_models()
    registry = ExperimentRegistry(config.registry_directory)
    kwargs = dict(
        config=config,
        fold=fold,
        source=source,
        series=("s1", "s2"),
        models=models,
        model_info=info,
        model_config={},
        registry=registry,
        source_fingerprint=file_digest(source.path),
        code_metadata={"git_revision": "f" * 40},
    )
    completed = execute_validation(**kwargs)
    previous_calls = len(calls)
    with source.path.open("ab") as stream:
        stream.write(b"fixture mutation")
    with pytest.raises(ValueError, match="fingerprint"):
        execute_validation(**kwargs, run_id=completed["run_id"])
    assert len(calls) == previous_calls


def test_registry_refuses_output_path_escape_and_marks_attempt_failed(tmp_path):
    registry = ExperimentRegistry(tmp_path / "runs")
    spec = {"fixture": "path confinement"}
    run_id = registry.create(spec)
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    with pytest.raises(ValueError, match="attempt-local"):
        with registry.attempt(run_id, spec) as attempt:
            registry.complete(run_id, attempt, {"predictions": outside})
    assert registry.read(run_id)["status"] == "failed"


def test_training_row_history_excludes_the_contemporaneous_target(source, fold):
    view = source.at_origin(fold, ("s1",))
    history = pd.concat(view.history_before(fold.origin))
    assert history.date.max() == pd.Timestamp(fold.origin - timedelta(days=1))
    with pytest.raises(LeakageError):
        view.history_before(fold.validation_start)


@pytest.mark.parametrize("offset", [0, 1])
def test_unshifted_rolling_or_future_lag_lineage_fails(source, fold, offset):
    view = source.at_origin(fold, ("s1",))
    frame = pd.DataFrame(
        {
            "series_id": ["s1"],
            "target_date": [fold.origin],
            "max_source_date": [fold.origin + timedelta(days=offset)],
        }
    )
    with pytest.raises(LeakageError, match="strictly earlier"):
        validate_training_feature_lineage(frame, view)


def test_shifted_training_lineage_is_accepted_without_mutating_input(source, fold):
    view = source.at_origin(fold, ("s1",))
    frame = pd.DataFrame(
        {
            "series_id": ["s1"],
            "target_date": [fold.origin],
            "max_source_date": [fold.origin - timedelta(days=1)],
        }
    )
    result = validate_training_feature_lineage(frame, view)
    pd.testing.assert_frame_equal(result, frame)
    assert result is not frame


@pytest.mark.parametrize("dataset_id", ["store_item", "m5"])
@pytest.mark.parametrize("number", range(4))
def test_every_origin_filters_poison_future_and_protects_final_holdout(
    tmp_path, dataset_id, number
):
    boundary = load_splits(MANIFEST)[dataset_id][number]
    frame = pd.DataFrame({
        "dataset_id": [dataset_id] * 4,
        "series_id": ["s1"] * 4,
        "date": [boundary.origin - timedelta(days=1), boundary.origin,
                 boundary.validation_start, boundary.holdout_start],
        "sales_units": [3, 4, 987654321, 987654322],
    })
    schema = pa.schema([
        ("dataset_id", pa.string()), ("series_id", pa.string()),
        ("date", pa.date32()), ("sales_units", pa.int64()),
    ])
    path = tmp_path / "poison.parquet"
    pq.write_table(pa.Table.from_pandas(frame, schema=schema, preserve_index=False), path)
    reader = ParquetSource(path, dataset_id, batch_rows=1)
    visible = pd.concat(reader.at_origin(boundary, ("s1",)).history())
    assert visible.sales_units.tolist() == [3, 4]
    with pytest.raises(LeakageError):
        list(reader.at_origin(boundary, ("s1",)).history(end=boundary.validation_start))
    with pytest.raises(LeakageError):
        list(reader._read(boundary, boundary.origin, boundary.holdout_start,
                          ["sales_units"], ("s1",)))


@pytest.mark.parametrize("entry", ["source", "capability", "reader", "prediction", "scales"])
def test_forged_fold_cannot_change_public_access_boundaries(source, fold, tmp_path, entry):
    forged = SimpleNamespace(**asdict(fold))
    forged.origin = fold.holdout_start
    forged.holdout_start += timedelta(days=365)
    calls = {
        "source": lambda: source.at_origin(forged, ("s1",)),
        "capability": lambda: OriginData(source, forged, ("s1",)),
        "reader": lambda: list(source._read(forged, fold.origin, forged.origin,
                                            ["sales_units"], ("s1",))),
        "prediction": lambda: PredictionWriter(tmp_path / "bad.parquet", forged,
                                               ("s1",), ModelInfo("fixture", "1", "local"), "x"),
        "scales": lambda: training_scales([], forged, ("s1",)),
    }
    with pytest.raises(ValueError, match="ValidationFold"):
        calls[entry]()
    assert not (tmp_path / "bad.parquet.part").exists()


def test_mutated_fold_is_revalidated_before_a_model_visible_scan(source, fold):
    view = source.at_origin(fold, ("s1",))
    object.__setattr__(fold, "origin", fold.holdout_start)
    with pytest.raises(ValueError, match="frozen Phase 2"):
        list(view.history())


@pytest.mark.parametrize("null", [None, pd.NA])
def test_all_undefined_scales_and_zero_actuals_stay_json_null(fold, null):
    actual, predicted, scales = evaluation_fixture(fold)
    actual["actual"] = 0.0
    scales["scale_absolute"] = pd.Series([null, null], dtype=object)
    scales["scale_squared"] = pd.Series([null, null], dtype=object)
    original = scales.copy(deep=True)
    result = score_predictions(actual, predicted, scales, fold, ("s1", "s2"))
    for metric in ("mase", "rmsse", "wape_percent", "bias_percent"):
        assert result["all"]["macro"][metric] is None
        assert result["all"]["coverage"]["undefined_series"][metric] == 2
    canonical_json(result)
    pd.testing.assert_frame_equal(scales, original)


def completed_fixture_run(registry, specification):
    run_id = registry.create(specification)
    with registry.attempt(run_id, specification) as attempt:
        outputs = {}
        for name in ("predictions", "metrics", "model_metadata"):
            path = attempt / (name + ".json")
            atomic_json(path, {"fixture": True})
            outputs[name] = path
        registry.complete(run_id, attempt, outputs)
    return run_id


@pytest.mark.parametrize("mutation", ["empty", "missing", "unknown_attempt", "escaped_attempt",
                                       "partial", "missing_file", "malformed"])
def test_completed_manifest_requires_all_owned_outputs(tmp_path, mutation):
    registry = ExperimentRegistry(tmp_path)
    run_id = completed_fixture_run(registry, {"fixture": True})
    state = registry.read(run_id)
    state.pop("specification")
    if mutation == "empty":
        state["outputs"] = {}
    elif mutation == "missing":
        del state["outputs"]["metrics"]
    elif mutation in ("unknown_attempt", "escaped_attempt"):
        state["attempt_id"] = "0" * 32 if mutation == "unknown_attempt" else "../../escape"
    elif mutation == "partial":
        original = registry.directory(run_id) / state["outputs"]["metrics"]["path"]
        partial = original.with_suffix(".part")
        original.rename(partial)
        state["outputs"]["metrics"]["path"] = str(partial.relative_to(registry.directory(run_id)))
    elif mutation == "missing_file":
        (registry.directory(run_id) / state["outputs"]["metrics"]["path"]).unlink()
    else:
        state["outputs"]["metrics"] = {}
    atomic_json(registry.directory(run_id) / "status.json", state)
    with pytest.raises(ValueError):
        registry.completed(run_id)


@pytest.mark.parametrize("status", ["pending", "running", "failed", "interrupted"])
def test_incomplete_status_cannot_enter_comparison(tmp_path, status):
    registry = ExperimentRegistry(tmp_path)
    run_id = registry.create({"fixture": True})
    state = registry.read(run_id)
    state.pop("specification")
    state["status"] = status
    atomic_json(registry.directory(run_id) / "status.json", state)
    with pytest.raises(ValueError, match="no completed result"):
        registry.comparison_candidates([run_id])


@pytest.mark.parametrize("changed", [None, "series_sha256", "source_fingerprint", "protocol_sha256",
                                      "fold", "settings"])
def test_comparison_gate_accepts_only_verified_same_cohort(config, fold, tmp_path, changed):
    registry = ExperimentRegistry(tmp_path)
    spec = experiment_specification(config, fold, ModelInfo("fixture-a", "1", "global"), {},
                                    ("s1", "s2"), "a" * 64, {"git_revision": "fixture"})
    first = completed_fixture_run(registry, spec)
    other = json.loads(canonical_json(spec))
    other["model"]["identifier"] = "fixture-b"
    if changed is not None:
        other[changed] = "different"
    second = completed_fixture_run(registry, other)
    if changed is None:
        states = registry.comparison_candidates([first, second])
        assert [state["run_id"] for state in states] == [first, second]
    else:
        with pytest.raises(ValueError, match="matching protocol"):
            registry.comparison_candidates([first, second])


def test_failed_atomic_json_replace_preserves_previous_manifest(tmp_path, monkeypatch):
    path = tmp_path / "status.json"
    atomic_json(path, {"status": "running"})
    before = path.read_bytes()

    def fail(*args):
        raise OSError("injected publication failure")

    monkeypatch.setattr("intelligent_demand.experiments.registry.os.replace", fail)
    with pytest.raises(OSError, match="injected"):
        atomic_json(path, {"status": "completed"})
    assert path.read_bytes() == before
    assert list(tmp_path.glob("*.tmp"))


def test_failed_prediction_replace_never_publishes_final(tmp_path, fold, monkeypatch):
    path = tmp_path / "predictions.parquet"
    writer = PredictionWriter(path, fold, ("s1", "s2"), ModelInfo("fixture", "1", "global"), "x")
    writer.write(forecast_fixture(fold))
    sync_calls = []
    real_sync = __import__("os").fsync

    def sync(descriptor):
        sync_calls.append(descriptor)
        real_sync(descriptor)

    def fail(*args):
        raise OSError("injected publication failure")

    monkeypatch.setattr("intelligent_demand.evaluation.predictions.os.fsync", sync)
    monkeypatch.setattr("intelligent_demand.evaluation.predictions.os.replace", fail)
    with pytest.raises(OSError, match="injected"):
        writer.finish()
    assert sync_calls
    assert not path.exists()
    assert pq.ParquetFile(writer.partial).metadata.num_rows == 56


@pytest.mark.parametrize("dataset_id,population", [("store_item", 500), ("m5", 30490)])
def test_full_population_capacity_without_forecasts(tmp_path, config, dataset_id, population):
    boundary = load_splits(MANIFEST)[dataset_id][0]
    series = tuple(f"fixture-{i}" for i in range(population))
    writer = PredictionWriter(tmp_path / "capacity.parquet", boundary, series,
                              ModelInfo("fixture", "1", "global"), "x")
    try:
        assert writer.seen.size == population * 28 <= config.max_evaluation_rows
        assert writer.seen.nbytes < 1_000_000
        with pytest.raises(ValueError, match="Incomplete"):
            writer.finish()
        assert not writer.path.exists()
    finally:
        writer.close()


def test_boolean_predictions_are_not_sales_quantities(fold):
    with pytest.raises(ValueError, match="Finite numeric"):
        validate_prediction_frame(forecast_fixture(fold, value=True), fold, ("s1", "s2"))


@pytest.mark.parametrize("batch_rows", [0, -1, True, 1.5])
def test_invalid_batch_size_cannot_skip_prediction_validation(tmp_path, fold, batch_rows):
    with pytest.raises(ValueError, match="batch size"):
        PredictionWriter(tmp_path / "invalid.parquet", fold, ("s1",),
                         ModelInfo("fixture", "1", "local"), "x", batch_rows=batch_rows)


def test_equivalent_string_dates_cannot_disguise_duplicate_future_feature_keys(source, fold):
    features = source.at_origin(fold, ("s1",)).calendar_features()
    # Different timestamp spellings describe the same daily key after parsing.
    features["target_date"] = features.target_date.dt.strftime("%Y-%m-%d")
    day = fold.validation_start
    features.loc[1, "target_date"] = f"{day.year}-{day.month}-{day.day}"
    features.loc[1, "horizon_step"] = 1
    with pytest.raises(LeakageError, match="keys or dates"):
        validate_future_features(features, fold, ("s1",), features.attrs["availability"])


def test_failed_final_status_publication_cannot_enter_comparison(tmp_path, monkeypatch):
    registry = ExperimentRegistry(tmp_path)
    specification = {"fixture": True}
    run_id = registry.create(specification)
    real_atomic_json = atomic_json

    def fail_completion(path, value):
        if value.get("status") == "completed":
            raise OSError("injected completed manifest failure")
        real_atomic_json(path, value)

    monkeypatch.setattr("intelligent_demand.experiments.registry.atomic_json", fail_completion)
    with pytest.raises(OSError, match="manifest failure"):
        with registry.attempt(run_id, specification) as attempt:
            outputs = {}
            for name in ("predictions", "metrics", "model_metadata"):
                path = attempt / (name + ".json")
                atomic_json(path, {"fixture": True})
                outputs[name] = path
            registry.complete(run_id, attempt, outputs)
    assert registry.read(run_id)["status"] == "failed"
    assert not (registry.directory(run_id) / "execution.lock").exists()
    with pytest.raises(ValueError, match="no completed result"):
        registry.comparison_candidates([run_id])
