"Offline scientific reporting from independently audited validation simulations."

import argparse
import html
import json
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from PIL import Image

from intelligent_demand.inventory.design import POLICIES, Scenario
from intelligent_demand.inventory.plan import OUTPUT, REPORTS, ROOT, plan, read
from intelligent_demand.inventory.runner import case_key, completed, execution
from intelligent_demand.preservation.backup import sha256

LABELS = {
    "fixed_reorder_point": "Fixed ROP",
    "moving_average_28": "MA28",
    "seasonal_naive": "Seasonal naive",
    "selected_ml": "Selected ML",
}
COLORS = ["#526777", "#d38b27", "#7c5daf", "#087e8b"]
FIGURES = ROOT / "reports/figures/phase5"
QUALIFICATION = (
    "Hypothetical lost-sales simulation; sales are a potentially censored demand proxy. "
    "Full populations: Store Item 500 and M5 30,490 series at each of four original "
    "validation origins; 28 days per episode. Origins reset stock. Saved forecasts "
    "are fixed at issue, not daily refreshed. These validation windows also informed "
    "Phase 4 selection; comparisons are exploratory and validation-reused, with no "
    "significance claim. Costs are normalised hypothetical units (NCU), not realised savings."
)
BASE = (
    "Base: L=7 full intervening days; R=1; buffer=3 training-mean days; initial=7 days; "
    "h=1 NCU/unit/day, p=10 NCU/unmet unit, k=1 NCU/order. Empty initial pipeline. "
    "End-day orders arrive start t+L+1. All policies stop new orders when the remaining "
    "L+R forecast dates are unavailable; remaining demand is still scored."
)


def pooled(frame, keys):
    """Sum units first for fill; series-weight means, never mean-of-ratios fill."""
    records = []
    for key, block in frame.groupby(keys, sort=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(keys, key, strict=True))
        n = float(block.series.sum())
        for name in (
            "total_cost",
            "holding_cost",
            "shortage_cost",
            "ordering_cost",
            "terminal_cost",
            "demand_units",
            "fulfilled_units",
            "unmet_units",
            "stockout_days",
            "orders",
            "final_on_hand",
            "terminal_pipeline",
        ):
            row[name] = float(block[name].sum())
        row["series_episodes"] = int(n)
        row["mean_cost"] = row["total_cost"] / n
        row["pooled_fill_rate"] = (
            row["fulfilled_units"] / row["demand_units"] if row["demand_units"] else np.nan
        )
        row["stockout_days_per_episode"] = row["stockout_days"] / n
        for name in ("average_on_hand", "average_inventory_position"):
            row[name] = float(np.average(block[name], weights=block.series))
        records.append(row)
    return pd.DataFrame(records)


def table(frame, columns=None):
    return frame.to_html(
        index=False,
        columns=columns,
        border=0,
        float_format=lambda x: f"{x:,.6f}",
        classes="data",
        escape=True,
    )


def markdown(frame):
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for _, row in frame.iterrows():
        lines.append(
            "| " + " | ".join(f"{v:.6f}" if isinstance(v, float) else str(v) for v in row) + " |"
        )
    return "\n".join(lines)


