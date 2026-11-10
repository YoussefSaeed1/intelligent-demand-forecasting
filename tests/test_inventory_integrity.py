import json

import numpy as np
import pandas as pd
import pytest

from intelligent_demand.inventory import runner
from intelligent_demand.inventory.audit import equal, scalar_reference
from intelligent_demand.inventory.design import Scenario
from intelligent_demand.inventory.inputs import align, load_cohort
from intelligent_demand.preservation.backup import sha256


@pytest.mark.parametrize("status", ["running", "failed", "interrupted"])
def test_incomplete_inventory_cases_cannot_be_ranked(tmp_path, status):
    (tmp_path / "status.json").write_text(json.dumps({"status": status}))
    with pytest.raises(ValueError, match="Incomplete"):
        runner.completed(tmp_path)


def test_completed_resume_authenticates_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    target = tmp_path / "series.parquet"
    target.write_bytes(b"original fixture bytes")
    state = {
        "status": "completed",
        "files": {"series": {"path": target.name, "sha256": sha256(target)}},
    }
    (tmp_path / "status.json").write_text(json.dumps(state))
    assert runner.completed(tmp_path) == state
    target.write_bytes(b"changed fixture bytes")
    with pytest.raises(ValueError, match="changed"):
        runner.completed(tmp_path)


@pytest.mark.parametrize("defect", ["duplicate", "gap", "extra", "negative", "nan"])
def test_input_alignment_rejects_adversarial_keys_and_values(defect):
    frame = pd.DataFrame(
        {
            "series_id": ["a"] * 28,
            "target_date": pd.date_range("2020-01-02", periods=28),
            "prediction": np.ones(28),
        }
    )
    if defect == "duplicate":
        frame.loc[27, "target_date"] = frame.target_date.iloc[0]
    elif defect == "gap":
        frame = frame.iloc[:-1]
    elif defect == "extra":
        frame.loc[27, "series_id"] = "b"
    elif defect == "negative":
        frame.loc[1, "prediction"] = -1
    else:
        frame.loc[1, "prediction"] = np.nan
    with pytest.raises(ValueError):
        align(frame, pd.DataFrame({"series_id": ["a"]}), "2020-01-02", "prediction")


def test_final_period_rejected_before_any_target_scan(monkeypatch):
    from intelligent_demand.inventory import inputs

    monkeypatch.setattr(
        inputs,
        "read",
        lambda _: {
            "m5": {
                "validation_folds": [
                    {
                        "train_start": "2011-01-29",
                        "origin": "2016-02-28",
                        "validation_start": "2016-02-29",
                        "validation_end": "2016-03-27",
                    }
                ],
                "test_start": "2016-04-25",
            }
        },
    )
    monkeypatch.setattr(inputs.ds, "dataset", lambda *a, **k: pytest.fail("target scan invoked"))
    with pytest.raises(ValueError, match="Only the four"):
        load_cohort(
            {
                "dataset": "m5",
                "fold": {
                    "number": 1,
                    "train_start": "2011-01-29",
                    "origin": "2016-04-24",
                    "validation_start": "2016-04-25",
                    "validation_end": "2016-05-22",
                },
            }
        )


def test_separate_scalar_reference_hand_cost_and_tamper_detection():
    reference = scalar_reference(
        [2, 2, 2],
        2,
        np.array([2, 2, 2]),
        Scenario(horizon=3, lead_days=0, initial_cover_days=0, buffer_days=0),
        "selected_ml",
    )
    assert reference["total_cost"] == 22
    assert reference["received_units"] == 4
    with pytest.raises(ValueError, match="reconciliation"):
        equal(reference["total_cost"], 23, "altered saved cost")


