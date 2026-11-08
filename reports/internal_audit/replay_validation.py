"""Sampled saved-estimator replay on validation windows only; no fits or final replay."""

import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from intelligent_demand.features.recursive import FeatureEncoder, observed_context

ROOT = Path(__file__).resolve().parents[2]
P4 = ROOT / "artifacts/experiments/phase4"


def read(path):
    return json.loads(Path(path).read_text())


results = []
for dataset, case_id, sample in (("store_item", "store_item_lightgbm_00", 500),
                                 ("m5", "m5_random_forest_02", 128)):
    case = next(r for r in read(P4 / "trial_leaderboard.json") if r["trial_id"] == case_id)
    directory = P4 / "registry" / case["runs"][0]
    status, spec = read(directory / "status.json"), read(directory / "specification.json")
    fold, outputs = spec["fold"], status["outputs"]
    metadata = pd.read_parquet(ROOT / f"reports/eda/tables/{dataset}/series.parquet")
    metadata = metadata.sort_values("series_id").reset_index(drop=True)
    chosen = np.linspace(0, len(metadata) - 1, sample, dtype=int)
    encoder = FeatureEncoder(metadata, dataset, fold["train_start"], False)
    schema = read(directory / outputs["model_0_feature_schema"]["path"])
    assert encoder.metadata() == schema
    candidates = []
    for path in (ROOT / "artifacts/experiments/phase3/cache").glob("*/complete.json"):
        saved = read(path)
        if saved["contract"]["dataset"] != dataset or saved["contract"]["origin"] != fold["origin"]:
            continue
        panel = np.load(path.parent / saved["values"], mmap_mode="r")
        if len(panel) == len(metadata):
            candidates.append(panel)
    assert len(candidates) == 1
    history = candidates[0][chosen, -56:].astype(float).copy()
    observed = observed_context(history)
    static = encoder.static_codes(metadata)[chosen]
    path = directory / outputs["model_0_estimator"]["path"]
    estimator = lgb.Booster(model_file=str(path)) if dataset == "store_item" else joblib.load(path)
    replay = np.empty((sample, 28))
    for step in range(28):
        target = pd.Timestamp(fold["origin"]) + pd.Timedelta(days=step + 1)
        dates = pd.DatetimeIndex([target] * sample)
        matrix = encoder.matrix(history, dates, static, observed, None)
        replay[:, step] = (estimator.predict(matrix, num_threads=4) if dataset == "store_item"
                          else estimator.predict(matrix))
        history = np.column_stack((history[:, 1:], np.maximum(replay[:, step], 0)))
    persisted = pd.read_parquet(directory / outputs["predictions"]["path"])
    persisted = persisted[persisted.series_id.isin(metadata.series_id.iloc[chosen])]
    persisted = persisted.sort_values(["series_id", "target_date"])
    expected = persisted.raw_prediction.to_numpy().reshape(sample, 28)
    np.testing.assert_allclose(replay, expected, rtol=1e-12, atol=1e-12)
    results.append({"trial_id": case_id, "origin": fold["origin"], "series": sample,
                    "forecast_records": replay.size,
                    "maximum_absolute_difference": float(np.abs(replay - expected).max()),
                    "status": "passed", "research_refits": 0, "final_forecasts_regenerated": 0})
with (ROOT / "reports/internal_audit/prediction_replay.json").open("x", encoding="utf-8") as stream:
    json.dump(results, stream, indent=2)
    stream.write("\n")
print(json.dumps(results, indent=2))
