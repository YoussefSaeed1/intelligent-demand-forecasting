# Phased roadmap

| Phase | Status and deliverables | Acceptance criteria |
|---|---|---|
| 0 Foundation | Complete: package, configuration, tests and project plans | Import/config checks, local environment and offline tests verified |
| 1 Acquisition and validation | Complete, 2026-11-06: both datasets, canonical Parquet, independent persisted-file audits | Exact quantities/keys/coverage and current hashes passed; original 60 tests passed; limitations retained |
| 2 Advanced EDA and experimental design | Complete: full-series training-prefix EDA, ADI/CV², price investigation, verified figures/tables and frozen protocol | Immutable inputs, aggregate reconciliation, protected evaluation tails and documented evidence |
| 3 Forecasting implementation | Complete: 3A checkpoint preserved; 3B–3E validated; 318 tests and 224 independently reconciled evaluations | Independent predictions/metrics/features, matched populations, four origins, holdout isolation, source hashes and local report checks passed; automated browser preview limited by file URL policy |
| 4 Model Optimisation & Evaluation | Complete, 2026-11-07: 27 fixed cases, 108 validation runs, immutable selection, eight one-time final comparisons, offline report and audit inventory | 352 tests; independent 45,177,440 validation and 3,470,880 final forecast checks; source/protocol hashes, once-only ledger, all technical gates passed; browser rendering not run under file URL policy |
| Independent Claude technical audit | Mandatory future gate after Phase 4 and before Phase 5 | Review integrity, features, leakage, methodology, tuning, statistical validity, code and reproducibility; resolve all critical/high findings and independently revalidate |
| 5 Inventory scenarios | Future, conditional on the audit gate: defined simulator, assumptions and sensitivity studies | Tested event/information ordering, comparable policies, qualified simulated outcomes; no claim of observed business savings |
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

Completed Phase 4 evidence: [scientific interpretation](PHASE4_SCIENTIFIC_REVIEW.md), [completion checklist](PHASE4_COMPLETION_CHECKLIST.md), [safe review commands](PHASE4_REPRODUCIBILITY.md), and [audit inventory](PHASE4_AUDIT_PACKAGE.md). The next required gate is the independent Claude audit; resolve critical/high findings before authorising Phase 5.
