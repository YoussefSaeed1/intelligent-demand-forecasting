"""Phase 7 data and database quality gates (D-01..D-07, A-05, A-09).

Data gates compare the curated export with independent saved evidence (Phase 6 detail facts, registry
metrics, Phase 4 leaderboard, Phase 5 per-case outputs). Database gates (`--db URL`) check the seeded
Postgres: row counts, provenance, actual size, and role/RLS behaviour.
Usage:  .venv\\Scripts\\python.exe -m intelligent_demand.bi.webapp_qa [--db postgresql://...]
"""

import argparse
import hashlib
import json
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "reports/webapp/export_manifest.json"
RESULTS = ROOT / "reports/webapp/qa_data_results.json"
CHECKS = []


def gate(gate_id, severity, description):
    def register(function):
        CHECKS.append((gate_id, severity, description, function))
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
    def __init__(self, db=None):
        self.manifest = read_json(MANIFEST)
        self.plan = read_json(ROOT / "artifacts/inventory/phase5/plan.json")
        self.phase6 = read_json(ROOT / "reports/powerbi/data_manifest.json")
        self.cache, self.db = {}, db

    def table(self, name):
        if name not in self.cache:
            self.cache[name] = pd.read_csv(ROOT / self.manifest["tables"][name]["file"], low_memory=False)
        return self.cache[name]

    def phase6_table(self, name, usecols=None):
        return pd.read_csv(ROOT / self.phase6["tables"][name]["file"], usecols=usecols, low_memory=False)


@gate("D-01", "CRITICAL", "Export files match the manifest; source evidence hashes unchanged")
def d01(ctx):
    bad = [
        n
        for n, e in ctx.manifest["tables"].items()
        if sha256(ROOT / e["file"]) != e["sha256"] or len(ctx.table(n)) != e["rows"]
    ]
    p = ctx.manifest["provenance"]
    from intelligent_demand.inventory.plan import plan

    sources = {
        "plan": (plan()["sha256"], p["PlanSha256"], "63efc59ed0dc2b35b2ad3067fb790c0b42d0c1f279e3f8142519b78c07cce76e"),
        "selection": (
            read_json(ROOT / "artifacts/experiments/phase4/frozen_selection.json")["manifest_sha256"],
            p["SelectionFingerprint"],
            "a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb",
        ),
        "ledger": (
            sha256(ROOT / "artifacts/experiments/phase4/holdout_access.jsonl"),
            p["LedgerSha256"],
            "fa2af529b50299b50c8d77d67b0ce70f73fab35e4731a5b825dd27a20e4bc204",
        ),
        "execution": (
            read_json(ROOT / "artifacts/inventory/phase5/execution.json")["sha256"],
            p["ExecutionSha256"],
            "b55ba4a0c9c8fafb2ee3997f38d2f31efea99f4157033e70288814a2006c87c3",
        ),
        "phase6_manifest": (sha256(ROOT / "reports/powerbi/data_manifest.json"), p["Phase6ManifestSha256"], None),
    }
    drift = [k for k, (now, recorded, frozen) in sources.items() if now != recorded or (frozen and now != frozen)]
    return not bad and not drift, f"{len(ctx.manifest['tables'])} files; mismatched {bad}; source drift {drift}"


@gate("D-02", "CRITICAL", "Actuals and forecasts for the 506 Phase 6 detail series equal FactForecastSeriesDaily exactly")
def d02(ctx):
    detail = ctx.phase6_table("FactForecastSeriesDaily")
    actual = ctx.table("validation_actuals")
    fc = ctx.table("forecasts")
    keys = set(detail.SeriesKey)
    a = actual[actual.SeriesKey.isin(keys)].merge(
        detail[detail.ModelKey.str.endswith("|selected_ml")][["SeriesKey", "OriginKey", "Date", "Actual"]],
        on=["SeriesKey", "OriginKey", "Date"],
        validate="one_to_one",
    )
    f = fc[fc.SeriesKey.isin(keys)].merge(
        detail[["SeriesKey", "OriginKey", "ModelKey", "Date", "Forecast"]],
        on=["SeriesKey", "OriginKey", "ModelKey", "Date"],
        suffixes=("", "_p6"),
        validate="one_to_one",
    )
    expected_a = len(keys) * 4 * 28
    ok = (
        len(a) == expected_a
        and len(f) == expected_a * 3
        and np.array_equal(a.Units, a.Actual)
        and np.array_equal(f.Forecast, f.Forecast_p6)
    )
    return ok, f"{len(keys)} series; {len(a):,} actual and {len(f):,} forecast rows compared exactly"


