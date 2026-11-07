"""Source-backed milestone reporting; refuses incomplete four-origin comparisons."""

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from intelligent_demand.experiments.benchmark import OUTPUT, ROOT
from intelligent_demand.experiments.config import load_experiment_config
from intelligent_demand.experiments.gates import require_gate
from intelligent_demand.experiments.registry import ExperimentRegistry


def load_gate(phase):
    gate = require_gate(phase)
    if gate["status"] != "passed" or not gate["independent_reconciliation"]:
        raise ValueError("Reporting requires a passed independent milestone gate")
    registry = ExperimentRegistry(
        load_experiment_config(ROOT / "configs/forecasting.yaml").registry_directory
    )
    frame = []
    for record in gate["runs"]:
        state = registry.completed(record["run_id"])
        if record["status"] != "passed":
            raise ValueError("Incomplete run cannot enter report rankings")
        frame.append(
            {
                "dataset": record["dataset"],
                "model": record["model"],
                "scope": record.get("scope", "full"),
                "fold": record["fold"],
                "run_id": state["run_id"],
                **{f"macro_{k}": v for k, v in record["macro"].items()},
                **record["totals"],
                "observations": record["coverage"]["observations"],
                "series": record["coverage"]["series"],
                "fallback": record["coverage"]["fallback_observations"],
                "clipped": record["coverage"]["clipped_observations"],
            }
        )
    frame = pd.DataFrame(frame)
    if frame.duplicated(["dataset", "scope", "model", "fold"]).any():
        raise ValueError("Duplicated comparison origin")
    for _, group in frame.groupby(["dataset", "scope", "model"]):
        if set(group.fold) != {1, 2, 3, 4} or len(group) != 4 or group.series.nunique() != 1:
            raise ValueError("All four matching validation folds are required")
    return gate, frame


def markdown_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def aggregate(frame):
    rows = []
    for (dataset, scope, model), group in frame.groupby(["dataset", "scope", "model"], sort=True):
        observations, actual = group.observations.sum(), group.actual.sum()
        rows.append(
            {
                "dataset": dataset,
                "model": model,
                "scope": scope,
                "series": int(group.series.iloc[0]),
                "observations": int(observations),
                "macro_mae": group.macro_mae.mean(),
                "mean_fold_macro_rmse": group.macro_rmse.mean(),
                "macro_mase": group.macro_mase.mean(),
                "macro_rmsse": group.macro_rmsse.mean(),
                "pooled_rmse": np.sqrt(group.squared_error.sum() / observations),
                "pooled_wape_percent": 100 * group.absolute_error.sum() / actual
                if actual
                else np.nan,
                "bias_units": group.error.sum() / observations,
                "fallback_percent": 100 * group.fallback.sum() / observations,
                "clipped_percent": 100 * group.clipped.sum() / observations,
                "fold_mae_min": group.macro_mae.min(),
                "fold_mae_max": group.macro_mae.max(),
            }
        )
    return pd.DataFrame(rows)


