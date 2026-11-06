"""Independent Arrow/NumPy source-to-Parquet audit; never transform or rewrite data."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pcsv
import pyarrow.parquet as pq

from intelligent_demand.config import ProjectConfig
from intelligent_demand.ingestion.datasets import sha256, write_json

SOURCE_TYPES = {"date": pa.date32(), "store": pa.int64(), "item": pa.int64()}
PARQUET_TYPES = {
    "dataset_id": pa.string(),
    "series_id": pa.string(),
    "date": pa.date32(),
    "sales_units": pa.float64(),
    "store_id": pa.string(),
    "item_id": pa.string(),
    "category_id": pa.string(),
    "unit_price": pa.float64(),
    "is_observed": pa.bool_(),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _source(path: Path, labelled: bool) -> tuple[pa.Table, dict]:
    """Use a typed CSV reader independent of the original pandas ingestion."""
    types = {**SOURCE_TYPES, "sales" if labelled else "id": pa.int64()}
    table = pcsv.read_csv(path, convert_options=pcsv.ConvertOptions(column_types=types))
    _require(set(table.column_names) == set(types), f"{path.name}: unexpected source schema")
    _require(table.num_rows > 0, f"{path.name}: no data rows")
    table.validate(full=True)
    missing = {name: table[name].null_count for name in table.column_names}
    _require(not any(missing.values()), f"{path.name}: missing source values")
    return table, {
        "rows": table.num_rows,
        "schema": {f.name: str(f.type) for f in table.schema},
        "missing": missing,
        "has_sales_labels": labelled,
    }


def _array(table: pa.Table, column: str) -> np.ndarray:
    values = table[column]
    if column == "date":
        values = values.cast(pa.int32())
    return values.to_numpy(zero_copy_only=False)


def _coverage(table: pa.Table) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Check a daily rectangular panel and record gaps for every observed ID combination."""
    stores, store_indexes = np.unique(_array(table, "store"), return_inverse=True)
    items, item_indexes = np.unique(_array(table, "item"), return_inverse=True)
    _require(bool((stores > 0).all() and (items > 0).all()), "Nonpositive source identifiers")
    dates = _array(table, "date")
    first, last = int(dates.min()), int(dates.max())
    days = last - first + 1
    pairs = store_indexes * len(items) + item_indexes
    keys = pairs * days + dates - first
    grid = np.bincount(keys, minlength=len(stores) * len(items) * days).reshape(-1, days)
    present = grid > 0
    duplicates = int((grid - present).sum())
    date_counts = present.sum(axis=1)
    detail = []
    for index, count in enumerate(date_counts):
        positions = np.flatnonzero(present[index])
        interior = int(positions[-1] - positions[0] + 1 - count) if len(positions) else None
        detail.append(
            {
                "store": int(stores[index // len(items)]),
                "item": int(items[index % len(items)]),
                "observed_dates": int(count),
                "expected_dates": days,
                "missing_dates_global_window": int(days - count),
                "missing_dates_within_series_bounds": interior,
            }
        )
    profile = {
        "stores": len(stores),
        "products": len(items),
        "observed_series": int((date_counts > 0).sum()),
        "expected_series": len(detail),
        "days": days,
        "date_min": str(np.datetime64(first, "D")),
        "date_max": str(np.datetime64(last, "D")),
        "duplicate_business_keys_after_first": duplicates,
        "missing_store_item_combinations": int((date_counts == 0).sum()),
        "missing_dates_global_window": int((~present).sum()),
        "missing_dates_per_series": detail,
    }
    return profile, stores, items, dates, keys


def _indexes(values: np.ndarray, domain: np.ndarray, label: str) -> np.ndarray:
    result = pd.Index(domain.astype(str)).get_indexer(values)
    _require(bool((result >= 0).all()), f"Canonical has extra/invalid {label} identifiers")
    return result


def _write_report(directory: Path, report: dict) -> None:
    write_json(directory / "store_item_canonical_audit.json", report)
    lines = [
        "# Store Item independent source-to-Parquet audit",
        "",
        f"Status: {report['status']}",
        "",
        "Typed Arrow CSV parsing and NumPy key grids are independent of the pandas transformation.",
        "Competition test records are unlabelled and excluded from observed sales.",
        "",
    ]
    for error in report["critical_errors"]:
        lines.append(f"- Critical: {error}")
    if report["status"] == "passed":
        lines += [
            f"- Source / canonical rows: {report['source_rows']:,} / {report['canonical_rows']:,}",
            f"- Source / canonical sales: {report['source_sales_units_sum']:,} / "
            f"{report['canonical_sales_units_sum']:,}",
            f"- Row-level sales mismatches: {report['row_level_sales_mismatches']}",
            f"- Duplicate canonical business keys: {report['duplicate_business_keys']}",
            f"- Missing source/canonical historical days: "
            f"{report['train']['missing_dates_global_window']} / "
            f"{report['canonical_missing_keys']}",
            f"- Historical dates: {report['train']['date_min']} to {report['train']['date_max']}",
            f"- Historical series: {report['train']['observed_series']}",
            f"- Raw hashes unchanged and matching acquisition: {report['raw_hashes_unchanged']}",
            "",
            "The prior missing-date statement was informational; no calendar gaps were found.",
            "The zero-sales record is preserved and matches Parquet. It is not treated as missing.",
            "Sales are observations, not verified unconstrained demand.",
        ]
    (directory / "store_item_canonical_audit.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def audit_store_item(config: ProjectConfig) -> dict:
    """Verify raw files, every persisted key/value and coverage without writing datasets."""
    started = time.perf_counter()
    raw = config.paths["raw"] / "store_item"
    output = config.paths["processed"] / "store_item/daily_sales.parquet"
    directory = config.paths["reports"] / "data_quality"
    report = {
        "dataset": "store_item",
        "status": "invalid",
        "critical_errors": [],
        "checked_at_utc": datetime.now(UTC).isoformat(),
    }
    try:
        manifest = json.loads((raw / "acquisition.json").read_text(encoding="utf-8-sig"))
        baseline = {r["filename"]: r.get("sha256") for r in manifest["files"]}
        paths = {name: raw / name for name in ("train.csv", "test.csv")}
        if (raw / "sample_submission.csv").is_file():
            paths["sample_submission.csv"] = raw / "sample_submission.csv"
        before = {name: sha256(path) for name, path in paths.items()}
        _require(
            all(baseline.get(name) == digest for name, digest in before.items()),
            "Raw source hashes do not match the acquisition baseline",
        )
        output_before = sha256(output)
        train, train_schema = _source(paths["train.csv"], labelled=True)
        test, test_schema = _source(paths["test.csv"], labelled=False)
        train_profile, stores, items, train_dates, keys = _coverage(train)
        test_profile, test_stores, test_items, test_dates, _ = _coverage(test)
        report.update(train={**train_schema, **train_profile}, test={**test_schema, **test_profile})
        for name in ("train", "test"):
            p = report[name]
            _require(
                p["duplicate_business_keys_after_first"] == 0, f"{name}: duplicate business keys"
            )
            _require(p["missing_dates_global_window"] == 0, f"{name}: historical/panel date gaps")
            _require(
                p["missing_store_item_combinations"] == 0, f"{name}: missing series combinations"
            )
        _require(
            np.array_equal(stores, test_stores) and np.array_equal(items, test_items),
            "Training and competition test series universes differ",
        )
        _require(
            int(test_dates.min()) == int(train_dates.max()) + 1,
            "Competition test dates must follow labelled history without overlap",
        )
        ids = _array(test, "id")
        _require(np.unique(ids).size == ids.size, "Duplicate competition test IDs")
        units = _array(train, "sales")
        report.update(
            source_rows=train.num_rows,
            source_sales_units_sum=int(units.sum()),
            source_zero_sales_observations=int((units == 0).sum()),
            negative_source_sales=int((units < 0).sum()),
        )
        _require(
            report["negative_source_sales"] == 0, "Negative source sales require investigation"
        )
        days = train_profile["days"]
        expected = len(stores) * len(items) * days
        source_values = np.full(expected, -1, dtype="int64")
        source_values[keys] = units
        seen = np.zeros(expected, dtype=bool)
        parquet = pq.ParquetFile(output)
        schema = {field.name: field.type for field in parquet.schema_arrow}
        _require(schema == PARQUET_TYPES, "Canonical Parquet physical schema mismatch")
        _require(parquet.metadata.num_rows == train.num_rows, "Source/canonical row counts differ")
        report["canonical_schema"] = {name: str(dtype) for name, dtype in schema.items()}
        total = rows = duplicate_keys = value_mismatches = canonical_zeros = 0
        null_counts = dict.fromkeys(PARQUET_TYPES, 0)
        series_pairs = {}
        zero_matches = []
        for batch in parquet.iter_batches(batch_size=65536):
            batch.validate(full=True)
            for name in PARQUET_TYPES:
                null_counts[name] += batch.column(batch.schema.get_field_index(name)).null_count
            required = set(PARQUET_TYPES) - {"category_id", "unit_price"}
            _require(
                all(null_counts[name] == 0 for name in required), "Missing canonical core fields"
            )
            frame = batch.to_pandas(date_as_object=False)
            _require(
                bool(frame.dataset_id.eq("store_item").all()), "Wrong canonical dataset namespace"
            )
            _require(bool(frame.is_observed.eq(True).all()), "Canonical includes unobserved rows")
            _require(
                bool(frame.series_id.str.len().gt(0).all()), "Empty canonical series identifiers"
            )
            _require(
                bool(frame.category_id.isna().all() and frame.unit_price.isna().all()),
                "Unavailable Store Item category/price values were populated",
            )
            store_indexes = _indexes(frame.store_id.to_numpy(), stores, "store")
            item_indexes = _indexes(frame.item_id.to_numpy(), items, "item")
            pairs = store_indexes * len(items) + item_indexes
            dates = batch.column(batch.schema.get_field_index("date")).cast(pa.int32()).to_numpy()
            offsets = dates - int(train_dates.min())
            _require(
                bool(((offsets >= 0) & (offsets < days)).all()),
                "Canonical dates extend outside labelled history (possible test contamination)",
            )
            indexes = pairs * days + offsets
            unique = np.unique(indexes)
            duplicate_keys += len(indexes) - len(unique) + int(seen[unique].sum())
            seen[unique] = True
            quantities = frame.sales_units.to_numpy()
            _require(
                bool(
                    np.isfinite(quantities).all()
                    and (quantities >= 0).all()
                    and (quantities % 1 == 0).all()
                ),
                "Invalid canonical sales quantities",
            )
            integers = quantities.astype("int64")
            value_mismatches += int((integers != source_values[indexes]).sum())
            total += int(integers.sum())
            canonical_zeros += int((integers == 0).sum())
            labels = pd.DataFrame({"pair": pairs, "series_id": frame.series_id}).drop_duplicates()
            for pair, label in labels.itertuples(index=False, name=None):
                _require(
                    pair not in series_pairs or series_pairs[pair] == label,
                    "One business series has multiple canonical IDs",
                )
                series_pairs[pair] = label
            for index in np.flatnonzero(integers == 0)[:100]:
                zero_matches.append(
                    {
                        "date": frame.date.iloc[index].strftime("%Y-%m-%d"),
                        "store": str(frame.store_id.iloc[index]),
                        "item": str(frame.item_id.iloc[index]),
                        "sales_units": 0,
                        "source_and_canonical_match": bool(source_values[indexes[index]] == 0),
                    }
                )
            rows += len(frame)
        _require(duplicate_keys == 0, "Duplicate canonical business keys")
        _require(bool(seen.all()), "Missing canonical historical keys")
        _require(value_mismatches == 0, "Canonical row-level sales differ from CSV source")
        _require(total == report["source_sales_units_sum"], "Source/canonical sales totals differ")
        _require(
            len(series_pairs) == len(stores) * len(items)
            and len(set(series_pairs.values())) == len(series_pairs),
            "Series ID mapping is not bijective",
        )
        after = {name: sha256(path) for name, path in paths.items()}
        _require(before == after, "Raw source hashes changed during audit")
        _require(output_before == sha256(output), "Canonical file changed during audit")
        report.update(
            status="passed",
            canonical_rows=rows,
            expected_rows=expected,
            canonical_sales_units_sum=total,
            row_level_sales_mismatches=value_mismatches,
            duplicate_business_keys=duplicate_keys,
            canonical_missing_keys=int((~seen).sum()),
            canonical_series=len(series_pairs),
            extra_or_missing_canonical_series=0,
            canonical_zero_sales_observations=canonical_zeros,
            zero_sales_records=zero_matches,
            canonical_null_counts=null_counts,
            raw_hashes_unchanged=True,
            raw_hashes_match_acquisition=True,
            source_sha256=after,
            canonical_sha256=output_before,
            unlabelled_test_rows=test.num_rows,
            unlabelled_test_rows_in_canonical=0,
            test_sales_total=None,
            test_id_duplicates=0,
            method="Typed Arrow CSV reader; NumPy full historical key grid; batched persisted "
            "row-by-row sales comparison; series-ID bijection independent of ID encoding",
            warnings=["Sales are observations, not verified unconstrained demand."],
        )
    except (OSError, ValueError, KeyError, pa.ArrowException) as exc:
        report["critical_errors"].append(str(exc))
        report["failure_type"] = type(exc).__name__
    report["elapsed_seconds"] = time.perf_counter() - started
    _write_report(directory, report)
    # Enrich the existing profiling report only when it describes these exact audited files.
    profile_path = directory / "store_item.json"
    if report["status"] == "passed" and profile_path.is_file():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        recorded = {r["filename"]: r.get("sha256") for r in profile["inventory"]["files"]}
        if profile["transformation"].get("sha256") == report["canonical_sha256"] and all(
            recorded.get(name) == digest for name, digest in report["source_sha256"].items()
        ):
            from intelligent_demand.validation.pipeline import _save_report

            original = "Missing calendar dates are not filled; sales are not unconstrained demand."
            profile["warnings"] = [
                warning for warning in profile["warnings"] if warning != original
            ]
            risk = "Sales are observations, not verified unconstrained demand."
            if risk not in profile["warnings"]:
                profile["warnings"].append(risk)
            note = (
                "Independent audit found zero missing historical dates in every store/item series. "
                "The earlier missing-date warning described a no-imputation policy, not a data gap."
            )
            if note not in profile.setdefault("notes", []):
                profile["notes"].append(note)
            profile["independent_audit"] = {
                "status": "passed",
                "checked_at_utc": report["checked_at_utc"],
                "missing_dates_global_window": report["train"]["missing_dates_global_window"],
                "duplicate_business_keys": report["duplicate_business_keys"],
                "row_level_sales_mismatches": report["row_level_sales_mismatches"],
                "canonical_sha256": report["canonical_sha256"],
                "report": "reports/data_quality/store_item_canonical_audit.json",
            }
            for name, audit_profile in (
                ("train.csv", report["train"]),
                ("test.csv", report["test"]),
            ):
                profile["profiles"][name].update(
                    stores=audit_profile["stores"],
                    products=audit_profile["products"],
                    series=audit_profile["observed_series"],
                    missing_historical_dates=audit_profile["missing_dates_global_window"],
                )
            _save_report(profile_path, profile)
    return report
