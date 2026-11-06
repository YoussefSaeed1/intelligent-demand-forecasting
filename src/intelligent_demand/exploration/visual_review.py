"""Audit existing EDA images and assemble a portable, offline visual review.

Run with ``python -m intelligent_demand.exploration.visual_review``. Reproduction
renders only the small saved chart inputs into ignored verification copies.
It never calls ingestion, transformation, forecasting or full-panel analysis.
"""

import argparse
import base64
import hashlib
import io
import json
import os
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from intelligent_demand.config import load_config

COMMON = {
    "distribution": (
        "Daily sales distribution",
        "Exact daily-unit frequencies and the cumulative distribution of positive sales.",
        ["distribution", "largest_observations"],
    ),
    "trends": (
        "Daily and monthly sales",
        "Daily aggregate units, trailing 28-day mean and complete calendar-month totals.",
        ["daily", "monthly"],
    ),
    "calendar_patterns": (
        "Weekly and annual calendar structure",
        "Within-week ratios with pointwise bootstrap intervals and normalised monthly profiles.",
        ["weekdays", "month_year"],
    ),
    "intermittency": (
        "Demand-pattern classifications",
        "Store Item positive-size variability and smooth-population facts; M5 ADI/CV² scatter.",
        ["series", "patterns"],
    ),
    "zeros_variability": (
        "Zero-sales frequency and variability",
        "Series-level zero percentages and the distribution of defined positive all-sales CVs.",
        ["series"],
    ),
    "concentration": (
        "Product sales concentration",
        "Cumulative sales shares ordered by product volume and the ten highest-volume products.",
        ["products"],
    ),
    "stores": (
        "Store-level comparisons",
        "Units per store-product day and zero-sales percentages, with equal historical exposure.",
        ["stores"],
    ),
    "diagnostics": (
        "Trend, annual structure and autocorrelation",
        "Log aggregate sales/trend, approximate annual component and first-differenced log ACF.",
        ["components", "acf"],
    ),
    "volatility": (
        "Rolling volatility and zero-sales breadth",
        (
            "Aggregate 28-day coefficient of variation and the daily "
            "percentage of zero-selling series."
        ),
        ["daily"],
    ),
    "representatives": (
        "Representative demand histories",
        (
            "Deterministic examples with explicit windows; "
            "zero/single-positive M5 cases show full training histories."
        ),
        ["representative_series", "series"],
    ),
}
EXTRA = {
    "price_missingness": (
        "Historical price coverage and sales activity",
        "Full-history price gaps by date/store/year, plus the training-only activity partition.",
        [
            "price_by_date_full_quality",
            "price_by_store_full_quality",
            "price_by_year_full_quality",
            "price_by_series_eda",
        ],
    ),
    "price_products": (
        "Price coverage by product and series",
        (
            "Product missing-price rates and their descriptive relationship "
            "to series zero-sales rates."
        ),
        ["price_by_product_full_quality", "price_by_series_eda", "series"],
    ),
    "events_groups": (
        "Calendar events and product categories",
        "Ten lowest-mean named events and category-level trailing means adjusted by series count.",
        ["calendar_events", "cat_id_daily", "series"],
    ),
}
COMMON["extremes"] = (
    "Unusual sales and the empirical tail",
    "Full-population tail probabilities and clearly labelled retained extreme examples.",
    ["distribution", "largest_observations", "series"],
)
EXTRA["snap"] = (
    "SNAP versus non-SNAP calendar days",
    "Within-state units per store-day, with the actual flagged/non-flagged exposures.",
    ["snap_associations"],
)
EXTRA["departments"] = (
    "Department-level demand",
    "Daily rates per department series and monthly mean daily rates, not raw unequal totals.",
    ["dept_id_daily", "series"],
)
M5_ONLY = {
    "classification": (
        "All M5 demand classes",
        "Log-position counts with exact counts and percentages, including minority histories.",
        ["patterns", "series"],
    )
}
LABELS = {"store_item": "Store Item", "m5": "M5", "both": "Both datasets"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory():
    records = []
    for dataset in ("store_item", "m5"):
        for name, (title, purpose, tables) in {
            **COMMON,
            **({**M5_ONLY, **EXTRA} if dataset == "m5" else {}),
        }.items():
            records.append(
                {
                    "stem": f"{dataset}_{name}",
                    "dataset": dataset,
                    "kind": name,
                    "title": title,
                    "purpose": purpose,
                    "tables": [f"tables/{dataset}/{t}.parquet" for t in tables],
                }
            )
    records.append(
        {
            "stem": "cross_dataset_comparison",
            "dataset": "both",
            "kind": "comparison",
            "title": "Different sales structures across datasets",
            "purpose": "Compare zero-sales frequency, median series CV and product concentration.",
            "tables": ["store_item_results.json", "m5_results.json"],
        }
    )
    return records


def svg_signature(path):
    """Compare rendered SVG content, excluding timestamps and random artist IDs."""
    root = ET.parse(path).getroot()
    ids = {e.attrib["id"]: f"artist_{i}" for i, e in enumerate(root.iter()) if "id" in e.attrib}

    def normalise(value):
        if value.startswith("data:image/png;base64,"):
            with Image.open(io.BytesIO(base64.b64decode(value.split(",", 1)[1]))) as im:
                return hashlib.sha256(im.convert("RGBA").tobytes()).hexdigest()
        for key, target in ids.items():
            value = value.replace(f"url(#{key})", f"url(#{target})")
            if value == f"#{key}":
                value = f"#{target}"
        return " ".join(value.split())

    def visit(element):
        attrs = {
            key: ids[value] if key == "id" else normalise(value)
            for key, value in element.attrib.items()
        }
        return (
            element.tag,
            attrs,
            " ".join((element.text or "").split()),
            [visit(child) for child in element if not child.tag.endswith("metadata")],
        )

    return visit(root)


def check_tables(directory, results):
    """Cross-check consequential displayed quantities without rereading large source panels."""
    checks = {}
    for name, result in results.items():
        tables = directory / "tables" / name

        def read(table, tables=tables):
            return pd.read_parquet(tables / f"{table}.parquet")

        series, daily, hist = read("series"), read("daily"), read("distribution")
        products, stores, monthly = read("products"), read("stores"), read("monthly")
        assert len(series) == result["series"]
        assert int(hist.observations.sum()) == result["eda_rows"]
        assert int(hist.loc[hist.units.eq(0), "observations"].sum()) == result["eda_zero_count"]
        for total in (
            series.sales_units.sum(),
            daily.sales_units.sum(),
            products.sales_units.sum(),
            stores.sales_units.sum(),
            np.dot(hist.units, hist.observations),
        ):
            assert total == result["eda_sales_units"], name
        assert daily.date.min() == pd.Timestamp(result["split_plan"]["eda_start"])
        assert daily.date.max() == pd.Timestamp(result["split_plan"]["eda_end"])
        recomputed_months = daily.groupby(daily.date.dt.strftime("%Y-%m")).sales_units.sum()
        np.testing.assert_array_equal(recomputed_months, monthly.sales_units)
        np.testing.assert_allclose(
            daily.sales_units.rolling(28).mean(), daily.mean_28d, equal_nan=True
        )
        np.testing.assert_allclose(
            stores.sales_units / (stores.series * result["eda_days"]),
            stores.mean_units_per_series_day,
        )
        actual = series.pattern.value_counts().to_dict()
        assert all(actual.get(key, 0) == value for key, value in result["patterns"].items())
        cv = series.std_units / series.mean_units.replace(0, np.nan)
        assert np.isclose(cv.median(), result["median_series_cv"])
        top = int(np.ceil(len(products) / 10))
        assert np.isclose(
            products.nlargest(top, "sales_units").sales_units.sum() / products.sales_units.sum(),
            result["product_top10_percent_share"],
        )
        iso = daily.date.dt.isocalendar()
        week = iso.year.astype(str) + "-" + iso.week.astype(str)
        grid = (
            daily.assign(week=week, weekday=daily.date.dt.day_of_week)
            .pivot(index="week", columns="weekday", values="sales_units")
            .dropna()
        )
        ratios = grid.div(grid.mean(axis=1), axis=0).mean()
        np.testing.assert_allclose(ratios, read("weekdays").mean_within_week_ratio)
        if name == "m5":
            for field in ("date", "year", "store", "product"):
                price = read(f"price_by_{field}_full_quality")
                assert (
                    price.missing_prices.sum()
                    == result["price_missingness"]["full_history_missing"]
                )
            activity = read("price_by_series_eda")
            for column, value in result["price_missingness"]["eda_activity_partition"].items():
                assert activity[column].sum() == value
            category = read("cat_id_daily").groupby("date").sales_units.sum()
            np.testing.assert_array_equal(category, daily.sales_units)
            departments = read("dept_id_daily").groupby("date").sales_units.sum()
            np.testing.assert_array_equal(departments, daily.sales_units)
            snap = read("snap_associations")
            assert np.isclose(
                (snap.mean_store_daily_units * snap.store_days).sum(),
                result["eda_sales_units"],
                rtol=0,
                atol=1e-7,
            )
            exposure = series[["store_id", "state_id"]].drop_duplicates().groupby("state_id").size()
            assert (
                snap.groupby("state").store_days.sum().to_dict()
                == (exposure * result["eda_days"]).to_dict()
            )
        for path in tables.glob("*.parquet"):
            if "full_quality" in path.name:
                continue
            frame = pd.read_parquet(path)
            if "date" in frame:
                assert frame.date.between(daily.date.min(), daily.date.max()).all(), path.name
        extreme = read("largest_observations")
        assert (
            extreme.sales_units.max() == hist.units.max() == result["distribution_quantiles"]["1.0"]
        )
        checks[name] = "saved chart inputs reconcile with EDA quantities, scope and reported ratios"
    return checks


def reproduce_images(config, results, output):
    """Render disposable comparison copies from saved tables; preserve every original."""
    from intelligent_demand.exploration import reporting

    copied = replace(config, paths={**config.paths, "reports": output})
    (output / "eda").mkdir(parents=True, exist_ok=True)
    original_save = reporting._save
    reporting._save = lambda _config, *args: original_save(copied, *args)
    try:
        for result in results.values():
            reporting.figures(config, result)
        reporting.comparative_report(copied, results)
    finally:
        reporting._save = original_save


def notes(record, result):
    kind = record["kind"]
    descriptions = {
        ("distribution"): (
            "Frequency axis is logarithmic; the positive CDF excludes "
            "zeros. No sales were imputed or removed."
        ),
        ("trends"): (
            "Complete monthly totals are shown; boundary months are "
            "excluded. Raw units are source-specific."
        ),
        ("calendar_patterns"): (
            "500 four-week-block resamples, seed 42; pointwise 95% "
            "intervals, not causal estimates. Monthly profiles use "
            "complete years."
        ),
        ("intermittency"): (
            "ADI=1.32 and positive-size CV²=0.49 are descriptive "
            "cutoffs, not a model-selection rule. Undefined histories "
            "are counted separately."
        ),
        ("classification"): (
            "Every published M5 series is included. The log count axis "
            "makes small groups visible; labels give exact shares of "
            "30,490 series."
        ),
        ("zeros_variability"): (
            "Recorded zeros are retained. All-sales CV is undefined for "
            "M5's 16 all-zero histories. Store Item CV uses readable "
            "linear decimal ticks."
        ),
        ("concentration"): (
            "Products aggregate over stores. The curve uses fractions; "
            "compare within-source shares rather than physical units "
            "across datasets."
        ),
        ("stores"): (
            "Rates divide by each store's observed series-days. Store "
            "Item's one zero is annotated explicitly, rather than hidden "
            "on a broad percentage axis."
        ),
        ("diagnostics"): (
            "Historical STL diagnostics do not forecast. A 365-day "
            "period approximates the leap calendar; aggregate patterns "
            "need not hold at leaf level."
        ),
        ("volatility"): (
            "The first 27 rolling statistics are undefined. Store Item "
            "zero breadth is shown as an exact count; M5 breadth is a "
            "percentage."
        ),
        ("representatives"): (
            "These median-ranked examples do not estimate the "
            "population. Independent y-scales and date windows are "
            "explicit; all quantities are non-negative."
        ),
        ("price_missingness"): (
            "Coverage panels use full-history price fields only. "
            "Activity categories use training sales only; the 465 "
            "reserved gaps have no sales-activity analysis."
        ),
        ("price_products"): (
            "The left panel uses full-history price coverage; the right "
            "uses training-only sales/price summaries. Neither "
            "establishes stock availability."
        ),
        ("events_groups"): (
            "Only ten lowest-mean named events are displayed. Exact "
            "labels expose Christmas's small total; event groups overlap "
            "and are not causal effects."
        ),
        ("snap"): (
            "Means divide by actual observed store-days within each "
            "state/flag. Different dates, holidays and assortment remain "
            "confounders; flags are not observed customer benefit use."
        ),
        ("departments"): (
            "Each rate divides by the department's published series "
            "count. Complete daily training coverage is used; monthly "
            "heatmap boundary months may be partial."
        ),
        ("extremes"): (
            "The empirical tail uses every training observation. The "
            "saved top-20 table supplies ten labelled examples; ties are "
            "not exhaustive and extremes are not declared errors."
        ),
        ("comparison"): (
            "Different dates, identities and unit semantics permit "
            "methodological comparison, not direct model transfer or "
            "pooled raw-unit error comparisons."
        ),
    }
    return descriptions[kind]


def findings(record, results, directory):
    name, kind = record["dataset"], record["kind"]
    if name == "both":
        return (
            (
                "M5 has 68.84% zero-sale observations, versus one in Store "
                "Item; its top 10% of products account for 51.68% of units "
                "versus 16.28%."
            ),
            (
                "Compare methods independently on each source, with "
                "source-specific baselines and explicit metric coverage."
            ),
        )
    result = results[name]
    table_dir = directory / "tables" / name
    if kind in ("intermittency", "classification"):
        finding = (
            "All 500 Store Item histories are descriptively smooth."
            if name == "store_item"
            else (
                "M5 includes 23,044 intermittent, 5,953 lumpy, 983 smooth, "
                "489 erratic, 16 all-zero and 5 single-positive histories."
            )
        )
        return (
            finding,
            (
                "Test suitable model families by training-only demand "
                "stratum; classifications do not prove a winning method."
            ),
        )
    if kind == "snap":
        frame = pd.read_parquet(table_dir / "snap_associations.parquet")
        text = []
        for state, block in frame.groupby("state"):
            means = block.set_index("snap_flag").mean_store_daily_units
            text.append(f"{state}: {means[1]:,.1f} versus {means[0]:,.1f}")
        return (
            "SNAP / non-SNAP mean units per store-day: " + "; ".join(text) + ".",
            (
                "Consider calendar flags only under an origin-availability "
                "contract; do not interpret these differences causally."
            ),
        )
    if kind == "departments":
        from intelligent_demand.exploration.presentation import department_summary

        frame = department_summary(
            pd.read_parquet(table_dir / "dept_id_daily.parquet"),
            pd.read_parquet(table_dir / "series.parquet"),
        )
        means = frame.groupby("group").units_per_series_day.mean()
        return (
            (
                "Mean daily rates range from "
                f"{means.min():.3f}"
                " ("
                f"{means.idxmin()}"
                ") to "
                f"{means.max():.3f}"
                " ("
                f"{means.idxmax()}"
                ") units per series."
            ),
            (
                "A global model may share information within hierarchy "
                "groups; compare rate and sparsity differences before "
                "choosing that structure."
            ),
        )
    if kind == "extremes":
        return (
            (
                "The maximum recorded training observation is "
                f"{result['distribution_quantiles']['1.0']:,}"
                " units; the 99th percentile is "
                f"{result['distribution_quantiles']['0.99']:,}"
                "."
            ),
            (
                "Report both MAE and RMSE so large misses remain visible; "
                "retain source observations unless independently shown "
                "erroneous."
            ),
        )
    if kind.startswith("price_"):
        return (
            (
                "12,299,413 full-history price gaps remain null; 12,270,132 "
                "training gaps precede first positive sale, and 28,816 occur "
                "in histories with no training positives."
            ),
            (
                "Use only origin-available prices and explicit missingness "
                "indicators; no automatic backfill or stockout inference."
            ),
        )
    if kind == "calendar_patterns":
        ratios = result["weekday_ratios"]
        peak = max(ratios, key=lambda row: row["mean_within_week_ratio"])
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return (
            (
                f"{days[peak['weekday']]}"
                " has the highest normalised weekday ratio ("
                f"{peak['mean_within_week_ratio']:.3f}"
                "); monthly profiles also vary."
            ),
            (
                "Include weekly seasonal naive as a baseline and test "
                "origin-safe calendar effects; aggregate seasonality is not "
                "a forecast score."
            ),
        )
    if kind == "concentration":
        return (
            (
                "The top 10% of products account for "
                f"{100 * result['product_top10_percent_share']:.2f}"
                "% of training units."
            ),
            (
                "Report macro per-series and pooled metrics separately so "
                "high-volume products do not obscure minority performance."
            ),
        )
    if kind in ("zeros_variability", "volatility"):
        return (
            (
                "There are "
                f"{result['eda_zero_count']:,}"
                " zero-sale observations ("
                f"{result['eda_zero_percent']:.9f}"
                "%) in this training prefix."
            ),
            (
                "Preserve zeros and use denominator-safe metrics; changing "
                "aggregate volatility may warrant checking stability across "
                "rolling origins."
            ),
        )
    if kind == "representatives":
        return (
            (
                "The full training view reveals the single-positive M5 "
                "example; the all-zero example has no training positives."
            )
            if name == "m5"
            else "The displayed smooth example shows variation over its labelled 180-day window.",
            (
                "Keep cold-start and insufficient-history fallbacks "
                "explicit; examples do not determine population model "
                "rankings."
            ),
        )
    if kind == "events_groups":
        return (
            (
                "Christmas averages 15.6 aggregate units across five "
                "training dates; category daily rates differ after adjusting "
                "for series counts."
            ),
            (
                "Treat event/calendar signals as candidate covariates with "
                "known-at-origin rules, not causal demand lifts."
            ),
        )
    if kind == "stores":
        frame = pd.read_parquet(table_dir / "stores.parquet")
        peak = frame.loc[frame.mean_units_per_series_day.idxmax()]
        return (
            (
                "Store "
                f"{peak.store_id}"
                " has the highest training rate: "
                f"{peak.mean_units_per_series_day:.3f}"
                " units per series-day."
            ),
            (
                "Check store-level error coverage and avoid comparing raw "
                "totals with unequal exposure."
            ),
        )
    if kind == "diagnostics":
        diagnostic = result["diagnostics"]
        return (
            (
                "Aggregate weekly strength is "
                f"{diagnostic['aggregate_weekly_strength']:.3f}"
                "; annual diagnostic strength is "
                f"{diagnostic['aggregate_annual_strength_after_weekly']:.3f}"
                "."
            ),
            (
                "Use these diagnostics to motivate seasonal candidates, then "
                "judge them on matched chronological windows."
            ),
        )
    return (
        (
            "Training sales total "
            f"{result['eda_sales_units']:,}"
            " units across "
            f"{result['eda_rows']:,}"
            " observations; dates and complete-month rules are labelled."
        ),
        "Use chronological backtests and report scale-dependent errors separately by source.",
    )


def scope(record, results):
    if record["dataset"] == "both":
        return "Store Item: 2013-01-01–2017-08-13; M5: 2011-01-29–2016-01-03."
    result = results[record["dataset"]]
    plan = result["split_plan"]
    value = f"{plan['eda_start']}–{plan['eda_end']}; all {result['series']:,} series."
    if record["kind"].startswith("price_"):
        value += " Label-free price coverage additionally extends through 2016-05-22."
    return value


def contact_sheets(records, figure_dir, output):
    for batch in range(0, len(records), 6):
        canvas = Image.new("RGB", (1800, 1650), "#edf1f5")
        draw = ImageDraw.Draw(canvas)
        for position, record in enumerate(records[batch : batch + 6]):
            x, y = (position % 2) * 900, (position // 2) * 550
            with Image.open(figure_dir / f"{record['stem']}.png") as original:
                im = original.convert("RGB")
                im.thumbnail((880, 510))
                canvas.paste(im, (x + (900 - im.width) // 2, y + 30))
            draw.text((x + 12, y + 8), record["stem"], fill="#15273c")
        canvas.save(output / f"contact_sheet_{batch // 6 + 1}.png")


def write_index(records, results, directory):
    lines = [
        "# Phase 2 visualisation index",
        "",
        "29 figures / 58 files: 29 PNG and 29 SVG. All existing image files open and",
        "match verification copies rendered from the saved EDA tables. No full analysis",
        "or canonical transformation was rerun. Targeted figures were enhanced from saved tables.",
        "",
        "[Open the offline visual report](EDA_VISUAL_REVIEW.html).",
        "[Machine-readable checks](visualisation_audit.json).",
        "",
        "Paths below are relative to this index. The images depend on the neighbouring",
        "`reports/figures/phase2/` directory; keep that directory when moving the report.",
        "",
    ]
    for dataset in ("store_item", "m5", "both"):
        lines.extend(
            [
                f"## {LABELS[dataset]}",
                "",
                "| Figure | Purpose | Dataset | PNG relative path | SVG relative path |",
                "|---|---|---|---|---|",
            ]
        )
        for record in records:
            if record["dataset"] != dataset:
                continue
            stem = record["stem"]
            lines.append(
                f"| {record['title']} | {record['purpose']} | {LABELS[dataset]} | "
                f"[PNG](../figures/phase2/{stem}.png) | [SVG](../figures/phase2/{stem}.svg) |"
            )
        lines.extend(["", scope(next(r for r in records if r["dataset"] == dataset), results), ""])
    lines.extend(
        [
            "## Findings from the visual review",
            "",
            "No image files or expected PNG/SVG pairs are missing. Data bindings passed",
            "exact PNG pixel comparison and normalised SVG artist-content comparison.",
            "",
            (
                "Remaining interpretation limits are documented in the HTML; "
                "presentation defects were addressed:"
            ),
            "",
        ]
    )
    for item in review_limitations():
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Chart inputs",
            "",
            "Figures use saved Parquet tables, not newly sampled or fabricated observations.",
            "",
        ]
    )
    for record in records:
        sources = ", ".join(f"[{Path(p).stem}]({p})" for p in record["tables"])
        lines.append(f"- **{record['stem']}**: {sources}.")
    (directory / "VISUALISATION_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def review_limitations():
    return [
        (
            "ADI/CV² thresholds and aggregate seasonality are "
            "descriptive, not guarantees of individual-series "
            "forecastability."
        ),
        (
            "M5's 45 zero-CV² histories need a labelled positive display "
            "floor on a log scatter; 21 undefined histories appear in "
            "the separate classification figure."
        ),
        (
            "SNAP and event comparisons are descriptive: date "
            "composition, holidays, assortment and other confounders are "
            "uncontrolled."
        ),
        (
            "Department rates use a fixed published series universe, not "
            "independently observed assortment or stock availability; "
            "boundary heatmap months may be partial."
        ),
        (
            "Retained extreme examples are not an exhaustive tie list or "
            "proof of invalid data; only the histogram tail is a "
            "full-population distribution."
        ),
        (
            "Representative panels have independent y-scales and "
            "explicitly different windows. They are illustrations, not "
            "sampling-based population estimates."
        ),
        (
            "Historical price coverage extends through 2016-05-22 "
            "without inspecting reserved sales targets. The 465 "
            "reserved-period price gaps have no activity interpretation."
        ),
        (
            "Observed sales may be constrained demand. No measured "
            "inventory savings, causal effects, forecasting winner or "
            "direct cross-source transfer is established."
        ),
    ]


def write_html(records, results, directory):
    a, b = results["store_item"], results["m5"]
    css = """
:root{color-scheme:light;
--ink:#182b42;
--muted:#526174;
--line:#dce3eb;
--blue:#2463a0;
--orange:#a66019}

*{box-sizing:border-box}
html{scroll-behavior:smooth;
scroll-padding-top:24px}

body{margin:0;
background:#f2f5f8;
color:var(--ink);
font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}

a{color:#195c99;
text-underline-offset:3px}
a:focus-visible{outline:3px solid #ca811d;
outline-offset:3px}

.layout{max-width:1500px;
margin:auto;
display:grid;
grid-template-columns:210px minmax(0,1fr);
gap:36px;
padding:32px}

nav{position:sticky;
top:30px;
align-self:start}
nav strong{display:block;
margin-bottom:16px}
nav a{display:block;
padding:8px 0}

main{min-width:0;
max-width:1120px}
header{padding:20px 0 32px}
.eyebrow{font-size:13px;
letter-spacing:.12em;
text-transform:uppercase;
color:var(--muted)}

h1{font-size:clamp(28px,3.4vw,46px);
line-height:1.15;
max-width:850px;
margin:14px 0 18px;
letter-spacing:-.025em}

h2{font-size:29px;
margin:42px 0 16px;
line-height:1.25}
h3{font-size:21px;
line-height:1.3;
margin:0 0 10px}

p{margin:10px 0}
section{margin-bottom:28px}
.summary,.scope,.limitations{background:white;
padding:24px 28px;
border:1px solid var(--line)}

.summary h2{margin:0 0 12px;
font-size:23px}
.scope{border-left:4px solid var(--blue)}

table{width:100%;
border-collapse:collapse;
font-size:14px;
margin:18px 0}
th,td{text-align:left;
border-bottom:1px solid var(--line);
padding:12px 8px;
vertical-align:top}

th{background:#e9eff5}
td:not(:first-child){font-variant-numeric:tabular-nums}
.table-wrap{overflow:auto}

.figure-card{background:#fff;
border:1px solid var(--line);
margin:24px 0;
padding:24px;
break-inside:avoid}

.figure-card figure{margin:18px 0 0}
.figure-card img{display:block;
width:100%;
height:auto;
background:white}

.scope-label{font-size:13px;
color:var(--muted)}
.note{border-left:3px solid #c47a28;
padding:8px 14px;
background:#fff9f1;
font-size:14px}

figcaption{font-size:14px}
.file-links{display:flex;
flex-wrap:wrap;
gap:8px 20px;
margin:12px 0}

details{font-size:13px;
color:var(--muted)}
summary{cursor:pointer}
details ul{padding-left:20px}
.status{color:#355d43;
font-size:14px}

.limitations li{margin:12px 0}
footer{border-top:1px solid var(--line);
padding:24px 0;
font-size:13px;
color:var(--muted)}

@media(max-width:950px){.layout{display:block;
padding:18px}
nav{position:static;
border-bottom:1px solid var(--line);
padding-bottom:14px}
nav a{display:inline-block;
margin-right:18px;
padding:4px 0}
nav strong{margin-bottom:5px}
.figure-card{padding:16px}
.summary,.scope,.limitations{padding:18px}
h2{font-size:26px}
}

@media print{body{background:white}
.layout{display:block;
padding:0}
nav{display:none}
main{max-width:none}
.figure-card{padding:8px;
margin:14px 0}
.file-links{display:none}
h2{break-after:avoid}
.figure-card img{max-height:210mm;object-fit:contain}
.figure-card{break-inside:auto}
figure{break-inside:avoid}
}

"""
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<meta name='description' content='Offline review of all verified Phase 2 EDA figures.'>",
        "<title>Phase 2 · EDA visual review</title>",
        f"<style>{css}</style></head><body>",
        (
            "<div class='layout'><nav aria-label='Report "
            "sections'><strong>Phase 2 visual review</strong>"
        ),
        "<a href='#summary'>Executive summary</a><a href='#comparison'>Dataset comparison</a>",
        "<a href='#store-item'>Store Item · 11 figures</a><a href='#m5'>M5 · 12 figures</a>",
        (
            "<a href='#prices'>M5 prices, SNAP &amp; groups · 5</a><a "
            "href='#limitations'>Review limitations</a>"
        ),
        (
            "<a href='#methods'>Evidence &amp; methods</a><a "
            "href='VISUALISATION_INDEX.md'>Figure index</a></nav><main>"
        ),
        (
            "<header><div class='eyebrow'>Intelligent Demand Forecasting "
            "&amp; Inventory Optimisation</div>"
        ),
        "<h1>Regular seasonal sales and sparse demand require different benchmarks</h1>",
        (
            "<p>All 29 enhanced Phase 2 figures, with findings, exact "
            "coverage and interpretation notes.</p>"
        ),
        (
            "<p class='status'>29 PNG + 29 SVG files verified · data "
            "preserved · no forecasting models trained</p></header>"
        ),
        "<section id='summary' class='summary'><h2>Executive Summary</h2><ul>",
        (
            "<li>Store Item has regular sales: all "
            f"{a['series']:,}"
            " series are descriptively smooth, with one zero in its EDA "
            "period.</li>"
        ),
        (
            "<li>M5's EDA observations are "
            f"{b['eda_zero_percent']:.2f}"
            "% zero; "
            f"{b['patterns']['intermittent']:,}"
            " series are intermittent and "
            f"{b['patterns']['lumpy']:,}"
            " lumpy.</li>"
        ),
        (
            "<li>Both sources show weekday structure. Store Item has a "
            "pronounced annual monthly profile; M5 adds sparse histories and "
            "strong calendar-event contrasts.</li>"
        ),
        (
            "<li>M5 price gaps concentrate before first positive sales in "
            "training. Missing prices do not establish stock availability or "
            "known future prices.</li></ul></section>"
        ),
        "<section class='scope'><h2>Read the periods correctly</h2>",
        (
            "<p>Detailed target EDA stops before four 28-day validation "
            "windows and a final 28-day holdout. The figures cover every "
            "series, not an arbitrary sample.</p>"
        ),
        (
            "<div class='table-wrap'><table><thead><tr><th>EDA "
            "population</th><th>Store "
            "Item</th><th>M5</th></tr></thead><tbody>"
        ),
    ]
    for label, first, second in (
        ("Dates", "2013-01-01–2017-08-13", "2011-01-29–2016-01-03"),
        ("Series", f"{a['series']:,}", f"{b['series']:,}"),
        ("Observations", f"{a['eda_rows']:,}", f"{b['eda_rows']:,}"),
        ("Sales units", f"{a['eda_sales_units']:,}", f"{b['eda_sales_units']:,}"),
        (
            "Zero-sales observations",
            f"{a['eda_zero_count']:,} ({a['eda_zero_percent']:.9f}%)",
            f"{b['eda_zero_count']:,} ({b['eda_zero_percent']:.6f}%)",
        ),
    ):
        parts.append(f"<tr><th>{label}</th><td>{first}</td><td>{second}</td></tr>")
    parts.extend(
        [
            (
                "</tbody></table></div><p class='scope-label'>Full-history "
                "exceptions are known Phase 1 integrity totals and label-free "
                "price coverage. Unlabelled competition test rows are "
                "excluded.</p></section>"
            )
        ]
    )

    groups = [
        ("comparison", "Cross-dataset comparison", "both", False),
        (
            "store-item",
            "Store Item: regular sales and strong calendar structure",
            "store_item",
            False,
        ),
        ("m5", "M5: sparse histories and concentrated product volume", "m5", False),
        ("prices", "M5: historical prices and calendar associations", "m5", True),
    ]
    for anchor, title, dataset, extra in groups:
        parts.append(f"<section id='{anchor}'><h2>{title}</h2>")
        for record in records:
            if record["dataset"] != dataset or (record["kind"] in EXTRA) != extra:
                continue
            stem = record["stem"]
            result = results.get(dataset, {})
            key_finding, implication = findings(record, results, directory)
            sources = "".join(
                f"<li><a href='{escape(p)}'>{escape(p)}</a></li>" for p in record["tables"]
            )
            with Image.open(directory.parent / "figures/phase2" / f"{stem}.png") as im:
                width, height = im.size
            parts.extend(
                [
                    f"<article class='figure-card' id='{stem}' data-dataset='{dataset}'>",
                    f"<h3>{escape(record['title'])}</h3><p>{escape(record['purpose'])}</p>",
                    f"<p class='scope-label'>{escape(scope(record, results))}</p>",
                    (
                        "<p class='key-finding'><strong>Key Finding:</strong> "
                        f"{escape(key_finding)}"
                        "</p>"
                    ),
                    (
                        "<p class='implication'><strong>Forecasting "
                        "Implication:</strong> "
                        f"{escape(implication)}"
                        "</p>"
                    ),
                    (
                        "<figure><img src='../figures/phase2/"
                        f"{stem}"
                        ".png' width='"
                        f"{width}"
                        "' height='"
                        f"{height}"
                        "' alt='"
                        f"{escape(record['title'])}"
                        ": "
                        f"{escape(record['purpose'])}"
                        "' decoding='async'>"
                    ),
                    f"<figcaption><p class='note'>{escape(notes(record, result))}</p>",
                    (
                        "<div class='file-links'><a href='../figures/phase2/"
                        f"{stem}"
                        ".png'>Open PNG</a><a href='../figures/phase2/"
                        f"{stem}"
                        ".svg'>Open SVG</a><a href='#"
                        f"{stem}"
                        "'>Figure permalink</a></div>"
                    ),
                    (
                        "<details><summary>Underlying saved EDA inputs</summary><ul>"
                        f"{sources}"
                        "</ul></details></figcaption></figure></article>"
                    ),
                ]
            )
        parts.append("</section>")
    parts.extend(
        [
            (
                "<section id='limitations' class='limitations'><h2>Remaining "
                "interpretation limits</h2>"
            ),
            (
                "<p>No expected image files are missing or unreadable. The targeted "
                "presentation issues are resolved; these analytical limits remain.</p><ul>"
            ),
        ]
    )
    parts.extend(f"<li>{escape(item)}</li>" for item in review_limitations())
    parts.extend(
        [
            "</ul><h3>Training-period price-gap reconciliation</h3>",
            (
                "<div class='table-wrap'><table><thead><tr><th>Training-period "
                "missing-price "
                "relation</th><th>Observations</th></tr></thead><tbody>"
            ),
        ]
    )
    for label, key in [
        ("Before first positive", "missing_before_first_positive"),
        ("Within positive-sales span", "missing_between_first_last_positive"),
        ("After last positive", "missing_after_last_positive"),
        ("No positive in EDA", "missing_no_positive_in_eda"),
    ]:
        value = b["price_missingness"]["eda_activity_partition"][key]
        parts.append(f"<tr><th>{label}</th><td>{value:,}</td></tr>")
    parts.extend(
        [
            (
                "</tbody></table></div><p>Training missing-price total: "
                "12,298,948. Another 465 gaps occur in reserved periods: only "
                "their price coverage was examined. Whole-history total: "
                "12,299,413. No prices were imputed.</p></section>"
            ),
            "<section id='methods'><h2>Evidence, verification and next steps</h2>",
            (
                "<p>Existing images were decoded and compared with disposable "
                "chart renders from the current small EDA tables: exact PNG "
                "pixels and normalised SVG artist content. Saved counts, ratios, "
                "date limits and major marginal sums were cross-checked. This "
                "confirms the figures' bindings to saved inputs; it does not "
                "constitute a new independent raw-data audit.</p>"
            ),
            (
                "<p>Reference evidence: <a "
                "href='visualisation_audit.json'>visualisation checks</a>, <a "
                "href='validation.json'>Phase 2 reconciliation</a>, <a "
                "href='VISUALISATION_INDEX.md'>complete figure index</a>, <a "
                "href='../../docs/EDA_FINDINGS.md'>EDA findings</a>, and <a "
                "href='../../docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md'>proposed "
                "forecasting protocol</a>.</p>"
            ),
            (
                "<p>The next planned task is review of the 28-day protocol, with "
                "separate source benchmarks, origin-safe inputs and explicit "
                "metric coverage. Phase 3 has not begun. The independent Claude "
                "audit remains after Phase 4 and before Phase 5.</p>"
            ),
            (
                "<p class='scope-label'>Rebuild this review: python -m "
                "intelligent_demand.exploration.visual_review. No server, CDN, "
                "web font, external script or internet connection is needed. "
                "Move the reports/eda and reports/figures directories together; "
                "some images and all analytical tables are intentionally "
                "excluded from Git.</p></section>"
            ),
            (
                "<footer>Historical measurements: Store Item through 2017-08-13; "
                "M5 through 2016-01-03, with explicitly labelled full-history "
                "price coverage through 2016-05-22. Generated with the Data "
                "reporting and visualisation "
                "skills.</footer></main></div></body></html>"
            ),
        ]
    )
    html = "\n".join(parts)
    kpis = (
        "<div class='kpi-grid'>"
        f"<div><strong>{a['series']:,}</strong><span>Store Item series · 100% smooth</span></div>"
        f"<div><strong>{b['series']:,}</strong><span>M5 series · all included</span></div>"
        f"<div><strong>{b['eda_zero_percent']:.2f}%</strong><span>M5 training zeros</span></div>"
        "<div><strong>28 days</strong><span>Proposed horizon · no models trained</span></div></div>"
    )
    html = html.replace("<section id='summary'", kpis + "<section id='summary'", 1)
    html = html.replace(
        ".summary h2{",
        (
            ".kpi-grid{display:grid;grid-template-columns:repeat(auto-fit"
            ",minmax(180px,1fr));gap:12px;margin-bottom:24px}.kpi-grid "
            "div{background:white;border:1px solid "
            "#dce3eb;padding:18px}.kpi-grid "
            "strong{display:block;font-size:28px}.kpi-grid "
            "span{display:block;font-size:13px}.key-finding{border-left:3"
            "px solid "
            "#2463a0;padding-left:12px}.implication{font-size:14px;color:"
            "#44576e}details{overflow-wrap:anywhere}.summary h2{"
        ),
    )
    html = html.replace(
        (
            "The following presentation limits remain in the original "
            "figures; this report supplies context rather than altering "
            "them."
        ),
        "Targeted presentation issues are resolved. These analytical interpretation limits remain.",
    )
    (directory / "EDA_VISUAL_REVIEW.html").write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-figures", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    config = load_config(root / "configs/default.yaml")
    directory = config.paths["reports"] / "eda"
    figure_dir = config.paths["reports"] / "figures/phase2"
    output = config.paths["artifacts"] / "visual_review"
    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(config.paths["artifacts"] / "matplotlib_cache"))
    records = inventory()
    results = {
        name: json.loads((directory / f"{name}_results.json").read_text())
        for name in ("store_item", "m5")
    }
    actual = set(config.paths["reports"].joinpath("figures").rglob("*.png")) | set(
        config.paths["reports"].joinpath("figures").rglob("*.svg")
    )
    expected = {figure_dir / f"{r['stem']}.{ext}" for r in records for ext in ("png", "svg")}
    if not args.refresh_figures and actual != expected:
        raise ValueError(f"Missing or unexpected figures: {sorted(actual ^ expected)}")
    originals = {str(p.relative_to(root)): digest(p) for p in actual}
    input_hashes = {}
    for name, result in results.items():
        for filename, expected_hash in result["input_raw_sha256"].items():
            path = config.paths["raw"] / name / filename
            assert digest(path) == expected_hash
            input_hashes[path] = expected_hash
        path = config.paths["processed"] / name / "daily_sales.parquet"
        assert digest(path) == result["input_canonical_sha256"]
        input_hashes[path] = result["input_canonical_sha256"]
    tables = {
        str(p.relative_to(root)): digest(p) for p in directory.joinpath("tables").rglob("*.parquet")
    }
    checks = check_tables(directory, results)
    reproduce_images(config, results, output)
    if args.refresh_figures:
        backup = output / "before_enhancement"
        backup.mkdir(exist_ok=True)
        for path in actual:
            if not (backup / path.name).exists():
                shutil.copyfile(path, backup / path.name)
        for path in expected:
            shutil.copyfile(output / "figures/phase2" / path.name, path)
        originals = {str(p.relative_to(root)): digest(p) for p in expected}
    image_checks = []
    for record in records:
        stem = record["stem"]
        with Image.open(figure_dir / f"{stem}.png") as original:
            original.load()
            with Image.open(output / "figures/phase2" / f"{stem}.png") as rebuilt:
                if not np.array_equal(
                    np.asarray(original.convert("RGBA")), np.asarray(rebuilt.convert("RGBA"))
                ):
                    raise ValueError(f"PNG disagrees with its saved EDA inputs: {stem}")
            dimensions = list(original.size)
        if svg_signature(figure_dir / f"{stem}.svg") != svg_signature(
            output / "figures/phase2" / f"{stem}.svg"
        ):
            raise ValueError(f"SVG artist content disagrees with its saved inputs: {stem}")
        image_checks.append(
            {
                **record,
                "png_dimensions": dimensions,
                "png_pixel_match": True,
                "svg_artist_match": True,
                "png_sha256": originals[str((figure_dir / f"{stem}.png").relative_to(root))],
                "svg_sha256": originals[str((figure_dir / f"{stem}.svg").relative_to(root))],
            }
        )
    contact_sheets(records, figure_dir, output)
    write_index(records, results, directory)
    write_html(records, results, directory)
    assert originals == {p: digest(root / p) for p in originals}
    assert tables == {p: digest(root / p) for p in tables}
    assert input_hashes == {p: digest(p) for p in input_hashes}
    report = {
        "status": "passed_with_presentation_notes",
        "reviewed_at_utc": datetime.now(UTC).isoformat(),
        "figure_count": len(records),
        "image_file_count": len(expected),
        "table_checks": checks,
        "saved_tables_unchanged": True,
        "raw_and_canonical_hashes_unchanged": True,
        "saved_tables_sha256": tables,
        "figures_refreshed_from_saved_tables": args.refresh_figures,
        "renderer_sha256": {p.name: digest(p) for p in Path(__file__).parent.glob("*.py")},
        "full_analysis_or_transformation_rerun": False,
        "models_trained": 0,
        "limitations": review_limitations(),
        "images": image_checks,
    }
    (directory / "visualisation_audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "images"}, indent=2))


if __name__ == "__main__":
    main()
