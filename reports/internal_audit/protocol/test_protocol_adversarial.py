"""Audit-only synthetic lifecycle checks; original ledger and evidence stay untouched."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from intelligent_demand.experiments.registry import ExperimentRegistry
from intelligent_demand.tuning import authority, final, plan


def test_exclusive_publication_has_one_winner_under_race(tmp_path):
    path = tmp_path / "one.json"
    barrier = threading.Barrier(8)

    def publish(number):
        barrier.wait()
        try:
            plan.publish_once(path, {"candidate": number})
            return number
        except FileExistsError:
            return None

    with ThreadPoolExecutor(8) as pool:
        winners = [n for n in pool.map(publish, range(8)) if n is not None]
    assert len(winners) == 1
    assert json.loads(path.read_text()) == {"candidate": winners[0]}


@pytest.mark.parametrize("failure", [RuntimeError, KeyboardInterrupt])
def test_partial_attempt_cannot_publish_or_rank(tmp_path, failure):
    registry = ExperimentRegistry(tmp_path / "registry")
    spec = {"synthetic": "no forecasting"}
    run = registry.create(spec)
    with pytest.raises(failure), registry.attempt(run, spec) as attempt:
        (attempt / "predictions.parquet").write_bytes(b"incomplete synthetic bytes")
        raise failure("deliberate synthetic interruption")
    with pytest.raises(ValueError, match="Partial/failed/interrupted"):
        registry.completed(run)
    with pytest.raises(ValueError):
        registry.comparison_candidates([run])
    assert registry.read(run)["status"] == (
        "failed" if failure is RuntimeError else "interrupted"
    )


def test_ledger_rejects_changed_payload_but_local_clock_is_not_trusted(tmp_path, monkeypatch):
    monkeypatch.setattr(authority, "OUTPUT", tmp_path)
    times = iter(["2030-01-01T00:00:00+00:00", "2020-01-01T00:00:00+00:00"])
    monkeypatch.setattr(authority, "utc_now", lambda: next(times))
    authority.append_access("synthetic_first")
    authority.append_access("synthetic_second")
    rows = authority.ledger_events()
    assert rows[1]["timestamp_utc"] < rows[0]["timestamp_utc"]
    path = tmp_path / "holdout_access.jsonl"
    path.write_text(path.read_text().replace("synthetic_second", "changed_second"))
    with pytest.raises(ValueError, match="changed or reordered"):
        authority.ledger_events()


def test_direct_final_worker_has_per_case_check_then_create_race(tmp_path, monkeypatch):
    """Demonstrates a robustness gap without fitting or generating even fixture forecasts."""
    dataset, trial = "store_item", "synthetic_trial"
    frozen = {"manifest_sha256": "synthetic", "package_versions": {}, "datasets": {dataset: {
        "evaluations": [{"trial_id": trial}],
    }}}
    monkeypatch.setattr(final, "OUTPUT", tmp_path)
    monkeypatch.setattr(final, "verify_frozen", lambda: frozen)
    monkeypatch.setattr(final, "environment_versions", lambda: {})
    monkeypatch.setattr(final, "assert_unopened", lambda: None)
    monkeypatch.setattr(final, "final_fold", lambda _: SimpleNamespace())
    monkeypatch.setattr(final, "assert_training_unlocked", lambda _: None)
    job = tmp_path / "final_jobs" / f"{trial}.json"
    job.parent.mkdir()
    attempts = tmp_path / "final_forecasts" / dataset / trial
    exists = Path.exists
    gates = {job: threading.Barrier(2), attempts: threading.Barrier(2)}

    def racing_exists(path):
        if path in gates:
            existed = exists(path)
            gates[path].wait(timeout=10)
            return existed
        return exists(path)

    monkeypatch.setattr(Path, "exists", racing_exists)
    both_entered = threading.Barrier(2)
    original_atomic_json = final.atomic_json
    publication = threading.Lock()

    def publish_serially(path, value):
        # A valid schedule with sequential successful pointer replacements avoids
        # Windows sharing conflicts obscuring the worker-ownership question.
        # This protects only an individual write, not the worker/attempt lifetime.
        if path == job:
            with publication:
                return original_atomic_json(path, value)
        return original_atomic_json(path, value)

    monkeypatch.setattr(final, "atomic_json", publish_serially)

    def no_data_access(_):
        both_entered.wait(timeout=10)
        raise RuntimeError("synthetic stop before any source or model access")

    monkeypatch.setattr(final, "population", no_data_access)
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(final.forecast_worker, dataset, trial) for _ in range(2)]
        errors = []
        for future in futures:
            try:
                future.result(timeout=15)
            except Exception as exc:
                errors.append(exc)
        assert len(errors) == 2
        assert all(isinstance(e, RuntimeError) and "synthetic stop" in str(e) for e in errors), (
            [(type(e).__name__, str(e)) for e in errors]
        )
    assert len(list(attempts.iterdir())) == 2
    assert all(json.loads((p / "state.json").read_text())["status"] == "failed"
               for p in attempts.iterdir())
