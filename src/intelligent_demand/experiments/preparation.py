"""Versioned origin-only matrix caches; source files are never changed."""

import json
import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from intelligent_demand.evaluation.splits import validate_fold
from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.data import ParquetSource
from intelligent_demand.experiments.registry import atomic_json, file_digest

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrainingPanel:
    values: np.ndarray
    dates: pd.DatetimeIndex
    metadata: pd.DataFrame
    prices: np.ndarray | None = None

    def __post_init__(self):
        if self.values.shape != (len(self.metadata), len(self.dates)):
            raise ValueError("Panel keys and matrix shape differ")
        self.values.flags.writeable = False
        if self.prices is not None:
            if self.prices.shape != self.values.shape:
                raise ValueError("Price shape differs")
            self.prices.flags.writeable = False


class PreparedSource(ParquetSource):
    """An optional acceleration of the existing capability, confined to a single origin."""

    def __init__(self, path, dataset_id, metadata, cache_root, fingerprint, batch_rows=65536):
        super().__init__(path, dataset_id, batch_rows)
        self.metadata = metadata.sort_values("series_id").reset_index(drop=True)
        if self.metadata.series_id.duplicated().any() or self.metadata.empty:
            raise ValueError("Unique source population metadata required")
        self.cache_root, self.fingerprint = Path(cache_root), fingerprint
        self._cached = {}

    def panel(self, fold, series):
        validate_fold(fold)
        if fold.dataset_id != self.dataset_id:
            raise ValueError("Dataset mismatch")
        population = tuple(self.metadata.series_id)
        codes = pd.Index(population).get_indexer(series)
        if (codes < 0).any() or len(set(series)) != len(series):
            raise ValueError("Unknown or repeated panel series")
        if fold not in self._cached:
            self._cached[fold] = self._prepare(fold, population)
        full = self._cached[fold]
        if tuple(series) == population:
            return full
        return TrainingPanel(
            full.values[codes],
            full.dates,
            full.metadata.iloc[codes].reset_index(drop=True),
            None if full.prices is None else full.prices[codes],
        )

    def _prepare(self, fold, population):
        dates = pd.date_range(fold.train_start, fold.origin)
        contract = {
            "version": 1,
            "source": self.fingerprint,
            "origin": str(fold.origin),
            "start": str(fold.train_start),
            "dataset": self.dataset_id,
            "population": identity(population),
        }
        directory = self.cache_root / identity(contract)
        manifest = directory / "complete.json"
        if manifest.exists():
            saved = json.loads(manifest.read_text())
            if saved["contract"] != contract:
                raise ValueError("Cache contract changed")
            for name, digest in saved["files"].items():
                if file_digest(directory / name) != digest:
                    raise ValueError("Prepared cache checksum mismatch")
        else:
            directory.mkdir(parents=True, exist_ok=True)
            tag = uuid.uuid4().hex
            shape = (len(population), len(dates))
            values_path = directory / f"values-{tag}.npy"
            values = np.lib.format.open_memmap(values_path, mode="w+", dtype="float32", shape=shape)
            values[:] = np.nan
            prices_path, prices = None, None
            if self.dataset_id == "m5":
                prices_path = directory / f"prices-{tag}.npy"
                prices = np.lib.format.open_memmap(
                    prices_path, mode="w+", dtype="float32", shape=shape
                )
                prices[:] = np.nan
            indexes, count = pd.Index(population), 0
            columns = ["series_id", "date", "sales_units"]
            if prices is not None:
                columns.append("unit_price")
            for batch in self.at_origin(fold, population).history(columns=columns):
                rows = indexes.get_indexer(batch.series_id)
                days = (
                    pd.to_datetime(batch.date) - pd.Timestamp(fold.train_start)
                ).dt.days.to_numpy()
                flat = rows * len(dates) + days
                if (rows < 0).any() or len(np.unique(flat)) != len(flat):
                    raise ValueError("Invalid or duplicate source panel keys")
                units = batch.sales_units.to_numpy(dtype="float64")
                if not np.isfinite(units).all() or (units < 0).any():
                    raise ValueError("Invalid historical target")
                if not np.isnan(values[rows, days]).all():
                    raise ValueError("Duplicate panel keys across batches")
                if not np.array_equal(units, units.astype("float32").astype("float64")):
                    raise ValueError("Compact target cache would lose source precision")
                values[rows, days] = units
                if prices is not None:
                    prices[rows, days] = batch.unit_price.to_numpy(dtype="float32")
                count += len(batch)
                if count % (self.batch_rows * 100) < self.batch_rows:
                    LOGGER.info(
                        "Preparing %s origin %s: %s/%s rows",
                        self.dataset_id,
                        fold.origin,
                        count,
                        values.size,
                    )
            if count != values.size:
                raise ValueError("Incomplete historical panel")
            for start in range(0, len(population), 256):
                if not np.isfinite(values[start : start + 256]).all():
                    raise ValueError("Missing historical panel keys")
            files = {}
            for array, path in ((values, values_path), (prices, prices_path)):
                if array is not None:
                    array.flush()
                    with path.open("r+b") as stream:
                        os.fsync(stream.fileno())
                    files[path.name] = file_digest(path)
            atomic_json(
                manifest,
                {
                    "contract": contract,
                    "files": files,
                    "values": values_path.name,
                    "prices": None if prices_path is None else prices_path.name,
                },
            )
            del values, prices
            saved = json.loads(manifest.read_text())
        return TrainingPanel(
            np.load(directory / saved["values"], mmap_mode="r"),
            dates,
            self.metadata.copy(),
            None
            if saved["prices"] is None
            else np.load(directory / saved["prices"], mmap_mode="r"),
        )

    def scales(self, fold, series):
        panel = self.panel(fold, series)
        pairs = []
        for start in range(0, len(series), 256):
            block = panel.values[start : start + 256].astype("float64")
            differences = block[:, 7:] - block[:, :-7]
            if block.shape[1] <= 7:
                pairs.extend([(np.nan, np.nan)] * len(block))
            else:
                pairs.extend(
                    zip(
                        np.abs(differences).mean(axis=1),
                        np.square(differences).mean(axis=1),
                        strict=True,
                    )
                )
        result = pd.DataFrame(pairs, columns=["scale_absolute", "scale_squared"])
        result = result.mask(result.eq(0))
        result["series_id"] = list(series)
        result["dataset_id"] = fold.dataset_id
        result["training_start"], result["training_end"] = fold.train_start, fold.origin
        result["season_days"] = 7
        return result


def panel_from_view(view):
    """Public adapter helper; only the capability's validated historical window is returned."""
    view.__post_init__()
    if isinstance(view._source, PreparedSource):
        return view._source.panel(view.fold, view.series)
    dates = pd.date_range(view.fold.train_start, view.fold.origin)
    values = np.full((len(view.series), len(dates)), np.nan, dtype="float64")
    index = pd.Index(view.series)
    for batch in view.history():
        rows = index.get_indexer(batch.series_id)
        days = (pd.to_datetime(batch.date) - dates[0]).dt.days.to_numpy()
        if not np.isnan(values[rows, days]).all() or batch.duplicated(["series_id", "date"]).any():
            raise ValueError("Duplicate training keys")
        values[rows, days] = batch.sales_units.to_numpy()
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Incomplete or invalid training panel")
    return TrainingPanel(values, dates, pd.DataFrame({"series_id": list(view.series)}))
