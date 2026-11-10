"""Deterministic Phase 6 dashboard QA runner.

Rules live in configs/powerbi_qa.yaml. Each produces: rule id, layer, description, expected,
actual, tolerance, severity, status (PASS / WARNING / FAIL / ERROR) and an evidence reference.
References come from saved scientific evidence, not from the export code. Any CRITICAL FAIL or ERROR
makes the overall status FAIL. Usage:  .venv\\Scripts\\python.exe -m intelligent_demand.bi.qa
"""

import hashlib
import json
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
RULES = ROOT / "configs/powerbi_qa.yaml"
MANIFEST = ROOT / "reports/powerbi/data_manifest.json"
CHECKS = {}


def check(name):
    def register(function):
        CHECKS[name] = function
        return function

    return register


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Context:
    """Lazy access to reporting tables and evidence; tables are read once."""

    def __init__(self):
        self.manifest = read_json(MANIFEST)
        self.cache = {}
        self.plan = read_json(ROOT / "artifacts/inventory/phase5/plan.json")

    def table(self, name):
        if name not in self.cache:
            self.cache[name] = pd.read_csv(
                ROOT / self.manifest["tables"][name]["file"], keep_default_na=True, low_memory=False
            )
        return self.cache[name]

    def runs(self):
        """(dataset, fold, role, registry metrics['all']) for the 24 Phase 5 forecast sources."""
        for cohort in self.plan["cohorts"]:
            for role, source in cohort["sources"].items():
                directory = (ROOT / source["specification"]["path"]).parent
                status = read_json(directory / "status.json")
                path = directory / status["outputs"]["metrics"]["path"].replace("\\", "/")
                if sha256(path) != status["outputs"]["metrics"]["sha256"]:
                    raise ValueError("Registry metrics changed")
                yield (
                    cohort["dataset"],
                    cohort["fold"]["number"],
                    role,
                    read_json(path)["all"],
                    path,
                )


def close(actual, expected, tolerance):
    return np.allclose(
        np.asarray(actual, float),
        np.asarray(expected, float),
        rtol=tolerance.get("rtol", 0),
        atol=tolerance.get("atol", 0),
        equal_nan=True,
    )


# ---------------------------------------------------------------- Layer A
@check("frozen_plan_hash")
def frozen_plan_hash(ctx, rule):
    from intelligent_demand.inventory.plan import plan

    value = plan()["sha256"]
    return value == rule["expected"], value, "artifacts/inventory/phase5/plan.json"


@check("selection_fingerprint")
def selection_fingerprint(ctx, rule):
    frozen = read_json(ROOT / "artifacts/experiments/phase4/frozen_selection.json")
    body = {k: v for k, v in frozen.items() if k != "manifest_sha256"}
    value = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return (
        value == rule["expected"] == frozen["manifest_sha256"],
        value,
        "artifacts/experiments/phase4/frozen_selection.json",
    )


@check("holdout_ledger")
def holdout_ledger(ctx, rule):
    path = ROOT / "artifacts/experiments/phase4/holdout_access.jsonl"
    events = len(path.read_text(encoding="utf-8").splitlines())
    value = sha256(path)
    return (
        value == rule["expected"] and events == 12,
        f"{value} ({events} events)",
        path.relative_to(ROOT).as_posix(),
    )


@check("inventory_cases_complete")
def inventory_cases_complete(ctx, rule):
    count = 0
    for path in (ROOT / "artifacts/inventory/phase5/runs").glob("*/status.json"):
        status = read_json(path)
        item = status["files"]["series"]
        count += status["status"] == "completed" and sha256(ROOT / item["path"]) == item["sha256"]
    return count == rule["expected"], count, "artifacts/inventory/phase5/runs/*/status.json"


@check("manifest_hashes")
def manifest_hashes(ctx, rule):
    bad = [
        name
        for name, entry in ctx.manifest["tables"].items()
        if sha256(ROOT / entry["file"]) != entry["sha256"] or len(ctx.table(name)) != entry["rows"]
    ]
    return (
        not bad,
        bad or f"{len(ctx.manifest['tables'])} tables match",
        MANIFEST.relative_to(ROOT).as_posix(),
    )


@check("validation_dates_only")
def validation_dates_only(ctx, rule):
    splits = read_json(ROOT / "reports/eda/proposed_splits.json")
    origins = ctx.table("DimValidationOrigin")
    problems = 0
    for name in ("FactForecastDaily", "FactForecastSeriesDaily"):
        frame = ctx.table(name).merge(
            origins, on=["OriginKey", "DatasetKey"], validate="many_to_one"
        )
        date = pd.to_datetime(frame.Date)
        inside = (date >= pd.to_datetime(frame.ValidationStart)) & (
            date <= pd.to_datetime(frame.ValidationEnd)
        )
        test_start = frame.DatasetKey.map({k: v["test_start"] for k, v in splits.items()})
        problems += int((~inside).sum() + (date >= pd.to_datetime(test_start)).sum())
    return (
        problems == 0,
        f"{problems} rows outside approved validation windows",
        "reports/eda/proposed_splits.json",
    )


@check("no_fallback_forecasts")
def no_fallback_forecasts(ctx, rule):
    total = sum(
        read_json(p)["source_fallback_observations"]
        for p in (ROOT / "artifacts/inventory/phase5/runs").glob("*/status.json")
    )
    return total == 0, total, "artifacts/inventory/phase5/runs/*/status.json"


