# Final scientific audit (Phase 8)

Project: Intelligent Demand Forecasting & Inventory Optimisation.
Audit date: 2026-11-12. Repository HEAD at audit start: `9453f28` (private `main`).
Auditor: Claude, acting as the project's research engineer. **This is a self-review by the same assistant that
built much of Phases 7 to 8, not an external examination.** Where an earlier independent audit exists it is cited
as such. Every check below was run read-only; no model was retrained, no simulation rerun and no final-holdout
target opened.

## 1. Verdict

**Scientifically sound within its stated scope, with documented limitations. No critical or high defect found.**
The headline forecasting and inventory numbers reproduce exactly from the persisted evidence. The main open item
is preservation (no verified off-device copy, see section 6), not science.

| Area | Verdict | Basis |
|---|---|---|
| Dataset provenance and integrity | PASS | All 9 raw/canonical files re-hashed in Phase 8 match the Phase 4 freeze record exactly |
| Time-series split methodology | PASS | Four expanding 28-day origins plus one final window, date-only, no gap, no overlap ([protocol](../../docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md)) |
| Leakage prevention | PASS (code-read by the 2026-11-10 audit) | Features for label t use values strictly before t; recursion feeds only its own clipped forecasts |
| Feature availability | PASS | Price, event and SNAP features excluded from every Phase 4 model (publication latency unverified) |
| Horizon and recursive forecasting | PASS | 28 daily steps, one-step global regressors recursed without target updating |
| Baselines and comparisons | PASS | Naive, seasonal naive, moving averages, ETS, ARIMA/SARIMA (subset), Croston, SBA, TSB, RF, LightGBM |
| Model selection | PASS with caveat | Pre-declared objective (equal-origin mean of macro MAE); selection reused the validation windows (optimism, F-05) |
| Metrics and aggregation | PASS | Explicit macro/pooled definitions; undefined denominators kept null; no epsilon |
| Final-holdout governance | PASS with caveat | Fingerprint and 12-event ledger verify; chronology is self-recorded (F-08) |
| Inventory simulation assumptions | PASS (as a hypothetical study) | Assumptions frozen in `configs/inventory.yaml` before results |
| Hypothetical cost units | PASS | NCU everywhere; no savings claim in the deliverables |
| Reproducibility | PARTIAL | Saved-artefact reproduction exact; clean-machine retraining untested (F-10) |

## 2. Independent recomputations performed in Phase 8

Scripts are in `final_submission/_verification/` and use no project model code.

| Check | Method | Result |
|---|---|---|
| Source data integrity | SHA-256 of the 4 M5 CSVs, 3 Store Item CSVs and 2 canonical Parquet files | 9 of 9 match `frozen_selection.json` |
| Validation MAE, selected models and key baselines | Recomputed from saved validation `predictions.parquet` and canonical sales, validation dates only (all strictly before the holdout start) | Store Item LightGBM 6.308039821970 and Seasonal Naive 9.154964285714; M5 RF 1.020066985084 and MA28 1.033779225039; relative difference 0.0 for all four |
| Final-holdout metrics | Each `final_metrics/*.json` SHA-256 checked against `final_evaluation.json`; values compared with the published table | 8 of 8 hashes match; values equal the published tables to within 2 units in the last place (at most 4e-16 relative, from printing/summation order) |
| Selection fingerprint | SHA-256 of sorted compact JSON of `frozen_selection.json` | `a71ab187aaad10eb…` reproduces; `holdout_targets_accessed=false` at freeze |
| Holdout ledger | Self-hash of each event and `previous_sha256` chain | 12 events, chain intact; freeze 2026-11-07T12:41:51Z precedes first canonical read 12:44:48Z (M5) and 12:45:12Z (Store Item) |
| Phase 5 inventory results | Re-aggregated all 544 completed cases from per-series Parquet | 544 cases, 8,429,280 series-episodes, 17 scenarios; every base pooled cost and fill rate equals `post_audit_reconciliation.json` exactly (max discrepancy 0.0); per-origin ML-minus-MA28 and ML-minus-Seasonal-Naive differences equal the published tables |
| Tuning configuration counts | Counted Phase 4 job files | 12 Store Item and 11 M5 tuning trials, 4 references, 108 fold runs, as documented |

Not recomputed (would need the sealed holdout or new training): final-holdout errors from actuals, MASE/RMSSE
from scratch for every case, and retraining of any model.

## 3. Observed, simulated and assumed: how results must be read

| Category | Examples | How to report |
|---|---|---|
| **Observed experimental results** | Validation and final-holdout forecast errors on recorded sales | Report as measured on these two histories; no significance claim |
| **Simulated results** | Phase 5 costs, fill rates, stock levels for four policies | Report as outputs of a deterministic simulator under frozen assumptions |
| **Assumptions** | Lead 7 days, review 1 day, buffer 3 mean-days, initial cover 7 days, h=1, p=10, k=1 NCU, lost sales, unlimited supply | State explicitly; they are not measurements |
| **Illustrative scenarios** | 17 sensitivity scenarios; the live planner's custom scenarios | Parameter sensitivity on the same four origins; not independent confirmation |