@pytest.mark.parametrize("failure", [RuntimeError, KeyboardInterrupt])
def test_partial_publication_preserves_failed_attempt_and_resumes(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "OUTPUT", tmp_path / "inventory")
    monkeypatch.setattr(runner, "plan", lambda: {"settings": {"resources": {"batch_series": 1}}})
    monkeypatch.setattr(
        runner,
        "file_record",
        lambda path: {
            "path": path.relative_to(tmp_path).as_posix(),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        },
    )
    cohort = {
        "dataset": "fixture",
        "fold": {"number": 1, "origin": "2020-01-01", "validation_start": "2020-01-02"},
        "sources": {"selected_ml": {"fixture": True}},
        "representatives": ["a", "b"],
    }
    metadata = pd.DataFrame({"series_id": ["a", "b"]})
    data = (
        metadata,
        np.ones((2, 28)),
        np.ones(2),
        {"selected_ml": np.ones((2, 28))},
        {"selected_ml": 0},
    )
    contract = {"sha256": "synthetic-execution", "plan_sha256": "synthetic-plan"}
    settings = Scenario(lead_days=1)
    calls = 0

    def crash_after_first_batch():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise failure("simulated interruption after persisted partial batch")

    with pytest.raises(failure):
        runner.run_case(cohort, data, settings, "selected_ml", contract, crash_after_first_batch)
    key = runner.case_key(cohort, settings, "selected_ml", contract)
    directory = runner.OUTPUT / "runs" / key
    state = json.loads((directory / "status.json").read_text())
    assert state["status"] == ("interrupted" if failure is KeyboardInterrupt else "failed")
    partial = list(directory.glob("attempts/*/*.partial"))
    assert partial and "files" not in state
    with pytest.raises(ValueError, match="Incomplete"):
        runner.completed(directory)
    complete = runner.run_case(cohort, data, settings, "selected_ml", contract, lambda: None)
    assert complete["status"] == "completed" and len(complete["attempts"]) == 2
    assert complete["series"] == 2 and complete["event_rows"] == 56
    assert all(path.exists() for path in partial)
    reused = runner.run_case(
        cohort,
        data,
        settings,
        "selected_ml",
        contract,
        lambda: pytest.fail("completed result recomputed"),
    )
    assert reused == complete


def test_report_pools_units_and_weights_series_instead_of_averaging_rates():
    from intelligent_demand.inventory.report import pooled

    fields = (
        "total_cost",
        "holding_cost",
        "shortage_cost",
        "ordering_cost",
        "terminal_cost",
        "demand_units",
        "fulfilled_units",
        "unmet_units",
        "stockout_days",
        "orders",
        "final_on_hand",
        "terminal_pipeline",
        "average_on_hand",
        "average_inventory_position",
    )
    frame = pd.DataFrame([{name: 0.0 for name in fields} for _ in range(2)])
    frame["policy"] = "fixture"
    frame["series"] = [1, 9]
    frame["demand_units"], frame["fulfilled_units"] = [2, 18], [1, 18]
    frame["total_cost"], frame["average_on_hand"] = [10, 90], [2, 4]
    result = pooled(frame, ["policy"]).iloc[0]
    assert result.pooled_fill_rate == 0.95  # Mean of origin rates would wrongly be .75.
    assert result.average_on_hand == 3.8 and result.mean_cost == 10
    frame["demand_units"] = 0
    assert np.isnan(pooled(frame, ["policy"]).pooled_fill_rate.iloc[0])


def test_persisted_event_audit_rejects_wrong_absolute_dates(tmp_path):
    from intelligent_demand.inventory.audit import event_audit
    from intelligent_demand.inventory.engine import ForecastWindow, simulate

    settings = Scenario(lead_days=1)
    y = np.ones((1, 28))
    forecast = ForecastWindow("2020-01-01", tuple(pd.date_range("2020-01-02", periods=28).date), y)
    table, events = simulate(y, [1], forecast, settings, "selected_ml")
    events["series_id"] = "a"
    events = events.drop(columns="series_row")
    path = tmp_path / "events.parquet"
    events.loc[0, "target_date"] = pd.Timestamp("2020-01-03").date()
    events.to_parquet(path)
    with pytest.raises(ValueError, match="absolute date"):
        event_audit(
            path, table, pd.DataFrame({"series_id": ["a"]}), y, settings, True, "2020-01-02", ["a"]
        )
