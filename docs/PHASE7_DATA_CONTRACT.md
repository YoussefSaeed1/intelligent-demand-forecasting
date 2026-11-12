# Phase 7A: application data contract

> **Amended by Phase 7B (2026-11-12):** the implementation refines this design (no browser database access, dedicated least-privilege roles instead of the service-role key, Postgres-backed rate limiting, `/api/v1` routes, measured 137 MB footprint). See [PHASE7B_BACKEND_RESULTS.md](PHASE7B_BACKEND_RESULTS.md) section 3.

Defines the five data domains, what the application may ship, the curated demo budget, and the exports that
Phase 7B must build. Nothing here changes scientific evidence; all exports are read-only derivations.

## 1. Data domains

| Domain | Examples | Location | Mutability | Shipped to the app |
|---|---|---|---|---|
| 1. Immutable scientific evidence | canonical Parquet, registry predictions, frozen selection, ledger, Phase 5 case outputs, Phase 6 CSVs and manifest | Owner laptop + same-device backups | Never (hash-bound) | No. Only derived curated tables and hashes |
| 2. Curated public demonstration data | series metadata, pre-origin history, validation actuals, saved forecasts, metrics, scenario study results | Supabase schema `app` | Replaced wholesale by a versioned re-export; never edited in place | Yes, read-only |
| 3. Application configuration and metadata | labels, descriptions, limitations, audit findings, provenance hashes, export version | Supabase schema `app` + repository config | Versioned with the export | Yes |
| 4. User-created hypothetical scenarios | parameter sets, names | Supabase schema `planner` (post-MVP) | Owner-editable | Yes, per owner |
| 5. Temporary simulation outputs | planner run results | Response payload (MVP); `planner.runs` with 30-day retention (post-MVP) | Ephemeral | Per request or owner |

Rule: application users can read domains 2 and 3 and write only domain 4 (their own rows). Domain 1 is never
reachable from any deployed component.

## 2. Validation-only boundary

Every dated row shipped to the app lies in one of two windows per validation origin: the pre-origin history
window (training side) or the 28-day validation window. For each dataset the final 28-day holdout window
(Store Item 2017-12-04 to 2017-12-31; M5 2016-04-25 to 2016-05-22) is excluded by construction and asserted by
QA gate D-03. Saved final-holdout metrics appear only as the eight reported rows already in
`FactFinalHoldoutReported`, labelled as reported values.

## 3. Curated series budget

| Dataset | Population | Curated series | Selection rule |
|---|---|---|---|
| Store Item | 500 | 500 (all) | None needed |
| M5 | 30,490 | 300 | Deterministic stratified sample by training-prefix demand pattern, seed 42, drawn from `DimSeries` before any result is consulted: all_zero 10, insufficient_positive_history 5, erratic 40, intermittent 150, lumpy 60, smooth 35; the six Phase 5 representatives are force-included and replace sampled members of their stratum |

The curated M5 set is for exploration and planning only. Every population-level statement in the app comes
from full-population precomputed aggregates, never from the curated subset. The UI labels M5 series lists as
"300 curated of 30,490".

## 4. Export specification (Phase 7B, `bi/webapp_export.py`)

All exports are CSV plus a JSON manifest with row counts and SHA-256, produced the same way as the Phase 6
manifest, and loaded into Supabase by a seed script. Sources are hash-verified before reading.

| Export | Grain | Rows (estimate) | Source | Notes |
|---|---|---|---|---|
| `series_curated` | series | 800 | `DimSeries` + manifest | adds `is_curated`, `curation_stratum` |
| `series_history` | series x origin x date | 800 x 4 x 84 = 268,800 | canonical `daily_sales.parquet`, dates `origin-83 .. origin` | training side only; stops at the origin |
| `validation_actuals` | series x origin x date | 800 x 4 x 28 = 89,600 | Phase 5 adapter `load_cohort` (rejects non-validation windows) | identical to the demand paths used in Phase 5 |
| `forecasts` | series x origin x model x horizon day | 800 x 4 x 3 x 28 = 268,800 | registry predictions via the Phase 5 plan sources | fixed-origin, not daily refreshed |
| `series_origin_mean56` | series x origin | 3,200 | Phase 5 per-series Parquet `historical_mean56` | engine input; copied, not recomputed |
| `forecast_metrics_series` | series x origin x model | 9,600 | `FactForecastSeriesOrigin` filtered to curated | additive components + MASE/RMSSE scales |
| `forecast_metrics_aggregate` | dataset x origin x model x pattern (+ "all" pattern) | about 170 | `FactForecastSeriesOrigin`, full population | sums only; ratios computed by the API |
| `inventory_scenario_results` | origin x scenario x policy x pattern | 1,904 | `FactInventoryScenarioResults` | full population |
| `inventory_series_base` | series x origin x policy | 12,800 | `FactInventorySeriesBase` filtered to curated | planner "compare with the study" and parity |
| reference tables | as Phase 6 | small | `Dim*`, `FactModelSelectionTrials`, `FactFinalHoldoutReported`, `DimLimitation`, `DimAuditFinding` | copied |
| `provenance` | 1 | 1 | plan, execution, selection, ledger, Phase 6 manifest hashes; export version; git SHA | shown on the Research page |

Estimated curated footprint: about 650,000 rows, roughly 60 to 90 MB in Postgres with indexes, well inside the
Supabase Free 500 MB database limit.

## 5. Key and naming conventions

Keys are the Phase 6 keys unchanged: `dataset_key` (`store_item`, `m5`), `origin_key` (`dataset|fold`),
`model_key` (`dataset|role`), `series_key` (`dataset|series_id`), `policy_key`, `scenario_key`, `pattern_key`.
Column names are snake_case in Postgres and camelCase in JSON responses. Dates are ISO `YYYY-MM-DD`.
Monetary-looking values are always labelled NCU in field names (`mean_cost_ncu`).

## 6. Reconciliation requirements (enforced by gates D-01 to D-06)

- Every exported table matches its manifest hash and row count.
- `validation_actuals` and `forecasts` for the 506 Phase 6 detail series equal `FactForecastSeriesDaily` exactly.
- `forecast_metrics_aggregate` reproduces the 24 registry pooled MAE, RMSE, WAPE and bias values and the two leaderboard primary scores.
- `inventory_series_base` equals the Phase 5 per-case Parquet for the curated series.
- No `series_history` or `validation_actuals` date is on or after each dataset's `test_start`.
- Business keys unique; every foreign key resolves.
