"""Shifted one-step features and origin-frozen observed context for recursive forecasts."""

import json
import os
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.data import validate_training_feature_lineage
from intelligent_demand.experiments.preparation import panel_from_view
from intelligent_demand.experiments.registry import atomic_json, file_digest

LAGS = (1, 7, 14, 28, 56)
OBSERVED_NAMES = (
    "obs_zero_fraction28",
    "obs_zero_fraction56",
    "obs_positive_count56",
    "obs_adi56",
    "obs_positive_cv2_56",
    "obs_last_positive_age_capped56",
)
CALENDAR_NAMES = (
    "day_of_week",
    "day_of_month",
    "month",
    "weekend",
    "annual_sin",
    "annual_cos",
    "weekly_sin",
    "weekly_cos",
    "days_since_training_start",
)


def observed_context(history):
    y = np.asarray(history, dtype=float)
    if y.ndim != 2 or y.shape[1] != 56 or not np.isfinite(y).all() or (y < 0).any():
        raise ValueError("Complete nonnegative 56-day observed context required")
    positive = y > 0
    count, total = positive.sum(axis=1), y.sum(axis=1)
    adi = np.divide(56.0, count, out=np.full(len(y), np.nan), where=count > 0)
    mean = np.divide(total, count, out=np.full(len(y), np.nan), where=count > 0)
    variance = np.divide(
        np.square(y).sum(axis=1)
        - np.divide(total**2, count, out=np.zeros(len(y)), where=count > 0),
        count - 1,
        out=np.full(len(y), np.nan),
        where=count > 1,
    )
    cv2 = np.maximum(variance, 0) / mean**2
    age = np.where(count > 0, positive[:, ::-1].argmax(axis=1), 56)
    return np.column_stack(
        ((y[:, -28:] == 0).mean(axis=1), (y == 0).mean(axis=1), count, adi, cv2, age)
    )


def historical_price_context(prices, rows, targets):
    """28 daily records ending seven days before target; no incomplete weekly prices."""
    positions = np.asarray(targets)[:, None] - np.arange(34, 6, -1)
    if (positions < 0).any() or (positions >= prices.shape[1]).any():
        raise ValueError("Price snapshot crosses its observed history")
    block = prices[np.asarray(rows)[:, None], positions].astype(float)
    if np.isinf(block).any():
        raise ValueError("Infinite historical price is invalid, not missing")
    known = np.isfinite(block)
    if (block[known] <= 0).any():
        raise ValueError("Invalid observed historical price")
    count = known.sum(axis=1)
    mean = np.divide(
        np.where(known, block, 0).sum(axis=1),
        count,
        out=np.full(len(rows), np.nan),
        where=count > 0,
    )
    return np.column_stack((mean, 1 - count / 28))


