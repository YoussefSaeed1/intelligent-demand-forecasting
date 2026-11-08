"""Independent read-only NumPy reconciliation; never invokes research fits/scorers.

Canonical target scans are strictly limited to the four validation windows.
Final actuals come only from original checksummed scoring snapshots. Their audit
access is recorded separately; the original holdout ledger is never modified.
"""

import gc
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import pyarrow as pa
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/post_audit"
P4 = ROOT / "artifacts/experiments/phase4"
METRICS = ("mae", "rmse", "bias_units", "wape_percent", "bias_percent", "mase", "rmsse")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def same(a, b):
    if isinstance(a, dict):
        for key in a:
            same(a[key], b[key])
    elif a is None:
        assert b is None, (a, b)
    else:
        assert np.isclose(a, b, rtol=1e-9, atol=1e-10), (a, b)


def metrics(y, p, q, fallback, clipped):
    residual = p - y
    absolute, squared = np.abs(residual), residual * residual
    volume = y.sum(1)
    per = {"mae": absolute.mean(1), "rmse": np.sqrt(squared.mean(1)),
           "bias_units": residual.mean(1)}
    with np.errstate(divide="ignore", invalid="ignore"):
        per.update(wape_percent=np.where(volume > 0, 100 * absolute.sum(1) / volume, np.nan),
                   bias_percent=np.where(volume > 0, 100 * residual.sum(1) / volume, np.nan),
                   mase=per["mae"] / q[:, 0], rmsse=np.sqrt(squared.mean(1) / q[:, 1]))
    macro, defined = {}, {}
    for key, values in per.items():
        mask = np.isfinite(values)
        defined[key] = int(mask.sum())
        macro[key] = float(values[mask].mean()) if mask.any() else None
    total = float(y.sum())
    pooled = {"mae": float(absolute.mean()), "rmse": float(np.sqrt(squared.mean())),
              "bias_units": float(residual.mean()),
              "wape_percent": float(100 * absolute.sum() / total) if total else None,
              "bias_percent": float(100 * residual.sum() / total) if total else None}
    coverage = {"observations": int(y.size), "series": len(y), "defined_series": defined,
                "undefined_series": {k: len(y) - n for k, n in defined.items()},
                "fallback_observations": int(fallback.sum()),
                "clipped_observations": int(clipped.sum())}
    return {"macro": macro, "pooled": pooled, "coverage": coverage}, per, {
        "n": int(y.size), "actual": total, "absolute": float(absolute.sum()),
        "squared": float(squared.sum()), "signed": float(residual.sum())}


def aligned(frame, metadata, start, value):
    series = pd.Index(metadata.series_id)
    row = series.get_indexer(frame.series_id)
    dates = pd.to_datetime(frame.target_date)
    col = (dates - pd.Timestamp(start)).dt.days.to_numpy()
    assert len(frame) == len(series) * 28
    assert (row >= 0).all() and ((col >= 0) & (col < 28)).all()
    assert dates.eq(dates.dt.normalize()).all() and dates.dt.tz is None
    assert len(np.unique(row * 28 + col)) == len(frame)
    data = frame[value].to_numpy()
    assert np.isfinite(data).all() and (data >= 0).all()
    result = np.empty((len(series), 28), dtype=float)
    result[row, col] = data
    return result, row, col


def scales(dataset, origin, metadata):
    matches = []
    for directory in (ROOT / "artifacts/experiments/phase3/cache", P4 / "cache"):
        for manifest in directory.glob("*/complete.json"):
            value = read(manifest)
            contract = value["contract"]
            if contract["dataset"] != dataset or contract["origin"] != origin:
                continue
            panel = np.load(manifest.parent / value["values"], mmap_mode="r")
            if panel.shape[0] == len(metadata):
                matches.append((manifest, value, panel))
    assert len(matches) == 1, (dataset, origin, len(matches))
    manifest, value, panel = matches[0]
    assert identity(list(metadata.series_id)) == value["contract"]["population"]
    length = (pd.Timestamp(origin) - pd.Timestamp(value["contract"]["start"])).days + 1
    assert panel.shape[1] == length
    assert digest(manifest.parent / value["values"]) == value["files"][value["values"]]
    result = np.empty((len(panel), 2))
    for first in range(0, len(panel), 64):
        history = panel[first:first + 64].astype(float)
        difference = history[:, 7:] - history[:, :-7]
        result[first:first + len(history), 0] = np.abs(difference).sum(1) / difference.shape[1]
        result[first:first + len(history), 1] = np.square(difference).sum(1) / difference.shape[1]
    result[result == 0] = np.nan
    return result


