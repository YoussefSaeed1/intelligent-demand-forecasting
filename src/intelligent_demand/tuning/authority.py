"""Explicit frozen-plan authority and append-only final-target access records."""

import json
import os
from dataclasses import dataclass
from datetime import date, timedelta

from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.registry import file_digest, utc_now
from intelligent_demand.tuning.plan import (
    OUTPUT,
    REPORTS,
    ROOT,
    load_plan,
    publish_once,
    require_phase,
)


def read_frozen():
    """No frozen file / failed tuning gate means no final-window capability."""
    path = OUTPUT / "frozen_selection.json"
    record = json.loads(path.read_text())
    unsigned = dict(record)
    expected = unsigned.pop("manifest_sha256")
    if identity(unsigned) != expected:
        raise ValueError("Frozen model-selection manifest changed")
    gate_path = REPORTS / "phase4b_gate.json"
    gate = json.loads(gate_path.read_text())
    if (
        gate.get("status") != "passed"
        or not gate.get("quality_checks_passed")
        or gate.get("holdout_targets_accessed") is not False
        or gate.get("plan_sha256") != record["plan_sha256"]
        or file_digest(gate_path) != record["phase4b_gate_sha256"]
    ):
        raise ValueError("Final authority requires an unchanged, passed Phase 4B gate")
    return record


def verify_frozen():
    record = read_frozen()
    plan = load_plan()
    require_phase("4b")
    if record["plan_sha256"] != plan["contract_sha256"]:
        raise ValueError("Frozen selection differs from the optimisation contract")
    for relative, digest in record["code_sha256"].items():
        if file_digest(ROOT / relative) != digest:
            raise ValueError(f"Pre-holdout scientific code changed: {relative}")
        snapshot = OUTPUT / "code_snapshot" / relative
        if file_digest(snapshot) != digest:
            raise ValueError("Immutable code snapshot changed")
    return record


@dataclass(frozen=True)
class FinalFold:
    dataset_id: str
    number: int
    train_start: date
    origin: date
    validation_start: date
    validation_end: date
    holdout_start: date
    selection_sha256: str

    def __post_init__(self):
        from intelligent_demand.evaluation.splits import COVERAGE

        record = read_frozen()
        if self.dataset_id not in COVERAGE or self.number != 0:
            raise ValueError(
                "Final fold requires a known dataset and separate assessment index zero"
            )
        start, end = COVERAGE[self.dataset_id]
        if (
            any(
                type(v) is not date
                for v in (
                    self.train_start,
                    self.origin,
                    self.validation_start,
                    self.validation_end,
                    self.holdout_start,
                )
            )
            or self.train_start != start
            or self.validation_end != end
            or self.holdout_start != end - timedelta(days=27)
            or self.validation_start != self.holdout_start
            or self.origin != self.holdout_start - timedelta(days=1)
            or self.selection_sha256 != record["manifest_sha256"]
            or record["datasets"][self.dataset_id]["origin"] != str(self.origin)
        ):
            raise ValueError("Final boundary differs from the immutable selected assessment")

    @property
    def horizon(self):
        return 28

    @property
    def dates(self):
        return tuple(self.origin + timedelta(days=n) for n in range(1, 29))


def final_fold(dataset):
    from intelligent_demand.evaluation.splits import COVERAGE

    record = verify_frozen()
    start, end = COVERAGE[dataset]
    holdout = end - timedelta(days=27)
    return FinalFold(
        dataset,
        0,
        start,
        holdout - timedelta(days=1),
        holdout,
        end,
        holdout,
        record["manifest_sha256"],
    )


def ledger_events():
    path = OUTPUT / "holdout_access.jsonl"
    if not path.exists():
        return []
    content = path.read_bytes()
    if content and not content.endswith(b"\n"):
        raise ValueError("Partial holdout ledger entry; never reset the access history")
    records = []
    previous = None
    for line in content.splitlines():
        record = json.loads(line)
        payload = dict(record)
        digest = payload.pop("event_sha256")
        if (
            identity(payload) != digest
            or record["previous_sha256"] != previous
            or record["sequence"] != len(records) + 1
        ):
            raise ValueError("Holdout access ledger was changed or reordered")
        records.append(record)
        previous = digest
    return records


def append_access(event, dataset=None, details=None):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    lock = OUTPUT / "holdout_access.lock"
    with lock.open("x") as stream:
        stream.write(str(os.getpid()))
    try:
        rows = ledger_events()
        record = {
            "sequence": len(rows) + 1,
            "timestamp_utc": utc_now(),
            "event": event,
            "dataset": dataset,
            "details": details or {},
            "previous_sha256": rows[-1]["event_sha256"] if rows else None,
        }
        record["event_sha256"] = identity(record)
        with (OUTPUT / "holdout_access.jsonl").open("ab") as stream:
            stream.write(
                (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
            )
            stream.flush()
            os.fsync(stream.fileno())
        return record
    finally:
        lock.unlink()


def assert_training_unlocked(fold):
    if type(fold) is FinalFold and any(
        e["event"] == "canonical_targets_read_started" for e in ledger_events()
    ):
        raise ValueError(
            "Final targets have been opened; refitting/regenerating forecasts is prohibited"
        )


def verified_bundle():
    frozen = verify_frozen()
    bundle = json.loads((OUTPUT / "sealed_predictions.json").read_text())
    unsigned = dict(bundle)
    digest = unsigned.pop("bundle_sha256")
    if identity(unsigned) != digest or bundle["selection_sha256"] != frozen["manifest_sha256"]:
        raise ValueError("Final forecast bundle changed")
    expected = {
        (dataset, entry["trial_id"])
        for dataset, plan in frozen["datasets"].items()
        for entry in plan["evaluations"]
    }
    if {(r["dataset"], r["trial_id"]) for r in bundle["forecasts"]} != expected:
        raise ValueError("Every selected model and predeclared comparator must be sealed first")
    for forecast in bundle["forecasts"]:
        for item in forecast["files"].values():
            path = (OUTPUT / item["path"]).resolve()
            if not path.is_relative_to(OUTPUT.resolve()) or file_digest(path) != item["sha256"]:
                raise ValueError("Sealed pre-target model/prediction artifact changed")
    return bundle


def begin_canonical_access(dataset):
    bundle = verified_bundle()
    if any(
        e["dataset"] == dataset and e["event"] == "canonical_targets_read_started"
        for e in ledger_events()
    ):
        raise ValueError("Canonical final targets can be unlocked only once per dataset")
    reservation = OUTPUT / "access_consumed" / f"{dataset}.json"
    publish_once(reservation, {"dataset": dataset, "bundle_sha256": bundle["bundle_sha256"]})
    append_access(
        "canonical_targets_read_started",
        dataset,
        {"bundle_sha256": bundle["bundle_sha256"], "selection_sha256": bundle["selection_sha256"]},
    )
    return bundle