@gate(
    "D-03",
    "CRITICAL",
    "No exported date reaches the final holdout; history ends on the origin; validation rows inside windows",
)
def d03(ctx):
    origins = ctx.table("validation_origins").set_index("OriginKey")
    test_start = ctx.table("datasets").set_index("DatasetKey").TestStart
    problems = 0
    for name in ("series_history", "validation_actuals", "forecasts"):
        frame = ctx.table(name)
        date = pd.to_datetime(frame.Date)
        o = origins.loc[frame.OriginKey]
        ts = pd.to_datetime(test_start.loc[frame.OriginKey.str.split("|").str[0]].to_numpy())
        problems += int((date.to_numpy() >= ts).sum())
        if name == "series_history":
            problems += int((date.to_numpy() > pd.to_datetime(o.OriginDate).to_numpy()).sum())
            last = frame.assign(D=date).groupby(["SeriesKey", "OriginKey"]).D.max()
            problems += int(
                (last.to_numpy() != pd.to_datetime(origins.loc[last.index.get_level_values(1)].OriginDate).to_numpy()).sum()
            )
        else:
            inside = (date.to_numpy() >= pd.to_datetime(o.ValidationStart).to_numpy()) & (
                date.to_numpy() <= pd.to_datetime(o.ValidationEnd).to_numpy()
            )
            problems += int((~inside).sum())
    return problems == 0, f"{problems} rows outside approved windows (test starts {dict(test_start)})"


@gate(
    "D-04", "CRITICAL", "Aggregates reproduce the 24 registry pooled metrics, macro MASE and the leaderboard primary scores"
)
def d04(ctx):
    agg = ctx.table("forecast_metrics_aggregate")
    agg = agg[agg.PatternKey == "all"].set_index(["OriginKey", "ModelKey"])
    mine, ref = [], []
    for cohort in ctx.plan["cohorts"]:
        for role, source in cohort["sources"].items():
            directory = (ROOT / source["specification"]["path"]).parent
            status = read_json(directory / "status.json")
            saved = read_json(directory / status["outputs"]["metrics"]["path"].replace("\\", "/"))["all"]
            row = agg.loc[(f"{cohort['dataset']}|{cohort['fold']['number']}", f"{cohort['dataset']}|{role}")]
            mine += [
                row.SumAbsError / row.Observations,
                np.sqrt(row.SumSquaredError / row.Observations),
                100 * row.SumAbsError / row.SumActual,
                row.SumError / row.Observations,
                row.MaseSum / row.MaseCount,
            ]
            ref += [
                saved["pooled"]["mae"],
                saved["pooled"]["rmse"],
                saved["pooled"]["wape_percent"],
                saved["pooled"]["bias_units"],
                saved["macro"]["mase"],
            ]
    board = {t["trial_id"]: t for t in read_json(ROOT / "artifacts/experiments/phase4/trial_leaderboard.json")}
    for dataset, trial in (("store_item", "store_item_lightgbm_00"), ("m5", "m5_random_forest_02")):
        rows = agg[agg.index.get_level_values(1) == f"{dataset}|selected_ml"]
        mine.append((rows.SumAbsError / rows.Observations).mean())
        ref.append(board[trial]["primary_score"])
    ok = np.allclose(mine, ref, rtol=1e-9, atol=0)
    worst = float(np.max(np.abs(np.array(mine) - np.array(ref)) / np.abs(np.array(ref))))
    return ok, f"{len(ref)} reference values; max relative difference {worst:.2e}"


@gate("D-05", "CRITICAL", "Keys unique, foreign keys resolve, curated set matches the predeclared rule")
def d05(ctx):
    config = yaml.safe_load((ROOT / "configs/webapp.yaml").read_text(encoding="utf-8"))
    problems = []
    pk = {
        "series": ["SeriesKey"],
        "series_history": ["SeriesKey", "OriginKey", "Date"],
        "validation_actuals": ["SeriesKey", "OriginKey", "Date"],
        "forecasts": ["SeriesKey", "OriginKey", "ModelKey", "HorizonDay"],
        "series_origin_mean56": ["SeriesKey", "OriginKey"],
        "forecast_metrics_series": ["SeriesKey", "OriginKey", "ModelKey"],
        "forecast_metrics_aggregate": ["OriginKey", "ModelKey", "PatternKey"],
        "inventory_scenario_results": ["OriginKey", "ScenarioKey", "PolicyKey", "PatternKey"],
        "inventory_series_base": ["SeriesKey", "OriginKey", "PolicyKey"],
    }
    for name, key in pk.items():
        if ctx.table(name).duplicated(key).any():
            problems.append(f"duplicate key in {name}")
    series = set(ctx.table("series").SeriesKey)
    for name in (
        "series_history",
        "validation_actuals",
        "forecasts",
        "series_origin_mean56",
        "forecast_metrics_series",
        "inventory_series_base",
    ):
        if not set(ctx.table(name).SeriesKey) <= series:
            problems.append(f"orphan series in {name}")
        expected = (
            len(series)
            * 4
            * {
                "series_history": config["history_days"],
                "validation_actuals": 28,
                "forecasts": 84,
                "series_origin_mean56": 1,
                "forecast_metrics_series": 3,
                "inventory_series_base": 4,
            }[name]
        )
        if len(ctx.table(name)) != expected:
            problems.append(f"{name} rows {len(ctx.table(name))} != {expected}")
    cur = ctx.table("series")
    m5 = cur[cur.DatasetKey == "m5"]
    counts = m5.CurationStratum.value_counts().to_dict()
    if counts != config["curation"]["m5"]["strata"] or (m5.CurationStratum != m5.PatternKey).any():
        problems.append(f"strata {counts}")
    reps = {f"m5|{s}" for s in next(c["representatives"] for c in ctx.plan["cohorts"] if c["dataset"] == "m5")}
    if not reps <= set(m5.SeriesKey) or (cur.DatasetKey == "store_item").sum() != 500:
        problems.append("representatives or Store Item coverage")
    from intelligent_demand.bi import webapp_export

    again, _ = webapp_export.curate(config, ctx.plan, ctx.phase6_table("DimSeries"))
    if again != ctx.manifest["curated_m5_series"]:
        problems.append("curation not reproducible")
    return not problems, problems or f"800 series (500 + 300), strata {counts}, 6 representatives, reproducible"


