"""Reproducible training-only full-population EDA over immutable audited Parquet."""

import ctypes
import gc
import json
import logging
import os
import platform
import subprocess
import time
from datetime import date
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from intelligent_demand.config import ProjectConfig
from intelligent_demand.evaluation.design import chronological_plan
from intelligent_demand.exploration.statistics import (
    PATTERNS,
    aggregate_diagnostics,
    panel_statistics,
    price_activity,
    weekday_bootstrap,
)
from intelligent_demand.ingestion.datasets import select_datasets, sha256, write_json
from intelligent_demand.validation.quality import series_key

LOGGER = logging.getLogger(__name__)


def execution_provenance(root: Path) -> dict:
    """Record local code/environment identity without reading remotes or credentials."""
    package = Path(__file__).parent.parent
    sources = [
        *package.joinpath("exploration").glob("*.py"),
        *package.joinpath("evaluation").glob("*.py"),
        package / "__main__.py",
    ]
    git = ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root)]
    revision, dirty = None, None
    try:
        revision = subprocess.run(
            git + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                git + ["status", "--porcelain"], capture_output=True, text=True, check=True
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        pass
    return {
        "git_revision": revision,
        "git_working_tree_dirty": dirty,
        "python": platform.python_version(),
        "package_versions": {
            name: version(name)
            for name in ("numpy", "pandas", "pyarrow", "statsmodels", "matplotlib")
        },
        "analysis_source_sha256": {str(p.relative_to(package)): sha256(p) for p in sources},
    }


def peak_memory_bytes() -> int | None:
    """Read the current Windows worker's OS high-water working set without extra packages."""
    if os.name != "nt":
        return None

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t)
            for name in (
                "peak",
                "working",
                "quota_peak_paged",
                "quota_paged",
                "quota_peak_nonpaged",
                "quota_nonpaged",
                "pagefile",
                "peak_pagefile",
            )
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(Counters),
        ctypes.c_ulong,
    ]
    if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return int(counters.peak)
    return None


def load_settings(path: Path) -> dict:
    settings = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key in (
        "horizon_days",
        "validation_windows",
        "batch_rows",
        "bootstrap_replicates",
        "bootstrap_block_weeks",
        "figure_dpi",
    ):
        if type(settings.get(key)) is not int or settings[key] < 1:
            raise ValueError(f"Positive integer required: {key}")
    if type(settings.get("random_seed")) is not int or settings["random_seed"] < 0:
        raise ValueError("Nonnegative integer random_seed required")
    if settings.get("adi_threshold", 0) <= 0 or settings.get("cv2_threshold", 0) <= 0:
        raise ValueError("Positive classification thresholds required")
    return settings


def _metadata(name: str, raw: Path) -> pd.DataFrame:
    if name == "store_item":
        meta = pd.read_csv(raw / "train.csv", usecols=["store", "item"], dtype="string")
        meta = meta.drop_duplicates().rename(columns={"store": "store_id", "item": "item_id"})
    else:
        meta = pd.read_csv(
            raw / "sales_train_evaluation.csv",
            dtype="string",
            usecols=["store_id", "item_id", "cat_id", "dept_id", "state_id"],
        )
    if meta.duplicated(["store_id", "item_id"]).any():
        raise ValueError("Source metadata series keys not unique")
    meta["series_id"] = series_key(meta.store_id, meta.item_id)
    return meta.sort_values(["store_id", "item_id"]).reset_index(drop=True)


def _table(directory: Path, name: str, frame: pd.DataFrame) -> None:
    frame.to_parquet(directory / f"{name}.parquet", index=False, compression="zstd")


def _hist_quantile(hist: np.ndarray, probability: float) -> int:
    return int(np.searchsorted(hist.cumsum(), max(1, np.ceil(probability * hist.sum()))))


