"""Immutable Phase 4 search contract; deterministic manifests before any optimisation."""

import copy
import json
import os
import uuid
from itertools import product
from pathlib import Path

import numpy as np
import yaml

from intelligent_demand.experiments.benchmark import ROOT, verify_sources
from intelligent_demand.experiments.config import canonical_json, identity
from intelligent_demand.experiments.engine import provenance
from intelligent_demand.experiments.registry import file_digest, utc_now

OUTPUT = ROOT / "artifacts/experiments/phase4"
REPORTS = ROOT / "reports/forecasting"
BASE_REVISION = "6e1a407de0b676e858ffec43bab1fae8d51dae1d"


def publish_once(path, record):
    """Exclusive atomic creation. Never replace a frozen plan or sealed assessment."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_json(record) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_settings(path=None):
    data = yaml.safe_load(
        (ROOT / "configs/phase4.yaml" if path is None else Path(path)).read_text()
    )
    expected = {
        "schema_version",
        "seed",
        "search",
        "primary_metric",
        "folds",
        "horizon",
        "price_features",
        "training_rows",
        "resources",
        "trial_counts",
        "references",
        "spaces",
        "selection",
    }
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("Phase 4 settings require the exact declared schema")
    if (
        data["schema_version"] != 1
        or type(data["seed"]) is not int
        or data["seed"] != 42
        or data["horizon"] != 28
        or data["folds"] != [1, 2, 3, 4]
        or data["price_features"] is not False
        or data["primary_metric"] != "mean_four_origin_macro_mae"
        or data["search"] != "seeded_random_without_replacement_plus_anchor"
    ):
        raise ValueError("Phase 4 scientific contract differs from the approved task")
    resources = data["resources"]
    if (
        set(resources)
        != {
            "threads",
            "concurrent_workers",
            "worker_rss_mib",
            "minimum_available_mib",
            "minimum_free_disk_gib",
            "worker_timeout_seconds",
            "search_wall_seconds",
            "maximum_attempts_per_fold",
        }
        or any(type(v) is not int or v < 1 for v in resources.values())
        or resources["threads"] > 4
        or resources["concurrent_workers"] != 1
        or resources["worker_rss_mib"] > 2048
        or resources["maximum_attempts_per_fold"] > 2
    ):
        raise ValueError("Invalid sequential resource budget")
    if data["training_rows"] != {"store_item": 150000, "m5": 183000}:
        raise ValueError("Training-sample design must not change during search")
    required = {
        "store_item": {"lightgbm", "random_forest", "holt_winters_additive"},
        "m5": {"random_forest", "tsb", "lightgbm"},
    }
    if set(data["trial_counts"]) != set(required) or set(data["spaces"]) != set().union(
        *required.values()
    ):
        raise ValueError("Unknown or missing candidate family")
    if data["references"] != {
        "store_item": ["seasonal_naive", "seasonal_moving_average"],
        "m5": ["seasonal_naive", "moving_average_28"],
    }:
        raise ValueError("Mandatory references are fixed")
    for dataset, families in required.items():
        if set(data["trial_counts"][dataset]) != families:
            raise ValueError("Candidate inclusion differs from the declared shortlist")
        for method, count in data["trial_counts"][dataset].items():
            if type(count) is not int or not 2 <= count <= 30:
                raise ValueError("Trial budgets must be explicit integers between 2 and 30")
            if any(
                not isinstance(v, list) or not v or len(set(v)) != len(v)
                for v in data["spaces"][method].values()
            ):
                raise ValueError("Search axes must be nonempty unique lists")
    space_keys = {
        "lightgbm": {
            "num_leaves",
            "max_depth",
            "learning_rate",
            "num_boost_round",
            "min_data_in_leaf",
            "feature_fraction",
            "bagging_fraction",
            "lambda_l1",
            "lambda_l2",
        },
        "random_forest": {
            "n_estimators",
            "max_depth",
            "min_samples_leaf",
            "max_features",
            "min_samples_split",
        },
        "holt_winters_additive": {"alpha", "trend_beta", "seasonal_gamma", "damping_phi"},
        "tsb": {"alpha", "occurrence_beta"},
    }
    for method, axes in data["spaces"].items():
        if set(axes) != space_keys[method]:
            raise ValueError("Unexpected hyperparameter axis")
        for key, values in axes.items():
            for value in values:
                parameters_for(method, {key: value})
    selection = data["selection"]
    if (
        set(selection)
        != {
            "objective_tie_tolerance",
            "tie_order",
            "minimum_complete_tuning_trials_per_family",
            "final_comparators",
        }
        or set(selection["tie_order"])
        != set().union(
            *required.values(), {"moving_average_28", "seasonal_naive", "seasonal_moving_average"}
        )
        or len(selection["tie_order"]) != 7
        or type(selection["objective_tie_tolerance"]) is not float
        or not 0 <= selection["objective_tie_tolerance"] <= 1e-12
        or selection["minimum_complete_tuning_trials_per_family"] != 2
        or selection["final_comparators"]
        != {
            "store_item": [
                "seasonal_naive",
                "seasonal_moving_average",
                "best_holt_winters_additive",
            ],
            "m5": ["seasonal_naive", "moving_average_28", "best_tsb", "best_random_forest"],
        }
    ):
        raise ValueError("Invalid predeclared selection or final comparator policy")
    return data


def parameters_for(method, overrides=None):
    path = "ml.yaml" if method in ("random_forest", "lightgbm") else "statistical.yaml"
    parameters = yaml.safe_load((ROOT / "configs" / path).read_text())
    if method in ("random_forest", "lightgbm"):
        parameters["use_historical_prices"] = False
        target = parameters[method]
        if method == "random_forest":
            target["min_samples_split"] = 2
        else:
            target.update(
                max_depth=-1,
                feature_fraction=1.0,
                bagging_fraction=1.0,
                lambda_l1=0.0,
                lambda_l2=0.0,
            )
        target.update(overrides or {})
        if method == "lightgbm":
            target["bagging_freq"] = 1 if target.get("bagging_fraction", 1) < 1 else 0
    else:
        parameters.update(overrides or {})
    validate_parameters(method, parameters)
    return parameters


def validate_parameters(method, p):
    if method == "random_forest":
        r = p[method]
        if any(
            type(r[k]) is not int
            for k in (
                "n_estimators",
                "max_depth",
                "min_samples_leaf",
                "min_samples_split",
                "max_leaf_nodes",
            )
        ):
            raise ValueError("RF size/split parameters must be integers")
        if (
            p.get("use_historical_prices") is not False
            or type(r["n_estimators"]) is not int
            or not 1 <= r["n_estimators"] <= 160
            or type(r["max_depth"]) is not int
            or not 1 <= r["max_depth"] <= 16
            or not 1 <= r["min_samples_leaf"] <= 100
            or not 2 <= r.get("min_samples_split", 2) <= 100
            or not 0 < r["max_features"] <= 1
            or r["max_leaf_nodes"] > 512
        ):
            raise ValueError("RF parameters exceed the declared bounded search")
    elif method == "lightgbm":
        r = p[method]
        if any(
            type(r[k]) is not int
            for k in (
                "num_leaves",
                "max_depth",
                "num_boost_round",
                "min_data_in_leaf",
                "bagging_freq",
            )
        ):
            raise ValueError("LightGBM size parameters must be integers")
        if (
            p.get("use_historical_prices") is not False
            or not 1 <= r["num_leaves"] <= 63
            or r.get("max_depth", -1) not in (-1, 8, 12)
            or not 0 < r["learning_rate"] <= 0.1
            or not 1 <= r["num_boost_round"] <= 300
            or not 20 <= r["min_data_in_leaf"] <= 100
            or not 0 < r.get("feature_fraction", 1) <= 1
            or not 0 < r.get("bagging_fraction", 1) <= 1
            or r.get("bagging_freq", 0) != (1 if r.get("bagging_fraction", 1) < 1 else 0)
            or not 0 <= r.get("lambda_l1", 0) <= 0.1
            or not 0 <= r.get("lambda_l2", 0) <= 5
            or r["device_type"] != "cpu"
            or r["deterministic"] is not True
        ):
            raise ValueError("LightGBM parameters exceed the declared safe CPU search")
    elif method in ("tsb", "holt_winters_additive"):
        if not (
            0 < p["alpha"] < 1
            and 0 <= p["trend_beta"] <= p["alpha"]
            and 0 <= p["seasonal_gamma"] <= 1 - p["alpha"]
            and 0 < p["damping_phi"] <= 1
            and 0 < p["occurrence_beta"] < 1
            and p["season"] == 7
        ):
            raise ValueError("Invalid fixed statistical candidate")
    else:
        raise ValueError("Unknown tuning family")


def build_trials(settings):
    trials = []
    rng = np.random.default_rng(settings["seed"])
    for dataset in ("store_item", "m5"):
        families = settings["trial_counts"][dataset]
        for method in sorted(families):
            count = families[method]
            space = settings["spaces"][method]
            keys = sorted(space)
            candidates = [
                dict(zip(keys, v, strict=True)) for v in product(*(space[k] for k in keys))
            ]
            anchor = parameters_for(method)
            chosen = [anchor]
            for i in rng.permutation(len(candidates)):
                candidate = parameters_for(method, candidates[int(i)])
                if identity(candidate) not in {identity(p) for p in chosen}:
                    chosen.append(candidate)
                if len(chosen) == count:
                    break
            if len(chosen) != count:
                raise ValueError("Search budget exceeds unique candidate space")
            for number, parameters in enumerate(chosen):
                trials.append(
                    {
                        "trial_id": f"{dataset}_{method}_{number:02d}",
                        "dataset": dataset,
                        "model": method,
                        "kind": "tuning",
                        "parameters": parameters,
                        "configuration_sha256": identity(parameters),
                        "seed": settings["seed"],
                    }
                )
        for method in settings["references"][dataset]:
            trials.append(
                {
                    "trial_id": f"{dataset}_{method}_reference",
                    "dataset": dataset,
                    "model": method,
                    "kind": "reference",
                    "parameters": {},
                    "configuration_sha256": identity({}),
                    "seed": settings["seed"],
                }
            )
    return trials


def freeze_plan():
    settings = load_settings()
    target = OUTPUT / "plan.json"
    if target.exists():
        return load_plan()
    doc = {
        "schema_version": 1,
        "phase": "4a",
        "created_at": utc_now(),
        "settings": settings,
        "settings_sha256": file_digest(ROOT / "configs/phase4.yaml"),
        "trials": build_trials(settings),
        "source_sha256": verify_sources(),
        "metadata_sha256": {
            dataset: file_digest(ROOT / f"reports/eda/tables/{dataset}/series.parquet")
            for dataset in ("store_item", "m5")
        },
        "split_sha256": file_digest(ROOT / "reports/eda/proposed_splits.json"),
        "protocol_sha256": file_digest(ROOT / "docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md"),
        "base_revision": BASE_REVISION,
        "code": provenance(ROOT),
        "holdout_targets_accessed": False,
    }
    doc["contract_sha256"] = identity(doc)
    publish_once(target, doc)
    return load_plan()


def load_plan():
    doc = json.loads((OUTPUT / "plan.json").read_text())
    unsigned = copy.deepcopy(doc)
    digest = unsigned.pop("contract_sha256")
    if (
        identity(unsigned) != digest
        or doc["settings"] != load_settings()
        or doc["settings_sha256"] != file_digest(ROOT / "configs/phase4.yaml")
        or doc["split_sha256"] != file_digest(ROOT / "reports/eda/proposed_splits.json")
        or doc["protocol_sha256"] != file_digest(ROOT / "docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md")
        or doc["trials"] != build_trials(doc["settings"])
        or any(
            file_digest(ROOT / f"reports/eda/tables/{dataset}/series.parquet") != digest
            for dataset, digest in doc["metadata_sha256"].items()
        )
    ):
        raise ValueError(
            "Frozen optimisation plan changed; no silent resampling or budget expansion"
        )
    return doc


def require_phase(phase):
    record = json.loads((REPORTS / f"phase{phase}_gate.json").read_text())
    plan = load_plan()
    if (
        record.get("status") != "passed"
        or record.get("plan_sha256") != plan["contract_sha256"]
        or not record.get("source_hashes_unchanged")
        or not record.get("quality_checks_passed")
    ):
        raise ValueError(f"Phase {phase} has not passed its scientific and technical gates")
    return record
