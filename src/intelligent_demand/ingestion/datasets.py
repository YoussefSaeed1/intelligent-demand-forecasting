"""Source contracts, local discovery and reproducible file inventories."""

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class DatasetSpec:
    """Expected source files; a historical M5 variant can be unavailable."""

    name: str
    competition: str
    expected: tuple[str, ...]
    required: tuple[str, ...]


DATASETS = {
    "store_item": DatasetSpec(
        "store_item",
        "demand-forecasting-kernels-only",
        ("train.csv", "test.csv", "sample_submission.csv"),
        ("train.csv", "test.csv"),
    ),
    "m5": DatasetSpec(
        "m5",
        "m5-forecasting-accuracy",
        (
            "calendar.csv",
            "sell_prices.csv",
            "sales_train_validation.csv",
            "sales_train_evaluation.csv",
        ),
        ("calendar.csv", "sell_prices.csv"),
    ),
}
M5_IDS = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]


def select_datasets(selection: str) -> list[DatasetSpec]:
    """Resolve a supported name or all without network access."""
    if selection == "all":
        return list(DATASETS.values())
    if selection not in DATASETS:
        raise ValueError("dataset must be store_item, m5, or all")
    return [DATASETS[selection]]


def sha256(path: Path) -> str:
    """Hash incrementally, including large source and Parquet files."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    """Atomically replace a local metadata document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def file_inventory(directory: Path, spec: DatasetSpec) -> dict:
    """Inspect actual expected CSV headers, sizes and hashes; never read credentials."""
    records = []
    for filename in spec.expected:
        path = directory / filename
        record = {"filename": filename, "status": "missing"}
        if path.is_file():
            try:
                with path.open(encoding="utf-8-sig", newline="") as stream:
                    reader = csv.reader(stream)
                    header = next(reader, [])
                    first_row = next(reader, [])
                if spec.name == "store_item":
                    required = {
                        "train.csv": {"date", "store", "item", "sales"},
                        "test.csv": {"id", "date", "store", "item"},
                        "sample_submission.csv": {"id", "sales"},
                    }[filename]
                elif filename.startswith("sales_train"):
                    required = set(M5_IDS)
                else:
                    required = (
                        {"d", "date", "wm_yr_wk"}
                        if filename == "calendar.csv"
                        else {"store_id", "item_id", "wm_yr_wk", "sell_price"}
                    )
                valid = (
                    required.issubset(header)
                    and len(header) == len(set(header))
                    and len(first_row) == len(header)
                    and bool(first_row)
                )
                if filename.startswith("sales_train"):
                    valid = valid and any(c.startswith("d_") for c in header)
                record.update(
                    status="header_valid" if valid else "invalid_header",
                    size_bytes=path.stat().st_size,
                    sha256=sha256(path),
                    columns=header,
                )
            except (OSError, UnicodeError, csv.Error):
                record["status"] = "unreadable"
        records.append(record)
    valid_names = {r["filename"] for r in records if r["status"] == "header_valid"}
    ready = set(spec.required).issubset(valid_names)
    if spec.name == "m5":
        ready = ready and bool(
            valid_names
            & {
                "sales_train_validation.csv",
                "sales_train_evaluation.csv",
            }
        )
    return {
        "dataset": spec.name,
        "competition": spec.competition,
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "ready_for_profiling": ready,
        "files": records,
        "warnings": [
            f"{r['filename']}: {r['status']}" for r in records if r["status"] != "header_valid"
        ],
        "validation_scope": "Header and local SHA-256 only; full data checks require profile-data",
    }
