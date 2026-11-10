"""Read-only post-audit reconciliation of saved Phase 5 per-series outputs.

Re-aggregates all 544 completed cases directly from their persisted per-series Parquet files,
cross-checks them against the saved audit summary, and derives only descriptive tables that the
independent Claude audit requested (per-origin comparisons, scenario counts, fixed-ROP behaviour,
M5 sparse subgroup). It reads no demand targets, forecasts or models, runs no simulation and
never overwrites an existing output (exclusive creation).

Usage (from the project root):
    .venv\\Scripts\\python.exe reports/inventory/post_audit_reconcile.py
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "artifacts/inventory/phase5/runs"
OUTPUT = ROOT / "reports/inventory/post_audit_reconciliation.json"
POLICIES = ("fixed_reorder_point", "moving_average_28", "seasonal_naive", "selected_ml")
COLUMNS = [
    "series_id", "demand_units", "fulfilled_units", "unmet_units", "total_cost", "holding_cost",
    "shortage_cost", "ordering_cost", "stockout_days", "orders", "average_on_hand",
    "average_inventory_position", "historical_mean56", "forecast_mae",
    "origin_sample_all_zero", "retrospective_final_training_all_zero",
]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_cases():
    cases = {}
    for path in RUNS.glob("*/status.json"):
        status = json.loads(path.read_text(encoding="utf-8"))
        if status["status"] != "completed":
            raise ValueError("Incomplete case present")
        key = (status["dataset"], status["fold"]["number"], status["scenario"]["identifier"],
               status["policy"])
        cases[key] = status
    if len(cases) != 544:
        raise ValueError("Expected exactly 544 completed cases")
    return cases


def aggregate(cases):
    rows, tables = [], {}
    for key, status in sorted(cases.items()):
        item = ROOT / status["files"]["series"]["path"]
        if sha256(item) != status["files"]["series"]["sha256"]:
            raise ValueError("Persisted case output changed: " + item.as_posix())
        frame = pq.read_table(item, columns=COLUMNS).to_pandas()
        dataset, fold, scenario, policy = key
        rows.append({
            "dataset": dataset, "fold": fold, "scenario": scenario, "policy": policy,
            "series": len(frame), "total_cost": frame.total_cost.sum(),
            "demand_units": frame.demand_units.sum(),
            "fulfilled_units": frame.fulfilled_units.sum(),
            "holding_cost": frame.holding_cost.sum(), "shortage_cost": frame.shortage_cost.sum(),
            "ordering_cost": frame.ordering_cost.sum(), "stockout_days": frame.stockout_days.sum(),
            "orders": frame.orders.sum(), "average_on_hand_sum": frame.average_on_hand.sum(),
            "forecast_mae_mean": frame.forecast_mae.mean(),
        })
        if scenario == "base":
            tables[(dataset, fold, policy)] = frame
    return pd.DataFrame(rows), tables


def reconcile_with_saved(frame):
    saved = json.loads((ROOT / "reports/inventory/phase5_summary.json").read_text(encoding="utf-8"))
    summary = pd.DataFrame(saved["summaries"])
    merged = frame.merge(summary, on=["dataset", "fold", "scenario", "policy"], suffixes=("", "_s"),
                         validate="one_to_one")
    checked = 0
    for mine, theirs in (("total_cost", "total_cost"), ("demand_units", "demand_units"),
                         ("fulfilled_units", "fulfilled_units"), ("holding_cost", "holding_cost"),
                         ("shortage_cost", "shortage_cost"), ("ordering_cost", "ordering_cost"),
                         ("stockout_days", "stockout_days"), ("orders", "orders"),
                         ("series", "series")):
        left, right = merged[mine].to_numpy(float), merged[theirs + "_s"].to_numpy(float)
        if not np.allclose(left, right, rtol=1e-9, atol=1e-6):
            raise ValueError("Raw re-aggregation disagrees with saved audit summary: " + mine)
        checked += len(merged)
    return {"cases": len(merged), "metric_comparisons": checked,
            "summary_sha256": sha256(ROOT / "reports/inventory/phase5_summary.json")}


def pooled(frame, keys):
    grouped = frame.groupby(keys).agg(
        series=("series", "sum"), total_cost=("total_cost", "sum"),
        demand=("demand_units", "sum"), fulfilled=("fulfilled_units", "sum"),
        on_hand=("average_on_hand_sum", "sum"), stockout_days=("stockout_days", "sum"),
        mae=("forecast_mae_mean", "mean"),
    )
    grouped["mean_cost"] = grouped.total_cost / grouped.series
    grouped["pooled_fill"] = grouped.fulfilled / grouped.demand
    grouped["average_on_hand"] = grouped.on_hand / grouped.series
    grouped["cost_per_demand_unit"] = grouped.total_cost / grouped.demand
    grouped["stockout_days_per_episode"] = grouped.stockout_days / grouped.series
    return grouped


def build():
    cases = load_cases()
    frame, tables = aggregate(cases)
    reconciliation = reconcile_with_saved(frame)
    result = {"schema_version": 1, "purpose": "Post-independent-audit descriptive reconciliation; "
              "no simulation, forecast, target or model access",
              "reconciliation_with_saved_summary": reconciliation,
              "plan_sha256": json.loads((ROOT / "artifacts/inventory/phase5/plan.json")
                                        .read_text(encoding="utf-8"))["sha256"]}
    base = frame[frame.scenario == "base"]
    scenarios = sorted(frame.scenario.unique())
    result["scenario_count"] = len(scenarios)
    by_origin = pooled(base, ["dataset", "fold", "policy"])
    overall = pooled(base, ["dataset", "policy"])
    result["base_pooled"] = {
        d: {p: {"mean_cost": float(overall.loc[(d, p), "mean_cost"]),
                "pooled_fill_rate": float(overall.loc[(d, p), "pooled_fill"]),
                "average_on_hand": float(overall.loc[(d, p), "average_on_hand"]),
                "cost_per_demand_unit": float(overall.loc[(d, p), "cost_per_demand_unit"]),
                "stockout_days_per_episode": float(
                    overall.loc[(d, p), "stockout_days_per_episode"])}
            for p in POLICIES} for d in ("store_item", "m5")}
    result["base_by_origin"] = {
        d: {str(f): {p: {"mean_cost": float(by_origin.loc[(d, f, p), "mean_cost"]),
                         "pooled_fill_rate": float(by_origin.loc[(d, f, p), "pooled_fill"]),
                         "forecast_mae": float(by_origin.loc[(d, f, p), "mae"])
                         if p != "fixed_reorder_point" else None}
                     for p in POLICIES} for f in (1, 2, 3, 4)} for d in ("store_item", "m5")}
    comparisons = {}
    scenario_pooled = pooled(frame, ["dataset", "scenario", "policy"])
    scenario_origin = pooled(frame, ["dataset", "fold", "scenario", "policy"])
    for dataset in ("store_item", "m5"):
        comparisons[dataset] = {}
        for reference in ("moving_average_28", "seasonal_naive"):
            base_difference = (overall.loc[(dataset, "selected_ml"), "mean_cost"]
                               - overall.loc[(dataset, reference), "mean_cost"])
            per_origin = [float(by_origin.loc[(dataset, f, "selected_ml"), "mean_cost"]
                                - by_origin.loc[(dataset, f, reference), "mean_cost"])
                          for f in (1, 2, 3, 4)]
            pooled_scn = {s: float(scenario_pooled.loc[(dataset, s, "selected_ml"), "mean_cost"]
                                   - scenario_pooled.loc[(dataset, s, reference), "mean_cost"])
                          for s in scenarios}
            cheaper_by_origin = {}
            for f in (1, 2, 3, 4):
                cheaper_by_origin[str(f)] = int(sum(
                    scenario_origin.loc[(dataset, f, s, "selected_ml"), "mean_cost"]
                    < scenario_origin.loc[(dataset, f, s, reference), "mean_cost"]
                    for s in scenarios))
            comparisons[dataset][reference] = {
                "base_difference": float(base_difference),
                "base_percent": float(100 * base_difference
                                      / overall.loc[(dataset, reference), "mean_cost"]),
                "per_origin_difference": per_origin,
                "origins_where_ml_cheaper": int(sum(v < 0 for v in per_origin)),
                "scenarios_ml_cheaper_pooled": int(sum(v < 0 for v in pooled_scn.values())),
                "scenarios_ml_cheaper_by_origin": cheaper_by_origin,
                "scenario_origin_cells_ml_cheaper": int(sum(cheaper_by_origin.values())),
                "scenario_origin_cells": 4 * len(scenarios),
                "pooled_scenario_difference_range": [min(pooled_scn.values()),
                                                     max(pooled_scn.values())],
                "base_fill_difference_points": float(100 * (
                    overall.loc[(dataset, "selected_ml"), "pooled_fill"]
                    - overall.loc[(dataset, reference), "pooled_fill"])),
            }
    result["ml_comparisons"] = comparisons
    rop = {}
    for dataset in ("store_item", "m5"):
        eligible = share = orders = ratio = 0.0
        count = 0
        for fold in (1, 2, 3, 4):
            frame_rop = tables[(dataset, fold, "fixed_reorder_point")]
            positive = frame_rop[frame_rop.historical_mean56 > 0]
            share += float((positive.orders == 20).sum())
            eligible += len(positive)
            orders += float(positive.orders.sum())
            ratio += float((positive.average_inventory_position / positive.historical_mean56).sum())
            count += len(positive)
        fixed = {s: bool(scenario_pooled.loc[(dataset, s), "mean_cost"].idxmin()
                         == "fixed_reorder_point") for s in scenarios}
        lower_fill = {
            s: bool(scenario_pooled.loc[(dataset, s, "fixed_reorder_point"), "pooled_fill"]
                    < scenario_pooled.loc[(dataset, s, "selected_ml"), "pooled_fill"])
            for s in scenarios}
        rop[dataset] = {
            "eligible_reviews_in_base_episode": 20,
            "reorder_point_in_mean_days_of_demand": 11,
            "positive_mean_series_episodes": int(eligible),
            "share_ordering_at_every_eligible_review": share / eligible,
            "mean_orders_per_episode": orders / eligible,
            "mean_inventory_position_in_mean_days": ratio / count,
            "scenarios_where_fixed_rop_has_lowest_mean_cost": int(sum(fixed.values())),
            "scenarios_where_fixed_rop_fill_below_selected_ml": int(sum(lower_fill.values())),
        }
    result["fixed_reorder_point"] = rop
    sparse = {}
    for mask in ("retrospective_final_training_all_zero", "origin_sample_all_zero"):
        sparse[mask] = {}
        for fold in (1, 2, 3, 4):
            ml = tables[("m5", fold, "selected_ml")]
            ma = tables[("m5", fold, "moving_average_28")]
            group = ml[mask].to_numpy()
            sparse[mask][str(fold)] = {
                "series": int(group.sum()),
                "ml_mae_in_group": float(ml.forecast_mae[group].mean()),
                "ma28_mae_in_group": float(ma.forecast_mae[group].mean()),
                "ml_mae_rest": float(ml.forecast_mae[~group].mean()),
                "ma28_mae_rest": float(ma.forecast_mae[~group].mean()),
                "cost_ml_minus_ma28_in_group": float(
                    (ml.total_cost[group] - ma.total_cost[group]).mean()),
                "cost_ml_minus_ma28_rest": float(
                    (ml.total_cost[~group] - ma.total_cost[~group]).mean()),
            }
    result["m5_sparse_subgroup"] = sparse
    ties = {}
    for fold in (1, 2, 3, 4):
        ml = tables[("m5", fold, "selected_ml")]
        ma = tables[("m5", fold, "moving_average_28")]
        difference = ml.total_cost.to_numpy() - ma.total_cost.to_numpy()
        ties[str(fold)] = {"tied_series": int((np.abs(difference) <= 1e-8).sum()),
                           "median_difference": float(np.median(difference)),
                           "series": len(difference)}
    result["m5_paired_ties"] = ties
    board = json.loads((ROOT / "artifacts/experiments/phase4/trial_leaderboard.json")
                       .read_text(encoding="utf-8"))
    frozen = json.loads((ROOT / "artifacts/experiments/phase4/frozen_selection.json")
                        .read_text(encoding="utf-8"))
    tuning = {}
    for dataset in ("store_item", "m5"):
        rows = [r for r in board if r["dataset"] == dataset]
        tuning[dataset] = {
            "tuning_configurations": sum(r["kind"] == "tuning" for r in rows),
            "reference_configurations": sum(r["kind"] == "reference" for r in rows),
            "selected_trial": frozen["datasets"][dataset]["selected_trial_id"],
        }
    result["phase4_selection_asymmetry"] = tuning
    if OUTPUT.exists():
        raise FileExistsError("Refusing to overwrite existing reconciliation output")
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "written", "cases": reconciliation["cases"],
                      "metric_comparisons": reconciliation["metric_comparisons"]}))
    return result


if __name__ == "__main__":
    sys.exit(0 if build() else 1)