def baseline_report():
    gate, folds = load_gate("3b")
    results = aggregate(folds)
    execution = json.loads((OUTPUT / "3b_execution.json").read_text())
    resources = {row["run_id"]: row for row in execution["runs"]}
    figure_directory = ROOT / "reports/figures/phase3"
    figure_directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis, dataset in zip(axes, ("store_item", "m5"), strict=True):
        selected = results[results.dataset.eq(dataset)].sort_values("macro_mae")
        bars = axis.barh(selected.model.str.replace("_", " "), selected.macro_mae, color="#2463a0")
        axis.invert_yaxis()
        axis.set_title(f"{dataset}: {int(selected.series.iloc[0]):,} series")
        axis.set_xlabel("Mean of four fold macro MAEs (sales units)")
        axis.set_xlim(0, selected.macro_mae.max() * 1.2)
        axis.bar_label(bars, fmt="%.3f", padding=4, fontsize=10)
        axis.grid(axis="x", alpha=0.18)
        axis.set_axisbelow(True)
    figure.suptitle("Baseline accuracy on matched 28-day validation windows", fontsize=15)
    for extension in ("png", "svg"):
        figure.savefig(figure_directory / f"phase3b_accuracy.{extension}", dpi=180)
    plt.close(figure)
    metric_rows, resource_rows, findings = [], [], []
    for dataset in ("store_item", "m5"):
        selected = results[results.dataset.eq(dataset)].sort_values("macro_mae")
        best = selected.iloc[0]
        seasonal = selected[selected.model.eq("seasonal_naive")].iloc[0]
        relative = 100 * (1 - best.macro_mae / seasonal.macro_mae) if seasonal.macro_mae else np.nan
        findings.append(
            f"- {dataset}: {best.model} has the lowest four-fold macro MAE "
            f"({best.macro_mae:.6f} units), {relative:.2f}% below seasonal naive "
            "on the same population/windows. This is validation evidence, not a final-test result."
        )
        for row in selected.itertuples():
            metric_rows.append(
                [
                    dataset,
                    row.model,
                    f"{row.macro_mae:.6f}",
                    f"{row.pooled_rmse:.6f}",
                    f"{row.pooled_wape_percent:.4f}",
                    f"{row.bias_units:+.6f}",
                    f"{row.macro_mase:.6f}",
                    f"{row.macro_rmsse:.6f}",
                ]
            )
            run_ids = folds[folds.dataset.eq(dataset) & folds.model.eq(row.model)].run_id
            peak_mib = max(resources[key]["peak_worker_rss_bytes"] for key in run_ids) / 2**20
            resource_rows.append(
                [
                    dataset,
                    row.model,
                    row.series,
                    f"{row.observations:,}",
                    f"{row.fallback_percent:.4f}",
                    f"{sum(resources[key]['elapsed_seconds'] for key in run_ids):.2f}",
                    f"{peak_mib:.2f}",
                ]
            )
    text = "# Phase 3B baseline results\n\n"
    text += "Status: COMPLETE; independent reconciliation gate passed.\n\n"
    text += "\n".join(findings) + "\n\n"
    text += markdown_table(
        [
            "Dataset",
            "Model",
            "Macro MAE",
            "Pooled RMSE",
            "Pooled WAPE %",
            "Bias units",
            "Macro MASE",
            "Macro RMSSE",
        ],
        metric_rows,
    )
    text += "\n\nMAE/MASE/RMSSE are means of the four fold macro values. Pooled RMSE, WAPE "
    text += "and bias use summed errors and actual quantities over all four validation windows. "
    text += "Undefined per-series denominators remain null and have explicit coverage "
    text += "in the gate JSON.\n\n"
    text += "![Matched baseline accuracy](../reports/figures/phase3/phase3b_accuracy.png)\n\n"
    text += markdown_table(
        [
            "Dataset",
            "Model",
            "Series/fold",
            "Predictions (4 folds)",
            "Fallback %",
            "Worker seconds (4 runs)",
            "Maximum sampled RSS MiB",
        ],
        resource_rows,
    )
    text += (
        "\n\nWorker times include preparation/cache checks, forecasting, scoring and publication; "
    )
    text += "first-use cache creation is included. They are not isolated algorithm fit times. "
    text += "Memory is sampled worker RSS; it is not whole-system peak memory.\n\n"
    text += f"All {len(gate['runs'])} runs passed complete-key, 28-day horizon, metadata, "
    text += (
        "clipping, delivery-method, per-series/macro/pooled/horizon/class metric reconciliation "
    )
    text += "and unchanged raw/canonical hash checks. Store/product/hierarchy results are in "
    text += "`artifacts/experiments/phase3/3b_hierarchy_metrics.parquet`. Final holdout targets "
    text += "remain protected. Four adjacent windows cover a limited seasonal span and do not "
    text += "establish significance or a universal winning method.\n\n"
    text += "Evidence: [independent gate](../reports/forecasting/phase3b_gate.json), "
    text += "[method definitions](BASELINE_MODELS.md), and the ignored local experiment registry.\n"
    (ROOT / "docs/BASELINE_RESULTS.md").write_text(text, encoding="utf-8")
    results.to_parquet(OUTPUT / "3b_model_summary.parquet", index=False)
    print(text)


