"""Independently inspect saved training positions/labels/schema; never decode final targets."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from intelligent_demand.experiments.config import identity

ROOT = Path(__file__).resolve().parents[3]
DEST = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def contracts():
    references, all_runs = {}, 0
    for phase, registry in [
        ("3", ROOT / "artifacts/experiments/forecasting"),
        ("4", ROOT / "artifacts/experiments/phase4/registry"),
    ]:
        for path in registry.glob("*/specification.json"):
            spec = read(path)
            if spec.get("model", {}).get("identifier") not in ["lightgbm", "random_forest"]:
                continue
            if "derived_from" in spec:
                continue
            all_runs += 1
            state = read(path.parent / "status.json")
            meta = read(path.parent / state["outputs"]["model_metadata"]["path"])[0]
            cache = Path(spec["model_configuration"]["feature_cache"]) / identity(
                meta["feature_cache_contract"]
            )
            schema_path = path.parent / state["outputs"]["model_0_feature_schema"]["path"]
            references[cache] = (phase, spec, schema_path)
    output = ROOT / "artifacts/experiments/phase4"
    for record in read(output / "sealed_predictions.json")["forecasts"]:
        if record["role"] != "selected":
            continue
        spec = record["specification"]
        meta = read(output / record["files"]["model_metadata"]["path"])[0]
        cache = Path(spec["model_configuration"]["feature_cache"]) / identity(
            meta["feature_cache_contract"]
        )
        references[cache] = (
            "final_training", spec, output / record["files"]["model_0_feature_schema"]["path"]
        )
    return all_runs, references


def audit():
    all_runs, references = contracts()
    results = []
    for cache, (phase, spec, schema_path) in references.items():
        manifest = read(cache / "complete.json")
        for name, digest in manifest["files"].items():
            with (cache / name).open("rb") as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest() == digest
        positions = np.load(cache / manifest["names"]["positions"], mmap_mode="r")
        labels = np.load(cache / manifest["names"]["labels"], mmap_mode="r")
        features = np.load(cache / manifest["names"]["features"], mmap_mode="r")
        metadata = pd.read_parquet(
            ROOT / f"reports/eda/tables/{spec['dataset_id']}/series.parquet"
        ).sort_values("series_id").reset_index(drop=True)
        series = len(metadata)
        start = np.datetime64(spec["fold"]["train_start"])
        origin = np.datetime64(spec["fold"]["origin"])
        periods = int((origin - start) / np.timedelta64(1, "D")) + 1
        per = min(periods - 56, spec["model_configuration"]["maximum_training_rows"] // series)
        boundaries = np.linspace(56, periods, per + 1, dtype=int)
        expected = np.random.default_rng(spec["random_seed"]).integers(
            boundaries[:-1], boundaries[1:], size=(series, per)
        )
        assert np.array_equal(positions[:, 0], np.repeat(np.arange(series), per))
        assert np.array_equal(positions[:, 1], expected.ravel())
        assert positions[:, 1].min() >= 56 and positions[:, 1].max() < periods
        assert len(labels) == series * per and (labels >= 0).all()
        schema = read(schema_path)
        price_features = [name for name in schema["feature_names"] if "price" in name]
        assert not any(
            token in name.lower() for name in schema["feature_names"]
            for token in ["snap", "event", "future", "target", "actual"]
        )
        if phase != "3":
            assert not price_features
        all_zero = (np.asarray(labels).reshape(series, per) == 0).all(axis=1)
        results.append({
            "phase": phase, "dataset": spec["dataset_id"], "origin": str(origin),
            "sampled_labels": len(labels), "labels_per_series": per, "series": series,
            "zero_labels": int((labels == 0).sum()), "negative_labels": 0,
            "all_sampled_labels_zero_series": int(all_zero.sum()),
            "all_sampled_labels_zero_with_initial_positive_history": int(
                (all_zero & (metadata.sales_units > 0)).sum()
            ),
            "all_sampled_labels_zero_by_initial_class": {
                str(key): int(value)
                for key, value in metadata.loc[all_zero, "pattern"].value_counts().items()
            },
            "stores": int(metadata.store_id.nunique()),
            "products": int(metadata.item_id.nunique()),
            "classes": {str(k): int(v) for k, v in metadata.pattern.value_counts().items()},
            "earliest_label": str(start + np.timedelta64(int(positions[:, 1].min()), "D")),
            "latest_label": str(start + np.timedelta64(int(positions[:, 1].max()), "D")),
            "feature_count": features.shape[1], "price_features": price_features,
            "seeded_positions_reproduced": True,
        })
    record = {
        "validation_run_references": all_runs, "unique_validation_training_caches": 16,
        "final_training_caches": 2, "canonical_holdout_reads": 0,
        "real_model_fits": 0, "sampling": results,
    }
    path = DEST / "sampling_verification.json"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "passed", "validation_run_references": all_runs,
                      "unique_caches_verified": len(results)}))


if __name__ == "__main__":
    audit()
