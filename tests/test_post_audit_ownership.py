"""Windows-compatible filesystem ownership tests, never protected experiments."""

import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from intelligent_demand.experiments.ownership import CaseLock, CaseOwnedError, recover_abandoned
from intelligent_demand.tuning import final


def test_same_case_cannot_be_owned_in_another_process(tmp_path):
    path = tmp_path / "case.json"
    code = (
        "import sys\n"
        "from intelligent_demand.experiments.ownership import CaseLock, CaseOwnedError\n"
        "try:\n with CaseLock(sys.argv[1]): raise AssertionError('duplicate owner')\n"
        "except CaseOwnedError: print('refused')\n"
    )
    with CaseLock(path):
        result = subprocess.run([sys.executable, "-c", code, str(path)],
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0 and result.stdout.strip() == "refused"
    assert not path.exists()


@pytest.mark.parametrize("failure", [RuntimeError, KeyboardInterrupt])
def test_interruption_cleanup_and_repeated_execution(tmp_path, failure):
    path = tmp_path / "case.json"
    with pytest.raises(failure), CaseLock(path):
        raise failure("synthetic")
    assert not path.exists()
    with CaseLock(path):
        assert path.exists()
    assert not path.exists()


def test_dead_owner_requires_explicit_recovery_and_keeps_archive(tmp_path):
    path = tmp_path / "case.json"
    code = ("import os,sys; from intelligent_demand.experiments.ownership import CaseLock; "
            "CaseLock(sys.argv[1]).__enter__(); os._exit(0)")
    result = subprocess.run([sys.executable, "-c", code, str(path)], timeout=10)
    assert result.returncode == 0
    original = json.loads(path.read_text())
    with pytest.raises(CaseOwnedError):
        with CaseLock(path):
            pytest.fail("Must not take over automatically")
    archive = recover_abandoned(path, expected_token=original["token"])
    assert json.loads(archive.read_text()) == original and not path.exists()
    with CaseLock(path):
        pass


def test_live_and_uncertain_owners_cannot_be_recovered(tmp_path, monkeypatch):
    path = tmp_path / "case.json"
    with CaseLock(path) as lock:
        with pytest.raises(CaseOwnedError, match="alive or uncertain"):
            recover_abandoned(path, expected_token=lock.token)
        monkeypatch.setattr("intelligent_demand.experiments.ownership.owner_state",
                            lambda _: "uncertain")
        with pytest.raises(CaseOwnedError, match="alive or uncertain"):
            recover_abandoned(path, expected_token=lock.token)
        assert path.exists()


def test_worker_entry_point_owns_case_until_completion(tmp_path, monkeypatch):
    monkeypatch.setattr(final, "OUTPUT", tmp_path)
    monkeypatch.setattr(final, "assert_unopened", lambda: None)
    entered, release = threading.Event(), threading.Event()

    def callback(*args):
        entered.set()
        assert release.wait(10)
        return "only_owner"

    monkeypatch.setattr(final, "_forecast_worker_owned", callback)
    with ThreadPoolExecutor(2) as pool:
        owner = pool.submit(final.forecast_worker, "m5", "synthetic_case")
        assert entered.wait(10)
        other = pool.submit(final.forecast_worker, "m5", "synthetic_case")
        try:
            with pytest.raises(CaseOwnedError):
                other.result(timeout=10)
        finally:
            release.set()
        assert owner.result(timeout=10) == "only_owner"
    assert not list((tmp_path / "worker_locks").glob("*.json"))


@pytest.mark.parametrize("action", ["worker", "forecast", "assess"])
def test_closed_assessment_fails_before_lock_model_or_scorer(tmp_path, monkeypatch, action):
    monkeypatch.setattr(final, "OUTPUT", tmp_path)
    events = [{"event": "canonical_targets_read_started"}]
    monkeypatch.setattr(final, "ledger_events", lambda: events)

    def forbidden(*args):
        pytest.fail("Sealed assessment reached a model, bundle or scoring path")

    monkeypatch.setattr(final, "_forecast_worker_owned", forbidden)
    monkeypatch.setattr(final, "verify_pre_target_bundle", forbidden)
    monkeypatch.setattr(final, "_forecast_all", forbidden)
    with pytest.raises(ValueError, match="already opened"):
        if action == "worker":
            final.forecast_worker("m5", "synthetic_case")
        elif action == "forecast":
            final.forecast_all()
        else:
            final.assess_once()
    assert not list(tmp_path.iterdir())
