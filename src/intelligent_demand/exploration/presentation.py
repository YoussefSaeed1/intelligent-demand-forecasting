"""Clear, exposure-aware figures using only validated Phase 2 summary tables."""

import re
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import EngFormatter, FuncFormatter, MaxNLocator, NullFormatter


def context(config, result):
    from intelligent_demand.exploration import reporting as r

    def load(name):
        return r._load(config, result["dataset"], name)

    def save(fig, name, title):
        r._save(config, fig, name, result, title)

    return r, load, save


def plain(axis, dimension="x"):
    target = axis.xaxis if dimension == "x" else axis.yaxis
    target.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    target.set_minor_formatter(NullFormatter())


def demand_patterns(config, result):
    r, load, save = context(config, result)
    series, patterns = load("series"), load("patterns")
    if result["dataset"] == "store_item":
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
        axes[0].hist(series.cv2_positive, bins=24, color=r.COLORS["store_item"])
        axes[0].set(
            xlabel="CV² of positive daily sale sizes",
            ylabel="Series",
            title="Variation within the 500 smooth series",
        )
        plain(axes[0])
        axes[1].axis("off")
        facts = [
            ["Smooth series", f"{result['series']:,} / {result['series']:,} (100%)"],
            ["ADI range", f"{series.adi.min():.6f}–{series.adi.max():.6f} days"],
            [
                "Positive-size CV² range",
                f"{series.cv2_positive.min():.4f}–{series.cv2_positive.max():.4f}",
            ],
            ["Zero-sale observations", "1 / 843,000 (0.000118624%)"],
            ["Recorded zero", "Store 6 · item 4 · 2014-01-15"],
        ]
        table = axes[1].table(cellText=facts, colWidths=[0.47, 0.53], loc="center", cellLoc="left")
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2.3)
        axes[1].set_title("ADI < 1.32 and CV² < 0.49 for every series")
        save(fig, "intermittency", "Store Item: an entirely smooth training population")
        return
    fig, ax = plt.subplots(figsize=(10.5, 5.7))
    for label in r.PATTERNS[:4]:
        block = series[series.pattern.eq(label)]
        positive = block[block.cv2_positive.gt(0)]
        ax.scatter(
            positive.adi,
            positive.cv2_positive,
            s=8,
            alpha=0.3,
            color=r.COLORS[label],
            label=label.capitalize(),
            rasterized=True,
        )
    zero = series[series.cv2_positive.eq(0)]
    ax.scatter(
        zero.adi,
        np.full(len(zero), 0.001),
        s=24,
        marker="v",
        facecolors="none",
        edgecolors="#222",
        label=f"CV²=0: {len(zero)} series at display floor",
    )
    ax.axvline(1.32, color="#333", linestyle="--", linewidth=0.8)
    ax.axhline(0.49, color="#333", linestyle="--", linewidth=0.8)
    ax.set(
        xscale="log",
        yscale="log",
        xlabel="ADI (daily periods; log scale)",
        ylabel="Positive-size CV² (log scale)",
        title="Defined histories only; 16 all-zero and 5 one-positive histories omitted",
    )
    ax.legend(frameon=False, fontsize=9, ncol=2)
    save(fig, "intermittency", "M5: intermittency and positive-sale variability")
    fig, ax = plt.subplots(figsize=(11, 4.5))
    labels = [p.replace("_", " ").capitalize() for p in patterns.pattern]
    y = np.arange(len(patterns))
    for position, row in enumerate(patterns.itertuples()):
        ax.scatter(
            row.series, position, color=r.COLORS[row.pattern], s=75, edgecolor="#333", linewidth=0.4
        )
        ax.text(
            1.04,
            position,
            f"{row.series:,}  ·  {100 * row.series / result['series']:.4f}%",
            transform=ax.get_yaxis_transform(),
            va="center",
            fontsize=11,
        )
    ax.set_yticks(y, labels)
    ax.set(
        xscale="log",
        xlim=(3, 50000),
        xlabel="Series count (log axis; exact counts and shares at right)",
    )
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.2)
    fig.subplots_adjust(right=0.7)
    save(fig, "classification", "M5: every demand class, including the minority histories")


