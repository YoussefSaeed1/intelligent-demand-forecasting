"""Build the Phase 6 Power BI reporting tables from saved, hash-verified Phase 3-5 evidence.

Read-only with respect to all scientific evidence. Validation-window demand is read through the
approved Phase 5 adapter (`load_cohort`), which rejects any period outside the four original
validation origins, so no final-holdout target is read. Saved final-holdout metrics are copied as
reported values only. Missing or undefined values stay empty in the CSV output; nothing is zero-filled.

Usage:  .venv\\Scripts\\python.exe -m intelligent_demand.bi.export
"""

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

from intelligent_demand.inventory.inputs import load_cohort
from intelligent_demand.inventory.plan import plan as frozen_plan

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "configs/powerbi.yaml"
ROLES = ("selected_ml", "moving_average_28", "seasonal_naive")
POLICIES = ("selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def origin_key(dataset, fold):
    return f"{dataset}|{fold}"


def series_key(dataset, series_id):
    return f"{dataset}|{series_id}"


def model_key(dataset, role):
    return f"{dataset}|{role}"


def yes_no(values):
    return np.where(np.asarray(values, dtype=bool), "Yes", "No")


# ------------------------------------------------------------------------------------- dimensions
def dimensions(config, plan, selection):
    datasets = pd.DataFrame(
        [
            {
                "DatasetKey": key,
                "Dataset": meta["label"],
                "DatasetSort": meta["sort"],
                "DatasetDescription": meta["description"],
                "SeriesCount": next(c["series"] for c in plan["cohorts"] if c["dataset"] == key),
                "SelectedTrial": selection["datasets"][key]["selected_trial_id"],
                "TrainingStart": selection["datasets"][key]["training_start"],
            }
            for key, meta in config["datasets"].items()
        ]
    )
    origins = pd.DataFrame(
        [
            {
                "OriginKey": origin_key(c["dataset"], c["fold"]["number"]),
                "DatasetKey": c["dataset"],
                "Fold": c["fold"]["number"],
                "FoldLabel": f"Origin {c['fold']['number']}",
                "OriginDate": c["fold"]["origin"],
                "ValidationStart": c["fold"]["validation_start"],
                "ValidationEnd": c["fold"]["validation_end"],
                "TrainStart": c["fold"]["train_start"],
                "OriginLabel": f"{config['datasets'][c['dataset']]['label']} O{c['fold']['number']} "
                f"({c['fold']['origin']})",
            }
            for c in plan["cohorts"]
        ]
    )
    models = []
    for dataset in config["datasets"]:
        cohorts = [c for c in plan["cohorts"] if c["dataset"] == dataset]
        for role, meta in config["model_roles"].items():
            sources = [c["sources"][role] for c in cohorts]
            models.append(
                {
                    "ModelKey": model_key(dataset, role),
                    "DatasetKey": dataset,
                    "ModelRole": meta["label"],
                    "ModelRoleKey": role,
                    "ModelRoleSort": meta["sort"],
                    "Algorithm": sources[0]["model"],
                    "IsSelectedModel": "Yes" if role == "selected_ml" else "No",
                    "ModelDescription": meta["description"],
                    "ValidationRunIds": ";".join(s["run_id"] for s in sources),
                }
            )
    policies = pd.DataFrame(
        [
            {
                "PolicyKey": key,
                "Policy": meta["label"],
                "PolicySort": meta["sort"],
                "ForecastRoleKey": meta["forecast_role"],
                "PolicyDescription": meta["description"],
                "IsLowStockComparator": "Yes" if key == "fixed_reorder_point" else "No",
            }
            for key, meta in config["policies"].items()
        ]
    )
    base = plan["scenarios"][0]
    scenarios = []
    for order, scenario in enumerate(plan["scenarios"], 1):
        changed = [
            k
            for k in (
                "lead_days",
                "review_days",
                "buffer_days",
                "initial_cover_days",
                "holding_cost",
                "shortage_cost",
                "fixed_order_cost",
                "variable_order_cost",
                "terminal_cost",
                "variability_multiplier",
            )
            if scenario[k] != base[k]
        ]
        scenarios.append(
            {
                "ScenarioKey": scenario["identifier"],
                "Scenario": scenario["identifier"].replace("_", " "),
                "ScenarioGroup": config["scenario_groups"][scenario["identifier"]],
                "ScenarioSort": order,
                "ChangedParameter": ", ".join(changed) if changed else "none (base)",
                "IsBase": "Yes" if scenario["identifier"] == "base" else "No",
                "LeadDays": scenario["lead_days"],
                "ReviewDays": scenario["review_days"],
                "BufferDays": scenario["buffer_days"],
                "InitialCoverDays": scenario["initial_cover_days"],
                "HoldingCost": scenario["holding_cost"],
                "ShortageCost": scenario["shortage_cost"],
                "FixedOrderCost": scenario["fixed_order_cost"],
                "VariableOrderCost": scenario["variable_order_cost"],
                "TerminalCost": scenario["terminal_cost"],
                "VariabilityMultiplier": scenario["variability_multiplier"],
            }
        )
    patterns = pd.DataFrame(
        [
            {
                "PatternKey": key,
                "DemandPattern": meta["label"],
                "PatternSort": meta["sort"],
                "PatternDescription": meta["description"],
            }
            for key, meta in config["demand_patterns"].items()
        ]
    )
    dates = pd.DataFrame({"Date": pd.date_range("2016-01-01", "2017-12-31", freq="D")})
    dates["Year"] = dates.Date.dt.year
    dates["MonthNumber"] = dates.Date.dt.month
    dates["Month"] = dates.Date.dt.strftime("%b")
    dates["YearMonth"] = dates.Date.dt.strftime("%Y-%m")
    dates["DayOfWeekNumber"] = dates.Date.dt.day_of_week + 1
    dates["DayOfWeek"] = dates.Date.dt.strftime("%a")
    dates["IsWeekend"] = yes_no(dates.Date.dt.day_of_week >= 5)
    dates["Date"] = dates.Date.dt.date
    return {
        "DimDataset": datasets,
        "DimValidationOrigin": origins,
        "DimForecastModel": pd.DataFrame(models),
        "DimInventoryPolicy": policies,
        "DimScenario": pd.DataFrame(scenarios),
        "DimDemandPattern": patterns,
        "DimDate": dates,
    }


# ------------------------------------------------------------------------------------- forecasts
def training_scales(cohort, count):
    """Seasonal (lag-7) absolute/squared scales on origin-bounded training history (MASE/RMSSE)."""
    manifest = read_json(ROOT / cohort["training_cache"]["path"])
    values = np.load(
        (ROOT / cohort["training_cache"]["path"]).parent / manifest["values"], mmap_mode="r"
    )
    if values.shape[0] != count:
        raise ValueError("Training cache population differs")
    absolute, squared = np.empty(count), np.empty(count)
    for start in range(0, count, 2048):
        block = np.asarray(values[start : start + 2048], dtype=float)
        difference = block[:, 7:] - block[:, :-7]
        absolute[start : start + 2048] = np.abs(difference).mean(axis=1)
        squared[start : start + 2048] = np.square(difference).mean(axis=1)
    del values
    return np.where(absolute > 0, absolute, np.nan), np.where(squared > 0, squared, np.nan)


def forecast_tables(config, plan):
    evaluation, daily, detail, series_rows = [], [], [], {}
    for cohort in plan["cohorts"]:
        dataset, fold = cohort["dataset"], cohort["fold"]["number"]
        metadata, actual, _, forecasts, coverage = load_cohort(cohort)
        if any(coverage[role] for role in ROLES):
            raise ValueError("Unexpected forecast fallback observations")
        scale_abs, scale_sq = training_scales(cohort, len(metadata))
        keys = [series_key(dataset, s) for s in metadata.series_id]
        dates = pd.date_range(cohort["fold"]["validation_start"], periods=28).date
        detail_ids = (
            set(metadata.series_id)
            if config["series_daily_detail"][dataset] == "all"
            else set(cohort["representatives"])
        )
        if dataset not in series_rows:
            series_rows[dataset] = metadata
        for role in ROLES:
            error = forecasts[role] - actual
            frame = pd.DataFrame(
                {
                    "SeriesKey": keys,
                    "OriginKey": origin_key(dataset, fold),
                    "ModelKey": model_key(dataset, role),
                    "DatasetKey": dataset,
                    "PatternKey": metadata.pattern.to_numpy(),
                    "Observations": 28,
                    "SumAbsError": np.abs(error).sum(axis=1),
                    "SumSquaredError": np.square(error).sum(axis=1),
                    "SumError": error.sum(axis=1),
                    "SumActual": actual.sum(axis=1),
                    "SumForecast": forecasts[role].sum(axis=1),
                    "ScaleAbs": scale_abs,
                    "ScaleSquared": scale_sq,
                    "OriginSampleAllZero": yes_no(metadata.origin_sample_all_zero)
                    if dataset == "m5"
                    else "Not applicable",
                }
            )
            evaluation.append(frame)
            for pattern, rows in metadata.groupby("pattern").indices.items():
                block_error = error[rows]
                daily.append(
                    pd.DataFrame(
                        {
                            "OriginKey": origin_key(dataset, fold),
                            "ModelKey": model_key(dataset, role),
                            "DatasetKey": dataset,
                            "PatternKey": pattern,
                            "Date": dates,
                            "Series": len(rows),
                            "SumActual": actual[rows].sum(axis=0),
                            "SumForecast": forecasts[role][rows].sum(axis=0),
                            "SumAbsError": np.abs(block_error).sum(axis=0),
                            "SumSquaredError": np.square(block_error).sum(axis=0),
                            "SumError": block_error.sum(axis=0),
                        }
                    )
                )
            rows = np.flatnonzero(metadata.series_id.isin(detail_ids).to_numpy())
            detail.append(
                pd.DataFrame(
                    {
                        "SeriesKey": np.repeat(np.asarray(keys)[rows], 28),
                        "OriginKey": origin_key(dataset, fold),
                        "ModelKey": model_key(dataset, role),
                        "DatasetKey": dataset,
                        "PatternKey": np.repeat(metadata.pattern.to_numpy()[rows], 28),
                        "Date": np.tile(dates, len(rows)),
                        "HorizonDay": np.tile(np.arange(1, 29), len(rows)),
                        "Actual": actual[rows].ravel(),
                        "Forecast": forecasts[role][rows].ravel(),
                    }
                )
            )
        print(f"forecast cohort {dataset} fold {fold}: {len(metadata):,} series", flush=True)
        del actual, forecasts
    series = []
    for dataset, metadata in series_rows.items():
        series.append(
            pd.DataFrame(
                {
                    "SeriesKey": [series_key(dataset, s) for s in metadata.series_id],
                    "DatasetKey": dataset,
                    "SeriesId": metadata.series_id,
                    "StoreId": metadata.store_id,
                    "ItemId": metadata.item_id,
                    "DepartmentId": metadata.get("dept_id"),
                    "CategoryId": metadata.get("cat_id"),
                    "StateId": metadata.get("state_id"),
                    "PatternKey": metadata.pattern,
                    "TrainingPrefixUnits": metadata.sales_units,
                    "TrainingPrefixMeanUnits": metadata.mean_units,
                    "RetrospectiveSparseGroup": yes_no(
                        metadata.retrospective_final_training_all_zero
                    )
                    if dataset == "m5"
                    else "Not applicable",
                    "HasDailyDetail": yes_no(
                        metadata.series_id.isin(
                            metadata.series_id
                            if config["series_daily_detail"][dataset] == "all"
                            else next(
                                c["representatives"]
                                for c in plan["cohorts"]
                                if c["dataset"] == dataset
                            )
                        )
                    ),
                }
            )
        )
    return {
        "FactForecastSeriesOrigin": pd.concat(evaluation, ignore_index=True),
        "FactForecastDaily": pd.concat(daily, ignore_index=True),
        "FactForecastSeriesDaily": pd.concat(detail, ignore_index=True),
        "DimSeries": pd.concat(series, ignore_index=True),
    }


# ------------------------------------------------------------------------------------- inventory
SUMMARY = [
    "demand_units",
    "fulfilled_units",
    "unmet_units",
    "received_units",
    "placed_units",
    "holding_cost",
    "shortage_cost",
    "ordering_cost",
    "terminal_cost",
    "total_cost",
    "stockout_days",
    "orders",
    "average_on_hand",
    "average_inventory_position",
    "final_on_hand",
    "final_pipeline",
    "initial_on_hand",
]
RENAME = {
    "demand_units": "DemandUnits",
    "fulfilled_units": "FulfilledUnits",
    "unmet_units": "UnmetUnits",
    "received_units": "ReceivedUnits",
    "placed_units": "PlacedUnits",
    "holding_cost": "HoldingCost",
    "shortage_cost": "ShortageCost",
    "ordering_cost": "OrderingCost",
    "terminal_cost": "TerminalCost",
    "total_cost": "TotalCost",
    "stockout_days": "StockoutDays",
    "orders": "Orders",
    "average_on_hand": "AverageOnHand",
    "average_inventory_position": "AverageInventoryPosition",
    "final_on_hand": "FinalOnHand",
    "final_pipeline": "FinalPipeline",
    "initial_on_hand": "InitialOnHand",
}


def inventory_tables():
    cases = {}
    for path in (ROOT / "artifacts/inventory/phase5/runs").glob("*/status.json"):
        status = read_json(path)
        if status["status"] != "completed":
            raise ValueError("Incomplete inventory case")
        cases[
            (
                status["dataset"],
                status["fold"]["number"],
                status["scenario"]["identifier"],
                status["policy"],
            )
        ] = status
    if len(cases) != 544:
        raise ValueError("Expected 544 completed inventory cases")
    grouped, series = [], []
    for (dataset, fold, scenario, policy), status in sorted(cases.items()):
        item = status["files"]["series"]
        if sha256(ROOT / item["path"]) != item["sha256"]:
            raise ValueError("Inventory case output changed")
        columns = ["series_id", "pattern", "origin_sample_all_zero", "forecast_mae", *SUMMARY]
        frame = pq.read_table(ROOT / item["path"], columns=columns).to_pandas()
        sums = frame.groupby("pattern")[SUMMARY].sum().rename(columns=RENAME)
        sums["SeriesEpisodes"] = frame.groupby("pattern").size()
        sums = sums.reset_index().rename(columns={"pattern": "PatternKey"})
        sums.insert(0, "CaseId", status["case_id"])
        sums.insert(1, "DatasetKey", dataset)
        sums.insert(2, "OriginKey", origin_key(dataset, fold))
        sums.insert(3, "ScenarioKey", scenario)
        sums.insert(4, "PolicyKey", policy)
        grouped.append(sums)
        if scenario == "base":
            out = frame[SUMMARY].rename(columns=RENAME)
            out.insert(0, "SeriesKey", [series_key(dataset, s) for s in frame.series_id])
            out.insert(1, "DatasetKey", dataset)
            out.insert(2, "OriginKey", origin_key(dataset, fold))
            out.insert(3, "PolicyKey", policy)
            out.insert(4, "PatternKey", frame.pattern.to_numpy())
            out["ForecastMAE"] = frame.forecast_mae.to_numpy()
            out["OriginSampleAllZero"] = (
                yes_no(frame.origin_sample_all_zero) if dataset == "m5" else "Not applicable"
            )
            series.append(out)
    return {
        "FactInventoryScenarioResults": pd.concat(grouped, ignore_index=True),
        "FactInventorySeriesBase": pd.concat(series, ignore_index=True),
    }


# ------------------------------------------------------------------------------------- governance
def governance_tables(config, selection):
    board = read_json(ROOT / "artifacts/experiments/phase4/trial_leaderboard.json")
    trials = pd.DataFrame(
        [
            {
                "TrialId": t["trial_id"],
                "DatasetKey": t["dataset"],
                "TrialKind": t["kind"],
                "Algorithm": t["model"],
                "ValidationMacroMAE": t["primary_score"],
                "ValidationMacroMASE": t["macro_mase"],
                "ValidationMacroRMSSE": t["macro_rmsse"],
                "ValidationPooledRMSE": t["pooled_rmse"],
                "ValidationPooledWAPEPercent": t["pooled_wape_percent"],
                "ValidationBiasUnits": t["bias_units"],
                "Observations": t["observations"],
                "FallbackObservations": t["fallback_observations"],
                "IsSelected": "Yes"
                if t["trial_id"] == selection["datasets"][t["dataset"]]["selected_trial_id"]
                else "No",
            }
            for t in board
        ]
    )
    final = read_json(ROOT / "artifacts/experiments/phase4/final_evaluation.json")
    reported = []
    for result in final["results"]:
        path = ROOT / "artifacts/experiments/phase4" / result["metrics"]["path"]
        if sha256(path) != result["metrics"]["sha256"]:
            raise ValueError("Saved final metrics changed")
        metrics = read_json(path)["all"]
        reported.append(
            {
                "DatasetKey": result["dataset"],
                "TrialId": result["trial_id"],
                "Algorithm": result["model"],
                "Role": result["role"],
                "EvidenceType": "Saved Phase 4 one-time final assessment (reported, not recomputed)",
                "MacroMAE": metrics["macro"]["mae"],
                "MacroMASE": metrics["macro"].get("mase"),
                "MacroRMSSE": metrics["macro"].get("rmsse"),
                "PooledRMSE": metrics.get("pooled", {}).get("rmse"),
                "PooledWAPEPercent": metrics.get("pooled", {}).get("wape_percent"),
                "Series": metrics["coverage"]["series"],
                "Observations": metrics["coverage"]["observations"],
            }
        )
    checks = []
    receipts = [
        ("reports/inventory/post_audit_verification.json", "Post-audit verification record"),
        ("reports/inventory/phase5_summary.json", "Phase 5 independent simulation audit"),
        ("reports/inventory/metric_validation.json", "Phase 5 persisted metric reconciliation"),
        (
            "reports/inventory/protected_evidence_verification.json",
            "Phase 4 protected evidence (pre-audit)",
        ),
        ("reports/inventory/phase5d_gate.json", "Phase 5D completion gate"),
        (
            "reports/preservation/PHASE5_LOCAL_BACKUP_VERIFICATION.json",
            "Phase 5 same-device backup copy",
        ),
    ]
    for path, label in receipts:
        record = read_json(ROOT / path)
        checks.append(
            {
                "CheckId": f"R{len(checks) + 1:02d}",
                "Check": label,
                "Status": record.get("status", "recorded"),
                "EvidencePath": path,
                "EvidenceSha256": sha256(ROOT / path),
            }
        )
    post = read_json(ROOT / "reports/inventory/post_audit_verification.json")
    for key, label in (
        ("phase4_protected_evidence_verifier", "Phase 4 protected evidence verifier (post-audit)"),
        ("phase5_backup_verifier", "Phase 5 backup verifier (post-audit)"),
    ):
        checks.append(
            {
                "CheckId": f"R{len(checks) + 1:02d}",
                "Check": label,
                "Status": post[key]["status"],
                "EvidencePath": "reports/inventory/post_audit_verification.json",
                "EvidenceSha256": sha256(ROOT / "reports/inventory/post_audit_verification.json"),
            }
        )
    findings = []
    text = (ROOT / "docs/PHASE5_AUDIT_RESPONSE.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        match = re.match(r"\| (F-\d\d) \| (\w+) \| (.+?) \| (.+?) \| (.+?) \|$", line)
        if match:
            findings.append(
                dict(
                    zip(
                        ("FindingId", "Severity", "Finding", "Disposition", "Status"),
                        (g.replace("**", "") for g in match.groups()),
                        strict=True,
                    )
                )
            )
    if len(findings) != 12:
        raise ValueError("Expected the 12 audit findings in the audit response")
    limitations = pd.DataFrame(
        [
            {"LimitationId": x["id"], "Limitation": x["text"], "SourceDocument": x["source"]}
            for x in config["limitations"]
        ]
    )
    return {
        "FactModelSelectionTrials": trials,
        "FactFinalHoldoutReported": pd.DataFrame(reported),
        "FactScientificValidation": pd.DataFrame(checks),
        "DimAuditFinding": pd.DataFrame(findings),
        "DimLimitation": limitations,
    }


GRAIN = {
    "DimDataset": ("One row per dataset", ["DatasetKey"]),
    "DimValidationOrigin": ("One row per dataset validation origin", ["OriginKey"]),
    "DimForecastModel": ("One row per dataset and forecast model role", ["ModelKey"]),
    "DimInventoryPolicy": ("One row per inventory policy", ["PolicyKey"]),
    "DimScenario": ("One row per frozen hypothetical scenario", ["ScenarioKey"]),
    "DimDemandPattern": ("One row per training-prefix demand pattern", ["PatternKey"]),
    "DimDate": ("One row per calendar day 2016-2017", ["Date"]),
    "DimSeries": ("One row per dataset series", ["SeriesKey"]),
    "FactForecastSeriesOrigin": (
        "Series x validation origin x model role (28 observations each)",
        ["SeriesKey", "OriginKey", "ModelKey"],
    ),
    "FactForecastDaily": (
        "Validation origin x model role x demand pattern x target date",
        ["OriginKey", "ModelKey", "PatternKey", "Date"],
    ),
    "FactForecastSeriesDaily": (
        "Detail series x origin x model role x target date",
        ["SeriesKey", "OriginKey", "ModelKey", "Date"],
    ),
    "FactInventoryScenarioResults": (
        "Inventory case (origin x scenario x policy) x demand pattern",
        ["OriginKey", "ScenarioKey", "PolicyKey", "PatternKey"],
    ),
    "FactInventorySeriesBase": (
        "Series x origin x policy, base scenario only",
        ["SeriesKey", "OriginKey", "PolicyKey"],
    ),
    "FactModelSelectionTrials": ("One row per Phase 4 trial", ["TrialId"]),
    "FactFinalHoldoutReported": ("One row per saved final assessment", ["TrialId"]),
    "FactScientificValidation": ("One row per verification receipt", ["CheckId"]),
    "DimAuditFinding": ("One row per independent audit finding", ["FindingId"]),
    "DimLimitation": ("One row per declared scientific limitation", ["LimitationId"]),
}


def build():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    plan = frozen_plan()  # verifies the frozen plan and design-file hashes
    selection = read_json(ROOT / "artifacts/experiments/phase4/frozen_selection.json")
    tables = dimensions(config, plan, selection)
    tables.update(forecast_tables(config, plan))
    tables.update(inventory_tables())
    tables.update(governance_tables(config, selection))
    output = ROOT / config["output_directory"]
    output.mkdir(parents=True, exist_ok=True)
    entries = {}
    for name, frame in tables.items():
        keys = GRAIN[name][1]
        if frame.duplicated(keys).any():
            raise ValueError(f"Duplicate business key in {name}")
        path = output / f"{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
        entries[name] = {
            "file": path.relative_to(ROOT).as_posix(),
            "rows": len(frame),
            "columns": list(frame.columns),
            "grain": GRAIN[name][0],
            "keys": keys,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
    sources = {
        name: {"path": rel, "sha256": sha256(ROOT / rel)}
        for name, rel in {
            "frozen_plan": "artifacts/inventory/phase5/plan.json",
            "execution_contract": "artifacts/inventory/phase5/execution.json",
            "phase5_audit_summary": "reports/inventory/phase5_summary.json",
            "trial_leaderboard": "artifacts/experiments/phase4/trial_leaderboard.json",
            "final_evaluation": "artifacts/experiments/phase4/final_evaluation.json",
            "frozen_selection": "artifacts/experiments/phase4/frozen_selection.json",
            "audit_response": "docs/PHASE5_AUDIT_RESPONSE.md",
            "reporting_config": "configs/powerbi.yaml",
        }.items()
    }
    manifest = {
        "schema_version": 1,
        "plan_sha256": plan["sha256"],
        "selection_fingerprint": selection["manifest_sha256"],
        "final_holdout_targets_read": False,
        "tables": entries,
        "sources": sources,
    }
    target = ROOT / config["manifest"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, entry in entries.items():
        print(f"{name:32s} {entry['rows']:>10,} rows  {entry['bytes'] / 1e6:8.2f} MB")


if __name__ == "__main__":
    build()