@gate("D-06", "HIGH", "Inventory base rows and historical means equal the Phase 5 per-case outputs for curated series")
def d06(ctx):
    exported = ctx.table("inventory_series_base").set_index(["SeriesKey", "OriginKey", "PolicyKey"])
    mean56 = ctx.table("series_origin_mean56").set_index(["SeriesKey", "OriginKey"]).HistoricalMean56
    compared = mismatch = 0
    for path in (ROOT / "artifacts/inventory/phase5/runs").glob("*/status.json"):
        status = read_json(path)
        if status["scenario"]["identifier"] != "base":
            continue
        item = status["files"]["series"]
        if sha256(ROOT / item["path"]) != item["sha256"]:
            raise ValueError("Phase 5 case output changed")
        frame = pq.read_table(
            ROOT / item["path"], columns=["series_id", "total_cost", "fulfilled_units", "demand_units", "historical_mean56"]
        ).to_pandas()
        dataset, origin = status["dataset"], f"{status['dataset']}|{status['fold']['number']}"
        frame["SeriesKey"] = dataset + "|" + frame.series_id
        frame = frame[frame.SeriesKey.isin(set(exported.index.get_level_values(0)))]
        ex = exported.loc[[(k, origin, status["policy"]) for k in frame.SeriesKey]]
        m = mean56.loc[[(k, origin) for k in frame.SeriesKey]]
        mismatch += int((~np.isclose(ex.TotalCost.to_numpy(), frame.total_cost, rtol=1e-12, atol=0)).sum())
        mismatch += int((~np.isclose(m.to_numpy(), frame.historical_mean56, rtol=1e-12, atol=0)).sum())
        compared += len(frame)
    return mismatch == 0 and compared == 12800, f"{compared:,} series-origin-policy rows; mismatches {mismatch}"


# ------------------------------------------------------------------ database gates (--db)
def connect(url):
    import psycopg

    return psycopg.connect(url, autocommit=True)


@gate("D-07", "CRITICAL", "Seeded Postgres row counts equal the manifest; provenance export version matches")
def d07(ctx):
    if not ctx.db:
        return None, "skipped (no --db)"
    with connect(ctx.db) as conn:
        bad = []
        for name, entry in ctx.manifest["tables"].items():
            rows = conn.execute(f'select count(*) from app."{name}"').fetchone()[0]
            if rows != entry["rows"]:
                bad.append(f"{name}: {rows} != {entry['rows']}")
        version = conn.execute("select export_version from app.provenance").fetchone()[0]
        size = conn.execute(
            "select sum(pg_total_relation_size(c.oid)) from pg_class c join pg_namespace n "
            "on n.oid = c.relnamespace where n.nspname = 'app' and c.relkind = 'r'"
        ).fetchone()[0]
        db_size = conn.execute("select pg_database_size(current_database())").fetchone()[0]
    ok = not bad and version == ctx.manifest["export_version"]
    return (
        ok,
        f"{len(ctx.manifest['tables'])} tables; mismatches {bad}; version {version}; "
        f"app schema {float(size) / 1e6:.1f} MB incl. indexes and TOAST; database {float(db_size) / 1e6:.1f} MB",
    )


