# Academic traceability checklist

Status distinguishes verified empirical evidence from proposed forecasting work.
Offline test fixtures are not forecasting results on the real datasets.

| Status | Required item | Current evidence / remaining work |
|---|---|---|
| Complete | Two published datasets | DATASETS.md; independent audits in reports/data_quality; both source adapters and hashes |
| Partial | Source documentation | Provenance/layout documented; detailed competition terms still require user's recorded review |
| Complete | Data quality assessment | Independent source-to-Parquet audits, VALIDATION.md, immutable hash checks |
| Partial | Cleaning/preprocessing | Canonical representation verified; zeros/null prices preserved; any future preprocessing must remain fold-safe |
| Complete | Training-prefix EDA | EDA_FINDINGS.md, dataset reports, all-series ADI/CV², 39 tables and 24 PNG/SVG figure pairs |
| Design complete | Explicit forecast horizon | 28 daily steps; exact dates and rationale in FORECASTING_EXPERIMENTAL_PROTOCOL.md |
| Design complete | Chronological train/validation/test | Four expanding rolling origins and final protected holdout; date-only construction tested |
| Design complete | Relevant error metrics | MAE/RMSE/WAPE/bias plus weekly MASE/RMSSE definitions and edge-case tests; no real prediction scores yet |
| Future | Appropriate baseline implementation | Naive, weekly seasonal naive and moving average; matched-window evidence required |
| Future | Comparison of forecasting approaches | Statistical, intermittent and ML family recommendations; actual implementations/scores not produced |
| Future | Systematic hyperparameter optimisation | Freeze spaces/caps; record validation trials, failures and selected settings in Phase 4 |
| Future | Evaluation/comparison | Identical series/target windows; final holdout only after model choices freeze |
| Partial | Cross-dataset evaluation where feasible | EDA comparison and independent benchmark design ready; baseline-relative performance still future; direct transfer unsupported |
| Partial | Interpretation/discussion | Source-backed EDA and limitations complete; forecasting/error discussion remains future |
| Partial | Reproducibility | Tested pipelines, settings, hashes, seeds, source-code manifest and measured resource use; future experiment logs still required |
| Mandatory future gate | Independent Claude technical audit | After Phase 4 and before Phase 5; critical/high findings resolved and independently revalidated |
| Future | Inventory implications | Assumption registry, simulator and sensitivity report; no simulation or business savings claim yet |

The protocol defines experiments; documentation alone does not satisfy implementation,
tuning or forecasting-evaluation requirements. See [ROADMAP.md](ROADMAP.md) for gates.
Optional LightGBM, SHAP, MLflow and advanced uncertainty methods remain separate from
core academic requirements. Inventory and Power BI follow the audited forecasting core.
