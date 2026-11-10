"""Exclusive Phase 5 design freeze and explicit saved validation forecast sources."""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from intelligent_demand.experiments.registry import ExperimentRegistry
from intelligent_demand.inventory.design import load_design
from intelligent_demand.preservation.backup import sha256, write_new
from intelligent_demand.preservation.verify import SELECTION, identity

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts/inventory/phase5"
REPORTS = ROOT / "reports/inventory"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Phase 5 input/output must remain within configured project")
    return path.relative_to(ROOT).as_posix()


def file_record(path):
    return {"path": relative(path), "sha256": sha256(path), "bytes": Path(path).stat().st_size}


def plan():
    result = read(OUTPUT / "plan.json")
    unsigned = dict(result)
    expected = unsigned.pop("sha256")
    if identity(unsigned) != expected:
        raise ValueError("Phase 5 frozen plan changed")
    for item in result["design_files"]:
        if sha256(ROOT / item["path"]) != item["sha256"]:
            raise ValueError("Frozen inventory assumptions changed")
    return result


def freeze():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    if (OUTPUT / "plan.json").exists():
        return plan()
    config, scenarios = load_design(ROOT / "configs/inventory.yaml")
    frozen = read(ROOT / "artifacts/experiments/phase4/frozen_selection.json")
    if frozen["manifest_sha256"] != SELECTION:
        raise ValueError("Unexpected scientific model selection")
    preflight = read(ROOT / "artifacts/experiments/phase5_preflight_evidence_20261108.json")
    if preflight["status"] != "passed":
        raise ValueError("Protected evidence preflight required")
    board = read(ROOT / "artifacts/experiments/phase4/trial_leaderboard.json")
    phase4 = ROOT / "artifacts/experiments/phase4/registry"
    phase3 = ROOT / "artifacts/experiments/forecasting"
    cohorts = []
    for dataset in ("store_item", "m5"):
        metadata_path = ROOT / f"reports/eda/tables/{dataset}/series.parquet"
        metadata = pd.read_parquet(metadata_path).sort_values("series_id").reset_index(drop=True)
        sources = {}
        for label, trial in (("selected_ml", frozen["datasets"][dataset]["selected_trial_id"]),
                             ("seasonal_naive", f"{dataset}_seasonal_naive_reference"),
                             ("moving_average_28", f"{dataset}_moving_average_28_reference")):
            if dataset == "store_item" and label == "moving_average_28":
                cases = []
                registry = ExperimentRegistry(phase3)
                for path in phase3.glob("*/status.json"):
                    spec = read(path.parent / "specification.json")
                    if (spec["dataset_id"] == dataset and spec["series_count"] == 500
                            and spec["model"]["identifier"] == "moving_average_28"):
                        cases.append((spec["fold"]["number"], path.parent.name))
                if len(cases) != 4:
                    raise ValueError("Exactly four existing Store Item MA28 runs required")
                runs = [r for _, r in sorted(cases)]
            else:
                registry = ExperimentRegistry(phase4)
                runs = next(r["runs"] for r in board if r["trial_id"] == trial)
            sources[label] = []
            for run in runs:
                state = registry.completed(run)
                spec = state["specification"]
                if (spec["series_count"] != len(metadata)
                        or spec["series_sha256"] != identity(list(metadata.series_id))):
                    raise ValueError("Full matched source population required")
                predictions = registry.directory(run) / state["outputs"]["predictions"]["path"]
                sources[label].append({"run_id": run, "model": spec["model"]["identifier"],
                                       "fold": spec["fold"], "specification": file_record(
                                           registry.directory(run) / "specification.json"),
                                       "predictions": file_record(predictions)})
        for i in range(4):
            fold = sources["selected_ml"][i]["fold"]
            matching = {label: records[i] for label, records in sources.items()}
            if any(r["fold"] != fold for r in matching.values()):
                raise ValueError("Forecast models use different origins/windows")
            cache_matches = []
            for path in (ROOT / "artifacts/experiments/phase3/cache").glob("*/complete.json"):
                cached = read(path)
                if (cached["contract"]["dataset"] != dataset
                        or cached["contract"]["origin"] != fold["origin"]):
                    continue
                array = np.load(path.parent / cached["values"], mmap_mode="r")
                if len(array) == len(metadata):
                    cache_matches.append(file_record(path))
                del array
            if len(cache_matches) != 1:
                raise ValueError("One pre-origin full-population training cache required")
            top = metadata.sort_values(["sales_units", "series_id"], ascending=[False, True])
            representatives = sorted(set([str(metadata.series_id.iloc[k]) for k in
                                          (0, len(metadata) // 2, len(metadata) - 1)]
                                         + list(top.series_id.iloc[:3])))
            cohorts.append({"dataset": dataset, "fold": fold, "series": len(metadata),
                            "metadata": file_record(metadata_path), "sources": matching,
                            "training_cache": cache_matches[0], "representatives": representatives})
    files = ["configs/inventory.yaml", "src/intelligent_demand/inventory/design.py",
             "docs/INVENTORY_SIMULATION_PROTOCOL.md", "docs/INVENTORY_POLICY_MATHEMATICS.md",
             "docs/PHASE5_ASSUMPTIONS.md", "docs/CLAUDE_FOCUSED_FORECASTING_GATE.md"]
    record = {"schema_version": 1, "selection_sha256": SELECTION,
              "source_sha256": frozen["source_sha256"], "cohorts": cohorts,
              "scenarios": [s.metadata() for s in scenarios], "settings": config,
              "design_files": [file_record(ROOT / name) for name in files],
              "final_holdout_used": False, "forecast_cadence": "one fixed H28 per origin",
              "purpose": "Hypothetical validation-reused inventory comparisons"}
    record["sha256"] = identity(record)
    write_new(OUTPUT / "plan.json", record)
    write_new(REPORTS / "phase5a_gate.json", {"status": "passed", "plan_sha256": record["sha256"],
              "scenarios": len(scenarios), "cohorts": len(cohorts), "policies": 4,
              "design_tests": 12, "source_forecasts": 24, "final_holdout_used": False,
              "mathematics_review": "Explicit EOD offset L+1 yields protection L+R; common cutoff"})
    print(json.dumps({"status": "passed", "plan_sha256": record["sha256"],
                      "scenarios": len(scenarios), "cohorts": len(cohorts)}, indent=2))
    return record


if __name__ == "__main__":
    os.chdir(ROOT)
    freeze()