def build():
    p, contract = plan(), execution()
    saved = read(REPORTS / "phase5_summary.json")
    if (
        saved["status"] != "passed"
        or saved["cases"] != 544
        or saved["plan_sha256"] != p["sha256"]
        or saved["execution_sha256"] != contract["sha256"]
    ):
        raise ValueError("Complete independent scenario audit required before reporting")
    frame = pd.DataFrame(saved["summaries"])
    groups = pd.DataFrame(saved["groups"])
    base = frame[frame.scenario.eq("base")]
    combined = pooled(frame, ["dataset", "scenario", "policy"])
    main = combined[combined.scenario.eq("base")].copy()
    figures = []
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "figure.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
        }
    )

    def axes(title, subtitle="Four origins; full populations; 28-day episodes"):
        fig, ax = plt.subplots(1, 2, figsize=(13, 5.5))
        fig.suptitle(title + "\n" + subtitle, fontsize=14)
        for a, dataset in zip(ax, ("store_item", "m5"), strict=True):
            a.set_title(
                dataset.replace("_", " ").title()
                + (" | LightGBM" if dataset == "store_item" else " | price-free RF"),
                pad=10,
            )
            a.grid(axis="y", alpha=0.2)
            a.set_axisbelow(True)
        return fig, ax

    def save(fig, slug, purpose, note):
        top = 0.96 if fig.get_figheight() > 8 else 0.88
        fig.tight_layout(rect=(0, 0, 1, top))
        for extension in ("png", "svg"):
            fig.savefig(FIGURES / f"{slug}.{extension}", dpi=150, bbox_inches="tight")
        plt.close(fig)
        figures.append(
            {
                "id": slug,
                "purpose": purpose,
                "note": note,
                "png": f"../figures/phase5/{slug}.png",
                "svg": f"../figures/phase5/{slug}.svg",
            }
        )

    def ordered(dataset):
        return main[main.dataset.eq(dataset)].set_index("policy").loc[list(POLICIES)]

    fig, ax = axes(
        "Total simulated cost by policy",
        "Base; points show origin means, bars the four-origin mean",
    )
    for a, dataset in zip(ax, ("store_item", "m5"), strict=True):
        block = ordered(dataset)
        a.bar(range(4), block.mean_cost, color=COLORS)
        for i, policy in enumerate(POLICIES):
            a.scatter(
                [i] * 4,
                base[(base.dataset == dataset) & (base.policy == policy)].mean_cost,
                color="black",
                s=18,
                zorder=3,
            )
        a.set_xticks(range(4), [LABELS[x] for x in POLICIES], rotation=15)
        a.set_ylabel("NCU per series / 28-day episode")
        a.set_ylim(bottom=0)
    save(
        fig,
        "01_total_cost",
        "Total simulated cost",
        ("Axes start at zero; dataset scales differ. Dots are origins, not confidence intervals."),
    )

    fig, ax = axes("Simulated cost components", "Base; NCU per series per 28-day episode")
    for a, dataset in zip(ax, ("store_item", "m5"), strict=True):
        block = ordered(dataset)
        bottom = np.zeros(4)
        for field, label, color in zip(
            ("holding_cost", "shortage_cost", "ordering_cost"),
            ("Holding", "Unmet penalty", "Ordering"),
            ("#087e8b", "#d38b27", "#526777"),
            strict=True,
        ):
            values = block[field].to_numpy() / block.series_episodes.to_numpy()
            a.bar(range(4), values, bottom=bottom, label=label, color=color)
            bottom += values
        a.set_xticks(range(4), [LABELS[x] for x in POLICIES], rotation=15)
        a.set_ylabel("NCU per series / episode")
        a.legend(fontsize=10)
    save(
        fig,
        "02_cost_breakdown",
        "Cost breakdown",
        (
            "Base terminal charge is zero. Initial acquisition is common and "
            "excluded; small ordering costs may be visually thin."
        ),
    )

    fig, ax = axes(
        "Stockholding and service trade-off", "Base; unit fill is pooled fulfilled / pooled demand"
    )
    for a, dataset in zip(ax, ("store_item", "m5"), strict=True):
        for i, (policy, row) in enumerate(ordered(dataset).iterrows()):
            a.scatter(
                row.average_on_hand,
                row.pooled_fill_rate,
                s=85,
                color=COLORS[i],
                label=LABELS[policy],
            )
        a.set_xlabel("Mean daily closing on-hand units / series")
        a.set_ylabel("Pooled unit fill rate")
        a.set_xlim(left=0)
        a.set_ylim(0, 1.04)
        a.legend(loc="lower right", fontsize=10)
    save(
        fig,
        "03_fill_inventory",
        "Fill rate versus stockholding",
        (
            "Full 0–1 fill scale. Fill is not cycle service probability; zero-demand "
            "series have undefined individual fill."
        ),
    )

    fig, ax = axes("Days with unmet demand", "Base; average count per 28-day series episode")
    for a, dataset in zip(ax, ("store_item", "m5"), strict=True):
        a.bar(range(4), ordered(dataset).stockout_days_per_episode, color=COLORS)
        a.set_xticks(range(4), [LABELS[x] for x in POLICIES], rotation=15)
        a.set_ylabel("Days with unmet demand / episode")
        a.set_ylim(bottom=0)
    save(
        fig,
        "04_stockout_days",
        "Stockout days",
        (
            "A day with unmet demand in the hypothetical simulator is not an observed"
            " historical stockout."
        ),
    )

    pattern = pooled(
        groups[(groups.scenario == "base") & (groups.group_field == "pattern")],
        ["dataset", "group", "policy"],
    )
    fig, ax = axes(
        "Cost differences by training-prefix demand class",
        "Base; mean policy cost minus MA28, NCU / series / episode",
    )
    for a, dataset in zip(ax, ("store_item", "m5"), strict=True):
        block = pattern[pattern.dataset.eq(dataset)]
        classes = sorted(block.group.unique())
        reference = block[block.policy.eq("moving_average_28")].set_index("group")
        for i, policy in enumerate(POLICIES):
            values = (
                block[block.policy.eq(policy)].set_index("group").loc[classes].mean_cost
                - reference.loc[classes].mean_cost
            )
            a.bar(
                np.arange(len(classes)) + (i - 1.5) * 0.19,
                values,
                width=0.19,
                color=COLORS[i],
                label=LABELS[policy],
            )
        a.axhline(0, color="black", lw=0.7)
        a.set_ylabel("Difference from MA28 (NCU); lower is cheaper")
        a.set_xticks(
            range(len(classes)),
            [
                x.replace(
                    "insufficient_positive_history", "insufficient\npositive history"
                ).replace("_", " ")
                for x in classes
            ],
            rotation=30,
            ha="right",
        )
        a.legend(fontsize=9)
    save(
        fig,
        "05_demand_patterns",
        "Performance by demand pattern",
        (
            "Classes use pre-existing training-prefix EDA, with separate all-zero and"
            " insufficient-history groups. Group sizes are in the machine summary."
        ),
    )

    for slug, title, scenarios, values, xlabel in (
        (
            "06_lead_sensitivity",
            "Lead-time sensitivity",
            ["lead_short", "base", "lead_long"],
            [1, 7, 14],
            "L: full intervening demand days",
        ),
        (
            "07_buffer_sensitivity",
            "Hypothetical buffer sensitivity",
            ["buffer_zero", "base", "buffer_high"],
            [0, 3, 7],
            "Buffer: trailing training-mean demand days",
        ),
    ):
        fig, ax = axes(title, "One-at-a-time variations; other base assumptions held fixed")
        for a, dataset in zip(ax, ("store_item", "m5"), strict=True):
            for i, policy in enumerate(POLICIES):
                block = combined[
                    (combined.dataset == dataset) & (combined.policy == policy)
                ].set_index("scenario")
                a.plot(
                    values,
                    block.loc[scenarios].mean_cost,
                    "o-",
                    color=COLORS[i],
                    label=LABELS[policy],
                )
            a.set_ylabel("NCU per series / 28-day episode")
            a.set_xlabel(xlabel)
            a.set_xticks(values)
            a.set_ylim(bottom=0)
            a.legend(fontsize=10)
        save(
            fig,
            slug,
            title,
            (
                "Buffer is not a calibrated target service level. Lead changes also "
                "change the common last supported ordering date."
            ),
        )

    accuracy, trajectory, coverage, paired_detail = [], [], [], []
    base_settings = Scenario(**p["scenarios"][0])
    for cohort in p["cohorts"]:
        policy_tables = {}
        for policy in POLICIES:
            key = case_key(cohort, base_settings, policy, contract)
            state = completed(OUTPUT / "runs" / key)
            block = pd.read_parquet(ROOT / state["files"]["series"]["path"])
            policy_tables[policy] = block
            coverage.append(
                {
                    "dataset": cohort["dataset"],
                    "fold": cohort["fold"]["number"],
                    "policy": policy,
                    "series": len(block),
                    "forecast_fallback_observations": state["source_fallback_observations"],
                    "origin_allzero_sample_series": int(block.origin_sample_all_zero.sum()),
                    "retrospective_allzero_sample_series": int(
                        block.retrospective_final_training_all_zero.sum()
                    ),
                }
            )
            if policy != "fixed_reorder_point":
                accuracy.append(
                    {
                        "dataset": cohort["dataset"],
                        "fold": cohort["fold"]["number"],
                        "policy": policy,
                        "macro_mae": float(block.forecast_mae.mean()),
                        "mean_cost": float(block.total_cost.mean()),
                        "spearman_series_mae_cost": float(
                            block.forecast_mae.corr(block.total_cost, method="spearman")
                        ),
                    }
                )
            if cohort["fold"]["number"] == 1:
                events = pd.read_parquet(
                    ROOT / state["files"]["events"]["path"],
                    filters=[("series_id", "in", cohort["representatives"])],
                )
                for series_id in cohort["representatives"]:
                    piece = events[events.series_id.eq(series_id)].sort_values("day_index")
                    trajectory.append(
                        {
                            "dataset": cohort["dataset"],
                            "series_id": series_id,
                            "policy": policy,
                            "events": piece,
                        }
                    )
        delta = (
            policy_tables["selected_ml"].total_cost - policy_tables["moving_average_28"].total_cost
        )
        for field, mask in (
            ("all", np.ones(len(delta), dtype=bool)),
            ("origin_sample_all_zero", policy_tables["selected_ml"].origin_sample_all_zero),
            (
                "retrospective_final_training_all_zero",
                policy_tables["selected_ml"].retrospective_final_training_all_zero,
            ),
        ):
            if not np.any(mask):
                continue
            values = delta[mask]
            paired_detail.append(
                {
                    "dataset": cohort["dataset"],
                    "fold": cohort["fold"]["number"],
                    "group": field,
                    "series": int(np.sum(mask)),
                    "mean_ml_minus_ma28": float(values.mean()),
                    "q10": float(values.quantile(0.1)),
                    "median": float(values.median()),
                    "q90": float(values.quantile(0.9)),
                    "lower_cost": int((values < -1e-8).sum()),
                    "higher_cost": int((values > 1e-8).sum()),
                    "ties": int((values.abs() <= 1e-8).sum()),
                }
            )
    accuracy = pd.DataFrame(accuracy)
    fig, ax = axes(
        "Forecast accuracy versus simulated inventory cost",
        "Base; each point is one full-population model/origin; shapes identify origins",
    )
    for a, dataset in zip(ax, ("store_item", "m5"), strict=True):
        for i, policy in enumerate(POLICIES):
            block = accuracy[(accuracy.dataset == dataset) & (accuracy.policy == policy)]
            if block.empty:
                continue
            for index, row in enumerate(block.itertuples()):
                a.scatter(
                    row.macro_mae,
                    row.mean_cost,
                    color=COLORS[i],
                    marker=("o", "s", "^", "D")[row.fold - 1],
                    label=LABELS[policy] if index == 0 else None,
                )
        a.set_xlabel("Macro MAE (sales units)")
        a.set_ylabel("NCU per series / episode")
        a.set_xlim(left=0)
        a.set_ylim(bottom=0)
        model_legend = a.legend(fontsize=10, loc="upper left")
        a.add_artist(model_legend)
        a.legend(
            handles=[
                Line2D(
                    [], [], color="#536674", marker=marker, linestyle="None", label=f"Origin {fold}"
                )
                for fold, marker in enumerate(("o", "s", "^", "D"), 1)
            ],
            fontsize=9,
            loc="lower left",
        )
    save(
        fig,
        "08_accuracy_inventory",
        "Accuracy versus inventory outcome",
        (
            "Association is descriptive, affected by origin volume, bias and scale. "
            "No causal or significance inference from 12 points per dataset."
        ),
    )

    fig, ax = plt.subplots(6, 2, figsize=(15, 20), squeeze=False)
    fig.suptitle(
        (
            "Representative inventory trajectories | first validation origin\nFrozen "
            "prefix-volume / ID-rank selection; all six representatives per dataset"
        ),
        fontsize=15,
    )
    for column, dataset in enumerate(("store_item", "m5")):
        ids = next(c["representatives"] for c in p["cohorts"] if c["dataset"] == dataset)
        for row, series_id in enumerate(ids):
            a = ax[row, column]
            pieces = [
                x for x in trajectory if x["dataset"] == dataset and x["series_id"] == series_id
            ]
            for i, item in enumerate(pieces):
                events = item["events"]
                a.plot(
                    events.day_index + 1,
                    events.closing_stock,
                    color=COLORS[i],
                    label=LABELS[item["policy"]],
                )
            a.plot(events.day_index + 1, events.demand, "k:", alpha=0.6, label="Demand proxy")
            a.set_title(dataset + " / " + series_id, fontsize=11)
            a.set_ylabel("Units")
            a.set_xlabel("Episode day")
            a.set_ylim(bottom=0)
            a.grid(alpha=0.2)
            if row == 0:
                a.legend(fontsize=9)
    save(
        fig,
        "09_trajectories",
        "Inventory trajectories",
        (
            "Closing stock and demand have different meanings despite shared unit "
            "scale. Complete base events exist for every series/origin; other origins"
            " remain inspectable in Parquet."
        ),
    )

    fig, ax = axes(
        "Policy robustness across all frozen scenarios",
        "Difference from matched MA28 (% of its cost); negative means lower simulated cost",
    )
    fig.set_size_inches(14, 10)
    for a, dataset in zip(ax, ("store_item", "m5"), strict=True):
        block = (
            combined[combined.dataset.eq(dataset)]
            .pivot(index="scenario", columns="policy", values="mean_cost")
            .loc[[x["identifier"] for x in p["scenarios"]], list(POLICIES)]
        )
        difference = 100 * block.sub(block.moving_average_28, axis=0).div(
            block.moving_average_28, axis=0
        )
        limit = max(1, float(np.nanmax(np.abs(difference))))
        im = a.imshow(difference, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
        a.grid(False)
        a.set_yticks(range(len(block)), block.index.str.replace("_", " "))
        a.set_xticks(range(4), [LABELS[x] for x in POLICIES], rotation=25)
        fig.colorbar(im, ax=a, label="Cost difference from MA28 (%)", shrink=0.7)
    save(
        fig,
        "10_robustness",
        "Policy robustness",
        (
            "Colour ranges are symmetric about zero separately by dataset. Scenarios "
            "are one-at-a-time stresses, not a joint uncertainty distribution or new "
            "tuning search."
        ),
    )

    findings = []
    for dataset in ("store_item", "m5"):
        b = ordered(dataset)
        ml, ma = b.loc["selected_ml"], b.loc["moving_average_28"]
        best = b.mean_cost.idxmin()
        origins = (
            base[(base.dataset == dataset) & (base.policy == "selected_ml")]
            .sort_values("fold")
            .mean_cost.to_numpy()
            - base[(base.dataset == dataset) & (base.policy == "moving_average_28")]
            .sort_values("fold")
            .mean_cost.to_numpy()
        )
        findings.append(
            f"{dataset}: selected ML costs {ml.mean_cost:.6f} NCU/series/episode "
            f"versus MA28 {ma.mean_cost:.6f}; ML-minus-MA28 "
            f"{ml.mean_cost - ma.mean_cost:+.6f} "
            f"({100 * (ml.mean_cost / ma.mean_cost - 1):+.3f}%). Pooled fill "
            f"{ml.pooled_fill_rate:.6%} versus {ma.pooled_fill_rate:.6%}. Lowest base "
            f"cost: {LABELS[best]} ({b.loc[best].mean_cost:.6f}). Four origin "
            f"ML-minus-MA28 mean-cost differences: " + ", ".join(f"{v:+.6f}" for v in origins) + "."
        )
    sensitivity = []
    for dataset in ("store_item", "m5"):
        block = combined[combined.dataset.eq(dataset)].pivot(
            index="scenario", columns="policy", values="mean_cost"
        )
        delta = block.selected_ml - block.moving_average_28
        sensitivity.append(
            f"{dataset}: ML has lower mean cost than MA28 in "
            f"{int((delta < -1e-8).sum())}/17 scenarios, higher in "
            f"{int((delta > 1e-8).sum())}/17. Difference range {delta.min():+.6f} to "
            f"{delta.max():+.6f} NCU/series/episode. These counts are scenario "
            f"descriptions, not probabilities."
        )
        ml_cases = combined[
            combined.dataset.eq(dataset) & combined.policy.eq("selected_ml")
        ].set_index("scenario")
        deviations = ml_cases.mean_cost - ml_cases.loc["base", "mean_cost"]
        largest = deviations.drop("base").abs().idxmax()
        sensitivity.append(
            f"{dataset}: among these frozen one-at-a-time cases, the largest absolute "
            f"change in ML mean cost from base is {largest}: "
            f"{deviations.loc[largest]:+.6f} NCU/series/episode. "
            "This depends on the chosen parameter ranges and is not a general importance ranking."
        )
    pattern_differences = []
    for (dataset, group), block in pattern.groupby(["dataset", "group"], sort=True):
        by_policy = block.set_index("policy")
        ml, ma = by_policy.loc["selected_ml"], by_policy.loc["moving_average_28"]
        pattern_differences.append(
            {
                "dataset": dataset,
                "pattern": group,
                "series_episodes": int(ml.series_episodes),
                "ml_minus_ma28_cost": float(ml.mean_cost - ma.mean_cost),
                "ml_pooled_fill": float(ml.pooled_fill_rate)
                if np.isfinite(ml.pooled_fill_rate)
                else None,
                "ma28_pooled_fill": float(ma.pooled_fill_rate)
                if np.isfinite(ma.pooled_fill_rate)
                else None,
            }
        )
    records = {
        "status": "reported",
        "summary_sha256": sha256(REPORTS / "phase5_summary.json"),
        "base": main.to_dict("records"),
        "scenario_comparison": combined.to_dict("records"),
        "forecast_accuracy": accuracy.to_dict("records"),
        "coverage": coverage,
        "paired_ml_ma28": paired_detail,
        "findings": findings,
        "sensitivity": sensitivity,
        "pattern_comparison": pattern_differences,
        "figures": figures,
        "qualification": QUALIFICATION,
        "base_assumptions": BASE,
    }
    (REPORTS / "report_data.json").write_text(
        json.dumps(records, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    displayed = main[
        [
            "dataset",
            "policy",
            "mean_cost",
            "pooled_fill_rate",
            "average_on_hand",
            "stockout_days_per_episode",
        ]
    ]
    body = [
        "<h1>Phase 5: Inventory simulation review</h1>",
        f"<p class='warning'>{html.escape(QUALIFICATION)}</p>",
        "<h2>Scope and assumptions</h2>",
        f"<p>{html.escape(BASE)}</p>",
        (
            "<p>17 predefined scenarios × 8 dataset/origin cohorts × 4 policies = 544"
            " completed cases. No final holdout demand was used. Buffers and initial "
            "stocks use trailing 56-day origin-available means, not same-window "
            "errors. No target service probability is calibrated.</p>"
        ),
        "<h2>Base findings</h2>",
        *(f"<p>{html.escape(x)}</p>" for x in findings),
        table(displayed),
        "<h2>Sensitivity and interpretation</h2>",
        *(f"<p>{html.escape(x)}</p>" for x in sensitivity),
        (
            "<p>Higher forecast accuracy need not minimise an asymmetric "
            "finite-window inventory objective. Cost rankings depend on "
            "holding/shortage trade-offs, starting stock, pipeline timing, buffer and"
            " end-of-horizon cutoff. Four origins and repeated series are dependent. "
            "No confidence interval or significance test is asserted.</p>"
        ),
        "<h2>Scientific figures</h2>",
    ]
    for figure in figures:
        body += [
            f"<section><h3>{html.escape(figure['purpose'])}</h3><figure><a "
            f"href='{figure['svg']}'><img loading='lazy' src='{figure['png']}' "
            f"alt='{html.escape(figure['purpose'])}'></a><figcaption>{html.escape(figure['note'])} "
            f"<a href='{figure['svg']}'>Open SVG</a></figcaption></figure></section>"
        ]
    body += [
        "<h2>Coverage and fallback provenance</h2>",
        table(pd.DataFrame(coverage)),
        "<h2>Demand-pattern comparisons</h2>",
        table(pd.DataFrame(pattern_differences)),
        "<h2>Paired differences and sparse training groups</h2>",
        table(pd.DataFrame(paired_detail)),
        (
            "<p>The 6,878-series final-training all-zero-label group is retrospective"
            " relative to earlier validation origins. It uses training labels only "
            "and is a reporting group, never a decision input. Origin-specific masks "
            "are the primary origin-available sparse comparison. Labels do not imply "
            "that the full demand history is zero.</p>"
        ),
        (
            "<h2>Limits and reproducibility</h2><p>Unlimited deterministic supply; no"
            " observed stock, supplier constraints, calibrated costs or latent "
            "demand. No backorders. Finite episodes with reset inventory and "
            "identical late-order cutoff do not establish steady-state operational "
            "performance. Variability stress can change mean and zero frequency as "
            "well as variance. No realised savings or deployment recommendation "
            "follows.</p>"
        ),
        (
            "<ul><li><a href='../../docs/PHASE5_INVENTORY_RESULTS.md'>Results and "
            "commands</a></li><li><a href='../../docs/PHASE5_LIMITATIONS.md'>Threats "
            "to validity</a></li><li><a "
            "href='../../docs/PHASE5_CLAUDE_AUDIT_HANDOFF.md'>Independent audit "
            "handoff</a></li><li><a href='phase5_summary.json'>Independently "
            "reconciled machine results</a></li><li><a href='report_data.json'>Chart "
            "data and coverage</a></li></ul>"
        ),
    ]
    document = (
        (
            "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta "
            "name='viewport' "
            "content='width=device-width,initial-scale=1'><title>Phase 5 inventory "
            "simulation</title><style>body{font:16px/1.6 "
            "system-ui,sans-serif;color:#182b38;background:#f6f8fa;max-width:1240px;margin:auto;padding:28px}h1,h2,h3{line-height:1.25}h2{margin-top:2.5em}section,figure{margin:1.5em"
            " "
            "0}img{width:100%;height:auto;background:white}table{display:block;overflow-x:auto;border-collapse:collapse;max-width:100%;font-size:14px}th,td{padding:9px;border-bottom:1px"
            " solid "
            "#ccd5db;text-align:left;white-space:nowrap}.warning{border-left:5px "
            "solid "
            "#b77717;padding:16px;background:#fff4dd}a{color:#006778}figcaption{color:#405361;font-size:15px}</style></head><body>"
        )
        + "\n".join(body)
        + "</body></html>"
    )
    (REPORTS / "PHASE5_INVENTORY_REPORT.html").write_text(document, encoding="utf-8")
    (REPORTS / "VISUALISATION_INDEX.md").write_text(
        "# Phase 5 figure index\n\n"
        + QUALIFICATION
        + "\n\n"
        + "\n\n".join(
            f"- **{x['purpose']}** — both datasets. [PNG]({x['png']}) / "
            f"[SVG]({x['svg']}). {x['note']}"
            for x in figures
        )
        + "\n",
        encoding="utf-8",
    )
    docs = ROOT / "docs"
    commands = """```powershell
.venv\\Scripts\\python.exe -m ruff check . --no-cache
.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider `
    --basetemp artifacts/test_runs/phase5_review_unique
.venv\\Scripts\\python.exe -m pip check
.venv\\Scripts\\python.exe -m intelligent_demand.inventory.plan
.venv\\Scripts\\python.exe -m pytest `
    tests/test_inventory_design.py tests/test_inventory_engine.py `
    tests/test_inventory_integrity.py -q -p no:cacheprovider `
    --basetemp artifacts/test_runs/phase5_reference_unique
.venv\\Scripts\\python.exe -m intelligent_demand.inventory.runner smoke
.venv\\Scripts\\python.exe -m intelligent_demand.inventory.runner base
.venv\\Scripts\\python.exe -m intelligent_demand.inventory.audit base
.venv\\Scripts\\python.exe -m intelligent_demand.inventory.runner sensitivity
.venv\\Scripts\\python.exe -m intelligent_demand.inventory.audit all
.venv\\Scripts\\python.exe -m intelligent_demand.inventory.report
.venv\\Scripts\\python.exe -m intelligent_demand.inventory.report validate
.venv\\Scripts\\python.exe -m intelligent_demand.preservation.verify `
    --workspace-root . --overlay reports/inventory/documentation_overlay.json
```
Use fresh test temporary directories. Existing completed cases are hash-checked and reused;
immutable gates/audit receipts use exclusive creation and intentionally refuse overwrites.
For an independent audit repeat, call the audit CLI with `--receipt-directory` pointing to
a new empty directory. Never delete originals to make a rerun work. Smoke/audit gate receipts
are preserved. Rebuilding report.py overwrites derived charts/reports only, never scientific
inputs or simulation results. A fresh machine needs local ignored inputs listed in plan.json;
Git alone cannot reconstruct them. No command here fits or tunes a forecasting model or opens
the final holdout. Verify SHA-256 of plan/design/code and all input predictions; runner and
audit enforce these contracts. No forecast is advanced or regenerated during an episode.
"""
    (docs / "PHASE5_INVENTORY_RESULTS.md").write_text(
        "# Phase 5 inventory results\n\n"
        + QUALIFICATION
        + "\n\n"
        + BASE
        + "\n\n"
        + "\n\n".join(findings)
        + "\n\n"
        + markdown(displayed)
        + (
            "\n\nFull matched populations are evaluated for every scenario. Base events"
            " cover all series; sensitivity daily events retain only the six "
            "predeclared representatives per dataset, while per-series summaries "
            "cover everyone. Original run/model IDs, fallback counts, source hashes "
            "and timings are in case status manifests. ML policy names refer to the "
            "unchanged Store Item LightGBM and price-free M5 RF frozen choices.\n\n"
            "Independent audit: "
        )
        + str(saved["cases"])
        + " cases; "
        + str(saved["series_episodes"])
        + " series episodes; "
        + str(saved["independent_event_rows"])
        + " retained daily events; "
        + str(saved["scalar_reference_episodes"])
        + (
            " separate scalar replays. The input adapter is shared; state-machine "
            "arithmetic is independently implemented.\n\n[Offline "
            "report](../reports/inventory/PHASE5_INVENTORY_REPORT.html), [machine "
            "results](../reports/inventory/phase5_summary.json), [chart "
            "data](../reports/inventory/report_data.json).\n\n## Reproducibility\n\n"
        )
        + commands,
        encoding="utf-8",
    )
    (docs / "PHASE5_SENSITIVITY_ANALYSIS.md").write_text(
        "# Phase 5 sensitivity analysis\n\n"
        + QUALIFICATION
        + "\n\n"
        + "\n\n".join(sensitivity)
        + (
            "\n\n17 scenarios were frozen before outcomes: base plus one-at-a-time "
            "lead, buffer, initial cover, holding, shortage, fixed-order, terminal, "
            "variability and review changes. Every case uses the same full matched "
            "population and demand path across policies. See configs/inventory.yaml "
            "and immutable plan.json for exact values. No new policy or forecasting "
            "winner is selected.\n\nThe full per-scenario totals, fill, stock, unmet "
            "days, orders and paired differences are in phase5_summary.json and "
            "report_data.json. Figures show all lead/buffer levels and all 17 cost "
            "comparisons. The variability stress is max(0,mu+a*(sales-mu)); clipping "
            "changes mean/zeros as well as variability. Terminal-charge and "
            "initial-stock cases qualify finite-horizon effects but do not remove "
            "them. Buffer days are hypothetical coverage, not a calibrated "
            "probability.\n\nPer-series paired distributions are descriptive (10th, "
            "median, 90th percentiles); four-origin differences are reported "
            "individually. These are neither uncertainty intervals nor independent "
            "replications. Repeated series, shared products/stores and reused "
            "selection folds prevent an unsupported significance claim.\n"
        ),
        encoding="utf-8",
    )
    (docs / "PHASE5_LIMITATIONS.md").write_text(
        "# Phase 5 limitations\n\n"
        + QUALIFICATION
        + (
            "\n\n- Observed sales can be supply-censored; latent customer demand and "
            "actual lost sales are unknown.\n- All inventory states, lead times, costs"
            " and buffers are hypothetical; unlimited deterministic supply omits "
            "supplier constraints, minimum order sizes, capacity and disruptions.\n- "
            "Fixed-origin H28 forecasts and a common late-order cutoff support finite"
            " episodes only. Initial stock resets and empty pipelines are artificial;"
            " terminal stock is not salvaged in base costs. Orders beyond supported "
            "protection dates are prohibited even for ROP.\n- Equal stock is fair "
            "within a scenario, but initialization and endpoint handling can dominate"
            " the result. Terminal exposure is only a declared sensitivity, not a "
            "valuation model.\n- Buffers use trailing 56-day historical means; no "
            "calibrated target service probability or out-of-sample residual "
            "distribution is claimed. First origin needs no later residuals.\n- Four "
            "original validation windows were reused after model selection; results "
            "are exploratory, not independently held-out policy effectiveness. No "
            "final holdout target was read or scored.\n- Demand-pattern labels are "
            "existing training-prefix EDA. The final-training 6,878 sparse-label mask"
            " is retrospective for earlier origins and report-only. Origin-specific "
            "zero-label masks are separately provided. All-zero labels do not imply "
            "an all-zero historical series.\n- Per-series correlations reflect volume,"
            " error, bias and policy scale; they are not causal evidence. Four origin"
            " ranges and percentiles are descriptive, not confidence intervals.\n- "
            "Cost trade-offs can favour low-stock policies at lower service. "
            "Aggregate cost alone cannot establish operational superiority or "
            "deployment suitability.\n- Variability stresses alter mean/zeros too; "
            "one-at-a-time tests do not estimate a joint distribution of business "
            "uncertainty. No backorder model or oracle benchmark is implemented.\n- "
            "Git excludes large local inputs/results/figures. The preserved Phase 4 "
            "backup is local on the same device; Phase 5 outputs have not been "
            "independently backed up off-device.\n- HTML links and image decoding are "
            "checked locally; automated browser rendering is unavailable under the "
            "existing local-file policy.\n\nDeployment would require verified "
            "stock/pipeline/stockout histories, unconstrained-demand information, "
            "supplier distributions, lead-time/capacity constraints, measured "
            "economic costs and service objectives, and a fresh prospective "
            "operational test with approved forecast refresh cadence. Broader "
            "independent Claude review remains required before Phase 6/7; the prior "
            "limited conditional review is not comprehensive certification.\n"
        ),
        encoding="utf-8",
    )
    (docs / "PHASE5_CLAUDE_AUDIT_HANDOFF.md").write_text(
        (
            "# Phase 5 independent audit handoff\n\nScope: broader scientific and "
            "technical audit before Phase 6 and Phase 7. No Claude call was made by "
            "this implementation.\n\nRead INVENTORY_SIMULATION_PROTOCOL.md, "
            "INVENTORY_POLICY_MATHEMATICS.md, PHASE5_ASSUMPTIONS.md and "
            "INVENTORY_ENGINE.md for timing, policy mathematics, training-only "
            "calibration and fixed-origin availability. Review "
            "inventory/{design,plan,inputs,engine,runner,audit,report}.py and the "
            "three test_inventory_*.py files. Simulator policy decisions receive "
            "current position, historical means and frozen forecasts; future actuals "
            "and reporting labels are outside that interface. End-day t order arrives"
            " t+L+1; protection L+R; daily conservation is enforced.\n\nFrozen plan: `"
        )
        + p["sha256"]
        + "`; execution: `"
        + contract["sha256"]
        + (
            "`. Stored under artifacts/inventory/phase5. Each of 544 cases has atomic"
            " completion status and hashed per-series/event outputs; "
            "non-completed/tampered cases are rejected. Source model run "
            "IDs/configurations and fallback observations remain explicit. No final "
            "holdout was used.\n\n[Results](PHASE5_INVENTORY_RESULTS.md), "
            "[sensitivities](PHASE5_SENSITIVITY_ANALYSIS.md), "
            "[limitations](PHASE5_LIMITATIONS.md), [completion "
            "gate](PHASE5_COMPLETION_CHECKLIST.md), [offline "
            "report](../reports/inventory/PHASE5_INVENTORY_REPORT.html), [audit "
            "machine results](../reports/inventory/phase5_summary.json). Reproduction"
            " commands are in the results document. Large artefacts remain local and "
            "ignored; Git alone is insufficient. See the Phase 5 local evidence "
            "inventory for paths/bytes/hashes.\n\nScrutinise: common protection cutoff "
            "versus useful operating horizon; fairness and dominance of initial "
            "stock/terminal effects; hypothetical buffer versus true service targets;"
            " stockholding/service trade-offs and ROP interpretation; validation "
            "reuse; sparse subgroup chronology; scalar-reference independence and "
            "shared adapter risk; phase-origin source guards and original ledger "
            "preservation; resume/atomic status failures; report aggregation and "
            "plots. Explicitly distinguish internally checked gates from independent "
            "scientific approval. Do not rerun final forecasting or decode final "
            "targets during this audit.\n"
        ),
        encoding="utf-8",
    )
    with (docs / "PHASE5_INVENTORY_RESULTS.md").open("a", encoding="utf-8") as stream:
        stream.write(
            "\n\n## Demand-pattern details\n\n"
            + markdown(pd.DataFrame(pattern_differences))
            + "\n\n"
        )
        stream.write(
            "The M5 primary sparse-training masks are origin-specific. The separate 6,878-series "
            "final-training zero-label mask is retrospective and report-only. Coverage and "
            "paired per-series mean/median/10th/90th differences are in report_data.json. "
            "They are descriptive distributions, not confidence intervals.\n\n"
            "Audit correction: the first sensitivity replay reassociated S-IP as S-stock-pipeline. "
            "Fractional stress arithmetic around ceil produced a one-unit boundary disagreement. "
            "The separate reference now follows the declared IP=stock+pipeline grouping; all "
            "3,264 scalar episodes reconcile without changing production code/results or "
            "widening tolerances. Raw floating-point ceiling remains the deterministic numerical "
            "convention; near-integer fractional cases can be sensitive at the one-unit level. "
            "The failed diagnostic log is retained.\n"
        )
    print(
        json.dumps(
            {
                "status": "built",
                "figures": len(figures),
                "html": str((REPORTS / "PHASE5_INVENTORY_REPORT.html").relative_to(ROOT)),
                "findings": findings,
            },
            indent=2,
        )
    )


def validate():
    """Decode every exported image, validate offline links, check report accounting."""
    data = read(REPORTS / "report_data.json")
    summary = read(REPORTS / "phase5_summary.json")
    if sha256(REPORTS / "phase5_summary.json") != data["summary_sha256"]:
        raise ValueError("Report references changed audit results")
    expected = pooled(pd.DataFrame(summary["summaries"]), ["dataset", "scenario", "policy"])
    actual = pd.DataFrame(data["scenario_comparison"])
    pd.testing.assert_frame_equal(expected, actual, check_exact=False, rtol=1e-12, atol=1e-12)

    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links = []
            self.images = 0

        def handle_starttag(self, tag, attributes):
            values = dict(attributes)
            if tag in ("script", "iframe"):
                raise ValueError("Offline report must not depend on external execution")
            if tag == "img":
                self.images += 1
                if not values.get("alt"):
                    raise ValueError("Missing figure description")
            for name in ("href", "src"):
                if name in values:
                    self.links.append(values[name])

    parser = Links()
    parser.feed((REPORTS / "PHASE5_INVENTORY_REPORT.html").read_text(encoding="utf-8"))
    for value in parser.links:
        if ":" in value or value.startswith(("/", "\\")):
            raise ValueError("Absolute or network dependency in offline report")
        if not (REPORTS / value).resolve().is_file():
            raise ValueError("Broken offline report link: " + value)
    if parser.images != 10 or len(data["figures"]) != 10:
        raise ValueError("Missing requested scientific figure")
    images = []
    for figure in data["figures"]:
        for extension in ("png", "svg"):
            path = (REPORTS / figure[extension]).resolve()
            if extension == "png":
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    if min(image.size) < 500:
                        raise ValueError("Insufficient figure resolution")
                    dimensions = list(image.size)
            else:
                if not ET.parse(path).getroot().tag.endswith("svg"):
                    raise ValueError("Malformed SVG")
                dimensions = None
            images.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "dimensions": dimensions,
                }
            )
    record = {
        "status": "passed",
        "figures": images,
        "offline_links": len(parser.links),
        "scenario_rows_reconciled": len(actual),
        "browser_rendering": "not performed",
        "scope": "Image decoding/XML, local link checks and saved chart-data accounting; "
        "visual inspection is recorded separately in the completion gate",
        "html_sha256": sha256(REPORTS / "PHASE5_INVENTORY_REPORT.html"),
        "report_data_sha256": sha256(REPORTS / "report_data.json"),
    }
    from intelligent_demand.preservation.backup import write_new

    write_new(REPORTS / "report_validation.json", record)
    print(json.dumps({k: v for k, v in record.items() if k != "figures"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=["build", "validate"], default="build")
    args = parser.parse_args()
    if args.action == "validate":
        validate()
    else:
        build()