def sparsity(config, result):
    r, load, save = context(config, result)
    series = load("series")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    color = r.COLORS[result["dataset"]]
    if result["dataset"] == "store_item":
        counts = [result["eda_zero_count"], result["eda_rows"] - result["eda_zero_count"]]
        axes[0].scatter(counts, [0, 1], s=80, color=color)
        axes[0].set(
            yticks=[0, 1],
            yticklabels=["Zero sale", "Positive sale"],
            xscale="log",
            xlabel="Observed store-product days (log scale)",
            ylim=(-0.7, 1.7),
        )
        for value, y in zip(counts, [0, 1], strict=True):
            axes[0].annotate(
                f"{value:,} ({100 * value / result['eda_rows']:.9f}%)",
                (value, y),
                xytext=(0, 18),
                textcoords="offset points",
                fontsize=9,
                ha="left" if y == 0 else "right",
            )
        axes[0].set_title("The single zero remains a recorded observation")
        cv = series.std_units / series.mean_units
        axes[1].hist(cv, bins=28, color=color)
        axes[1].set(xlabel="CV of all daily sales (linear scale)", ylabel="Series")
        plain(axes[1])
    else:
        axes[0].hist(series.zero_percent, bins=np.linspace(0, 100, 21), color=color, rwidth=0.95)
        axes[0].set(xlabel="Zero-sale observations per series (%)", ylabel="Series", xlim=(0, 100))
        cv = (series.std_units / series.mean_units.replace(0, np.nan)).dropna()
        axes[1].hist(
            cv[cv.gt(0)], bins=np.geomspace(cv[cv.gt(0)].min(), cv.max() * 1.001, 30), color=color
        )
        axes[1].set(
            xscale="log",
            xlabel="CV of all daily sales (log scale)",
            ylabel="Series",
            title="16 all-zero histories have undefined CV and are excluded",
        )
    save(fig, "zeros_variability", "Recorded zeros and the variability of daily sales")


def store_comparison(config, result):
    r, load, save = context(config, result)
    stores = load("stores").copy()
    stores = stores.sort_values("mean_units_per_series_day", ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].barh(
        stores.store_id, stores.mean_units_per_series_day, color=r.COLORS[result["dataset"]]
    )
    axes[0].invert_yaxis()
    axes[0].set(xlabel="Units per store-product day", title="Comparable historical exposure")
    if result["dataset"] == "store_item":
        axes[1].axis("off")
        axes[1].text(0.05, 0.9, "One zero-sale observation", fontsize=17, weight="bold")
        axes[1].text(0.05, 0.55, "Store 6 · item 4\n15 January 2014", fontsize=15, linespacing=1.8)
        axes[1].text(
            0.05,
            0.2,
            "1 of 843,000 training observations\n0.000118624% · no sales imputed",
            fontsize=11,
        )
    else:
        axes[1].barh(stores.store_id, stores.mean_zero_percent, color=r.COLORS["m5"])
        axes[1].invert_yaxis()
        axes[1].set(
            xlabel="Zero-sale observations (%)",
            xlim=(0, 100),
            title="Same full daily grid within each store",
        )
    save(fig, "stores", "Store-level sales and sparsity")


def volatility(config, result):
    r, load, save = context(config, result)
    daily = load("daily")
    fig, axes = plt.subplots(2, 1, figsize=(11, 5.7))
    axes[0].plot(daily.date, daily.cv_28d, color=r.COLORS[result["dataset"]])
    axes[0].set(
        ylabel="28-day coefficient of variation", title="Local variation in aggregate daily sales"
    )
    if result["dataset"] == "store_item":
        count = np.rint(daily.zero_percent * result["series"] / 100).astype(int)
        axes[1].plot(daily.date, count, color=r.COLORS["store_item"])
        selected = daily.loc[count.gt(0)].iloc[0]
        axes[1].scatter([selected.date], [1], color="#9b4f08", zorder=3)
        axes[1].annotate(
            "2014-01-15 · store 6 / item 4",
            (selected.date, 1),
            xytext=(15, -20),
            textcoords="offset points",
            fontsize=9,
        )
        axes[1].set(
            ylabel="Series with zero sales",
            ylim=(0, 1.25),
            yticks=[0, 1],
            title="One zero-selling series on one day; 500 series observed each day",
        )
    else:
        axes[1].plot(daily.date, daily.zero_percent, color=r.COLORS["m5"])
        axes[1].set(
            ylabel="Zero-sale series (%)",
            ylim=(0, 100),
            title="Daily breadth of recorded zero sales",
        )
    for ax in axes:
        r._dates(ax, daily.date)
    save(fig, "volatility", "Volatility and zero-sales breadth over the training period")


