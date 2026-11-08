"""Independent bounded Phase 1/2 controls; never select canonical holdout values."""

import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from intelligent_demand.exploration.statistics import panel_statistics, price_activity

ROOT = Path(__file__).resolve().parents[3]
DEST = Path(__file__).parent / "data_eda_checks.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def header(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return next(csv.reader(stream))


def labels(adi, cv, count):
    result = []
    for a, c, n in zip(adi, cv, count, strict=True):
        if n == 0:
            result.append("all_zero")
        elif n < 2:
            result.append("insufficient_positive_history")
        elif a < 1.32:
            result.append("smooth" if c < 0.49 else "erratic")
        else:
            result.append("intermittent" if c < 0.49 else "lumpy")
    return np.array(result)


def check_dataset(name):
    result = load(ROOT / f"reports/eda/{name}_results.json")
    audit = load(ROOT / f"reports/data_quality/{name}_canonical_audit.json")
    tables = ROOT / f"reports/eda/tables/{name}"
    series = pd.read_parquet(tables / "series.parquet")
    series = series.sort_values(["store_id", "item_id"]).reset_index(drop=True)
    index = pd.MultiIndex.from_frame(series[["store_id", "item_id"]])
    assert index.is_unique
    dates = pd.date_range(result["split_plan"]["eda_start"], result["split_plan"]["eda_end"])
    n, t = len(series), len(dates)
    start = np.datetime64(dates[0].date(), "D").astype(int)
    seen = np.zeros(n * t, dtype=bool)
    count = np.zeros(n, np.int64)
    total = np.zeros(n, np.float64)
    square = np.zeros(n, np.float64)
    first = np.full(n, t, np.int64)
    daily_total = np.zeros(t, np.float64)
    daily_zero = np.zeros(t, np.int64)
    null_prices, negative, duplicate, rows = 0, 0, 0, 0
    path = ROOT / f"data/processed/{name}/daily_sales.parquet"
    parquet = pq.ParquetFile(path)
    assert parquet.metadata.num_rows == audit["canonical_rows"]
    expected_types = [
        pa.string(),
        pa.string(),
        pa.date32(),
        pa.float64(),
        pa.string(),
        pa.string(),
        pa.string(),
        pa.float64(),
        pa.bool_(),
    ]
    assert list(parquet.schema_arrow.types) == expected_types
    expression = (ds.field("date") >= pa.scalar(dates[0].date(), pa.date32())) & (
        ds.field("date") <= pa.scalar(dates[-1].date(), pa.date32())
    )
    columns = [
        "dataset_id",
        "store_id",
        "item_id",
        "date",
        "sales_units",
        "unit_price",
        "is_observed",
    ]
    scanner = ds.dataset(path, format="parquet").scanner(
        columns=columns, filter=expression, batch_size=65536, use_threads=False
    )
    for batch in scanner.to_batches():
        frame = batch.to_pandas(date_as_object=False)
        if frame.empty:
            continue
        assert frame.dataset_id.eq(name).all() and frame.is_observed.all()
        assert not frame[["store_id", "item_id", "date", "sales_units"]].isna().any().any()
        r = index.get_indexer(pd.MultiIndex.from_frame(frame[["store_id", "item_id"]]))
        d = batch.column(3).cast(pa.int32()).to_numpy() - start
        y = frame.sales_units.to_numpy()
        assert np.all(r >= 0) and np.all((d >= 0) & (d < t))
        assert np.isfinite(y).all() and (np.floor(y) == y).all()
        negative += int((y < 0).sum())
        pos = r * t + d
        unique = np.unique(pos)
        duplicate += len(pos) - len(unique) + int(seen[unique].sum())
        seen[unique] = True
        positive = y > 0
        count += np.bincount(r[positive], minlength=n)
        total += np.bincount(r, weights=y, minlength=n)
        square += np.bincount(r, weights=y * y, minlength=n)
        np.minimum.at(first, r[positive], d[positive])
        daily_total += np.bincount(d, weights=y, minlength=t)
        daily_zero += np.bincount(d[y == 0], minlength=t)
        null_prices += int(frame.unit_price.isna().sum())
        rows += len(frame)
    assert seen.all() and duplicate == negative == 0
    assert rows == result["eda_rows"] == n * t
    assert int(total.sum()) == result["eda_sales_units"]
    assert int(daily_zero.sum()) == result["eda_zero_count"]
    adi = np.divide(t, count, out=np.full(n, np.nan), where=count > 0)
    mean = np.divide(total, count, out=np.full(n, np.nan), where=count > 0)
    var = np.divide(
        square - np.divide(total * total, count, out=np.zeros(n), where=count > 0),
        count - 1,
        out=np.full(n, np.nan),
        where=count > 1,
    )
    cv = np.maximum(var, 0) / (mean * mean)
    np.testing.assert_allclose(adi, series.adi.to_numpy(), equal_nan=True)
    np.testing.assert_allclose(cv, series.cv2_positive.to_numpy(), equal_nan=True)
    classes = labels(adi, cv, count)
    assert np.array_equal(classes, series.pattern.to_numpy())
    active = np.divide(t - first, count, out=np.full(n, np.nan), where=count > 0)
    active_classes = labels(active, cv, count)
    assert np.array_equal(active_classes, series.active_span_pattern.to_numpy())
    daily = pd.read_parquet(tables / "daily.parquet")
    assert list(pd.to_datetime(daily.date)) == list(dates)
    np.testing.assert_array_equal(daily_total, daily.sales_units.to_numpy())
    for table in ("products", "stores", "store_daily"):
        data = pd.read_parquet(tables / f"{table}.parquet")
        assert float(data.sales_units.sum()) == float(total.sum())
    if name == "m5":
        for table in ("cat_id_daily", "dept_id_daily"):
            assert (
                float(pd.read_parquet(tables / f"{table}.parquet").sales_units.sum()) == total.sum()
            )
        assert (
            null_prices == result["price_missingness"]["eda_activity_partition"]["missing_prices"]
        )
    return {
        "status": "passed",
        "canonical_metadata_rows": parquet.metadata.num_rows,
        "full_history_quality": (
            "Original exact Phase 1 evidence retained; current full-target scan prohibited"
        ),
        "prefix_start": str(dates[0].date()),
        "prefix_end": str(dates[-1].date()),
        "prefix_rows": rows,
        "prefix_series": n,
        "prefix_sales_units": int(total.sum()),
        "prefix_zero_observations": int(daily_zero.sum()),
        "prefix_null_prices": null_prices,
        "duplicate_keys": duplicate,
        "missing_keys": int((~seen).sum()),
        "negative_sales": negative,
        "all_series_adi_cv2_patterns_match": True,
        "leading_zero_sensitivity_matches": True,
        "prefix_group_and_daily_totals_match": True,
        "canonical_schema": {str(f.name): str(f.type) for f in parquet.schema_arrow},
    }


