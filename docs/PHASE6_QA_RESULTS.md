# Phase 6 dashboard QA results

Generated from `reports/powerbi/qa_results.json` (`python -m intelligent_demand.bi.qa`). PASS/FAIL
comes from the deterministic rules in `configs/powerbi_qa.yaml`, not from interpretation.

Overall: **PASS**. Rules 43: 42 pass, 1 warning, 0 fail, 0 error.

Layers: A source evidence, B reporting data, C semantic model (live engine), D DAX business logic
(live engine vs saved scientific evidence), E report definition.

| Rule | Layer | Severity | Status | Description | Actual | Tolerance |
|---|---|---|---|---|---|---|
| A01 | A | CRITICAL | PASS | Frozen Phase 5 plan self-hash and design files are unchanged | 63efc59ed0dc2b35b2ad3067fb790c0b42d0c1f279e3f8142519b78c07cce76e |  |
| A02 | A | CRITICAL | PASS | Phase 4 frozen model-selection fingerprint reproduces | a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb |  |
| A03 | A | CRITICAL | PASS | Holdout access ledger file hash unchanged, 12 events | fa2af529b50299b50c8d77d67b0ce70f73fab35e4731a5b825dd27a20e4bc204 (12 events) |  |
| A04 | A | CRITICAL | PASS | All 544 inventory cases completed with authenticated per-series outputs | 544 |  |
| A05 | A | CRITICAL | PASS | Every reporting CSV matches the row count and SHA-256 recorded in the data manifest | 18 tables match |  |
| A06 | A | CRITICAL | PASS | Every dated reporting row lies inside an approved validation window and before the final-holdout start | 0 rows outside approved validation windows |  |
| A07 | A | HIGH | PASS | Phase 5 forecast sources contain zero fallback observations | 0 |  |
| B01 | B | CRITICAL | PASS | Declared business keys are unique in every reporting table | all keys unique |  |
| B02 | B | CRITICAL | PASS | Every fact foreign key exists in its dimension | 28 relationships, no orphan keys |  |
| B03 | B | CRITICAL | PASS | Series-origin forecast fact covers every series x 4 origins x 3 model roles | 371880 rows (expected 371880) |  |
| B04 | B | CRITICAL | PASS | Per-run pooled MAE equals the saved registry metrics (24 validation runs) | 24 runs; max relative difference 2.15e-16 | {"rtol": 1e-09} |
| B05 | B | CRITICAL | PASS | Per-run pooled RMSE equals the saved registry metrics | 24 runs; max relative difference 1.12e-16 | {"rtol": 1e-09} |
| B06 | B | CRITICAL | PASS | Per-run pooled WAPE equals the saved registry metrics | 24 runs; max relative difference 2.16e-16 | {"rtol": 1e-09} |
| B07 | B | HIGH | PASS | Per-run pooled bias equals the saved registry metrics | 24 runs; max relative difference 2.32e-15 | {"rtol": 1e-09} |
| B08 | B | HIGH | PASS | Per-run macro MASE (defined series only) equals the saved registry metrics | 24 runs; max relative difference 0.00e+00 | {"rtol": 1e-06} |
| B09 | B | HIGH | PASS | Per-run macro RMSSE (defined series only) equals the saved registry metrics | 24 runs; max relative difference 1.96e-16 | {"rtol": 1e-06} |
| B10 | B | CRITICAL | PASS | Four-origin macro MAE of each selected model equals the Phase 4 leaderboard primary score | [np.float64(6.308039821969917), np.float64(1.0200669850841517)] vs [6.308039821969917, 1.0200669850841517] | {"rtol": 1e-09} |
| B11 | B | HIGH | PASS | Daily pattern-level forecast fact sums equal the series-origin fact (no double counting) | 24 origin-model groups compared | {"rtol": 1e-09} |
| B12 | B | CRITICAL | PASS | Every inventory case total equals the saved Phase 5 independent audit summary (544 cases) | 544 cases x 11 measures | {"rtol": 1e-09} |
| B13 | B | HIGH | PASS | Base-scenario series-level inventory fact sums equal the case-level fact | 112 groups | {"rtol": 1e-09} |
| B14 | B | CRITICAL | PASS | Base pooled mean cost and fill rate equal the post-audit reconciliation | 8 dataset-policy pairs | {"rtol": 1e-09} |
| B15 | B | HIGH | PASS | Additive fact columns have no missing values; only undefined MASE/RMSSE scales may be empty | no unexpected gaps; 78 undefined MASE scales kept empty |  |
| B16 | B | CRITICAL | PASS | 17 scenarios x 4 policies x 8 origins present in the scenario fact | 544 cases |  |
| C01 | C | CRITICAL | PASS | Every model table row count after refresh equals the reporting-data manifest | 18 tables match manifest |  |
| C02 | C | CRITICAL | PASS | Exactly the 28 declared relationships exist, all many-to-one, single direction and active | 28 relationships; missing []; extra []; cardinality/direction ok=True |  |
| C03 | C | CRITICAL | PASS | All declared measures exist in the engine with no error state | 69 measures; errors []; missing [] |  |
| C04 | C | MEDIUM | PASS | All key columns and fact columns are hidden; dimension attributes stay visible | 0 visible key/fact columns: [] |  |
| C05 | C | MEDIUM | PASS | DimDate is a Time-category table keyed on a unique Date column | category Time; rows 731 distinct 731 |  |
| D01 | D | CRITICAL | PASS | DAX MAE, RMSE, WAPE, Bias, Macro MASE and Macro RMSSE per origin and model equal the saved registry metrics (24 runs) | 24 origin-model rows x 6 metrics; max relative difference 9.95e-15 | {"rtol": 1e-09} |
| D02 | D | CRITICAL | PASS | DAX four-origin metrics of each selected model equal the Phase 4 leaderboard | 2 datasets x 6 metrics; DAX MAE [6.308039821969918, 1.0200669850841513] | {"rtol": 1e-09} |
| D03 | D | CRITICAL | PASS | DAX mean cost, fill rate, cost components, stockout days and on-hand per case equal the Phase 5 audit summary (544 cases) | 544 cases x 7 measures | {"rtol": 1e-09} |
| D04 | D | CRITICAL | PASS | DAX base pooled mean cost, fill, cost per demanded unit and on-hand per dataset and policy equal the post-audit reconciliation | 8 dataset-policy rows x 5 | {"rtol": 1e-09} |
| D05 | D | CRITICAL | PASS | DAX ML vs MA28 and ML vs Seasonal Naive cost differences (pooled and per origin) equal the post-audit reconciliation | 24 values; Store Item ML-MA28 per origin [-915.78, -598.09, -375.92, 385.21] | {"rtol": 1e-09} |
| D06 | D | CRITICAL | PASS | DAX scenario and origin counts where ML is cheaper equal the post-audit reconciliation (17/17, 3/17, 16/17, 17/17) | DAX [17, 16, 3, 3, 17, 0] vs reference [17, 16, 3, 3, 17, 0] |  |
| D07 | D | HIGH | PASS | DAX base series-origin pairs where ML is cheaper or costlier than MA28 equal the Phase 5 paired audit counts | 8 origins; DAX [499, 1, 499, 1]... vs [499, 1, 499, 1]... |  |
| D08 | D | HIGH | PASS | Measures return BLANK when datasets, model roles or scenarios would be mixed | mixed contexts blank=[True, True, True]; valid context value=223.8198917677927 |  |
| E01 | E | CRITICAL | PASS | pbi-cli PBIR validation reports a valid report with no errors | valid=True errors=[] files=94 |  |
| E02 | E | CRITICAL | PASS | Five pages in the declared order, Executive Overview active, each with page navigator and visible scientific caveat | 5 pages; navigator and caveat on every page |  |
| E03 | E | CRITICAL | PASS | Every visual and filter field reference resolves to a model column or measure | 146 field references resolve |  |
| E04 | E | CRITICAL | PASS | Custom theme is registered as a CustomTheme resource and the theme file parses | customTheme=IntelligentDemandAcademic.json items=[{'name': 'IntelligentDemandAcademic.json', 'path': 'IntelligentDemandAcademic.json', 'type |  |
| E05 | E | HIGH | PASS | No unsupported Legend roles; Dataset slicers are single-select, default Store Item and share one sync group | no Legend roles; 4 dataset slicers synced |  |
| E06 | E | MEDIUM | WARNING | 86 visuals, all inside their page canvas | 86 visuals; outside canvas ['executive_overview/ftr_caveat', 'forecasting_performance/ftr_caveat', 'inventory_optimisation/ftr_caveat', 'sce |  |
| E07 | E | CRITICAL | PASS | No report text calls simulated cost differences savings except to deny it | every mention of savings is a denial |  |