def representatives(config, result):
    r, load, save = context(config, result)
    representatives = load("representative_series")
    meta = load("series").set_index("series_id")
    groups = list(representatives.groupby("pattern", sort=False))
    fig, axes = plt.subplots(
        len(groups), 1, figsize=(11, max(3.7, 2.7 * len(groups))), squeeze=False
    )
    for ax, (pattern, full) in zip(axes[:, 0], groups, strict=True):
        frame = full if pattern in ("all_zero", "insufficient_positive_history") else full.tail(180)
        row = meta.loc[full.series_id.iloc[0]]
        ax.plot(frame.date, frame.sales_units, color=r.COLORS[pattern], linewidth=0.9)
        ax.set_ylim(0, max(1, frame.sales_units.max() * 1.25))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
        ax.set(
            ylabel="Units/day",
            title=f"{pattern.replace('_', ' ').capitalize()} · {row.store_id} / {row.item_id} · "
            + ("full training history" if len(frame) == len(full) else "last 180 training days"),
        )
        if pattern == "insufficient_positive_history":
            positive = full[full.sales_units.gt(0)].iloc[0]
            ax.scatter([positive.date], [positive.sales_units], color="#222", zorder=3)
            ax.annotate(
                f"Only positive: {positive.sales_units:g} units · {positive.date:%Y-%m-%d}",
                (positive.date, positive.sales_units),
                xytext=(20, -12),
                textcoords="offset points",
                fontsize=9,
            )
        if pattern == "all_zero":
            ax.text(
                0.02,
                0.62,
                (
                    "No positive sales in these "
                    f"{len(full):,}"
                    " training days; future activity is unexamined."
                ),
                transform=ax.transAxes,
                fontsize=9,
            )
        r._dates(ax, frame.date)
    save(
        fig,
        "representatives",
        "Illustrative series only · independent y-scales and labelled windows",
    )


def price_coverage(config, result):
    r, load, save = context(config, result)
    dates, years = load("price_by_date_full_quality"), load("price_by_year_full_quality")
    stores = load("price_by_store_full_quality")
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5))
    axes[0, 0].plot(
        dates.date, 100 * dates.missing_prices / dates.observations, color=r.COLORS["m5"]
    )
    cutoff = pd.Timestamp(result["split_plan"]["eda_end"])
    axes[0, 0].axvspan(
        cutoff, dates.date.max(), color="#eee", label="Reserved: price coverage only"
    )
    axes[0, 0].set(
        ylabel="Missing prices (%)", ylim=(0, 100), title="Full-history label-free coverage"
    )
    axes[0, 0].legend(frameon=False, fontsize=8)
    r._dates(axes[0, 0], dates.date)
    parts = result["price_missingness"]["eda_activity_partition"]
    names = [
        ("Before first positive", "missing_before_first_positive"),
        ("Within positive span", "missing_between_first_last_positive"),
        ("After last positive", "missing_after_last_positive"),
        ("No positive in EDA", "missing_no_positive_in_eda"),
    ]
    cells = [
        [label, f"{parts[key]:,}", f"{100 * parts[key] / parts['missing_prices']:.4f}%"]
        for label, key in names
    ]
    axes[0, 1].axis("off")
    table = axes[0, 1].table(
        cellText=cells,
        colLabels=["Training activity proxy", "Missing", "Share of gaps"],
        colWidths=[0.48, 0.27, 0.25],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.0)
    axes[0, 1].set_title("All 12,298,948 training gaps; no price imputation")
    for ax, frame, field, title in [
        (axes[1, 0], stores, "store_id", "Store coverage"),
        (axes[1, 1], years, "year", "Year coverage; boundary years partial"),
    ]:
        values = 100 * frame.missing_prices / frame.observations
        bars = ax.bar(frame[field].astype(str), values, color=r.COLORS["m5"])
        ax.bar_label(bars, labels=[f"{v:.2f}%" for v in values], padding=3, fontsize=8)
        ax.set(ylabel="Missing prices (%)", ylim=(0, max(values) * 1.22), title=title)
    save(
        fig,
        "price_missingness",
        "M5 historical price coverage · 12,299,413 gaps, including 465 reserved gaps",
    )


