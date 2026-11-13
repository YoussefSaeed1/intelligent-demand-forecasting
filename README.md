# Intelligent Demand Forecasting & Inventory Optimisation

**Current status (2026-11-13): Phases 0 to 7 are complete, and the Phase 8 submission package has been prepared.
The research web application is deployed at <https://idf-web.vercel.app>. The independent audit verdict is still
CONDITIONAL (0 Critical, 0 High findings), and several owner actions remain open; see
[Independent review and outstanding conditions](#independent-review-and-outstanding-conditions).**

Earlier versions of this README described development checkpoints (for example "Phase 6 has not started",
"no dashboard yet" and "nothing was pushed"). Those statements were true when they were written and have since
been superseded. See [Historical checkpoints](#historical-checkpoints) for where those records are kept.
GitHub renders [`.github/README.md`](.github/README.md) as the public landing page. This file is the full
technical README.

## Project status by phase

| Phase | Status | Evidence |
|---|---|---|
| 0 Foundation | Complete | Package, configuration and offline tests ([roadmap](docs/ROADMAP.md)) |
| 1 Acquisition and validation | Complete (2026-11-06) | [Datasets](docs/DATASETS.md), [validation](docs/VALIDATION.md), `reports/data_quality/` |
| 2 EDA and experimental design | Complete | [EDA findings](docs/EDA_FINDINGS.md), [protocol](docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md) |
| 3 Forecasting implementation | Complete | [Benchmark report](docs/PHASE3_BENCHMARK_REPORT.md), [integrity review](docs/PHASE3_INTEGRITY_REVIEW.md) |
| 4 Optimisation and final evaluation | Complete (2026-11-07) | [Final evaluation](docs/PHASE4_FINAL_EVALUATION.md), [checklist](docs/PHASE4_COMPLETION_CHECKLIST.md) |
| Independent audit of Phases 0 to 5 | Complete (2026-11-10), verdict **CONDITIONAL** | [Audit](docs/CLAUDE_INDEPENDENT_AUDIT_PHASES_0_5.md), [response](docs/PHASE5_AUDIT_RESPONSE.md) |
| 5 Hypothetical inventory simulation | Complete | [Results](docs/PHASE5_INVENTORY_RESULTS.md), [checklist](docs/PHASE5_COMPLETION_CHECKLIST.md) |
| 6 Power BI report | Complete (2026-11-10) | [Checkpoint](docs/PHASE6_CHECKPOINT.md), [QA results](docs/PHASE6_QA_RESULTS.md) |
| 7A–7C Web application | Complete (2026-11-12) | [Checkpoint](docs/PHASE7_CHECKPOINT.md), [QA report](docs/PHASE7C_QA_REPORT.md) |
| 7D Deployment | Complete (2026-11-12) | [Deployment record](docs/PHASE7D_DEPLOYMENT_RECORD.md), [progress](docs/PHASE7D_PROGRESS.md) |
| 8 Final submission package | Prepared (2026-11-13); owner actions open | [Package](final_submission/README.md), [remaining risks](final_submission/07_checklists/REMAINING_RISKS_AND_FOLLOW_UP.md) |

"Complete" means the phase's deliverables exist in this repository and passed the gates recorded in the linked
evidence. It does not mean the project is approved without conditions, and it does not stand in for external
examination.

## Overview and architecture

The project asks whether machine learning forecasts daily retail demand better than simple baselines, and what
the difference would mean for replenishment under explicitly assumed inventory conditions. Observed sales may be
limited by availability, so they are treated as a proxy for demand, not as latent demand.

```text
Kaggle sources ──> ingestion and audits ──> canonical Parquet ──> EDA and frozen protocol
                                                              └─> forecasting (Phases 3–4) ──> sealed final holdout
                                                              └─> inventory simulation (Phase 5)
Saved evidence ──> Power BI PBIP report (Phase 6)
Saved evidence ──> curated export ──> Supabase PostgreSQL ──> Next.js web app (idf-web)
                                                          └─> FastAPI engine (idf-engine, frozen Phase 5 engine)
```

The research pipeline runs locally in Python. The Power BI report and the web application read only saved,
hash-verified evidence. They do not retrain or reselect any model. See the
[architecture figure](final_submission/figures/fig_architecture.png) and
[application architecture](docs/PHASE7_APPLICATION_ARCHITECTURE.md).

## Datasets and methodology

- [Store Item Demand Forecasting Challenge](https://www.kaggle.com/competitions/demand-forecasting-kernels-only/data):
  500 daily store/item series, 913,000 rows, 2013–2017.
- [M5 Forecasting Accuracy](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data): 30,490 Walmart
  series, 59,181,090 rows, 2011–2016. 68.8% of series-days in the EDA prefix have zero sales.

Raw data is not redistributed. Download it yourself under each competition's rules
([DATASETS.md](docs/DATASETS.md)). The two datasets are separate benchmarks, and direct model transfer between
them is not established.

Methodology: hashed acquisition and quality audits; training-prefix EDA; four expanding 28-day validation
origins and one final 28-day holdout; leakage-safe, origin-bounded lag and calendar features; a seeded, fixed
search budget; and a frozen, fingerprinted model choice scored once on the holdout and recorded in a
hash-chained ledger. Price, event and SNAP features were excluded from Phase 4 models because their publication
timing could not be verified. See [experimental design](docs/EXPERIMENTAL_DESIGN.md),
[metric definitions](docs/METRIC_DEFINITIONS.md) and [feature availability](docs/PHASE4_FEATURE_AVAILABILITY.md).

## Forecasting models and evaluation

Phase 3 defines 15 methods. Thirteen are evaluated on full populations: five baselines (naive, seasonal naive,
28-day and seasonal moving averages, zero), exponential smoothing (SES, Holt, Holt-Winters), Croston, SBA, TSB,
and global Random Forest and LightGBM. ARIMA and SARIMA run only on declared 53/51-series statistical subsets.
Phase 4 evaluated 27 fixed cases (23 tuning configurations and 4 references) over 108 validation fold runs and
45,177,440 forecasts, then sealed 3,470,880 final forecasts across eight selected model/comparator evaluations
before either holdout was opened (selection fingerprint `a71ab187…`, 12-event ledger).

| Selected method (final holdout) | Macro MAE | Pooled RMSE | Pooled WAPE % | Best simple baseline (MAE) | Gain |
|---|---:|---:|---:|---|---:|
| Store Item LightGBM | 5.434343 | 7.066976 | 12.258462 | Seasonal naive (12.814643) | 57.59% |
| M5 price-free Random Forest | 1.047231 | 2.201063 | 72.582278 | 28-day moving average (1.065729) | 1.74% |

On M5, MA28 has a better macro MASE than the Random Forest (1.6106 vs 1.6370), so the M5 ranking depends on the
metric. These are predictive benchmark results on two histories. They are not evidence of statistical
significance or of inventory savings. Details: [tuning](docs/PHASE4_TUNING_RESULTS.md),
[frozen selection](docs/PHASE4_FROZEN_MODEL_SELECTION.md), [final evaluation](docs/PHASE4_FINAL_EVALUATION.md),
[scientific review](docs/PHASE4_SCIENTIFIC_REVIEW.md).

## Inventory simulation and limitations

A deterministic lost-sales simulator compares four replenishment policies (selected ML, MA28 and seasonal-naive
forecast-driven order-up-to policies, plus a fixed reorder-point comparator) across 17 predefined scenarios:
544 cases and 8,429,280 series-episodes, reported in normalised cost units (NCU). Lead times, costs, initial
stock and buffers are assumptions, not measurements.

| Base scenario, pooled over four origins | ML − MA28 | ML − Seasonal naive |
|---|---:|---:|
| Store Item | −376.14 NCU (−5.86%); reverses at origin 4 (+385.21) | −67.27 NCU (−1.10%); ML costlier at origin 3 |
| M5 | +1.90 NCU (+0.85%); ML costlier at all four origins | −11.01 NCU (−4.69%) |

Reporting rules from the independent audit apply to every output. Per-origin ML, MA28 and seasonal-naive
results are shown together. The 17 scenarios are not independent confirmations, because they share the same
four origins and forecasts. Fixed reorder point is a low-stock, low-service comparator, not the best policy.
Simulated cost differences are never realised savings. The inventory study reuses validation windows that were
also used for model selection, which favours ML (F-05).

Read the [results](docs/PHASE5_INVENTORY_RESULTS.md), [protocol](docs/INVENTORY_SIMULATION_PROTOCOL.md),
[sensitivity analysis](docs/PHASE5_SENSITIVITY_ANALYSIS.md) and [limitations](docs/PHASE5_LIMITATIONS.md).

## Power BI report

[`powerbi/`](powerbi/README.md) holds a five-page PBIP project: Executive Overview, Forecasting Performance,
Inventory Optimisation, Scenario & Sensitivity, and Model Explorer & Governance. It has 86 visuals, 69 DAX
measures, 19 model tables and 28 relationships. The full 43-rule QA passed 42 rules, with 1 cosmetic warning
(E06, caveat footers about 0.4 px beyond the canvas) and 0 failures. DAX values reconcile with the saved
scientific evidence ([QA results](docs/PHASE6_QA_RESULTS.md)). The later Phase 6 checkpoint re-ran Layers A and E
only, and does not claim a new full-engine run ([checkpoint](docs/PHASE6_CHECKPOINT.md)). The `DataRoot`
parameter must point at the local reporting CSVs, which are not committed. See
[DAX catalogue](docs/PHASE6_DAX_MEASURE_CATALOGUE.md) and [dashboard guide](docs/PHASE6_POWERBI_DASHBOARD.md).

## Web application and forecasting engine

- **Web application (`apps/web`)**: Next.js 16 research explorer with five pages (Executive Overview, Forecast
  Explorer, Inventory Planner, Scenario Comparison, Research & Methodology). It reads curated evidence from Supabase
  PostgreSQL through read-only roles: all 500 Store Item series and 300 of the 30,490 M5 series. It never reads
  final-holdout targets.
- **Engine (`apps/engine`)**: a FastAPI service that runs the frozen Phase 5 engine. The engine is vendored
  byte-identically in [`packages/inventory_core`](packages/inventory_core). It is reachable only
  server-to-server, behind a shared key and Vercel Authentication.
- Live simulations were verified byte-for-byte against the local reference. Two defects were found and fixed
  before go-live: database float rounding to 15 digits (182 of 3,200 cases affected) and a rejected TLS startup
  parameter.

Specifications: [API](docs/PHASE7_API_SPECIFICATION.md), [data contract](docs/PHASE7_DATA_CONTRACT.md),
[schema](docs/PHASE7_SUPABASE_SCHEMA_DESIGN.md), [backend results](docs/PHASE7B_BACKEND_RESULTS.md),
[quality gates](docs/PHASE7_QUALITY_GATES.md).

## Deployment

| Component | URL | Access |
|---|---|---|
| Research web application | <https://idf-web.vercel.app> | Public |
| Simulation engine | `https://idf-engine.vercel.app` | Protected by design. Anonymous requests return 401; only the web application calls it |
| Database | Supabase `idf-research-explorer` (eu-central-1, Free) | Private; least-privilege roles through the transaction pooler |

The Phase 7D record documents production QA on 2026-11-12, against web build `36da979` (rewritten as `9685e8d`,
see [COMMIT_ID_MAP.md](docs/COMMIT_ID_MAP.md)). It recorded 21/21 API responses byte-identical to the local
reference, browser QA 15/15, and passing header, secret-scan and rate-limit checks
([record](docs/PHASE7D_DEPLOYMENT_RECORD.md), [runbook](docs/PHASE7D_DEPLOYMENT_RUNBOOK.md),
[rollback plan](docs/PHASE7D_ROLLBACK_PLAN.md)).

Since then, the web app was redeployed from `04f5731`, which changed only page text (removing institutional
wording). A health check on 2026-11-13 returned `status ok`, build `04f5731a9571`, engine reachable, and engine
version `cedc5a31533772fc` (unchanged frozen engine). The full 7D production QA suite has not been re-run against
that build. Supabase Free pauses idle projects, so open the app before any demonstration.

## Reproducibility and testing

Windows PowerShell, from the project root (Python 3.11+; the recorded environment used 3.14):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,boosting]"
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m pytest

# Data is not redistributed: review the competition rules on Kaggle first
.\.venv\Scripts\python.exe -m intelligent_demand download-data --dataset all
.\.venv\Scripts\python.exe -m intelligent_demand audit-store-item
```

Large data, models, predictions and generated figures are Git-ignored and held in verified local backups. Use
the read-only, saved-evidence commands in [PHASE4_REPRODUCIBILITY.md](docs/PHASE4_REPRODUCIBILITY.md) and
[PHASE5_INVENTORY_RESULTS.md](docs/PHASE5_INVENTORY_RESULTS.md) rather than re-running experiments.
Environment notes: [VALIDATION.md](docs/VALIDATION.md); snapshot: `docs/environment-freeze.txt`.

Recorded test evidence:

- Python suite: 352 tests at Phase 4.
- Web: 88/88 (UI 34, API 19, precision 24, engine client 11), plus TypeScript, ESLint and `next build` (Phase 7D-3A).
- Engine: 69/69.
- Power BI QA: 42 pass, 1 warning.

Phase 8 independently recomputed validation MAE and the Phase 5 totals from saved outputs, with a discrepancy of
0.0 ([scientific audit](final_submission/01_audits/FINAL_SCIENTIFIC_AUDIT.md)).

Re-run on 2026-11-13 from a fresh clone (Linux, Python 3.13, no local data or artefacts): 448 passed and 3 failed.
All three failures are environment-specific, not regressions:

- Two inventory-runner tests read the Windows-only `psutil` field `peak_wset`.
- One Phase 4 report test needs the Git-ignored `artifacts/experiments/phase4/plan.json`.

Ruff reports 0 findings in `src/` and `tests/`, and 101 line-length (E501) findings in the `final_submission/`
helper scripts. Clean-machine retraining has not been tested (audit finding F-10).

## Independent review and outstanding conditions

- **Independent audit of Phases 0 to 5 (2026-11-10): CONDITIONAL.** 0 Critical, 0 High, 6 Medium, 4 Low and
  2 Informational findings. Work could proceed under reporting conditions. Finding dispositions are in
  [PHASE5_AUDIT_RESPONSE.md](docs/PHASE5_AUDIT_RESPONSE.md). The verdict has not been upgraded to unconditional.
- **Phase 8 reviews (2026-11-12/13):** a scientific self-audit ("scientifically sound within its stated scope"),
  a technical and security self-audit, and a second-pass review in two separate AI contexts
  ([final_submission/01_audits/](final_submission/01_audits/INDEPENDENT_REVIEW.md)). These are AI-assisted
  reviews, not external human examination.

Open items, as recorded in the [remaining risks](final_submission/07_checklists/REMAINING_RISKS_AND_FOLLOW_UP.md)
and the [submission checklist](final_submission/07_checklists/REPRODUCIBILITY_AND_SUBMISSION_CHECKLIST.md):

1. **F-02: no verified off-device copy** of the 6.5 GB Phase 4/5 evidence or of the Phase 8 backup. All backups
   are on the same laptop. This blocks submission readiness.
2. **R-01: the owner's review of the Kaggle data-use terms is not yet recorded.** This now includes whether the
   public app may display curated daily sales.
3. External validation by the supervisor or examiners, supervisor name on the title page, and programme
   format requirements.
4. Not tested in production: engine and database outage handling, and built-preview protection.
5. Accepted limitations: selection optimism from reused validation windows (F-05), M5 sparse-demand weakness
   (F-06), self-recorded holdout chronology (F-08), finite-episode effects (F-09), and censored demand.

## Repository structure

```text
configs/                  Experiment, inventory, Power BI and web-export settings
src/intelligent_demand/   Ingestion, validation, EDA, features, models, tuning, evaluation,
                          experiments, inventory simulation, BI export/QA, preservation, reporting
tests/                    Offline Python test suite (including leakage and evidence-integrity tests)
powerbi/                  Five-page Power BI PBIP project (semantic model and report definitions)
apps/web/                 Next.js research application (idf-web)
apps/engine/              FastAPI simulation engine (idf-engine)
packages/inventory_core/  Byte-identical vendored copy of the frozen Phase 5 engine
tools/phase7d/            Deployment verification tools
reports/                  Selected small reports, QA evidence and hash-bound provenance manifests
docs/                     Phase-by-phase design, results, audits, checkpoints and roadmap
final_submission/         Paper, presentation, audits, traceability, checklists and backup report
data/, artifacts/         Git-ignored local data and generated artefacts
```

## Historical checkpoints

Each phase was closed by a checkpoint document written at that time. Those documents are preserved unchanged
and describe the project as it was then. For example, the Phase 5 and Phase 6 checkpoints state that later phases
had not started and that nothing had been pushed. Read them as dated records, not as current status:

- Phase 3: [progress](docs/PHASE3_PROGRESS.md), [3A review](docs/PHASE3A_INTEGRITY_REVIEW.md)
- Phase 4: [checkpoint preservation](docs/PHASE4_CHECKPOINT_PRESERVATION.md), [internal audit](docs/CODEX_INTERNAL_AUDIT_PHASES_0_4.md),
  [post-audit remediation](docs/POST_AUDIT_REMEDIATION_REPORT.md)
- Phase 5: [progress](docs/PHASE5_PROGRESS.md), [backup preservation](docs/PHASE5_BACKUP_PRESERVATION.md)
- Phase 6: [checkpoint](docs/PHASE6_CHECKPOINT.md)
- Phase 7: [checkpoint](docs/PHASE7_CHECKPOINT.md), [7D progress](docs/PHASE7D_PROGRESS.md)
- Roadmap: [current status and historical table](docs/ROADMAP.md)

The previous text of this README (current to Phase 5) is kept in Git history at commit `fc27f35`
(`git show fc27f35:README.md`). Earlier archived copies are under `reports/inventory/original_documents/` and
`reports/post_audit/original_source/`. This update is recorded in
[`reports/preservation/CURRENT_STATUS_DOCS_OVERLAY_20261113.json`](reports/preservation/CURRENT_STATUS_DOCS_OVERLAY_20261113.json).
Commit IDs written before 2026-11-13 map to the current history through [COMMIT_ID_MAP.md](docs/COMMIT_ID_MAP.md).

## Copyright

© 2026 Youssef Saeed. All rights reserved. The source is published for viewing and assessment only; no licence is
granted to use, copy, modify or redistribute it. No licence is granted for the source datasets.
