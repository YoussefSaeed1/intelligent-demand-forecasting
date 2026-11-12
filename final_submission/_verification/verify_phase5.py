"""Independent read-only recomputation of Phase 5 base results from persisted per-series outputs (no holdout)."""

import collections
import glob
import json
import os

import pyarrow.parquet as pq

root = "artifacts/inventory/phase5/runs"
cases = [json.load(open(p)) for p in glob.glob(f"{root}/*/status.json")]
done = [c for c in cases if c["status"] == "completed"]
print("cases", len(cases), "completed", len(done), "series-episodes", sum(c["series"] for c in done))
print("scenarios", len({c["scenario"]["identifier"] for c in done}))
agg = collections.defaultdict(lambda: collections.Counter())
for c in done:
    if c["scenario"]["identifier"] != "base":
        continue
    f = c["files"]
    sp = f.get("series") or f.get("series_parquet")
    path = os.path.join(root, c["case_id"], sp["path"]) if isinstance(sp, dict) else None
    if path is None or not os.path.exists(path):
        path = sorted(glob.glob(f"{root}/{c['case_id']}/attempts/*/series.parquet"))[-1]
    t = pq.read_table(path, columns=["total_cost", "fulfilled_units", "demand_units", "average_on_hand", "stockout_days"]).to_pydict()
    for k in ("total_cost", "fulfilled_units", "demand_units", "average_on_hand", "stockout_days"):
        agg[(c["dataset"], c["policy"], c["fold"]["number"])][k] += sum(t[k])
    agg[(c["dataset"], c["policy"], c["fold"]["number"])]["n"] += len(t["total_cost"])
ref = json.load(open("reports/inventory/post_audit_reconciliation.json"))
worst = 0.0
out = {}
for ds in ("store_item", "m5"):
    for pol in ("selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point"):
        tot = collections.Counter()
        for fold in (1, 2, 3, 4):
            a = agg[(ds, pol, fold)]
            tot.update(a)
            out[f"{ds}/{pol}/origin{fold}"] = a["total_cost"] / a["n"]
        mean_cost = tot["total_cost"] / tot["n"]
        fill = tot["fulfilled_units"] / tot["demand_units"]
        r = ref["base_pooled"][ds][pol]
        d = max(abs(mean_cost - r["mean_cost"]) / abs(r["mean_cost"]), abs(fill - r["pooled_fill_rate"]))
        worst = max(worst, d)
        print(
            f"{ds:10s} {pol:20s} n={tot['n']:7d} mean_cost={mean_cost:12.6f} ref={r['mean_cost']:12.6f} "
            f"fill={100 * fill:8.4f}% ref={100 * r['pooled_fill_rate']:8.4f}%"
        )
print("max relative/absolute discrepancy vs saved reconciliation:", worst)
for ds in ("store_item", "m5"):
    print(
        ds,
        "ML-MA28 by origin:",
        [round(out[f"{ds}/selected_ml/origin{o}"] - out[f"{ds}/moving_average_28/origin{o}"], 2) for o in (1, 2, 3, 4)],
        "ML-SN:",
        [round(out[f"{ds}/selected_ml/origin{o}"] - out[f"{ds}/seasonal_naive/origin{o}"], 2) for o in (1, 2, 3, 4)],
    )
