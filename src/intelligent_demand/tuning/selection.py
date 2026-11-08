"""Freeze exact validation-selected models and comparators before any final target access."""

import json
import os
import platform
import subprocess
import uuid
from importlib.metadata import version

from intelligent_demand.evaluation.splits import COVERAGE, load_splits
from intelligent_demand.experiments.benchmark import population, verify_sources
from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.registry import file_digest, utc_now
from intelligent_demand.features.recursive import FeatureEncoder
from intelligent_demand.tuning.authority import append_access, ledger_events, verify_frozen
from intelligent_demand.tuning.plan import (
    OUTPUT,
    REPORTS,
    ROOT,
    load_plan,
    publish_once,
    require_phase,
)


def environment_versions():
    return {
        "python": platform.python_version(),
        **{
            name: version(name)
            for name in (
                "numpy",
                "pandas",
                "pyarrow",
                "scikit-learn",
                "lightgbm",
                "statsmodels",
                "scipy",
            )
        },
    }


def choose(rows, settings):
    eligible = [r for r in rows if r["status"] == "completed"]
    if not eligible:
        raise ValueError("No completed comparable candidate")
    best = min(r["primary_score"] for r in eligible)
    tied = [r for r in eligible if r["primary_score"] <= best + settings["objective_tie_tolerance"]]
    return min(
        tied,
        key=lambda r: (
            settings["tie_order"].index(r["model"]),
            r["configuration_sha256"],
            r["trial_id"],
        ),
    )


