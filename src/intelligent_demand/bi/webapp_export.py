"""Phase 7 curated web-application export (read-only with respect to all scientific evidence).

Sources: the frozen Phase 5 plan (verified by `plan()`), the approved Phase 5 validation adapter
`load_cohort` (rejects any non-validation window), origin-bounded training caches (hash-checked), and the
hash-verified Phase 6 reporting CSVs. Writes CSVs to artifacts/webapp/data and a tracked manifest.
No final-holdout target is read; every dated row ends before each dataset's test start.

Usage:  .venv\\Scripts\\python.exe -m intelligent_demand.bi.webapp_export
"""

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from intelligent_demand.inventory.inputs import load_cohort
from intelligent_demand.inventory.plan import plan as frozen_plan

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "configs/webapp.yaml"
PHASE6 = ROOT / "reports/powerbi/data_manifest.json"
ROLES = ("selected_ml", "moving_average_28", "seasonal_naive")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def phase6_table(manifest, name, usecols=None):
    entry = manifest["tables"][name]
    path = ROOT / entry["file"]
    if sha256(path) != entry["sha256"]:
        raise ValueError(f"Phase 6 reporting table changed: {name}")
    return pd.read_csv(path, usecols=usecols, low_memory=False)


def curate(config, plan, series):
    """Deterministic, predeclared M5 subset; uses only the training-prefix pattern column."""
    rule = config["curation"]["m5"]
    m5 = series[series.DatasetKey == "m5"].sort_values("SeriesId")
    representatives = set(next(c["representatives"] for c in plan["cohorts"] if c["dataset"] == "m5"))
    rng = np.random.default_rng(rule["seed"])
    chosen, strata = [], {}
    for pattern, count in rule["strata"].items():
        pool = m5[m5.PatternKey == pattern].SeriesId.tolist()
        if count > len(pool):
            raise ValueError(f"Stratum {pattern} has only {len(pool)} series")
        picked = [pool[i] for i in sorted(rng.choice(len(pool), size=count, replace=False))]
        forced = sorted(representatives & set(pool))
        for rep in forced:
            if rep not in picked:  # replace the last sampled non-representative of the stratum
                victim = next(s for s in reversed(picked) if s not in representatives)
                picked[picked.index(victim)] = rep
        chosen += picked
        strata.update({s: pattern for s in picked})
    if not representatives <= set(chosen) or len(chosen) != sum(rule["strata"].values()):
        raise ValueError("Curated M5 set violates its declared rule")
    return sorted(chosen), strata


