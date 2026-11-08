"""Exercise the irreversible final-assessment workflow only on synthetic source files."""

import json
from datetime import date
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from intelligent_demand.evaluation.splits import COVERAGE
from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.preparation import PreparedSource
from intelligent_demand.experiments.registry import file_digest, utc_now
from intelligent_demand.reporting import phase4_report
from intelligent_demand.tuning import authority, final, plan, selection
from intelligent_demand.tuning.reconcile import hierarchy_table, training_sampling_profile


@pytest.fixture
def synthetic_final(tmp_path, monkeypatch):
    output = tmp_path / "phase4"
    reports = tmp_path / "reports/forecasting"
    reports.mkdir(parents=True)
    for module in (authority, final):
        monkeypatch.setattr(module, "OUTPUT", output)
        monkeypatch.setattr(module, "REPORTS", reports)
    gate = {
        "status": "passed",
        "quality_checks_passed": True,
        "holdout_targets_accessed": False,
        "plan_sha256": "p" * 64,
    }
    gate_path = reports / "phase4b_gate.json"
    gate_path.write_text(json.dumps(gate))
    sources, datasets, populations = {}, {}, {}
    for dataset, (start, end) in COVERAGE.items():
        metadata = pd.DataFrame(
            {
                "series_id": ["s1", "s2"],
                "store_id": ["a", "b"],
                "item_id": ["i", "j"],
                "pattern": ["smooth", "intermittent"],
            }
        )
        metadata["sales_units"] = [100, 50]
        if dataset == "m5":
            metadata = metadata.assign(cat_id="c", dept_id="d", state_id="z")
        populations[dataset] = metadata
        dates = pd.date_range(start, end)
        frame = pd.MultiIndex.from_product(
            [metadata.series_id, dates], names=["series_id", "date"]
        ).to_frame(index=False)
        frame["dataset_id"] = dataset
        frame["sales_units"] = (np.arange(len(frame)) % 13).astype(float)
        frame["unit_price"] = 99.0
        table = pa.Table.from_pandas(frame, preserve_index=False)
        table = table.set_column(
            table.schema.get_field_index("date"),
            "date",
            pa.array(frame.date.dt.date, type=pa.date32()),
        )
        path = tmp_path / f"{dataset}.parquet"
        pq.write_table(table, path)
        sources[dataset] = path
        cases = [
            {
                "trial_id": f"{dataset}_{method}",
                "model": method,
                "parameters": {},
                "seed": 42,
                "role": "selected" if method == "moving_average_28" else "comparator",
            }
            for method in ("moving_average_28", "seasonal_naive")
        ]
        datasets[dataset] = {
            "training_start": str(start),
            "selected_trial_id": cases[0]["trial_id"],
            "origin": str(end - pd.Timedelta(days=28)),
            "series_count": 2,
            "series_sha256": identity(["s1", "s2"]),
            "maximum_training_rows": 120,
            "evaluations": cases,
            "class_as_of": str(start + pd.Timedelta(days=365)),
        }
    fingerprints = {
        f"data/processed/{d}/daily_sales.parquet": file_digest(p) for d, p in sources.items()
    }
    record = {
        "package_versions": selection.environment_versions(),
        "created_at_utc": utc_now(),
        "datasets": datasets,
        "source_sha256": fingerprints,
        "plan_sha256": "p" * 64,
        "phase4b_gate_sha256": file_digest(gate_path),
    }
    record["manifest_sha256"] = identity(record)
    plan.publish_once(output / "frozen_selection.json", record)
    monkeypatch.setattr(authority, "verify_frozen", authority.read_frozen)
    monkeypatch.setattr(final, "verify_frozen", authority.read_frozen)
    monkeypatch.setattr(final, "source_path", lambda d: sources[d])
    monkeypatch.setattr(final, "population", lambda d: populations[d])
    monkeypatch.setattr(final, "verify_sources", lambda: fingerprints)
    monkeypatch.setattr(final, "Phase4Source", PreparedSource)
    return record, sources


def seal_synthetic(record):
    rows = []
    for dataset, definition in record["datasets"].items():
        for case in definition["evaluations"]:
            final.forecast_worker(dataset, case["trial_id"])
            rows.append(
                json.loads((final.OUTPUT / "final_jobs" / f"{case['trial_id']}.json").read_text())
            )
    bundle = {
        "selection_sha256": record["manifest_sha256"],
        "sealed_at_utc": utc_now(),
        "forecasts": rows,
        "holdout_targets_accessed": False,
    }
    bundle["bundle_sha256"] = identity(bundle)
    plan.publish_once(final.OUTPUT / "sealed_predictions.json", bundle)
    return bundle