# ---------------------------------------------------------------- Layer B
@check("key_uniqueness")
def key_uniqueness(ctx, rule):
    bad = [
        name
        for name, entry in ctx.manifest["tables"].items()
        if ctx.table(name).duplicated(entry["keys"]).any()
    ]
    return not bad, bad or "all keys unique", MANIFEST.relative_to(ROOT).as_posix()


RELATIONSHIPS = [
    ("FactForecastSeriesOrigin", "SeriesKey", "DimSeries"),
    ("FactForecastSeriesOrigin", "OriginKey", "DimValidationOrigin"),
    ("FactForecastSeriesOrigin", "ModelKey", "DimForecastModel"),
    ("FactForecastSeriesOrigin", "DatasetKey", "DimDataset"),
    ("FactForecastSeriesOrigin", "PatternKey", "DimDemandPattern"),
    ("FactForecastDaily", "OriginKey", "DimValidationOrigin"),
    ("FactForecastDaily", "ModelKey", "DimForecastModel"),
    ("FactForecastDaily", "DatasetKey", "DimDataset"),
    ("FactForecastDaily", "PatternKey", "DimDemandPattern"),
    ("FactForecastDaily", "Date", "DimDate"),
    ("FactForecastSeriesDaily", "SeriesKey", "DimSeries"),
    ("FactForecastSeriesDaily", "OriginKey", "DimValidationOrigin"),
    ("FactForecastSeriesDaily", "ModelKey", "DimForecastModel"),
    ("FactForecastSeriesDaily", "DatasetKey", "DimDataset"),
    ("FactForecastSeriesDaily", "PatternKey", "DimDemandPattern"),
    ("FactForecastSeriesDaily", "Date", "DimDate"),
    ("FactInventoryScenarioResults", "OriginKey", "DimValidationOrigin"),
    ("FactInventoryScenarioResults", "ScenarioKey", "DimScenario"),
    ("FactInventoryScenarioResults", "PolicyKey", "DimInventoryPolicy"),
    ("FactInventoryScenarioResults", "DatasetKey", "DimDataset"),
    ("FactInventoryScenarioResults", "PatternKey", "DimDemandPattern"),
    ("FactInventorySeriesBase", "SeriesKey", "DimSeries"),
    ("FactInventorySeriesBase", "OriginKey", "DimValidationOrigin"),
    ("FactInventorySeriesBase", "PolicyKey", "DimInventoryPolicy"),
    ("FactInventorySeriesBase", "DatasetKey", "DimDataset"),
    ("FactInventorySeriesBase", "PatternKey", "DimDemandPattern"),
    ("FactModelSelectionTrials", "DatasetKey", "DimDataset"),
    ("FactFinalHoldoutReported", "DatasetKey", "DimDataset"),
]


@check("referential_integrity")
def referential_integrity(ctx, rule):
    bad = []
    for fact, column, dim in RELATIONSHIPS:
        key = ctx.manifest["tables"][dim]["keys"][0]
        missing = set(ctx.table(fact)[column].astype(str)) - set(ctx.table(dim)[key].astype(str))
        if missing:
            bad.append(f"{fact}.{column}: {len(missing)} orphan keys")
    return (
        not bad,
        bad or f"{len(RELATIONSHIPS)} relationships, no orphan keys",
        "src/intelligent_demand/bi/qa.py",
    )


@check("forecast_population")
def forecast_population(ctx, rule):
    fact = ctx.table("FactForecastSeriesOrigin")
    expected = int(ctx.table("DimDataset").SeriesCount.sum()) * 4 * 3
    complete = (fact.Observations == 28).all()
    return (
        len(fact) == expected and complete,
        f"{len(fact)} rows (expected {expected})",
        "DimDataset.SeriesCount",
    )


def run_metrics(ctx):
    fact = ctx.table("FactForecastSeriesOrigin")
    grouped = fact.groupby(["OriginKey", "ModelKey"])
    return fact, grouped


@check("registry_metric")
def registry_metric(ctx, rule):
    fact = ctx.table("FactForecastSeriesOrigin")
    mine, reference = [], []
    for dataset, fold, role, saved, _ in ctx.runs():
        block = fact[
            (fact.OriginKey == f"{dataset}|{fold}") & (fact.ModelKey == f"{dataset}|{role}")
        ]
        n = block.Observations.sum()
        metric = rule["metric"]
        if metric == "pooled_mae":
            value, ref = block.SumAbsError.sum() / n, saved["pooled"]["mae"]
        elif metric == "pooled_rmse":
            value, ref = np.sqrt(block.SumSquaredError.sum() / n), saved["pooled"]["rmse"]
        elif metric == "pooled_wape_percent":
            value, ref = (
                100 * block.SumAbsError.sum() / block.SumActual.sum(),
                saved["pooled"]["wape_percent"],
            )
        elif metric == "pooled_bias_units":
            value, ref = block.SumError.sum() / n, saved["pooled"]["bias_units"]
        elif metric == "macro_mase":
            value = ((block.SumAbsError / block.Observations) / block.ScaleAbs).dropna().mean()
            ref = saved["macro"]["mase"]
        elif metric == "macro_rmsse":
            value = (
                np.sqrt((block.SumSquaredError / block.Observations) / block.ScaleSquared)
                .dropna()
                .mean()
            )
            ref = saved["macro"]["rmsse"]
        mine.append(value)
        reference.append(ref)
    ok = len(mine) == 24 and close(mine, reference, rule["tolerance"])
    worst = float(np.nanmax(np.abs(np.asarray(mine) - np.asarray(reference)) / np.abs(reference)))
    return (
        ok,
        f"24 runs; max relative difference {worst:.2e}",
        "registry metrics.json of each validation run",
    )