def events_categories(config, result):
    r, load, save = context(config, result)
    events = load("calendar_events").sort_values("mean_total_units").head(10)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    labels = [
        textwrap.fill(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", row.event), 22) + f" (n={row.days})"
        for row in events.itertuples()
    ]
    bars = axes[0].barh(labels, events.mean_total_units, color=r.COLORS["m5"])
    axes[0].bar_label(
        bars, labels=[f"{v:,.1f}" for v in events.mean_total_units], padding=3, fontsize=9
    )
    axes[0].set(
        xlabel="Aggregate units per event day",
        xlim=(0, events.mean_total_units.max() * 1.27),
        title="Ten lowest-mean events; descriptive association",
    )
    axes[0].xaxis.set_major_formatter(EngFormatter())
    category, meta = load("cat_id_daily"), load("series")
    for color, (group, frame) in zip(
        ["#2463a0", "#c47a28", "#007f73"], category.groupby("group"), strict=True
    ):
        n = meta.cat_id.eq(group).sum()
        axes[1].plot(
            frame.date,
            (frame.sales_units / n).rolling(28).mean(),
            color=color,
            label=f"{group} (n={n:,})",
        )
    axes[1].set(
        ylabel="Trailing mean units per series/day", title="Categories adjusted by series count"
    )
    axes[1].legend(frameon=False, fontsize=9)
    r._dates(axes[1], category.date)
    save(
        fig,
        ("events_groups"),
        ("Calendar associations and product categories · no causal attribution"),
    )


def department_summary(daily, series):
    exposure = series.groupby("dept_id").size()
    frame = daily.copy()
    frame["series"] = frame.group.map(exposure)
    frame["units_per_series_day"] = frame.sales_units / frame.series
    return frame


def tail_probabilities(histogram):
    frame = histogram.sort_values("units").copy()
    frame["at_least_probability"] = (
        frame.observations.iloc[::-1].cumsum().iloc[::-1] / frame.observations.sum()
    )
    return frame


def extra_figures(config, result):
    r, load, save = context(config, result)
    hist = tail_probabilities(load("distribution"))
    extremes = (
        load("largest_observations")
        .head(10)
        .merge(
            load("series")[["series_id", "store_id", "item_id"]],
            on="series_id",
            validate="many_to_one",
        )
    )
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.7))
    axes[0].step(
        hist.units, hist.at_least_probability, where="post", color=r.COLORS[result["dataset"]]
    )
    axes[0].set(
        yscale="log",
        xlabel="Daily units threshold q",
        ylabel="Share of all observations with sales ≥ q",
        title=f"Full training population · {result['eda_rows']:,} observations",
    )
    axes[0].grid(axis="y", alpha=0.2)
    labels = [
        f"{row.store_id} / {row.item_id}\n{row.date:%Y-%m-%d}" for row in extremes.itertuples()
    ]
    bars = axes[1].barh(
        labels[::-1], extremes.sales_units.iloc[::-1], color=r.COLORS[result["dataset"]]
    )
    axes[1].bar_label(
        bars, labels=[f"{v:g}" for v in extremes.sales_units.iloc[::-1]], padding=3, fontsize=9
    )
    axes[1].set(
        xlabel="Observed daily sales units",
        title="Retained extreme examples: 10 of 20; ties not exhaustive",
        xlim=(0, extremes.sales_units.max() * 1.16),
    )
    axes[1].tick_params(axis="y", labelsize=8)
    save(fig, "extremes", "Extreme sales values · descriptive tail, not a data-error diagnosis")
    if result["dataset"] != "m5":
        return
    snap = load("snap_associations")
    fig, ax = plt.subplots(figsize=(11, 4.8))
    states = sorted(snap.state.unique())
    x = np.arange(len(states))
    for flag, color, offset in [(0, "#647487", -0.2), (1, r.COLORS["m5"], 0.2)]:
        frame = snap[snap.snap_flag.eq(flag)].set_index("state").loc[states]
        bars = ax.bar(
            x + offset,
            frame.mean_store_daily_units,
            width=0.38,
            color=color,
            label="SNAP calendar flag" if flag else "Non-SNAP calendar flag",
        )
        ax.bar_label(
            bars,
            labels=[
                f"{row.mean_store_daily_units:,.1f}\nn={row.store_days:,} store-days"
                for row in frame.itertuples()
            ],
            fontsize=9,
            padding=4,
        )
    ax.set(
        xticks=x,
        xticklabels=states,
        ylabel="Units per observed store-day",
        ylim=(0, snap.mean_store_daily_units.max() * 1.3),
        title="Within-state comparison; unequal flagged-day exposure is divided out",
    )
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "snap", "SNAP versus non-SNAP calendar days · descriptive, not causal")
    dept = department_summary(load("dept_id_daily"), load("series"))
    means = dept.groupby("group").units_per_series_day.mean().sort_values()
    monthly = (
        dept.assign(month=dept.date.dt.to_period("M").astype(str))
        .pivot_table(index="group", columns="month", values="units_per_series_day", aggfunc="mean")
        .loc[means.index]
    )
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    bars = axes[0].barh(means.index, means, color=r.COLORS["m5"])
    axes[0].bar_label(bars, labels=[f"{v:.3f}" for v in means], padding=3, fontsize=9)
    axes[0].set(
        xlabel="Units per department series/day",
        xlim=(0, means.max() * 1.22),
        title="Equal daily exposure; published series universe",
    )
    im = axes[1].imshow(monthly, aspect="auto", origin="lower", cmap="YlOrBr", vmin=0)
    ticks = np.linspace(0, len(monthly.columns) - 1, 5).astype(int)
    axes[1].set(
        yticks=np.arange(len(monthly)),
        yticklabels=monthly.index,
        xticks=ticks,
        xticklabels=monthly.columns[ticks],
        title="Monthly daily rates; boundary months partial",
    )
    axes[1].tick_params(axis="x", labelsize=8)
    fig.colorbar(im, ax=axes[1], label="Mean units per series/day", fraction=0.045)
    save(fig, "departments", "M5 department demand · rates adjusted by department series count")
