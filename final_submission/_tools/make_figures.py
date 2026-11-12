"""Phase 8 figures generated ONLY from frozen, hash-verified project evidence (read-only; no model, holdout or simulation rerun).

Run from the repository root with the project venv:
    .venv\\Scripts\\python.exe final_submission\\_tools\\make_figures.py

Inputs (all pre-existing):
  artifacts/experiments/phase4/frozen_selection.json        validation fold MAE of the frozen candidates
  artifacts/experiments/phase4/final_metrics/*.json         sealed final-holdout metrics (hash-checked via final_evaluation.json)
  reports/inventory/post_audit_reconciliation.json          Phase 5 base results by origin and pooled
Outputs: final_submission/figures/*.png and figure_data.json (the exact numbers plotted).
"""

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "final_submission" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
P4 = ROOT / "artifacts/experiments/phase4"

# Validated categorical palette (dataviz reference instance; CVD separation PASS). Fixed per entity, never by rank.
COLOR = {
    "selected_ml": "#2a78d6",
    "moving_average_28": "#eb6834",
    "seasonal_naive": "#1baf7a",
    "fixed_reorder_point": "#eda100",
    "tsb": "#6250d6",
    "holt_winters": "#6250d6",
    "seasonal_moving_average": "#e87ba4",
}
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e6e5e0", "#ffffff"
LABEL = {
    "selected_ml": "Selected ML",
    "moving_average_28": "MA28",
    "seasonal_naive": "Seasonal Naive",
    "fixed_reorder_point": "Fixed ROP (low-stock comparator)",
}

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "axes.titlecolor": INK,
        "legend.frameon": False,
    }
)
data = {}


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def role_of(trial):
    for key, role in (
        ("random_forest", "selected_ml"),
        ("lightgbm", "selected_ml"),
        ("seasonal_naive", "seasonal_naive"),
        ("moving_average_28", "moving_average_28"),
        ("tsb", "tsb"),
        ("holt_winters", "holt_winters"),
        ("seasonal_moving_average", "seasonal_moving_average"),
    ):
        if key in trial:
            return role
    raise KeyError(trial)


PRETTY = {
    "store_item_lightgbm_00": "LightGBM (selected)",
    "m5_random_forest_02": "Random Forest, price-free (selected)",
    "store_item_seasonal_naive_reference": "Seasonal Naive",
    "m5_seasonal_naive_reference": "Seasonal Naive",
    "store_item_seasonal_moving_average_reference": "Seasonal Moving Average",
    "m5_moving_average_28_reference": "MA28",
    "store_item_holt_winters_additive_01": "Holt-Winters additive",
    "m5_tsb_01": "TSB",
}
DS = {"store_item": "Store Item (500 series)", "m5": "M5 (30,490 series)"}