class FeatureEncoder:
    def __init__(self, metadata, dataset, training_start, use_historical_prices=True):
        if type(use_historical_prices) is not bool:
            raise ValueError("Price feature policy must be an explicit boolean")
        self.use_historical_prices = dataset == "m5" and use_historical_prices
        self.dataset, self.training_start = dataset, pd.Timestamp(training_start)
        self.static_fields = ["store_id", "item_id"] + (
            ["cat_id", "dept_id", "state_id"] if dataset == "m5" else []
        )
        self.mappings = {}
        for field in self.static_fields:
            if field not in metadata or metadata[field].isna().any():
                raise ValueError("Static identifiers must be supplied, never invented")
            self.mappings[field] = {
                str(label): i
                for i, label in enumerate(sorted(metadata[field].astype(str).unique()))
            }
        self.names = [
            *(f"lag_{lag}" for lag in LAGS),
            "rolling_mean7",
            "rolling_mean28",
            "rolling_mean56",
            "rolling_std7",
            "rolling_std28",
            *OBSERVED_NAMES,
            *CALENDAR_NAMES,
            *(f"{field}_code" for field in self.static_fields),
        ]
        if self.use_historical_prices:
            self.names += ["origin_observed_price_mean28", "origin_price_missing_fraction28"]
        self.categorical_indexes = [
            self.names.index(f"{field}_code") for field in self.static_fields
        ]

    def static_codes(self, metadata):
        columns = []
        for field in self.static_fields:
            values = metadata[field].astype(str).map(self.mappings[field])
            if values.isna().any():
                raise ValueError("Unknown identifier outside the fitted benchmark universe")
            columns.append(values.to_numpy())
        return np.column_stack(columns)

    def matrix(self, history, dates, static, observed=None, prices=None):
        history = np.asarray(history, dtype=float)
        if (
            history.ndim != 2
            or history.shape[1] != 56
            or not np.isfinite(history).all()
            or (history < 0).any()
        ):
            raise ValueError(
                "Feature state must contain 56 finite nonnegative available quantities"
            )
        days = pd.DatetimeIndex(dates)
        if (
            len(days) != len(history)
            or days.isna().any()
            or days.tz is not None
            or not days.equals(days.normalize())
        ):
            raise ValueError("Aligned naive daily target dates required")
        if static.shape != (len(history), len(self.static_fields)):
            raise ValueError("Static feature rows do not match series")
        observed = observed_context(history) if observed is None else observed
        dow = days.day_of_week.to_numpy()
        year_fraction = (days.day_of_year.to_numpy() - 1) / np.where(days.is_leap_year, 366, 365)
        calendar = np.column_stack(
            (
                dow,
                days.day.to_numpy(),
                days.month.to_numpy(),
                dow >= 5,
                np.sin(2 * np.pi * year_fraction),
                np.cos(2 * np.pi * year_fraction),
                np.sin(2 * np.pi * dow / 7),
                np.cos(2 * np.pi * dow / 7),
                (days - self.training_start).days.to_numpy(),
            )
        )
        parts = [
            history[:, -np.asarray(LAGS)],
            np.column_stack([history[:, -width:].mean(axis=1) for width in (7, 28, 56)]),
            np.column_stack([history[:, -width:].std(axis=1, ddof=0) for width in (7, 28)]),
            observed,
            calendar,
            static,
        ]
        if self.use_historical_prices:
            if prices is None or prices.shape != (len(history), 2):
                raise ValueError("Origin-available historical price snapshot required")
            parts.append(prices)
        features = np.column_stack(parts).astype("float32")
        self.validate(features)
        return features

    def validate(self, matrix):
        if matrix.ndim != 2 or matrix.shape[1] != len(self.names) or np.isinf(matrix).any():
            raise ValueError("Feature shape or infinity violates the fitted schema")
        allowed = {"obs_adi56", "obs_positive_cv2_56", "origin_observed_price_mean28"}
        for i, name in enumerate(self.names):
            if name not in allowed and not np.isfinite(matrix[:, i]).all():
                raise ValueError(f"Unexpected missing feature: {name}")

    def metadata(self):
        return {
            "dataset": self.dataset,
            "training_start": str(self.training_start.date()),
            "feature_names": self.names,
            "static_mappings": self.mappings,
            "categorical_indexes": self.categorical_indexes,
            "observed_activity_policy": "frozen_at_true_forecast_origin",
            "price_policy": (
                "observed_only_28_records_ending_origin_minus6; frozen; no imputation"
                if self.use_historical_prices
                else "excluded_availability_safe"
                if self.dataset == "m5"
                else "not_supplied"
            ),
        }


