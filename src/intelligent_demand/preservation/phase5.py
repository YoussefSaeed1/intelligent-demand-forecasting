"""Read-only Phase 5 backup manifests and source/destination hash reconciliation.

No model execution, target decoding, experiment regeneration or ledger writes.
Copying uses the separately tested preservation.backup command.
"""

import argparse
import json
import shutil
from pathlib import Path

import pyarrow.parquet as pq

from intelligent_demand.inventory.design import POLICIES, Scenario
from intelligent_demand.inventory.plan import plan
from intelligent_demand.inventory.runner import case_key, completed, execution
from intelligent_demand.preservation.backup import evidence_path, sha256, write_new
from intelligent_demand.preservation.paths import EvidenceResolver
from intelligent_demand.preservation.verify import identity

ROOT = Path(__file__).resolve().parents[3]
PRESERVATION = ROOT / "reports/preservation"
PRIMARY = "reports/inventory/PHASE5_EVIDENCE_INVENTORY.json"
COMBINED = "reports/preservation/PHASE5_BACKUP_SOURCE_MANIFEST.json"
SUPPLEMENT = "reports/preservation/PHASE5_BACKUP_SUPPLEMENT.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def prepare():
    p, contract = plan(), execution()
    primary = read(ROOT / PRIMARY)
    gate = read(ROOT / "reports/inventory/phase5d_gate.json")
    if sha256(ROOT / PRIMARY) != gate["inventory"]["sha256"]:
        raise ValueError("Original Phase 5 inventory identity changed")
    if len(primary["files"]) != primary["file_count"] or primary["file_count"] != 2252:
        raise ValueError("Original inventory count differs")
    records, reasons = {}, {}

    def add(logical, reason, expected=None):
        logical = str(logical).replace("\\", "/")
        path = evidence_path(ROOT, logical)
        digest = sha256(path)
        if expected is not None and digest != expected:
            raise ValueError("Dependency hash differs: " + logical)
        records[logical] = {"path": logical, "bytes": path.stat().st_size, "sha256": digest}
        reasons.setdefault(logical, set()).add(reason)

    for item in primary["files"]:
        add(item["path"], "original_phase5_inventory", item["sha256"])
        if records[item["path"]]["bytes"] != item["bytes"]:
            raise ValueError("Original inventory size differs")
    if sum(records[x["path"]]["bytes"] for x in primary["files"]) != primary["total_bytes"]:
        raise ValueError("Original inventory total differs")

    rows = events = 0
    expected_cases = set()
    for cohort in p["cohorts"]:
        for settings in p["scenarios"]:
            scenario = Scenario(**settings)
            for policy in POLICIES:
                key = case_key(cohort, scenario, policy, contract)
                expected_cases.add(key)
                state = completed(ROOT / "artifacts/inventory/phase5/runs" / key)
                n = pq.ParquetFile(ROOT / state["files"]["series"]["path"]).metadata.num_rows
                e = pq.ParquetFile(ROOT / state["files"]["events"]["path"]).metadata.num_rows
                if n != cohort["series"] or n != state["series"] or e != state["event_rows"]:
                    raise ValueError("Persisted population/event count differs")
                rows += n
                events += e
    actual_cases = {x.name for x in (ROOT / "artifacts/inventory/phase5/runs").iterdir()}
    replay_count = sum(len(c["representatives"]) for c in p["cohorts"]) * 17 * 4
    if (
        actual_cases != expected_cases
        or len(actual_cases) != 544
        or rows != 8429280
        or events != 13969536
        or replay_count != 3264
    ):
        raise ValueError("Case/row/event/replay coverage differs")
    for key, value in (
        ("cases", 544),
        ("series_episodes", rows),
        ("retained_event_rows", events),
        ("scalar_reference_episodes", replay_count),
    ):
        if gate[key] != value:
            raise ValueError("Gate disagrees with persisted evidence")

    historical = read(ROOT / "reports/forecasting/PHASE4_EVIDENCE_INVENTORY.json")
    historical_files = {x["path"]: x for x in historical["files"]}
    resolver = EvidenceResolver(ROOT, ROOT)

    def sampled_labels(directory, item, spec):
        metadata_path = Path(directory) / item["path"]
        logical = metadata_path.relative_to(ROOT).as_posix()
        add(logical, "sparse_group_metadata", item["sha256"])
        metadata = read(metadata_path)[0]
        cache = resolver.resolve(spec["model_configuration"]["feature_cache"])
        cache /= identity(metadata["feature_cache_contract"])
        manifest = read(cache / "complete.json")
        add((cache / "complete.json").relative_to(ROOT), "necessary_sparse_label_cache_manifest")
        for field in ("labels", "positions"):
            filename = manifest["names"][field]
            add(
                (cache / filename).relative_to(ROOT),
                "necessary_sparse_group_training_evidence",
                manifest["files"][filename],
            )

    for cohort in p["cohorts"]:
        item = cohort["metadata"]
        add(item["path"], "series_population_and_demand_classes", item["sha256"])
        item = cohort["training_cache"]
        add(item["path"], "origin_bound_calibration_manifest", item["sha256"])
        cache = ROOT / item["path"]
        cached = read(cache)
        name = cached["values"]
        add(
            (cache.parent / name).relative_to(ROOT),
            "necessary_origin_bound_calibration_array",
            cached["files"][name],
        )
        for label, source in cohort["sources"].items():
            for field in ("predictions", "specification"):
                item = source[field]
                add(item["path"], "frozen_validation_forecast_dependency", item["sha256"])
            directory = (ROOT / source["specification"]["path"]).parent
            prefix = directory.relative_to(ROOT).as_posix() + "/"
            for logical, item in historical_files.items():
                if logical.startswith(prefix):
                    add(logical, "complete_original_input_run_evidence", item["sha256"])
            if cohort["dataset"] == "m5" and label == "selected_ml":
                state = read(directory / "status.json")
                sampled_labels(
                    directory,
                    state["outputs"]["model_metadata"],
                    read(directory / "specification.json"),
                )
    sealed = read(ROOT / "artifacts/experiments/phase4/sealed_predictions.json")
    final = next(x for x in sealed["forecasts"] if x["dataset"] == "m5" and x["role"] == "selected")
    sampled_labels(
        ROOT / "artifacts/experiments/phase4",
        final["files"]["model_metadata"],
        final["specification"],
    )
    for dataset in ("store_item", "m5"):
        logical = f"data/processed/{dataset}/daily_sales.parquet"
        add(logical, "canonical_validation_input_byte_copy_only", p["source_sha256"][logical])
    for pattern in (
        "src/**/*.py",
        "configs/*.yaml",
        "artifacts/experiments/phase5*.log",
        "artifacts/experiments/phase5*evidence*.json",
    ):
        for path in ROOT.glob(pattern):
            add(path.relative_to(ROOT), "implementation_or_environment_or_original_check_log")
    for logical in (
        PRIMARY,
        "reports/inventory/phase5d_gate.json",
        "pyproject.toml",
        ".gitattributes",
        "docs/environment-freeze.txt",
        "reports/eda/proposed_splits.json",
        "docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md",
        "artifacts/experiments/phase4/frozen_selection.json",
        "artifacts/experiments/phase4/holdout_access.jsonl",
        "artifacts/experiments/phase4/sealed_predictions.json",
        "artifacts/experiments/phase4/trial_leaderboard.json",
        "reports/forecasting/PHASE4_EVIDENCE_INVENTORY.json",
        "reports/post_audit/remediation_overlay.json",
        "reports/preservation/PHASE5_PHASE4_PREFLIGHT.json",
        "artifacts/experiments/phase5_checkpoint_initial_git_status.json",
    ):
        add(logical, "supplementary_provenance_or_reproduction_dependency")
    supplemental = [
        records[k] | {"reasons": sorted(reasons[k])}
        for k in sorted(records)
        if "original_phase5_inventory" not in reasons[k]
    ]
    report = {
        "schema_version": 1,
        "primary_inventory": PRIMARY,
        "primary_sha256": sha256(ROOT / PRIMARY),
        "primary_files": 2252,
        "primary_bytes": primary["total_bytes"],
        "files": supplemental,
        "file_count": len(supplemental),
        "total_bytes": sum(x["bytes"] for x in supplemental),
        "scope": "Dependencies omitted by original namespace inventory; necessary calibration "
        "and sparse-label caches only. Canonical files copied as bytes, no target decoding. "
        "Unused feature matrices/prices, virtual environments, raw CSVs and credentials excluded.",
        "case_reconciliation": {
            "completed": 544,
            "series_episodes": rows,
            "retained_events": events,
            "declared_scalar_replays": replay_count,
        },
    }
    write_new(ROOT / SUPPLEMENT, report)
    add(SUPPLEMENT, "supplementary_manifest")
    combined = {
        "schema_version": 1,
        "primary_inventory": PRIMARY,
        "primary_sha256": sha256(ROOT / PRIMARY),
        "supplement": SUPPLEMENT,
        "files": [records[k] for k in sorted(records)],
        "file_count": len(records),
        "total_bytes": sum(x["bytes"] for x in records.values()),
        "free_bytes_at_preflight": shutil.disk_usage(ROOT).free,
        "phase4_full_evidence": "Original full Phase 4 inventory/backup remains separate "
        "and unchanged; this includes the exact input runs needed for Phase 5, not all "
        "unrelated Phase 4 trials or final holdout outcomes.",
    }
    write_new(ROOT / COMBINED, combined)
    print(
        json.dumps(
            {k: combined[k] for k in ("file_count", "total_bytes", "free_bytes_at_preflight")},
            indent=2,
        )
    )


