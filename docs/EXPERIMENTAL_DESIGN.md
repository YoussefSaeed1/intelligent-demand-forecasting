# Experimental design and verified dataset readiness

Phase 1 source and independent persisted-file gates are closed as of 2026-11-06.
Phase 2 EDA is now complete on the initial training prefixes. Forecasting feature
generation and fixed-configuration training are now implemented in authorised Phase 3;
tuning remains reserved for Phase 4. See [progress](PHASE3_PROGRESS.md).
The authoritative detailed plan is
[FORECASTING_EXPERIMENTAL_PROTOCOL.md](FORECASTING_EXPERIMENTAL_PROTOCOL.md), with exact
28-day split dates generated from coverage before detailed EDA. It supersedes the
earlier provisional settings below. See [EDA_FINDINGS.md](EDA_FINDINGS.md) for actual
training-period patterns; the Phase 1 readiness evidence below remains valid.

- Task: daily multi-step sales forecasting; provisional H=28 days. Finalise horizon,
  series selection, minimum history and exact date boundaries after schema validation,
  before comparing model outcomes. One-step updating is a separate experiment.
- Reserve the last fully labelled H days as the final test; use earlier expanding-window
  rolling origins for validation when coverage permits. Record origins, cutoffs, gaps,
  horizon and fold count in configuration. Never tune or select features on final test.
- Fit imputers, scalers, encoders and feature selection inside each training fold.
  Lag values must predate the origin; rolling windows must be shifted. Recursive forecasts
  use prior predictions after the origin, never actual held-out sales. Direct models use
  origin-available features. Calendar features can be known ahead; other covariates require
  an explicit availability contract. Backtest the actual intended forecasting procedure.
- Baselines: last observation and weekly seasonal naive where history supports them.
  Statistical candidates: exponential smoothing and suitable ARIMA-family models.
  ML candidates: scikit-learn regressors; LightGBM optional. Systematic search (grid,
  random or Optuna) uses the same validation folds and a declared budget and objective.
- Use identical origin/target windows and series sets for model comparisons. Record
  failures, coverage and excluded series; do not silently compare different subsets.
  Seeds, versions, configuration, Git revision and input hashes belong to every run.

## Metrics

For matched observations y and predictions p: MAE = mean(abs(p-y));
RMSE = sqrt(mean((p-y)^2)); WAPE = 100*sum(abs(p-y))/sum(abs(y));
signed bias in units = mean(p-y), positive for overforecasting.
Optional percentage bias = 100*sum(p-y)/sum(abs(y)).
If the WAPE or percentage-bias denominator is zero, report undefined with the count of
affected groups; never divide by an arbitrary epsilon. MAE/RMSE remain useful on zero
sales. Missing targets are excluded explicitly with coverage reported, not set to zero.
Declare pooled (volume-weighted) and macro-per-series summaries separately, plus
horizon-step summaries. Raw unit errors are not comparable across different scales.
Avoid MAPE as a primary metric with zeros. Any official M5 metric is additional and
requires independently verified weighting, scaling and hierarchy definitions.

## Cross-dataset evaluation

Run the same methodological protocol independently on each source, preserving
source-specific transformations. Compare relative gains over each source's baseline
with zero-baseline cases flagged undefined. Direct cross-dataset model transfer is
conditional on compatible features, targets, availability and units; otherwise report
it infeasible with evidence. Do not call replicated rankings proof of generalisation.

### Verified cross-dataset readiness (2026-11-06)

| Dimension | Store Item | M5 |
|---|---|---|
| Labelled historical dates | 2013-01-01–2017-12-31 | 2011-01-29–2016-05-22 |
| Historical days | 1,826 | 1,941 |
| Observations | 913,000 | 59,181,090 |
| Stores / products / series | 10 / 50 / 500 | 10 / 3,049 / 30,490 |
| Grain / target | Daily store/product observed unit sales | Daily store/product observed unit sales |
| Zero-sales observations | 1 (0.000109529%) | 40,241,819 (67.997766%) |
| Missing historical keys / target values | 0 / 0 | 0 / 0 |
| Duplicated business keys | 0 | 0 |
| Available source covariates | Store/product identifiers; calendar date | Store/product and hierarchy IDs; calendar/event/SNAP fields; historical weekly prices |
| Covariate missingness | Price/category absent; canonical nulls are structural | 12,299,413 missing historical prices (20.782674%); optional calendar event nulls retained |
| Seasonality potential | Multi-year daily coverage permits future weekly/annual assessment | Multi-year daily coverage plus event/calendar fields permits future assessment |

The seasonality-potential row records the Phase 1 coverage/schema assessment. Phase 2
has since produced training-prefix ACF, decomposition and trend diagnostics, documented
separately in EDA_FINDINGS.md. Phase 3 feature availability is documented in
[FEATURE_AVAILABILITY.md](FEATURE_AVAILABILITY.md).
Zero frequencies describe observed sales, not verified unconstrained demand.

Readiness decisions:

1. Independent model benchmarking: supported, with separate source adapters, namespace,
   configurations and matched model windows within each source. Document any M5 subset
   selected for compute feasibility; do not silently change the compared population.
2. Common horizons and metrics: supported for the planned H=28 daily multi-step task,
   MAE/RMSE/WAPE and signed bias. The sources' final labelled dates differ; identical
   relative windows do not mean identical calendar/economic conditions. A separate
   calendar-aligned design can use their 2013-01-01–2016-05-22 overlap if justified.
   Exact Phase 2 split dates are now recorded in the detailed protocol and split manifest,
   without using held-out outcomes to choose them.
3. Methodological replication/comparison: supported. Report source-specific performance,
   coverage, zero-denominator cases and relative improvement over each source's baseline.
   Distinguish pooled and macro-series results. Raw unit MAE/RMSE values do not establish
   which dataset generalises better, especially with different scales and sparsity.
4. Direct model transfer: not justified by current evidence and excluded from the default
   benchmark. A shared output schema is insufficient: no store/product identity alignment,
   physical-unit equivalence, common covariate availability or stable target distribution
   has been established. A future separately justified transfer study would need compatible
   origin-available inputs, explicit ID handling, source-only fitting or clearly declared
   target-training adaptation, and an untouched target test set. It must be labelled
   zero-shot transfer or adaptation appropriately, without tuning on the target test.

The 45,000 Store Item competition test rows have no observed labels and cannot serve as
ground truth for any metric or be included in its 913,000-row historical target panel.
M5 missing-price treatment, calendar-event encoding and covariate availability policies
remain documented decisions for later phases; Phase 1 did not impute or manufacture values.
Evidence: reports/data_quality/store_item_canonical_audit.json, m5_canonical_audit.json
and phase1_readiness.json. The current hashes bind both independent audits to local files;
the full M5 transformation was not repeated for this readiness review.

## Interpretation

Discuss uncertainty across series and origins, failure cases and scale sensitivity.
Treat feature attribution as explanatory association, not causality. Do not equate
observed sales with uncensored demand or simulated savings with realised business results.