@gate(
    "A-05", "CRITICAL", "Roles and RLS: readers can only SELECT app tables; anon/authenticated have no access; writes fail"
)
def a05(ctx):
    if not ctx.db:
        return None, "skipped (no --db)"
    import psycopg

    outcomes = {}
    with connect(ctx.db) as conn:
        for role in ("webapp_api", "engine_api", "anon", "authenticated"):
            for label, sql in (
                ("select", "select count(*) from app.series"),
                ("insert", "insert into app.limitations values ('X', 'x', 'x')"),
                ("update", "update app.series set series_id = series_id"),
                ("delete", "delete from app.limitations"),
                ("ddl", "create table app.intruder(x int)"),
            ):
                try:
                    with conn.transaction():
                        conn.execute(f"set local role {role}")
                        conn.execute(sql)
                        raise _Rollback("allowed")
                except _Rollback:
                    outcomes[(role, label)] = "allowed"
                except psycopg.Error:
                    outcomes[(role, label)] = "denied"
            try:
                with conn.transaction():
                    conn.execute(f"set local role {role}")
                    conn.execute("select count(*) from app.validation_actuals")
                    raise _Rollback("allowed")
            except _Rollback:
                outcomes[(role, "actuals")] = "allowed"
            except psycopg.Error:
                outcomes[(role, "actuals")] = "denied"
    expected = {
        (r, op): "denied"
        for r in ("webapp_api", "engine_api", "anon", "authenticated")
        for op in ("insert", "update", "delete", "ddl")
    }
    expected.update(
        {
            ("webapp_api", "select"): "allowed",
            ("engine_api", "actuals"): "allowed",
            ("webapp_api", "actuals"): "allowed",
            ("engine_api", "select"): "denied",
            ("anon", "select"): "denied",
            ("authenticated", "select"): "denied",
            ("anon", "actuals"): "denied",
            ("authenticated", "actuals"): "denied",
        }
    )
    wrong = {f"{r}.{o}": v for (r, o), v in outcomes.items() if expected.get((r, o)) != v}
    return not wrong, wrong or f"{len(outcomes)} role/operation probes behaved as designed"


@gate("A-09", "HIGH", "Rate-limit function is callable only by webapp_api and stores hashed buckets only")
def a09(ctx):
    if not ctx.db:
        return None, "skipped (no --db)"
    import psycopg

    with connect(ctx.db) as conn:
        results = {}
        for role in ("webapp_api", "engine_api", "anon"):
            try:
                with conn.transaction():
                    conn.execute(f"set local role {role}")
                    results[role] = conn.execute("select ops.rate_limit_hit(%s, 2, 60)", ("a" * 64,)).fetchone()[0]
                    raise _Rollback("ok")
            except _Rollback:
                pass
            except psycopg.Error:
                results[role] = "denied"
        try:
            with conn.transaction():
                conn.execute("set local role webapp_api")
                conn.execute("select ops.rate_limit_hit(%s, 2, 60)", ("not-a-hash",))
                bad_bucket = "accepted"
        except psycopg.Error:
            bad_bucket = "rejected"
    ok = (
        results.get("webapp_api") is True
        and results.get("engine_api") == "denied"
        and results.get("anon") == "denied"
        and bad_bucket == "rejected"
    )
    return ok, f"calls {results}; non-hash bucket {bad_bucket}"


class _Rollback(Exception):
    pass


def run(db=None, only=None):
    ctx = Context(db)
    previous = read_json(RESULTS)["results"] if RESULTS.exists() and only else []
    results = [r for r in previous if r["id"] not in (only or ())]
    for gate_id, severity, description, function in CHECKS:
        if only and gate_id not in only:
            continue
        try:
            ok, actual = function(ctx)
            status = (
                "SKIPPED" if ok is None else ("PASS" if ok else ("FAIL" if severity in ("CRITICAL", "HIGH") else "WARNING"))
            )
        except Exception as exc:
            status, actual = "ERROR", f"{type(exc).__name__}: {exc} | {traceback.format_exc(limit=2).splitlines()[-1]}"
        results.append(
            {
                "id": gate_id,
                "severity": severity,
                "description": description,
                "status": status,
                "actual": actual if isinstance(actual, (str, list, dict)) else str(actual),
            }
        )
        print(f"{gate_id} {status:7s} {description[:70]} | {str(actual)[:160]}")
    order = [c[0] for c in CHECKS]
    results.sort(key=lambda r: order.index(r["id"]))
    summary = {s: sum(r["status"] == s for r in results) for s in ("PASS", "WARNING", "FAIL", "ERROR", "SKIPPED")}
    summary["overall"] = "FAIL" if summary["FAIL"] or summary["ERROR"] else "PASS"
    RESULTS.write_text(json.dumps({"summary": summary, "results": results}, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", help="Postgres URL with owner rights (local test database only)")
    parser.add_argument("--only", help="comma-separated gate ids; merges into the existing results file")
    args = parser.parse_args()
    run(args.db, set(args.only.split(",")) if args.only else None)