def build():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    plan = frozen_plan()  # verifies the frozen plan and design-file hashes
    manifest6 = read_json(PHASE6)
    splits = read_json(ROOT / "reports/eda/proposed_splits.json")
    series = phase6_table(manifest6, "DimSeries")
    m5_ids, strata = curate(config, plan, series)
    store_ids = sorted(series[series.DatasetKey == "store_item"].SeriesId)
    curated = {"store_item": set(store_ids), "m5": set(m5_ids)}
    keys = {f"store_item|{s}" for s in store_ids} | {f"m5|{s}" for s in m5_ids}

    tables = {}
    datasets = phase6_table(manifest6, "DimDataset")
    datasets["TestStart"] = datasets.DatasetKey.map({k: v["test_start"] for k, v in splits.items()})
    datasets["CuratedSeries"] = datasets.DatasetKey.map({k: len(v) for k, v in curated.items()})
    tables["datasets"] = datasets
    for name, source in (
        ("validation_origins", "DimValidationOrigin"),
        ("forecast_models", "DimForecastModel"),
        ("demand_patterns", "DimDemandPattern"),
        ("inventory_policies", "DimInventoryPolicy"),
        ("scenarios", "DimScenario"),
        ("model_selection_trials", "FactModelSelectionTrials"),
        ("final_holdout_reported", "FactFinalHoldoutReported"),
        ("limitations", "DimLimitation"),
        ("audit_findings", "DimAuditFinding"),
        ("inventory_scenario_results", "FactInventoryScenarioResults"),
    ):
        tables[name] = phase6_table(manifest6, source)
    cur = series[series.SeriesKey.isin(keys)].copy()
    cur["CurationStratum"] = np.where(cur.DatasetKey == "m5", cur.SeriesId.map(strata), "all")
    tables["series"] = cur.drop(columns=["HasDailyDetail"])

    history, actuals, forecasts, means = [], [], [], []
    days = config["history_days"]
    for cohort in plan["cohorts"]:
        dataset, fold = cohort["dataset"], cohort["fold"]["number"]
        origin_key = f"{dataset}|{fold}"
        metadata, actual, mean, predictions, coverage = load_cohort(cohort)
        if any(coverage[r] for r in ROLES):
            raise ValueError("Unexpected forecast fallback observations")
        rows = np.flatnonzero(metadata.series_id.isin(curated[dataset]).to_numpy())
        sid = metadata.series_id.to_numpy()[rows]
        skey = np.array([f"{dataset}|{s}" for s in sid])
        cache_manifest = read_json(ROOT / cohort["training_cache"]["path"])
        cache_path = (ROOT / cohort["training_cache"]["path"]).parent / cache_manifest["values"]
        if sha256(cache_path) != cache_manifest["files"][cache_manifest["values"]]:
            raise ValueError("Origin-bound training cache changed")
        values = np.load(cache_path, mmap_mode="r")
        block = np.asarray(values[rows, -days:], dtype=float)
        del values
        origin = pd.Timestamp(cohort["fold"]["origin"])
        hist_dates = pd.date_range(origin - pd.Timedelta(days=days - 1), origin).date
        val_dates = pd.date_range(cohort["fold"]["validation_start"], periods=28).date
        history.append(
            pd.DataFrame(
                {
                    "SeriesKey": np.repeat(skey, days),
                    "OriginKey": origin_key,
                    "Date": np.tile(hist_dates, len(rows)),
                    "Units": block.ravel(),
                }
            )
        )
        actuals.append(
            pd.DataFrame(
                {
                    "SeriesKey": np.repeat(skey, 28),
                    "OriginKey": origin_key,
                    "Date": np.tile(val_dates, len(rows)),
                    "Units": actual[rows].ravel(),
                }
            )
        )
        for role in ROLES:
            forecasts.append(
                pd.DataFrame(
                    {
                        "SeriesKey": np.repeat(skey, 28),
                        "OriginKey": origin_key,
                        "ModelKey": f"{dataset}|{role}",
                        "HorizonDay": np.tile(np.arange(1, 29), len(rows)),
                        "Date": np.tile(val_dates, len(rows)),
                        "Forecast": predictions[role][rows].ravel(),
                    }
                )
            )
        means.append(pd.DataFrame({"SeriesKey": skey, "OriginKey": origin_key, "HistoricalMean56": mean[rows]}))
        print(f"cohort {origin_key}: {len(rows):,} curated series", flush=True)
    tables["series_history"] = pd.concat(history, ignore_index=True)
    tables["validation_actuals"] = pd.concat(actuals, ignore_index=True)
    tables["forecasts"] = pd.concat(forecasts, ignore_index=True)
    tables["series_origin_mean56"] = pd.concat(means, ignore_index=True)

    fso = phase6_table(manifest6, "FactForecastSeriesOrigin")
    tables["forecast_metrics_series"] = fso[fso.SeriesKey.isin(keys)].reset_index(drop=True)
    fso["MaseValue"] = fso.SumAbsError / fso.Observations / fso.ScaleAbs
    fso["RmsseValue"] = np.sqrt(fso.SumSquaredError / fso.Observations / fso.ScaleSquared)
    additive = ["Observations", "SumAbsError", "SumSquaredError", "SumError", "SumActual", "SumForecast"]
    parts = []
    for pattern_level in (True, False):
        keys_ = ["DatasetKey", "OriginKey", "ModelKey"] + (["PatternKey"] if pattern_level else [])
        grouped = fso.groupby(keys_)
        agg = grouped[additive].sum()
        agg["Series"] = grouped.size()
        agg["MaseSum"] = grouped.MaseValue.sum()  # NaN (undefined scale) excluded by sum/count
        agg["MaseCount"] = grouped.MaseValue.count()
        agg["RmsseSum"] = grouped.RmsseValue.sum()
        agg["RmsseCount"] = grouped.RmsseValue.count()
        agg = agg.reset_index()
        if not pattern_level:
            agg["PatternKey"] = "all"
        parts.append(agg)
    tables["forecast_metrics_aggregate"] = pd.concat(parts, ignore_index=True)
    fisb = phase6_table(manifest6, "FactInventorySeriesBase")
    tables["inventory_series_base"] = fisb[fisb.SeriesKey.isin(keys)].reset_index(drop=True)

    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    selection = read_json(ROOT / "artifacts/experiments/phase4/frozen_selection.json")
    provenance = {
        "ExportVersion": config["export_version"],
        "GitCommit": git,
        "PlanSha256": plan["sha256"],
        "ExecutionSha256": read_json(ROOT / "artifacts/inventory/phase5/execution.json")["sha256"],
        "SelectionFingerprint": selection["manifest_sha256"],
        "LedgerSha256": sha256(ROOT / "artifacts/experiments/phase4/holdout_access.jsonl"),
        "Phase6ManifestSha256": sha256(PHASE6),
        "FinalHoldoutTargetsRead": False,
        "CuratedM5Sha256": hashlib.sha256("\n".join(m5_ids).encode()).hexdigest(),
    }
    tables["provenance"] = pd.DataFrame([provenance])

    output = ROOT / config["output_directory"]
    output.mkdir(parents=True, exist_ok=True)
    entries = {}
    for name, frame in tables.items():
        path = output / f"{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
        entries[name] = {
            "file": path.relative_to(ROOT).as_posix(),
            "rows": len(frame),
            "columns": list(frame.columns),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
    manifest = {
        "schema_version": 1,
        "export_version": config["export_version"],
        "provenance": provenance,
        "curated_m5_series": m5_ids,
        "tables": entries,
    }
    target = ROOT / config["manifest"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    total = sum(e["bytes"] for e in entries.values())
    for name, entry in entries.items():
        print(f"{name:28s} {entry['rows']:>9,} rows {entry['bytes'] / 1e6:7.2f} MB")
    print(f"total CSV {total / 1e6:.1f} MB")


if __name__ == "__main__":
    build()
