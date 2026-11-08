"""Partial, failed and resumed trials cannot masquerade as four-origin evidence."""

from types import SimpleNamespace

import pytest

from intelligent_demand.experiments.registry import ExperimentRegistry, atomic_json
from intelligent_demand.tuning import runner


def complete_fold(registry, run_id, spec, value, resume=False):
    with registry.attempt(run_id, spec, resume=resume) as attempt:
        (attempt / "predictions.parquet").write_bytes(b"synthetic prediction evidence")
        atomic_json(attempt / "metrics.json", {"all": {"macro": {"mae": value}}})
        atomic_json(attempt / "model_metadata.json", {"synthetic": True})
        registry.complete(
            run_id,
            attempt,
            {
                "predictions": attempt / "predictions.parquet",
                "metrics": attempt / "metrics.json",
                "model_metadata": attempt / "model_metadata.json",
            },
        )


@pytest.mark.parametrize("failure", [RuntimeError, KeyboardInterrupt])
def test_trial_needs_four_completed_origins_and_preserves_failed_attempts(
    tmp_path, monkeypatch, failure
):
    monkeypatch.setattr(runner, "OUTPUT", tmp_path)
    registry = ExperimentRegistry(tmp_path / "registry")
    monkeypatch.setattr(
        runner, "experiment_config", lambda: SimpleNamespace(registry_directory=registry.root)
    )
    case = {"trial_id": "fixture", "model": "random_forest", "dataset": "store_item"}
    assert runner.refresh_case(case)["status"] == "pending"
    for number in (1, 2, 3, 4):
        spec = {"synthetic_fold": number}
        run_id = registry.create(spec)
        pointer = runner.job_path("fixture", number)
        pointer.parent.mkdir(exist_ok=True)
        atomic_json(pointer, {"run_id": run_id})
        if number < 4:
            complete_fold(registry, run_id, spec, float(number))
            pending = runner.refresh_case(case)
            assert pending["status"] == "pending" and "primary_score" not in pending
        else:
            with pytest.raises(failure), registry.attempt(run_id, spec):
                raise failure("synthetic interrupted fourth origin")
            record = runner.refresh_case(case)
            assert record["status"] in ("failed", "interrupted") and "primary_score" not in record
            previous = list(registry.read(run_id)["attempts"])
            complete_fold(registry, run_id, spec, 4.0, resume=True)
            assert registry.read(run_id)["attempts"][:1] == previous
    completed = runner.refresh_case(case)
    assert completed["status"] == "completed" and completed["primary_score"] == 2.5
    assert completed["fold_mae"] == [1, 2, 3, 4]
    metrics = registry.directory(run_id) / registry.completed(run_id)["outputs"]["metrics"]["path"]
    metrics.write_text("tampered")
    with pytest.raises(ValueError, match="changed"):
        runner.refresh_case(case)
