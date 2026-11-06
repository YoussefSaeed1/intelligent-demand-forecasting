"""Full-panel descriptive statistics and explicit intermittency conventions."""

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import acf

PATTERNS = [
    "smooth",
    "erratic",
    "intermittent",
    "lumpy",
    "all_zero",
    "insufficient_positive_history",
]


def classify_patterns(
    adi: np.ndarray,
    cv2: np.ndarray,
    positive_count: np.ndarray,
    adi_threshold: float = 1.32,
    cv2_threshold: float = 0.49,
) -> np.ndarray:
    """Equality belongs to the high group; undefined size variance is never forced into a class."""
    labels = np.full(len(adi), "insufficient_positive_history", dtype=object)
    labels[positive_count == 0] = "all_zero"
    valid = (positive_count >= 2) & np.isfinite(adi) & np.isfinite(cv2)
    for label, intermittent, variable in (
        ("smooth", False, False),
        ("erratic", False, True),
        ("intermittent", True, False),
        ("lumpy", True, True),
    ):
        labels[
            valid & ((adi >= adi_threshold) == intermittent) & ((cv2 >= cv2_threshold) == variable)
        ] = label
    return labels


def panel_statistics(
    values: np.ndarray, adi_threshold: float = 1.32, cv2_threshold: float = 0.49
) -> pd.DataFrame:
    """ADI=T/nonzero count; positive-size CVÂ² uses sample variance (ddof=1)."""
    y = np.asarray(values, dtype=float)
    if y.ndim != 2 or not y.shape[1] or not np.isfinite(y).all() or (y < 0).any():
        raise ValueError("Finite, nonnegative, complete series-by-day panel required")
    n, periods = y.shape
    records = []
    for first in range(0, n, 256):
        block = y[first : first + 256]
        positive = block > 0
        count = positive.sum(axis=1)
        total = block.sum(axis=1)
        squares = np.square(block).sum(axis=1)
        mean_positive = np.divide(total, count, out=np.full(len(block), np.nan), where=count > 0)
        variance = np.divide(
            squares - np.divide(total**2, count, out=np.zeros(len(block)), where=count > 0),
            count - 1,
            out=np.full(len(block), np.nan),
            where=count > 1,
        )
        cv2 = np.maximum(variance, 0) / mean_positive**2
        adi = np.divide(periods, count, out=np.full(len(block), np.nan), where=count > 0)
        first_positive = np.where(count > 0, positive.argmax(axis=1), -1)
        last_positive = np.where(count > 0, periods - 1 - positive[:, ::-1].argmax(axis=1), -1)
        active_periods = np.where(count > 0, periods - first_positive, 0)
        active_adi = np.divide(
            active_periods, count, out=np.full(len(block), np.nan), where=count > 0
        )
        frame = pd.DataFrame(
            {
                "observations": periods,
                "sales_units": total,
                "positive_count": count,
                "nonzero_frequency": count / periods,
                "zero_percent": 100 * (periods - count) / periods,
                "mean_units": block.mean(axis=1),
                "std_units": block.std(axis=1, ddof=1) if periods > 1 else np.nan,
                "positive_mean": mean_positive,
                "adi": adi,
                "cv2_positive": cv2,
                "first_positive_index": first_positive,
                "last_positive_index": last_positive,
                "active_span_days": active_periods,
                "active_span_adi": active_adi,
                "maximum_units": block.max(axis=1),
            }
        )
        frame["pattern"] = classify_patterns(adi, cv2, count, adi_threshold, cv2_threshold)
        frame["active_span_pattern"] = classify_patterns(
            active_adi, cv2, count, adi_threshold, cv2_threshold
        )
        for lag in (1, 7, 28, 365):
            if periods <= lag + 1:
                frame[f"corr_lag_{lag}"] = np.nan
                continue
            left, right = block[:, :-lag], block[:, lag:]
            x, z = (
                left - left.mean(axis=1, keepdims=True),
                right - right.mean(axis=1, keepdims=True),
            )
            denominator = np.sqrt(np.square(x).sum(axis=1) * np.square(z).sum(axis=1))
            frame[f"corr_lag_{lag}"] = np.divide(
                (x * z).sum(axis=1),
                denominator,
                out=np.full(len(block), np.nan),
                where=denominator > 0,
            )
        records.append(frame)
    return pd.concat(records, ignore_index=True)