def check_prediction(path, state, dataset, origin, metadata, y, q):
    spec = state["specification"]
    frame = pd.read_parquet(path)
    assert frame.dataset_id.eq(dataset).all() and frame.run_id.eq(state["run_id"]).all()
    assert frame.model_id.eq(spec["model"]["identifier"]).all()
    assert frame.model_version.eq(spec["model"]["version"]).all()
    assert pd.to_datetime(frame.forecast_origin).eq(pd.Timestamp(origin)).all()
    start = pd.Timestamp(origin) + pd.Timedelta(days=1)
    p, row, col = aligned(frame, metadata, start, "prediction")
    assert frame.horizon_step.eq(col + 1).all()
    assert np.array_equal(frame.prediction, np.maximum(frame.raw_prediction, 0))
    assert np.isfinite(frame.raw_prediction).all()
    assert frame.was_clipped.eq(frame.raw_prediction.lt(0)).all()
    flags = []
    for flag in ("is_fallback", "was_clipped"):
        assert frame[flag].dtype == bool and not frame[flag].isna().any()
        array = np.empty_like(p, dtype=bool)
        array[row, col] = frame[flag]
        flags.append(array)
    return p, flags, metrics(y, p, q, *flags)


def compare(saved, calculated, per, metadata, y, p, q, flags):
    same(calculated, saved["all"])
    table = pd.DataFrame(saved["all"]["per_series"]).set_index("series_id").loc[metadata.series_id]
    for name in METRICS:
        assert np.allclose(per[name], table[name].to_numpy(dtype=float),
                           rtol=1e-9, atol=1e-10, equal_nan=True), name
    for step in range(28):
        result = metrics(y[:, step:step + 1], p[:, step:step + 1], q,
                         flags[0][:, step:step + 1], flags[1][:, step:step + 1])[0]
        same(result, saved["by_horizon"][str(step + 1)])
    for pattern in metadata.pattern.unique():
        mask = metadata.pattern.eq(pattern).to_numpy()
        same(metrics(y[mask], p[mask], q[mask], flags[0][mask], flags[1][mask])[0],
             saved["by_demand_class"][pattern])


