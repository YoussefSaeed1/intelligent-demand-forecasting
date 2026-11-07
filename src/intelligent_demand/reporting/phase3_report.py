"Offline scientific benchmark report from independently gated validation results only."

import argparse
import html
import json
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from intelligent_demand.experiments.benchmark import OUTPUT, ROOT, population
from intelligent_demand.experiments.config import load_experiment_config
from intelligent_demand.experiments.registry import ExperimentRegistry, atomic_json, file_digest
from intelligent_demand.models.baselines import BASELINES
from intelligent_demand.models.global_ml import ML_METHODS
from intelligent_demand.reporting.benchmark_report import aggregate, load_gate, markdown_table

FIGURES = ROOT / "reports/figures/phase3"
REPORTS = ROOT / "reports/forecasting"
COLORS = {"baseline": "#2463a0", "statistical": "#087f73", "ml": "#bd6012"}
DATASETS = ("store_item", "m5")


def family(model):
    return "baseline" if model in BASELINES else "ml" if model in ML_METHODS else "statistical"


def label(model):
    return model.replace("_", " ")


def metric_row(record, score, **extra):
    return {
        "dataset": record["dataset"],
        "scope": record["scope"],
        "model": record["model"],
        "fold": record["fold"],
        "run_id": record["run_id"],
        **extra,
        **{f"macro_{k}": v for k, v in score["macro"].items()},
        **{f"pooled_{k}": v for k, v in score["pooled"].items()},
        **{f"defined_{k}": v for k, v in score["coverage"]["defined_series"].items()},
        **{f"undefined_{k}": v for k, v in score["coverage"]["undefined_series"].items()},
        "series": score["coverage"]["series"],
        "observations": score["coverage"]["observations"],
        "fallback": score["coverage"]["fallback_observations"],
    }