def test_full_synthetic_final_assessment_is_one_time_and_independently_reconciled(synthetic_final):
    record, _ = synthetic_final
    with pytest.raises(FileNotFoundError):
        final.read_canonical_targets_once("store_item")
    assert authority.ledger_events() == []
    bundle = seal_synthetic(record)
    assert authority.verified_bundle() == bundle
    assert authority.ledger_events() == []
    final.assess_once()
    final.audit_final()
    gate = json.loads((final.REPORTS / "phase4c_gate.json").read_text())
    assert gate["status"] == "passed" and len(gate["runs"]) == 4
    digest = file_digest(final.REPORTS / "phase4c_gate.json")
    final.audit_final(readonly=True)
    assert file_digest(final.REPORTS / "phase4c_gate.json") == digest
    events = authority.ledger_events()
    for dataset in record["datasets"]:
        assert (
            sum(
                e["event"] == "canonical_targets_read_started" and e["dataset"] == dataset
                for e in events
            )
            == 1
        )
        assert len(final.saved_actuals(dataset, "final_report")) == 56
        with pytest.raises(ValueError, match="only once"):
            final.read_canonical_targets_once(dataset)
    with pytest.raises(ValueError, match="already opened"):
        final.assess_once()
    with pytest.raises(ValueError, match="already opened"):
        final.forecast_worker("store_item", "store_item_moving_average_28")
    with pytest.raises(ValueError, match="only support"):
        final.saved_actuals("store_item", "tune")


def test_future_target_poison_cannot_affect_pre_target_forecasts(synthetic_final):
    record, sources = synthetic_final
    dataset = "store_item"
    case = record["datasets"][dataset]["evaluations"][0]["trial_id"]
    final.forecast_worker(dataset, case)
    pointer = final.OUTPUT / "final_jobs" / f"{case}.json"
    first = json.loads(pointer.read_text())
    expected = pd.read_parquet(final.OUTPUT / first["files"]["predictions"]["path"])
    # A second, separately named frozen comparator has identical pre-origin mathematics.
    original = sources[dataset]
    table = pq.read_table(original)
    values = table["sales_units"].to_numpy().copy()
    holdout = np.array(table["date"].to_pylist()) >= date(2017, 12, 4)
    values[holdout] = 1e9
    table = table.set_column(
        table.schema.get_field_index("sales_units"), "sales_units", pa.array(values)
    )
    pq.write_table(table, original)
    # A changed data hash invalidates the freeze before even training can start.
    with pytest.raises(ValueError, match="fingerprint changed"):
        final.forecast_worker(dataset, "store_item_seasonal_naive")
    pd.testing.assert_frame_equal(
        expected, pd.read_parquet(final.OUTPUT / first["files"]["predictions"]["path"])
    )
    assert authority.ledger_events() == []


def test_incomplete_or_tampered_bundle_cannot_unlock_targets(synthetic_final):
    record, _ = synthetic_final
    bundle = seal_synthetic(record)
    path = final.OUTPUT / bundle["forecasts"][0]["files"]["predictions"]["path"]
    with path.open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="artifact changed"):
        final.read_canonical_targets_once("m5")
    assert not authority.ledger_events()


def test_changed_actual_and_manifest_cannot_replace_the_canonical_ledger_receipt(synthetic_final):
    record, _ = synthetic_final
    seal_synthetic(record)
    final.assess_once()
    path = final.OUTPUT / "final_actuals/m5.parquet"
    with path.open("ab") as stream:
        stream.write(b"tamper")
    manifest_path = final.OUTPUT / "final_actuals/m5.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["sha256"] = file_digest(path)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="ledger receipt"):
        final.saved_actuals("m5", "independent_metric_audit")


@pytest.mark.parametrize("method", ["random_forest", "lightgbm"])
def test_final_ml_refit_audits_features_and_persistence_before_targets(synthetic_final, method):
    record, sources = synthetic_final
    definition = record["datasets"]["m5"]
    case = definition["evaluations"][0]
    case.update(model=method, parameters=plan.parameters_for(method))
    record.pop("manifest_sha256")
    record["manifest_sha256"] = identity(record)
    # Isolated synthetic authority, never a real experiment manifest.
    (final.OUTPUT / "frozen_selection.json").write_text(json.dumps(record))
    final.forecast_worker("m5", case["trial_id"])
    saved = json.loads((final.OUTPUT / "final_jobs" / f"{case['trial_id']}.json").read_text())
    proof = json.loads((final.OUTPUT / saved["files"]["pre_target_audit"]["path"]).read_text())
    assert proof["feature_audit"]["status"] == "passed"
    assert proof["holdout_targets_accessed"] is False
    assert authority.ledger_events() == []
    # Validation stores its seed only at the specification level, unlike the final worker.
    spec = saved["specification"]
    spec["model_configuration"].pop("random_seed")
    source = PreparedSource(
        sources["m5"],
        "m5",
        final.population("m5"),
        final.OUTPUT / "cache",
        file_digest(sources["m5"]),
    )
    panel = source.panel(authority.final_fold("m5"), ("s1", "s2"))
    profile = training_sampling_profile(
        {"specification": spec, "outputs": saved["files"]}, final.OUTPUT, panel
    )
    assert profile["seeded_strata_reproduced"] and profile["series"] == 2