def verify(destination, overlay=None):
    destination = Path(destination).resolve()
    manifest = read(ROOT / COMBINED)
    source_overlay = {} if overlay is None else read(overlay)["files"]
    # Only checkpoint metadata may map to its immutable archived original.
    if not set(source_overlay).issubset({"docs/PHASE5_CLAUDE_AUDIT_HANDOFF.md", ".gitattributes"}):
        raise ValueError("Unexpected source overlay")
    for logical, entry in source_overlay.items():
        if sha256(evidence_path(ROOT, logical)) != entry["current_sha256"]:
            raise ValueError("Updated handoff changed after checkpoint declaration")
    expected = {x["path"] for x in manifest["files"]}
    expected |= {"EVIDENCE_INVENTORY.json", "BACKUP_VERIFICATION.json"}
    actual = {p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file()}
    if expected != actual:
        raise ValueError(
            f"Backup file set differs: missing {len(expected - actual)}, "
            f"extra {len(actual - expected)}"
        )
    for item in manifest["files"]:
        logical = item["path"]
        original = source_overlay.get(logical, {}).get("original_copy", logical)
        for root, name in ((ROOT, original), (destination, logical)):
            path = evidence_path(root, name)
            if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
                raise ValueError("Backup/source mismatch: " + logical)
    if sha256(destination / "EVIDENCE_INVENTORY.json") != sha256(ROOT / COMBINED):
        raise ValueError("Backup inventory sidecar differs")
    receipt = read(destination / "BACKUP_VERIFICATION.json")
    if receipt["status"] != "passed" or receipt["verified_files"] != len(manifest["files"]):
        raise ValueError("Incomplete original copy verification")
    return {
        "status": "passed",
        "verified_files": len(manifest["files"]),
        "verified_bytes": manifest["total_bytes"],
        "missing": [],
        "mismatched": [],
        "unexpected": [],
        "source_handoff_archived": bool(source_overlay),
        "scope": "Original copied file set plus two declared verification sidecars; "
        "every source/backup SHA-256 and size checked. No copying or scientific execution.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "verify"])
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--source-overlay", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        if args.destination is None:
            parser.error("verify requires --destination")
        print(json.dumps(verify(args.destination, args.source_overlay), indent=2))
