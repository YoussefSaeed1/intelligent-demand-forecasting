"""Offline Phase 4 evidence reports; never fit models or rescan canonical holdouts."""

import argparse
import html
import json
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

from intelligent_demand.experiments.benchmark import population, verify_sources
from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.registry import ExperimentRegistry, atomic_json, file_digest
from intelligent_demand.reporting.benchmark_report import markdown_table as render_table
from intelligent_demand.tuning.authority import ledger_events, verify_frozen
from intelligent_demand.tuning.final import saved_actuals, verify_pre_target_bundle
from intelligent_demand.tuning.plan import OUTPUT, REPORTS, ROOT, load_plan, require_phase
from intelligent_demand.tuning.runner import experiment_config
from intelligent_demand.tuning.selection import choose

FIGURES = ROOT / "reports/figures/phase4"
DATASETS = ("store_item", "m5")
COLORS = ["#14608a", "#b45309", "#007c70", "#8549a5", "#a33e52"]
MODEL_COLORS = {
    "lightgbm": COLORS[0],
    "random_forest": COLORS[1],
    "holt_winters_additive": COLORS[2],
    "tsb": COLORS[2],
    "seasonal_moving_average": COLORS[3],
    "moving_average_28": COLORS[3],
    "seasonal_naive": COLORS[4],
}
LIMITATIONS = """Observed sales may be constrained by availability and are not latent demand.
M5 price publication latency is unverified: every Phase 4 ML candidate is price-free;
Phase 3 price-enabled M5 scores remain conditional research references.
SNAP, events and future prices are excluded. Equal seeded series/time-stratified ML
sampling uses 150,000 Store Item labels and 182,940 M5 labels per origin, with no
outcome filtering; all series and zero-demand histories remain eligible. This is
300 and 6 labels per series respectively, not full-history supervised training.
Four validation windows and one final 28-day window cover limited seasonal regimes.
Search-selected validation gains are optimistic estimates after model selection.
Origin spread is descriptive variability, not a confidence interval. Correlated
series and only four origins do not establish statistical significance. Grouped
leaf errors by hierarchy are not aggregate-node forecasts or official WRMSSE.
Undefined scale/actual denominators stay null and their coverage is reported.
Accuracy does not demonstrate inventory savings or economic superiority.
Runtime is measured worker cost with verified cache reuse; hardware load and cache
warmth vary, so these observations are not controlled hardware benchmarks.
Direct cross-dataset transfer is untested; compare methodology and relative baseline
performance rather than absolute sales-unit errors. Historical Phase 3 statistical
subset results cannot establish population performance; Phase 4 comparisons use
the complete approved populations. Holdout results cannot be used for retuning.
An independent Claude audit is still mandatory after Phase 4 and before Phase 5;
it must review scientific integrity without redesigning models to fit the holdout.
"""


def markdown_table(frame):
    return render_table(list(frame.columns), frame.itertuples(index=False, name=None))


def initialise():
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.prop_cycle": plt.cycler(color=COLORS),
        }
    )


def save(figure, name, caption, inventory):
    for extension in ("png", "svg"):
        path = FIGURES / f"{name}.{extension}"
        figure.savefig(path, dpi=165, bbox_inches="tight", facecolor="white")
        inventory.append(
            {
                "path": path.relative_to(REPORTS.parent).as_posix(),
                "purpose": caption,
                "sha256": file_digest(path),
            }
        )
    plt.close(figure)


def best_cases(gate):
    settings = load_plan()["settings"]["selection"]
    rows = []
    for dataset in DATASETS:
        candidates = [r for r in gate["trials"] if r["dataset"] == dataset]
        for method in sorted({r["model"] for r in candidates}):
            rows.append(choose([r for r in candidates if r["model"] == method], settings))
    return rows


def validation_details(cases):
    registry = ExperimentRegistry(experiment_config().registry_directory)
    records, paired = [], []
    for case in cases:
        for fold, run_id in enumerate(case["runs"], 1):
            state = registry.completed(run_id)
            metrics = json.loads(
                (registry.directory(run_id) / state["outputs"]["metrics"]["path"]).read_text()
            )
            record = {
                "dataset": case["dataset"],
                "trial_id": case["trial_id"],
                "model": case["model"],
                "fold": fold,
                "horizon": {k: v["macro"]["mae"] for k, v in metrics["by_horizon"].items()},
                "classes": {
                    k: {"mae": v["macro"]["mae"], "series": v["coverage"]["series"]}
                    for k, v in metrics["by_demand_class"].items()
                },
            }
            records.append(record)
            if case["dataset"] == "m5" and case["model"] in ("random_forest", "moving_average_28"):
                table = pd.DataFrame(metrics["all"]["per_series"])[["series_id", "mae"]]
                table = table.rename(columns={"mae": case["model"]})
                table["fold"] = fold
                paired.append(table)
    comparisons = []
    for fold in range(1, 5):
        parts = [p for p in paired if p.fold.iloc[0] == fold]
        if len(parts) != 2:
            raise ValueError("M5 paired comparison requires both full-population candidates")
        joint = parts[0].merge(parts[1], on=["series_id", "fold"], validate="one_to_one")
        if len(joint) != 30490:
            raise ValueError("M5 paired population differs")
        difference = joint.random_forest - joint.moving_average_28
        comparisons.append(
            {
                "fold": fold,
                "rf_minus_ma28_mae": float(difference.mean()),
                "rf_series_win_percent": float(100 * (difference < -1e-12).mean()),
                "ma28_series_win_percent": float(100 * (difference > 1e-12).mean()),
                "tie_percent": float(100 * (difference.abs() <= 1e-12).mean()),
            }
        )
    return records, comparisons


