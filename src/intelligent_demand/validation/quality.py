"""Incremental quality evidence and a fixed canonical Parquet contract."""

import sqlite3
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

CANONICAL_SCHEMA = pa.schema(
    [
        ("dataset_id", pa.string()),
        ("series_id", pa.string()),
        ("date", pa.date32()),
        ("sales_units", pa.float64()),
        ("store_id", pa.string()),
        ("item_id", pa.string()),
        ("category_id", pa.string()),
        ("unit_price", pa.float64()),
        ("is_observed", pa.bool_()),
    ]
)


def issue(report: dict, message: str, critical: bool = True) -> None:
    """Record an actionable quality finding only once."""
    key = "critical_errors" if critical else "warnings"
    if message not in report[key]:
        report[key].append(message)


def profile_frame(report: dict, name: str, frame: pd.DataFrame) -> None:
    """Accumulate input row counts, observed parser types and null counts."""
    profile = report["profiles"].setdefault(
        name,
        {
            "rows": 0,
            "columns": list(frame.columns),
            "parser_dtypes": {str(k): str(v) for k, v in frame.dtypes.items()},
            "missing": {str(k): 0 for k in frame.columns},
        },
    )
    profile["rows"] += len(frame)
    for column in frame:
        profile["missing"][column] += int(frame[column].isna().sum())


def numeric_values(values: pd.Series, report: dict, label: str) -> pd.Series:
    """Parse quantities and record invalid, zero, negative and fractional observations."""
    numeric = pd.to_numeric(values, errors="coerce").astype("float64")
    finite = pd.Series(np.isfinite(numeric.to_numpy()), index=numeric.index)
    counts = report["quantities"].setdefault(
        label,
        {
            "observations": 0,
            "zero": 0,
            "negative": 0,
            "invalid_or_missing": 0,
            "fractional": 0,
            "finite_value_sum": 0.0,
        },
    )
    counts["observations"] += len(values)
    counts["zero"] += int(numeric.eq(0).sum())
    counts["negative"] += int(numeric.lt(0).sum())
    counts["invalid_or_missing"] += int((~finite).sum())
    counts["fractional"] += int((finite & numeric.mod(1).ne(0)).sum())
    counts["finite_value_sum"] += float(numeric[finite].sum())
    if (~finite).any() or numeric.lt(0).any():
        issue(report, f"{label}: missing, nonfinite, nonnumeric or negative values")
    if label != "sell_price" and (finite & numeric.mod(1).ne(0)).any():
        issue(report, f"{label}: fractional unit sales require source verification")
    return numeric


def series_key(store: pd.Series, item: pd.Series) -> pd.Series:
    """Length-prefix the store identifier to avoid delimiter collisions."""
    return store.str.len().astype("string") + ":" + store + item


class CanonicalWriter:
    """Write bounded batches and independently validate the persisted schema/count."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows = 0
        self.total_sales = 0.0
        self.invalid_keys = False
        self.key_path = path.with_name(f".canonical-keys-{uuid.uuid4().hex}.sqlite")
        self.keys = sqlite3.connect(self.key_path)
        self.keys.execute("PRAGMA cache_size=-8192")
        self.keys.execute("PRAGMA journal_mode=OFF")
        self.keys.execute(
            "CREATE TABLE keys (dataset TEXT NOT NULL, day INTEGER NOT NULL, "
            "store TEXT NOT NULL, item TEXT NOT NULL, "
            "PRIMARY KEY(dataset, day, store, item)) WITHOUT ROWID"
        )
        self.writer = pq.ParquetWriter(path, CANONICAL_SCHEMA, compression="zstd")

    def append(self, frame: pd.DataFrame) -> None:
        """Write observed rows without imputation or demand inference."""
        frame = frame.copy()
        dates = pd.to_datetime(frame["date"], errors="raise")
        if dates.dt.tz is not None or dates.isna().any():
            self.invalid_keys = True
            raise ValueError("Canonical dates must be valid timezone-naive calendar days")
        frame["date"] = dates.dt.normalize()
        table = pa.Table.from_pandas(frame, schema=CANONICAL_SCHEMA, preserve_index=False)
        columns = [table[name] for name in ("dataset_id", "date", "store_id", "item_id")]
        if any(column.null_count for column in columns):
            self.invalid_keys = True
            raise ValueError("Canonical business keys cannot be missing")
        keys = zip(columns[0].to_pylist(), columns[1].cast(pa.int32()).to_pylist(),
                   columns[2].to_pylist(), columns[3].to_pylist(), strict=True)
        try:
            self.keys.executemany("INSERT INTO keys VALUES (?, ?, ?, ?)", keys)
            self.keys.commit()
        except sqlite3.IntegrityError as exc:
            self.invalid_keys = True
            raise ValueError("Duplicate canonical dataset/date/store/product key") from exc
        self.writer.write_table(table)
        self.rows += len(frame)
        self.total_sales += float(frame["sales_units"].sum())

    def close(self) -> dict:
        """Check on-disk rows, quantities and schema without loading all observations."""
        self.writer.close()
        try:
            if self.invalid_keys:
                raise ValueError("Canonical business-key validation failed; do not publish")
            if self.keys.execute("SELECT COUNT(*) FROM keys").fetchone()[0] != self.rows:
                raise ValueError("Canonical key count differs from written rows")
        finally:
            self.keys.close()
            self.key_path.unlink(missing_ok=True)
        parquet = pq.ParquetFile(self.path)
        actual_rows = parquet.metadata.num_rows
        actual_sales = 0.0
        for batch in parquet.iter_batches(columns=["sales_units"]):
            values = batch.column(0).to_numpy()
            if not np.isfinite(values).all() or (values < 0).any():
                raise ValueError("Canonical sales validation failed")
            actual_sales += float(values.sum())
        if (
            actual_rows != self.rows
            or not parquet.schema_arrow.equals(CANONICAL_SCHEMA, check_metadata=False)
            or not np.isclose(actual_sales, self.total_sales)
        ):
            raise ValueError("Canonical persistence reconciliation failed")
        return {
            "rows": actual_rows,
            "sales_units_sum": actual_sales,
            "schema_verified": True,
            "row_and_quantity_reconciliation": True,
            "canonical_business_keys_unique": True,
        }
