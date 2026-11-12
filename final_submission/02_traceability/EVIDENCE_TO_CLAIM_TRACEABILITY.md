# Evidence-to-claim traceability

Each claim used in the paper (`03_paper`), presentation (`04_presentation`) and portfolio summary (`06_portfolio`) maps to
its source. **Status** says how the claim was checked in Phase 8:

- **R** = recomputed independently from raw evidence in Phase 8 (scripts in `_verification/`);
- **H** = verified by hash or fingerprint;
- **D** = taken from a project document and cross-checked against its machine-readable source;
- **P** = verified live in production on 2026-11-12;
- **A** = assumption, by design.

Paths are relative to the repository root.

## Data

| Claim | Value | Source | Status |
|---|---|---|---|
| Store Item rows, series, period | 913,000; 500; 2013-01-01 to 2017-12-31 | `docs/DATASETS.md`, `docs/EDA_FINDINGS.md`; `data/processed/store_item/daily_sales.parquet` (913,000 rows read in Phase 8) | R |
| M5 rows, series, period | 59,181,090; 30,490; 2011-01-29 to 2016-05-22 | `docs/EDA_FINDINGS.md`, `reports/eda/*` | D |
| Source files unchanged | 9 of 9 SHA-256 match | `artifacts/experiments/phase4/frozen_selection.json` (`source_sha256`) | H |
| M5 zero share in prefix | 68.837443% | `docs/EDA_FINDINGS.md`, `reports/eda/m5_summary.md` | D |
| M5 demand classes | 983 / 489 / 23,044 / 5,953 / 16 / 5 | `docs/EDA_FINDINGS.md`; figure `reports/figures/phase2/m5_classification.png` | D |
| Weekday ratios | Store Item Sun 1.1916, Mon 0.7913; M5 Sat 1.2104, Wed 0.8749 | `docs/EDA_FINDINGS.md` | D |
| M5 missing prices | 12,299,413 (20.782674%) | `docs/EDA_FINDINGS.md`, `docs/DATASETS.md` | D |

## Forecasting

| Claim | Value | Source | Status |
|---|---|---|---|
| Origins and windows | Store Item 2017-08-13 … 2017-12-03; M5 2016-01-03 … 2016-04-24 | `reports/eda/proposed_splits.json`, protocol | D |
| Phase 4 configurations | 27 (12 + 11 tuning, 4 references), 108 fold runs | `artifacts/experiments/phase4/jobs/*.json` (counted) | R |
| Validation forecasts checked | 45,177,440 | `docs/PHASE4_TUNING_RESULTS.md` | D |
| Selected validation MAE | Store Item LightGBM 6.308039821970; M5 RF 1.020066985084 | Recomputed from `registry/*/predictions.parquet` + canonical sales | R |
| Baseline validation MAE | Store Item Seasonal Naive 9.154964285714; M5 MA28 1.033779225039 | Same | R |
| Validation fold MAE (all frozen candidates) | per-origin values | `frozen_selection.json` (`fold_mae`) → `final_submission/figures/figure_data.json` | D |
| Selection fingerprint | `a71ab187aaad10eb…3fdb`, frozen 2026-11-07T12:41Z | `frozen_selection.json` | H |
| Holdout ledger | 12 events, chain intact, file `fa2af529…` | `artifacts/experiments/phase4/holdout_access.jsonl` | H |
| Final forecasts sealed | 3,470,880 | `docs/PHASE4_SCIENTIFIC_REVIEW.md` | D |
| Final MAE Store Item | LightGBM 5.434342531; SN 12.814642857; HW 10.651093201; SMA 15.807285714 | `artifacts/experiments/phase4/final_metrics/*.json` (hash-checked) | H |
| Final MAE M5 | RF 1.047231371; MA28 1.065729312; TSB 1.063192967; SN 1.243972263 | Same | H |
| Store Item gain vs SN | −57.592712% | Derived from the two final MAEs | H |
| M5 gain vs MA28 | −1.735707% | Same | H |
| M5 MASE reversal | RF 1.637036 > MA28 1.610618, TSB 1.624712 | `final_metrics/*.json` | H |
| M5 per-series final wins | RF 15,655, MA28 14,835 (51.3447%) | `docs/PHASE4_SCIENTIFIC_REVIEW.md` | D |
| Validation series majority for MA28 | 50.15% to 53.20% per origin | Same | D |
| M5 zero-sales series in final window | 812 | `final_metrics/*.json` (`undefined_wape`) | H |
| Phase 3 comparison table | values in paper Table 5; M5 RF and LightGBM rows are price-enabled conditional references (price-free anchors 1.0267 and 1.0731 in `docs/PHASE4_TUNING_RESULTS.md`) | `docs/PHASE3_MODEL_COMPARISON.md`, `docs/PHASE3_LIMITATIONS.md` | D |
| Frozen hyperparameters | paper Table 7 | `frozen_selection.json` (`parameters`) | D |