def tuning_figures(gate, cases, details):
    initialise()
    inventory = []
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        for case in [c for c in cases if c["dataset"] == dataset and c["kind"] == "tuning"]:
            rows = [
                r for r in gate["trials"] if r["dataset"] == dataset and r["model"] == case["model"]
            ]
            rows.sort(key=lambda r: r["trial_id"])
            axis.plot(
                range(1, len(rows) + 1),
                np.minimum.accumulate([r["primary_score"] for r in rows]),
                "o-",
                label=case["model"],
                color=MODEL_COLORS[case["model"]],
            )
        axis.set(
            title=dataset,
            xlabel="Frozen configuration order within family",
            ylabel="Best four-origin macro MAE (units)",
        )
        axis.legend(fontsize=8)
        axis.grid(alpha=0.2)
    save(
        figure,
        "tuning_progress",
        "Validation incumbent by predetermined configuration order; "
        "not wall-clock time or holdout progress.",
        inventory,
    )
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        rows = sorted(
            [c for c in cases if c["dataset"] == dataset], key=lambda r: r["primary_score"]
        )
        bars = axis.barh(
            [r["model"].replace("_", " ") for r in rows],
            [r["primary_score"] for r in rows],
            color=COLORS[0],
        )
        axis.bar_label(bars, fmt="%.4f", padding=3)
        axis.invert_yaxis()
        axis.set(title=dataset, xlabel="Four-origin macro MAE (units); lower is better")
        axis.set_xlim(0, max(r["primary_score"] for r in rows) * 1.22)
    save(
        figure,
        "candidate_accuracy",
        "Best validation configuration per family and unchanged "
        "baselines; equal full populations, four origins, H28.",
        inventory,
    )
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        for case in [c for c in cases if c["dataset"] == dataset]:
            axis.plot(range(1, 5), case["fold_mae"], "o-", label=case["model"])
        axis.set(
            title=dataset,
            xlabel="Validation origin index",
            ylabel="Macro MAE (units)",
            xticks=[1, 2, 3, 4],
        )
        axis.legend(fontsize=7)
        axis.grid(alpha=0.2)
    save(
        figure,
        "origin_stability",
        "Descriptive performance across the four fixed validation "
        "origins; connecting lines are not uncertainty intervals.",
        inventory,
    )
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        for case in [c for c in cases if c["dataset"] == dataset]:
            rows = [r for r in details if r["trial_id"] == case["trial_id"]]
            axis.plot(
                range(1, 29),
                [np.mean([r["horizon"][str(h)] for r in rows]) for h in range(1, 29)],
                label=case["model"],
                color=MODEL_COLORS[case["model"]],
            )
        axis.set(
            title=dataset,
            xlabel="Forecast horizon (days)",
            ylabel="Mean validation macro MAE (units)",
        )
        axis.legend(fontsize=7)
        axis.grid(alpha=0.2)
    save(
        figure,
        "validation_horizon",
        "Error by horizon, averaged over four validation origins "
        "for each family's best configuration.",
        inventory,
    )
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        for method in sorted({c["model"] for c in cases if c["dataset"] == dataset}):
            rows = [r for r in gate["trials"] if r["dataset"] == dataset and r["model"] == method]
            axis.scatter(
                [r["worker_seconds"] for r in rows],
                [r["primary_score"] for r in rows],
                label=method,
                color=MODEL_COLORS[method],
                s=45,
            )
        axis.set(
            title=dataset,
            xlabel="Four-fold worker time (seconds)",
            ylabel="Four-origin macro MAE (units)",
            xscale="log",
        )
        axis.legend(fontsize=7)
        axis.grid(alpha=0.2)
    save(
        figure,
        "runtime_accuracy",
        "Accuracy versus measured four-fold worker time; "
        "log time axis, cache reuse and feature preparation included.",
        inventory,
    )
    return inventory


def summary_frame(cases):
    return pd.DataFrame(
        [
            {
                "dataset": c["dataset"],
                "trial": c["trial_id"],
                "MAE": c["primary_score"],
                "pooled RMSE": c["pooled_rmse"],
                "WAPE %": c["pooled_wape_percent"],
                "bias units": c["bias_units"],
                "MASE": c["macro_mase"],
                "RMSSE": c["macro_rmsse"],
                "seconds": c["worker_seconds"],
                "peak MiB": c["peak_rss_mib"],
            }
            for c in cases
        ]
    )