Observed sales are a potentially censored proxy for demand: zeros and low values can reflect stock-outs or
assortment, not absence of demand (Conrad, 1976). The datasets contain no stock, order, lead-time or cost records.

## 4. Inconsistencies found

None changes a number. They are status-text inconsistencies between documents written at different times.
The affected documents are partly hash-bound by preservation overlays, so they were **not edited**; this audit
records the correction instead.

| # | Location | Inconsistency | Correct reading |
|---|---|---|---|
| I-1 | `docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md` title | Says "proposed, not executed" | Written in Phase 2; the protocol was executed in Phases 3 and 4 unchanged |
| I-2 | `docs/PHASE4_FINAL_EVALUATION.md`, `PHASE4_SCIENTIFIC_REVIEW.md` | Say the independent Claude audit is "still mandatory" / "not performed" | Completed 2026-11-10, verdict CONDITIONAL ([audit](../../docs/CLAUDE_INDEPENDENT_AUDIT_PHASES_0_5.md)) |
| I-3 | `docs/ROADMAP.md` | Phase 6 listed as "Future"; "Phase 6 and Phase 7 are unstarted"; "four-page Power BI report" | Phase 6 complete (five pages, commit `987e27f`); Phase 7 deployed (records in `PHASE7D_*`) |
| I-4 | `docs/ACADEMIC_REQUIREMENTS.md` | No rows for BI, web application or submission deliverables | Covered by Phase 6/7 documents and this Phase 8 package |
| I-5 | Published final-metric tables vs `final_metrics/*.json` | Differences in the last one or two binary digits for 4 of 8 rows | Numerical representation only; not a discrepancy of substance |
| I-6 | `docs/EDA_FINDINGS.md` | "24 figures" (original run) and "29 figures" (enhanced) both appear | Both correct; the enhanced presentation regenerated figures from the same tables |
| I-8 | Paper Table 5 (draft) | Phase 3 M5 random forest and LightGBM rows were shown as plain validation results | They used historical prices and are conditional references; the price-free Phase 4 anchors (1.0267, 1.0731) give the same ranking. Corrected in the paper after the independent review |
| I-7 | `docs/PHASE5_ASSUMPTIONS.md` | Mentions an "ARIMA subset count" from the focused gate | Historical; ARIMA/SARIMA were Phase 3 subset comparators only, not Phase 4/5 candidates |

## 5. Statements the evidence does NOT support (must not appear in any deliverable)

- That ML forecasting produces **savings** or any realised financial benefit.
- That the Store Item cost advantage over MA28 (−5.86%) is robust: it reverses at origin 4 (+385.21 NCU) and is
  only −1.10% against Seasonal Naive, with ML costlier at origin 3.
- That M5 Random Forest is better for inventory: it is costlier than MA28 at all four origins (+1.90 NCU pooled).
- That Random Forest suits intermittent demand: in the 6,878-series sparse subgroup MA28 has lower MAE at all origins.
- That Fixed Reorder Point is the best policy: its low cost reflects lower stock and lower fill (a degenerate comparator).
- That "17 of 17 scenarios" is robustness evidence: all scenarios share the same four origins and forecasts.
- That any difference is statistically significant: four adjacent origins and correlated series do not support it.
- That results transfer across datasets or to an official M5 leaderboard metric (WRMSSE was not computed).
- That the M5 model ranking holds on every metric: MA28 and TSB beat RF on macro MASE in the final holdout.

## 6. Remaining scientific and preservation risks

| Risk | Severity | Status |
|---|---|---|
| Selection optimism from reusing validation windows in Phase 5 (F-05) | Medium | Accepted; unquantifiable now that the holdout is consumed; direction favours ML |
| Limited seasonal coverage: four adjacent 28-day origins and one final window | Medium | Accepted limitation |
| Censored demand: sales proxy for demand; lost-sales model is assumed | Medium | Accepted limitation |
| Self-recorded chronology of the freeze and holdout read (F-08) | Low | Accepted; mitigated by code snapshot hashes and once-only ledger |
| Bounded ML training sample (300 labels per Store Item series, 6 per M5 series) | Low | Disclosed; the M5 sample is very small per series |
| Clean-machine reproduction untested; Python 3.14 snapshot environment (F-10) | Low | Open, optional |
| **No verified off-device copy of the evidence (F-02)** | **Medium, blocks submission readiness** | See the backup report; requires one owner action |

## 7. Conclusion for the examiners

The project's strongest scientific contributions are its governance and honesty: a frozen, hash-verified
selection evaluated once on an untouched holdout, full-population evaluation on 30,490 M5 series, and an
inventory analysis that reports where machine learning does not help. Its forecasting claims are modest and
supported: on the final holdout the selected Store Item LightGBM reduces MAE by 57.59% relative to Seasonal
Naive, and the selected M5 Random Forest by 1.74% relative to MA28, with the M5 ranking reversed on macro MASE.
Its inventory claims are explicitly hypothetical.
