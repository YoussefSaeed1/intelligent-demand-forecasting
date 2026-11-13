# Phased roadmap

## Current status (updated 2026-11-13)

All planned phases are complete. The independent audit verdict for Phases 0 to 5 remains **CONDITIONAL**, and
the submission-readiness items listed below are still open. This section is the current status. The table and
notes under [Historical roadmap](#historical-roadmap-recorded-at-the-phase-5-audit-response-checkpoint) are kept
unchanged as the record written at the Phase 5 checkpoint.

| Phase | Current status | Evidence |
|---|---|---|
| 0 Foundation | Complete | Package, configuration and offline tests |
| 1 Acquisition and validation | Complete, 2026-11-06 | [DATASETS.md](DATASETS.md), [VALIDATION.md](VALIDATION.md) |
| 2 Advanced EDA and experimental design | Complete | [EDA_FINDINGS.md](EDA_FINDINGS.md), [protocol](FORECASTING_EXPERIMENTAL_PROTOCOL.md) (written as "proposed" in Phase 2; executed unchanged in Phases 3 and 4) |
| 3 Forecasting implementation | Complete | [PHASE3_BENCHMARK_REPORT.md](PHASE3_BENCHMARK_REPORT.md), [PHASE3_INTEGRITY_REVIEW.md](PHASE3_INTEGRITY_REVIEW.md) |
| 4 Model optimisation and final evaluation | Complete, 2026-11-07 | [PHASE4_FINAL_EVALUATION.md](PHASE4_FINAL_EVALUATION.md), [PHASE4_COMPLETION_CHECKLIST.md](PHASE4_COMPLETION_CHECKLIST.md) |
| Independent audit of Phases 0 to 5 | Complete, 2026-11-10; verdict CONDITIONAL (0 Critical, 0 High, 6 Medium, 4 Low, 2 Informational) | [Audit](CLAUDE_INDEPENDENT_AUDIT_PHASES_0_5.md), [response](PHASE5_AUDIT_RESPONSE.md) |
| 5 Hypothetical inventory scenarios | Complete: 17 scenarios, four policies, 544 cases | [PHASE5_INVENTORY_RESULTS.md](PHASE5_INVENTORY_RESULTS.md), [PHASE5_COMPLETION_CHECKLIST.md](PHASE5_COMPLETION_CHECKLIST.md) |
| 6 Power BI report | Complete, 2026-11-10: five pages, 86 visuals, 69 DAX measures; 43-rule QA 42 pass, 1 cosmetic warning, 0 fail | [PHASE6_CHECKPOINT.md](PHASE6_CHECKPOINT.md), [PHASE6_QA_RESULTS.md](PHASE6_QA_RESULTS.md) |
| 7A–7C Web application | Complete, 2026-11-12 | [PHASE7_CHECKPOINT.md](PHASE7_CHECKPOINT.md), [PHASE7C_QA_REPORT.md](PHASE7C_QA_REPORT.md) |
| 7D Deployment | Complete, 2026-11-12: <https://idf-web.vercel.app> public; engine protected | [PHASE7D_DEPLOYMENT_RECORD.md](PHASE7D_DEPLOYMENT_RECORD.md) |
| 8 Final submission package | Prepared, 2026-11-13; owner actions open | [final_submission/README.md](../final_submission/README.md) |

The historical plan below combined "BI and academic submission" as a single Phase 6. In practice the work ran as
Phase 6 (Power BI), Phase 7 (web application and deployment) and Phase 8 (submission package).

Open before academic submission (see
[remaining risks](../final_submission/07_checklists/REMAINING_RISKS_AND_FOLLOW_UP.md)):

- F-02: a verified off-device copy of the Phase 4, Phase 5 and Phase 8 backups.
- R-01: the owner's recorded review of the Kaggle data-use terms, including the public display of curated sales.
- External validation by the supervisor or examiners. The AI-assisted audits do not replace it.

Accepted limitations from the audit (F-05, F-06, F-08, F-09) remain in force, as do the reporting rules for every
output: show per-origin comparisons, do not treat the 17 scenarios as independent confirmations, and never call
simulated cost differences savings.

## Historical roadmap (recorded at the Phase 5 audit-response checkpoint)

Preserved without edits. Statements such as "Future", "unstarted" and "nothing was pushed" describe the project
at that checkpoint, not its current state.

| Phase | Status and deliverables | Acceptance criteria |
|---|---|---|
| 0 Foundation | Complete: package, configuration, tests and project plans | Import/config checks, local environment and offline tests verified |
| 1 Acquisition and validation | Complete, 2026-11-06: both datasets, canonical Parquet, independent persisted-file audits | Exact quantities/keys/coverage and current hashes passed; original 60 tests passed; limitations retained |
| 2 Advanced EDA and experimental design | Complete: full-series training-prefix EDA, ADI/CV², price investigation, verified figures/tables and frozen protocol | Immutable inputs, aggregate reconciliation, protected evaluation tails and documented evidence |
| 3 Forecasting implementation | Complete: 3A checkpoint preserved; 3B–3E validated; 318 tests and 224 independently reconciled evaluations | Independent predictions/metrics/features, matched populations, four origins, holdout isolation, source hashes and local report checks passed; automated browser preview limited by file URL policy |
| 4 Model Optimisation & Evaluation | Complete, 2026-11-07: 27 fixed cases, 108 validation runs, immutable selection, eight one-time final comparisons, offline report and audit inventory | 352 tests; independent 45,177,440 validation and 3,470,880 final forecast checks; source/protocol hashes, once-only ledger, all technical gates passed; browser rendering not run under file URL policy |
| Independent Claude technical audit | Complete, 2026-11-10: risk-based audit of Phases 0 to 5; verdict CONDITIONAL (0 Critical, 0 High, 6 Medium, 4 Low, 2 Informational); see [PHASE5_AUDIT_RESPONSE.md](PHASE5_AUDIT_RESPONSE.md) | Review integrity, features, leakage, methodology, tuning, inventory logic, code and reproducibility; no critical/high findings; reporting conditions apply to Phase 6 |
| 5 Inventory scenarios | Implemented and executed under the owner-authorised focused gate: 17 scenarios, four policies, full populations, four validation origins; see current completion checklist | Sequential design/engine/base/report gates; independent stock/cost reconciliation; protected Phase 4 evidence; no observed business savings claim |
| 6 BI and academic submission | Future: validated exports, four-page Power BI report, interpretation/writeup/presentation | Reconciled dashboard totals, academic traceability and defensible final conclusions |

Phase 1 closure is preserved: both datasets passed independent persisted-file audits.
Store Item has complete per-date/per-series coverage; its old missing-date warning was
informational, and its one zero was preserved. M5 retains 12,299,413 missing historical
prices. Hashes bind current files to the independent audits. Phase 2 reads those files
without acquisition, canonical rewriting, target imputation or observation removal.

Phase 2 evidence and exact proposed 28-day rolling windows are documented in
[EDA_FINDINGS.md](EDA_FINDINGS.md) and
[FORECASTING_EXPERIMENTAL_PROTOCOL.md](FORECASTING_EXPERIMENTAL_PROTOCOL.md).
Its validation/metric definitions are implemented and authorised Phase 3 experiments
now run under independent gates. The Claude audit is a future independent
review of the developed solution, not part of Phase 2 and not satisfied by fixture tests.

Phase 3A implements the saved protocol, model interfaces, leakage-safe data capabilities,
metrics and local experiment lifecycle. Its original infrastructure-only checkpoint
remains unchanged. Phase 3B–3E are authorised by the master execution prompt, including
fixed initial statistical/ML fits and full-population or explicitly matched-subset
validation. Final holdout targets were inaccessible throughout Phase 3; their separately authorised one-time Phase 4C assessment is now complete. See
[PHASE3_PROGRESS.md](PHASE3_PROGRESS.md), [ML availability](FEATURE_AVAILABILITY.md), and
the historical [Phase 3A review](PHASE3A_INTEGRITY_REVIEW.md).
The master execution initially left changes uncommitted. The subsequent final
scientific review authorises a secure local Phase 3 checkpoint after its gates pass.
The subsequent Phase 4 master prompt authorised and completed 4A?4D. No push, upload, automatic final Phase 4 checkpoint or Phase 5 work was performed.

CPU LightGBM is now an implemented Phase 3 comparator. SHAP, MLflow and advanced
uncertainty methods remain optional enhancements.
They must not displace baselines, systematic optimisation, appropriate evaluation,
cross-dataset methodological comparison, interpretation or reproducibility.

Completed Phase 4 evidence: [scientific interpretation](PHASE4_SCIENTIFIC_REVIEW.md), [completion checklist](PHASE4_COMPLETION_CHECKLIST.md), [safe review commands](PHASE4_REPRODUCIBILITY.md), and [audit inventory](PHASE4_AUDIT_PACKAGE.md). The owner subsequently accepted the limited focused conditional gate for hypothetical Phase 5. Broader Claude review of forecasting and inventory remains mandatory before Phase 6/7.


Phase 5 uses existing frozen validation forecasts only: no final-holdout demand,
new forecast training/tuning, daily forecast regeneration or forecasting reselection.
See [actual gates](PHASE5_COMPLETION_CHECKLIST.md),
[results](PHASE5_INVENTORY_RESULTS.md), and
[broader audit handoff](PHASE5_CLAUDE_AUDIT_HANDOFF.md).
Phase 5 and the audit response are checkpointed in one local commit; nothing was pushed.
Off-device backup remains outstanding before academic submission.
Phase 6 and Phase 7 are unstarted. Earlier statements above describe their historical
phase checkpoints, not a new independent certification.