def tuning_report():
    gate = require_phase("4b")
    cases = best_cases(gate)
    details, paired = validation_details(cases)
    inventory = tuning_figures(gate, cases, details)
    frame = summary_frame(cases)
    anchors = []
    for case in cases:
        if case["kind"] != "tuning":
            continue
        anchor = next(
            r
            for r in gate["trials"]
            if r["dataset"] == case["dataset"]
            and r["model"] == case["model"]
            and r["trial_id"].endswith("_00")
        )
        anchors.append(
            {
                "dataset": case["dataset"],
                "family": case["model"],
                "anchor MAE": anchor["primary_score"],
                "best MAE": case["primary_score"],
                "gain %": 100 * (1 - case["primary_score"] / anchor["primary_score"]),
            }
        )
    selection = load_plan()["settings"]["selection"]
    decisions = {
        d: choose([r for r in gate["trials"] if r["dataset"] == d], selection)["trial_id"]
        for d in DATASETS
    }
    text = "# Phase 4 tuning results — validation only\n\n"
    text += (
        f"All {len(gate['trials'])} cases (23 tuning, four unchanged references), "
        f"{len(gate['runs'])} fold runs and "
        f"{sum(r['coverage']['observations'] for r in gate['runs']):,} forecasts passed "
        "independent NumPy reconciliation. No final targets were accessed in tuning.\n\n"
    )
    text += "## Best configuration per family\n\n" + markdown_table(frame) + "\n\n"
    stability = pd.DataFrame(
        [
            {
                "trial": c["trial_id"],
                **{f"origin {i}": score for i, score in enumerate(c["fold_mae"], 1)},
            }
            for c in cases
        ]
    )
    text += "## Origin-by-origin macro MAE\n\n" + markdown_table(stability) + "\n\n"
    class_rows = []
    for case in cases:
        rows = [r for r in details if r["trial_id"] == case["trial_id"]]
        for pattern in sorted(rows[0]["classes"]):
            class_rows.append(
                {
                    "trial": case["trial_id"],
                    "pattern": pattern,
                    "series": rows[0]["classes"][pattern]["series"],
                    "four-origin MAE": np.mean([r["classes"][pattern]["mae"] for r in rows]),
                }
            )
    text += "## Demand-class validation\n\n" + markdown_table(pd.DataFrame(class_rows)) + "\n\n"
    profiles = []
    for audited in gate["unique_training_caches_semantically_audited"]:
        profile = audited["sampling_profile"]
        profiles.append(
            {
                "dataset": audited["dataset"],
                "fold": audited["fold"],
                **{
                    k: profile[k]
                    for k in (
                        "labels",
                        "labels_per_series",
                        "series",
                        "stores",
                        "products",
                        "zero_label_percent",
                        "earliest_label",
                        "latest_label",
                        "eligible_label_fraction",
                    )
                },
            }
        )
    text += "## Independently verified training samples\n\n"
    text += markdown_table(pd.DataFrame(profiles)) + "\n\n"
    text += (
        "Every cached position array exactly reproduces seed-42 draws within equal time "
        "strata for every series. Initial demand classes and all stores/products are retained; "
        "quartile counts and class coverage are in the machine-readable gate. Zero labels "
        "remain in the samples. Four-origin worker cost totals "
        f"{sum(c['worker_seconds'] for c in gate['trials']):.1f} seconds; largest observed "
        f"worker RSS is {max(c['peak_rss_mib'] for c in gate['trials']):.1f} MiB. "
        "Trial statuses must all be completed before this report is permitted; failed and "
        "interrupted attempts cannot supply a partial ranking.\n\n"
    )
    text += "## Improvements over price-free initial anchors\n\n"
    text += markdown_table(pd.DataFrame(anchors)) + "\n\n"
    text += "M5 Phase 3 price-enabled RF/LightGBM are conditional references; the matched "
    text += "Phase 4 price-free anchors above isolate tuning from price availability changes.\n\n"
    text += "## M5 paired RF versus MA28\n\n" + markdown_table(pd.DataFrame(paired)) + "\n\n"
    text += "Negative RF-minus-MA28 values favour RF; series wins weight every series equally. "
    text += (
        "Four origins give descriptive stability evidence, not significance or business value.\n\n"
    )
    rf = next(c for c in cases if c["dataset"] == "m5" and c["model"] == "random_forest")
    ma = next(c for c in cases if c["dataset"] == "m5" and c["model"] == "moving_average_28")
    text += (
        f"The best price-free RF reduces mean validation MAE by "
        f"{100 * (1 - rf['primary_score'] / ma['primary_score']):.6f}% versus MA28. "
        f"RF has lower origin-mean errors in {sum(p['rf_minus_ma28_mae'] < 0 for p in paired)} "
        f"of four windows; MA28 wins a majority of individual series in "
        f"{sum(p['ma28_series_win_percent'] > 50 for p in paired)} of four windows. "
        "Mean improvement therefore does not establish broad series-level dominance.\n\n"
    )
    text += f"Protocol-selected cases: `{decisions}`. Selection uses four-origin macro MAE; "
    text += "only exact 1e-12 ties invoke the frozen simplicity order.\n\n"
    text += "## Exact best configurations\n\n```json\n"
    text += (
        json.dumps(
            [{k: c[k] for k in ("trial_id", "parameters", "configuration_sha256")} for c in cases],
            indent=2,
        )
        + "\n```\n\n"
    )
    text += "## Limitations\n\n" + LIMITATIONS
    (ROOT / "docs/PHASE4_TUNING_RESULTS.md").write_text(text, encoding="utf-8")
    atomic_json(
        REPORTS / "phase4_tuning_report.json",
        {
            "status": "passed",
            "plan_sha256": gate["plan_sha256"],
            "decisions": decisions,
            "best_cases": [c["trial_id"] for c in cases],
            "paired_m5_rf_ma28": paired,
            "details": details,
            "figures": inventory,
        },
    )
    print(
        json.dumps(
            {
                "status": "tuning_report_written",
                "best_cases": len(cases),
                "figures": len(inventory) // 2,
            }
        )
    )


