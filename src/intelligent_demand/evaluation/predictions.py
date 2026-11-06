"""Strict daily prediction alignment and atomic, bounded Parquet publication."""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from intelligent_demand.evaluation.splits import validate_fold

PREDICTION_SCHEMA = pa.schema(
    [
        ("dataset_id", pa.string()),
        ("series_id", pa.string()),
        ("forecast_origin", pa.date32()),
        ("target_date", pa.date32()),
        ("horizon_step", pa.int16()),
        ("model_id", pa.string()),
        ("model_version", pa.string()),
        ("run_id", pa.string()),
        ("prediction", pa.float64()),
        ("raw_prediction", pa.float64()),
        ("is_fallback", pa.bool_()),
        ("was_clipped", pa.bool_()),
    ]
)


def daily_dates(values):
    dates = pd.to_datetime(values, errors="raise")
    if dates.isna().any() or dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
        raise ValueError("Nonmissing naive daily dates required")
    return dates


def validate_prediction_frame(frame, fold, series):
    validate_fold(fold)
    if not {"series_id", "target_date", "prediction"}.issubset(frame):
        raise ValueError("Prediction keys and values are required")
    allowed = {"series_id", "target_date", "prediction", "is_fallback"}
    if set(frame) - allowed or frame.empty:
        raise ValueError("Unexpected prediction fields or empty batch")
    work = frame.copy()
    work.attrs = {}
    work["target_date"] = daily_dates(work.target_date)
    if (
        work.series_id.isna().any()
        or not work.series_id.isin(series).all()
        or work.duplicated(["series_id", "target_date"]).any()
        or not work.target_date.between(
            pd.Timestamp(fold.validation_start), pd.Timestamp(fold.validation_end)
        ).all()
    ):
        raise ValueError("Unknown, duplicate or out-of-window prediction keys")
    if (
        pd.api.types.is_bool_dtype(work.prediction)
        or not pd.api.types.is_numeric_dtype(work.prediction)
        or not np.isfinite(work.prediction).all()
    ):
        raise ValueError("Finite numeric predictions required")
    if "is_fallback" not in work:
        work["is_fallback"] = False
    if work.is_fallback.isna().any() or work.is_fallback.dtype != bool:
        raise ValueError("Fallback flags must be nonmissing boolean values")
    work["horizon_step"] = (work.target_date - pd.Timestamp(fold.origin)).dt.days
    return work


class PredictionWriter:
    def __init__(self, path: Path, fold, series, model_info, run_id, batch_rows=65536):
        validate_fold(fold)
        if type(batch_rows) is not int or batch_rows < 1:
            raise ValueError("Positive integer prediction batch size required")
        self.path, self.fold, self.series = Path(path), fold, tuple(series)
        if not series or len(set(series)) != len(series):
            raise ValueError("A fixed unique series population is required")
        self.index = pd.Index(series)
        self.seen = np.zeros((len(series), fold.horizon), dtype=bool)
        self.model_info, self.run_id, self.batch_rows = model_info, run_id, batch_rows
        self.partial = self.path.with_suffix(".parquet.part")
        if self.path.exists() or self.partial.exists():
            raise FileExistsError("Prediction outputs are never overwritten")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.partial.open("xb")
        self.writer = pq.ParquetWriter(self.stream, PREDICTION_SCHEMA, compression="zstd")
        self.closed = False

    def write(self, frame):
        if self.closed:
            raise ValueError("Prediction writer is closed")
        for start in range(0, len(frame), self.batch_rows):
            work = validate_prediction_frame(
                frame.iloc[start : start + self.batch_rows], self.fold, self.series
            )
            codes, steps = self.index.get_indexer(work.series_id), work.horizon_step.to_numpy() - 1
            if self.seen[codes, steps].any():
                raise ValueError("Duplicate prediction across batches")
            self.seen[codes, steps] = True
            work["dataset_id"] = self.fold.dataset_id
            work["forecast_origin"] = self.fold.origin
            work["model_id"], work["model_version"] = (
                self.model_info.identifier,
                self.model_info.version,
            )
            work["run_id"] = self.run_id
            work["raw_prediction"] = work.prediction.astype(float)
            work["was_clipped"] = work.raw_prediction.lt(0)
            work["prediction"] = work.raw_prediction.clip(lower=0)
            table = pa.Table.from_pandas(work, schema=PREDICTION_SCHEMA, preserve_index=False)
            self.writer.write_table(table)

    def close(self):
        if not self.closed:
            self.writer.close()
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.stream.close()
            self.closed = True

    def finish(self):
        self.close()
        if not self.seen.all():
            raise ValueError("Incomplete predictions cannot be published")
        if self.path.exists():
            raise FileExistsError("Prediction publication target already exists")
        os.replace(self.partial, self.path)
        return {
            "rows": int(self.seen.sum()),
            "series": len(self.series),
            "horizon_days": self.fold.horizon,
        }
