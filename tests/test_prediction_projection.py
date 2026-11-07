"""Matched evaluation reuses valid predictions and retains verifiable parent lineage."""

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest
from test_baseline_models import synthetic_source

from intelligent_demand.experiments.config import load_experiment_config
from intelligent_demand.experiments.engine import execute_validation
from intelligent_demand.experiments.projection import project_completed
from intelligent_demand.experiments.registry import ExperimentRegistry, file_digest
from intelligent_demand.models.base import ModelInfo
from intelligent_demand.models.baselines import baseline_registry

ROOT = Path(__file__).resolve().parents[1]


def test_projection_preserves_parent_predictions_without_refitting_and_rejects_broken_lineage(
    tmp_path,
):
    source, fold = synthetic_source(tmp_path, validation_complete=True)
    config = replace(
        load_experiment_config(ROOT / "configs/forecasting.yaml"),
        registry_directory=tmp_path / "runs",
    )
    registry = ExperimentRegistry(config.registry_directory)
    parent = execute_validation(
        config=config,
        fold=fold,
        source=source,
        series=("s1", "s2"),
        models=baseline_registry(),
        model_info=ModelInfo("naive", "1", "global"),
        model_config={},
        registry=registry,
        source_fingerprint=file_digest(source.path),
        code_metadata={"git_revision": "fixture"},
        classes={"s1": "smooth", "s2": "all_zero"},
        class_as_of=fold.origin,
    )
    subset = pd.DataFrame({"series_id": ["s1"], "pattern": ["smooth"]})
    child = project_completed(registry, parent["run_id"], fold, subset, source, tmp_path)
    assert child["specification"]["derived_from"]["models_refitted"] is False
    assert child["specification"]["series_count"] == 1
    parent_path = registry.directory(parent["run_id"]) / parent["outputs"]["predictions"]["path"]
    child_path = registry.directory(child["run_id"]) / child["outputs"]["predictions"]["path"]
    expected = pd.read_parquet(parent_path).query("series_id == 's1'").reset_index(drop=True)
    actual = pd.read_parquet(child_path)
    assert len(actual) == 28
    for column in (
        "series_id",
        "target_date",
        "prediction",
        "raw_prediction",
        "is_fallback",
        "was_clipped",
    ):
        pd.testing.assert_series_equal(actual[column], expected[column])
    cached = project_completed(registry, parent["run_id"], fold, subset, source, tmp_path)
    assert cached["run_id"] == child["run_id"]
    assert len(cached["attempts"]) == 1
    metrics = json.loads(
        (registry.directory(child["run_id"]) / child["outputs"]["metrics"]["path"]).read_text()
    )
    assert metrics["all"]["coverage"]["series"] == 1
    with parent_path.open("ab") as stream:
        stream.write(b"changed-parent")
    with pytest.raises(ValueError):
        registry.completed(child["run_id"])
