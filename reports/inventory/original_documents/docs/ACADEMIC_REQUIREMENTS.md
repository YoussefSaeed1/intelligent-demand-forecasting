# Academic traceability checklist

Current status after the 2026-11-08 internal audit and post-audit engineering remediation.
Original Phase 4 results remain frozen; historical checklist bytes are preserved in
`reports/post_audit/original_source/docs/ACADEMIC_REQUIREMENTS.md`.
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
| Complete; independently recalculated internally | Systematic hyperparameter optimisation | 27 fixed cases, 108 fold runs; original configurations and validation predictions preserved |
| Complete; fixed final assessment preserved | Evaluation/comparison | Four unchanged origins and eight frozen final cases; snapshot-only internal reconciliation, no canonical final rescan |
| Validation implemented | Cross-dataset evaluation where feasible | Separate source-specific scores and baseline-relative comparisons; direct transfer unsupported |
| Validation discussion implemented | Interpretation/discussion | Actual errors, sparse-demand coverage, bias, horizon, class and resource limitations; no significance claim |
| Metric reconciliation verified; prediction reproduction partial | Reproducibility | All 332 validation/eight final metric cases reconciled; sampled validation replay exact; clean-room reproduction unverified; explicit historical-root mapping |
| Mandatory future gate | Independent Claude technical audit | After Phase 4 and before Phase 5; critical/high findings resolved and independently revalidated |
| Future | Inventory implications | Assumption registry, simulator and sensitivity report; no simulation or business savings claim yet |

The Phase 4 checkpoint is `54a689b7cb07970556bbf2fc164adf934307eab8`.
See [internal audit](CODEX_INTERNAL_AUDIT_PHASES_0_4.md),
[remediation report](POST_AUDIT_REMEDIATION_REPORT.md) and
[Claude handoff](CLAUDE_AUDIT_HANDOFF.md) for current verification and limitations.
A verified local same-device evidence copy mitigates accidental loss; it is not an
independent off-device backup. The independent Claude gate and Phase 5 remain unstarted.

The protocol defines experiments; documentation alone does not satisfy implementation,
tuning or forecasting-evaluation requirements. See [ROADMAP.md](ROADMAP.md) for gates.
CPU LightGBM is implemented; optional SHAP, MLflow and advanced uncertainty remain separate from
core academic requirements. Inventory and Power BI follow the audited forecasting core.
