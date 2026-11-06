"""Validate the dataset-free setup and configuration boundary."""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from intelligent_demand.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def test_default_config_is_independent_of_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = load_config(ROOT / "configs/default.yaml")
    assert config.paths["raw"] == ROOT / "data/raw"
    assert config.forecast_horizon_days == 28
    assert config.random_seed == 42


@pytest.mark.parametrize("field,value", [("forecast_horizon_days", 0), ("random_seed", True)])
def test_rejects_invalid_experiment_settings(tmp_path, field, value):
    raw = yaml.safe_load((ROOT / "configs/default.yaml").read_text(encoding="utf-8"))
    raw[field] = value
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match=field):
        load_config(path)


def test_rejects_path_escape(tmp_path):
    raw = yaml.safe_load((ROOT / "configs/default.yaml").read_text(encoding="utf-8"))
    raw["paths"]["raw"] = "../../outside"
    path = tmp_path / "configs/bad.yaml"
    path.parent.mkdir()
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="inside the project root"):
        load_config(path)


def test_cli_runs_without_datasets(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "intelligent_demand",
            "--config",
            str(ROOT / "configs/default.yaml"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Configuration valid" in result.stderr
