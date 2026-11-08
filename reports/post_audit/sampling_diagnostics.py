"""Descriptive fixed-sample diagnostics; final outcome files are never opened."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from intelligent_demand.preservation.backup import sha256
from intelligent_demand.preservation.paths import EvidenceResolver
from intelligent_demand.preservation.verify import identity

ROOT = Path(__file__).resolve().parents[2]
P4 = ROOT / "artifacts/experiments/phase4"
resolver = EvidenceResolver(ROOT, ROOT)


def read(path):
    return json.loads(Path(path).read_text())


meta = pd.read_parquet(ROOT / "reports/eda/tables/m5/series.parquet")
meta = meta.sort_values("series_id").reset_index(drop=True)
board = read(P4 / "trial_leaderboard.json")
rf = next(c for c in board if c["trial_id"] == "m5_random_forest_02")
ma = next(c for c in board if c["trial_id"] == "m5_moving_average_28_reference")
bundle = read(P4 / "sealed_predictions.json")
selected = next(c for c in bundle["forecasts"] if c["trial_id"] == "m5_random_forest_02")
records = []
cases = [(str(i + 1), P4 / "registry" / run, None) for i, run in enumerate(rf["runs"])]
cases.append(("final_training_only", P4, selected))
for fold, directory, forecast in cases:
    if forecast:
        spec = forecast["specification"]
        metadata_path = P4 / forecast["files"]["model_metadata"]["path"]
    else:
        spec = read(directory / "specification.json")
        state = read(directory / "status.json")
        metadata_path = directory / state["outputs"]["model_metadata"]["path"]
    contract = read(metadata_path)[0]["feature_cache_contract"]
    cache = resolver.resolve(spec["model_configuration"]["feature_cache"]) / identity(contract)
    complete = read(cache / "complete.json")
    for name, digest in complete["files"].items():
        assert sha256(cache / name) == digest
    labels = np.load(cache / complete["names"]["labels"], mmap_mode="r").reshape(len(meta), 6)
    positions = np.load(cache / complete["names"]["positions"], mmap_mode="r")
    zero_only = (labels == 0).all(axis=1)
    profile = meta.assign(all_sampled_zero=zero_only, positive_labels=(labels > 0).sum(axis=1))
    positive_distribution = profile.positive_labels.value_counts().sort_index()
    record = {"fold": fold, "origin": spec["fold"]["origin"], "labels": int(labels.size),
              "all_sampled_labels_zero_series": int(zero_only.sum()),
              "all_sampled_zero_with_initial_positive_history": int(
                  (zero_only & meta.sales_units.gt(0).to_numpy()).sum()),
              "positive_label_count_distribution": {
                  str(int(k)): int(v) for k, v in positive_distribution.items()
              },
              "zero_labels": int((labels == 0).sum()),
              "positive_labels": int((labels > 0).sum()), "coverage": {},
              "sampled_time_index_min": int(positions[:, 1].min()),
              "sampled_time_index_max": int(positions[:, 1].max()),
              "seed": spec["random_seed"]}
    for field in ("store_id", "item_id", "dept_id", "cat_id", "state_id", "pattern"):
        if field not in profile:
            continue
        grouped = profile.groupby(field, sort=True).agg(
            series=("series_id", "size"), all_sampled_zero=("all_sampled_zero", "sum"),
            positive_labels=("positive_labels", "sum"))
        record["coverage"][field] = {
            "groups": len(grouped),
            "groups_with_positive_labels": int(grouped.positive_labels.gt(0).sum()),
            "series_count_min": int(grouped.series.min()),
            "series_count_max": int(grouped.series.max())}
        if field != "item_id":
            record["coverage"][field]["details"] = grouped.reset_index().to_dict(orient="records")
    if not forecast:
        index = int(fold) - 1
        rf_state = read(directory / "status.json")
        other = P4 / "registry" / ma["runs"][index]
        ma_state = read(other / "status.json")
        errors = []
        for folder, status in ((directory, rf_state), (other, ma_state)):
            result = read(folder / status["outputs"]["metrics"]["path"])
            table = pd.DataFrame(result["all"]["per_series"]).set_index("series_id")
            table = table.loc[meta.series_id]
            errors.append(table.mae.to_numpy())
        record["validation_only_error_comparison"] = {}
        for name, mask in (("all_sampled_zero", zero_only), ("sampled_positive", ~zero_only)):
            rf_mean, ma_mean = (float(e[mask].mean()) for e in errors)
            record["validation_only_error_comparison"][name] = {
                "series": int(mask.sum()), "rf_macro_mae": rf_mean, "ma28_macro_mae": ma_mean,
                "rf_minus_ma28_mae": rf_mean - ma_mean,
                "rf_lower_mae_series": int((errors[0][mask] < errors[1][mask]).sum())}
    records.append(record)
output = {"status": "passed", "final_outcomes_used": False, "training_samples_modified": False,
          "model_refits": 0, "records": records,
          "interpretation": "Complete membership is not complete positive-label supervision. "
          "Subgroup errors are descriptive validation diagnostics, "
          "not a replacement sampling search."}
with (ROOT / "reports/post_audit/sampling_diagnostics.json").open("x", encoding="utf-8") as stream:
    json.dump(output, stream, indent=2)
    stream.write("\n")
print(json.dumps([{k: r[k] for k in ("fold", "labels", "all_sampled_labels_zero_series")}
                  for r in records], indent=2))