def final_records(gate, bundle):
    rows, details = [], []
    for record in gate["runs"]:
        forecast = next(r for r in bundle["forecasts"] if r["trial_id"] == record["trial_id"])
        path = OUTPUT / "final_metrics" / f"{record['trial_id']}.json"
        metrics = json.loads(path.read_text())
        metrics["all"].pop("per_series", None)
        rows.append(
            {
                "dataset": record["dataset"],
                "trial": record["trial_id"],
                "model": record["model"],
                "role": record["role"],
                **{k: record["macro"][k] for k in ("mae", "mase", "rmsse")},
                **{f"pooled_{k}": v for k, v in record["pooled"].items()},
                "series": record["coverage"]["series"],
                "observations": record["coverage"]["observations"],
                "fallback": record["coverage"]["fallback_observations"],
                "clipped": record["coverage"]["clipped_observations"],
                "fallback_percent": 100
                * record["coverage"]["fallback_observations"]
                / record["coverage"]["observations"],
                "undefined_mase": record["coverage"]["undefined_series"]["mase"],
                "undefined_rmsse": record["coverage"]["undefined_series"]["rmsse"],
                "undefined_wape": record["coverage"]["undefined_series"]["wape_percent"],
                "fit_seconds": forecast["fit_seconds"],
                "prediction_seconds": forecast["prediction_seconds"],
            }
        )
        details.append(
            {
                "trial": record["trial_id"],
                "dataset": record["dataset"],
                "model": record["model"],
                "metrics": metrics,
            }
        )
    return pd.DataFrame(rows), details


