# Phase 6 Power BI analytics dashboard

Editable Power BI Project: `powerbi/IntelligentDemand.pbip` (PBIR report + TMDL semantic model).
Built 2026-11-10 on Power BI Desktop 2.159.1231.0 (October 2026) with pbi-cli 3.12.0.

The dashboard reports existing, verified Phase 3-5 evidence. It adds no new forecasts, models,
simulations or final-holdout analysis. Inventory figures are hypothetical normalised cost units (NCU),
never realised savings.

Related generated references: [data dictionary and lineage](PHASE6_DATA_DICTIONARY.md),
[DAX measure catalogue](PHASE6_DAX_MEASURE_CATALOGUE.md), [QA results](PHASE6_QA_RESULTS.md),
[Phase 7 handoff](PHASE7_INTEGRATION_HANDOFF.md).

## 1. Architecture (metadata-driven)

| Layer | Artefact | Role |
|---|---|---|
| Data contract | `configs/powerbi.yaml` | Labels, descriptions, limitations, detail-series scope |
| Validated data foundation | `src/intelligent_demand/bi/export.py` | Reads saved evidence through hash-checked adapters; writes 18 CSVs and `reports/powerbi/data_manifest.json` |
| Power Query | `expressions.tmdl` | `DataRoot` parameter and one shared `LoadReportingTable` function: explicit schema, early projection, empty text to null, en-US typing |
| Semantic model | `configs/powerbi_model.yaml` -> `bi/tmdl.py` -> `powerbi/IntelligentDemand.SemanticModel/` | Star schema, 28 single-direction many-to-one relationships, 69 measures |
| Report UX | `configs/powerbi_report.yaml` -> `bi/report_builder.py` -> `powerbi/IntelligentDemand.Report/` | Five pages, 86 visuals, built with pbi-cli; theme `powerbi/theme/IntelligentDemandAcademic.json` |
| QA | `configs/powerbi_qa.yaml` -> `bi/qa.py` -> `reports/powerbi/qa_results.json` | 43 deterministic rules across five layers |
| Documentation | `bi/docs.py` | Data dictionary, measure catalogue and QA results generated from the same metadata |

Model grain is controlled so the model stays small on a 16 GB laptop: the largest facts are
series x origin x model (371,880 rows) and base-scenario series x origin x policy (495,840 rows).
The 59 million canonical M5 rows and 13.9 million simulation events are not loaded; daily detail is
pre-aggregated by demand pattern, and series-level daily lines cover all Store Item series plus the six
predeclared M5 representatives only.

## 2. KPI specifications

| KPI | Definition | Aggregation rule |
|---|---|---|
| MAE | sum of absolute errors / observations | Pooled additive components; equals the Phase 4 four-origin macro MAE because every series has 28 observations per origin |
| RMSE | sqrt(sum of squared errors / observations) | Pooled |
| WAPE | sum of absolute errors / sum of actual | Pooled; blank when actual demand is zero |
| Bias | sum of (forecast - actual) / observations | Pooled; positive means over-forecasting |
| Macro MASE, Macro RMSSE | per-series MAE (RMSE) over the lag-7 training scale, averaged per origin, then over origins | Origin-bounded training scale; undefined (zero) scales excluded |
| Mean cost per episode (NCU) | total simulated cost / series-episodes | Requires one dataset, scenario and policy |
| Fill rate | fulfilled units / demanded units | Pooled units, not an average of series rates |
| Stockout days, average on-hand, orders | per series-episode | Additive numerators over series-episodes |
| ML vs MA28 / Seasonal Naive cost difference | selected-ML minus baseline mean cost, absolute and % | Policy filter replaced explicitly; hypothetical NCU |
| Scenario / origin counts | scenarios (origins pooled) or origins where ML is cheaper | Descriptive counts, not independent confirmations |

No targets, thresholds or traffic-light statuses are defined, because the evidence supplies none.

## 3. Report pages

| Page | Purpose and content |
|---|---|
| Executive Overview | Per-dataset KPI rows (coverage, validation MAE, MAE change vs MA28 and Seasonal Naive, simulated cost difference vs both baselines); per-origin cost-difference chart showing the Store Item reversal at origin 4; policy cost and service matrix; evidence-based conclusions; base scenario page filter |
| Forecasting Performance | Dataset, origin and pattern slicers; MAE, Macro MASE cards for all three models; model accuracy matrix (MAE, RMSE, WAPE, Bias, MASE, RMSSE, coverage); MAE by origin; actual vs saved fixed-origin forecasts; MAE by demand pattern. Validation origins only |
| Inventory Optimisation | Base scenario. Mean cost cards for all four policies (Fixed ROP labelled a low-stock comparator); ML differences vs MA28 and Seasonal Naive; full policy detail matrix; cost components; per-origin differences; fill-rate vs cost scatter |
| Scenario & Sensitivity | 17 scenarios; scenario counts with the non-independence caveat; scenario x policy cost matrix; ML difference by scenario; scenario x origin matrix exposing origin-level variability |
| Model Explorer & Governance | Series slicer (detail series only); actual vs saved forecasts per series; Phase 4 trials; saved final-holdout results labelled "reported, not a new evaluation"; verification receipts; audit findings; limitations; methodology and rebuild commands |

