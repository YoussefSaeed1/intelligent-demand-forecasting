# Phased roadmap

| Phase | Status and deliverables | Acceptance criteria |
|---|---|---|
| 0 Foundation | Complete: package, configuration, tests and project plans | Import/config checks, local environment and offline tests verified |
| 1 Acquisition and validation | Complete, 2026-11-06: both datasets, canonical Parquet, independent persisted-file audits | Exact quantities/keys/coverage and current hashes passed; original 60 tests passed; limitations retained |
| 2 Advanced EDA and experimental design | Ready for review: full-series training-prefix EDA, ADI/CV², price investigation, figures/tables, proposed protocol | Immutable inputs, aggregate reconciliation, protected evaluation tails, tests and documented evidence; no forecasting training |
| 3 Forecasting implementation | Future: leakage-safe features, baselines, statistical/intermittent/global ML candidates and initial backtests | Explicit approval after Phase 2; matched dates/series, recursive information tests, fallback/coverage records |
| 4 Model Optimisation & Evaluation | Future: systematic tuning on rolling validation, frozen choice, final holdout evaluation and cross-dataset discussion | Declared search spaces/budgets/objective, no test tuning, metric/coverage/error analysis and reproducible manifests |
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
Its validation/metric definitions are implemented; no forecasting experiment has run.
Review does not automatically begin Phase 3. The Claude audit is a future independent
review of the developed solution, not part of Phase 2 and not satisfied by fixture tests.

LightGBM, SHAP, MLflow and advanced uncertainty methods remain optional enhancements.
They must not displace baselines, systematic optimisation, appropriate evaluation,
cross-dataset methodological comparison, interpretation or reproducibility.
