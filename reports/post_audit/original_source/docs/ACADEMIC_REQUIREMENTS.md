# Academic traceability checklist

Status distinguishes verified empirical evidence from proposed forecasting work.
Offline test fixtures are not forecasting results on the real datasets.

| Status | Required item | Current evidence / remaining work |
|---|---|---|
| Complete | Two published datasets | DATASETS.md; independent audits in reports/data_quality; both source adapters and hashes |
| Partial | Source documentation | Provenance/layout documented; detailed competition terms still require user's recorded review |
| Complete | Data quality assessment | Independent source-to-Parquet audits, VALIDATION.md, immutable hash checks |
| Partial | Cleaning/preprocessing | Canonical representation verified; zeros/null prices preserved; any future preprocessing must remain fold-safe |
| Complete | Training-prefix EDA | EDA_FINDINGS.md, dataset reports, all-series ADI/CV², 39 tables and 29 enhanced PNG/SVG figure pairs |
| Design complete | Explicit forecast horizon | 28 daily steps; exact dates and rationale in FORECASTING_EXPERIMENTAL_PROTOCOL.md |
| Design complete | Chronological train/validation/test | Four expanding rolling origins and final protected holdout; date-only construction tested |
| Complete for validation | Relevant error metrics | Independently reconciled real predictions; pooled/macro/horizon/class MAE/RMSE/WAPE/bias and weekly MASE/RMSSE; explicit undefined denominators |
| Complete | Appropriate baseline implementation | Five baselines, four origins, full populations; BASELINE_RESULTS.md and Phase 3B gate |
| Implemented and executed | Comparison of forecasting approaches | Eight statistical/intermittent and two global ML methods; exact population rules; Phase 3C/3D gates and final consolidation |
| Future | Systematic hyperparameter optimisation | Freeze spaces/caps; record validation trials, failures and selected settings in Phase 4 |
| Validation implemented; final test future | Evaluation/comparison | Four unchanged origins, full and explicitly matched subsets; final holdout only after choices freeze in Phase 4 |
| Validation implemented | Cross-dataset evaluation where feasible | Separate source-specific scores and baseline-relative comparisons; direct transfer unsupported |
| Validation discussion implemented | Interpretation/discussion | Actual errors, sparse-demand coverage, bias, horizon, class and resource limitations; no significance claim |
| Implemented locally | Reproducibility | Fixed configurations, seeds, package/code/source hashes, frozen splits, immutable predictions and registry; no upload or new commit |
| Mandatory future gate | Independent Claude technical audit | After Phase 4 and before Phase 5; critical/high findings resolved and independently revalidated |
| Future | Inventory implications | Assumption registry, simulator and sensitivity report; no simulation or business savings claim yet |

The protocol defines experiments; documentation alone does not satisfy implementation,
tuning or forecasting-evaluation requirements. See [ROADMAP.md](ROADMAP.md) for gates.
CPU LightGBM is implemented; optional SHAP, MLflow and advanced uncertainty remain separate from
core academic requirements. Inventory and Power BI follow the audited forecasting core.
