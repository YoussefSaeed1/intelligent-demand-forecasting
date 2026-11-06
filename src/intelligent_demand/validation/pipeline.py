"""Run explicit source gates and publish only reconciled canonical observations."""

import logging
import math
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from intelligent_demand.config import ProjectConfig
from intelligent_demand.ingestion.datasets import DatasetSpec, file_inventory, sha256, write_json
from intelligent_demand.ingestion.m5 import transform_m5
from intelligent_demand.ingestion.store_item import transform_store_item
from intelligent_demand.validation.quality import CanonicalWriter, issue

LOGGER = logging.getLogger(__name__)


def _save_report(path: Path, report: dict) -> None:
    write_json(path, report)
    finished = report.get("finished_at_utc")
    if finished is None:
        finished = (
            "in progress" if report["status"] == "running" else "not recorded (historical run)"
        )
    lines = [
        f"# {report['dataset']} — Phase 1 data quality",
        "",
        f"Status: {report['status']}",
        "",
        f"Started (UTC): {report.get('started_at_utc', 'not recorded')}",
        f"Finished (UTC): {finished}",
        "",
        "## Critical errors",
        "",
    ]
    lines += [f"- {text}" for text in report["critical_errors"]] or ["None recorded."]
    lines += ["", "## Warnings and interpretation", ""]
    lines += [f"- {text}" for text in report["warnings"]] or ["None recorded."]
    if report.get("notes"):
        lines += ["", "## Policy and audit notes", ""]
        lines += [f"- {text}" for text in report["notes"]]
    if report["profiles"]:
        lines += [
            "",
            "## Input profiles",
            "",
            "| File | Rows | Date range | Stores | Products |",
            "|---|---:|---|---:|---:|",
        ]
        for filename, profile in report["profiles"].items():
            lines.append(
                f"| {filename} | {profile['rows']} | "
                f"{profile.get('date_min', 'n/a')} to {profile.get('date_max', 'n/a')} | "
                f"{profile.get('stores', 'n/a')} | {profile.get('products', 'n/a')} |"
            )
    if report["quantities"]:
        lines += [
            "",
            "## Quantity checks",
            "",
            "| Measure | Observations | Zeros | Negative | Invalid/missing |",
            "|---|---:|---:|---:|---:|",
        ]
        for label, counts in report["quantities"].items():
            lines.append(
                f"| {label} | {counts['observations']} | {counts['zero']} | "
                f"{counts['negative']} | {counts['invalid_or_missing']} |"
            )
    transformation = report["transformation"]
    if transformation.get("output_published"):
        lines += [
            "",
            "## Canonical transformation",
            "",
            f"Output: `{transformation['output']}`",
            "",
            f"- Canonical rows: {transformation['rows']:,}",
            f"- Expected source observations: {transformation['expected_rows']:,}",
            f"- Source sales units: {transformation['source_sales_units_sum']:,.0f}",
            f"- Persisted sales units: {transformation['sales_units_sum']:,.0f}",
            f"- Source/Parquet reconciliation: {transformation['row_and_quantity_reconciliation']}",
        ]
        if "join_cardinality" in transformation:
            lines.append(f"- Join cardinality: {transformation['join_cardinality']}")
    if report.get("independent_audit"):
        audit = report["independent_audit"]
        lines += [
            "",
            "## Independent persisted-file audit",
            "",
            f"Status: {audit['status']}; checked {audit['checked_at_utc']}",
            f"- Missing historical dates: {audit['missing_dates_global_window']}",
            f"- Duplicate business keys: {audit['duplicate_business_keys']}",
            f"- Row-level source/Parquet sales mismatches: {audit['row_level_sales_mismatches']}",
            f"- Evidence: `{audit['report']}`",
        ]
    lines += [
        "",
        "See the adjacent JSON for inventory hashes, parser schemas, counts,",
        "missingness, duplicate checks, quantities and transformation reconciliation.",
        "Checks are implemented in src/intelligent_demand/ingestion and validation.",
    ]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def profile_dataset(spec: DatasetSpec, config: ProjectConfig) -> dict:
    """Profile real files only; missing inputs produce blocked evidence, not observations."""
    raw = config.paths["raw"] / spec.name
    inventory = file_inventory(raw, spec)
    report = {
        "dataset": spec.name,
        "status": "running",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "inventory": inventory,
        "critical_errors": [],
        "warnings": list(inventory["warnings"]),
        "profiles": {},
        "quantities": {},
        "transformation": {},
    }
    report_path = config.paths["reports"] / "data_quality" / f"{spec.name}.json"
    if not inventory["ready_for_profiling"]:
        report["status"] = "blocked"
        issue(report, "Required local source files are missing or have invalid headers.")
        report["finished_at_utc"] = datetime.now(UTC).isoformat()
        _save_report(report_path, report)
        return report
    # Discovery is current even while a large transformation is still in progress.
    _save_report(report_path, report)
    processed = config.paths["processed"] / spec.name
    processed.mkdir(parents=True, exist_ok=True)
    try:
        with TemporaryDirectory(prefix=".canonical-", dir=processed) as staging:
            temporary = Path(staging) / "daily_sales.parquet"
            writer = CanonicalWriter(temporary)
            try:
                transform = transform_store_item if spec.name == "store_item" else transform_m5
                transform(raw, writer, report)
            finally:
                stats = writer.close()
            if stats["rows"] != report["transformation"].get("expected_rows"):
                issue(report, "Canonical row count differs from expected observed source rows")
            sales_label = "train.sales" if spec.name == "store_item" else "history.sales"
            source_sum = report["quantities"].get(sales_label, {}).get("finite_value_sum")
            if source_sum is not None:
                report["transformation"]["source_sales_units_sum"] = source_sum
                if not math.isclose(stats["sales_units_sum"], source_sum, rel_tol=1e-9):
                    issue(report, "Persisted canonical sales differ from source sales total")
            # Detect a source mutation during processing, before publishing derived output.
            after = file_inventory(raw, spec)
            before_hashes = {r["filename"]: r.get("sha256") for r in inventory["files"]}
            if before_hashes != {r["filename"]: r.get("sha256") for r in after["files"]}:
                issue(report, "Raw input hashes changed during profiling")
            if not report["critical_errors"]:
                output = processed / "daily_sales.parquet"
                temporary.replace(output)
                report["transformation"].update(
                    stats,
                    output=str(output.relative_to(config.paths["processed"].parent.parent)),
                    sha256=sha256(output),
                )
                report["status"] = "passed_with_warnings" if report["warnings"] else "passed"
    except Exception as exc:
        # Preserve a current failure report even for errors not covered by parser exceptions.
        # This scope handles local files only; no credential-bearing client text is logged.
        report["failure_type"] = type(exc).__name__
        LOGGER.exception("%s: local profiling failed", spec.name)
        issue(report, "Source parsing or canonical persistence failed; no new output published.")
    if report["critical_errors"]:
        report["status"] = "invalid"
        report["transformation"]["output_published"] = False
    else:
        report["transformation"]["output_published"] = True
    for quantities in report["quantities"].values():
        count = quantities["observations"]
        quantities["zero_share"] = quantities["zero"] / count if count else None
    for profile in report["profiles"].values():
        profile["missing_share"] = {
            column: count / profile["rows"] if profile["rows"] else None
            for column, count in profile["missing"].items()
        }
    report["finished_at_utc"] = datetime.now(UTC).isoformat()
    _save_report(report_path, report)
    LOGGER.info("%s: %s; report %s", spec.name, report["status"], report_path)
    return report
