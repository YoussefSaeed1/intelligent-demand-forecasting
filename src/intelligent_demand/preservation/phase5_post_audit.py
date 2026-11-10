"""Read-only Phase 5 backup verification with the post-audit documentation overlay.

`phase5.verify` is itself part of the backed-up source manifest, so it stays byte-identical. This
separate module checks the same backup against the same manifest but additionally accepts a
declared overlay for reviewed documentation whose current bytes differ from the backed-up originals.
Every original must come from a declared archive directory and match the manifest hash exactly.
Nothing is copied, fitted, regenerated or written.
"""

import argparse
import json
from pathlib import Path

from intelligent_demand.preservation.backup import evidence_path, sha256
from intelligent_demand.preservation.phase5 import COMBINED, ROOT, read

# Reviewed documentation/metadata whose current bytes may differ from the backed-up originals.
# Scientific inputs, simulation code, plans, ledgers and results are deliberately absent.
OVERLAY_ALLOWED = frozenset({
    ".gitattributes",
    "README.md",
    "docs/ROADMAP.md",
    "docs/ACADEMIC_REQUIREMENTS.md",
    "docs/PHASE5_CLAUDE_AUDIT_HANDOFF.md",
    "docs/PHASE5_COMPLETION_CHECKLIST.md",
    "docs/PHASE5_INVENTORY_RESULTS.md",
    "docs/PHASE5_LIMITATIONS.md",
    "docs/PHASE5_SENSITIVITY_ANALYSIS.md",
    "docs/PHASE5_PROGRESS.md",
    "reports/inventory/PHASE5_INVENTORY_REPORT.html",
})
ARCHIVE_PREFIXES = (
    "reports/preservation/phase5_precheckpoint_original/",
    "reports/inventory/original_documents/phase5_pre_audit/",
)


def verify(destination, overlay):
    destination = Path(destination).resolve()
    manifest = read(ROOT / COMBINED)
    declared = read(overlay)["files"]
    if not set(declared).issubset(OVERLAY_ALLOWED):
        raise ValueError("Unexpected source overlay")
    for logical, entry in declared.items():
        if not entry["original_copy"].startswith(ARCHIVE_PREFIXES):
            raise ValueError("Overlay original must come from a declared archive directory")
        if sha256(evidence_path(ROOT, logical)) != entry["current_sha256"]:
            raise ValueError("Overlay document changed after its declaration: " + logical)
    expected = {x["path"] for x in manifest["files"]} | {
        "EVIDENCE_INVENTORY.json", "BACKUP_VERIFICATION.json"}
    actual = {p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file()}
    if expected != actual:
        raise ValueError(
            f"Backup file set differs: missing {len(expected - actual)}, "
            f"extra {len(actual - expected)}"
        )
    checked_overlay = 0
    for item in manifest["files"]:
        logical = item["path"]
        original = declared.get(logical, {}).get("original_copy", logical)
        checked_overlay += logical in declared
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
        "documents_mapped_to_archived_originals": checked_overlay,
        "missing": [],
        "mismatched": [],
        "unexpected": [],
        "scope": "Original copied file set plus two declared verification sidecars; every "
        "source/backup SHA-256 and size checked, with reviewed documentation mapped to archived "
        "originals. No copying or scientific execution.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--source-overlay", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.destination, args.source_overlay), indent=2))