# ---------------------------------------------------------------- evidence
frozen = json.loads((P4 / "frozen_selection.json").read_text(encoding="utf-8"))
final_eval = json.loads((P4 / "final_evaluation.json").read_text(encoding="utf-8"))
final = {}
for r in final_eval["results"]:
    raw = (P4 / r["metrics"]["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == r["metrics"]["sha256"], r["trial_id"]
    final[r["trial_id"]] = json.loads(raw)["all"]
recon = json.loads((ROOT / "reports/inventory/post_audit_reconciliation.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------- Figure: validation MAE by origin
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
data["validation_fold_mae"] = {}
for ax, ds in zip(axes, ("store_item", "m5"), strict=True):
    for e in frozen["datasets"][ds]["evaluations"]:
        role = role_of(e["trial_id"])
        ys = e["fold_mae"]
        data["validation_fold_mae"][e["trial_id"]] = ys
        lw = 2.6 if e["role"] == "selected" else 1.6
        ax.plot(
            [1, 2, 3, 4],
            ys,
            marker="o",
            ms=7 if e["role"] == "selected" else 5,
            lw=lw,
            color=COLOR[role],
            label=PRETTY[e["trial_id"]],
            zorder=3 if e["role"] == "selected" else 2,
        )
    ax.set_title(DS[ds], loc="left")
    ax.set_xticks([1, 2, 3, 4], ["Origin 1", "Origin 2", "Origin 3", "Origin 4"])
    ax.set_ylabel("Macro MAE (units per day)")
    ax.legend(fontsize=9, loc="upper left" if ds == "store_item" else "center right")
fig.suptitle("Validation MAE at the four expanding origins (lower is better)", x=0.01, ha="left", fontweight="bold", color=INK)
fig.text(
    0.01,
    -0.03,
    "Source: artifacts/experiments/phase4/frozen_selection.json (fold_mae). Origins are adjacent windows, not independent replications.",
    fontsize=8.5,
    color=MUTED,
)
fig.tight_layout()
save(fig, "fig_validation_by_origin")

# ---------------------------------------------------------------- Figure: final holdout MAE
fig, axes = plt.subplots(1, 2, figsize=(11, 4.0))
data["final_holdout"] = {}
for ax, ds in zip(axes, ("store_item", "m5"), strict=True):
    trials = [t for t in final if t.startswith(ds + "_")]
    trials.sort(key=lambda t: final[t]["macro"]["mae"], reverse=True)
    vals = [final[t]["macro"]["mae"] for t in trials]
    data["final_holdout"][ds] = {
        t: {
            "macro_mae": final[t]["macro"]["mae"],
            "pooled_rmse": final[t]["pooled"]["rmse"],
            "pooled_wape_percent": final[t]["pooled"]["wape_percent"],
            "macro_mase": final[t]["macro"]["mase"],
            "macro_rmsse": final[t]["macro"]["rmsse"],
        }
        for t in trials
    }
    bars = ax.barh([PRETTY[t] for t in trials], vals, color=[COLOR[role_of(t)] for t in trials], height=0.6, edgecolor=SURFACE, linewidth=2)
    for b, v in zip(bars, vals, strict=True):
        ax.text(v + max(vals) * 0.01, b.get_y() + b.get_height() / 2, f"{v:.3f}", va="center", fontsize=10, color=INK)
    ax.set_xlim(0, max(vals) * 1.18)
    ax.set_title(DS[ds], loc="left")
    ax.set_xlabel("Macro MAE on the sealed final 28-day holdout")
    ax.grid(axis="y", visible=False)
fig.suptitle(
    "Final holdout: frozen selections and predeclared comparators (evaluated once)", x=0.01, ha="left", fontweight="bold", color=INK
)
fig.text(
    0.01,
    -0.04,
    "Source: artifacts/experiments/phase4/final_metrics/*.json (SHA-256 verified against final_evaluation.json). "
    "Store Item 2017-12-04 to 2017-12-31; M5 2016-04-25 to 2016-05-22.",
    fontsize=8.5,
    color=MUTED,
)
fig.tight_layout()
save(fig, "fig_final_holdout")

# ---------------------------------------------------------------- Figure: M5 metric dependence (relative to MA28)
m5 = ["m5_random_forest_02", "m5_tsb_01"]
metrics = [
    ("macro", "mae", "Macro MAE (primary)"),
    ("pooled", "rmse", "Pooled RMSE"),
    ("pooled", "wape_percent", "Pooled WAPE"),
    ("macro", "mase", "Macro MASE"),
    ("macro", "rmsse", "Macro RMSSE"),
]
fig, ax = plt.subplots(figsize=(10, 4.2))
data["m5_relative_to_ma28"] = {}
width = 0.2
for i, t in enumerate(m5):
    rel = [100 * (final[t][a][b] / final["m5_moving_average_28_reference"][a][b] - 1) for a, b, _ in metrics]
    data["m5_relative_to_ma28"][t] = dict(zip([m[2] for m in metrics], rel, strict=True))
    xs = [k + (i - 0.5) * 0.3 for k in range(len(metrics))]
    ax.bar(xs, rel, width=0.28, color=COLOR[role_of(t)], label=PRETTY[t])
    for x, v in zip(xs, rel, strict=True):
        if abs(v) > 1e-9:
            ax.text(x, v + (0.06 if v >= 0 else -0.06), f"{v:+.2f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=9, color=INK)
ax.axhline(0, color=COLOR["moving_average_28"], lw=2, label="MA28 reference (0%)")
ax.set_xticks(range(len(metrics)), [m[2] for m in metrics])
ax.set_ylabel("% difference vs MA28 (negative = better)")
ax.set_ylim(-2.6, 2.4)
ax.legend(fontsize=9, ncol=3, loc="upper left")
ax.set_title("M5 final holdout: the ranking depends on the metric", loc="left")
fig.text(
    0.01,
    -0.04,
    "RF is best on MAE, RMSE, WAPE and RMSSE but worse than MA28 and TSB on macro MASE. Seasonal Naive (12-30% worse "
    "on every metric) is omitted for scale. Source: final_metrics/*.json.",
    fontsize=8.5,
    color=MUTED,
)
fig.tight_layout()
save(fig, "fig_m5_metric_dependence")

# ---------------------------------------------------------------- Figure: inventory differences by origin
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
data["inventory_ml_minus_reference_by_origin"] = {}
for ax, ds in zip(axes, ("store_item", "m5"), strict=True):
    by = recon["base_by_origin"][ds]
    diffs = {
        ref: [by[o]["selected_ml"]["mean_cost"] - by[o][ref]["mean_cost"] for o in ("1", "2", "3", "4")]
        for ref in ("moving_average_28", "seasonal_naive")
    }
    data["inventory_ml_minus_reference_by_origin"][ds] = diffs
    for j, ref in enumerate(("moving_average_28", "seasonal_naive")):
        xs = [k + (j - 0.5) * 0.36 for k in range(4)]
        ax.bar(xs, diffs[ref], width=0.34, color=COLOR[ref], label=f"Selected ML minus {LABEL[ref]}")
        span = max(abs(v) for d in diffs.values() for v in d)
        for x, v in zip(xs, diffs[ref], strict=True):
            ax.text(
                x,
                v + (span * 0.03 if v >= 0 else -span * 0.03),
                f"{v:+.1f}" if ds == "store_item" else f"{v:+.2f}",
                ha="center",
                va="bottom" if v >= 0 else "top",
                fontsize=8.5,
                color=INK,
            )
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xticks(range(4), ["Origin 1", "Origin 2", "Origin 3", "Origin 4"])
    ax.set_ylabel("NCU per series per 28-day episode")
    ax.set_title(DS[ds], loc="left")
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo * 1.25, hi * 1.35 if hi > 0 else hi)
fig.legend(*axes[0].get_legend_handles_labels(), loc="upper right", ncol=2, fontsize=9, bbox_to_anchor=(1.0, 1.0))
fig.suptitle(
    "Simulated cost difference, Selected ML minus baseline (below zero = ML cheaper)",
    x=0.01,
    y=1.07,
    ha="left",
    fontweight="bold",
    color=INK,
)
fig.text(
    0.01,
    -0.04,
    "Hypothetical normalised cost units (NCU) from a validation-reused simulation; not realised savings. "
    "Source: reports/inventory/post_audit_reconciliation.json.",
    fontsize=8.5,
    color=MUTED,
)
fig.tight_layout()
save(fig, "fig_inventory_by_origin")

# ---------------------------------------------------------------- Figure: cost versus fill trade-off (labelled bars)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.0))
data["inventory_pooled"] = recon["base_pooled"]
order = ["selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point"]
for ax, ds in zip(axes, ("store_item", "m5"), strict=True):
    pooled = recon["base_pooled"][ds]
    ys = list(range(len(order)))[::-1]
    costs = [pooled[p]["mean_cost"] for p in order]
    ax.barh(ys, costs, color=[COLOR[p] for p in order], height=0.6, edgecolor=SURFACE, linewidth=2)
    for y, pol, c in zip(ys, order, costs, strict=True):
        ax.text(
            c + max(costs) * 0.015,
            y,
            f"{c:,.1f} NCU | fill {100 * pooled[pol]['pooled_fill_rate']:.2f}% | on-hand {pooled[pol]['average_on_hand']:,.1f}",
            va="center",
            fontsize=8.6,
            color=INK,
        )
    ax.set_yticks(ys, ["Selected ML", "MA28", "Seasonal Naive", "Fixed ROP\n(low-stock comparator)"])
    ax.set_xlim(0, max(costs) * 2.05)
    ax.set_xlabel("Mean cost, NCU per series per 28-day episode")
    ax.set_title(DS[ds], loc="left")
    ax.grid(axis="y", visible=False)
fig.suptitle(
    "Base scenario, pooled over four origins: the cheapest rule holds the least stock and serves least",
    x=0.01,
    ha="left",
    fontweight="bold",
    color=INK,
)
fig.text(
    0.01,
    -0.04,
    "Fixed ROP is a low-stock, lower-service comparator, not a better policy. NCU are hypothetical, not savings. "
    "Source: post_audit_reconciliation.json (base_pooled).",
    fontsize=8.5,
    color=MUTED,
)
fig.tight_layout()
save(fig, "fig_cost_fill_tradeoff")

# ---------------------------------------------------------------- Figure: rolling-origin design
import datetime as dt  # noqa: E402

fig, axes = plt.subplots(2, 1, figsize=(11, 3.8), sharex=False)
design = {
    "store_item": ("2013-01-01", ["2017-08-13", "2017-09-10", "2017-10-08", "2017-11-05"], "2017-12-03", "2017-12-31"),
    "m5": ("2011-01-29", ["2016-01-03", "2016-01-31", "2016-02-28", "2016-03-27"], "2016-04-24", "2016-05-22"),
}
data["rolling_origin_design"] = design
d = lambda s: dt.date.fromisoformat(s)  # noqa: E731
for ax, (ds, (start, origins, final_origin, end)) in zip(axes, design.items(), strict=True):
    view0 = d(origins[0]) - dt.timedelta(days=60)
    rows = origins + [final_origin]
    for i, o in enumerate(rows):
        y = len(rows) - i
        ax.barh(y, (d(o) - view0).days, left=view0, color="#cde2fb", height=0.62)
        color = "#d03b3b" if o == final_origin else COLOR["selected_ml"]
        ax.barh(y, 28, left=d(o) + dt.timedelta(days=1), color=color, height=0.62)
        ax.text(
            d(o) + dt.timedelta(days=31),
            y,
            "final holdout (read once)" if o == final_origin else f"validation fold {i + 1}",
            va="center",
            fontsize=8.5,
            color=INK,
        )
    ax.set_yticks([])
    ax.set_xlim(view0, d(end) + dt.timedelta(days=48))
    ax.set_title(f"{DS[ds]}: training from {start} (expanding), 28-day targets", loc="left", fontsize=10.5)
    ax.grid(axis="y", visible=False)
fig.suptitle(
    "Chronological expanding-origin design (light: training history; dark: 28-day forecast window)",
    x=0.01,
    ha="left",
    fontweight="bold",
    color=INK,
)
fig.tight_layout()
save(fig, "fig_rolling_origin")

# ---------------------------------------------------------------- Figure: system architecture
fig, ax = plt.subplots(figsize=(12, 5.2))
ax.set_xlim(0, 13.0)
ax.set_ylim(0, 5.4)
ax.axis("off")


def box(x, y, w, h, title, lines, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=MUTED, lw=1))
    ax.text(x + 0.15, y + h - 0.22, title, fontsize=10.5, fontweight="bold", color=INK, va="top")
    for k, line in enumerate(lines):
        ax.text(x + 0.15, y + h - 0.6 - 0.29 * k, line, fontsize=8.6, color=INK2, va="top")


def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14, color=INK2, lw=1.3))


def note(x, y, text, ha="center"):
    ax.text(x, y, text, fontsize=8, color=INK2, ha=ha)


box(0.1, 3.0, 2.6, 1.9, "Browser", ["Five research pages", "Typed /api/v1 client", "No secrets, no DB access"], "#f2f6fd")
box(
    4.0,
    2.8,
    3.0,
    2.1,
    "idf-web (Vercel, fra1)",
    ["Next.js 16 route handlers", "Validation, rate limiting", "Exact-float read transactions", "Security headers"],
    "#f2f6fd",
)
box(
    8.9,
    2.8,
    3.1,
    2.1,
    "idf-engine (Vercel, fra1)",
    ["FastAPI simulation service", "Frozen Phase 5 engine", "Vercel Authentication", "(all deployments)"],
    "#f3f9f5",
)
box(
    4.0,
    0.2,
    3.0,
    1.7,
    "Supabase Postgres 17",
    ["eu-central-1, transaction pooler", "Read-only roles", "655,711 exported evidence rows"],
    "#fdf6ea",
)
box(
    8.9,
    0.2,
    3.1,
    1.7,
    "Offline research pipeline",
    ["Phases 1-5 (Python)", "Frozen evidence + manifests", "Power BI report (Phase 6)"],
    "#f4f3f1",
)
arrow(2.7, 3.95, 4.0, 3.95)
note(3.35, 4.08, "HTTPS JSON")
arrow(7.0, 3.95, 8.9, 3.95)
note(7.95, 4.32, "engine key +")
note(7.95, 4.08, "bypass header")
arrow(5.5, 2.8, 5.5, 1.9)
note(5.65, 2.45, "webapp_api, TLS,", ha="left")
note(5.65, 2.2, "exact floats", ha="left")
arrow(10.45, 2.8, 7.05, 1.75)
note(10.6, 2.45, "engine_api: saved demand", ha="left")
note(10.6, 2.2, "and forecasts, server-side", ha="left")
arrow(8.9, 0.75, 7.0, 0.75)
note(7.95, 0.88, "seeded export")
save(fig, "fig_architecture")

(OUT / "figure_data.json").write_text(json.dumps(data, indent=1, default=str) + "\n", encoding="utf-8")
print("figures:", sorted(p.name for p in OUT.glob("*.png")))