@check("leaderboard_selected")
def leaderboard_selected(ctx, rule):
    fact = ctx.table("FactForecastSeriesOrigin")
    board = {
        t["trial_id"]: t
        for t in read_json(ROOT / "artifacts/experiments/phase4/trial_leaderboard.json")
    }
    selection = read_json(ROOT / "artifacts/experiments/phase4/frozen_selection.json")
    mine, reference = [], []
    for dataset in ("store_item", "m5"):
        block = fact[fact.ModelKey == f"{dataset}|selected_ml"]
        per_origin = block.groupby("OriginKey").apply(
            lambda b: b.SumAbsError.sum() / b.Observations.sum()
        )
        mine.append(per_origin.mean())
        reference.append(
            board[selection["datasets"][dataset]["selected_trial_id"]]["primary_score"]
        )
    return (
        close(mine, reference, rule["tolerance"]),
        f"{mine} vs {reference}",
        "artifacts/experiments/phase4/trial_leaderboard.json",
    )


@check("daily_vs_series")
def daily_vs_series(ctx, rule):
    a = (
        ctx.table("FactForecastDaily")
        .groupby(["OriginKey", "ModelKey"])[
            ["SumActual", "SumForecast", "SumAbsError", "SumSquaredError", "SumError"]
        ]
        .sum()
    )
    b = ctx.table("FactForecastSeriesOrigin").groupby(["OriginKey", "ModelKey"])[a.columns].sum()
    return (
        close(a.sort_index(), b.sort_index(), rule["tolerance"]),
        f"{len(a)} origin-model groups compared",
        "FactForecastDaily vs FactForecastSeriesOrigin",
    )


@check("inventory_vs_audit")
def inventory_vs_audit(ctx, rule):
    summary = pd.DataFrame(read_json(ROOT / "reports/inventory/phase5_summary.json")["summaries"])
    summary["OriginKey"] = summary.dataset + "|" + summary.fold.astype(str)
    fact = (
        ctx.table("FactInventoryScenarioResults")
        .groupby(["OriginKey", "ScenarioKey", "PolicyKey"])
        .sum(numeric_only=True)
        .reset_index()
    )
    merged = fact.merge(
        summary,
        left_on=["OriginKey", "ScenarioKey", "PolicyKey"],
        right_on=["OriginKey", "scenario", "policy"],
        validate="one_to_one",
    )
    pairs = [
        ("TotalCost", "total_cost"),
        ("HoldingCost", "holding_cost"),
        ("ShortageCost", "shortage_cost"),
        ("OrderingCost", "ordering_cost"),
        ("TerminalCost", "terminal_cost"),
        ("DemandUnits", "demand_units"),
        ("FulfilledUnits", "fulfilled_units"),
        ("UnmetUnits", "unmet_units"),
        ("StockoutDays", "stockout_days"),
        ("Orders", "orders"),
        ("SeriesEpisodes", "series"),
    ]
    ok = len(merged) == 544 and all(
        close(merged[a], merged[b], rule["tolerance"]) for a, b in pairs
    )
    return (
        ok,
        f"{len(merged)} cases x {len(pairs)} measures",
        "reports/inventory/phase5_summary.json",
    )


@check("inventory_series_vs_case")
def inventory_series_vs_case(ctx, rule):
    columns = [
        "TotalCost",
        "HoldingCost",
        "ShortageCost",
        "OrderingCost",
        "DemandUnits",
        "FulfilledUnits",
        "StockoutDays",
        "Orders",
        "AverageOnHand",
    ]
    a = (
        ctx.table("FactInventorySeriesBase")
        .groupby(["OriginKey", "PolicyKey", "PatternKey"])[columns]
        .sum()
    )
    case = ctx.table("FactInventoryScenarioResults")
    b = (
        case[case.ScenarioKey == "base"]
        .groupby(["OriginKey", "PolicyKey", "PatternKey"])[columns]
        .sum()
    )
    return (
        close(a.sort_index(), b.sort_index(), rule["tolerance"]),
        f"{len(a)} groups",
        "base scenario",
    )


@check("headline_reconciliation")
def headline_reconciliation(ctx, rule):
    reference = read_json(ROOT / "reports/inventory/post_audit_reconciliation.json")["base_pooled"]
    case = ctx.table("FactInventoryScenarioResults")
    base = (
        case[case.ScenarioKey == "base"].groupby(["DatasetKey", "PolicyKey"]).sum(numeric_only=True)
    )
    mine, ref = [], []
    for (dataset, policy), row in base.iterrows():
        mine += [row.TotalCost / row.SeriesEpisodes, row.FulfilledUnits / row.DemandUnits]
        ref += [
            reference[dataset][policy]["mean_cost"],
            reference[dataset][policy]["pooled_fill_rate"],
        ]
    return (
        close(mine, ref, rule["tolerance"]),
        f"{len(mine) // 2} dataset-policy pairs",
        "reports/inventory/post_audit_reconciliation.json",
    )


