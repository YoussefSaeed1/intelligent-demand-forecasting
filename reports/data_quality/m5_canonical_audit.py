"""Independent, bounded verification of the actual M5 canonical business keys and totals."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import pyarrow as pa
import pyarrow.parquet as pq

from intelligent_demand.config import load_config
from intelligent_demand.ingestion.datasets import DATASETS, file_inventory, sha256, write_json
from intelligent_demand.validation.quality import series_key

root = Path(__file__).resolve().parents[2]
config = load_config(root / "configs/default.yaml")
directory = config.paths["reports"] / "data_quality"
raw = config.paths["raw"] / "m5"
report = json.loads((directory / "m5.json").read_text(encoding="utf-8"))
assert report["status"] in ("passed", "passed_with_warnings"), report["status"]
started = time.perf_counter()
history = raw / report["transformation"]["selected_history"]
days = [c for c in pd.read_csv(history, nrows=0).columns if c.startswith("d_")]
identifiers = pd.read_csv(history, usecols=["store_id", "item_id"], dtype="string")
series = pd.Index(series_key(identifiers.store_id, identifiers.item_id))
assert series.is_unique
stores = identifiers.store_id.to_numpy()
items = identifiers.item_id.to_numpy()
calendar = pd.read_csv(raw / "calendar.csv", usecols=["d", "date"])
dates = pd.to_datetime(calendar.set_index("d").loc[days, "date"])
date_codes = dates.to_numpy(dtype="datetime64[D]").astype("int32")
assert np.all(np.diff(date_codes) == 1)
assert not dates.duplicated().any()
expected_rows = len(series) * len(days)
seen = np.zeros(expected_rows, dtype=bool)
parquet = pq.ParquetFile(config.paths["processed"] / "m5/daily_sales.parquet")
assert parquet.metadata.num_rows == expected_rows
total = 0.0
rows = zeros = missing_prices = 0
columns = [
    "dataset_id",
    "series_id",
    "date",
    "sales_units",
    "store_id",
    "item_id",
    "unit_price",
    "is_observed",
]
for batch in parquet.iter_batches(batch_size=131072, columns=columns):
    frame = batch.to_pandas(date_as_object=False)
    indexes = series.get_indexer(frame.series_id)
    assert (indexes >= 0).all()
    offsets = batch.column(columns.index("date")).cast(pa.int32()).to_numpy() - date_codes[0]
    assert ((offsets >= 0) & (offsets < len(days))).all()
    keys = indexes * len(days) + offsets
    assert np.unique(keys).size == len(keys), "Duplicate keys within a Parquet batch"
    assert not seen[keys].any(), "Duplicate keys across Parquet batches"
    seen[keys] = True
    assert frame.dataset_id.eq("m5").all()
    assert frame.is_observed.eq(True).all()
    assert (frame.store_id.to_numpy() == stores[indexes]).all()
    assert (frame.item_id.to_numpy() == items[indexes]).all()
    quantities = frame.sales_units.to_numpy()
    assert np.isfinite(quantities).all() and (quantities >= 0).all()
    assert (quantities % 1 == 0).all()
    total += float(quantities.sum())
    zeros += int((quantities == 0).sum())
    missing_prices += int(frame.unit_price.isna().sum())
    rows += len(frame)
assert seen.all()
source_total = 0.0
source_rows = 0
for chunk in pd.read_csv(history, usecols=days, chunksize=512):
    values = chunk.to_numpy(dtype="float64")
    source_total += float(values.sum())
    source_rows += values.size
assert rows == source_rows == expected_rows
assert total == source_total == report["transformation"]["source_sales_units_sum"]
assert missing_prices == report["transformation"]["missing_price_observations"]
before = json.loads((directory / "m5_debug_before.json").read_text(encoding="utf-8"))
after = file_inventory(raw, DATASETS["m5"])
hashes_before = {r["filename"]: r["sha256"] for r in before["inventory"]["files"]}
hashes_after = {r["filename"]: r["sha256"] for r in after["files"]}
assert hashes_before == hashes_after, "Raw source hashes changed"
canonical_hash = sha256(config.paths["processed"] / "m5/daily_sales.parquet")
assert canonical_hash == report["transformation"]["sha256"]
evidence = {
    "status": "passed",
    "checked_at_utc": datetime.now(UTC).isoformat(),
    "canonical_rows": rows,
    "expected_rows": expected_rows,
    "source_observations": source_rows,
    "series": len(series),
    "stores": int(identifiers.store_id.nunique()),
    "products": int(identifiers.item_id.nunique()),
    "days": len(days),
    "date_min": dates.min().strftime("%Y-%m-%d"),
    "date_max": dates.max().strftime("%Y-%m-%d"),
    "source_sales_units_sum": source_total,
    "canonical_sales_units_sum": total,
    "duplicate_business_keys": 0,
    "business_key": ["dataset_id", "store_id", "item_id", "date"],
    "business_key_coverage_complete": True,
    "zero_sales_observations": zeros,
    "missing_price_observations": missing_prices,
    "raw_hashes_unchanged": True,
    "source_sha256": hashes_after,
    "canonical_sha256": canonical_hash,
    "elapsed_seconds": time.perf_counter() - started,
    "peak_worker_working_set_bytes": getattr(psutil.Process().memory_info(), "peak_wset", None),
    "method": "131072-row Parquet batches; one NumPy bool per series/day for key coverage; "
    "independent 512-series source summation",
}
write_json(directory / "m5_canonical_audit.json", evidence)
print(json.dumps(evidence, indent=2))
