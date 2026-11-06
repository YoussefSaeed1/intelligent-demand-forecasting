# Academic traceability checklist

All research evidence below is **planned**, not completed. Phase 0 only supplies the
foundation; check off requirements only when linked evidence is produced and verified.

| Status | Required item | Planned implementation | Planned evidence |
|---|---|---|---|
| [ ] | Two published datasets | Separate source adapters (Phase 1–2) | Source manifests and permitted hashes |
| [ ] | Dataset source documentation | DATASETS.md verified and completed | Access dates, terms and provenance records |
| [ ] | Data quality assessment | validation/ and profiling | reports/data_quality.md with checks and coverage |
| [ ] | Cleaning/preprocessing | preprocessing/ source policies | Cleaning log and validated canonical tables |
| [ ] | Baseline implementation | models/ naive and seasonal naive | Baseline code, tests and backtest records |
| [ ] | Systematic hyperparameter optimisation | tuning/ grid/random/Optuna | Search spaces, budgets, fold scores and chosen settings |
| [ ] | Evaluation/comparison | evaluation/ common windows | Matched prediction exports and comparison report |
| [ ] | Cross-dataset evaluation where feasible | Independent protocol; conditional transfer | Compatibility assessment, replicated comparisons or infeasibility rationale |
| [ ] | Interpretation/discussion | reporting/ and academic writeup | Error analysis, limitations and supported conclusions |
| [ ] | Reproducible experiments/configuration | configs/ plus run manifests | Hashes, versions, seeds, revision, splits and run instructions |
| [ ] | Explicit forecast horizon | Freeze provisional 28-day proposal | Final experiment config and rationale |
| [ ] | Chronological train/test | Date-based splits and rolling validation | Split manifests and leakage checks |
| [ ] | Appropriate forecasting baselines | History-aware naive/weekly seasonal naive | Baseline rationale and identical-window results |
| [ ] | Comparison of forecasting approaches | Baseline/statistical/ML families | Final comparison tables with coverage |
| [ ] | Relevant error metrics | MAE, RMSE, WAPE, signed bias | Metric tests, zero policies and evaluation exports |
| [ ] | Inventory implications | Explicit scenario assumptions | Simulation sensitivity report and qualified discussion |

The research proposal and experimental protocol define the planned methodology; no
empirical requirement is satisfied by documentation alone. See ROADMAP.md dependencies.

Optional professional enhancements, separate from university requirements: LightGBM,
SHAP explanations, MLflow tracking, advanced uncertainty modelling. Power BI and inventory
simulation are project deliverables; build them after the academic forecasting core.