def main():
    began = time.perf_counter()
    before = digest(P4 / "holdout_access.jsonl")
    splits = read(ROOT / "reports/eda/proposed_splits.json")
    board = read(P4 / "trial_leaderboard.json")
    states = []
    for phase, directory in (("phase3", ROOT / "artifacts/experiments/forecasting"),
                             ("phase4", P4 / "registry")):
        for status in directory.glob("*/status.json"):
            state = read(status)
            assert state["status"] == "completed"
            state["specification"] = read(status.parent / "specification.json")
            assert identity(state["specification"]) == state["specification_sha256"]
            states.append((phase, status.parent, state))
    records = []
    for dataset in ("store_item", "m5"):
        meta = pd.read_parquet(ROOT / f"reports/eda/tables/{dataset}/series.parquet")
        meta = meta.sort_values("series_id").reset_index(drop=True)
        for fold in splits[dataset]["validation_folds"]:
            origin = fold["origin"]
            q = scales(dataset, origin, meta)
            # Explicit bounded validation predicates, with no final target request.
            first = pa.scalar(pd.Timestamp(fold["validation_start"]).date())
            last = pa.scalar(pd.Timestamp(fold["validation_end"]).date())
            expression = (ds.field("date") >= first) & (ds.field("date") <= last)
            assert fold["validation_end"] < splits[dataset]["test_start"]
            source = ds.dataset(ROOT / f"data/processed/{dataset}/daily_sales.parquet")
            actual_frame = source.to_table(columns=["series_id", "date", "sales_units"],
                                           filter=expression, use_threads=False).to_pandas()
            actual_frame = actual_frame.rename(columns={"date": "target_date"})
            actual, _, _ = aligned(actual_frame, meta, fold["validation_start"], "sales_units")
            del actual_frame, source
            cohort = [s for s in states if s[2]["specification"]["dataset_id"] == dataset
                      and s[2]["specification"]["fold"]["origin"] == origin]
            for phase, directory, state in cohort:
                outputs, spec = state["outputs"], state["specification"]
                pred_path = directory / outputs["predictions"]["path"]
                ids = sorted(pd.read_parquet(pred_path, columns=["series_id"]).series_id.unique())
                assert identity(ids) == spec["series_sha256"] and len(ids) == spec["series_count"]
                indexes = pd.Index(meta.series_id).get_indexer(ids)
                assert (indexes >= 0).all()
                metadata, y, qs = meta.iloc[indexes], actual[indexes], q[indexes]
                p, flags, (calculated, per, totals) = check_prediction(
                    pred_path, state, dataset, origin, metadata, y, qs)
                saved = read(directory / outputs["metrics"]["path"])
                compare(saved, calculated, per, metadata, y, p, qs, flags)
                records.append({"phase": phase, "dataset": dataset, "origin": origin,
                                "run_id": state["run_id"], "model": spec["model"]["identifier"],
                                "series": len(ids), **calculated, "totals": totals})
                del p, flags, saved, per, y, metadata
            print(dataset, origin, len(cohort), "runs reconciled", flush=True)
            del actual, q
            gc.collect()
    trial_results = []
    for case in board:
        folds = [next(r for r in records if r["run_id"] == run) for run in case["runs"]]
        n = sum(r["totals"]["n"] for r in folds)
        result = {"trial_id": case["trial_id"], "fold_mae": [r["macro"]["mae"] for r in folds],
                  "primary_score": float(np.mean([r["macro"]["mae"] for r in folds])),
                  "pooled_rmse": float(np.sqrt(sum(r["totals"]["squared"] for r in folds) / n)),
                  "pooled_wape_percent": 100 * sum(r["totals"]["absolute"] for r in folds)
                  / sum(r["totals"]["actual"] for r in folds)}
        for key in ("primary_score", "pooled_rmse", "pooled_wape_percent"):
            same(result[key], case[key])
        trial_results.append(result)
    final = []
    bundle, frozen = read(P4 / "sealed_predictions.json"), read(P4 / "frozen_selection.json")
    evaluation = read(P4 / "final_evaluation.json")
    for dataset in ("store_item", "m5"):
        metadata = pd.read_parquet(ROOT / f"reports/eda/tables/{dataset}/series.parquet")
        metadata = metadata.sort_values("series_id").reset_index(drop=True)
        origin = frozen["datasets"][dataset]["origin"]
        manifest = read(P4 / f"final_actuals/{dataset}.json")
        path = P4 / manifest["path"]
        expected = manifest["sha256"]
        assert digest(path) == expected
        ledger_lines = (P4 / "holdout_access.jsonl").read_text().splitlines()
        events = [json.loads(line) for line in ledger_lines]
        assert sum(e["event"] == "canonical_targets_read_completed" and e["dataset"] == dataset
                   and e["details"]["actual_sha256"] == expected for e in events) == 1
        access = {"timestamp_utc": datetime.now(UTC).isoformat(),
                  "path": str(path.relative_to(ROOT)),
                  "sha256": expected, "purpose": "read_only_internal_audit_saved_snapshot",
                  "canonical_holdout_read": False}
        with (OUT / "saved_snapshot_audit_access.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(access) + "\n")
        actual_frame = pd.read_parquet(path)
        y, _, _ = aligned(actual_frame, metadata,
                          pd.Timestamp(origin) + pd.Timedelta(days=1), "actual")
        del actual_frame
        q = scales(dataset, origin, metadata)
        for forecast in bundle["forecasts"]:
            if forecast["dataset"] != dataset:
                continue
            p, flags, (calculated, per, totals) = check_prediction(
                P4 / forecast["files"]["predictions"]["path"], forecast, dataset, origin,
                metadata, y, q)
            saved_scales = np.load(P4 / forecast["files"]["independent_scales"]["path"])
            assert np.allclose(saved_scales, q, equal_nan=True, atol=1e-12, rtol=1e-12)
            entry = next(r for r in evaluation["results"] if r["run_id"] == forecast["run_id"])
            saved = read(P4 / entry["metrics"]["path"])
            compare(saved, calculated, per, metadata, y, p, q, flags)
            class_scores = {str(c): metrics(y[m], p[m], q[m], flags[0][m], flags[1][m])[0]
                            for c in metadata.pattern.unique()
                            for m in [metadata.pattern.eq(c).to_numpy()]}
            final.append({"trial_id": forecast["trial_id"], "dataset": dataset,
                          **calculated, "totals": totals, "by_demand_class": class_scores})
            del p, flags, saved, per
        assert digest(path) == expected
        print(dataset, "four saved final cases reconciled", flush=True)
    assert digest(P4 / "holdout_access.jsonl") == before
    output = {"status": "passed", "validation_runs": records, "trials": trial_results,
              "final": final, "seconds": time.perf_counter() - began,
              "peak_working_set_bytes": psutil.Process().memory_info().peak_wset,
              "original_ledger_sha256": before, "ledger_unchanged": True,
              "canonical_final_target_reads": 0, "research_fits": 0,
              "scope": "All 224 Phase3 plus108 Phase4 validation runs and8 saved final cases; "
              "seven metrics, per-series, horizon/class groups and coverage; "
              "training denominators independently computed from checksummed origin-only caches"}
    with (OUT / "independent_metrics.json").open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
        stream.write("\n")
    brief = {k: v for k, v in output.items() if k not in ("validation_runs", "trials", "final")}
    print(json.dumps(brief, indent=2), flush=True)


if __name__ == "__main__":
    main()