def check_raw_m5():
    calendar = pd.read_csv(ROOT / "data/raw/m5/calendar.csv", usecols=["d", "date"])
    days = calendar.loc[calendar.date.le("2016-01-03"), "d"].tolist()
    ids = ["store_id", "item_id"]
    digests = {}
    totals = {}
    for filename in ("sales_train_evaluation.csv", "sales_train_validation.csv"):
        rows, units, zeros, count = 0, 0, 0, 0
        for frame in pd.read_csv(
            ROOT / "data/raw/m5" / filename, usecols=ids + days, chunksize=512
        ):
            y = frame[days].to_numpy(dtype="int32")
            assert (y >= 0).all()
            for i, key in enumerate(zip(frame.store_id, frame.item_id, strict=True)):
                digest = hashlib.sha256(y[i].tobytes()).hexdigest()
                if filename == "sales_train_evaluation.csv":
                    assert key not in digests
                    digests[key] = digest
                else:
                    assert digests[key] == digest
            rows += y.size
            units += int(y.sum(dtype="int64"))
            zeros += int((y == 0).sum())
            count += len(frame)
        totals[filename] = {"rows": rows, "sales_units": units, "zeros": zeros, "series": count}
    assert len(digests) == 30490
    assert totals["sales_train_evaluation.csv"] == totals["sales_train_validation.csv"]
    assert totals["sales_train_evaluation.csv"]["sales_units"] == 61066490
    return {
        "status": "passed",
        "prefix_day_columns": len(days),
        "results": totals,
        "scope": "d_1..d_1801 only; canonical/raw final targets not projected",
    }


def synthetic():
    y = np.array([[0, 0, 2, 0, 4], [0, 0, 0, 0, 0], [0, 0, 3, 0, 0], [3, 3, 3, 3, 3]])
    actual = panel_statistics(y)
    np.testing.assert_allclose(actual.adi.to_numpy(), [2.5, np.nan, 5, 1], equal_nan=True)
    np.testing.assert_allclose(
        actual.cv2_positive.to_numpy(), [2 / 9, np.nan, np.nan, 0], equal_nan=True
    )
    assert actual.pattern.tolist() == [
        "intermittent",
        "all_zero",
        "insufficient_positive_history",
        "smooth",
    ]
    _, partition = price_activity(np.ones(y.shape, bool), y)
    assert (
        sum(
            partition[k]
            for k in [
                "missing_before_first_positive",
                "missing_between_first_last_positive",
                "missing_after_last_positive",
                "missing_no_positive_in_eda",
            ]
        )
        == y.size
    )
    return {
        "status": "passed",
        "cases": "leading zeros, one/all-zero positives, constant, price partition",
    }


if __name__ == "__main__":
    started = time.perf_counter()
    outcome = {"canonical_holdout_targets_selected": False, "original_files_modified": False}
    outcome["source_headers"] = {}
    for name in ("store_item", "m5"):
        outcome["source_headers"][name] = {
            p.name: {
                "columns": len(header(p)),
                "unique_header": len(header(p)) == len(set(header(p))),
                "sales_column": "sales" in header(p),
            }
            for p in (ROOT / "data/raw" / name).glob("*.csv")
        }
        outcome[name] = check_dataset(name)
    outcome["m5_raw_prefix_overlap"] = check_raw_m5()
    outcome["synthetic_reference_checks"] = synthetic()
    outcome["seconds"] = time.perf_counter() - started
    outcome["current_rss_bytes"] = psutil.Process().memory_info().rss
    memory = psutil.Process().memory_info()
    outcome["peak_working_set_bytes"] = getattr(memory, "peak_wset", None)
    with DEST.open("x", encoding="utf-8") as stream:
        json.dump(outcome, stream, indent=2)
        stream.write("\n")
    print(json.dumps(outcome, indent=2))
