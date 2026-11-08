"""Read-only evidence preservation checks: no fitting, scoring, or target decoding.

Only the requested new inventory/receipt files are written, with exclusive creation.
The historical ledger, original manifests, models, and results are never modified.
"""

import argparse
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image

from intelligent_demand.experiments.benchmark import verify_sources
from intelligent_demand.experiments.registry import ExperimentRegistry, file_digest
from intelligent_demand.tuning.authority import ledger_events, verify_frozen
from intelligent_demand.tuning.final import verify_pre_target_bundle

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts/experiments/phase4"
EXPECTED = "a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb"
BASE = "6e1a407de0b676e858ffec43bab1fae8d51dae1d"
SCOPES = (
    "artifacts/experiments/phase4",
    "artifacts/experiments/phase3",
    "artifacts/experiments/forecasting",
    "reports/figures/phase4",
    "data",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def local(relative, base=ROOT):
    path = (base / relative).resolve()
    require(path.is_relative_to(ROOT), "Evidence path escapes project")
    return path


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.paths.append(value)


def reports():
    record = load(ROOT / "reports/forecasting/phase4_report_validation.json")
    html = ROOT / "reports/forecasting/PHASE4_FORECASTING_REPORT.html"
    require(file_digest(html) == record["html_sha256"], "HTML report changed")
    for figure in record["figures"]:
        path = local(figure["path"], ROOT / "reports")
        require(file_digest(path) == figure["sha256"], "Figure changed")
        if path.suffix == ".png":
            with Image.open(path) as image:
                image.verify()
        else:
            ET.parse(path)
    parser = Links()
    parser.feed(html.read_text(encoding="utf-8"))
    checked = 0
    for link in parser.paths:
        parts = urlsplit(link)
        require(not parts.scheme and not parts.netloc, "HTML has external dependencies")
        if parts.path:
            require(local(unquote(parts.path), html.parent).is_file(), "Broken report link")
            checked += 1
    for phase in "abcd":
        gate = load(ROOT / f"reports/forecasting/phase4{phase}_gate.json")
        require(gate["status"] == "passed" and gate["quality_checks_passed"], "Failed gate")
    docs = list((ROOT / "docs").glob("PHASE4*.md"))
    markdown_links = 0
    for path in docs:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            parts = urlsplit(link)
            if not parts.scheme and parts.path:
                require(local(unquote(parts.path), path.parent).exists(), "Broken document link")
                markdown_links += 1
    return {
        "status": "passed",
        "figure_files": len(record["figures"]),
        "html_relative_links": checked,
        "markdown_relative_links": markdown_links,
        "browser_render": "not_rerun; prior local-file policy limitation retained",
    }


def verify():
    ledger_path = OUTPUT / "holdout_access.jsonl"
    ledger_before = file_digest(ledger_path)
    frozen = verify_frozen()
    require(frozen["manifest_sha256"] == EXPECTED, "Unexpected selection fingerprint")
    require(verify_sources() == frozen["source_sha256"], "Raw/canonical source changed")
    bundle = verify_pre_target_bundle()  # Reads predictions/delivery, never final actuals.
    package = load(OUTPUT / "independent_audit_package.json")
    seen = set()
    for item in package["files"]:
        require(item["path"] not in seen, "Duplicate audit package entry")
        seen.add(item["path"])
        path = local(item["path"])
        require(path.stat().st_size == item["bytes"], "Original evidence size changed")
        require(file_digest(path) == item["sha256"], "Original audit evidence changed")
    registries = {}
    for relative, expected in (
        ("artifacts/experiments/forecasting", 224),
        ("artifacts/experiments/phase4/registry", 108),
    ):
        directory = ROOT / relative
        registry = ExperimentRegistry(directory)
        counts = Counter()
        for status_file in sorted(directory.glob("*/status.json")):
            state = registry.read(status_file.parent.name)
            counts[state["status"]] += 1
            if state["status"] == "completed":
                registry.completed(status_file.parent.name)
        require(counts == {"completed": expected}, "Missing, incomplete or extra registry run")
        registries[relative] = dict(counts)
    board = load(OUTPUT / "trial_leaderboard.json")
    require(len(board) == 27, "Unexpected trial count")
    runs = [run for case in board for run in case["runs"]]
    require(len(runs) == len(set(runs)) == 108, "Incomplete or duplicated validation folds")
    require(all(c["status"] == "completed" and len(c["runs"]) == 4 for c in board),
            "Incomplete case entered leaderboard")
    events = ledger_events()
    require(len(events) == package["ledger_events"], "Historical ledger length changed")
    require(events[-1]["event_sha256"] == package["ledger_head_sha256"], "Ledger head changed")
    require(events[0]["event"] == "selection_frozen", "Missing first freeze event")
    require(events[0]["details"]["selection_sha256"] == EXPECTED, "Wrong ledger freeze")
    counts = Counter((e["event"], e["dataset"]) for e in events)
    for dataset, definition in frozen["datasets"].items():
        for event in ("canonical_targets_read_started", "canonical_targets_read_completed",
                      "dataset_assessment_completed"):
            require(counts[(event, dataset)] == 1, "Canonical assessment was not once-only")
        receipt = next(e for e in events if e["event"] == "canonical_targets_read_completed"
                       and e["dataset"] == dataset)
        started = next(e for e in events if e["event"] == "canonical_targets_read_started"
                       and e["dataset"] == dataset)
        require(frozen["created_at_utc"] <= bundle["sealed_at_utc"] <= started["timestamp_utc"],
                "Freeze / sealing / target-access order is invalid")
        manifest = load(OUTPUT / f"final_actuals/{dataset}.json")
        require(manifest["selection_sha256"] == EXPECTED, "Snapshot selection mismatch")
        require(manifest["rows"] == receipt["details"]["rows"] == definition["series_count"] * 28,
                "Snapshot row receipt mismatch")
        require(file_digest(local(manifest["path"], OUTPUT)) == manifest["sha256"]
                == receipt["details"]["actual_sha256"], "Actual snapshot fingerprint mismatch")
        consumed = load(OUTPUT / f"access_consumed/{dataset}.json")
        require(consumed["bundle_sha256"] == bundle["bundle_sha256"], "Access reservation changed")
    assessment = OUTPUT / "final_evaluation.json"
    completed = [e for e in events if e["event"] == "final_assessment_completed"]
    require(len(completed) == 1, "Missing/extra final assessment completion")
    require(file_digest(assessment) == completed[0]["details"]["evaluation_sha256"],
            "Final score receipt changed")
    evaluation = load(assessment)
    require(evaluation["selection_sha256"] == EXPECTED and evaluation["status"] == "completed",
            "Final assessment identity/status mismatch")
    require(len(evaluation["results"]) == 8, "Missing final comparator")
    for result in evaluation["results"]:
        item = result["metrics"]
        require(file_digest(local(item["path"], OUTPUT)) == item["sha256"], "Final metrics changed")
    report_status = reports()
    require(file_digest(ledger_path) == ledger_before, "Verification unexpectedly changed ledger")
    return {
        "status": "passed",
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "phase3_base": BASE,
        "selection_fingerprint": EXPECTED,
        "scientific_files_and_snapshots": len(frozen["code_sha256"]),
        "original_audit_package_entries": len(package["files"]),
        "original_audit_package_sha256": file_digest(OUTPUT / "independent_audit_package.json"),
        "source_files": len(frozen["source_sha256"]),
        "registries": registries,
        "validation_cases": len(board),
        "final_evaluations": len(evaluation["results"]),
        "bundle_fingerprint": bundle["bundle_sha256"],
        "ledger_events": len(events),
        "ledger_head_sha256": events[-1]["event_sha256"],
        "ledger_file_sha256": ledger_before,
        "ledger_unchanged": True,
        "canonical_target_reads_this_check": 0,
        "saved_actuals_decoded_this_check": 0,
        "model_fits_or_metric_recomputations": 0,
        "reports": report_status,
    }


def inventory():
    paths = set()
    for scope in SCOPES:
        paths.update(p for p in (ROOT / scope).rglob("*") if p.is_file())
    package = load(OUTPUT / "independent_audit_package.json")
    paths.update(local(item["path"]) for item in package["files"])
    files = []
    for path in sorted(paths):
        before = path.stat()
        digest = file_digest(path)
        after = path.stat()
        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                "Evidence changed during hashing")
        files.append({"path": path.relative_to(ROOT).as_posix(), "bytes": after.st_size,
                      "sha256": digest})
    names = "".join(item["path"] + "\n" for item in files)
    ignored = subprocess.run(["git", "check-ignore", "--stdin"], cwd=ROOT, input=names,
                             capture_output=True, text=True, check=False)
    require(ignored.returncode in (0, 1), "Git ignore inspection failed")
    ignored_names = set(ignored.stdout.splitlines())
    for item in files:
        item["ignored_by_git"] = item["path"] in ignored_names
    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "scope": list(SCOPES),
        "additional_scope": "All files referenced by the original Phase 4 audit package",
        "excluded_scope": "Virtualenv, test temp trees, generic caches and credential stores",
        "read_only_evidence_scan": True,
        "final_actuals_policy": "Opaque byte hashing only; targets not decoded or scored",
        "backup_status": (
            "Inventory records hashes; ignored files remain local and are not Git backups"
        ),
        "files": files,
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "ignored_files": len(ignored_names),
    }


def write_new(path, data):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    require(all(not path.exists() for path in (args.inventory, args.receipt) if path),
            "Never replace an existing preservation receipt")
    outcome = verify()
    if args.inventory:
        record = inventory()
        write_new(args.inventory, record)
        outcome["inventory"] = {
            "path": args.inventory.as_posix(), "sha256": file_digest(args.inventory),
            "files": record["file_count"], "bytes": record["total_bytes"],
            "ignored_files": record["ignored_files"],
        }
    if args.receipt:
        write_new(args.receipt, outcome)
    print(json.dumps(outcome, indent=2))
