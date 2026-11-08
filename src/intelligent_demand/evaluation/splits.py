"""Validate the saved Phase 2 protocol; never infer splits from target values."""

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from intelligent_demand.evaluation.design import chronological_plan

COVERAGE = {
    "store_item": (date(2013, 1, 1), date(2017, 12, 31)),
    "m5": (date(2011, 1, 29), date(2016, 5, 22)),
}


@dataclass(frozen=True)
class ValidationFold:
    dataset_id: str
    number: int
    train_start: date
    origin: date
    validation_start: date
    validation_end: date
    holdout_start: date

    def __post_init__(self):
        if (
            self.dataset_id not in COVERAGE
            or type(self.number) is not int
            or not 1 <= self.number <= 4
        ):
            raise ValueError("Known dataset and validation fold 1–4 required")
        expected = chronological_plan(*COVERAGE[self.dataset_id])
        reference = expected["validation_folds"][self.number - 1]
        actual = {
            "train_start": self.train_start,
            "origin": self.origin,
            "validation_start": self.validation_start,
            "validation_end": self.validation_end,
        }
        if any(type(value) is not date for value in (*actual.values(), self.holdout_start)):
            raise ValueError("Protocol boundaries require daily date values")
        if any(value != date.fromisoformat(reference[key]) for key, value in actual.items()):
            raise ValueError("Fold differs from the frozen Phase 2 protocol")
        if self.holdout_start != date.fromisoformat(expected["test_start"]):
            raise ValueError("Final holdout boundary cannot be changed")

    @property
    def horizon(self):
        return (self.validation_end - self.origin).days

    @property
    def dates(self):
        return tuple(self.origin + timedelta(days=i) for i in range(1, self.horizon + 1))


def validate_fold(fold):
    """Recheck public boundary inputs rather than trusting a duck-typed date container."""
    if type(fold) is not ValidationFold:
        from intelligent_demand.tuning.authority import FinalFold

        if type(fold) is not FinalFold:
            raise ValueError("A frozen, protocol-validated ValidationFold is required")
    fold.__post_init__()


def load_splits(path: Path) -> dict[str, tuple[ValidationFold, ...]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if set(raw) != set(COVERAGE):
        raise ValueError("Both separate dataset protocols are required")
    folds = {}
    for name, coverage in COVERAGE.items():
        expected = chronological_plan(*coverage)
        if raw[name] != expected:
            raise ValueError(f"{name}: saved split manifest differs from the Phase 2 protocol")
        folds[name] = tuple(
            ValidationFold(
                name,
                row["fold"],
                *[
                    date.fromisoformat(row[key])
                    for key in ("train_start", "origin", "validation_start", "validation_end")
                ],
                date.fromisoformat(raw[name]["test_start"]),
            )
            for row in raw[name]["validation_folds"]
        )
    return folds
