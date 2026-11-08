"""Read-only historical evidence verification with explicit forward-code overlays.

The original frozen runtime verifier remains strict: edited execution code cannot
claim to be the pre-assessment program. This command verifies historical snapshots
and receipts without fitting, decoding targets, publishing scores or appending logs.
"""

import argparse
import hashlib
import json
from pathlib import Path

from intelligent_demand.experiments.registry import ExperimentRegistry
from intelligent_demand.preservation.backup import sha256
from intelligent_demand.preservation.paths import EvidenceResolver

INVENTORY_SHA = "0b1de21020f2e1d2ceaeddd10845fd723a2f6f8e75161d15fa7efb9c29f5e1ee"
SELECTION = "a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb"
ALLOWED = {
    "src/intelligent_demand/ingestion/store_item.py",
    "src/intelligent_demand/validation/quality.py",
    "src/intelligent_demand/tuning/final.py",
    "src/intelligent_demand/experiments/benchmark.py",
    "src/intelligent_demand/tuning/runner.py",
    ".gitignore", "README.md", "docs/ACADEMIC_REQUIREMENTS.md",
}


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def verify(root, overlay_path=None, inventory_root=None):
    current = EvidenceResolver(root)
    evidence = current if inventory_root is None else EvidenceResolver(inventory_root)
    base = "artifacts/experiments/phase4/"
    inventory_name = "reports/forecasting/PHASE4_EVIDENCE_INVENTORY.json"
    inventory_path = current.resolve(inventory_name, INVENTORY_SHA)
    inventory = json.loads(inventory_path.read_text())
    overlays = {} if overlay_path is None else json.loads(Path(overlay_path).read_text())["files"]
    if not set(overlays).issubset(ALLOWED):
        raise ValueError("Unexpected modification outside reviewed remediation scope")
    for logical, entry in overlays.items():
        current.resolve(logical, entry["current_sha256"])
        current.resolve(entry["original_copy"], entry["original_sha256"])
    for item in inventory["files"]:
        if inventory_root is None and item["path"] in overlays:
            entry = overlays[item["path"]]
            if entry["original_sha256"] != item["sha256"]:
                raise ValueError("Overlay does not preserve original inventory identity")
            path = current.resolve(entry["original_copy"], item["sha256"])
        else:
            path = evidence.resolve(item["path"], item["sha256"])
        if path.stat().st_size != item["bytes"]:
            raise ValueError("Historical evidence size changed")
    frozen = json.loads(evidence.resolve(base + "frozen_selection.json").read_text())
    unsigned = dict(frozen)
    claimed = unsigned.pop("manifest_sha256")
    if claimed != SELECTION or identity(unsigned) != claimed:
        raise ValueError("Frozen selection fingerprint differs")
    for logical, digest in frozen["code_sha256"].items():
        evidence.resolve(base + "code_snapshot/" + logical, digest)
        if inventory_root is None:
            if logical in overlays:
                if overlays[logical]["original_sha256"] != digest:
                    raise ValueError("Code overlay original differs from frozen snapshot")
            else:
                current.resolve(logical, digest)
    ledger_path = evidence.resolve(base + "holdout_access.jsonl")
    previous, events = None, []
    payload = ledger_path.read_bytes()
    if not payload.endswith(b"\n"):
        raise ValueError("Partial ledger event")
    for line in payload.splitlines():
        event = json.loads(line)
        unsigned = dict(event)
        claimed = unsigned.pop("event_sha256")
        if (identity(unsigned) != claimed or event["previous_sha256"] != previous
                or event["sequence"] != len(events) + 1):
            raise ValueError("Original ledger changed/reordered")
        events.append(event)
        previous = claimed
    if len(events) != 12:
        raise ValueError("Unexpected original ledger length")
    for dataset in frozen["datasets"]:
        for kind in ("canonical_targets_read_started", "canonical_targets_read_completed",
                     "dataset_assessment_completed"):
            if sum(e["event"] == kind and e["dataset"] == dataset for e in events) != 1:
                raise ValueError("Assessment is not once-only")
        manifest = json.loads(evidence.resolve(base + f"final_actuals/{dataset}.json").read_text())
        receipt = next(e for e in events if e["dataset"] == dataset
                       and e["event"] == "canonical_targets_read_completed")
        evidence.resolve(base + manifest["path"], manifest["sha256"])
        if manifest["sha256"] != receipt["details"]["actual_sha256"]:
            raise ValueError("Saved actuals differ from canonical-read receipt")
    completed = [e for e in events if e["event"] == "final_assessment_completed"]
    if len(completed) != 1:
        raise ValueError("Missing/extra completed assessment")
    evidence.resolve(base + "final_evaluation.json", completed[0]["details"]["evaluation_sha256"])
    registries = {}
    for logical, expected in (("artifacts/experiments/forecasting", 224),
                              (base + "registry", 108)):
        directory = evidence.resolve(logical)
        registry = ExperimentRegistry(directory)
        runs = sorted(directory.glob("*/status.json"))
        if len(runs) != expected:
            raise ValueError("Missing/extra registry run")
        for status in runs:
            registry.completed(status.parent.name)
        registries[logical] = len(runs)
    for logical, digest in frozen["source_sha256"].items():
        evidence.resolve(logical, digest)
    result = {"status": "passed", "selection_sha256": SELECTION,
              "historical_inventory_files_verified": len(inventory["files"]),
              "historical_inventory_bytes": inventory["total_bytes"],
              "unchanged_live_inventory_entries": sum(
                  item["path"] not in overlays for item in inventory["files"]),
              "archived_current_metadata_inventory_entries": sorted(
                  item["path"] for item in inventory["files"] if item["path"] in overlays),
              "frozen_source_snapshots_verified": len(frozen["code_sha256"]),
              "registry_completed_runs_verified": registries,
              "raw_canonical_fingerprints_verified": len(frozen["source_sha256"]),
              "declared_current_code_document_overlays": len(overlays),
              "ledger_events": len(events), "ledger_sha256": sha256(ledger_path),
              "ledger_head_sha256": previous, "canonical_targets_decoded": 0,
              "model_fits": 0, "scores_published": 0, "original_ledger_writes": 0,
              "historical_source_is_current_execution_source": not bool(overlays)}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--overlay", type=Path)
    parser.add_argument("--inventory-root", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    record = verify(args.workspace_root, args.overlay, args.inventory_root)
    if args.receipt:
        with args.receipt.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2)
            stream.write("\n")
    print(json.dumps(record, indent=2))