def statistical_report():
    gate, statistical = load_gate("3c")
    _, baselines = load_gate("3b")
    folds = pd.concat([statistical, baselines], ignore_index=True)
    results = aggregate(folds)
    directory = ROOT / "reports/figures/phase3"
    directory.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(2, 2, figsize=(15, 12), layout="constrained")
    rows = []
    for row_index, scope in enumerate(("full", "statistical_subset")):
        for axis, dataset in zip(axes[row_index], ("store_item", "m5"), strict=True):
            chosen = results[results.dataset.eq(dataset) & results.scope.eq(scope)].sort_values(
                "macro_mae"
            )
            bars = axis.barh(chosen.model.str.replace("_", " "), chosen.macro_mae, color="#2463a0")
            axis.invert_yaxis()
            axis.set_xlim(0, chosen.macro_mae.max() * 1.2)
            axis.set_xlabel("Mean four-fold macro MAE (sales units)")
            axis.set_title(
                f"{dataset} · {scope.replace('_', ' ')} · {int(chosen.series.iloc[0])} series"
            )
            axis.bar_label(bars, fmt="%.3f", padding=3, fontsize=9)
            axis.grid(axis="x", alpha=0.18)
            axis.set_axisbelow(True)
            for record in chosen.itertuples():
                rows.append(
                    [
                        dataset,
                        scope,
                        record.model,
                        record.series,
                        f"{record.macro_mae:.6f}",
                        f"{record.pooled_rmse:.6f}",
                        f"{record.pooled_wape_percent:.4f}",
                        f"{record.bias_units:+.6f}",
                        f"{record.fallback_percent:.4f}",
                    ]
                )
    figure.suptitle("Statistical methods and matched baseline comparisons", fontsize=16)
    for extension in ("png", "svg"):
        figure.savefig(directory / f"phase3c_accuracy.{extension}", dpi=170)
    plt.close(figure)
    text = "# Phase 3C statistical results\n\n"
    text += "Status: COMPLETE; independent and automated quality gates passed.\n\n"
    text += (
        "Full-population and statistical-subset results below are separate comparisons. "
        "The unweighted stratified subsets contain 53 Store Item and 51 M5 series; "
        "their means must not be extrapolated to the populations. All comparisons "
        "use all four unchanged 28-day validation windows.\n\n"
    )
    text += markdown_table(
        [
            "Dataset",
            "Population",
            "Requested model",
            "Series/fold",
            "Macro MAE",
            "Pooled RMSE",
            "WAPE %",
            "Bias units",
            "Fallback %",
        ],
        rows,
    )
    text += (
        "\n\n![Matched statistical comparisons](../reports/figures/phase3/phase3c_accuracy.png)\n\n"
    )
    text += "## Native delivery and fallbacks\n\n"
    from intelligent_demand.models.statistical import STATISTICAL

    for dataset in ("store_item", "m5"):
        for method in STATISTICAL:
            selected = [
                row for row in gate["runs"] if row["dataset"] == dataset and row["model"] == method
            ]
            total = sum(row["coverage"]["series"] for row in selected)
            native = sum(row["actual_method_series"].get(method, 0) for row in selected)
            reasons = {}
            for record in selected:
                for reason, count in record["fallback_reason_series"].items():
                    reasons[reason] = reasons.get(reason, 0) + count
            text += f"- {dataset} / {method}: {native}/{total} native series-origin cases; "
            text += (
                "fallback cases "
                + (
                    ", ".join(f"{key}: {value}" for key, value in sorted(reasons.items()))
                    if reasons
                    else "none"
                )
                + ".\n"
            )
    text += (
        "\nThese are counts across four origins, not distinct series. Complete delivered-system "
        "scores include every declared fallback. Native-only diagnostics remain in the gate JSON "
        "and have a different, explicitly counted population; "
        "they are not used for unmatched rankings.\n\n"
    )
    execution = json.loads((OUTPUT / "3c_execution.json").read_text())
    text += "## Resources and limitations\n\n"
    text += f"Executed {len(execution['runs'])} statistical runs sequentially, "
    text += (
        f"{sum(row['elapsed_seconds'] for row in execution['runs']):.2f} worker seconds in total. "
    )
    peak_mib = max(row["peak_worker_rss_bytes"] for row in execution["runs"]) / 2**20
    text += f"Maximum recorded working set/RSS was {peak_mib:.2f} MiB. "
    text += (
        "Times include preparation, forecasting, scoring and publication; "
        "cached and first-use work "
        "differ. Later runs also retain stage timings. Projected baselines reuse completed "
        "Phase 3B forecasts and must not be described as newly fitted low-cost runs.\n\n"
    )
    text += (
        "Smoothing parameters and ARIMA orders are fixed initial choices, not optimised models. "
        "The documented statsmodels seasonal recycling discrepancy is avoided by forecasting "
        "from validated component states. Leading zeros and missing historical prices remain "
        "unchanged; no future prices or final-test labels were used. Adjacent validation folds "
        "do not establish statistical significance or universal method superiority.\n\n"
    )
    text += "Evidence: [methods and eligibility](STATISTICAL_MODELS.md), "
    text += "[independent gate](../reports/forecasting/phase3c_gate.json).\n"
    (ROOT / "docs/STATISTICAL_RESULTS.md").write_text(text, encoding="utf-8")
    results.to_parquet(OUTPUT / "3c_model_summary.parquet", index=False)
    print(text)


