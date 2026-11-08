"""Chunked Store Item source validation; no cleaning or imputation."""

from pathlib import Path

import numpy as np
import pandas as pd

from intelligent_demand.validation.quality import (
    CanonicalWriter,
    issue,
    numeric_values,
    profile_frame,
    series_key,
)


def transform_store_item(raw: Path, writer: CanonicalWriter, report: dict) -> None:
    """Validate train/test separately and emit only observed training sales."""
    stores, items = set(), set()
    coverage = []
    for filename in ("train.csv", "test.csv"):
        seen = set()
        duplicate_count = 0
        required = {"date", "store", "item"} | ({"sales"} if filename == "train.csv" else {"id"})
        header = pd.read_csv(raw / filename, nrows=0).columns
        if not required.issubset(header):
            issue(report, f"{filename}: required columns missing")
            continue
        for chunk in pd.read_csv(raw / filename, dtype="string", chunksize=100_000):
            profile_frame(report, filename, chunk)
            dates = pd.to_datetime(chunk["date"], format="%Y-%m-%d", errors="coerce")
            if dates.isna().any() or chunk[["store", "item"]].isna().any().any():
                issue(report, f"{filename}: invalid dates or missing identifiers")
            keys = list(zip(chunk["store"], chunk["item"], chunk["date"], strict=True))
            for key in keys:
                duplicate_count += key in seen
                seen.add(key)
            if dates.notna().any():
                bounds = [dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d")]
                profile = report["profiles"][filename]
                profile["date_min"] = min(profile.get("date_min", bounds[0]), bounds[0])
                profile["date_max"] = max(profile.get("date_max", bounds[1]), bounds[1])
            if filename == "test.csv":
                continue
            stores.update(chunk["store"].dropna())
            items.update(chunk["item"].dropna())
            sales = numeric_values(chunk["sales"], report, "train.sales")
            valid_sales = np.isfinite(sales)
            if valid_sales.any():
                finite_sales = sales[valid_sales]
                stats = report.setdefault(
                    "sales_summary",
                    {"min": float(finite_sales.min()), "max": float(finite_sales.max())},
                )
                stats["min"] = min(stats["min"], float(finite_sales.min()))
                stats["max"] = max(stats["max"], float(finite_sales.max()))
            coverage.append(len(chunk))
            if not report["critical_errors"]:
                writer.append(
                    pd.DataFrame(
                        {
                            "dataset_id": "store_item",
                            "series_id": series_key(chunk.store, chunk.item),
                            "date": dates,
                            "sales_units": sales,
                            "store_id": chunk.store,
                            "item_id": chunk.item,
                            "category_id": None,
                            "unit_price": None,
                            "is_observed": True,
                        }
                    )
                )
        profile = report["profiles"].get(filename)
        if profile is None:
            issue(report, f"{filename}: no data rows")
        else:
            profile["duplicate_keys_after_first"] = duplicate_count
            if duplicate_count:
                issue(report, f"{filename}: duplicate store/item/date keys")
            if filename == "train.csv":
                profile.update(
                    stores=len(stores),
                    products=len(items),
                    series=len({(key[0], key[1]) for key in seen}),
                )
    report["transformation"]["expected_rows"] = sum(coverage)
    issue(report, "Sales are observations, not verified unconstrained demand.", False)
    report.setdefault("notes", []).append(
        "No calendar completion is performed. The independent audit measures actual date gaps; "
        "this policy statement is not evidence of missing observations."
    )