def training_positions(series_count, periods, maximum_rows, seed):
    count = min(periods - 56, maximum_rows // series_count)
    if count < 1:
        raise ValueError("Training budget must cover every eligible series with 56 prior days")
    boundaries = np.linspace(56, periods, count + 1, dtype=int)
    targets = np.random.default_rng(seed).integers(
        boundaries[:-1], boundaries[1:], size=(series_count, count)
    )
    rows = np.repeat(np.arange(series_count), count)
    return rows.astype("int32"), targets.ravel().astype("int32")


def training_matrix(
    view,
    maximum_rows,
    seed,
    cache_root,
    fingerprint,
    batch_rows=8192,
    use_historical_prices=True,
):
    panel = panel_from_view(view)
    encoder = FeatureEncoder(
        panel.metadata, view.fold.dataset_id, view.fold.train_start, use_historical_prices
    )
    rows, targets = training_positions(len(view.series), len(panel.dates), maximum_rows, seed)
    contract = {
        "version": 1,
        "source": fingerprint,
        "origin": str(view.fold.origin),
        "population": identity(list(view.series)),
        "maximum_rows": maximum_rows,
        "seed": seed,
        "feature_code": file_digest(Path(__file__)),
        "encoder": identity(encoder.metadata()),
    }
    directory = Path(cache_root) / identity(contract)
    manifest = directory / "complete.json"
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        if saved["contract"] != contract:
            raise ValueError("Feature cache contract changed")
        for name, digest in saved["files"].items():
            if file_digest(directory / name) != digest:
                raise ValueError("Feature cache checksum mismatch")
    else:
        directory.mkdir(parents=True, exist_ok=True)
        tag = uuid.uuid4().hex
        names = {key: f"{key}-{tag}.npy" for key in ("features", "labels", "positions")}
        x = np.lib.format.open_memmap(
            directory / names["features"],
            mode="w+",
            dtype="float32",
            shape=(len(rows), len(encoder.names)),
        )
        y = np.lib.format.open_memmap(
            directory / names["labels"], mode="w+", dtype="float32", shape=(len(rows),)
        )
        pairs = np.lib.format.open_memmap(
            directory / names["positions"], mode="w+", dtype="int32", shape=(len(rows), 2)
        )
        static = encoder.static_codes(panel.metadata)
        for start in range(0, len(rows), batch_rows):
            selected_rows, selected_targets = (
                rows[start : start + batch_rows],
                targets[start : start + batch_rows],
            )
            history = panel.values[
                selected_rows[:, None], selected_targets[:, None] - np.arange(56, 0, -1)
            ]
            dates = panel.dates.take(selected_targets)
            lineage = pd.DataFrame(
                {
                    "series_id": np.asarray(view.series)[selected_rows],
                    "target_date": dates,
                    "max_source_date": dates - pd.Timedelta(days=1),
                }
            )
            validate_training_feature_lineage(lineage, view)
            prices = (
                None
                if panel.prices is None or not encoder.use_historical_prices
                else historical_price_context(panel.prices, selected_rows, selected_targets)
            )
            x[start : start + len(selected_rows)] = encoder.matrix(
                history, dates, static[selected_rows], prices=prices
            )
            y[start : start + len(selected_rows)] = panel.values[selected_rows, selected_targets]
            pairs[start : start + len(selected_rows)] = np.column_stack(
                (selected_rows, selected_targets)
            )
        if not np.isfinite(y).all() or (y < 0).any():
            raise ValueError("Invalid supervised labels")
        files = {}
        for key, array in (("features", x), ("labels", y), ("positions", pairs)):
            array.flush()
            with (directory / names[key]).open("r+b") as stream:
                os.fsync(stream.fileno())
            files[names[key]] = file_digest(directory / names[key])
        atomic_json(
            manifest,
            {
                "contract": contract,
                "files": files,
                "names": names,
                "training_rows": len(rows),
                "series": len(view.series),
                "target_min": str(panel.dates[targets.min()].date()),
                "target_max": str(panel.dates[targets.max()].date()),
                "max_source_date": str((panel.dates[targets.max()] - pd.Timedelta(days=1)).date()),
            },
        )
        del x, y, pairs
        saved = json.loads(manifest.read_text())
    return (
        np.load(directory / saved["names"]["features"], mmap_mode="r"),
        np.load(directory / saved["names"]["labels"], mmap_mode="r"),
        encoder,
        saved,
    )
