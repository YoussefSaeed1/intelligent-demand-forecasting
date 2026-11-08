"""Frozen tuning design, price-free features, and pre-freeze holdout-firewall tests."""

import copy
import json
from datetime import date

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from test_ml_forecasting import configuration, ml_source

from intelligent_demand.evaluation.splits import validate_fold
from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.data import OriginData, ParquetSource
from intelligent_demand.experiments.registry import file_digest
from intelligent_demand.models.global_ml import GlobalMLModel
from intelligent_demand.tuning import authority, plan


def test_search_is_seeded_unique_bounded_and_invariant_to_json_key_order():
    settings = plan.load_settings()
    left = plan.build_trials(settings)
    right = plan.build_trials(json.loads(json.dumps(settings, sort_keys=True)))
    assert left == right and len(left) == 27
    assert sum(row["kind"] == "tuning" for row in left) == 23
    for dataset in ("store_item", "m5"):
        for method, count in settings["trial_counts"][dataset].items():
            rows = [r for r in left if r["dataset"] == dataset and r["model"] == method]
            assert len(rows) == count and len({r["configuration_sha256"] for r in rows}) == count
            assert all(r["parameters"].get("use_historical_prices", False) is False for r in rows)


@pytest.mark.parametrize(
    "violation",
    [
        "seed",
        "price_features",
        "horizon",
        "folds",
        "primary_metric",
        "training_rows",
        "resources",
        "trial_counts",
        "selection",
        "unknown_axis",
        "bad_axis_value",
    ],
)
def test_invalid_search_contract_cannot_start_tuning(tmp_path, violation):
    settings = copy.deepcopy(plan.load_settings())
    if violation == "seed":
        settings["seed"] = 7
    elif violation == "price_features":
        settings[violation] = True
    elif violation == "horizon":
        settings[violation] = 1
    elif violation == "folds":
        settings[violation] = [1]
    elif violation == "primary_metric":
        settings[violation] = "holdout_mae"
    elif violation == "training_rows":
        settings[violation]["m5"] = 100
    elif violation == "resources":
        settings[violation]["concurrent_workers"] = 4
    elif violation == "trial_counts":
        settings[violation]["m5"]["random_forest"] = 31
    elif violation == "selection":
        settings[violation]["objective_tie_tolerance"] = 0.1
    elif violation == "unknown_axis":
        settings["spaces"]["lightgbm"]["future_price"] = [1]
    else:
        settings["spaces"]["random_forest"]["n_estimators"] = [99999]
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(settings))
    with pytest.raises(ValueError):
        plan.load_settings(path)


def test_exclusive_freeze_publication_never_overwrites_existing_contract(tmp_path):
    path = tmp_path / "frozen.json"
    plan.publish_once(path, {"selected": "original"})
    with pytest.raises(FileExistsError):
        plan.publish_once(path, {"selected": "changed"})
    assert json.loads(path.read_text()) == {"selected": "original"}


@pytest.mark.parametrize("method", ["random_forest", "lightgbm"])
def test_availability_safe_m5_forecasts_ignore_all_historical_and_future_prices(tmp_path, method):
    outputs = []
    for number, price in enumerate((2.5, 999999.0)):
        directory = tmp_path / str(number)
        directory.mkdir()
        source, fold = ml_source(directory, "m5")
        schema = pq.read_schema(source.path)
        frame = pd.read_parquet(source.path)
        frame["unit_price"] = price
        pq.write_table(
            pa.Table.from_pandas(frame, schema=schema, preserve_index=False), source.path
        )
        source.fingerprint = file_digest(source.path)
        settings = configuration(directory, source)
        settings["parameters"] = plan.parameters_for(method)
        view = source.at_origin(fold, ("s1", "s2"))
        model = GlobalMLModel(method).fit(view, settings)
        assert model.metadata()["feature_count"] == 30 and model.prices is None
        assert model.encoder.metadata()["price_policy"] == "excluded_availability_safe"
        assert not any("price" in name for name in model.encoder.names)
        outputs.append(pd.concat(model.predict(fold.origin, 28, view.calendar_features())))
    pd.testing.assert_frame_equal(*outputs, rtol=1e-12, atol=1e-12)
    assert np.isfinite(outputs[0].prediction).all()


def grant(tmp_path, monkeypatch):
    monkeypatch.setattr(authority, "OUTPUT", tmp_path / "phase4")
    monkeypatch.setattr(authority, "REPORTS", tmp_path / "reports")
    authority.REPORTS.mkdir()
    gate = {
        "status": "passed",
        "quality_checks_passed": True,
        "holdout_targets_accessed": False,
        "plan_sha256": "p" * 64,
    }
    gate_path = authority.REPORTS / "phase4b_gate.json"
    gate_path.write_text(json.dumps(gate))
    record = {
        "datasets": {"store_item": {"origin": "2017-12-03"}, "m5": {"origin": "2016-04-24"}},
        "plan_sha256": "p" * 64,
        "phase4b_gate_sha256": file_digest(gate_path),
    }
    record["manifest_sha256"] = identity(record)
    plan.publish_once(authority.OUTPUT / "frozen_selection.json", record)
    return record


def make_final(record):
    return authority.FinalFold(
        "store_item",
        0,
        date(2013, 1, 1),
        date(2017, 12, 3),
        date(2017, 12, 4),
        date(2017, 12, 31),
        date(2017, 12, 4),
        record["manifest_sha256"],
    )


def test_final_capability_cannot_exist_before_a_passed_tuning_gate_and_selection(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(authority, "OUTPUT", tmp_path)
    with pytest.raises(FileNotFoundError):
        make_final({"manifest_sha256": "a" * 64})


def test_authorised_final_origin_still_cannot_use_the_ordinary_target_reader(tmp_path, monkeypatch):
    record = grant(tmp_path, monkeypatch)
    fold = make_final(record)
    validate_fold(fold)
    source = ParquetSource(tmp_path / "unread.parquet", "store_item")
    with pytest.raises(ValueError, match="protected final holdout"):
        list(source.validation_targets(fold, ("s1",)))
    view = source.at_origin(fold, ("s1",))
    with pytest.raises(ValueError, match="past the forecast origin"):
        list(view.history(end=fold.holdout_start))


def test_changed_freeze_or_tuning_gate_revokes_final_capability(tmp_path, monkeypatch):
    record = grant(tmp_path, monkeypatch)
    path = authority.OUTPUT / "frozen_selection.json"
    content = json.loads(path.read_text())
    content["datasets"]["store_item"]["origin"] = "2017-12-04"
    path.write_text(json.dumps(content))
    with pytest.raises(ValueError, match="changed"):
        make_final(record)


def test_append_only_ledger_rejects_tampering_and_blocks_post_access_training(
    tmp_path, monkeypatch
):
    record = grant(tmp_path, monkeypatch)
    fold = make_final(record)
    authority.append_access("canonical_targets_read_started", "store_item")
    source = ParquetSource(tmp_path / "never_read.parquet", "store_item")
    with pytest.raises(ValueError, match="refitting/regenerating"):
        OriginData(source, fold, ("s1",))
    authority.append_access("canonical_targets_read_completed", "store_item")
    assert len(authority.ledger_events()) == 2
    path = authority.OUTPUT / "holdout_access.jsonl"
    content = path.read_text().replace("read_started", "read_changed")
    path.write_text(content)
    with pytest.raises(ValueError, match="changed or reordered"):
        authority.ledger_events()
