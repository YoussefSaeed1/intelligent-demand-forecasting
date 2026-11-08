"""Origin-bounded Parquet capabilities and explicit future-feature availability."""

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

from intelligent_demand.evaluation.splits import ValidationFold, validate_fold

KEYS = ["dataset_id", "series_id", "date"]
HISTORY_COLUMNS = set(
    KEYS + ["sales_units", "unit_price", "store_id", "item_id", "category_id", "is_observed"]
)
TARGET_NAMES = {"sales_units", "actual", "target", "prediction", "raw_prediction"}


class LeakageError(ValueError):
    """A requested field, date or availability contract crosses the origin boundary."""


def validate_training_feature_lineage(frame, view):
    """Validate declared lag/rolling lineage; does not construct or fit any features."""
    required = {"series_id", "target_date", "max_source_date"}
    if not required.issubset(frame) or frame.empty:
        raise LeakageError("Historical feature rows require their source-date lineage")
    targets = pd.to_datetime(frame.target_date, errors="raise")
    latest = pd.to_datetime(frame.max_source_date, errors="raise")
    if (
        targets.isna().any()
        or latest.isna().any()
        or targets.dt.tz is not None
        or latest.dt.tz is not None
        or not targets.eq(targets.dt.normalize()).all()
        or not latest.eq(latest.dt.normalize()).all()
        or not frame.series_id.isin(view.series).all()
        or frame.duplicated(["series_id", "target_date"]).any()
        or not targets.between(
            pd.Timestamp(view.fold.train_start), pd.Timestamp(view.fold.origin)
        ).all()
        or not latest.lt(targets).all()
    ):
        raise LeakageError("Lag/rolling features must use strictly earlier source dates")
    return frame.copy(deep=True)


@dataclass(frozen=True)
class Availability:
    kind: str
    published_at: date
    evidence: str

    def validate(self, origin):
        if (
            self.kind not in ("known_future", "static", "independent_forecast")
            or type(self.published_at) is not date
            or self.published_at > origin
            or not isinstance(self.evidence, str)
            or not self.evidence.strip()
        ):
            raise LeakageError("Only documented origin-available covariates are permitted")


def validate_future_features(frame, fold, series, availability):
    validate_fold(fold)
    required = {"series_id", "target_date", "horizon_step"}
    if not required.issubset(frame) or set(frame) & TARGET_NAMES:
        raise LeakageError("Future features require forecast keys and must not contain targets")
    work = frame.copy(deep=True)
    dates = pd.to_datetime(work.target_date, errors="raise")
    if dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
        raise LeakageError("Naive daily dates are required")
    work["target_date"] = dates
    if (
        work.series_id.isna().any()
        or not work.series_id.isin(series).all()
        or work.duplicated(["series_id", "target_date"]).any()
        or not dates.between(
            pd.Timestamp(fold.validation_start), pd.Timestamp(fold.validation_end)
        ).all()
        or not work.horizon_step.eq((dates - pd.Timestamp(fold.origin)).dt.days).all()
    ):
        raise LeakageError("Future feature keys or dates differ from this forecast window")
    if len(work) != len(series) * fold.horizon:
        raise LeakageError("Future features must cover the complete series × horizon grid")
    if set(availability) != set(work) - required:
        raise LeakageError("Every covariate needs an availability rule; no unregistered fields")
    for rule in availability.values():
        rule.validate(fold.origin)
    work.attrs["availability"] = dict(availability)
    return work