def collect(gate):
    registry = ExperimentRegistry(
        load_experiment_config(ROOT / "configs/forecasting.yaml").registry_directory
    )
    resources = {
        row["run_id"]: row
        for phase in ("3b", "3c", "3d")
        for row in json.loads((OUTPUT / f"{phase}_execution.json").read_text())["runs"]
    }
    rows = {key: [] for key in ("horizon", "class", "volume", "resources", "coverage")}
    top = {
        dataset: set(
            population(dataset)
            .sort_values(["sales_units", "series_id"], ascending=[False, True])
            .head(len(population(dataset)) // 10)
            .series_id
        )
        for dataset in DATASETS
    }
    for record in gate["runs"]:
        state = registry.completed(record["run_id"])
        directory = registry.directory(record["run_id"])
        scores = json.loads((directory / state["outputs"]["metrics"]["path"]).read_text())
        for step, score in scores["by_horizon"].items():
            rows["horizon"].append(metric_row(record, score, horizon_step=int(step)))
        for pattern, score in scores["by_demand_class"].items():
            rows["class"].append(metric_row(record, score, pattern=pattern))
        rows["coverage"].append(metric_row(record, scores["all"]))
        if record["run_id"] in resources:
            r = resources[record["run_id"]]
            metadata = json.loads(
                (directory / state["outputs"]["model_metadata"]["path"]).read_text()
            )[0]
            rows["resources"].append(
                {
                    "dataset": record["dataset"],
                    "scope": record["scope"],
                    "model": record["model"],
                    "fold": record["fold"],
                    "run_id": record["run_id"],
                    "worker_seconds": r["elapsed_seconds"],
                    "peak_rss_mib": r["peak_worker_rss_bytes"] / 2**20,
                    "feature_preparation_seconds": metadata.get("feature_preparation_seconds"),
                    "estimator_fit_seconds": metadata.get("estimator_fit_seconds"),
                    **scores.get("runtime_stages", {}),
                }
            )
        evidence = record["errors"]
        path = ROOT / evidence["path"]
        if file_digest(path) != evidence["sha256"]:
            raise ValueError("Persisted error evidence changed after independent audit")
        if record["scope"] == "full":
            errors = pd.read_parquet(path, columns=["series_id", "actual", "error"])
            errors["band"] = np.where(
                errors.series_id.isin(top[record["dataset"]]), "top10", "other90"
            )
            errors["absolute_error"] = errors.error.abs()
            errors["squared_error"] = errors.error**2
            for band, group in errors.groupby("band"):
                rows["volume"].append(
                    {
                        "dataset": record["dataset"],
                        "model": record["model"],
                        "fold": record["fold"],
                        "band": band,
                        "actual": group.actual.sum(),
                        "absolute_error": group.absolute_error.sum(),
                        "squared_error": group.squared_error.sum(),
                        "observations": len(group),
                    }
                )
            del errors
    tables = {key: pd.DataFrame(value) for key, value in rows.items()}
    for key, frame in tables.items():
        frame.to_parquet(OUTPUT / f"3e_{key}_table.parquet", index=False)
    return tables


def save_figure(figure, name, purpose, figures):
    for extension in ("png", "svg"):
        figure.savefig(FIGURES / f"{name}.{extension}", dpi=175)
    plt.close(figure)
    figures.append({"name": name, "purpose": purpose})


def bar_comparison(results, scope, columns, titles, name, figures):
    figure, axes = plt.subplots(
        len(columns), 2, figsize=(16, 8 * len(columns)), squeeze=False, layout="constrained"
    )
    for j, dataset in enumerate(DATASETS):
        data = results[results.dataset.eq(dataset) & results.scope.eq(scope)].sort_values(
            "macro_mae"
        )
        for i, (column, title) in enumerate(zip(columns, titles, strict=True)):
            axis = axes[i, j]
            bars = axis.barh(
                data.model.map(label),
                data[column],
                color=data.model.map(lambda m: COLORS[family(m)]),
            )
            axis.invert_yaxis()
            axis.set_title(
                f"{dataset} · {scope.replace('_', ' ')} · {int(data.series.iloc[0]):,} series"
            )
            axis.set_xlabel(title)
            axis.axvline(0, color="#444444", linewidth=0.7)
            axis.grid(axis="x", alpha=0.16)
            axis.set_axisbelow(True)
            if column != "bias_units":
                axis.set_xlim(0, max(0.1, data[column].max() * 1.18))
                axis.bar_label(bars, fmt="%.3f", padding=3, fontsize=9)
    figure.suptitle(
        ("Four approved 28-day windows · blue baselines / green statistical / orange ML"),
        fontsize=14,
    )
    save_figure(figure, name, "; ".join(titles) + f"; {scope} matched populations", figures)


def focus_models(results, dataset):
    data = results[results.dataset.eq(dataset) & results.scope.eq("full")]
    best_stat = (
        data[data.model.map(family).eq("statistical")].sort_values("macro_mae").iloc[0].model
    )
    return list(
        dict.fromkeys(
            ["seasonal_naive", "moving_average_28", best_stat, "random_forest", "lightgbm"]
        )
    )


def detail_figures(results, tables, gate, figures):
    full = results[results.scope.eq("full")]
    horizon = tables["horizon"]
    figure, axes = plt.subplots(1, 2, figsize=(15, 6), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        for model in focus_models(results, dataset):
            points = horizon[
                horizon.dataset.eq(dataset) & horizon.scope.eq("full") & horizon.model.eq(model)
            ]
            points = points.groupby("horizon_step").macro_mae.mean().sort_index()
            axis.plot(points.index, points.values, label=label(model), linewidth=1.8)
        axis.set(
            title=f"{dataset} · full population",
            xlabel="Forecast horizon (days)",
            ylabel="Four-fold mean macro MAE (units)",
            xlim=(1, 28),
            ylim=(0, None),
        )
        axis.legend(fontsize=9)
        axis.grid(alpha=0.2)
    save_figure(
        figure,
        "phase3e_horizon",
        ("Horizon errors for seasonal naive, MA28, best statistical, RF and LightGBM"),
        figures,
    )
    figure, axes = plt.subplots(1, 2, figsize=(14, 9), layout="constrained")
    classes = tables["class"]
    for axis, dataset in zip(axes, DATASETS, strict=True):
        data = classes[classes.dataset.eq(dataset) & classes.scope.eq("full")]
        pivot = data.pivot_table(
            index="model", columns="pattern", values="macro_mae", aggfunc="mean"
        )
        ordered = full[full.dataset.eq(dataset)].sort_values("macro_mae").model
        pivot = pivot.reindex(ordered)
        image = axis.imshow(pivot, aspect="auto", cmap="Blues", vmin=0)
        axis.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=25, ha="right")
        axis.set_yticks(range(len(pivot)), pivot.index.map(label))
        for i in range(len(pivot)):
            for j in range(len(pivot.columns)):
                value = pivot.iloc[i, j]
                axis.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if value > np.nanmax(pivot.to_numpy()) * 0.55 else "black",
                )
        axis.set_title(f"{dataset} · full population\nFixed initial-origin demand classes")
        figure.colorbar(image, ax=axis, label="Four-fold mean class macro MAE (units)", shrink=0.65)
    save_figure(
        figure,
        "phase3e_demand_classes",
        ("Demand-class accuracy; separate dataset colour scales and fixed initial-origin classes"),
        figures,
    )
    figure, axes = plt.subplots(1, 2, figsize=(16, 9), layout="constrained")
    for axis, dataset in zip(axes, DATASETS, strict=True):
        times = tables["resources"]
        times = (
            times[times.dataset.eq(dataset) & times.scope.eq("full")]
            .groupby("model")
            .worker_seconds.sum()
        )
        markers = ("o", "s", "^", "D", "v", "P", "X", "<", ">", "*", "h", "p", "8")
        for number, row in enumerate(
            full[full.dataset.eq(dataset)].sort_values("model").itertuples()
        ):
            axis.scatter(
                times[row.model],
                row.macro_mae,
                color=COLORS[family(row.model)],
                marker=markers[number],
                label=label(row.model),
                s=85,
                alpha=0.85,
            )
        axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncols=2, fontsize=9)
        axis.set(
            title=f"{dataset} · full population",
            xlabel="Total worker wall time, four runs (seconds; log scale)",
            ylabel="Four-fold mean macro MAE (units)",
            ylim=(0, None),
        )
        axis.set_xscale("log")
        axis.margins(x=0.4, y=0.15)
        axis.grid(alpha=0.2)
    figure.suptitle(
        "Pipeline cost, including cached/first-use preparation, scoring an"
        "d persistence; not isolated fit speed"
    )
    save_figure(
        figure,
        "phase3e_runtime",
        ("Worker pipeline runtime versus accuracy; cold-cache costs included, full populations"),
        figures,
    )
    figure, axes = plt.subplots(2, 2, figsize=(16, 12), layout="constrained")
    for j, dataset in enumerate(DATASETS):
        coverage = full[full.dataset.eq(dataset)].sort_values("macro_mae")
        axes[0, j].barh(coverage.model.map(label), coverage.fallback_percent, color="#bd6012")
        axes[0, j].invert_yaxis()
        axes[0, j].set(
            title=f"{dataset}: 100% delivered coverage",
            xlabel="Fallback observations (%)",
            xlim=(0, max(0.1, coverage.fallback_percent.max() * 1.2)),
        )
        for model in focus_models(results, dataset):
            records = [
                r
                for r in gate["runs"]
                if r["dataset"] == dataset and r["scope"] == "full" and r["model"] == model
            ]
            records.sort(key=lambda r: r["fold"])
            axes[1, j].plot(
                [r["fold"] for r in records],
                [r["macro"]["mae"] for r in records],
                marker="o",
                label=label(model),
            )
        axes[1, j].set(
            title=f"{dataset}: origin stability",
            xlabel="Validation fold",
            ylabel="Macro MAE (units)",
            xticks=[1, 2, 3, 4],
            ylim=(0, None),
        )
        axes[1, j].legend(fontsize=9)
        axes[1, j].grid(alpha=0.2)
    save_figure(
        figure,
        "phase3e_coverage_stability",
        (
            "Full-population delivered coverage, explicit fallback rates and v"
            "alidation-origin stability"
        ),
        figures,
    )