def freeze_selection():
    if (OUTPUT / "frozen_selection.json").exists():
        return verify_frozen()
    if ledger_events():
        raise ValueError("Cannot create a selection after final targets were opened")
    gate = require_phase("4b")
    plan = load_plan()
    if verify_sources() != plan["source_sha256"]:
        raise ValueError("Source changed before model freeze")
    selection = plan["settings"]["selection"]
    datasets = {}
    splits = load_splits(ROOT / "reports/eda/proposed_splits.json")
    for dataset in ("store_item", "m5"):
        rows = [r for r in gate["trials"] if r["dataset"] == dataset]
        for family in plan["settings"]["trial_counts"][dataset]:
            completed = [
                r
                for r in rows
                if r["model"] == family and r["kind"] == "tuning" and r["status"] == "completed"
            ]
            if len(completed) < selection["minimum_complete_tuning_trials_per_family"]:
                raise ValueError("A required model family lacks comparable completed trials")
        winner = choose(rows, selection)
        cases = [winner]
        for comparator in selection["final_comparators"][dataset]:
            if comparator.startswith("best_"):
                method = comparator.removeprefix("best_")
                chosen = choose([r for r in rows if r["model"] == method], selection)
            else:
                chosen = next(
                    r for r in rows if r["kind"] == "reference" and r["model"] == comparator
                )
            if chosen["trial_id"] not in {r["trial_id"] for r in cases}:
                cases.append(chosen)
        metadata = population(dataset)
        start, end = COVERAGE[dataset]
        from datetime import timedelta

        origin = end - timedelta(days=28)
        evaluations = []
        for case in cases:
            evaluations.append(
                {
                    key: case[key]
                    for key in (
                        "trial_id",
                        "dataset",
                        "model",
                        "parameters",
                        "configuration_sha256",
                        "seed",
                        "primary_score",
                        "fold_mae",
                        "runs",
                    )
                }
            )
            evaluations[-1]["role"] = (
                "selected" if case["trial_id"] == winner["trial_id"] else "comparator"
            )
        datasets[dataset] = {
            "selected_trial_id": winner["trial_id"],
            "origin": str(origin),
            "target_start": str(origin + timedelta(days=1)),
            "target_end": str(end),
            "horizon": 28,
            "training_start": str(start),
            "maximum_training_rows": plan["settings"]["training_rows"][dataset],
            "series_count": len(metadata),
            "series_sha256": identity(list(metadata.series_id)),
            "initial_classes_sha256": identity(
                dict(zip(metadata.series_id, metadata.pattern, strict=True))
            ),
            "class_as_of": str(splits[dataset][0].origin),
            "feature_schema": FeatureEncoder(metadata, dataset, start, False).metadata(),
            "evaluations": evaluations,
        }
    scientific = {
        p.relative_to(ROOT).as_posix(): file_digest(p)
        for p in sorted((ROOT / "src/intelligent_demand").rglob("*.py"))
    }
    scientific.update(
        {
            p.relative_to(ROOT).as_posix(): file_digest(p)
            for p in sorted((ROOT / "configs").glob("*.yaml"))
        }
    )
    scientific["pyproject.toml"] = file_digest(ROOT / "pyproject.toml")
    scientific.update(
        {
            p.relative_to(ROOT).as_posix(): file_digest(p)
            for p in sorted((ROOT / "tests").rglob("*.py"))
        }
    )
    scientific.update(
        {
            name: file_digest(ROOT / name)
            for name in (
                "reports/eda/proposed_splits.json",
                "docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md",
            )
        }
    )
    for relative, digest in scientific.items():
        source = ROOT / relative
        target = OUTPUT / "code_snapshot" / relative
        if target.exists():
            if file_digest(target) != digest:
                raise ValueError("Existing pre-freeze code snapshot differs")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + f".{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(source.read_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    git = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT)]
    revision = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
    record = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "phase": "pre_holdout_freeze",
        "git_revision": revision,
        "package_versions": environment_versions(),
        "git_dirty": bool(
            subprocess.check_output(git + ["status", "--porcelain"], text=True).strip()
        ),
        "plan_sha256": plan["contract_sha256"],
        "phase4b_gate_sha256": file_digest(REPORTS / "phase4b_gate.json"),
        "code_sha256": scientific,
        "source_sha256": plan["source_sha256"],
        "datasets": datasets,
        "primary_selection": "four-origin macro MAE; 1e-12 ties use frozen simplicity order",
        "sampling": (
            "seed42 equal series/time strata; 56 prior days; 150000/182940 "
            "actual rows; no outcome filtering"
        ),
        "refit": "all pre-holdout history eligible; same frozen bounded sampling and recursive_28",
        "features": (
            "price-free; no SNAP/events/future prices; deterministic calendar and target-free IDs"
        ),
        "metrics": ["mae", "rmse", "wape_percent", "bias_units", "bias_percent", "mase", "rmsse"],
        "scale": "full final-origin training history; season7; undefined scales remain null",
        "fallbacks": (
            "same frozen adapter eligibility; explicit whole-series/window "
            "fallback; common nonnegative clipping, retain raw; no rounding"
        ),
        "naming": (
            "unique UUID forecast attempt per frozen trial and dataset; "
            "preserve all earlier attempts"
        ),
        "holdout_targets_accessed": False,
        "holdout_assessments_per_dataset": 1,
        "saved_actuals_reads": (
            "audit/report recomputation only; every read logged; no new model selection"
        ),
    }
    record["manifest_sha256"] = identity(record)
    publish_once(OUTPUT / "frozen_selection.json", record)
    checked = verify_frozen()
    append_access("selection_frozen", details={"selection_sha256": record["manifest_sha256"]})
    text = "# Frozen Phase 4 model selection\n\n"
    text += (
        f"Frozen before final target access at {record['created_at_utc']} "
        f"UTC; manifest SHA-256 `{record['manifest_sha256']}`. "
    )
    text += (
        f"Git revision `{revision}` plus immutable checksummed scientific "
        f"code/config snapshot. No Git commit or push was needed.\n\n"
    )
    for dataset, definition in datasets.items():
        text += (
            f"## {dataset}\n\nSelected: `{definition['selected_trial_id']}`. "
            f"Final origin {definition['origin']}; "
        )
        text += (
            f"28 targets {definition['target_start']}–{definition['target_end']}; "
            f"{definition['series_count']:,} series.\n\n"
        )
        for case in definition["evaluations"]:
            text += (
                f"- {case['role']}: `{case['trial_id']}` / {case['model']}; "
                f"validation MAE {case['primary_score']:.9f}; "
            )
            text += f"configuration `{case['configuration_sha256']}`.\n"
        text += (
            "\nExact immutable hyperparameters:\n\n```json\n"
            + json.dumps(definition["evaluations"], indent=2)
            + "\n```\n\n"
        )
    text += (
        "All model choices, comparators, sampling, features, metrics, "
        "eligibility, fallbacks and source/code fingerprints "
    )
    text += (
        "are fixed in the machine-readable manifest. Both "
        "datasets' model artifacts, scales and predictions must be "
    )
    text += (
        "sealed before any target read. No refit, regeneration or replacement "
        "after access. Phase 5 and Claude audit remain unstarted.\n"
    )
    (ROOT / "docs/PHASE4_FROZEN_MODEL_SELECTION.md").write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "selection_sha256": record["manifest_sha256"],
                "created_at_utc": record["created_at_utc"],
                "selected": {d: v["selected_trial_id"] for d, v in datasets.items()},
            },
            indent=2,
        )
    )
    return checked


if __name__ == "__main__":
    freeze_selection()
