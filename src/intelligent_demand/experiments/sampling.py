"""Training-only stratified statistical benchmark selection, frozen before its fits."""

import json

import numpy as np
import pandas as pd

from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.registry import atomic_json, file_digest


def choose_statistical_subset(metadata, dataset, seed=42):
    frame = metadata.sort_values("series_id").reset_index(drop=True).copy()
    if frame.empty or frame.series_id.duplicated().any() or frame.sales_units.isna().any():
        raise ValueError("Unique, labelled training-only descriptors required")
    frame["volume_band"] = pd.qcut(
        frame.sales_units.rank(method="first"), 3, labels=["low", "middle", "high"]
    )
    rng, selected = np.random.default_rng(seed), set()
    for _, group in frame.groupby(["pattern", "store_id"], sort=True, observed=True):
        selected.add(int(rng.choice(group.index)))
    fields = ["volume_band", "cat_id", "dept_id", "state_id"]
    if dataset == "store_item":
        fields.append("item_id")
    # Guarantee marginal group representation in addition to primary cross-strata.
    for field in fields:
        if field not in frame:
            continue
        for _, group in frame.groupby(field, sort=True, observed=True):
            if selected.isdisjoint(group.index):
                selected.add(int(rng.choice(group.index)))
    result = frame.iloc[sorted(selected)].copy()
    return result.sort_values("series_id").reset_index(drop=True)


def frozen_statistical_subset(root, output, metadata, dataset, initial_origin):
    path = output / f"{dataset}_statistical_subset.json"
    metadata_path = root / f"reports/eda/tables/{dataset}/series.parquet"
    selected = choose_statistical_subset(metadata, dataset)
    ids = list(selected.series_id)
    record = {
        "dataset": dataset,
        "seed": 42,
        "initial_training_end": str(initial_origin),
        "source_metadata_sha256": file_digest(metadata_path),
        "selection": "seeded pattern/store sampling plus missing volume/hierarchy marginals",
        "series_sha256": identity(ids),
        "series_count": len(ids),
        "series_ids": ids,
        "descriptors": selected[
            [
                c
                for c in (
                    "series_id",
                    "pattern",
                    "store_id",
                    "item_id",
                    "volume_band",
                    "cat_id",
                    "dept_id",
                    "state_id",
                )
                if c in selected
            ]
        ]
        .astype(str)
        .to_dict(orient="records"),
    }
    if path.exists():
        if json.loads(path.read_text()) != record:
            raise ValueError("Frozen statistical selection changed; do not silently resample")
    else:
        output.mkdir(parents=True, exist_ok=True)
        atomic_json(path, record)
    return metadata.set_index("series_id").loc[ids].reset_index()
