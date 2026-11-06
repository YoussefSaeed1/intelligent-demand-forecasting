# Intelligent Demand Forecasting & Inventory Optimisation

Individual postgraduate Data Science diploma project, Cairo University.

## Problem statement

Retail sales uncertainty complicates replenishment. A reproducible comparison of
statistical and machine learning forecasts can establish which methods are useful for
defined forecasting tasks and explore planning implications under transparent assumptions.

## Research questions and objectives

1. How do naive, statistical and ML approaches compare on the same daily horizons and windows?
2. Which data-quality and feature choices affect forecast reliability across series?
3. Does the relative ranking of methods hold on a second independently sourced dataset?
4. How sensitive are simulated service and inventory cost tradeoffs to forecast policy,
   lead time and assumed operating parameters?

Build documented ingestion, profiling and cleaning; establish baselines; perform
systematic chronological tuning; compare and interpret models; retain reproducible
evidence; investigate inventory implications without claiming observed savings.

## Scope and exclusions

Use the two Kaggle datasets documented in DATASETS.md, subject to verified access and
terms. Prioritise manageable, explicitly selected series if full M5 scale is impractical.
No live deployment, cloud services, databases, causal business claims or actual stock
reconstruction. Phase 0 implements only packaging, configuration, tests and plans.

## Methodology and experimental design

Profile separately, verify schema, clean with auditable policies, explore training data,
engineer available-at-origin features, evaluate baselines, then statistical and ML models.
The provisional horizon is 28 daily steps; freeze it and split dates after inspecting
coverage and before test evaluation. Use expanding rolling-origin validation and one
untouched final chronological test window. See EXPERIMENTAL_DESIGN.md for metric and
leakage contracts. Use random/grid search or Optuna only inside validation folds.

## Evaluation and cross-dataset interpretation

Report MAE, RMSE, WAPE and signed forecast bias with explicit aggregation and zero
handling. Compare paired errors on identical series/windows within each source. Consider
source-specific official metrics only after verifying their definitions and input needs.
Cross-dataset evaluation primarily replicates the pipeline and compares relative baseline
improvement; raw errors are scale-dependent. Direct transfer requires a separate
compatibility argument and source-only training; it is not assumed valid.

## Expected deliverables

Verified provenance and quality reports; source adapters and canonical schema; EDA;
features; baseline/statistical/ML implementations; search records; reproducible backtests;
comparison and interpretation; scenario simulation; Power BI-ready exports and report;
technical documentation and academic presentation. These are planned, not achieved results.

## Limitations and risks

Sales censoring, sparse series, structural zeros, unavailable future covariates, differing
hierarchies, compute limits and changing package support can constrain conclusions.
Unknown stock, lead times and costs require sensitivity analysis. Dataset restrictions
may limit redistribution. A single observed history limits causal and generalisation claims.
