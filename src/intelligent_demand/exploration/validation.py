"""Independent reconciliation of saved Phase 2 analytical tables and input hashes."""

import json

import numpy as np
import pandas as pd

from intelligent_demand.config import ProjectConfig
from intelligent_demand.ingestion.datasets import sha256, write_json


def reconcile_training_sources(config: ProjectConfig, results: dict) -> dict:
    """Independently sum training-only CSV quantities in bounded chunks, not via adapters."""
    checks = {}
    raw = config.paths["raw"]
    result = results["store_item"]
    rows, total, zeros = 0, 0, 0
    for chunk in pd.read_csv(
        raw / "store_item/train.csv", usecols=["date", "sales"], chunksize=65_536
    ):
        values = chunk.loc[chunk.date.le(result["split_plan"]["eda_end"]), "sales"].to_numpy()
        rows += len(values)
        total += int(values.sum())
        zeros += int((values == 0).sum())
    checks["store_item"] = {"rows": rows, "sales_units": total, "zero_count": zeros}
    result = results["m5"]
    calendar = pd.read_csv(raw / "m5/calendar.csv", usecols=["d", "date"])
    columns = calendar.loc[
        calendar.date.between(result["split_plan"]["eda_start"], result["split_plan"]["eda_end"]),
        "d",
    ].tolist()
    rows, total, zeros = 0, 0, 0
    for chunk in pd.read_csv(
        raw / "m5/sales_train_evaluation.csv", usecols=columns, dtype="int32", chunksize=512
    ):
        values = chunk.to_numpy()
        rows += values.size
        total += int(values.sum(dtype="int64"))
        zeros += int((values == 0).sum())
    checks["m5"] = {"rows": rows, "sales_units": total, "zero_count": zeros}
    for name, check in checks.items():
        result = results[name]
        if (
            check["rows"] != result["eda_rows"]
            or check["sales_units"] != result["eda_sales_units"]
            or check["zero_count"] != result["eda_zero_count"]
        ):
            raise ValueError(f"{name}: independent source training totals disagree")
    return checks


def validate_outputs(config: ProjectConfig) -> dict:
    """Validate saved outputs without scanning or transforming the full M5 panel again."""
    directory = config.paths["reports"] / "eda"
    checks = {}
    results = {}
    for name in ("store_item", "m5"):
        result = json.loads((directory / f"{name}_results.json").read_text(encoding="utf-8"))
        results[name] = result
        tables = directory / "tables" / name
        series, daily = (
            pd.read_parquet(tables / "series.parquet"),
            pd.read_parquet(tables / "daily.parquet"),
        )
        histogram = pd.read_parquet(tables / "distribution.parquet")
        products, stores = (
            pd.read_parquet(tables / "products.parquet"),
            pd.read_parquet(tables / "stores.parquet"),
        )
        totals = [
            series.sales_units.sum(),
            daily.sales_units.sum(),
            products.sales_units.sum(),
            stores.sales_units.sum(),
            np.dot(histogram.units, histogram.observations),
        ]
        if not all(total == result["eda_sales_units"] for total in totals):
            raise ValueError(f"{name}: saved sales aggregates disagree")
        if histogram.observations.sum() != result["eda_rows"] or len(series) != result["series"]:
            raise ValueError(f"{name}: saved observation counts disagree")
        if histogram.loc[histogram.units.eq(0), "observations"].sum() != result["eda_zero_count"]:
            raise ValueError(f"{name}: saved zero counts disagree")
        if sum(result["patterns"].values()) != len(series):
            raise ValueError("Demand-pattern classes omit series")
        for path in tables.glob("*.parquet"):
            if "full_quality" in path.name:
                continue
            frame = pd.read_parquet(path)
            if "date" in frame and not frame.empty:
                if frame.date.min() < pd.Timestamp(
                    result["split_plan"]["eda_start"]
                ) or frame.date.max() > pd.Timestamp(result["split_plan"]["eda_end"]):
                    raise ValueError(f"Target analysis crossed reserved boundary: {path.name}")
        for file, digest in result["input_raw_sha256"].items():
            if sha256(config.paths["raw"] / name / file) != digest:
                raise ValueError("Raw input changed")
        if (
            sha256(config.paths["processed"] / name / "daily_sales.parquet")
            != result["input_canonical_sha256"]
        ):
            raise ValueError("Canonical input changed")
        if name == "m5":
            price = pd.read_parquet(tables / "price_by_series_eda.parquet")
            partition = price[
                [
                    "missing_before_first_positive",
                    "missing_between_first_last_positive",
                    "missing_after_last_positive",
                    "missing_no_positive_in_eda",
                ]
            ].sum(axis=1)
            if not np.array_equal(partition, price.missing_prices):
                raise ValueError("Saved price partition fails to reconcile")
            for dimension in ("date", "year", "product", "store"):
                frame = pd.read_parquet(tables / f"price_by_{dimension}_full_quality.parquet")
                if (
                    frame.missing_prices.sum()
                    != result["price_missingness"]["full_history_missing"]
                ):
                    raise ValueError("Full-history price marginal disagrees")
        checks[name] = {
            "aggregation_reconciled": True,
            "training_target_boundaries_valid": True,
            "all_series_covered": True,
            "raw_canonical_hashes_unchanged": True,
        }
    source_checks = reconcile_training_sources(config, results)
    report = {
        "status": "passed",
        "checks": checks,
        "independent_training_csv_reconciliation": source_checks,
        "tables": len(list((directory / "tables").rglob("*.parquet"))),
        "png_figures": len(list((config.paths["reports"] / "figures/phase2").glob("*.png"))),
    }
    write_json(directory / "validation.json", report)
    return report
