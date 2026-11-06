"""Complete-key evaluation, streaming training-only scales and explicit coverage."""

from collections import deque

import numpy as np
import pandas as pd

from intelligent_demand.evaluation.metrics import forecast_metrics
from intelligent_demand.evaluation.predictions import daily_dates
from intelligent_demand.evaluation.splits import validate_fold

METRICS = ["mae", "rmse", "wape_percent", "bias_units", "bias_percent", "mase", "rmsse"]


def training_scales(batches, fold, series, season=7):
    validate_fold(fold)
    if type(season) is not int or season < 1:
        raise ValueError("Positive integer scaling season required")
    records = {
        key: {
            "buffer": deque(maxlen=season),
            "last": None,
            "count": 0,
            "absolute": 0.0,
            "squared": 0.0,
        }
        for key in series
    }
    for batch in batches:
        for row in batch.itertuples(index=False):
            if row.dataset_id != fold.dataset_id or row.series_id not in records:
                raise ValueError("Scaling history has incompatible dataset/series")
            day = pd.Timestamp(row.date).date()
            state = records[row.series_id]
            expected = (
                fold.train_start if state["last"] is None else state["last"] + pd.Timedelta(days=1)
            )
            if (
                day != expected
                or day > fold.origin
                or not np.isfinite(row.sales_units)
                or row.sales_units < 0
            ):
                raise ValueError(
                    "Scaling history must be complete chronological training-only sales"
                )
            if len(state["buffer"]) == season:
                difference = float(row.sales_units) - state["buffer"][0]
                state["absolute"] += abs(difference)
                state["squared"] += difference**2
            state["buffer"].append(float(row.sales_units))
            state["count"] += 1
            state["last"] = day
    output = []
    for key, state in records.items():
        if state["last"] != fold.origin:
            raise ValueError("Incomplete scaling history")
        denominator = state["count"] - season
        absolute = state["absolute"] / denominator if denominator > 0 else 0
        squared = state["squared"] / denominator if denominator > 0 else 0
        output.append(
            {
                "series_id": key,
                "scale_absolute": absolute if absolute > 0 else np.nan,
                "scale_squared": squared if squared > 0 else np.nan,
                "dataset_id": fold.dataset_id,
                "training_start": fold.train_start,
                "training_end": fold.origin,
                "season_days": season,
            }
        )
    return pd.DataFrame(output)


def aligned_observations(actuals, predictions, fold, series):
    validate_fold(fold)
    required = {"dataset_id", "series_id", "target_date"}
    for frame, value in ((actuals, "actual"), (predictions, "prediction")):
        if not required.union({value}).issubset(frame):
            raise ValueError("Missing evaluation keys or values")
    actual, predicted = actuals.copy(), predictions.copy()
    for frame, value in ((actual, "actual"), (predicted, "prediction")):
        frame["target_date"] = daily_dates(frame.target_date)
        if (
            not frame.dataset_id.eq(fold.dataset_id).all()
            or frame.series_id.isna().any()
            or not frame.series_id.isin(series).all()
            or frame.duplicated(list(required)).any()
            or not frame.target_date.between(
                pd.Timestamp(fold.validation_start), pd.Timestamp(fold.validation_end)
            ).all()
            or not np.isfinite(frame[value]).all()
            or frame[value].lt(0).any()
        ):
            raise ValueError(
                "Invalid, duplicated, incompatible or out-of-window evaluation records"
            )
        if len(frame) != len(series) * fold.horizon:
            raise ValueError("Evaluation requires complete declared series × horizon coverage")
    if (
        "forecast_origin" in predicted
        and not daily_dates(predicted.forecast_origin).eq(pd.Timestamp(fold.origin)).all()
    ):
        raise ValueError("Predictions belong to a different origin")
    joined = actual[list(required) + ["actual"]].merge(
        predicted, on=list(required), how="outer", validate="one_to_one", indicator=True
    )
    if not joined._merge.eq("both").all():
        raise ValueError("Actual/prediction business keys do not align")
    joined = joined.drop(columns="_merge")
    steps = (joined.target_date - pd.Timestamp(fold.origin)).dt.days
    if "horizon_step" in joined and not joined.horizon_step.eq(steps).all():
        raise ValueError("Prediction horizon step and target date disagree")
    joined["horizon_step"] = steps
    for flag in ("is_fallback", "was_clipped"):
        if flag not in joined:
            joined[flag] = False
        if joined[flag].dtype != bool or joined[flag].isna().any():
            raise ValueError("Coverage flags must be boolean")
    return joined


