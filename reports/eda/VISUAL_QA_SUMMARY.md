# Phase 2 final visual QA

The enhanced report contains **29 figures, exported as 29 PNG and 29 SVG files**.
All render from the existing 39 validated analytical tables. The original Phase 2
checkpoint and analytical manifests are preserved. No forecasting model is trained.

## Resolved presentation issues

| Area | Enhancement |
|---|---|
| Store Item CV | Linear decimal ticks replace crowded scientific notation |
| Store Item zeros | Exact 1/843,000 count and percentage, store/item/date annotation; daily zero breadth uses counts |
| Store Item ADI/CV² | Positive-size variability histogram and all-smooth population facts replace redundant empty classes |
| M5 demand patterns | Separate scatter and log-position class-count figure; all six classes have exact counts/shares |
| M5 price gaps | Exact counts and percentages retain visibility of small/zero categories; full-history price-only scope is explicit |
| Representative histories | Zero/single-positive examples use full training histories; positive day labelled; axes start at zero |
| Calendar/group labels | Human-readable event names, exact small-value labels and category series exposures |
| Temporal axes | First and last dates included without crowded neighbouring annual ticks |
| Cross-dataset comparison | Explicit percentage units and numeric labels; source populations remain separate |
| HTML | Executive KPIs, navigation, 29 consistent cards, Key Finding and Forecasting Implication for each, responsive/print CSS |

## Five added figures

- [M5 classifications](../figures/phase2/m5_classification.png): counts and shares of all 30,490 series.
- [M5 SNAP](../figures/phase2/m5_snap.png): mean units per observed store-day within state and flag; actual exposures shown.
- [M5 departments](../figures/phase2/m5_departments.png): units per published department series/day, including a monthly daily-rate heatmap.
- [Store Item extremes](../figures/phase2/store_item_extremes.png): empirical tail over all 843,000 training observations and ten retained examples.
- [M5 extremes](../figures/phase2/m5_extremes.png): empirical tail over all 54,912,490 training observations and ten retained examples.

Every figure has an adjacent SVG export, listed in [VISUALISATION_INDEX.md](VISUALISATION_INDEX.md).

## Numerical and scope checks

Source findings remain Store Item 843,000 training rows / 43,666,945 units / one zero,
and M5 54,912,490 / 61,066,490 / 37,800,354 zeros. Full-history reference totals and
all existing source/canonical hashes remain unchanged. All 39 table hashes are checked
before and after figure production. Saved date-bearing target summaries are bounded
by 2017-08-13 (Store Item) and 2016-01-03 (M5). Only explicitly labelled price-quality
tables extend beyond those dates; reserved sales targets are never accessed.

Department totals reconcile by date to aggregate daily sales. SNAP mean × store-days
reconciles to total M5 training units; state exposures equal number of state stores ×
1,801 days. Marginal price gaps reconcile to 12,299,413; training activity counts sum
to 12,298,948, with the 465 reserved-period gaps left uninterpreted. Extreme maxima
match the histogram and results JSON: 231 Store Item units and 763 M5 units.

PNG pixels and normalised SVG artist content are checked against disposable renders
from saved tables. This checks the displayed bindings; it is not a new raw-data audit.
See [visualisation_audit.json](visualisation_audit.json) for current source/table/image
hashes and final browser verification. Original visual exports are retained locally
under ignored `artifacts/visual_review/before_enhancement/` for comparison.

## Remaining interpretation limits

- SNAP/event comparisons have uncontrolled calendar, assortment and other confounders.
- Department exposure is the fixed published series universe, not observed availability.
- Extreme examples come from the retained top-20 table; ties are not exhaustive.
- Representative panels have explicitly different windows and independent y-scales.
- Undefined ADI/CV² cases remain separate; zero CV² uses a labelled log display floor.
- Aggregate seasonality is diagnostic; a fixed 365-day period approximates leap dates.
- Historical price gaps do not establish stockouts or known future prices.
- No forecasting winner, direct transfer or measured inventory benefit is claimed.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand.exploration.visual_review --refresh-figures
```

The report works from local relative paths without a web server, CDN, web fonts or
external scripts. Keep `reports/eda/` and `reports/figures/` together. Five representative
figure pairs are retained in Git; the other images and all Parquet summaries remain
local and ignored. Final automated and browser results are recorded in the audit JSON.

## Final verification results

- Ruff passed; **85 Pytest tests passed**; pip check found no broken requirements.
- Three added tests cover department exposure, exact histogram tails and catalogue completeness.
- Chrome loaded all 29 report images and all 58 native PNG/SVG images with networking disabled.
- All 29 cards have a Key Finding and Forecasting Implication; four executive KPIs are present.
- All relative links and section anchors resolve; no external requests occurred.
- Desktop (1440 px), narrow/mobile (480 px) and print-style checks passed without page overflow.
- No full EDA scan, transformation, reserved-target analysis or forecasting training was run.
