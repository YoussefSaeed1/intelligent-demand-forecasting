"""Independent persisted training-array checks against origin-bounded source values."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.registry import file_digest


def audit_ml_training(state, directory, panel):
    series = tuple(panel.metadata.series_id)
    spec = state["specification"]
    outputs = state["outputs"]
    required = {"model_0_estimator", "model_0_feature_schema", "model_0_reload_validation"}
    if not required.issubset(outputs):
        raise ValueError("ML persistence evidence is incomplete")
    schema = json.loads((directory / outputs["model_0_feature_schema"]["path"]).read_text())
    proof = json.loads((directory / outputs["model_0_reload_validation"]["path"]).read_text())
    metadata = json.loads((directory / outputs["model_metadata"]["path"]).read_text())[0]
    config = spec["model_configuration"]
    contract = metadata["feature_cache_contract"]
    if (
        proof.get("passed") is not True
        or proof.get("probe_rows") != 16
        or proof.get("rtol") != 1e-12
        or proof.get("atol") != 1e-12
        or contract["source"] != spec["source_fingerprint"]
        or contract["origin"] != spec["fold"]["origin"]
        or contract["population"] != identity(list(series))
        or contract["encoder"] != identity(schema)
        or contract["seed"] != spec["random_seed"]
        or metadata["strategy"] != "recursive_28"
        or schema["observed_activity_policy"] != "frozen_at_true_forecast_origin"
    ):
        raise ValueError("ML origin/schema/reload contract differs from its run")
    cache = Path(config["feature_cache"]) / identity(contract)
    manifest = json.loads((cache / "complete.json").read_text())
    if manifest["contract"] != contract:
        raise ValueError("ML training manifest contract differs")
    for name, digest in manifest["files"].items():
        if file_digest(cache / name) != digest:
            raise ValueError("Persisted supervised array checksum differs")
    x, y, positions = (
        np.load(cache / manifest["names"][key], mmap_mode="r")
        for key in ("features", "labels", "positions")
    )
    per_series = min(len(panel.dates) - 56, config["maximum_training_rows"] // len(series))
    expected_rows = len(series) * per_series
    if (
        x.shape != (expected_rows, len(schema["feature_names"]))
        or y.shape != (expected_rows,)
        or positions.shape != (expected_rows, 2)
        or x.dtype != np.float32
        or y.dtype != np.float32
        or positions.dtype != np.int32
        or manifest["training_rows"] != expected_rows
        or metadata["training_rows"] != expected_rows
        or proof["training_rows"] != expected_rows
    ):
        raise ValueError("ML bounded-training coverage/types differ")
    rows, targets = positions[:, 0], positions[:, 1]
    if (
        (rows < 0).any()
        or (rows >= len(series)).any()
        or (targets < 56).any()
        or (targets >= len(panel.dates)).any()
        or len(np.unique(rows.astype("int64") * len(panel.dates) + targets)) != expected_rows
        or not np.all(np.bincount(rows, minlength=len(series)) == per_series)
        or manifest["target_min"] != str(panel.dates[targets.min()].date())
        or manifest["target_max"] != str(panel.dates[targets.max()].date())
        or manifest["max_source_date"]
        != str((panel.dates[targets.max()] - pd.Timedelta(days=1)).date())
    ):
        raise ValueError("ML supervised target positions violate historical coverage")
    fields = ["store_id", "item_id"] + (
        ["cat_id", "dept_id", "state_id"] if spec["dataset_id"] == "m5" else []
    )
    expected_names = [
        *(f"lag_{n}" for n in (1, 7, 14, 28, 56)),
        "rolling_mean7",
        "rolling_mean28",
        "rolling_mean56",
        "rolling_std7",
        "rolling_std28",
        "obs_zero_fraction28",
        "obs_zero_fraction56",
        "obs_positive_count56",
        "obs_adi56",
        "obs_positive_cv2_56",
        "obs_last_positive_age_capped56",
        "day_of_week",
        "day_of_month",
        "month",
        "weekend",
        "annual_sin",
        "annual_cos",
        "weekly_sin",
        "weekly_cos",
        "days_since_training_start",
        *(f"{field}_code" for field in fields),
    ]
    if spec["dataset_id"] == "m5":
        expected_names += ["origin_observed_price_mean28", "origin_price_missing_fraction28"]
    if schema["feature_names"] != expected_names:
        raise ValueError("Unexpected ML feature or unavailable covariate")
    for field in fields:
        mapping = {
            str(value): number
            for number, value in enumerate(sorted(panel.metadata[field].astype(str).unique()))
        }
        if schema["static_mappings"][field] != mapping:
            raise ValueError("Static ID mapping differs from the declared universe")
    for start in range(0, expected_rows, 8192):
        r, t = rows[start : start + 8192], targets[start : start + 8192]
        if not np.array_equal(y[start : start + len(r)], panel.values[r, t]):
            raise ValueError("Supervised labels differ from historical source targets")
        past = panel.values[r[:, None], t[:, None] + np.arange(-56, 0)].astype(float)
        expected = {f"lag_{lag}": past[:, 56 - lag] for lag in (1, 7, 14, 28, 56)}
        for width in (7, 28, 56):
            expected[f"rolling_mean{width}"] = np.sum(past[:, 56 - width :], axis=1) / width
        for width in (7, 28):
            block = past[:, 56 - width :]
            expected[f"rolling_std{width}"] = np.sqrt(
                np.mean((block - block.mean(axis=1)[:, None]) ** 2, axis=1)
            )
        count = np.count_nonzero(past, axis=1)
        expected["obs_zero_fraction28"] = np.count_nonzero(past[:, -28:] == 0, axis=1) / 28
        expected["obs_zero_fraction56"] = 1 - count / 56
        expected["obs_positive_count56"] = count
        with np.errstate(divide="ignore", invalid="ignore"):
            mean = past.sum(axis=1) / count
            centered = np.where(past > 0, past - mean[:, None], 0)
            expected["obs_adi56"] = np.where(count > 0, 56 / count, np.nan)
            expected["obs_positive_cv2_56"] = np.where(
                count > 1, (centered**2).sum(axis=1) / (count - 1) / mean**2, np.nan
            )
        expected["obs_last_positive_age_capped56"] = np.min(
            np.where(past > 0, np.arange(55, -1, -1), 56), axis=1
        )
        dates = panel.dates.take(t)
        dow = dates.day_of_week.to_numpy()
        phase = (dates.day_of_year.to_numpy() - 1) / np.where(dates.is_leap_year, 366, 365)
        expected.update(
            day_of_week=dow,
            day_of_month=dates.day.to_numpy(),
            month=dates.month.to_numpy(),
            weekend=dow >= 5,
            annual_sin=np.sin(2 * np.pi * phase),
            annual_cos=np.cos(2 * np.pi * phase),
            weekly_sin=np.sin(2 * np.pi * dow / 7),
            weekly_cos=np.cos(2 * np.pi * dow / 7),
            days_since_training_start=(dates - pd.Timestamp(spec["fold"]["train_start"])).days,
        )
        for field in fields:
            expected[f"{field}_code"] = (
                panel.metadata[field]
                .astype(str)
                .map(schema["static_mappings"][field])
                .to_numpy()[r]
            )
        if spec["dataset_id"] == "m5":
            price = panel.prices[r[:, None], t[:, None] + np.arange(-34, -6)].astype(float)
            available = np.isfinite(price)
            n = available.sum(axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                expected["origin_observed_price_mean28"] = np.where(
                    n > 0, np.where(available, price, 0).sum(axis=1) / n, np.nan
                )
            expected["origin_price_missing_fraction28"] = 1 - n / 28
        for col, name in enumerate(expected_names):
            if not np.allclose(
                x[start : start + len(r), col],
                np.asarray(expected[name], dtype="float32"),
                rtol=1e-6,
                atol=1e-6,
                equal_nan=True,
            ):
                raise ValueError(f"Independent historical feature reconciliation failed: {name}")
    return {
        "status": "passed",
        "training_rows": expected_rows,
        "feature_count": x.shape[1],
        "source_labels_and_all_features_reconciled": True,
        "reload_verified": True,
    }