@check("no_missing_additive")
def no_missing_additive(ctx, rule):
    problems = []
    allowed = {
        "ScaleAbs",
        "ScaleSquared",
        "ForecastMAE",
        "DepartmentId",
        "CategoryId",
        "StateId",
        "ForecastRoleKey",
        "MacroMASE",
        "MacroRMSSE",
        "PooledRMSE",
        "PooledWAPEPercent",
    }
    for name in ctx.manifest["tables"]:
        frame = ctx.table(name)
        for column in frame.columns:
            if column not in allowed and frame[column].isna().any():
                problems.append(f"{name}.{column}")
    fact = ctx.table("FactForecastSeriesOrigin")
    undefined = int(fact.ScaleAbs.isna().sum())
    return (
        not problems,
        problems or f"no unexpected gaps; {undefined} undefined MASE scales kept empty",
        "reporting CSVs",
    )


@check("scenario_completeness")
def scenario_completeness(ctx, rule):
    fact = ctx.table("FactInventoryScenarioResults")
    cases = fact[["OriginKey", "ScenarioKey", "PolicyKey"]].drop_duplicates()
    return (
        len(cases) == 17 * 4 * 8 and fact.CaseId.nunique() == 544,
        f"{len(cases)} cases",
        "FactInventoryScenarioResults",
    )