def ml_report():
    gate, ml = load_gate("3d")
    _, baseline = load_gate("3b")
    _, statistical = load_gate("3c")
    folds = pd.concat([baseline, statistical[statistical.scope.eq("full")], ml], ignore_index=True)
    results = aggregate(folds)
    rows = []
    figure, axes = plt.subplots(1, 2, figsize=(15, 8), layout="constrained")
    for axis, dataset in zip(axes, ("store_item", "m5"), strict=True):
        chosen = results[results.dataset.eq(dataset)].sort_values("macro_mae")
        colors = [
            "#d87918" if m in ("random_forest", "lightgbm") else "#2463a0" for m in chosen.model
        ]
        bars = axis.barh(chosen.model.str.replace("_", " "), chosen.macro_mae, color=colors)
        axis.invert_yaxis()
        axis.set_xlim(0, chosen.macro_mae.max() * 1.2)
        axis.bar_label(bars, fmt="%.3f", padding=3, fontsize=9)
        axis.set_title(f"{dataset}: {int(chosen.series.iloc[0]):,} series")
        axis.set_xlabel("Mean four-fold macro MAE (sales units)")
        for row in chosen.itertuples():
            rows.append(
                [
                    dataset,
                    row.model,
                    f"{row.macro_mae:.6f}",
                    f"{row.pooled_rmse:.6f}",
                    f"{row.pooled_wape_percent:.4f}",
                    f"{row.bias_units:+.6f}",
                    f"{row.fallback_percent:.4f}",
                ]
            )
    figure.suptitle("Global ML and full-population comparators · fixed initial configurations")
    for ext in ("png", "svg"):
        figure.savefig(ROOT / f"reports/figures/phase3/phase3d_accuracy.{ext}", dpi=170)
    plt.close(figure)
    execution = json.loads((OUTPUT / "3d_execution.json").read_text())
    resources = []
    for dataset in ("store_item", "m5"):
        for model in ("random_forest", "lightgbm"):
            runs = [
                r
                for r in execution["runs"]
                if f"3d_{dataset}_" in r["tag"] and r["tag"].endswith(model)
            ]
            resources.append(
                [
                    dataset,
                    model,
                    f"{sum(r['elapsed_seconds'] for r in runs):.2f}",
                    f"{max(r['peak_worker_rss_bytes'] for r in runs) / 2**20:.2f}",
                ]
            )
    text = "# Phase 3D ML results\n\nStatus: COMPLETE; independent and automated gates passed.\n\n"
    text += "Orange bars identify ML; all 13 methods share each full evaluation population. "
    text += "ARIMA/SARIMA are reserved for the matched statistical-subset comparison.\n\n"
    text += markdown_table(
        ["Dataset", "Model", "Macro MAE", "Pooled RMSE", "WAPE %", "Bias units", "Fallback %"], rows
    )
    text += "\n\n![Full-population comparisons](../reports/figures/phase3/phase3d_accuracy.png)\n\n"
    text += markdown_table(
        ["Dataset", "ML model", "4-run worker seconds", "Maximum recorded RSS MiB"], resources
    )
    text += (
        "\n\nWorker times include cache/preparation, fitting, all 28 recursive steps, persistence "
    )
    text += "and scoring. They are not isolated fit times. Stage timings and estimator-fit times "
    text += "are retained in each run. All 16 runs passed complete persisted-prediction "
    text += "reconciliation, "
    text += "model reload checks, and independent comparison of every sampled training label and "
    text += (
        "feature against historical source data. Training uses 150,000/182,940 rows per origin; "
    )
    text += (
        "evaluation uses every 500/30,490 series. No tuning or final holdout access occurred.\n\n"
    )
    text += "See [fixed models](ML_FORECASTING.md), "
    text += "[availability assumptions](FEATURE_AVAILABILITY.md), "
    text += "and [independent gate](../reports/forecasting/phase3d_gate.json).\n"
    (ROOT / "docs/ML_RESULTS.md").write_text(text, encoding="utf-8")
    results.to_parquet(OUTPUT / "3d_model_summary.parquet", index=False)
    print(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["3b", "3c", "3d"], default="3b")
    args = parser.parse_args()
    {"3b": baseline_report, "3c": statistical_report, "3d": ml_report}[args.phase]()