def score_predictions(actuals, predictions, scales, fold, series, classes=None, class_as_of=None):
    if len(series) != len(set(series)) or not series:
        raise ValueError("Fixed unique comparison series required")
    joined = aligned_observations(actuals, predictions, fold, series)
    if (
        scales.series_id.duplicated().any()
        or set(scales.series_id) != set(series)
        or not {"scale_absolute", "scale_squared"}.issubset(scales)
    ):
        raise ValueError("One training-only scale pair is required for each series")
    provenance_columns = {"dataset_id", "training_start", "training_end", "season_days"}
    if not provenance_columns.issubset(scales):
        raise ValueError("Scale provenance must identify the training window and season")
    if (
        not scales.dataset_id.eq(fold.dataset_id).all()
        or not daily_dates(scales.training_start).eq(pd.Timestamp(fold.train_start)).all()
        or not daily_dates(scales.training_end).eq(pd.Timestamp(fold.origin)).all()
        or not scales.season_days.eq(7).all()
    ):
        raise ValueError("Scaling window must be this origin's training history with season=7")
    scales = scales.copy()
    for column in ("scale_absolute", "scale_squared"):
        if any(isinstance(value, (bool, np.bool_)) for value in scales[column].dropna()):
            raise ValueError("Training scales must be numeric quantities, not flags")
        scales[column] = pd.to_numeric(scales[column], errors="raise").astype(float)
        if not (scales[column].isna() | (np.isfinite(scales[column]) & scales[column].gt(0))).all():
            raise ValueError("Undefined scales are null, never zero or infinite")
    if classes is None:
        classes = {key: "unclassified" for key in series}
    elif (
        class_as_of is None
        or class_as_of > fold.origin
        or set(classes) != set(series)
        or any(not isinstance(value, str) or not value for value in classes.values())
    ):
        raise ValueError("Demand classes must cover all series and predate this origin")
    joined = joined.merge(
        scales[["series_id", "scale_absolute", "scale_squared"]],
        on="series_id",
        validate="many_to_one",
    )
    joined["demand_class"] = joined.series_id.map(classes)

    def summary(frame, include_series=False):
        error = frame.prediction - frame.actual
        grouped = (
            frame.assign(error=error, absolute_error=error.abs(), squared_error=error**2)
            .groupby("series_id", sort=True)
            .agg(
                count=("actual", "size"),
                actual_total=("actual", "sum"),
                absolute_total=("absolute_error", "sum"),
                squared_mean=("squared_error", "mean"),
                bias=("error", "mean"),
                scale_absolute=("scale_absolute", "first"),
                scale_squared=("scale_squared", "first"),
            )
        )
        table = pd.DataFrame(index=grouped.index)
        table["mae"] = grouped.absolute_total / grouped["count"]
        table["rmse"] = np.sqrt(grouped.squared_mean)
        table["bias_units"] = grouped.bias
        denominator = grouped.actual_total.where(grouped.actual_total.gt(0))
        table["wape_percent"] = 100 * grouped.absolute_total / denominator
        table["bias_percent"] = 100 * grouped.bias * grouped["count"] / denominator
        table["mase"] = table.mae / grouped.scale_absolute
        table["rmsse"] = table.rmse / np.sqrt(grouped.scale_squared)
        counts = {metric: int(table[metric].notna().sum()) for metric in METRICS}
        macro = {
            metric: float(table[metric].mean()) if counts[metric] else None for metric in METRICS
        }
        pooled = forecast_metrics(frame.actual.to_numpy(), frame.prediction.to_numpy())
        coverage = {
            "observations": len(frame),
            "series": len(table),
            "defined_series": counts,
            "undefined_series": {metric: len(table) - counts[metric] for metric in METRICS},
            "fallback_observations": int(frame.is_fallback.sum()),
            "clipped_observations": int(frame.was_clipped.sum()),
        }
        result = {"pooled": pooled, "macro": macro, "coverage": coverage}
        if include_series:
            table = table.reset_index()
            result["per_series"] = (
                table.astype(object).where(pd.notna(table), None).to_dict(orient="records")
            )
        return result

    return {
        "dataset_id": fold.dataset_id,
        "fold": fold.number,
        "origin": str(fold.origin),
        "validation_start": str(fold.validation_start),
        "validation_end": str(fold.validation_end),
        "expected_observations": len(series) * fold.horizon,
        "all": summary(joined, include_series=True),
        "by_horizon": {
            str(int(key)): summary(frame) for key, frame in joined.groupby("horizon_step")
        },
        "by_demand_class": {key: summary(frame) for key, frame in joined.groupby("demand_class")},
    }
