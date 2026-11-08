"""Read selected estimator structure only; do not call predict, fit or access targets."""

import hashlib
import json
from pathlib import Path

import joblib
import lightgbm as lgb

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts/experiments/phase4"


def audit():
    records = json.loads((OUTPUT / "sealed_predictions.json").read_text())["forecasts"]
    results = []
    for record in records:
        if record["role"] != "selected":
            continue
        item = record["files"]["model_0_estimator"]
        path = OUTPUT / item["path"]
        with path.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == item["sha256"]
        schema_path = OUTPUT / record["files"]["model_0_feature_schema"]["path"]
        schema = json.loads(schema_path.read_text())
        if record["model"] == "random_forest":
            model = joblib.load(path)
            actual = {
                "n_features": model.n_features_in_, "trees": len(model.estimators_),
                "max_depth": model.max_depth, "min_leaf": model.min_samples_leaf,
                "min_split": model.min_samples_split, "max_features": model.max_features,
                "seed": model.random_state, "prediction_threads": model.n_jobs,
            }
            assert model.n_features_in_ == len(schema["feature_names"]) == 30
            assert len(model.estimators_) == 160 and model.max_depth == 16
            assert model.min_samples_leaf == 20 and model.min_samples_split == 20
            assert max(max(tree.tree_.feature) for tree in model.estimators_) < 30
        else:
            model = lgb.Booster(model_file=str(path))
            actual = {"n_features": model.num_feature(), "trees": model.num_trees(),
                      "current_iteration": model.current_iteration()}
            assert model.num_feature() == len(schema["feature_names"]) == 27
            assert model.num_trees() == 200
            assert model.feature_name() == schema["feature_names"]
        assert not any(token in name for name in schema["feature_names"]
                       for token in ["price", "snap", "event"])
        results.append({
            "dataset": record["dataset"], "model": record["model"],
            "trial_id": record["trial_id"], "actual_saved_estimator": actual,
            "schema_features": schema["feature_names"], "prediction_calls": 0,
            "real_fits": 0, "sha256_verified": True,
        })
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    audit()
