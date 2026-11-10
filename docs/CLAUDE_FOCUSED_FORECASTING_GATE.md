# Focused Forecasting Gate — Pre-Phase 5

Scope: risk-based, read-only review. **This is not a comprehensive independent audit.**
No holdout targets reopened; no retraining, re-scoring, or source/evidence edits; no test suite run.

## Evidence read
Handoff, Codex audit (§§7–14), remediation report (§ sampling), Phase 4 frozen selection;
source: `features/recursive.py`, `models/global_ml.py`, `models/baselines.py`;
`frozen_selection.json`, `holdout_access.jsonl`, `sealed_predictions.json`.
Commands run: 3 small read-only Python/git queries (frozen params, ledger timestamps, commit time).

## Verdicts

| # | Area | Verdict |
|---|---|---|
| 1 | Data leakage | **PASS** (with stated limits) |
| 2 | Forecasting correctness | **PASS** (baselines/ML logic); native ARIMA/SARIMA NOT VERIFIED |
| 3 | Model selection | **PASS** (chronology rests on self-recorded timestamps → WARNING on attestation) |
| 4 | Metric integrity | **WARNING** — definitions inspected, numbers not independently recomputed here |
| 5 | Inventory readiness | **PASS** for a hypothetical, fixed-policy simulation, with safeguards below |

### 1. Data leakage — PASS
- `training_matrix` (`recursive.py:215+`): features for a label at index *t* come from `panel.values[..., t-56:t]`; lineage validated (`max_source_date = target-1`); panel is the origin-bounded training view.
- `_predict` (`global_ml.py:122-152`): recursion feeds back own clipped forecasts only; observed-activity context frozen at the origin; no access to future actuals. Price columns absent in the selected M5 RF (`use_historical_prices=false`).
- Ledger: freeze manifest 12:41:37 → seal 12:43:55 → first canonical read 12:44:48 (UTC, 2026-11-07); one read/dataset in the assessment.
- Limit: later "saved actuals" reads (events 9–12) are post-hoc and do not affect scores.

### 2. Forecasting correctness — PASS
- Baselines (`baselines.py:13-46`): MA28 = mean of last 28 days repeated; seasonal MA = per-weekday 4-week mean tiled ×4; seasonal naive = last 7 tiled; all validate finite/nonnegative input and fall back explicitly. Correct.
- Recursive 28-step loop shifts the 56-day window by one each step; target-date calendar features advance correctly.
- Not verified: statsmodels ARIMA/SARIMA optimiser internals; Codex checked interfaces only.

### 3. Model selection — PASS
- Frozen M5 RF parameters (160 trees, depth 16, leaf 20, seed 42) are consistent with the Codex-reported saved final model; validation MAE 1.02007 matches reported value.
- Freeze, seal, then reads, in that order, with a hash-chained ledger; 108 pre-planned runs, fixed primary metric.
- WARNING-level caveats: chronology is self-recorded (AUD-003); selection used the same four origins as ranking (no nested validation); the freeze commit was not reproduced by me.

### 4. Metric integrity — WARNING
- MAE, RMSE (pooled), WAPE (ratio of totals, `metrics.py:34`, `final_review.py:34`) use sound definitions; error = prediction − actual; macro RMSE ≠ pooled RMSE, and the docs say so.
- Codex reports reconciliation at rtol 1e-9; I did not recompute from saved records. NOT independently verified.
- M5 WAPE ≈ 72–86% and 812 zero-actual windows with undefined per-series WAPE — treat WAPE as secondary for M5.

### 5. Inventory readiness — PASS (hypothetical only)
Forecasts are 28-day point forecasts only. Usable if the simulation explicitly **assumes** lead time (≤ 28 days, ideally 1–14), initial stock, review period, holding/shortage/ordering costs and service targets, all labelled synthetic. Sales are a censored-demand proxy; no uncertainty intervals exist.

## Findings
**Critical: none demonstrated. High: none demonstrated.**

Medium/qualifying (not new, confirmed from documents):
- **M5 sparse training** — 182,940 labels (six per series, ~0.32% of eligible); 6,878 series have all six zero. RF is worse than MA28 on that subgroup in all four validation origins (`POST_AUDIT_REMEDIATION_REPORT.md` §138-157).
- **RF over MA28 advantage is small**: 1.33% validation, 1.74% final MAE (1.0472 vs 1.0657); MA28 has better macro MASE and wins most individual series; no dependence-aware significance test. Do not claim RF is meaningfully better than MA28 or treat it as a cost saving.
- Store Item LGBM vs baselines (≈58% MAE reduction vs seasonal naive) is a large, credible effect, but covers one December window.

## Assumptions and limitations
- Reliance on Codex/remediation evidence for numerical reconciliation, feature-bytes hashes, and the 89-file snapshot.
- Not verified: backup integrity, test-suite health, native statistical libraries, canonical data quality, official M5 WRMSSE.
- One seasonal holdout window per dataset; two retail datasets; 500 of 30,490 M5 series for ARIMA-family comparisons.

## Phase 5 readiness
**CONDITIONAL GO — Proceed with documented safeguards**

Safeguards: (1) label the simulation hypothetical with all inputs predeclared before running; (2) include MA28 (and seasonal naive) as forecast inputs alongside RF so the small RF edge is tested in the inventory outcome rather than assumed; (3) calibrate safety buffers on validation errors only, never on the inspected final window; (4) limit lead-time demand to the 28-day forecast coverage; (5) use identical demand paths across policies; (6) report that conclusions are illustrative, not savings estimates.
