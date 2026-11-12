# Phase 7 quality gates

Deterministic, machine-readable gates in the style of Phase 6 (`configs/webapp_qa.yaml`, runner
`python -m intelligent_demand.bi.webapp_qa` for data gates; `pytest` for engine gates; Playwright for UI and
live gates). Each rule records id, layer, description, expected, actual, tolerance, severity, status
(PASS, WARNING, FAIL, ERROR) and evidence. Any CRITICAL FAIL or ERROR blocks the milestone.

## Data gates (D), run on the laptop after every export

| ID | Severity | Rule |
|---|---|---|
| D-01 | CRITICAL | Every exported CSV matches the manifest row count and SHA-256; source evidence hashes (plan, execution, selection, ledger, Phase 6 manifest) unchanged |
| D-02 | CRITICAL | `validation_actuals` and `forecasts` for the 506 Phase 6 detail series equal `FactForecastSeriesDaily` exactly |
| D-03 | CRITICAL | No `series_history` or `validation_actuals` date is on or after `test_start` for its dataset; every validation date lies in its origin window; history ends on the origin date |
| D-04 | CRITICAL | `forecast_metrics_aggregate` reproduces the 24 registry pooled MAE, RMSE, WAPE and bias values and the two leaderboard primary scores (rtol 1e-9) |
| D-05 | CRITICAL | Business keys unique; all foreign keys resolve; curated set equals the predeclared manifest (counts per stratum, six representatives included) |
| D-06 | HIGH | `inventory_series_base` equals the Phase 5 per-case Parquet for curated series (rtol 1e-9); `series_origin_mean56` equals the Phase 5 `historical_mean56` |
| D-07 | CRITICAL | After seeding, Postgres row counts equal the manifest; `provenance.export_version` matches |

## Simulation gates (S), `packages/inventory_core` tests on Python 3.12

| ID | Severity | Rule |
|---|---|---|
| S-01 | CRITICAL | `engine.py` and `design.py` copies hash-identical to the originals in `src/intelligent_demand/inventory/` |
| S-02 | CRITICAL | Parity: 6 representatives x 2 datasets x 17 scenarios x 4 policies replayed through `run_planner` equal the saved Phase 5 summaries (rtol 1e-9, every field) |
| S-03 | CRITICAL | Conservation: for every run, opening + receipts − fulfilled = closing daily; initial + received − fulfilled = final; placed − received = final pipeline |
| S-04 | CRITICAL | Cost reconciliation: holding + shortage + ordering + terminal = total; components equal rate x quantity |
| S-05 | HIGH | Determinism: identical inputs give byte-identical JSON; policies share the same demand path |
| S-06 | HIGH | Lead-time behaviour: an order on day t is received on day t+L+1; no order whose protection period exceeds the horizon |
| S-07 | CRITICAL | No future demand visibility: a mutation test that perturbs demand after day t does not change any order placed on or before day t |
| S-08 | HIGH | Bounds: every out-of-range parameter is rejected by Pydantic and by `Scenario` validation; protection > 28 rejected |

## API gates (A), contract tests against the local stack

| ID | Severity | Rule |
|---|---|---|
| A-01 | CRITICAL | Every endpoint response validates against its zod/OpenAPI schema |
| A-02 | CRITICAL | Invalid inputs return 400 with field messages; unknown keys 404; oversized bodies 413; no stack traces or file paths in any error |
| A-03 | CRITICAL | Dataset/model/origin compatibility: a model key from another dataset is rejected |
| A-04 | HIGH | `meta.evidence` is `validation` on all analysis endpoints and `reported_final_holdout` only on the research rows |
| A-05 | CRITICAL | RLS: anon key cannot insert/update/delete on `app.*`; cannot read `planner.*` rows of another user |
| A-06 | HIGH | Bounded queries: `limit` caps enforced; pagination stable; `q` length capped |
| A-07 | HIGH | Rate limit triggers at the configured thresholds and returns 429 with `Retry-After` |
| A-08 | CRITICAL | `POST /api/planner/simulate` for a frozen-scenario request equals the Phase 5 saved result for that series (rtol 1e-9) and populates `studyReference` |

## UI gates (U), Playwright plus axe

| ID | Severity | Rule |
|---|---|---|
| U-01 | CRITICAL | Each page renders its primary visual with the expected values for a fixed fixture series (data binding) |
| U-02 | HIGH | Navigation between the five pages works; the selected series carries from Explorer to Planner |
| U-03 | HIGH | Filters and model comparison controls change the displayed values as expected |
| U-04 | HIGH | Loading, empty and error states appear for simulated slow, empty and failing responses |
| U-05 | CRITICAL | Copy scan: no "savings", "profit", "ROI" or "optimal" in rendered text; every NCU value has the hypothetical label; fixed ROP labelled as low-stock comparator. *Clarified in Phase 7C:* the mandatory negated caveat "not (realised) (financial) savings" (API `ncuNotice`, limitation L1) is the only approved form; any other occurrence fails. Implemented in `apps/web/tests/copy-gate.mjs` |
| U-06 | HIGH | Responsive snapshots at 1280, 1024 and 390 px without horizontal overflow; axe has no serious or critical violations |
| U-07 | MEDIUM | PNG and CSV exports download with correct content |

## Deployment gates (P), against the live URLs

| ID | Severity | Rule |
|---|---|---|
| P-01 | CRITICAL | Production builds of both projects succeed; engine function bundle under 500 MB |
| P-02 | CRITICAL | Environment variables present per environment; no secret appears in the built client bundle |
| P-03 | CRITICAL | Live database row counts equal the manifest; `provenance.export_version` matches the deployed web `meta.exportVersion` |
| P-04 | CRITICAL | `/api/health` on both projects returns 200 with matching versions |
| P-05 | CRITICAL | Live planner run for the fixture series equals the local parity fixture |
| P-06 | CRITICAL | RLS negative test against the live database with the anon key fails as expected |
| P-07 | HIGH | Browser smoke test of the five critical flows passes on the live URL |
| P-08 | HIGH | Mobile viewport check on the live URL |
| P-09 | HIGH | Rate limit observed live |
| P-10 | MEDIUM | Cold-start latency of the engine measured and recorded |
| P-11 | HIGH | Deployment record written with URLs, versions, observed costs and any item left NOT VERIFIED |

A verified live URL with gates P-01 to P-07 green is the definition of a successful deployment; a build
success alone is not.
