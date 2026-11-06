"""Publication figures and source-backed Markdown reports from small analytical tables."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import EngFormatter, FixedLocator, FuncFormatter, NullFormatter

from intelligent_demand.config import ProjectConfig
from intelligent_demand.exploration.statistics import PATTERNS
from intelligent_demand.ingestion.datasets import write_json

COLORS = {
    "store_item": "#2463a0",
    "m5": "#c47a28",
    "smooth": "#2463a0",
    "erratic": "#b24d78",
    "intermittent": "#b7a53b",
    "lumpy": "#617f3d",
    "all_zero": "#7c858c",
    "insufficient_positive_history": "#bfbfbf",
}
LABELS = {"store_item": "Store Item", "m5": "M5"}


def _load(config: ProjectConfig, dataset: str, name: str) -> pd.DataFrame:
    return pd.read_parquet(config.paths["reports"] / "eda/tables" / dataset / f"{name}.parquet")


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "grid.alpha": 0.2,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "svg.fonttype": "none",
        }
    )


def _dates(axis, values) -> None:
    values = pd.DatetimeIndex(values)
    # Annual ticks keep nearby boundary dates from acquiring overlapping labels.
    ticks = list(pd.date_range(values.min(), values.max(), freq="YS"))
    axis.set_xticks(ticks if ticks else [values.min(), values.max()])
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axis.tick_params(axis="x", labelrotation=0)


def _save(config: ProjectConfig, fig, name: str, result: dict, title: str) -> None:
    directory = config.paths["reports"] / "figures/phase2"
    directory.mkdir(parents=True, exist_ok=True)
    scope = result["split_plan"]
    fig.suptitle(title, fontsize=15, x=0.07, ha="left")
    fig.text(
        0.07,
        0.015,
        f"{LABELS[result['dataset']]} | EDA: {scope['eda_start']}–{scope['eda_end']} | "
        f"{result['series']:,} series; observed sales, not unconstrained demand",
        fontsize=8,
    )
    fig.tight_layout(rect=(0.02, 0.04, 0.99, 0.93))
    stem = f"{result['dataset']}_{name}"
    fig.savefig(directory / f"{stem}.png", dpi=result["settings"]["figure_dpi"])
    fig.savefig(directory / f"{stem}.svg")
    plt.close(fig)


def figures(config: ProjectConfig, result: dict) -> None:
    _style()
    name = result["dataset"]
    color = COLORS[name]

    def load(table):
        return _load(config, name, table)

    distribution = load("distribution")
    daily, monthly = load("daily"), load("monthly")
    series, patterns = load("series"), load("patterns")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(distribution.units, distribution.observations, color=color, width=0.95)
    axes[0].set_yscale("log")
    axes[0].set(
        xlabel="Units per store-product day",
        ylabel="Observations (log scale)",
        title="Exact empirical frequencies, including zeros",
    )
    positive = distribution[distribution.units > 0]
    axes[1].step(
        positive.units,
        positive.observations.cumsum() / positive.observations.sum(),
        where="post",
        color=color,
    )
    axes[1].set(
        xlabel="Positive sales units",
        ylabel="Cumulative positive-observation share",
        ylim=(0, 1),
        title="Positive-sales distribution",
    )
    _save(config, fig, "distribution", result, "Daily sales distributions")

    fig, axes = plt.subplots(2, 1, figsize=(11, 6.2))
    axes[0].plot(daily.date, daily.sales_units, color="#adb4bb", linewidth=0.7, label="Daily total")
    axes[0].plot(
        daily.date, daily.mean_28d, color=color, linewidth=1.5, label="Trailing 28-day mean"
    )
    axes[0].legend(frameon=False, ncol=2)
    axes[0].set(ylabel="Sales units/day")
    _dates(axes[0], daily.date)
    complete = monthly[monthly.complete_month]
    axes[1].plot(
        pd.to_datetime(complete.month), complete.sales_units, color=color, marker="o", markersize=3
    )
    axes[1].set(ylabel="Sales units/month", title="Complete calendar months only")
    _dates(axes[1], pd.to_datetime(complete.month))
    for ax in axes:
        ax.yaxis.set_major_formatter(EngFormatter())
        ax.grid(axis="y")
    _save(config, fig, "trends", result, "Daily and monthly observed sales")

    weekday, month_year = load("weekdays"), load("month_year")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].errorbar(
        weekday.weekday,
        weekday.mean_within_week_ratio,
        yerr=[
            weekday.mean_within_week_ratio - weekday.ci_low,
            weekday.ci_high - weekday.mean_within_week_ratio,
        ],
        color=color,
        marker="o",
        capsize=4,
        linestyle="none",
    )
    axes[0].axhline(1, color="#333333", linestyle="--", linewidth=0.8)
    axes[0].set_xticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    axes[0].set(
        ylabel="Sales / within-week daily mean",
        title="95% pointwise 4-week-block bootstrap intervals",
    )
    for _, frame in month_year.groupby("year"):
        axes[1].plot(frame.month, frame.within_year_daily_index, color="#b5bbc1", linewidth=0.8)
    means = month_year.groupby("month").within_year_daily_index.mean()
    axes[1].plot(means.index, means, color=color, marker="o", linewidth=1.5)
    axes[1].axhline(1, color="#333333", linestyle="--", linewidth=0.8)
    axes[1].set_xticks(range(1, 13))
    axes[1].set(
        xlabel="Calendar month",
        ylabel="Monthly mean / annual daily mean",
        title="Complete years; gray lines show individual years",
    )
    _save(config, fig, "calendar_patterns", result, "Weekly and annual calendar structure")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for label in PATTERNS[:4]:
        selected = series[series.pattern == label]
        if selected.empty:
            continue
        axes[0].scatter(
            selected.adi,
            selected.cv2_positive.clip(lower=0.001),
            s=6,
            alpha=0.25,
            color=COLORS[label],
            label=label.capitalize(),
            rasterized=True,
        )
    axes[0].axvline(
        result["settings"]["adi_threshold"], color="#333", linestyle="--", linewidth=0.8
    )
    axes[0].axhline(
        result["settings"]["cv2_threshold"], color="#333", linestyle="--", linewidth=0.8
    )
    axes[0].set(
        xscale="log",
        yscale="log",
        xlabel="ADI (daily periods, log scale)",
        ylabel="Positive-size CV² (log scale)",
        title="Defined statistics only; CV²=0 shown at 0.001",
    )
    axes[0].legend(frameon=False, fontsize=8)
    max_adi = max(1.5, float(series.adi.dropna().max()) * 1.05)
    axes[0].set_xlim(0.95, max_adi)
    ticks = (
        [1, 1.32] if max_adi < 3 else [value for value in (1, 10, 100, 1000) if value <= max_adi]
    )
    axes[0].xaxis.set_major_locator(FixedLocator(ticks))
    axes[0].xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    axes[0].xaxis.set_minor_formatter(NullFormatter())
    labels = [p.replace("_", " ").capitalize() for p in patterns.pattern]
    labels = [
        label.replace("Insufficient positive history", "Insufficient positive\nhistory")
        for label in labels
    ]
    bars = axes[1].barh(
        labels,
        100 * patterns.series / result["series"],
        color=[COLORS[p] for p in patterns.pattern],
    )
    axes[1].bar_label(bars, labels=[f"{v:,}" for v in patterns.series], padding=3, fontsize=8)
    axes[1].set(
        xlabel="Percentage of all series",
        xlim=(0, 110),
        title="Full-window ADI/CV² descriptive classes",
    )
    axes[1].invert_yaxis()
    _save(config, fig, "intermittency", result, "Daily-sales intermittency and variability")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(series.zero_percent, bins=np.linspace(0, 100, 21), color=color, rwidth=0.96)
    axes[0].set(xlabel="Zero-sales observations per series (%)", ylabel="Series", xlim=(0, 100))
    cv = (series.std_units / series.mean_units.replace(0, np.nan)).dropna()
    positive_cv = cv[cv > 0]
    axes[1].hist(
        positive_cv,
        bins=np.geomspace(positive_cv.min(), positive_cv.max() * 1.001, 30),
        color=color,
    )
    axes[1].set(
        xscale="log",
        xlabel="Series CV of all daily sales (log scale)",
        ylabel="Series",
        title=f"Positive CV only; {(cv == 0).sum()} constant series excluded",
    )
    _save(config, fig, "zeros_variability", result, "Sales sparsity and variability")

    products = load("products")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    ordered = products.sort_values("sales_units")
    axes[0].plot(
        np.arange(1, len(ordered) + 1) / len(ordered),
        ordered.sales_units.cumsum() / ordered.sales_units.sum(),
        color=color,
    )
    axes[0].plot([0, 1], [0, 1], color="#777", linestyle="--", linewidth=0.8)
    axes[0].set(
        xlabel="Cumulative product share (ascending sales)",
        ylabel="Cumulative sales-unit share",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    top = products.head(10).iloc[::-1]
    axes[1].barh(top.item_id, top.sales_units, color=color)
    axes[1].set(xlabel="Total observed sales units", title="Ten highest-volume products")
    axes[1].xaxis.set_major_formatter(EngFormatter())
    _save(config, fig, "concentration", result, "Product sales concentration")

    stores = load("stores")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(stores.store_id, stores.mean_units_per_series_day, color=color)
    axes[0].set(ylabel="Units per store-product day", title="Exposure-adjusted store comparison")
    axes[1].bar(stores.store_id, stores.mean_zero_percent, color=color)
    axes[1].set(
        ylabel="Zero-sales observations (%)",
        title="Store sparsity, same observed daily grid",
        ylim=(0, 100),
    )
    _save(config, fig, "stores", result, "Store-level volume and sparsity")

    components, correlations = load("components"), load("acf")
    fig, axes = plt.subplots(3, 1, figsize=(11, 8))
    axes[0].plot(
        components.date,
        components.log_sales,
        color="#aab2bb",
        linewidth=0.7,
        label="log(1 + aggregate sales)",
    )
    axes[0].plot(
        components.date,
        components.trend_after_weekly,
        color=color,
        label="STL trend after seasonal removal",
    )
    axes[0].set(ylabel="Log units")
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].plot(components.date, components.annual_component_after_weekly, color=color)
    axes[1].set(
        ylabel="Log seasonal component",
        title="365-day diagnostic after weekly removal; leap-calendar approximation",
    )
    axes[2].plot(correlations.lag, correlations.log_first_difference_acf, color=color, linewidth=1)
    axes[2].axhline(0, color="#333", linewidth=0.8)
    for lag in (7, 28, 365):
        axes[2].axvline(lag, color="#aaa", linestyle="--", linewidth=0.7)
    axes[2].set(
        xlabel="Daily lag",
        ylabel="Aggregate ACF",
        title="First difference of log(1 + sales); no iid significance bands",
    )
    for ax in axes[:2]:
        _dates(ax, components.date)
    _save(config, fig, "diagnostics", result, "Trend, annual structure and serial dependence")

    fig, axes = plt.subplots(2, 1, figsize=(11, 5.5))
    axes[0].plot(daily.date, daily.cv_28d, color=color)
    axes[0].set(
        ylabel="28-day coefficient of variation", title="Local variation in aggregate daily sales"
    )
    axes[1].plot(daily.date, daily.zero_percent, color=color)
    axes[1].set(
        ylabel="Zero-sales series (%)", ylim=(0, 100), title="Daily breadth of zero observed sales"
    )
    for ax in axes:
        _dates(ax, daily.date)
    _save(config, fig, "volatility", result, "Volatility and zero-sales breadth over time")

    representatives = load("representative_series")
    groups = list(representatives.groupby("pattern", sort=False))
    fig, axes = plt.subplots(len(groups), 1, figsize=(11, max(3, 2.2 * len(groups))), squeeze=False)
    for ax, (pattern, frame) in zip(axes[:, 0], groups, strict=True):
        frame = frame.tail(180)
        ax.plot(frame.date, frame.sales_units, color=COLORS[pattern], linewidth=0.8)
        ax.set(
            ylabel="Units/day", title=f"{pattern}: {frame.series_id.iloc[0]} (individual y-scale)"
        )
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    _save(
        config,
        fig,
        "representatives",
        result,
        "Median-ranked class illustrations: last 180 EDA days",
    )
    if name == "m5":
        _price_figures(config, result)


def _price_figures(config: ProjectConfig, result: dict) -> None:
    def load(name):
        return _load(config, "m5", name)

    dates, years = load("price_by_date_full_quality"), load("price_by_year_full_quality")
    stores, products = load("price_by_store_full_quality"), load("price_by_product_full_quality")
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    axes[0, 0].plot(dates.date, 100 * dates.missing_prices / dates.observations, color=COLORS["m5"])
    cutoff = pd.Timestamp(result["split_plan"]["eda_end"])
    axes[0, 0].axvline(cutoff, color="#333", linestyle="--", linewidth=1)
    axes[0, 0].axvspan(
        cutoff, dates.date.max(), color="#eee", label="Reserved: price coverage only"
    )
    axes[0, 0].legend(frameon=False, fontsize=8)
    axes[0, 0].set(
        ylabel="Missing prices (%)", ylim=(0, 100), title="Full-history label-free price coverage"
    )
    _dates(axes[0, 0], dates.date)
    parts = result["price_missingness"]["eda_activity_partition"]
    keys = [
        "missing_before_first_positive",
        "missing_between_first_last_positive",
        "missing_after_last_positive",
        "missing_no_positive_in_eda",
    ]
    labels = [
        "Before first positive",
        "Within positive span",
        "After last positive",
        "No positive in EDA",
    ]
    axes[0, 1].barh(labels, [parts[k] for k in keys], color=COLORS["m5"])
    axes[0, 1].set(
        xlabel="Missing-price observations",
        title="EDA sales activity proxies, not stock availability",
    )
    axes[0, 1].xaxis.set_major_formatter(EngFormatter())
    axes[1, 0].bar(
        stores.store_id, 100 * stores.missing_prices / stores.observations, color=COLORS["m5"]
    )
    axes[1, 0].set(ylabel="Missing prices (%)", ylim=(0, 100), title="Full-history store coverage")
    axes[1, 1].bar(
        years.year.astype(str), 100 * years.missing_prices / years.observations, color=COLORS["m5"]
    )
    axes[1, 1].set(
        ylabel="Missing prices (%)",
        ylim=(0, 100),
        title="Full-history year coverage (boundary years partial)",
    )
    _save(
        config,
        fig,
        "price_missingness",
        result,
        "Historical price missingness: full quality coverage and EDA activity",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(
        100 * products.missing_prices / products.observations,
        bins=np.linspace(0, 100, 21),
        color=COLORS["m5"],
    )
    axes[0].set(
        xlabel="Product missing-price observations (%)",
        ylabel="Products",
        title="Full-history product coverage",
    )
    activity, series = load("price_by_series_eda"), load("series")
    axes[1].scatter(
        series.zero_percent,
        100 * activity.missing_prices / result["eda_days"],
        s=3,
        alpha=0.08,
        color=COLORS["m5"],
        rasterized=True,
    )
    axes[1].set(
        xlabel="EDA zero-sales percentage",
        ylabel="EDA missing-price percentage",
        xlim=(0, 100),
        ylim=(0, 100),
        title="All series; association does not establish causality",
    )
    _save(
        config, fig, "price_products", result, "Price coverage varies by product and sales history"
    )
    events = load("calendar_events").sort_values("mean_total_units").head(10)
    category = load("cat_id_daily")
    metadata = load("series")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].barh(
        [f"{r.event} (n={r.days})" for r in events.itertuples()],
        events.mean_total_units,
        color=COLORS["m5"],
    )
    axes[0].set(
        xlabel="Mean aggregate units on event dates",
        title="Ten lowest-mean named events; descriptive association",
    )
    axes[0].xaxis.set_major_formatter(EngFormatter())
    for number, (group, frame) in enumerate(category.groupby("group")):
        exposure = int(metadata.cat_id.eq(group).sum())
        smoothed = (frame.sales_units / exposure).rolling(28).mean()
        axes[1].plot(
            frame.date, smoothed, color=["#2463a0", "#c47a28", "#617f3d"][number], label=group
        )
    axes[1].set(
        ylabel="Trailing mean units per series/day",
        title="Product-category differences, normalised by series count",
    )
    axes[1].legend(frameon=False, fontsize=8)
    _dates(axes[1], category.date)
    _save(config, fig, "events_groups", result, "Calendar associations and product groups")


def dataset_report(config: ProjectConfig, result: dict) -> None:
    name, plan = result["dataset"], result["split_plan"]
    directory = config.paths["reports"] / "eda"
    groups = sorted(result["patterns"].items(), key=lambda pair: -pair[1])
    weekday = pd.DataFrame(result["weekday_ratios"])
    peak = weekday.iloc[weekday.mean_within_week_ratio.argmax()]
    trough = weekday.iloc[weekday.mean_within_week_ratio.argmin()]
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    lines = [
        f"# {LABELS[name]}: sales patterns and forecasting implications",
        "",
        "## Executive summary",
        "",
        f"- Across all {result['series']:,} series, {result['eda_zero_percent']:.4f}% "
        f"of EDA observations are zero sales.",
        f"- The largest full-window descriptive class is {groups[0][0]} ({groups[0][1]:,} series). "
        f"Removing leading zeros changes "
        f"{result['classification_changed_after_removing_leading_zeros']:,} class assignments.",
        f"- The top 10% of products account for "
        f"{100 * result['product_top10_percent_share']:.2f}% of EDA sales units.",
        "",
        "## Scope and holdout protection",
        "",
        f"All series are included; EDA targets cover **{plan['eda_start']}–{plan['eda_end']}** "
        f"({result['eda_rows']:,} observations). Four later 28-day validation windows "
        f"and the final "
        "28-day holdout were reserved before detailed exploration. Full-history figures below "
        "are Phase 1 reconciliation references, not model-selection evidence.",
        "",
        f"Full-history reference: {result['full_history_reference']['rows']:,} rows and "
        f"{result['full_history_reference']['sales_units']:,} units, independently "
        f"rechecked while scanning.",
        "",
        "## Distribution, scale and concentration",
        "",
        f"EDA sales total: **{result['eda_sales_units']:,} units**. Exact empirical unit quantiles "
        f"(inverse CDF): `{result['distribution_quantiles']}`. Median series "
        f"coefficient of variation "
        f"of all daily sales is {result['median_series_cv']:.3f}. Largest observed quantities are "
        "retained in the largest_observations table; they are not automatically "
        "labelled errors or removed.",
        "",
        f"![Sales distribution](../figures/phase2/{name}_distribution.png)",
        f"![Daily and monthly trends](../figures/phase2/{name}_trends.png)",
        f"![Product concentration](../figures/phase2/{name}_concentration.png)",
        f"![Store comparisons](../figures/phase2/{name}_stores.png)",
        "",
        "## Calendar structure, trend and volatility",
        "",
        f"Within complete weeks, {day_names[int(peak.weekday)]} has the highest "
        f"average sales ratio "
        f"({peak.mean_within_week_ratio:.3f}); {day_names[int(trough.weekday)]} has the lowest "
        f"({trough.mean_within_week_ratio:.3f}). The table contains 95% pointwise intervals from "
        "500 moving-block bootstrap replicates (4 weeks/block, fixed seed). These "
        "describe historical "
        "stability under block-resampling assumptions, not causal weekday effects or "
        "confirmatory multiple tests.",
        "",
        f"Aggregate diagnostic weekly strength is "
        f"{result['diagnostics']['aggregate_weekly_strength']:.3f}; "
        f"annual strength after weekly removal is "
        f"{result['diagnostics']['aggregate_annual_strength_after_weekly']:.3f}. "
        "These are log1p aggregate STL variance-ratio diagnostics, not forecast "
        "scores. The 365-day "
        "annual approximation does not exactly align leap days. Monthly indices use complete years "
        "and normalise by each year's daily mean to reduce level-trend confounding.",
        "",
        f"Median per-series lag-7 correlation: {result['median_series_corr_lag7']:.3f}; "
        f"lag-365: {result['median_series_corr_lag365']:.3f}. Level correlations can "
        f"reflect trend. "
        "The aggregate ACF figure also shows first-differenced log sales, with no "
        "misleading iid significance bands.",
        "",
        f"![Calendar patterns](../figures/phase2/{name}_calendar_patterns.png)",
        f"![Diagnostics](../figures/phase2/{name}_diagnostics.png)",
        f"![Volatility](../figures/phase2/{name}_volatility.png)",
        "",
        "## Series-level intermittency",
        "",
        "ADI is observed days divided by positive-sale days. CV² uses sample variance of positive "
        "sale sizes divided by their squared mean (ddof=1). Thresholds are 1.32 and 0.49; equality "
        "enters the high group. All-zero and one-positive histories remain separate "
        "undefined cases. "
        "This descriptive daily-sales convention is inspired by "
        "Syntetos–Boylan–Croston, not a universal "
        "model-selection rule; pre-launch zeros, censoring and temporal aggregation "
        "can change classes.",
        "",
        "| Pattern | Full EDA window | First-positive-to-EDA-end sensitivity |",
        "|---|---:|---:|",
    ]
    for pattern in PATTERNS:
        lines.append(
            f"| {pattern} | {result['patterns'][pattern]:,} | "
            f"{result['active_span_patterns'][pattern]:,} |"
        )
    lines += [
        "",
        "The active-span sensitivity removes leading zeros analytically, without changing source "
        "observations or asserting actual availability. No trailing-zero truncation is used.",
        "",
        f"![Intermittency](../figures/phase2/{name}_intermittency.png)",
        f"![Zeros and variability](../figures/phase2/{name}_zeros_variability.png)",
        f"![Representative illustrations](../figures/phase2/{name}_representatives.png)",
        "",
        "Illustrations select the median-ranked series within each class, ordered by "
        "zero percentage, "
        "mean units and series ID. They are not a random sample or the basis of "
        "population findings; "
        "all per-series statistics use the full published series population.",
    ]
    if name == "m5":
        price = result["price_missingness"]
        info = price["eda_activity_partition"]
        lines += [
            "",
            "## Historical price missingness",
            "",
            f"All {price['full_history_missing']:,} full-history missing prices "
            f"reconcile by date, year, "
            f"store and product. Of these, {price['reserved_period_missing']:,} occur "
            f"outside the EDA window; "
            "reserved targets are not stratified by their sales activity. The "
            "following activity partition "
            "uses EDA dates only and reconciles exactly:",
            "",
            "| Observed activity relation | Missing-price observations |",
            "|---|---:|",
        ]
        for key in (
            "missing_before_first_positive",
            "missing_between_first_last_positive",
            "missing_after_last_positive",
            "missing_no_positive_in_eda",
        ):
            lines.append(f"| {key} | {info[key]:,} |")
        lines += [
            "",
            f"Missing prices with positive EDA sales: **{info['missing_with_positive_sales']:,}**; "
            f"with zero EDA sales: **{info['missing_with_zero_sales']:,}**. First/last "
            f"positive sales "
            "are activity proxies. Temporal concentration can be consistent with assortment/launch "
            "effects but does not prove product availability, stockouts or the reason "
            "prices are absent. "
            "No price is imputed. The missingness mask is retained in analytical summaries. "
            "Observed historical prices are not assumed known over a future forecast horizon.",
            "",
            "![Price missingness](../figures/phase2/m5_price_missingness.png)",
            "![Product price coverage](../figures/phase2/m5_price_products.png)",
            "![Events and categories](../figures/phase2/m5_events_groups.png)",
            "Calendar/event/SNAP summaries are associations. Event dates overlap across names, "
            "sample sizes differ, and trend/seasonality/store composition can confound "
            "comparisons. "
            "They do not estimate causal promotional effects.",
        ]
    lines += [
        "",
        "## Evidence and reproducibility",
        "",
        "All chart inputs and analytical tables are in `tables/"
        + name
        + "/` as compressed Parquet. "
        "The adjacent results JSON records scope, settings, split dates, "
        "reconciliations and source hashes. "
        "Figures are exported as PNG and SVG. Inputs are hashed before and after; no "
        "raw/canonical file changes.",
        "",
        "Methods: [Syntetos–Boylan–Croston "
        "classification](https://doi.org/10.1057/palgrave.jors.2601841); "
        "[forecast accuracy and rolling-origin evaluation](https://otexts.com/fpp3/toolbox.html). "
        "No forecasting model or hyperparameter search was run.",
    ]
    (directory / f"{name}_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def comparative_report(config: ProjectConfig, results: dict) -> None:
    directory = config.paths["reports"] / "eda"
    a, b = results["store_item"], results["m5"]
    lines = [
        "# Different sales structures call for separate forecasting benchmarks",
        "",
        "## Executive summary",
        "",
        f"Store Item's EDA zero-sales rate is {a['eda_zero_percent']:.4f}%, compared with "
        f"{b['eda_zero_percent']:.2f}% for M5. This population difference does not imply every M5 "
        "series is intermittent. Leading-zero sensitivity and the per-series classes "
        "below matter for model choice.",
        "",
        "| EDA statistic | Store Item | M5 |",
        "|---|---:|---:|",
    ]
    for label, key in (
        ("Series", "series"),
        ("Training-prefix observations", "eda_rows"),
        ("Training-prefix units", "eda_sales_units"),
        ("Zero-sales percentage", "eda_zero_percent"),
        ("Median all-sales CV", "median_series_cv"),
        ("Median lag-7 correlation", "median_series_corr_lag7"),
        ("Median lag-365 correlation", "median_series_corr_lag365"),
        ("Top-10%-of-products sales share", "product_top10_percent_share"),
        (
            "Class changes after leading-zero removal",
            "classification_changed_after_removing_leading_zeros",
        ),
    ):
        lines.append(f"| {label} | {a[key]:,.4f} | {b[key]:,.4f} |")
    lines += [
        "",
        "Each EDA scope ends before its first validation window. These are full-series-population "
        "training summaries, not statistics of the untouched evaluation tails. Full-history audit "
        "references remain separate in the per-dataset reports.",
        "",
        "## Forecasting implications",
        "",
        "Use naive, weekly seasonal naive and trailing moving-average baselines for both sources. "
        "Store Item's calendar diagnostics support testing seasonal ETS and carefully "
        "scoped SARIMA, "
        "alongside global lag/calendar ML. M5 needs stratified evaluation across "
        "defined patterns and "
        "cold-start/all-zero histories; compare Croston/SBA and TSB where "
        "intermittent/nonstationary "
        "activity makes them plausible. Category-level aggregates and per-series "
        "behaviour must not be conflated.",
        "",
        "A global LightGBM candidate is computationally plausible for many series, "
        "with origin-safe "
        "features and explicit multi-step strategy; it is optional and was not "
        "installed or trained. "
        "Random Forest is a useful controlled ML comparator but row/lag matrices and tree memory "
        "must be budgeted. Fitting independent SARIMA searches to all 30,490 M5 series is not the "
        "default; use a predeclared training-stratified diagnostic subset if needed "
        "and report coverage.",
        "",
        "These are candidate-family recommendations, not empirical claims of "
        "forecasting superiority. "
        "Use a common 28-day design, source-specific chronological windows, "
        "MAE/RMSE/WAPE/signed bias, "
        "and training-only weekly MASE/RMSSE scales. Compare within-source improvements over "
        "baselines rather than raw scale-dependent errors across sources. No direct model transfer "
        "is established: IDs, covariate availability, units and sparsity differ.",
        "",
        "Full methods and exact proposed folds: [forecasting "
        "protocol](../../docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md). "
        "Model-family references: [forecasting toolbox](https://otexts.com/fpp3/toolbox.html), "
        "[intermittency and obsolescence](https://doi.org/10.1016/j.ejor.2011.05.018).",
    ]
    (directory / "cross_dataset_comparison.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    _style()
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, key, title in zip(
        axes,
        ("eda_zero_percent", "median_series_cv", "product_top10_percent_share"),
        ("Zero-sales observations (%)", "Median series CV", "Top 10% product sales share"),
        strict=True,
    ):
        ax.bar(["Store Item", "M5"], [a[key], b[key]], color=[COLORS["store_item"], COLORS["m5"]])
        ax.set_title(title, fontsize=11)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y")
    directory_fig = config.paths["reports"] / "figures/phase2"
    fig.suptitle("Full-population training-prefix comparisons; source periods differ", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    for extension in ("png", "svg"):
        fig.savefig(
            directory_fig / f"cross_dataset_comparison.{extension}", dpi=a["settings"]["figure_dpi"]
        )
    plt.close(fig)
    manifest = {name: result["split_plan"] for name, result in results.items()}
    write_json(directory / "proposed_splits.json", manifest)
