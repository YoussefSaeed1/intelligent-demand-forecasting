"""Bounded wide-to-long M5 ingestion with validated calendar/price joins."""

import logging
from pathlib import Path

import pandas as pd

from intelligent_demand.ingestion.datasets import M5_IDS
from intelligent_demand.validation.quality import (
    CanonicalWriter,
    issue,
    numeric_values,
    profile_frame,
    series_key,
)

LOGGER = logging.getLogger(__name__)


def _days(path: Path) -> list[str]:
    return [c for c in pd.read_csv(path, nrows=0).columns if c.startswith("d_")]


def _fingerprints(chunk: pd.DataFrame, days: list[str]) -> dict:
    values = chunk[days].apply(pd.to_numeric, errors="coerce").astype("float64")
    hashes = pd.util.hash_pandas_object(values, index=False)
    return dict(zip(zip(chunk.store_id, chunk.item_id, strict=True), hashes, strict=True))


def transform_m5(raw: Path, writer: CanonicalWriter, report: dict) -> None:
    """Prefer evaluation history; never concatenate overlapping history variants."""
    LOGGER.info("m5: validating calendar and price dimensions")
    calendar = pd.read_csv(raw / "calendar.csv", dtype="string")
    profile_frame(report, "calendar.csv", calendar)
    required_calendar = {"d", "date", "wm_yr_wk"}
    if not required_calendar.issubset(calendar):
        issue(report, "calendar.csv: required columns missing")
        return
    calendar["date"] = pd.to_datetime(calendar.date, format="%Y-%m-%d", errors="coerce")
    calendar["wm_yr_wk"] = pd.to_numeric(calendar.wm_yr_wk, errors="coerce")
    report["profiles"]["calendar.csv"].update(
        duplicate_day_keys_after_first=int(calendar.d.duplicated().sum()),
        duplicate_date_keys_after_first=int(calendar.date.duplicated().sum()),
    )
    if calendar[list(required_calendar)].isna().any().any():
        issue(report, "calendar.csv: invalid day/date/week mapping")
    if calendar.wm_yr_wk.mod(1).ne(0).any():
        issue(report, "calendar.csv: week identifiers must be integral")
    if calendar.d.duplicated().any() or calendar.date.duplicated().any():
        issue(report, "calendar.csv: duplicate day or date mapping")
    parsed_days = calendar.d.str.extract(r"^d_(\d+)$", expand=False)
    if parsed_days.isna().any():
        issue(report, "calendar.csv: invalid day identifiers")
    else:
        ordered = calendar.assign(day_number=parsed_days.astype(int)).sort_values("day_number")
        if (ordered.day_number.diff().dropna() != 1).any() or (
            ordered.date.diff().dropna() != pd.Timedelta(days=1)
        ).any():
            issue(report, "calendar.csv: day/date mappings must advance together daily")
    # Categories and compact numeric columns keep the multi-million-row price table bounded.
    price_header = set(pd.read_csv(raw / "sell_prices.csv", nrows=0).columns)
    if not {"store_id", "item_id", "wm_yr_wk", "sell_price"}.issubset(price_header):
        issue(report, "sell_prices.csv: required columns missing")
        return
    prices = pd.read_csv(
        raw / "sell_prices.csv",
        dtype={
            "store_id": "category",
            "item_id": "category",
            "wm_yr_wk": "string",
            "sell_price": "string",
        },
    )
    profile_frame(report, "sell_prices.csv", prices)
    prices["wm_yr_wk"] = pd.to_numeric(prices.wm_yr_wk, errors="coerce")
    prices["sell_price"] = numeric_values(prices.sell_price, report, "sell_price")
    price_keys = ["store_id", "item_id", "wm_yr_wk"]
    duplicates = int(prices.duplicated(price_keys).sum())
    report["profiles"]["sell_prices.csv"]["duplicate_keys_after_first"] = duplicates
    if duplicates or prices[price_keys].isna().any().any():
        issue(report, "sell_prices.csv: duplicate or missing join keys")
    if prices.wm_yr_wk.mod(1).ne(0).any():
        issue(report, "sell_prices.csv: week identifiers must be integral")
    if not len(calendar) or not len(prices):
        issue(report, "Calendar and price tables must contain data rows")
    if report["critical_errors"]:
        return
    LOGGER.info("m5: calendar rows=%s; price rows=%s; join keys unique", len(calendar), len(prices))
    prices["wm_yr_wk"] = prices.wm_yr_wk.astype("int32")
    # Validate once, then reuse the index instead of refactorising millions of price
    # rows in every sales batch. A unique lookup cannot expand the observation grain.
    price_lookup = prices.set_index(price_keys)["sell_price"]
    if not price_lookup.index.is_unique:
        issue(report, "sell_prices.csv: nonunique price lookup index")
        return
    del prices
    selected = "sales_train_evaluation.csv"
    if not (raw / selected).is_file():
        selected = "sales_train_validation.csv"
        issue(report, "Evaluation history unavailable; using validation history only.", False)
    other = "sales_train_validation.csv"
    compare_overlap = selected != other and (raw / other).is_file()
    days = _days(raw / selected)
    other_days = _days(raw / other) if compare_overlap else []
    other_day_set = set(other_days)
    common_days = [day for day in days if day in other_day_set]
    if not days or not set(days).issubset(set(calendar.d)):
        issue(report, "Historical sales day columns lack complete calendar mappings")
        return
    expected_days = [f"d_{n}" for n in range(1, len(days) + 1)]
    if days != expected_days:
        issue(report, "Historical sales day columns must be ordered and contiguous from d_1")
        return
    report["transformation"].update(
        selected_history=selected,
        overlapping_history_concatenated=False,
        batch_series_rows=256,
        historical_day_columns=len(days),
        missing_price_observations=0,
        overlap_days_compared=len(common_days),
    )
    fingerprints = {}
    seen, stores, items, series_ids = set(), set(), set(), set()
    row_count = 0
    duplicate_count = 0
    identifier_types = dict.fromkeys(M5_IDS, "string")
    LOGGER.info("m5: transforming %s in batches of 256 series", selected)
    for chunk in pd.read_csv(raw / selected, dtype=identifier_types, chunksize=256):
        profile_frame(report, selected, chunk)
        if not set(M5_IDS).issubset(chunk):
            issue(report, f"{selected}: required identifiers missing")
            return
        if chunk[M5_IDS].isna().any().any():
            issue(report, f"{selected}: missing hierarchy identifiers")
        for key in zip(chunk.store_id, chunk.item_id, strict=True):
            duplicate_count += key in seen
            seen.add(key)
        if chunk.id.isin(series_ids).any() or chunk.id.duplicated().any():
            issue(report, f"{selected}: duplicate source id")
        series_ids.update(chunk.id)
        stores.update(chunk.store_id)
        items.update(chunk.item_id)
        row_count += len(chunk)
        if common_days:
            fingerprints.update(_fingerprints(chunk, common_days))
        long = chunk.melt(id_vars=M5_IDS, value_vars=days, var_name="d", value_name="sales")
        long["sales"] = numeric_values(long.sales, report, "history.sales")
        if report["critical_errors"]:
            continue
        joined = long.merge(
            calendar[["d", "date", "wm_yr_wk"]], on="d", how="left", validate="many_to_one"
        )
        lookup_keys = pd.MultiIndex.from_frame(joined[price_keys])
        joined["sell_price"] = price_lookup.reindex(lookup_keys).to_numpy()
        if len(joined) != len(long) or joined.date.isna().any():
            issue(report, "M5 joins changed row cardinality or lost calendar dates")
            continue
        report["transformation"]["missing_price_observations"] += int(
            joined.sell_price.isna().sum()
        )
        writer.append(
            pd.DataFrame(
                {
                    "dataset_id": "m5",
                    "series_id": series_key(joined.store_id, joined.item_id),
                    "date": joined.date,
                    "sales_units": joined.sales,
                    "store_id": joined.store_id,
                    "item_id": joined.item_id,
                    "category_id": joined.cat_id,
                    "unit_price": joined.sell_price,
                    "is_observed": True,
                }
            )
        )
        if row_count == 256 or row_count % (256 * 20) == 0:
            LOGGER.info("m5: processed %s series; emitted %s observations", row_count, writer.rows)
    if duplicate_count:
        issue(report, f"{selected}: duplicate store/item series")
    if not row_count:
        issue(report, f"{selected}: no history rows")
    if selected in report["profiles"]:
        profile = report["profiles"][selected]
        mapped = calendar[calendar.d.isin(days)]
        profile.update(
            stores=len(stores),
            products=len(items),
            series=len(seen),
            duplicate_keys_after_first=duplicate_count,
            date_min=mapped.date.min().strftime("%Y-%m-%d"),
            date_max=mapped.date.max().strftime("%Y-%m-%d"),
        )
    if compare_overlap:
        LOGGER.info("m5: checking %s overlapping days against %s", len(common_days), other)
        other_seen = set()
        matched = 0
        for chunk in pd.read_csv(raw / other, dtype=identifier_types, chunksize=256):
            profile_frame(report, other, chunk)
            if not set(M5_IDS).issubset(chunk):
                issue(report, f"{other}: identifiers missing")
                break
            if chunk.duplicated(["store_id", "item_id"]).any():
                issue(report, "Overlap history has duplicate store/item series")
            quantity = chunk[other_days].apply(pd.to_numeric, errors="coerce").to_numpy(float)
            numeric_values(pd.Series(quantity.ravel()), report, "overlap_history.sales")
            hashes = _fingerprints(chunk, common_days)
            for key, digest in hashes.items():
                if key in other_seen or key not in fingerprints or fingerprints[key] != digest:
                    issue(
                        report, "History variants contain duplicate, unmatched or conflicting rows"
                    )
                else:
                    matched += 1
                other_seen.add(key)
        report["transformation"]["overlap_series_matched"] = matched
        if other_seen != seen or not common_days or set(other_days) - set(days):
            issue(report, "History variants have incompatible series/day coverage")
    report["transformation"]["expected_rows"] = row_count * len(days)
    report["transformation"]["join_cardinality"] = "many_to_one; no row expansion permitted"
    if report["transformation"]["missing_price_observations"]:
        issue(report, "Missing historical prices retained as null; no imputation performed.", False)
    issue(
        report,
        "Historical prices are observed covariates, not guaranteed future information.",
        False,
    )
    issue(report, "Sales zeros do not prove item availability or zero unconstrained demand.", False)