Common framework on every page: title, subtitle, page navigator, Dataset slicer (single-select,
default Store Item, synced across pages), KPI row, analysis visuals, and a scientific-caveat footer.
Measures return BLANK rather than mixing datasets, model roles, scenarios or policies, so incompatible
filter combinations show empty values instead of fabricated pooled numbers. Not implemented: drill-through
and report-tooltip pages (no material benefit over the governance page for this scope).

## 4. Setup and refresh

1. Build the reporting data (reads only saved evidence; about 3 minutes):
   `.venv\Scripts\python.exe -m intelligent_demand.bi.export`
2. Optional, only after editing the specs: regenerate the model and report:
   `python -m intelligent_demand.bi.tmdl` then `python -m intelligent_demand.bi.report_builder`
   (the report builder rebuilds every page and overwrites manual Desktop layout edits).
3. Open `powerbi/IntelligentDemand.pbip` in Power BI Desktop and choose Refresh. Desktop reads TMDL and
   PBIR only when a file is opened.
4. Moving the project: change the `DataRoot` parameter (Transform data > Manage parameters) to the new
   `artifacts\powerbi\data\` folder, or regenerate with `python -m intelligent_demand.bi.tmdl --data-root <path>`.
5. QA with Desktop open: `python -m intelligent_demand.bi.qa` (layers A-E), then
   `python -m intelligent_demand.bi.docs`. Layers C and D need the open Desktop model (`pbi connect`).

Git stores the PBIP definition, specs, generators and small manifests. The CSVs, Desktop cache
(`.pbi/cache.abf`) and local settings stay local (`*.csv`, `artifacts/**`, `powerbi/.gitignore`).

## 5. Verification evidence

| Check | Result |
|---|---|
| Deterministic QA (43 rules, layers A-E) | PASS: 42 pass, 1 warning, 0 fail, 0 error |
| Source to reporting reconciliation | All 24 validation runs match registry MAE, RMSE, WAPE, bias, MASE, RMSSE (max relative difference 2e-15); all 544 inventory cases match the Phase 5 audit summary |
| Live DAX vs saved evidence | 24 runs x 6 metrics, leaderboard metrics, 544 cases x 7 measures, headline, per-origin differences, 17/17, 3/17, 16/17 scenario counts, paired series counts: all equal within 1e-9 |
| Desktop open and refresh | PBIP opens; all 19 tables refresh with zero failures |
| Desktop rendering | Each of the five pages was opened with live data and inspected from a window capture of Desktop; every visual renders and the displayed values match the reconciled figures |
| Warning E06 | After the owner's Desktop saves, the auto-sized caveat footers on the four 720 px pages extend about 0.4 px beyond the canvas. Cosmetic; kept as the owner's edit (the builder now uses a 47 px footer inside the canvas for future rebuilds) |

Desktop rendering is a documented inspection, not an automated assertion; interaction behaviour (cross-
filtering clicks, slicer changes, page-navigator clicks) was not exercised automatically.

Two pbi-cli 3.12 defects were found and corrected in the builder: custom themes were registered with the
legacy numeric resource type 202 (Desktop then fails with "Failed to load the report"; PBIR needs
`"CustomTheme"`), and chart legends were written to a `Legend` role that Power BI ignores (charts render
empty; the role is `Series`). Root causes were isolated by bisection on isolated copies of the report.

## 6. Scientific limitations carried by the dashboard

All eight declared limitations are loaded as `DimLimitation` and shown on the governance page; every page
footer repeats the core caveat. In summary: NCU are hypothetical, not savings; accuracy does not guarantee
inventory outcomes; the Store Item ML advantage over MA28 reverses at origin 4 and is only -1.10% against
Seasonal Naive; the 17 scenarios reuse four origins; Fixed ROP is a low-stock comparator; ML was tuned on the
same validation windows; M5 sparse-demand performance differs by segment; and no real inventory transactions
or costs exist. Saved final-holdout metrics are reported values only.

## 7. Completion checklist

| Item | Status |
|---|---|
| Editable PBIP (TMDL + PBIR) | Done |
| Theme JSON | Done |
| Modular Power Query with configurable data root | Done |
| Star-schema model, hidden keys, folders, formats, sort orders, date table | Done (QA C01-C05) |
| Reusable documented DAX measures | Done: 69 measures (QA C03, D01-D08) |
| Five report pages with navigation, synced slicers, page filters, dynamic titles, caveats | Done (QA E01-E07) |
| Automated validation and reconciliation | Done (`reports/powerbi/qa_results.json`) |
| Data dictionary, measure catalogue, lineage diagram, page documentation, setup guide | Done |
| Desktop open, refresh, DAX execution and page rendering | Verified |
| Automated interaction testing, drill-through and tooltip pages | Not done (see section 5 and 3) |
| Off-device backup of evidence (inherited audit F-02) | Still open before academic submission |
| Git checkpoint | Not created; awaiting owner approval |
