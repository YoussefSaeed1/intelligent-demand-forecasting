"""Load and validate repository-relative research configuration."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ProjectConfig:
    """Validated settings; paths are resolved against the configuration's project root."""

    project_name: str
    random_seed: int
    forecast_horizon_days: int
    paths: dict[str, Path]


def load_config(config_path: Path) -> ProjectConfig:
    """Load a YAML file under <project>/configs; do not create or require data files."""
    config_path = config_path.resolve()
    with config_path.open(encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    if not isinstance(raw, dict):
        raise ValueError("Configuration must be a YAML mapping")
    name = raw.get("project_name")
    seed = raw.get("random_seed")
    horizon = raw.get("forecast_horizon_days")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("project_name must be a nonempty string")
    if type(seed) is not int or seed < 0:
        raise ValueError("random_seed must be a nonnegative integer")
    if type(horizon) is not int or horizon <= 0:
        raise ValueError("forecast_horizon_days must be a positive integer")
    paths = raw.get("paths")
    required = {"raw", "interim", "processed", "artifacts", "reports"}
    if not isinstance(paths, dict) or set(paths) != required:
        raise ValueError(f"paths must contain exactly {sorted(required)}")
    root = config_path.parent.parent
    resolved = {}
    for key, value in paths.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"paths.{key} must be a nonempty relative path")
        candidate = (root / value).resolve()
        if Path(value).is_absolute() or not candidate.is_relative_to(root):
            raise ValueError(f"paths.{key} must remain inside the project root")
        resolved[key] = candidate
    return ProjectConfig(name, seed, horizon, resolved)