def analyse_dataset(name: str, config: ProjectConfig, settings: dict) -> dict:
    started = time.perf_counter()
    evidence_dir = config.paths["reports"] / "data_quality"
    audit = json.loads((evidence_dir / f"{name}_canonical_audit.json").read_text(encoding="utf-8"))
    reference = json.loads((evidence_dir / f"{name}.json").read_text(encoding="utf-8"))
    if audit["status"] != "passed":
        raise ValueError("Independent Phase 1 audit must pass before EDA")
    raw = config.paths["raw"] / name
    hashes = {file: sha256(raw / file) for file in audit["source_sha256"]}
    if hashes != audit["source_sha256"]:
        raise ValueError("Raw files changed since Phase 1")
    canonical = config.paths["processed"] / name / "daily_sales.parquet"
    digest = sha256(canonical)
    if digest != audit["canonical_sha256"]:
        raise ValueError("Canonical file changed since independent audit")
    p = reference["profiles"]["train.csv" if name == "store_item" else "sales_train_evaluation.csv"]
    plan = chronological_plan(
        date.fromisoformat(p["date_min"]),
        date.fromisoformat(p["date_max"]),
        settings["horizon_days"],
        settings["validation_windows"],
    )
    dates = pd.date_range(p["date_min"], p["date_max"], freq="D")
    training_dates = dates[dates <= pd.Timestamp(plan["eda_end"])]
    meta = _metadata(name, raw)
    indexes = pd.Index(meta.series_id)
    n, t = len(meta), len(training_dates)
    values = np.full((n, t), -1.0, dtype="float64")
    missing_prices = np.zeros((n, t), dtype=bool) if name == "m5" else None
    store_codes, stores = pd.factorize(meta.store_id, sort=True)
    item_codes, items = pd.factorize(meta.item_id, sort=True)
    all_days_count = np.zeros(len(dates), dtype="int64")
    all_days_missing = np.zeros(len(dates), dtype="int64")
    missing_items, missing_stores = (
        np.zeros(len(items), dtype="int64"),
        np.zeros(len(stores), dtype="int64"),
    )
    histogram = np.zeros(1, dtype="int64")
    rows, total, zeros = 0, 0.0, 0
    base = int(np.datetime64(dates[0].date(), "D").astype(int))
    projection = ["dataset_id", "series_id", "date", "sales_units", "unit_price"]
    LOGGER.info(
        "%s: EDA %s to %s; all %s series; validation/test sales quarantined",
        name,
        plan["eda_start"],
        plan["eda_end"],
        n,
    )
    for number, batch in enumerate(
        pq.ParquetFile(canonical).iter_batches(
            batch_size=settings["batch_rows"], columns=projection
        )
    ):
        frame = batch.to_pandas(date_as_object=False)
        codes = indexes.get_indexer(frame.series_id)
        day = batch.column(2).cast(pa.int32()).to_numpy() - base
        sales = frame.sales_units.to_numpy()
        if (codes < 0).any() or (day < 0).any() or (day >= len(dates)).any():
            raise ValueError("Unknown canonical series/date")
        if not frame.dataset_id.eq(name).all() or not np.isfinite(sales).all() or (sales < 0).any():
            raise ValueError("Invalid canonical observations")
        mask = frame.unit_price.isna().to_numpy()
        # Full-history quantities are used only for reconciliation to already-known Phase 1 totals.
        rows += len(frame)
        total += float(sales.sum())
        zeros += int((sales == 0).sum())
        all_days_count += np.bincount(day, minlength=len(dates))
        all_days_missing += np.bincount(day, weights=mask, minlength=len(dates)).astype("int64")
        missing_items += np.bincount(item_codes[codes], weights=mask, minlength=len(items)).astype(
            "int64"
        )
        missing_stores += np.bincount(
            store_codes[codes], weights=mask, minlength=len(stores)
        ).astype("int64")
        allowed = day < t
        values[codes[allowed], day[allowed]] = sales[allowed]
        if missing_prices is not None:
            missing_prices[codes[allowed], day[allowed]] = mask[allowed]
        if allowed.any():
            integers = sales[allowed].astype("int64")
            if integers.max() > 1_000_000 or (integers != sales[allowed]).any():
                raise ValueError("Exact integer histogram limit exceeded")
            h = np.bincount(integers)
            if len(h) > len(histogram):
                histogram = np.pad(histogram, (0, len(h) - len(histogram)))
            histogram[: len(h)] += h
        if number % 50 == 0:
            LOGGER.info("%s: scanned %s rows", name, rows)
    q = reference["quantities"]["train.sales" if name == "store_item" else "history.sales"]
    if (
        rows != reference["transformation"]["rows"]
        or total != q["finite_value_sum"]
        or zeros != q["zero"]
        or (all_days_count != n).any()
        or (values < 0).any()
    ):
        raise ValueError("Full-history or EDA coverage reconciliation failed")
    report_dir = config.paths["reports"] / "eda"
    table_dir = report_dir / "tables" / name
    table_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info("%s: computing population intermittency, calendar and correlation summaries", name)
    statistics = panel_statistics(values, settings["adi_threshold"], settings["cv2_threshold"])
    series = pd.concat([meta, statistics], axis=1)
    _table(table_dir, "series", series)
    daily = pd.DataFrame(
        {
            "date": training_dates,
            "sales_units": values.sum(axis=0),
            "zero_percent": 100 * (values == 0).sum(axis=0) / n,
        }
    )
    daily["mean_28d"] = daily.sales_units.rolling(28, min_periods=28).mean()
    daily["cv_28d"] = daily.sales_units.rolling(28).std() / daily.mean_28d.replace(0, np.nan)
    _table(table_dir, "daily", daily)
    monthly = daily.groupby(daily.date.dt.to_period("M")).agg(
        sales_units=("sales_units", "sum"),
        observed_days=("sales_units", "size"),
        mean_daily_units=("sales_units", "mean"),
    )
    monthly.index = monthly.index.astype(str)
    monthly = monthly.rename_axis("month").reset_index()
    monthly["complete_month"] = (
        monthly.observed_days == pd.to_datetime(monthly.month).dt.days_in_month
    )
    _table(table_dir, "monthly", monthly)
    calendar = daily.assign(
        year=daily.date.dt.year, month=daily.date.dt.month, weekday=daily.date.dt.day_of_week
    )
    annual = calendar.groupby("year").agg(days=("date", "size"), mean=("sales_units", "mean"))
    complete_years = annual.index[
        annual.days == [366 if pd.Timestamp(y, 12, 31).is_leap_year else 365 for y in annual.index]
    ]
    month_year = (
        calendar[calendar.year.isin(complete_years)]
        .groupby(["year", "month"])
        .sales_units.mean()
        .reset_index()
    )
    month_year["within_year_daily_index"] = month_year.sales_units / month_year.year.map(
        annual["mean"]
    )
    _table(table_dir, "month_year", month_year)
    weekdays = weekday_bootstrap(
        daily,
        settings["random_seed"],
        settings["bootstrap_replicates"],
        settings["bootstrap_block_weeks"],
    )
    _table(table_dir, "weekdays", weekdays)
    acf_table, components, diagnostics = aggregate_diagnostics(daily)
    _table(table_dir, "acf", acf_table)
    _table(table_dir, "components", components)
    product = series.groupby("item_id", as_index=False).agg(
        sales_units=("sales_units", "sum"),
        series=("series_id", "size"),
        mean_zero_percent=("zero_percent", "mean"),
    )
    product = product.sort_values("sales_units", ascending=False).reset_index(drop=True)
    product["share"] = product.sales_units / product.sales_units.sum()
    product["cumulative_share"] = product.share.cumsum()
    _table(table_dir, "products", product)
    store = series.groupby("store_id", as_index=False).agg(
        sales_units=("sales_units", "sum"),
        series=("series_id", "size"),
        mean_zero_percent=("zero_percent", "mean"),
        mean_series_cv2=("cv2_positive", "mean"),
    )
    store["mean_units_per_series_day"] = store.sales_units / (store.series * t)
    _table(table_dir, "stores", store)
    store_daily = []
    for code, store_id in enumerate(stores):
        store_daily.append(
            pd.DataFrame(
                {
                    "date": training_dates,
                    "store_id": store_id,
                    "sales_units": values[store_codes == code].sum(axis=0),
                }
            )
        )
    store_daily = pd.concat(store_daily, ignore_index=True)
    _table(table_dir, "store_daily", store_daily)
    _table(
        table_dir,
        "store_weekday",
        store_daily.assign(weekday=store_daily.date.dt.day_of_week)
        .groupby(["store_id", "weekday"], as_index=False)
        .sales_units.mean(),
    )
    classifications = series.pattern.value_counts().reindex(PATTERNS, fill_value=0)
    active_classifications = series.active_span_pattern.value_counts().reindex(
        PATTERNS, fill_value=0
    )
    _table(
        table_dir,
        "patterns",
        pd.DataFrame(
            {
                "pattern": PATTERNS,
                "series": classifications.to_numpy(),
                "active_span_series": active_classifications.to_numpy(),
            }
        ),
    )
    hist = pd.DataFrame({"units": np.arange(len(histogram)), "observations": histogram})
    _table(table_dir, "distribution", hist[hist.observations > 0])
    # Illustrations are deterministic and stratified, not population estimates.
    illustrations = []
    selections = []
    for pattern in PATTERNS:
        subset = series[series.pattern == pattern]
        if subset.empty:
            continue
        ranked = subset.sort_values(["zero_percent", "mean_units", "series_id"])
        selected = ranked.iloc[len(ranked) // 2]
        index = int(selected.name)
        selections.append(
            {
                "pattern": pattern,
                "series_id": selected.series_id,
                "selection": "median rank by zero percentage, mean units, then ID within class",
            }
        )
        illustrations.append(
            pd.DataFrame(
                {
                    "date": training_dates,
                    "sales_units": values[index],
                    "series_id": selected.series_id,
                    "pattern": pattern,
                }
            )
        )
    _table(table_dir, "representative_series", pd.concat(illustrations, ignore_index=True))
    largest = []
    for first in range(0, n, 256):
        block = values[first : first + 256]
        flat = block.ravel()
        positions = np.argpartition(flat, -min(20, flat.size))[-min(20, flat.size) :]
        for position in positions:
            row, day = np.unravel_index(position, block.shape)
            largest.append(
                {
                    "series_id": meta.series_id.iloc[first + row],
                    "date": training_dates[day],
                    "sales_units": float(block[row, day]),
                }
            )
    extremes = (
        pd.DataFrame(largest)
        .sort_values(["sales_units", "series_id", "date"], ascending=[False, True, True])
        .head(20)
    )
    _table(table_dir, "largest_observations", extremes)
    if not (
        float(statistics.sales_units.sum())
        == float(daily.sales_units.sum())
        == float(product.sales_units.sum())
        == float(store.sales_units.sum())
        == float(np.dot(np.arange(len(histogram)), histogram))
    ):
        raise ValueError("Analytical aggregation totals disagree")
    result = {
        "dataset": name,
        "scope": "all series, EDA training prefix only unless marked full-history quality",
        "split_plan": plan,
        "eda_rows": n * t,
        "eda_days": t,
        "series": n,
        "eda_sales_units": int(daily.sales_units.sum()),
        "eda_zero_count": int(histogram[0]),
        "eda_zero_percent": float(100 * histogram[0] / histogram.sum()),
        "full_history_reference": {"rows": rows, "sales_units": int(total), "zero_count": zeros},
        "distribution_quantiles": {
            str(q): _hist_quantile(histogram, q) for q in (0.5, 0.9, 0.95, 0.99, 0.999, 1.0)
        },
        "patterns": {key: int(value) for key, value in classifications.items()},
        "active_span_patterns": {key: int(value) for key, value in active_classifications.items()},
        "classification_changed_after_removing_leading_zeros": int(
            (series.pattern != series.active_span_pattern).sum()
        ),
        "median_series_cv": float(
            (series.std_units / series.mean_units.replace(0, np.nan)).median()
        ),
        "median_series_corr_lag7": float(series.corr_lag_7.median()),
        "median_series_corr_lag365": float(series.corr_lag_365.median()),
        "product_top10_percent_share": float(
            product.share.iloc[: int(np.ceil(0.1 * len(product)))].sum()
        ),
        "product_hhi": float(np.square(product.share).sum()),
        "weekday_ratios": weekdays.to_dict("records"),
        "diagnostics": diagnostics,
        "illustration_selection": selections,
        "sampling_seed": settings["random_seed"],
        "input_canonical_sha256": digest,
        "input_raw_sha256": hashes,
        "output_reconciliation_passed": True,
    }
    if name == "m5":
        assert missing_prices is not None
        price_frame, price_info = price_activity(missing_prices, values)
        _table(table_dir, "price_by_series_eda", pd.concat([meta, price_frame], axis=1))
        price_dates = pd.DataFrame(
            {
                "date": dates,
                "observations": all_days_count,
                "missing_prices": all_days_missing,
                "eda_period": np.arange(len(dates)) < t,
            }
        )
        _table(table_dir, "price_by_date_full_quality", price_dates)
        _table(
            table_dir,
            "price_by_year_full_quality",
            price_dates.groupby(price_dates.date.dt.year)
            .agg(observations=("observations", "sum"), missing_prices=("missing_prices", "sum"))
            .rename_axis("year")
            .reset_index(),
        )
        _table(
            table_dir,
            "price_by_product_full_quality",
            pd.DataFrame(
                {
                    "item_id": items,
                    "missing_prices": missing_items,
                    "observations": len(stores) * len(dates),
                }
            ),
        )
        _table(
            table_dir,
            "price_by_store_full_quality",
            pd.DataFrame(
                {
                    "store_id": stores,
                    "missing_prices": missing_stores,
                    "observations": len(items) * len(dates),
                }
            ),
        )
        expected_missing = reference["transformation"]["missing_price_observations"]
        if not (
            int(all_days_missing.sum())
            == int(missing_items.sum())
            == int(missing_stores.sum())
            == expected_missing
        ):
            raise ValueError("Full missing-price coverage does not reconcile")
        result["price_missingness"] = {
            "full_history_missing": expected_missing,
            "reserved_period_missing": int(all_days_missing[t:].sum()),
            "eda_activity_partition": price_info,
            "interpretation": "Positive sales are activity proxies; availability is unverified",
        }
        calendar_source = pd.read_csv(raw / "calendar.csv", parse_dates=["date"])
        joined = daily.merge(calendar_source, on="date", validate="one_to_one")
        if len(joined) != t:
            raise ValueError("EDA calendar join lost observations")
        events = (
            joined.melt(
                id_vars=["date", "sales_units"],
                value_vars=["event_name_1", "event_name_2"],
                value_name="event",
            )
            .dropna(subset=["event"])
            .drop_duplicates(["date", "event"])
        )
        event_summary = events.groupby("event", as_index=False).agg(
            days=("date", "size"), mean_total_units=("sales_units", "mean")
        )
        _table(table_dir, "calendar_events", event_summary)
        snap = []
        states = meta[["store_id", "state_id"]].drop_duplicates()
        snap_daily = store_daily.merge(states, on="store_id", validate="many_to_one").merge(
            calendar_source[["date", "snap_CA", "snap_TX", "snap_WI"]],
            on="date",
            validate="many_to_one",
        )
        for state, frame in snap_daily.groupby("state_id"):
            flag = frame[f"snap_{state}"]
            for status in (0, 1):
                selected = frame[flag == status]
                snap.append(
                    {
                        "state": state,
                        "snap_flag": status,
                        "store_days": len(selected),
                        "mean_store_daily_units": float(selected.sales_units.mean()),
                    }
                )
        _table(table_dir, "snap_associations", pd.DataFrame(snap))
        for group in ("cat_id", "dept_id"):
            group_daily = []
            for value in sorted(meta[group].unique()):
                group_daily.append(
                    pd.DataFrame(
                        {
                            "date": training_dates,
                            "group": value,
                            "sales_units": values[meta[group].eq(value).to_numpy()].sum(axis=0),
                        }
                    )
                )
            _table(table_dir, f"{group}_daily", pd.concat(group_daily, ignore_index=True))
    if digest != sha256(canonical) or hashes != {file: sha256(raw / file) for file in hashes}:
        raise ValueError("Audited input files changed during EDA")
    result["elapsed_analysis_seconds"] = time.perf_counter() - started
    result["peak_worker_working_set_bytes_cumulative"] = peak_memory_bytes()
    result["settings"] = settings
    write_json(report_dir / f"{name}_results.json", result)
    del values, missing_prices
    gc.collect()
    return result


def run_eda(config: ProjectConfig, selection: str, settings_path: Path) -> dict:
    """Execute population analysis, figures and reports; never call a forecasting model."""
    os.environ.setdefault("MPLCONFIGDIR", str(config.paths["artifacts"] / "matplotlib_cache"))
    from intelligent_demand.exploration.reporting import comparative_report, dataset_report, figures

    started = time.perf_counter()
    settings = load_settings(settings_path)
    results = {}
    for spec in select_datasets(selection):
        result = analyse_dataset(spec.name, config, settings)
        figures(config, result)
        dataset_report(config, result)
        results[spec.name] = result
    if len(results) == 2:
        comparative_report(config, results)
        from intelligent_demand.exploration.validation import validate_outputs

        validate_outputs(config)
    report_dir = config.paths["reports"] / "eda"
    manifest = {
        "status": "passed",
        "datasets": list(results),
        "settings_sha256": sha256(settings_path),
        **execution_provenance(settings_path.resolve().parent.parent),
        "elapsed_seconds": time.perf_counter() - started,
        "models_trained": 0,
        "validation_test_targets_explored": False,
        "full_history_scope_exception": "Audited totals and label-free price coverage only",
        "peak_worker_working_set_bytes": peak_memory_bytes(),
    }
    write_json(report_dir / "run_manifest.json", manifest)
    return manifest