def examples(results, gate, figures):
    representatives = []
    for dataset in DATASETS:
        saved = json.loads((OUTPUT / f"{dataset}_statistical_subset.json").read_text())
        # Use the already frozen population via audited subset errors, not outcome-based selection.
        one = next(
            r
            for r in gate["runs"]
            if r["dataset"] == dataset and r["scope"] == "statistical_subset"
        )
        ids = pd.read_parquet(
            ROOT / one["errors"]["path"], columns=["series_id"]
        ).series_id.unique()
        meta = population(dataset)
        meta = meta[meta.series_id.isin(ids)]
        for pattern, group in meta.groupby("pattern"):
            ordered = group.sort_values(["sales_units", "series_id"])
            representatives.append((dataset, pattern, ordered.iloc[len(ordered) // 2].series_id))
        if not saved:
            raise ValueError("Missing frozen population evidence")
    figure, axes = plt.subplots(
        len(representatives),
        1,
        figsize=(15, 4 * len(representatives)),
        squeeze=False,
        layout="constrained",
    )
    for axis, (dataset, pattern, series) in zip(axes[:, 0], representatives, strict=True):
        for i, model in enumerate(focus_models(results, dataset)):
            record = next(
                r
                for r in gate["runs"]
                if r["dataset"] == dataset
                and r["scope"] == "statistical_subset"
                and r["model"] == model
                and r["fold"] == 4
            )
            frame = pd.read_parquet(
                ROOT / record["errors"]["path"], filters=[("series_id", "==", series)]
            ).sort_values("target_date")
            if i == 0:
                axis.plot(
                    frame.target_date,
                    frame.actual,
                    color="black",
                    marker="o",
                    markersize=3,
                    linewidth=2,
                    label="actual sales",
                )
            axis.plot(frame.target_date, frame.prediction, label=label(model), alpha=0.85)
        axis.set(
            title=f"{dataset} · {pattern} · {series} · validation fold 4",
            ylabel="Daily sales units",
            ylim=(0, None),
            xlim=(frame.target_date.min(), frame.target_date.max()),
        )
        axis.legend(fontsize=9, ncols=3)
        axis.grid(alpha=0.2)
    figure.suptitle(
        "Examples selected by median initial-training volume within each f"
        "rozen-subset class; no error-based selection"
    )
    save_figure(
        figure,
        "phase3e_examples",
        (
            "Actual versus forecast: median initial-training-volume representa"
            "tive per subset demand class, fold 4"
        ),
        figures,
    )
    atomic_json(
        OUTPUT / "3e_example_selection.json",
        {
            "rule": (
                "median initial-training volume within fixed-subset class; no vali"
                "dation-error selection"
            ),
            "series": representatives,
        },
    )


def findings(results, tables, gate):
    text = []
    for dataset in DATASETS:
        full = results[results.dataset.eq(dataset) & results.scope.eq("full")].sort_values(
            "macro_mae"
        )
        best = full.iloc[0]
        sn = full[full.model.eq("seasonal_naive")].iloc[0]
        naive = full[full.model.eq("naive")].iloc[0]
        text.append(
            f"{dataset}: {best.model} has the lowest four-fold mean macro MAE "
            f"({best.macro_mae:.6f} units), "
            f"{100 * (1 - best.macro_mae / sn.macro_mae):.2f}% below Seasonal Naive and "
            f"{100 * (1 - best.macro_mae / naive.macro_mae):.2f}% below Naive "
            "on the full matched population."
        )
        for method in ML_METHODS:
            ml = full[full.model.eq(method)].iloc[0]
            stat = full[full.model.map(family).eq("statistical")].iloc[0]
            text.append(
                f"{dataset}: {method} MAE {ml.macro_mae:.6f}; "
                f"best full-population statistical method {stat.model} {stat.macro_mae:.6f}. "
                f"ML is {'lower' if ml.macro_mae < stat.macro_mae else 'higher'} by "
                f"{100 * abs(ml.macro_mae / stat.macro_mae - 1):.2f}%. "
                "These are fixed initial fits, not tuned-family ceilings."
            )
            wins = sum(
                next(
                    r["macro"]["mae"]
                    for r in gate["runs"]
                    if r["dataset"] == dataset
                    and r["scope"] == "full"
                    and r["model"] == method
                    and r["fold"] == fold
                )
                < next(
                    r["macro"]["mae"]
                    for r in gate["runs"]
                    if r["dataset"] == dataset
                    and r["scope"] == "full"
                    and r["model"] == stat.model
                    and r["fold"] == fold
                )
                for fold in range(1, 5)
            )
            text.append(
                f"{dataset}: {method} beats {stat.model} in {wins}/4 validation origins; "
                "this descriptive count does not imply statistical significance."
            )
        class_rows = tables["class"]
        class_rows = class_rows[class_rows.dataset.eq(dataset) & class_rows.scope.eq("full")]
        for pattern, group in class_rows.groupby("pattern"):
            means = group.groupby("model").macro_mae.mean().sort_values()
            text.append(
                f"{dataset}, initial class {pattern}: lowest mean class macro MAE is "
                f"{means.index[0]} ({means.iloc[0]:.6f}); Seasonal Naive "
                f"{means['seasonal_naive']:.6f}, RF {means['random_forest']:.6f}, "
                f"LightGBM {means['lightgbm']:.6f}. Class populations are fixed, "
                "not selected by forecast errors."
            )
        subset = results[results.dataset.eq(dataset) & results.scope.eq("statistical_subset")]
        subset_best = subset.sort_values("macro_mae").iloc[0]
        text.append(
            f"{dataset}, matched {int(subset_best.series)}-series subset: "
            f"{subset_best.model} has lowest MAE {subset_best.macro_mae:.6f}. "
            "This is a separate descriptive comparison, not a population estimate."
        )
        best_runs = [
            r
            for r in gate["runs"]
            if r["dataset"] == dataset and r["scope"] == "full" and r["model"] == best.model
        ]
        text.append(
            f"{dataset}: {best.model} fold MAEs range "
            f"{best.fold_mae_min:.6f}–{best.fold_mae_max:.6f}; four adjacent windows "
            "provide no independent-season or significance claim."
        )
        h = tables["horizon"]
        h = h[h.dataset.eq(dataset) & h.scope.eq("full") & h.model.eq(best.model)]
        early = h[h.horizon_step.le(7)].macro_mae.mean()
        late = h[h.horizon_step.ge(22)].macro_mae.mean()
        text.append(
            f"{dataset}: {best.model} mean MAE days 1–7 is {early:.6f}, "
            f"days 22–28 {late:.6f}. Horizon deterioration is assessed empirically, "
            "not assumed monotonic."
        )
        volume = tables["volume"]
        volume = (
            volume[volume.dataset.eq(dataset) & volume.model.eq(best.model)]
            .groupby("band")
            .sum(numeric_only=True)
        )
        text.append(
            f"{dataset}: the top 10% of series by initial-training volume contribute "
            f"{100 * volume.loc['top10', 'actual'] / volume.actual.sum():.2f}% "
            "of validation sales, "
            f"{100 * volume.loc['top10', 'absolute_error'] / volume.absolute_error.sum():.2f}% "
            "of absolute error and "
            f"{100 * volume.loc['top10', 'squared_error'] / volume.squared_error.sum():.2f}% "
            f"of squared error for {best.model}. Pooled RMSE can therefore emphasise "
            "high-volume misses; macro MAE gives series equal weight."
        )
        undefined = Counter()
        for run in best_runs:
            undefined.update(run["coverage"]["undefined_series"])
        text.append(
            f"{dataset}: undefined series-origin metrics for {best.model}: "
            + ", ".join(f"{key}={value}" for key, value in sorted(undefined.items()))
            + (
                ". Nulls remain excluded only from that metric's macro mean, with "
                "coverage reported."
            )
        )
    return text


def comparison_table(results):
    rows = []
    for (dataset, scope), group in results.groupby(["dataset", "scope"]):
        for row in group.sort_values("macro_mae").itertuples():
            rows.append(
                [
                    dataset,
                    scope,
                    row.model,
                    row.series,
                    f"{row.macro_mae:.6f}",
                    f"{row.pooled_rmse:.6f}",
                    f"{row.pooled_wape_percent:.4f}",
                    f"{row.bias_units:+.6f}",
                    f"{row.macro_mase:.6f}",
                    f"{row.macro_rmsse:.6f}",
                    f"{row.fallback_percent:.4f}",
                ]
            )
    return markdown_table(
        [
            "Dataset",
            "Population",
            "Model",
            "Series/fold",
            "Macro MAE",
            "Pooled RMSE",
            "WAPE %",
            "Bias units",
            "Macro MASE",
            "Macro RMSSE",
            "Fallback %",
        ],
        rows,
    )


def build_report():
    gate, folds = load_gate("3e")
    results = aggregate(folds)
    results.to_parquet(OUTPUT / "3e_model_summary.parquet", index=False)
    folds.to_parquet(OUTPUT / "3e_origin_table.parquet", index=False)
    tables = collect(gate)
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    figures = []
    bar_comparison(
        results,
        "full",
        ["macro_mae", "pooled_rmse"],
        [
            "Mean four-fold macro MAE (sales units)",
            "Pooled RMSE across all four folds (sales units)",
        ],
        "phase3e_accuracy",
        figures,
    )
    bar_comparison(
        results,
        "full",
        ["pooled_wape_percent", "bias_units"],
        ["Pooled WAPE (%)", "Pooled signed bias (sales units; positive = overforecast)"],
        "phase3e_wape_bias",
        figures,
    )
    bar_comparison(
        results,
        "statistical_subset",
        ["macro_mae"],
        ["Mean four-fold macro MAE (sales units)"],
        "phase3e_matched_subset",
        figures,
    )
    detail_figures(results, tables, gate, figures)
    bar_comparison(
        results,
        "statistical_subset",
        ["fallback_percent"],
        ["Fallback observations (%)"],
        "phase3e_subset_fallbacks",
        figures,
    )
    examples(results, gate, figures)
    narrative = findings(results, tables, gate)
    comparison = comparison_table(results)
    heading = (
        "# Phase 3 benchmark report\n\nStatus: COMPLETE; scientific and automated gates passed.\n\n"
    )
    text = heading + "## Verified scope\n\n"
    text += (
        "Thirteen methods share full-population evaluation (500 Store Item"
        " and 30,490 M5 series). Fifteen share the frozen 53/51-series sta"
        "tistical subsets, including ARIMA and SARIMA. All use the four ap"
        "proved 28-day validation windows. Subset means are unweighted, de"
        "liberately stratified and cannot estimate population performance."
        " Projected forecasts reuse fitted full-population models without "
        "refitting.\n\n"
    )
    text += f"The independent final audit verified {len(gate['runs'])} saved evaluations and "
    text += f"{sum(r['coverage']['observations'] for r in gate['runs']):,} forecast records, "
    text += "including subset projections of the same underlying forecasts. "
    text += "No final holdout target was used.\n\n"
    text += "## Findings\n\n" + "\n\n".join(narrative) + "\n\n"
    text += "## Matched model comparisons\n\n" + comparison + "\n\n"
    text += (
        "MAE/MASE/RMSSE average the four fold macro values. Pooled RMSE is"
        " the square root of summed squared errors divided by total observ"
        "ations; pooled WAPE is summed absolute error divided by total act"
        "ual units. Bias is predicted minus actual. Undefined scales and z"
        "ero-actual ratios stay null. Every method delivered the complete "
        "declared grid; explicit fallbacks remain in delivered-system scor"
        "es. Native-only scores in the gate use different counted populati"
        "ons and are not used for unmatched rankings.\n\n"
    )
    text += "## Demand classes, horizons and hierarchy\n\n"
    text += (
        "Classes are frozen from initial-training data, never retrospectiv"
        "ely reclassified using validation. The class, horizon and origin "
        "tables retain exact counts and defined/undefined metrics. Store/p"
        "roduct/category/department/state tables contain grouped leaf-seri"
        "es errors, not aggregate-node forecast errors or official M5 WRMS"
        "SE. Cross-dataset evidence supports methodological comparison; di"
        "fferent periods, scale, product definitions and feature availabil"
        "ity do not justify direct model transfer.\n\n"
    )
    text += "## Resources and failures\n\n"
    resource_summary = (
        tables["resources"]
        .groupby(["dataset", "scope", "model"])
        .agg(
            worker_seconds=("worker_seconds", "sum"),
            peak_rss_mib=("peak_rss_mib", "max"),
            estimator_fit_seconds=("estimator_fit_seconds", lambda x: x.sum(min_count=1)),
        )
        .reset_index()
    )
    text += (
        markdown_table(
            [
                "Dataset",
                "Population",
                "Model",
                "4-run worker seconds",
                "Max recorded RSS MiB",
                "Estimator-fit seconds (ML only)",
            ],
            [
                [
                    r.dataset,
                    r.scope,
                    r.model,
                    f"{r.worker_seconds:.2f}",
                    f"{r.peak_rss_mib:.2f}",
                    f"{r.estimator_fit_seconds:.2f}"
                    if pd.notna(r.estimator_fit_seconds)
                    else "not recorded",
                ]
                for r in resource_summary.itertuples()
            ],
        )
        + "\n\n"
    )
    text += (
        "All 120 original fits ran sequentially under predefined budgets. "
        "Resource tables retain original worker wall times and recorded RS"
        "S/working-set peaks; projections incur no refitting. Wall times i"
        "nclude source/cache checks, preparation, inference, persistence a"
        "nd scoring. Cold preparation is charged to the first method; olde"
        "r baseline runs have no separate stage timings, so these points d"
        "o not establish intrinsic algorithm speed. Later ML runs retain s"
        "eparate feature-preparation and estimator-fit timing.\n\n"
    )
    for dataset in DATASETS:
        for model in ("arima_100", "sarima_100_100_7"):
            records = [r for r in gate["runs"] if r["dataset"] == dataset and r["model"] == model]
            reasons = Counter()
            for r in records:
                reasons.update(r["fallback_reason_series"])
            text += f"- {dataset}/{model}: {dict(reasons) if reasons else 'no fallbacks'} "
            text += "(series-origin cases).\n"
    text += "\n## Fixed initial methodology and Phase 4 candidates\n\n"
    text += (
        "Preserve Naive, Seasonal Naive, MA28 and seasonal moving average "
        "as reference methods. Prioritise each dataset's strongest validat"
        "ed statistical and ML candidates with declared search spaces and "
        "budgets; inspect bias, sparse-demand coverage and origin stabilit"
        "y as well as MAE. Retain intermittent-demand comparators for M5. "
        "Fixed initial RF/LightGBM training is bounded (150,000/182,940 ro"
        "ws per origin); sample-size, categorical representation and multi"
        "-step strategy are explicit future optimisation questions. No sys"
        "tematic search or final test evaluation has run.\n\n"
    )
    text += (
        "The mandatory independent Claude audit remains after Phase 4 and "
        "before Phase 5. Inventory, dashboards, applications and deploymen"
        "t have not started.\n\n"
    )
    text += "## Figures and inspectable evidence\n\n"
    for fig in figures:
        text += f"### {fig['purpose']}\n\n"
        text += f"![{fig['purpose']}](../reports/figures/phase3/{fig['name']}.png)\n\n"
    text += (
        "Technical evidence: `reports/forecasting/phase3e_gate.json`; per-"
        "origin/class/horizon/resource/volume/coverage tables, hierarchy t"
        "ables and complete per-run errors under ignored `artifacts/experi"
        "ments/phase3/`. Dataset and protocol hashes remain unchanged. Sou"
        "rce-backed report generation: `python -m intelligent_demand.repor"
        "ting.phase3_report`.\n"
    )
    (ROOT / "docs/PHASE3_BENCHMARK_REPORT.md").write_text(text, encoding="utf-8")
    (ROOT / "docs/PHASE3_MODEL_COMPARISON.md").write_text(
        "# Phase 3 model comparison\n\n"
        + comparison
        + (
            "\n\nSeparate populations; fixed initial configurations; no signific"
            "ance claim. See [benchmark interpretation](PHASE3_BENCHMARK_REPOR"
            "T.md).\n"
        ),
        encoding="utf-8",
    )
    index = (
        "# Forecasting visualisation index\n\nAll figures use independently "
        "verified validation predictions. PNG and SVG pairs share identica"
        "l plotted data.\n\n"
    )
    index += markdown_table(
        ["Figure", "Purpose", "Relative PNG path", "Relative SVG path"],
        [
            [
                f["name"],
                f["purpose"],
                f"../figures/phase3/{f['name']}.png",
                f"../figures/phase3/{f['name']}.svg",
            ]
            for f in figures
        ],
    )
    (REPORTS / "VISUALISATION_INDEX.md").write_text(index + "\n", encoding="utf-8")
    sections = [
        "<section id='findings'><h2>Verified findings</h2>"
        + "".join(f"<p>{html.escape(p)}</p>" for p in narrative)
        + "</section>"
    ]
    for scope in ("full", "statistical_subset"):
        selected = results[results.scope.eq(scope)].sort_values(["dataset", "macro_mae"])
        columns = [
            "dataset",
            "model",
            "series",
            "macro_mae",
            "pooled_rmse",
            "pooled_wape_percent",
            "bias_units",
            "macro_mase",
            "macro_rmsse",
            "fallback_percent",
        ]
        sections.append(
            f"<section id='{scope}'><h2>{scope.replace('_', ' ').title()} comparisons</h2>"
            "<div class='scroll'>"
            + selected[columns].to_html(
                index=False, float_format=lambda v: f"{v:.4f}", border=0, na_rep="undefined"
            )
            + "</div></section>"
        )
    for fig in figures:
        sections.append(
            f"<section id='{fig['name']}'><h2>{html.escape(fig['purpose'])}</h2><figure>"
            f"<img src='../figures/phase3/{fig['name']}.png' "
            f"alt='{html.escape(fig['purpose'], quote=True)}' loading='lazy'>"
            f"<figcaption><a href='../figures/phase3/{fig['name']}.svg'>Open SVG</a>"
            "</figcaption></figure></section>"
        )
    sections.append(
        "<section id='limits'><h2>Interpretation and limitations</h2><p>Fi"
        "xed initial configurations; bounded ML training; full evaluation."
        " Four adjacent windows do not establish significance. Stratified "
        "subsets are separate, unweighted comparisons. Missing historical "
        "prices remain missing; future events/SNAP/prices are excluded. Hi"
        "storical price publication latency is unknown. Point forecasts ar"
        "e recursively fed back, while observed activity/price context sta"
        "ys frozen.</p><p>Pipeline wall times include cached and cold prep"
        "aration. Grouped hierarchy results are leaf-series errors, not of"
        "ficial M5 WRMSSE. Source sales can be stock constrained. Direct m"
        "odel transfer has not been demonstrated. Protected final holdouts"
        " remain untouched.</p><p><a href='../../docs/PHASE3_BENCHMARK_REP"
        "ORT.md'>Full scientific report</a> · <a href='phase3e_gate.json'>"
        "Independent gate</a> · <a href='VISUALISATION_INDEX.md'>Figure in"
        "dex</a></p></section>"
    )
    nav = (
        (
            "<nav><a href='#findings'>Findings</a><a href='#full'>Full populat"
            "ions</a><a href='#statistical_subset'>Matched subsets</a>"
        )
        + "".join(
            f"<a href='#{f['name']}'>"
            f"{html.escape(f['name'].replace('phase3e_', '').replace('_', ' ').title())}</a>"
            for f in figures
        )
        + "<a href='#limits'>Limitations</a></nav>"
    )
    document = (
        (
            "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta "
            "name='viewport' content='width=device-width,initial-scale=1'><tit"
            "le>Phase 3 forecasting benchmark</title><style>body{font:16px/1.6"
            " system-ui,sans-serif;color:#192c40;background:#eef2f5;margin:0}h"
            "eader,main,nav{max-width:1400px;margin:auto;padding:24px}header{b"
            "ackground:#173a55;color:white;max-width:none}header>div{max-width"
            ":1400px;margin:auto}nav{display:flex;flex-wrap:wrap;gap:14px}a{co"
            "lor:#185d91}section{background:white;padding:24px;margin:20px 0;b"
            "order-radius:8px}h1{font-size:2.2rem}h2{line-height:1.3}img{displ"
            "ay:block;width:100%;height:auto}figure{margin:0}.scroll{overflow:"
            "auto}table{border-collapse:collapse;font-size:.9rem;width:100%}th"
            ",td{padding:9px;border-bottom:1px solid #dbe2e8;text-align:right}"
            "th{background:#edf3f7}footer{padding:24px}@media(max-width:650px)"
            "{main,nav{padding:10px}section{padding:12px}h1{font-size:1.6rem}}"
            "</style></head><body><header><div><p>INTELLIGENT DEMAND FORECASTI"
            "NG &amp; INVENTORY OPTIMISATION</p><h1>Phase 3 · Forecasting benc"
            "hmark</h1><p>Four approved origins · 28-day forecasts · fixed ini"
            "tial configurations · validation only</p><p>500 Store Item / 30,4"
            "90 M5 full-population series; 53 / 51 matched statistical-subset "
            "series.</p></div></header>"
        )
        + nav
        + "<main>"
        + "".join(sections)
        + (
            "</main><footer>Local offline report · no external fonts, scripts "
            "or assets · Phase 4 not started</footer></body></html>"
        )
    )
    (REPORTS / "PHASE3_BENCHMARK_REPORT.html").write_text(document, encoding="utf-8")
    atomic_json(
        OUTPUT / "3e_report_manifest.json",
        {
            "figures": figures,
            "gate_sha256": file_digest(REPORTS / "phase3e_gate.json"),
            "scope": "validation_only",
            "findings": narrative,
        },
    )
    print(
        json.dumps(
            {"status": "generated", "figure_pairs": len(figures), "findings": narrative}, indent=2
        )
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    build_report()