def final_figures(frame, details, frozen, bundle, validation):
    initialise()
    inventory = []
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        rows = frame[frame.dataset.eq(dataset)]
        labels = rows.model.str.replace("_", " ").tolist()
        x = np.arange(len(rows))
        scores = [
            next(r["primary_score"] for r in validation["trials"] if r["trial_id"] == t)
            for t in rows.trial
        ]
        axis.bar(x - 0.18, scores, width=0.36, label="Four-origin validation")
        axis.bar(x + 0.18, rows.mae, width=0.36, label="Final holdout")
        axis.set(title=dataset, ylabel="Macro MAE (units)", xticks=x, xticklabels=labels)
        axis.tick_params(axis="x", labelrotation=22)
        axis.legend(fontsize=8)
    save(
        figure,
        "validation_holdout",
        "Frozen candidates: validation versus one final H28 "
        "window. Validation was used for selection; holdout was not.",
        inventory,
    )
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        for row in [r for r in details if r["dataset"] == dataset]:
            axis.plot(
                range(1, 29),
                [row["metrics"]["by_horizon"][str(h)]["macro"]["mae"] for h in range(1, 29)],
                label=row["model"],
                color=MODEL_COLORS[row["model"]],
            )
        axis.set(title=dataset, xlabel="Final forecast horizon (days)", ylabel="Macro MAE (units)")
        axis.legend(fontsize=8)
        axis.grid(alpha=0.2)
    save(
        figure,
        "final_horizon",
        "Final errors at each forecast step for the frozen "
        "selected models and predeclared comparators.",
        inventory,
    )
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        rows = [r for r in details if r["dataset"] == dataset]
        patterns = sorted(rows[0]["metrics"]["by_demand_class"])
        x = np.arange(len(patterns))
        width = 0.8 / len(rows)
        for i, row in enumerate(rows):
            groups = row["metrics"]["by_demand_class"]
            axis.bar(
                x + (i - (len(rows) - 1) / 2) * width,
                [groups[p]["macro"]["mae"] for p in patterns],
                width,
                label=row["model"],
                color=MODEL_COLORS[row["model"]],
            )
        counts = [rows[0]["metrics"]["by_demand_class"][p]["coverage"]["series"] for p in patterns]
        axis.set(
            title=dataset,
            ylabel="Final macro MAE (units)",
            xticks=x,
            xticklabels=[f"{p}\n(n={n:,})" for p, n in zip(patterns, counts, strict=True)],
        )
        axis.tick_params(axis="x", labelrotation=15)
        axis.legend(fontsize=7)
    save(
        figure,
        "final_demand_patterns",
        "Demand classes are frozen from the initial training "
        "prefix; class size shown. No holdout-driven reclassification.",
        inventory,
    )
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        rows = frame[frame.dataset.eq(dataset)]
        method = "moving_average_28" if dataset == "m5" else "seasonal_naive"
        baseline = rows.loc[rows.model.eq(method), "mae"].iloc[0]
        gains = 100 * (1 - rows.mae / baseline)
        bars = axis.barh(rows.model.str.replace("_", " "), gains, color=COLORS[2])
        axis.bar_label(bars, fmt="%.2f%%", padding=4)
        axis.axvline(0, color="#333", linewidth=0.8)
        axis.set(title=f"{dataset}: reference {method}", xlabel="Final MAE reduction (%)")
        axis.margins(x=0.25)
    save(
        figure,
        "final_baseline_gains",
        "Final relative accuracy versus the predeclared "
        "simple baseline; negative values mean worse accuracy.",
        inventory,
    )
    figure, axes = plt.subplots(2, 2, figsize=(14, 8), layout="constrained")
    examples = []
    for column, dataset in enumerate(DATASETS):
        actual = saved_actuals(dataset, "final_report")
        metadata = population(dataset)
        # Defined before target access in frozen code: largest initial-prefix volume and median ID.
        selected_ids = [
            metadata.sort_values(
                ["sales_units", "series_id"], ascending=[False, True]
            ).series_id.iloc[0],
            metadata.sort_values("series_id").series_id.iloc[len(metadata) // 2],
        ]
        chosen = frozen["datasets"][dataset]["selected_trial_id"]
        forecast = next(r for r in bundle["forecasts"] if r["trial_id"] == chosen)
        predictions = pd.read_parquet(OUTPUT / forecast["files"]["predictions"]["path"])
        for row, series_id in enumerate(selected_ids):
            axis = axes[row, column]
            observed = actual.loc[actual.series_id.eq(series_id)].sort_values("target_date")
            predicted = predictions.loc[predictions.series_id.eq(series_id)].sort_values(
                "target_date"
            )
            axis.plot(
                pd.to_datetime(observed.target_date),
                observed.actual,
                "o-",
                label="Observed sales",
                markersize=3,
            )
            axis.plot(
                pd.to_datetime(predicted.target_date),
                predicted.prediction,
                "s--",
                label="Frozen selected model",
                markersize=3,
            )
            axis.set(title=f"{dataset}: {series_id}", ylabel="Daily units")
            axis.tick_params(axis="x", labelrotation=28, labelsize=8)
            axis.legend(fontsize=8)
            examples.append(
                {
                    "dataset": dataset,
                    "series_id": series_id,
                    "selection_rule": "largest initial volume" if row == 0 else "median ID",
                }
            )
    save(
        figure,
        "forecast_examples",
        "Illustrations selected by initial-prefix volume and "
        "median series ID, fixed in pre-holdout code; not representative error estimates.",
        inventory,
    )
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        for row in frame[frame.dataset.eq(dataset)].itertuples():
            groups = pd.read_parquet(OUTPUT / "final_hierarchy" / f"{row.trial}.parquet")
            field = "cat_id" if dataset == "m5" else "store_id"
            part = groups[groups.group_type.eq(field)].sort_values("group")
            axis.plot(
                part.group, part.macro_mae, "o", label=row.model, color=MODEL_COLORS[row.model]
            )
        axis.set(
            title=f"{dataset}: grouped leaf errors",
            ylabel="Final macro MAE (units)",
            xlabel="Category" if dataset == "m5" else "Store",
        )
        axis.legend(fontsize=7)
        axis.grid(alpha=0.2)
    save(
        figure,
        "final_hierarchy",
        "Final errors grouped by store (Store Item) or category "
        "(M5); these are means of leaf-series errors, not aggregate-node forecasts.",
        inventory,
    )
    return inventory, examples


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in ("src", "href") and value)


def verify_report(path, inventory):
    parser = LocalLinks()
    parser.feed(path.read_text(encoding="utf-8"))
    for value in parser.links:
        if value.startswith("#"):
            continue
        if "://" in value or not (path.parent / value).resolve().is_file():
            raise ValueError(f"Report has a nonlocal or broken reference: {value}")
    for item in inventory:
        image = REPORTS.parent / item["path"]
        if file_digest(image) != item["sha256"]:
            raise ValueError("Report figure checksum changed")
        if image.suffix == ".png":
            with Image.open(image) as opened:
                opened.verify()
        else:
            ET.parse(image)
    return {
        "relative_links": len(parser.links),
        "images_verified": len(inventory),
        "offline": True,
        "browser_render": "not_run_file_URL_policy_restriction",
    }