def price_activity(missing: np.ndarray, values: np.ndarray) -> tuple[pd.DataFrame, dict]:
    """Partition prices by observed sales span; do not impute or infer availability."""
    if missing.shape != values.shape:
        raise ValueError("Aligned price mask and sales panel required")
    records = []
    days = np.arange(values.shape[1])
    for first in range(0, len(values), 256):
        y, mask = values[first : first + 256], missing[first : first + 256]
        positive = y > 0
        count = positive.sum(axis=1)
        start = np.where(count > 0, positive.argmax(axis=1), -1)
        end = np.where(count > 0, y.shape[1] - 1 - positive[:, ::-1].argmax(axis=1), -1)
        has_sales = count[:, None] > 0
        before = (mask & has_sales & (days < start[:, None])).sum(axis=1)
        between = (mask & has_sales & (days >= start[:, None]) & (days <= end[:, None])).sum(axis=1)
        after = (mask & has_sales & (days > end[:, None])).sum(axis=1)
        never = (mask & ~has_sales).sum(axis=1)
        records.append(
            pd.DataFrame(
                {
                    "missing_prices": mask.sum(axis=1),
                    "missing_before_first_positive": before,
                    "missing_between_first_last_positive": between,
                    "missing_after_last_positive": after,
                    "missing_no_positive_in_eda": never,
                    "missing_with_positive_sales": (mask & positive).sum(axis=1),
                    "missing_with_zero_sales": (mask & ~positive).sum(axis=1),
                }
            )
        )
    frame = pd.concat(records, ignore_index=True)
    parts = [
        "missing_before_first_positive",
        "missing_between_first_last_positive",
        "missing_after_last_positive",
        "missing_no_positive_in_eda",
    ]
    if not np.array_equal(frame[parts].sum(axis=1), frame.missing_prices):
        raise ValueError("Missing-price partition does not reconcile")
    return frame, {column: int(frame[column].sum()) for column in frame}


def weekday_bootstrap(
    daily: pd.DataFrame, seed: int, repetitions: int = 500, block_weeks: int = 4
) -> pd.DataFrame:
    """Bootstrap complete, within-week normalised weeks in moving four-week blocks."""
    work = daily.copy()
    iso = work.date.dt.isocalendar()
    work["week"] = iso.year.astype(str) + "-" + iso.week.astype(str)
    work["weekday"] = work.date.dt.day_of_week
    weeks = work.pivot(index="week", columns="weekday", values="sales_units").dropna()
    # Lexical week IDs are not chronological; sort by the actual first date.
    first_dates = work.groupby("week").date.min()
    weeks = weeks.loc[first_dates.loc[weeks.index].sort_values().index]
    weeks = weeks.loc[weeks.mean(axis=1) > 0]
    ratios = weeks.to_numpy() / weeks.mean(axis=1).to_numpy()[:, None]
    if len(ratios) < block_weeks:
        raise ValueError("Insufficient complete weeks for block bootstrap")
    rng = np.random.default_rng(seed)
    estimates = np.empty((repetitions, 7))
    for repeat in range(repetitions):
        starts = rng.integers(
            0, len(ratios) - block_weeks + 1, size=int(np.ceil(len(ratios) / block_weeks))
        )
        indexes = (starts[:, None] + np.arange(block_weeks)).ravel()[: len(ratios)]
        estimates[repeat] = ratios[indexes].mean(axis=0)
    return pd.DataFrame(
        {
            "weekday": np.arange(7),
            "mean_within_week_ratio": ratios.mean(axis=0),
            "ci_low": np.quantile(estimates, 0.025, axis=0),
            "ci_high": np.quantile(estimates, 0.975, axis=0),
            "complete_weeks": len(ratios),
        }
    )


def aggregate_diagnostics(daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Diagnostic decomposition and aggregate ACF, never a forecasting estimator."""
    log_sales = np.log1p(daily.sales_units.to_numpy())
    weekly = STL(log_sales, period=7, seasonal=13, robust=True).fit()
    annual = STL(log_sales - weekly.seasonal, period=365, seasonal=7, robust=True).fit()

    def strength(residual, seasonal):
        denominator = np.var(residual + seasonal)
        return max(0.0, 1 - float(np.var(residual) / denominator)) if denominator else None

    lags = min(400, len(daily) - 2)
    correlation = pd.DataFrame(
        {
            "lag": np.arange(lags + 1),
            "log_level_acf": acf(log_sales, nlags=lags, fft=True),
            "log_first_difference_acf": acf(np.diff(log_sales), nlags=lags, fft=True),
        }
    )
    components = daily[["date"]].copy()
    components["log_sales"] = log_sales
    components["weekly_component"] = weekly.seasonal
    components["annual_component_after_weekly"] = annual.seasonal
    components["trend_after_weekly"] = annual.trend
    info = {
        "aggregate_weekly_strength": strength(weekly.resid, weekly.seasonal),
        "aggregate_annual_strength_after_weekly": strength(annual.resid, annual.seasonal),
        "annual_period_caveat": "365-day approximation; leap-calendar misalignment; aggregate only",
    }
    return correlation, components, info
