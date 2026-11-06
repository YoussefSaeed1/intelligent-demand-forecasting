# Phased roadmap

| Phase | Deliverables | Acceptance criteria | Depends on |
|---|---|---|---|
| 0 Foundation | Package, config, tests, documentation, environment | Import/config check, Ruff, Pytest verified or concrete blockers recorded | Local interpreter/access |
| 1 Acquisition and validation — COMPLETE (2026-11-06) | Acquired sources, hashes, profiles, canonical Parquet, independent audits, readiness review | Both independent gates passed and hashes rebound to current files; 60 tests/Ruff/pip check passed; documented limitations retained | 0; manual competition access and local acquisition |
| 2 Cleaning and EDA — NOT STARTED | Auditable cleaning policies and training-only EDA | Raw immutable; exclusions and sales limitations documented; separately authorised work | Closed Phase 1 gates and explicit instruction to start Phase 2 |
| 3 Baselines and protocol | Frozen horizon/splits, naive/seasonal naive, metric tests, rolling folds | No leakage; denominator/zero cases tested; test holdout protected | 2 |
| 4 Statistical and ML comparison | Feature pipeline, statistical and ML models, systematic search | Same evaluation windows; search logs and reproducible configs; no test tuning | 3 |
| 5 Final evaluation and discussion | Frozen model test evaluation, comparison, cross-dataset feasibility evidence | Required metrics/coverage; limitations and failed methods reported; conclusions supported | 4 |
| 6 Inventory scenarios | Defined simulator, assumption registry, sensitivity study | Event ordering and information timing tested; simulated labels; comparable policies | 5 |
| 7 BI and submission | Validated exports, four-page Power BI report, final writeup/presentation | Dashboard totals reconcile; sources and academic traceability complete | 5 and 6 |

Optional after core acceptance: LightGBM expansion, SHAP, MLflow and advanced uncertainty
methods. They must not displace academic requirements. Phase 0 does not authorise or
automatically begin dataset downloads or Phase 1 analysis.

Phase 1 closure (2026-11-06): both datasets passed independent persisted-file audits.
Store Item additionally passed exhaustive per-date/per-series coverage and row-level
quantity comparison. Its generic missing-date warning was informational; no gap exists.
M5's existing full audit was preserved and rebound by current source/Parquet hashes,
without rerunning its transformation. Remaining warnings are price availability and
sales-as-demand limitations. Future modelling must apply the cross-dataset protocol in
EXPERIMENTAL_DESIGN.md. These are documented limitations, not failed Phase 1 gates.
Fixture tests remain separate from empirical evidence. Phase 2 has not started.