class ParquetSource:
    """Trusted infrastructure reader; models receive an OriginData capability instead."""

    def __init__(self, path: Path, dataset_id: str, batch_rows: int = 65536):
        if type(batch_rows) is not int or batch_rows < 1:
            raise ValueError("Positive bounded batch size required")
        self.path, self.dataset_id, self.batch_rows = Path(path), dataset_id, batch_rows

    def _read(self, fold, start, end, columns, series):
        validate_fold(fold)
        if fold.dataset_id != self.dataset_id or end >= fold.holdout_start:
            raise LeakageError("Source identity mismatch or protected final holdout access")
        if start < fold.train_start or start > end:
            raise LeakageError("Requested history dates are invalid")
        if not set(columns).issubset(HISTORY_COLUMNS) or len(set(columns)) != len(columns):
            raise LeakageError("Unregistered source columns")
        expression = (
            (ds.field("dataset_id") == self.dataset_id)
            & (ds.field("date") >= pa.scalar(start, pa.date32()))
            & (ds.field("date") <= pa.scalar(end, pa.date32()))
            & ds.field("series_id").isin(series)
        )
        scanner = ds.dataset(self.path, format="parquet").scanner(
            columns=columns, filter=expression, batch_size=self.batch_rows, use_threads=False
        )
        for batch in scanner.to_batches():
            if batch.num_rows:
                yield batch.to_pandas(date_as_object=False)

    def at_origin(self, fold, series):
        validate_fold(fold)
        if fold.dataset_id != self.dataset_id:
            raise LeakageError("Dataset mismatch")
        return OriginData(self, fold, tuple(series))

    def validation_targets(self, fold, series):
        return self._read(
            fold, fold.validation_start, fold.validation_end, [*KEYS, "sales_units"], series
        )


@dataclass(frozen=True)
class OriginData:
    _source: ParquetSource
    fold: ValidationFold
    series: tuple[str, ...]

    def __post_init__(self):
        validate_fold(self.fold)
        from intelligent_demand.tuning.authority import assert_training_unlocked

        assert_training_unlocked(self.fold)
        if self._source.dataset_id != self.fold.dataset_id:
            raise LeakageError("Dataset mismatch")
        if (
            not self.series
            or len(self.series) != len(set(self.series))
            or any(not isinstance(value, str) or not value for value in self.series)
        ):
            raise ValueError("Nonempty, unique string series identifiers required")

    def history(self, *, end=None, columns=None):
        end = self.fold.origin if end is None else end
        if end > self.fold.origin:
            raise LeakageError("Historical target access cannot extend past the forecast origin")
        columns = [*KEYS, "sales_units"] if columns is None else list(columns)
        if not set(columns).issubset(HISTORY_COLUMNS):
            raise LeakageError("Unregistered historical fields")
        return self._source._read(self.fold, self.fold.train_start, end, columns, self.series)

    def for_series(self, series_id):
        if series_id not in self.series:
            raise LeakageError("Series is outside the declared comparison population")
        return OriginData(self._source, self.fold, (series_id,))

    def history_before(self, target_date, columns=None):
        if not self.fold.train_start < target_date <= self.fold.origin:
            raise LeakageError("A training-row history requires a prior observed date")
        return self.history(end=target_date - timedelta(days=1), columns=columns)

    def static_metadata(self):
        columns = ["series_id", "store_id", "item_id", "category_id"]
        parts = [batch.drop_duplicates() for batch in self.history(columns=columns)]
        if not parts:
            raise ValueError("No training metadata found")
        result = pd.concat(parts, ignore_index=True).drop_duplicates()
        if result.series_id.duplicated().any() or set(result.series_id) != set(self.series):
            raise LeakageError("Static join is not a complete many-to-one series mapping")
        return result

    def calendar_features(self):
        frame = pd.MultiIndex.from_product(
            [self.series, pd.to_datetime(self.fold.dates)], names=["series_id", "target_date"]
        ).to_frame(index=False)
        frame["horizon_step"] = (frame.target_date - pd.Timestamp(self.fold.origin)).dt.days
        frame["weekday"] = frame.target_date.dt.day_of_week
        frame["month"] = frame.target_date.dt.month
        rule = Availability(
            "known_future", self.fold.origin, "Deterministic Gregorian date calendar"
        )
        return validate_future_features(
            frame, self.fold, self.series, {"weekday": rule, "month": rule}
        )