def write_html(path, sections, inventory):
    body = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Phase 4 scientific forecasting report</title><style>
:root{color-scheme:light}body{font:16px/1.65 system-ui,sans-serif;color:#203246;
background:#f0f4f7;margin:0}main{max-width:1180px;margin:auto;background:white;padding:42px}
h1{font-size:2.4rem;line-height:1.2}
h2{margin-top:2.6rem;border-top:2px solid #dbe5ed;padding-top:20px}
.eyebrow{letter-spacing:.14em;color:#14608a;font-weight:bold}nav{display:flex;flex-wrap:wrap;gap:15px}
a{color:#14608a}table{border-collapse:collapse;font-size:13px;white-space:nowrap}
td,th{text-align:right;padding:9px;border-bottom:1px solid #dbe5ed}th{background:#eaf1f6}
td:first-child,th:first-child{text-align:left}.table{overflow:auto}figure{margin:28px 0}
img{width:100%;height:auto}figcaption{font-size:14px;color:#43566b}p{max-width:100ch}
.caveat{padding:18px;background:#fff4df;border-left:4px solid #b45309}
@media(max-width:650px){main{padding:20px}h1{font-size:1.9rem}}
</style><main><p class="eyebrow">FORECASTING RESEARCH</p>
<h1>Phase 4: optimisation and final assessment</h1>
<p>Exploratory analysis → validation → tuning → frozen selection → final holdout.</p><nav>"""
    body += "".join(f'<a href="#{slug}">{html.escape(title)}</a>' for slug, title, _ in sections)
    body += "</nav>"
    for slug, title, content in sections:
        body += f'<section id="{slug}"><h2>{html.escape(title)}</h2>{content}</section>'
    body += "<section id='figures'><h2>Visual evidence</h2>"
    for item in inventory:
        if item["path"].endswith(".png"):
            relative = "../" + item["path"]
            caption = html.escape(item["purpose"])
            body += f'<figure><img src="{relative}" alt="{caption}"><figcaption>{caption}'
            body += f' <a href="{relative[:-4]}.svg">SVG</a></figcaption></figure>'
    body += (
        "</section><p>Prepared for independent review; "
        "Phase 5 and Claude audit not started.</p></main></html>"
    )
    path.write_text(body, encoding="utf-8")


def paragraph(text):
    return "<p>" + html.escape(text).replace("\n", " ") + "</p>"


def final_report():
    gate = require_phase("4c")
    validation = require_phase("4b")
    frozen = verify_frozen()
    bundle = verify_pre_target_bundle()
    if verify_sources() != frozen["source_sha256"]:
        raise ValueError("Data fingerprints changed before reporting")
    tuning = json.loads((REPORTS / "phase4_tuning_report.json").read_text())
    frame, details = final_records(gate, bundle)
    inventory, examples = final_figures(frame, details, frozen, bundle, validation)
    inventory = tuning["figures"] + inventory
    comparison = []
    for row in frame.itertuples():
        reference = "moving_average_28" if row.dataset == "m5" else "seasonal_naive"
        baseline = frame.loc[frame.dataset.eq(row.dataset) & frame.model.eq(reference), "mae"].iloc[
            0
        ]
        prior = next(r for r in validation["trials"] if r["trial_id"] == row.trial)
        comparison.append(
            {
                "dataset": row.dataset,
                "trial": row.trial,
                "role": row.role,
                "validation MAE": prior["primary_score"],
                "final MAE": row.mae,
                "baseline gain %": 100 * (1 - row.mae / baseline),
            }
        )
    comparison = pd.DataFrame(comparison)
    sample = pd.DataFrame(
        [
            {
                "dataset": d,
                "series": frozen["datasets"][d]["series_count"],
                "labels": 150000 if d == "store_item" else 182940,
                "labels per series": 300 if d == "store_item" else 6,
                "eligible final labels": frozen["datasets"][d]["series_count"]
                * (
                    (
                        pd.Timestamp(frozen["datasets"][d]["origin"])
                        - pd.Timestamp(frozen["datasets"][d]["training_start"])
                    ).days
                    + 1
                    - 56
                ),
            }
            for d in DATASETS
        ]
    )
    sample["sample %"] = 100 * sample.labels / sample["eligible final labels"]
    scientific = (
        "Daily H28 point forecasting on Store Item (500 series; 913,000 historical rows; "
        "2013–2017) and M5 (30,490 series; 59,181,090 historical rows; 2011–2016). "
        "Assess whether compact global ML and statistical candidates improve over simple "
        "baselines under origin-bounded information. All comparisons are full-population."
    )
    method = (
        "The four original expanding validation origins are unchanged. A seed-42 finite "
        "random search evaluated 23 tuning configurations and four unchanged references, "
        "each on four origins. Primary selection is the equal-origin mean of equal-series "
        "MAE. Secondary errors use full-history seasonal-7 training scales; pooled RMSE and "
        "WAPE aggregate squared/absolute errors and actual totals. No early stopping, adaptive "
        "budget expansion, holdout screening or population mismatch was used. Store Item "
        "families: LightGBM, Random Forest, Holt-Winters; references: Seasonal Naive and "
        "Seasonal Moving Average. M5: price-free RF/LightGBM and TSB; references: SN and MA28."
    )
    freeze_text = (
        f"Manifest {frozen['manifest_sha256']} at {frozen['created_at_utc']} UTC fixes exact "
        "models, features, sample rules and comparators. Final origins are 2017-12-03 "
        "and 2016-04-24. Both datasets' entire forecast/model bundle was sealed before "
        "the first target scan. Each canonical holdout was read once; subsequent audit "
        "and report calculations use checksummed actual snapshots with logged access. "
        "The selected designation remains fixed even when a comparator performs better."
    )
    sections = [
        ("objective", "Research objective and datasets", paragraph(scientific)),
        (
            "method",
            "Search, metrics and training design",
            paragraph(method)
            + '<div class="table">'
            + sample.to_html(index=False, float_format=lambda v: f"{v:.4f}")
            + "</div>",
        ),
        (
            "validation",
            "Validation findings",
            paragraph(
                "Validation comparisons below were used for model selection and are not unbiased "
                "final estimates. Exact configuration spaces and all 27 trial records are retained."
            )
            + '<div class="table">'
            + summary_frame(best_cases(validation)).to_html(
                index=False, float_format=lambda v: f"{v:.6f}"
            )
            + "</div>",
        ),
        ("freeze", "Frozen final selection", paragraph(freeze_text)),
        (
            "holdout",
            "One-time final holdout results",
            '<div class="table">'
            + frame.to_html(index=False, float_format=lambda v: f"{v:.6f}")
            + "</div>"
            + '<div class="table">'
            + comparison.to_html(index=False, float_format=lambda v: f"{v:.6f}")
            + "</div>",
        ),
        (
            "limits",
            "Interpretation and threats to validity",
            '<div class="caveat">' + paragraph(LIMITATIONS) + "</div>",
        ),
        (
            "evidence",
            "Reproducibility and independent audit",
            paragraph(
                "Run the saved-prediction audit commands in docs/PHASE4_REPRODUCIBILITY.md. "
                "Do not rerun one-time fitting/scoring commands. The local audit inventory links "
                "the immutable code snapshot, source hashes, trial registry, final predictions, "
                "metric evidence and append-only access ledger."
            )
            + '<a href="../../docs/PHASE4_REPRODUCIBILITY.md">Commands</a> · '
            '<a href="../../docs/PHASE4_AUDIT_PACKAGE.md">Audit inventory guide</a>',
        ),
    ]
    path = REPORTS / "PHASE4_FORECASTING_REPORT.html"
    write_html(path, sections, inventory)
    text = "# Phase 4 final scientific forecasting report\n\n" + scientific + "\n\n"
    text += "## Experimental method\n\n" + method + "\n\n" + markdown_table(sample) + "\n\n"
    text += "## Frozen final assessment\n\n" + freeze_text + "\n\n"
    text += markdown_table(frame.drop(columns=["model"])) + "\n\n"
    text += "## Validation versus final holdout\n\n" + markdown_table(comparison) + "\n\n"
    text += "## Interpretation\n\n"
    for dataset in DATASETS:
        selected = frame[frame.dataset.eq(dataset) & frame.role.eq("selected")].iloc[0]
        descriptive_best = frame[frame.dataset.eq(dataset)].sort_values("mae").iloc[0]
        text += (
            f"{dataset}: the frozen selection `{selected.trial}` has final MAE "
            f"{selected.mae:.9f}. The lowest observed final MAE among predeclared candidates "
            f"is `{descriptive_best.trial}` ({descriptive_best.mae:.9f}); this descriptive "
            "comparison does not replace the frozen selection or authorise retuning.\n\n"
        )
    text += "## Threats to validity and limitations\n\n" + LIMITATIONS
    text += (
        "\nSee PHASE4_TUNING_RESULTS.md for exact trial configurations, anchor gains and paired "
    )
    text += "M5 stability; PHASE4_REPRODUCIBILITY.md for saved-artifact commands.\n"
    (ROOT / "docs/PHASE4_FINAL_EVALUATION.md").write_text(text, encoding="utf-8")
    (ROOT / "docs/PHASE4_LIMITATIONS.md").write_text(
        "# Phase 4 limitations\n\n" + LIMITATIONS, encoding="utf-8"
    )
    index = "# Phase 4 figure index\n\nAll PNG/SVG pairs share the same source-backed figure.\n\n"
    for item in inventory:
        index += f"- [{item['path']}](../{item['path']}): {item['purpose']}\n"
    (REPORTS / "PHASE4_VISUALISATION_INDEX.md").write_text(index, encoding="utf-8")
    verification = verify_report(path, inventory)
    atomic_json(
        REPORTS / "phase4_report_validation.json",
        {
            "status": "passed",
            **verification,
            "html_sha256": file_digest(path),
            "figures": inventory,
            "examples": examples,
            "selection_sha256": frozen["manifest_sha256"],
        },
    )
    audit_package(frozen, bundle, gate)
    atomic_json(
        REPORTS / "phase4d_gate.json",
        {
            "phase": "4d",
            "status": "passed",
            "plan_sha256": frozen["plan_sha256"],
            "selection_sha256": frozen["manifest_sha256"],
            "quality_checks_passed": False,
            "report_validation": verification,
            "source_hashes_unchanged": True,
            "holdout_targets_accessed": True,
            "independent_claude_audit": "not_started",
            "phase5": "not_started",
        },
    )
    print(
        json.dumps(
            {
                "status": "final_report_written",
                "final_evaluations": len(frame),
                "figures": len(inventory) // 2,
                **verification,
            },
            indent=2,
        )
    )


def audit_package(frozen, bundle, gate):
    ledger = ledger_events()
    files = [
        OUTPUT / n
        for n in (
            "plan.json",
            "execution_contract.json",
            "search_execution.json",
            "trial_leaderboard.json",
            "frozen_selection.json",
            "sealed_predictions.json",
            "holdout_access.jsonl",
            "final_evaluation.json",
        )
    ]
    files += [
        REPORTS / n
        for n in (
            "phase4_preflight.json",
            "phase4a_gate.json",
            "phase4b_gate.json",
            "phase4c_gate.json",
            "phase4_tuning_report.json",
            "phase4_report_validation.json",
        )
    ]
    files += list((OUTPUT / "final_metrics").glob("*.json"))
    files += list((OUTPUT / "final_actuals").glob("*.json"))
    files += list((OUTPUT / "final_actuals").glob("*.parquet"))
    for record in bundle["forecasts"]:
        files += [OUTPUT / value["path"] for value in record["files"].values()]
    registry = ExperimentRegistry(experiment_config().registry_directory)
    feature_caches = set()
    for run in require_phase("4b")["runs"]:
        state = registry.completed(run["run_id"])
        if run["model"] in ("lightgbm", "random_forest"):
            meta = json.loads(
                (
                    registry.directory(run["run_id"]) / state["outputs"]["model_metadata"]["path"]
                ).read_text()
            )[0]
            feature_caches.add(
                Path(state["specification"]["model_configuration"]["feature_cache"])
                / identity(meta["feature_cache_contract"])
            )
        files += [
            registry.directory(run["run_id"]) / p["path"]
            for p in state["outputs"].values()
            if p["path"].endswith((".json", "predictions.parquet"))
        ]
    files += [OUTPUT / "code_snapshot" / relative for relative in frozen["code_sha256"]]
    for forecast in bundle["forecasts"]:
        if forecast["model"] in ("lightgbm", "random_forest"):
            meta = json.loads((OUTPUT / forecast["files"]["model_metadata"]["path"]).read_text())[0]
            feature_caches.add(OUTPUT / "feature_cache" / identity(meta["feature_cache_contract"]))
    for cache in feature_caches:
        complete = cache / "complete.json"
        manifest = json.loads(complete.read_text())
        files += [complete] + [cache / name for name in manifest["files"]]
    files += list((ROOT / "docs").glob("PHASE4*.md"))
    files += [
        p
        for p in (
            REPORTS / "phase4d_gate.json",
            REPORTS / "phase4_completion_checklist.json",
            REPORTS / "PHASE4_FORECASTING_REPORT.html",
        )
        if p.exists()
    ]
    inventory = [
        {
            "path": p.relative_to(ROOT).as_posix(),
            "bytes": p.stat().st_size,
            "sha256": file_digest(p),
        }
        for p in sorted(set(files))
    ]
    atomic_json(
        OUTPUT / "independent_audit_package.json",
        {
            "status": "prepared_not_externally_audited",
            "selection_sha256": frozen["manifest_sha256"],
            "bundle_sha256": bundle["bundle_sha256"],
            "ledger_events": len(ledger),
            "ledger_head_sha256": ledger[-1]["event_sha256"],
            "final_evaluations": len(gate["runs"]),
            "source_sha256": frozen["source_sha256"],
            "files": inventory,
            "issues": {"critical": [], "high": [], "limitations": LIMITATIONS.splitlines()},
            "instructions": "Independent Claude integrity audit after Phase 4 before Phase 5; "
            "no model redesign based on holdout; no refit, retuning or canonical rescan",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["tuning", "final"])
    args = parser.parse_args()
    tuning_report() if args.action == "tuning" else final_report()
