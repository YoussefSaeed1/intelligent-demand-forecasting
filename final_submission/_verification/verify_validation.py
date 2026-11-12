"""Independent recomputation of Phase 4 validation macro MAE from saved validation predictions and canonical sales.
Reads ONLY validation-window dates (strictly before each dataset's final holdout start). No model code is used."""

import datetime as dt
import json

import numpy as np
import pyarrow.parquet as pq

HOLDOUT = {"store_item": dt.date(2017, 12, 4), "m5": dt.date(2016, 4, 25)}
PUB = {
    "store_item_lightgbm_00": 6.308039821969917,
    "store_item_seasonal_naive_reference": 9.154964285714286,
    "m5_random_forest_02": 1.0200669850841517,
    "m5_moving_average_28_reference": 1.0337792250386544,
}


def run_dir(case, fold):
    rid = json.load(open(f"artifacts/experiments/phase4/jobs/{case}_f{fold}.json"))["run_id"]
    st = json.load(open(f"artifacts/experiments/phase4/registry/{rid}/status.json"))
    return f"artifacts/experiments/phase4/registry/{rid}/attempts/{st['attempt_id']}/predictions.parquet"


actual_cache = {}
for case, published in PUB.items():
    ds = "store_item" if case.startswith("store_item") else "m5"
    fold_mae = []
    for fold in (1, 2, 3, 4):
        p = pq.read_table(run_dir(case, fold))
        if fold == 1 and case not in actual_cache:
            print(case, "prediction columns:", p.schema.names)
        cols = p.schema.names
        dcol = "date" if "date" in cols else [c for c in cols if "date" in c][0]
        pcol = [c for c in ("prediction", "forecast", "yhat", "value") if c in cols][0]
        dates = p.column(dcol).to_pylist()
        lo, hi = min(dates), max(dates)
        assert hi < HOLDOUT[ds], ("holdout date in validation predictions", hi)
        key = (ds, lo, hi)
        if key not in actual_cache:
            a = pq.read_table(
                f"data/processed/{ds}/daily_sales.parquet",
                columns=["series_id", "date", "sales_units"],
                filters=[("date", ">=", lo), ("date", "<=", hi)],
            )
            actual_cache[key] = {
                (s, d): y
                for s, d, y in zip(
                    a.column("series_id").to_pylist(), a.column("date").to_pylist(), a.column("sales_units").to_pylist(), strict=True
                )
            }
        act = actual_cache[key]
        err = {}
        for s, d, y in zip(p.column("series_id").to_pylist(), dates, p.column(pcol).to_pylist(), strict=True):
            err.setdefault(s, []).append(abs(y - act[(s, d)]))
        assert all(len(v) == 28 for v in err.values())
        fold_mae.append(np.mean([np.mean(v) for v in err.values()]))
    mae = float(np.mean(fold_mae))
    print(
        f"{case:42s} series={len(err):6d} folds={[round(x, 6) for x in fold_mae]} mean={mae:.12f} "
        f"published={published:.12f} rel_diff={abs(mae - published) / published:.2e}"
    )