# ---------------------------------------------------------------- live engine helpers (Layers C, D)
def dax(query):
    """Execute a DAX query against the connected Power BI Desktop model through pbi-cli."""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".dax", delete=False, encoding="utf-8") as handle:
        handle.write(query)
    try:
        result = subprocess.run(
            ["pbi", "--json", "dax", "execute", "--file", handle.name, "--max-rows", "100000"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
        )
    finally:
        Path(handle.name).unlink(missing_ok=True)
    if result.returncode != 0 or not result.stdout.strip().startswith("{"):
        raise RuntimeError(f"DAX query failed: {(result.stderr or result.stdout)[:300]}")
    payload = json.loads(result.stdout)
    frame = pd.DataFrame(payload["rows"], columns=payload["columns"])
    frame.columns = [c.split("[")[-1].rstrip("]") for c in frame.columns]
    return frame


def numeric(frame, columns):
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


@check("model_row_counts")
def model_row_counts(ctx, rule):
    names = list(ctx.manifest["tables"])
    query = "EVALUATE ROW ( " + ", ".join(f'"{n}", COUNTROWS ( {n} )' for n in names) + " )"
    row = dax(query).iloc[0]
    bad = [n for n in names if int(row[n] or 0) != ctx.manifest["tables"][n]["rows"]]
    return (
        not bad,
        bad or f"{len(names)} tables match manifest",
        "DAX COUNTROWS vs data_manifest.json",
    )


@check("model_relationships")
def model_relationships(ctx, rule):
    frame = dax(
        'EVALUATE SELECTCOLUMNS ( INFO.VIEW.RELATIONSHIPS (), "From", [FromTable], "FromColumn", '
        '[FromColumn], "To", [ToTable], "FromCard", [FromCardinality], "ToCard", [ToCardinality], '
        '"Cross", [CrossFilteringBehavior], "Active", [IsActive] )'
    )
    actual = {(r.From, r.FromColumn, r.To) for r in frame.itertuples()}
    expected = {(f, c, d) for f, c, d in RELATIONSHIPS}
    shape = (
        frame.FromCard.eq("Many").all()
        and frame.ToCard.eq("One").all()
        and frame.Cross.str.contains("One", case=False).all()
        and frame.Active.astype(str).str.lower().eq("true").all()
    )
    missing, extra = expected - actual, actual - expected
    ok = not missing and not extra and shape and len(frame) == 28
    return (
        ok,
        f"{len(frame)} relationships; missing {sorted(missing)}; extra {sorted(extra)}; "
        f"cardinality/direction ok={shape}",
        "INFO.VIEW.RELATIONSHIPS()",
    )


@check("model_measures_valid")
def model_measures_valid(ctx, rule):
    frame = dax(
        'EVALUATE SELECTCOLUMNS ( INFO.MEASURES (), "Name", [Name], "State", [State], '
        '"Err", [ErrorMessage] )'
    )
    spec = yaml.safe_load((ROOT / "configs/powerbi_model.yaml").read_text(encoding="utf-8"))
    declared = {m["name"] for m in spec["measures"]}
    bad = frame[(frame.State.astype(str) != "1") | frame.Err.notna()].Name.tolist()
    ok = set(frame.Name) == declared and not bad and len(frame) == rule["expected"]
    return (
        ok,
        f"{len(frame)} measures; errors {bad}; missing {sorted(declared - set(frame.Name))}",
        "INFO.MEASURES()",
    )


@check("model_hidden_keys")
def model_hidden_keys(ctx, rule):
    frame = dax(
        'EVALUATE SELECTCOLUMNS ( FILTER ( INFO.VIEW.COLUMNS (), [Type] <> "RowNumber" ), '
        '"Table", [Table], "Column", [Name], "Hidden", [IsHidden] )'
    )
    hidden = frame.Hidden.astype(str).str.lower() == "true"
    keys = frame.Column.str.endswith("Key")
    facts = frame.Table.str.startswith(("FactForecast", "FactInventory")) | frame.Table.eq(
        "_Measures"
    )
    bad = frame[(keys | facts) & ~hidden]
    return (
        bad.empty,
        f"{len(bad)} visible key/fact columns: {bad.Column.tolist()[:8]}",
        "INFO.VIEW.COLUMNS()",
    )


@check("model_date_table")
def model_date_table(ctx, rule):
    tables = dax(
        'EVALUATE SELECTCOLUMNS ( FILTER ( INFO.VIEW.TABLES (), [Name] = "DimDate" ), '
        '"Category", [DataCategory] )'
    )
    unique = dax(
        'EVALUATE ROW ( "Rows", COUNTROWS ( DimDate ), "Distinct", DISTINCTCOUNT ( DimDate[Date] ) )'
    )
    category = str(tables.Category.iloc[0]) if len(tables) else "missing"
    ok = category.lower() == "time" and unique.Rows.iloc[0] == unique.Distinct.iloc[0]
    return (
        ok,
        f"category {category}; rows {unique.Rows.iloc[0]} distinct {unique.Distinct.iloc[0]}",
        "INFO.VIEW.TABLES()",
    )


FORECAST_QUERY = """EVALUATE
SUMMARIZECOLUMNS (
    DimValidationOrigin[OriginKey], DimForecastModel[ModelKey],
    "MAE", [MAE], "RMSE", [RMSE], "WAPE", [WAPE], "Bias", [Bias],
    "MASE", [Macro MASE], "RMSSE", [Macro RMSSE]
)"""


@check("dax_forecast_runs")
def dax_forecast_runs(ctx, rule):
    frame = numeric(dax(FORECAST_QUERY), ["MAE", "RMSE", "WAPE", "Bias", "MASE", "RMSSE"])
    frame = frame.set_index(["OriginKey", "ModelKey"])
    mine, reference = [], []
    for dataset, fold, role, saved, _ in ctx.runs():
        row = frame.loc[(f"{dataset}|{fold}", f"{dataset}|{role}")]
        mine += [row.MAE, row.RMSE, row.WAPE, row.Bias, row.MASE, row.RMSSE]
        reference += [
            saved["pooled"]["mae"],
            saved["pooled"]["rmse"],
            saved["pooled"]["wape_percent"] / 100,
            saved["pooled"]["bias_units"],
            saved["macro"]["mase"],
            saved["macro"]["rmsse"],
        ]
    worst = float(
        np.nanmax(np.abs(np.array(mine) - np.array(reference)) / np.abs(np.array(reference)))
    )
    return (
        len(frame) == 24 and close(mine, reference, rule["tolerance"]),
        f"{len(frame)} origin-model rows x 6 metrics; max relative difference {worst:.2e}",
        "registry metrics.json of each validation run",
    )


@check("dax_leaderboard")
def dax_leaderboard(ctx, rule):
    frame = numeric(
        dax("""EVALUATE
SUMMARIZECOLUMNS (
    DimDataset[DatasetKey], TREATAS ( { "selected_ml" }, DimForecastModel[ModelRoleKey] ),
    "MAE", [MAE], "RMSE", [RMSE], "WAPE", [WAPE], "Bias", [Bias], "MASE", [Macro MASE], "RMSSE", [Macro RMSSE]
)"""),
        ["MAE", "RMSE", "WAPE", "Bias", "MASE", "RMSSE"],
    ).set_index("DatasetKey")
    board = {
        t["trial_id"]: t
        for t in read_json(ROOT / "artifacts/experiments/phase4/trial_leaderboard.json")
    }
    selection = read_json(ROOT / "artifacts/experiments/phase4/frozen_selection.json")
    mine, reference = [], []
    for dataset in ("store_item", "m5"):
        t = board[selection["datasets"][dataset]["selected_trial_id"]]
        row = frame.loc[dataset]
        mine += [row.MAE, row.RMSE, row.WAPE, row.Bias, row.MASE, row.RMSSE]
        reference += [
            t["primary_score"],
            t["pooled_rmse"],
            t["pooled_wape_percent"] / 100,
            t["bias_units"],
            t["macro_mase"],
            t["macro_rmsse"],
        ]
    return (
        close(mine, reference, rule["tolerance"]),
        f"2 datasets x 6 metrics; DAX MAE {list(frame.MAE)}",
        "artifacts/experiments/phase4/trial_leaderboard.json",
    )


@check("dax_inventory_cases")
def dax_inventory_cases(ctx, rule):
    frame = numeric(
        dax("""EVALUATE
SUMMARIZECOLUMNS (
    DimValidationOrigin[OriginKey], DimScenario[ScenarioKey], DimInventoryPolicy[PolicyKey],
    "Mean", [Mean Cost per Episode (NCU)], "Fill", [Fill Rate], "Hold", [Holding Cost per Episode (NCU)],
    "Short", [Unmet Demand Penalty per Episode (NCU)], "Ord", [Ordering Cost per Episode (NCU)],
    "Stockout", [Stockout Days per Episode], "OnHand", [Average On-Hand Units]
)"""),
        ["Mean", "Fill", "Hold", "Short", "Ord", "Stockout", "OnHand"],
    )
    summary = pd.DataFrame(read_json(ROOT / "reports/inventory/phase5_summary.json")["summaries"])
    summary["OriginKey"] = summary.dataset + "|" + summary.fold.astype(str)
    merged = frame.merge(
        summary,
        left_on=["OriginKey", "ScenarioKey", "PolicyKey"],
        right_on=["OriginKey", "scenario", "policy"],
        validate="one_to_one",
    )
    pairs = [
        ("Mean", merged.mean_cost),
        ("Fill", merged.pooled_fill_rate),
        ("Hold", merged.holding_cost / merged.series),
        ("Short", merged.shortage_cost / merged.series),
        ("Ord", merged.ordering_cost / merged.series),
        ("Stockout", merged.stockout_days / merged.series),
        ("OnHand", merged.average_on_hand),
    ]
    ok = len(merged) == 544 and all(close(merged[a], b, rule["tolerance"]) for a, b in pairs)
    return (
        ok,
        f"{len(merged)} cases x {len(pairs)} measures",
        "reports/inventory/phase5_summary.json",
    )


@check("dax_headline")
def dax_headline(ctx, rule):
    frame = numeric(
        dax("""EVALUATE
SUMMARIZECOLUMNS (
    DimDataset[DatasetKey], DimInventoryPolicy[PolicyKey], TREATAS ( { "base" }, DimScenario[ScenarioKey] ),
    "Mean", [Mean Cost per Episode (NCU)], "Fill", [Fill Rate], "PerUnit", [Cost per Demanded Unit (NCU)],
    "OnHand", [Average On-Hand Units], "Stockout", [Stockout Days per Episode]
)"""),
        ["Mean", "Fill", "PerUnit", "OnHand", "Stockout"],
    )
    reference = read_json(ROOT / "reports/inventory/post_audit_reconciliation.json")["base_pooled"]
    mine, ref = [], []
    for row in frame.itertuples():
        r = reference[row.DatasetKey][row.PolicyKey]
        mine += [row.Mean, row.Fill, row.PerUnit, row.OnHand, row.Stockout]
        ref += [
            r["mean_cost"],
            r["pooled_fill_rate"],
            r["cost_per_demand_unit"],
            r["average_on_hand"],
            r["stockout_days_per_episode"],
        ]
    return (
        len(frame) == 8 and close(mine, ref, rule["tolerance"]),
        f"{len(frame)} dataset-policy rows x 5",
        "reports/inventory/post_audit_reconciliation.json",
    )


@check("dax_ml_differences")
def dax_ml_differences(ctx, rule):
    base = 'TREATAS ( { "base" }, DimScenario[ScenarioKey] )'
    pooled = numeric(
        dax(f"""EVALUATE
SUMMARIZECOLUMNS ( DimDataset[DatasetKey], {base},
    "DMA", [ML vs MA28 Cost Difference (NCU)], "PMA", [ML vs MA28 Cost Difference %],
    "DSN", [ML vs Seasonal Naive Cost Difference (NCU)], "PSN", [ML vs Seasonal Naive Cost Difference %] )"""),
        ["DMA", "PMA", "DSN", "PSN"],
    ).set_index("DatasetKey")
    origin = numeric(
        dax(f"""EVALUATE
SUMMARIZECOLUMNS ( DimValidationOrigin[DatasetKey], DimValidationOrigin[Fold], {base},
    "DMA", [ML vs MA28 Cost Difference (NCU)], "DSN", [ML vs Seasonal Naive Cost Difference (NCU)] )"""),
        ["Fold", "DMA", "DSN"],
    )
    reference = read_json(ROOT / "reports/inventory/post_audit_reconciliation.json")[
        "ml_comparisons"
    ]
    mine, ref = [], []
    for dataset in ("store_item", "m5"):
        for column, key, pct in (
            ("DMA", "moving_average_28", "PMA"),
            ("DSN", "seasonal_naive", "PSN"),
        ):
            r = reference[dataset][key]
            mine += [pooled.loc[dataset, column], pooled.loc[dataset, pct]]
            ref += [r["base_difference"], r["base_percent"] / 100]
            rows = origin[origin.DatasetKey == dataset].sort_values("Fold")
            mine += list(rows[column])
            ref += r["per_origin_difference"]
    return (
        close(mine, ref, rule["tolerance"]),
        f"{len(mine)} values; Store Item ML-MA28 per origin "
        f"{[round(x, 2) for x in origin[origin.DatasetKey == 'store_item'].sort_values('Fold').DMA]}",
        "reports/inventory/post_audit_reconciliation.json",
    )


@check("dax_robustness_counts")
def dax_robustness_counts(ctx, rule):
    frame = numeric(
        dax("""EVALUATE
SUMMARIZECOLUMNS ( DimDataset[DatasetKey],
    "ScnMA", [Scenarios ML Cheaper than MA28], "ScnSN", [Scenarios ML Cheaper than Seasonal Naive],
    "OrgMA", CALCULATE ( [Origins ML Cheaper than MA28], DimScenario[ScenarioKey] = "base" ) )"""),
        ["ScnMA", "ScnSN", "OrgMA"],
    ).set_index("DatasetKey")
    reference = read_json(ROOT / "reports/inventory/post_audit_reconciliation.json")[
        "ml_comparisons"
    ]
    mine, ref = [], []
    for dataset in ("store_item", "m5"):
        mine += list(frame.loc[dataset, ["ScnMA", "ScnSN", "OrgMA"]])
        ref += [
            reference[dataset]["moving_average_28"]["scenarios_ml_cheaper_pooled"],
            reference[dataset]["seasonal_naive"]["scenarios_ml_cheaper_pooled"],
            reference[dataset]["moving_average_28"]["origins_where_ml_cheaper"],
        ]
    return (
        mine == ref,
        f"DAX {mine} vs reference {ref}",
        "reports/inventory/post_audit_reconciliation.json",
    )


@check("dax_paired_series")
def dax_paired_series(ctx, rule):
    frame = numeric(
        dax("""EVALUATE
SUMMARIZECOLUMNS ( DimValidationOrigin[OriginKey],
    "Lower", [Series-Origins ML Cheaper than MA28], "Higher", [Series-Origins ML Costlier than MA28] )"""),
        ["Lower", "Higher"],
    ).set_index("OriginKey")
    paired = pd.DataFrame(read_json(ROOT / "reports/inventory/phase5_summary.json")["paired"])
    paired = paired[(paired.scenario == "base") & (paired.policy == "selected_ml")]
    mine, ref = [], []
    for row in paired.itertuples():
        key = f"{row.dataset}|{row.fold}"
        mine += [int(frame.loc[key, "Lower"]), int(frame.loc[key, "Higher"])]
        ref += [row.lower_cost_series, row.higher_cost_series]
    return (
        mine == ref and len(ref) == 16,
        f"8 origins; DAX {mine[:4]}... vs {ref[:4]}...",
        "reports/inventory/phase5_summary.json paired",
    )


@check("dax_scope_guards")
def dax_scope_guards(ctx, rule):
    row = dax("""EVALUATE ROW (
    "MAEMixed", [MAE],
    "MAEOneModelBothDatasets", CALCULATE ( [MAE], DimForecastModel[ModelRoleKey] = "selected_ml" ),
    "CostMixedScenario", CALCULATE ( [Mean Cost per Episode (NCU)], DimDataset[DatasetKey] = "m5",
        DimInventoryPolicy[PolicyKey] = "selected_ml" ),
    "CostValid", CALCULATE ( [Mean Cost per Episode (NCU)], DimDataset[DatasetKey] = "m5",
        DimInventoryPolicy[PolicyKey] = "selected_ml", DimScenario[ScenarioKey] = "base" ) )""").iloc[
        0
    ]
    blanks = [
        row[c] is None or (isinstance(row[c], float) and np.isnan(row[c]))
        for c in ("MAEMixed", "MAEOneModelBothDatasets", "CostMixedScenario")
    ]
    valid = row["CostValid"] is not None
    return (
        all(blanks) and valid,
        f"mixed contexts blank={blanks}; valid context value={row['CostValid']}",
        "DAX guard measures",
    )


# ---------------------------------------------------------------- Layer E: report definition
REPORT_DEF = ROOT / "powerbi/IntelligentDemand.Report/definition"
PAGES = [
    "executive_overview",
    "forecasting_performance",
    "inventory_optimisation",
    "scenario_sensitivity",
    "model_explorer_governance",
]


def visual_files():
    return sorted(REPORT_DEF.glob("pages/*/visuals/*/visual.json"))


def field_refs(node, found):
    """Collect (entity, property, kind) from any PBIR field expression in a JSON tree."""
    if isinstance(node, dict):
        for kind in ("Column", "Measure"):
            if kind in node and isinstance(node[kind], dict) and "Property" in node[kind]:
                source = node[kind].get("Expression", {}).get("SourceRef", {})
                if "Entity" in source:
                    found.append((source["Entity"], node[kind]["Property"], kind))
        for value in node.values():
            field_refs(value, found)
    elif isinstance(node, list):
        for value in node:
            field_refs(value, found)
    return found


@check("pbir_validate")
def pbir_validate(ctx, rule):
    import subprocess

    result = subprocess.run(
        ["pbi", "--json", "report", "validate"],
        cwd=ROOT / "powerbi",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(result.stdout)
    return (
        payload["valid"] and not payload["errors"],
        f"valid={payload['valid']} errors={payload['errors']} files={payload['files_checked']}",
        "pbi report validate",
    )


@check("pbir_pages")
def pbir_pages(ctx, rule):
    pages = read_json(REPORT_DEF / "pages/pages.json")
    problems = [] if pages["pageOrder"] == PAGES else [f"order {pages['pageOrder']}"]
    if pages.get("activePageName") != PAGES[0]:
        problems.append(f"active {pages.get('activePageName')}")
    for page in PAGES:
        types = {
            p.parent.name: read_json(p)["visual"]["visualType"]
            for p in REPORT_DEF.glob(f"pages/{page}/visuals/*/visual.json")
        }
        caveat = json.dumps(read_json(REPORT_DEF / f"pages/{page}/visuals/ftr_caveat/visual.json"))
        if types.get("hdr_nav") != "pageNavigator" or "not realised savings" not in caveat:
            problems.append(f"{page}: navigator/caveat missing")
    return (
        not problems,
        problems or "5 pages; navigator and caveat on every page",
        "pages.json and page visuals",
    )


@check("pbir_field_references")
def pbir_field_references(ctx, rule):
    spec = yaml.safe_load((ROOT / "configs/powerbi_model.yaml").read_text(encoding="utf-8"))
    columns = set()
    for name, entry in ctx.manifest["tables"].items():
        rename = spec["tables"][name].get("rename", {})
        columns |= {(name, rename.get(c, c)) for c in entry["columns"]}
    measures = {("_Measures", m["name"]) for m in spec["measures"]}
    refs = []
    for path in visual_files() + sorted(REPORT_DEF.glob("pages/*/page.json")):
        refs += field_refs(read_json(path), [])
    bad = sorted(
        {(e, p) for e, p, k in refs if (e, p) not in (columns if k == "Column" else measures)}
    )
    return (
        not bad,
        bad or f"{len(refs)} field references resolve",
        "visual.json and page.json files",
    )


@check("pbir_theme")
def pbir_theme(ctx, rule):
    report = read_json(REPORT_DEF / "report.json")
    custom = report["themeCollection"].get("customTheme", {})
    items = [i for p in report.get("resourcePackages", []) for i in p["items"]]
    path = REPORT_DEF.parent / "StaticResources/RegisteredResources" / custom.get("name", "missing")
    ok = (
        custom.get("type") == "RegisteredResources"
        and any(i["name"] == custom.get("name") and i["type"] == "CustomTheme" for i in items)
        and path.is_file()
    )
    if ok:
        read_json(path)
    return ok, f"customTheme={custom.get('name')} items={items}", "report.json"


@check("pbir_roles_and_slicers")
def pbir_roles_and_slicers(ctx, rule):
    problems, groups = [], set()
    for path in visual_files():
        visual = read_json(path)["visual"]
        if "Legend" in visual.get("query", {}).get("queryState", {}):
            problems.append(f"Legend role in {path.parent.name}")
        if path.parent.name == "sl_dataset":
            text = json.dumps(visual)
            groups.add(visual.get("syncGroup", {}).get("groupName"))
            if "singleSelect" not in text or "'Store Item'" not in text:
                problems.append(f"dataset slicer settings in {path.parents[2].name}")
    if groups != {"Dataset"}:
        problems.append(f"sync groups {groups}")
    return (
        not problems,
        problems or "no Legend roles; 4 dataset slicers synced",
        "visual.json files",
    )


@check("pbir_layout")
def pbir_layout(ctx, rule):
    outside, count = [], 0
    for page in PAGES:
        meta = read_json(REPORT_DEF / f"pages/{page}/page.json")
        for path in REPORT_DEF.glob(f"pages/{page}/visuals/*/visual.json"):
            position = read_json(path)["position"]
            count += 1
            if (
                position["x"] + position["width"] > meta["width"]
                or position["y"] + position["height"] > meta["height"]
            ):
                outside.append(f"{page}/{path.parent.name}")
    return (
        count == 86 and not outside,
        f"{count} visuals; outside canvas {outside}",
        "visual positions",
    )


@check("pbir_wording")
def pbir_wording(ctx, rule):
    import re

    flagged = []
    for path in visual_files():
        for match in re.finditer(
            r"[^.\"]*\bsavings?\b[^.\"]*", path.read_text(encoding="utf-8"), re.IGNORECASE
        ):
            sentence = match.group(0).lower()
            if not re.search(r"\bnot\b|\bnever\b|\bno\b", sentence):
                flagged.append(f"{path.parent.name}: {match.group(0).strip()[:80]}")
    return not flagged, flagged or "every mention of savings is a denial", "visual text"


def run(layers=None):
    config = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    ctx = Context()
    results = []
    for rule in config["rules"]:
        if layers and rule["layer"] not in layers:
            continue
        entry = {
            k: rule.get(k)
            for k in ("id", "layer", "description", "severity", "expected", "tolerance")
        }
        try:
            ok, actual, evidence = CHECKS[rule["check"]](ctx, rule)
            entry.update(
                status="PASS"
                if ok
                else ("FAIL" if rule["severity"] in ("CRITICAL", "HIGH") else "WARNING"),
                actual=actual if isinstance(actual, (str, int, float, list)) else str(actual),
                evidence=str(evidence),
            )
        except Exception as exc:  # recorded, never hidden
            entry.update(
                status="ERROR",
                actual=f"{type(exc).__name__}: {exc}",
                evidence=traceback.format_exc(limit=1).splitlines()[-1],
            )
        results.append(entry)
        print(
            f"{entry['id']} {entry['status']:7s} {entry['description'][:70]} | {str(entry['actual'])[:80]}"
        )
    blocking = [
        r["id"] for r in results if r["status"] in ("FAIL", "ERROR") and r["severity"] == "CRITICAL"
    ]
    summary = {
        "rules": len(results),
        "pass": sum(r["status"] == "PASS" for r in results),
        "warning": sum(r["status"] == "WARNING" for r in results),
        "fail": sum(r["status"] == "FAIL" for r in results),
        "error": sum(r["status"] == "ERROR" for r in results),
        "overall": "FAIL"
        if blocking or any(r["status"] in ("FAIL", "ERROR") for r in results)
        else "PASS",
        "blocking_rules": blocking,
        "layers": sorted({r["layer"] for r in results}),
    }
    output = ROOT / config["results"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    import sys

    run(set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None)
