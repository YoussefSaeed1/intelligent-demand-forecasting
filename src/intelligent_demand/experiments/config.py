"""Validated, dataset-free settings and deterministic experiment identity."""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from intelligent_demand.evaluation.splits import load_splits


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def identity(value) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


@dataclass(frozen=True)
class ExperimentConfig:
    split_manifest: Path
    registry_directory: Path
    horizon_days: int = 28
    season_days: int = 7
    random_seed: int = 42
    batch_rows: int = 65536
    max_workers: int = 1
    max_threads: int = 4
    max_evaluation_rows: int = 1000000
    nonnegative_predictions: bool = True

    def __post_init__(self):
        for key in (
            "horizon_days",
            "season_days",
            "batch_rows",
            "max_workers",
            "max_threads",
            "max_evaluation_rows",
        ):
            if type(getattr(self, key)) is not int or getattr(self, key) < 1:
                raise ValueError(f"Positive integer required: {key}")
        if type(self.random_seed) is not int or self.random_seed < 0:
            raise ValueError("Nonnegative integer seed required")
        if self.horizon_days != 28 or self.season_days != 7:
            raise ValueError("Frozen protocol requires horizon=28 and scaling season=7")
        if self.max_workers > 2 or self.max_threads > 4:
            raise ValueError("Protocol limits are two workers and four threads")
        if self.nonnegative_predictions is not True:
            raise ValueError("Protocol requires nonnegative point predictions")

    def metadata(self):
        return {k: str(v) if isinstance(v, Path) else v for k, v in asdict(self).items()}


def load_experiment_config(path: Path) -> ExperimentConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    fields = set(ExperimentConfig.__dataclass_fields__)
    if not isinstance(raw, dict) or set(raw) != fields | {"schema_version"}:
        raise ValueError("Forecasting settings require exactly the documented schema")
    version = raw.pop("schema_version")
    if type(version) is not int or version != 1:
        raise ValueError("Unsupported forecasting schema version")
    root = path.resolve().parent.parent
    for key in ("split_manifest", "registry_directory"):
        value = raw[key]
        if not isinstance(value, str) or Path(value).is_absolute():
            raise ValueError("Configuration paths must be project-relative")
        raw[key] = (root / value).resolve()
        if not raw[key].is_relative_to(root):
            raise ValueError("Configuration path escapes the project")
    result = ExperimentConfig(**raw)
    load_splits(result.split_manifest)
    return result