## Inventory (all costs hypothetical NCU)

| Claim | Value | Source | Status |
|---|---|---|---|
| Cases and episodes | 544 cases; 8,429,280 series-episodes; 17 scenarios | `artifacts/inventory/phase5/runs/*/status.json` | R |
| Base pooled costs and fill | e.g. Store Item ML 6,038.4425 at 98.3828%; M5 ML 223.819892 at 83.9189% | Re-aggregated from `series.parquet`; equals `reports/inventory/post_audit_reconciliation.json` exactly | R |
| Per-origin differences | Store Item ML−MA28 −915.78, −598.09, −375.92, +385.21; ML−SN −200.30, −158.19, +112.83, −23.43; M5 ML−MA28 +0.40, +2.35, +1.66, +3.18; ML−SN −16.76, −9.47, −5.87, −11.95 | Same | R |
| Fixed ROP behaviour | 99.9% / 11.0% ordering every review; 7.33 / 11.34 mean days | `post_audit_reconciliation.json` (`fixed_reorder_point`) | D |
| Sensitivity counts | 17/17, 52/68 (Store Item vs MA28) etc. | `docs/PHASE5_INVENTORY_RESULTS.md` | D |
| M5 ties | 7,454 to 7,650 tied series; median difference 0 | `post_audit_reconciliation.json` (`m5_paired_ties`) | D |
| Origin 4 Store Item | 473 of 500 series costlier under ML | `docs/CLAUDE_INDEPENDENT_AUDIT_PHASES_0_5.md` (F-04, recomputed by that audit) | D |
| Base assumptions | L 7, R 1, buffer 3, initial 7, h 1, p 10, k 1 | `configs/inventory.yaml`, `docs/PHASE5_ASSUMPTIONS.md` | A |

## Application and deployment

| Claim | Value | Source | Status |
|---|---|---|---|
| Public URL and commit | https://idf-web.vercel.app, `36da979`, deployment `dpl_362iX8C1ZZjJgYAEXPLS4TknU6zL` | Vercel API; `/api/v1/health` build `36da9797baa3` | P |
| Engine protected and unchanged | 401 anonymous; `9a13fab`, `dpl_7qGSEBPMyeqvJnifA5w6fuUtcorG` | Vercel API, HTTP check | P |
| API parity | 21/21 byte-identical | `reports/webapp/phase7d/live_web_checks.json` | P |
| Reference series totals | 2,555 / 2,772 / 2,900 / 1,309 NCU | Same; `live_engine_checks.json` | P |
| Browser QA | 15/15 page × width, 0 console errors | `reports/webapp/phase7d/browser_prod/browser-qa.json` | P |
| Precision defect | 182 of 3,200 pairs affected before the fix | `reports/webapp/phase7d/float_transport_sweep.json` | D |
| Seeded rows | 655,711 | `docs/PHASE7D_PROGRESS.md`, export manifest | D |
| Dependency status | web prod 0; engine 21 pins no known vulnerabilities | `npm audit`, OSV query (2026-11-12) | P |
| Power BI | 5 pages, 86 visuals, 69 measures, 43-rule QA | `docs/PHASE6_CHECKPOINT.md`, `docs/PHASE6_QA_RESULTS.md` | D |

## References

All 22 references were checked against Crossref (Syntetos and Boylan 2001 added after review) (DOI metadata in `_verification/reference_verification_crossref.json`),
the NeurIPS proceedings page (LightGBM), JMLR (scikit-learn) or the publisher site (FPP3). One page range, Croston (1972),
is cited as pp. 289–303; Crossref lists only the first page (289).

## Statements without support (excluded from every deliverable)

1. Realised or financial **savings** from ML forecasting.
2. A robust Store Item cost advantage of ML (it reverses at origin 4 and is 1.10% against Seasonal Naive).
3. Any M5 inventory advantage of ML over MA28.
4. Suitability of Random Forest for intermittent demand.
5. Fixed Reorder Point as the best policy.
6. Scenario counts as independent confirmations, or any statistical significance.
7. Direct cross-dataset transfer, or comparability with official M5 leaderboard scores (WRMSSE).
8. Production behaviour under real engine or database outages, or of built preview protection (untested).

## Self-review note

This table was produced in the same context that wrote the deliverables. Two separate AI review contexts then
checked the deliverables (see `01_audits/INDEPENDENT_REVIEW.md`); every finding is dispositioned there. They are not
external human validation.