def test_selector_excludes_failed_trials_and_uses_predeclared_ties():
    settings = plan.load_settings()["selection"]
    rows = [
        {
            "status": status,
            "primary_score": score,
            "model": method,
            "configuration_sha256": digest,
            "trial_id": digest,
        }
        for status, score, method, digest in [
            ("failed", 0, "lightgbm", "a"),
            ("completed", 2, "lightgbm", "b"),
            ("completed", 2 + 1e-13, "seasonal_naive", "c"),
        ]
    ]
    assert selection.choose(rows, settings)["model"] == "seasonal_naive"
    with pytest.raises(ValueError, match="No completed"):
        selection.choose(rows[:1], settings)


def test_hierarchy_errors_are_grouped_leaf_errors_and_preserve_undefined_scales():
    actual = np.array([[0.0, 0.0], [2.0, 4.0], [3.0, 1.0]])
    predicted = np.array([[1.0, 0.0], [1.0, 4.0], [4.0, 2.0]])
    scales = np.array([[np.nan, np.nan], [2.0, 4.0], [1.0, 2.0]])
    flags = np.zeros_like(actual, dtype=bool)
    meta = pd.DataFrame({"store_id": ["a", "a", "b"], "item_id": ["i", "j", "i"]})
    result = hierarchy_table(actual, predicted, scales, flags, flags, meta)
    row = result.loc[result.group_type.eq("store_id") & result.group.eq("a")].iloc[0]
    assert row.observations == 4 and row.pooled_mae == 0.5
    assert row.pooled_rmse == pytest.approx(np.sqrt(0.5))
    assert row.pooled_wape_percent == pytest.approx(100 / 3)
    assert row.defined_mase == 1 and row.undefined_mase == 1


def test_final_controller_lock_rejects_concurrent_supervisors(synthetic_final):
    with final.forecast_lock(), pytest.raises(FileExistsError), final.forecast_lock():
        pass
    assert not (final.OUTPUT / "final_forecast.lock").exists()


def test_final_interruption_preserves_attempt_history_and_has_a_retry_limit(
    synthetic_final, monkeypatch
):
    def interrupted(*_):
        raise KeyboardInterrupt

    monkeypatch.setattr(final, "registry_for", lambda _: SimpleNamespace(create=interrupted))
    case = "store_item_moving_average_28"
    for _ in range(2):
        with pytest.raises(KeyboardInterrupt):
            final.forecast_worker("store_item", case)
    with pytest.raises(ValueError, match="attempt limit"):
        final.forecast_worker("store_item", case)
    history = list((final.OUTPUT / "final_forecasts/store_item" / case).glob("*/state.json"))
    assert len(history) == 2
    assert all(json.loads(p.read_text())["status"] == "interrupted" for p in history)
    assert authority.ledger_events() == []


def test_offline_scientific_report_uses_saved_assessment_without_canonical_reread(
    synthetic_final, monkeypatch
):
    record, _ = synthetic_final
    seal_synthetic(record)
    final.assess_once()
    final.audit_final()
    gate = json.loads((final.REPORTS / "phase4c_gate.json").read_text())
    trials = []
    for dataset, definition in record["datasets"].items():
        for case in definition["evaluations"]:
            trials.append(
                {
                    **case,
                    "dataset": dataset,
                    "status": "completed",
                    "primary_score": 1.0,
                    "configuration_sha256": "c" * 64,
                    "pooled_rmse": 2.0,
                    "pooled_wape_percent": 20.0,
                    "bias_units": 0.1,
                    "macro_mase": 0.8,
                    "macro_rmsse": 0.9,
                    "worker_seconds": 1.0,
                    "peak_rss_mib": 20.0,
                }
            )
    root = final.OUTPUT.parent
    (root / "docs").mkdir()
    for name in ("PHASE4_REPRODUCIBILITY.md", "PHASE4_AUDIT_PACKAGE.md"):
        (root / "docs" / name).write_text("Synthetic report source")
    plan.publish_once(final.REPORTS / "phase4_tuning_report.json", {"figures": []})
    monkeypatch.setattr(phase4_report, "ROOT", root)
    monkeypatch.setattr(phase4_report, "OUTPUT", final.OUTPUT)
    monkeypatch.setattr(phase4_report, "REPORTS", final.REPORTS)
    monkeypatch.setattr(phase4_report, "FIGURES", root / "reports/figures/phase4")
    monkeypatch.setattr(phase4_report, "population", final.population)
    monkeypatch.setattr(phase4_report, "verify_sources", final.verify_sources)
    monkeypatch.setattr(phase4_report, "verify_frozen", authority.read_frozen)
    monkeypatch.setattr(
        phase4_report, "require_phase", lambda p: gate if p == "4c" else {"trials": trials}
    )
    monkeypatch.setattr(phase4_report, "audit_package", lambda *args: None)
    # The canonical reader must never be called by the reporting path.
    monkeypatch.setattr(final, "read_canonical_targets_once", lambda *_: pytest.fail("reread"))
    phase4_report.final_report()
    evidence = json.loads((final.REPORTS / "phase4_report_validation.json").read_text())
    assert evidence["images_verified"] == 12 and evidence["offline"]
    assert (
        len(
            [e for e in authority.ledger_events() if e["event"] == "canonical_targets_read_started"]
        )
        == 2
    )
