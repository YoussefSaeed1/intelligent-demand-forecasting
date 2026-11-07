# Forecast metric definitions and coverage

Definitions implement the existing [experimental protocol](FORECASTING_EXPERIMENTAL_PROTOCOL.md).
Synthetic tests verify arithmetic and alignment; actual Phase 3 results additionally
require independent reconciliation of persisted validation predictions. See
[progress](PHASE3_PROGRESS.md) and the milestone gate JSON under `reports/forecasting/`.

For matched actual sales y and point predictions p, error e=p−y. Positive bias means
overforecasting. Data must be finite, nonnegative daily observed quantities; missing
actuals or predictions are not silently zero-filled or discarded.

| Metric | Formula | Units / interpretation |
|---|---|---|
| MAE | mean(abs(e)) | Sales units; absolute-error average |
| RMSE | sqrt(mean(e²)) | Sales units; large misses have greater influence |
| WAPE | 100 × sum(abs(e))/sum(abs(y)) | Percentage; volume-weighted pooled error |
| Bias units | mean(e) | Signed sales units; errors can cancel |
| Bias percent | 100 × sum(e)/sum(abs(y)) | Signed percentage; errors can cancel |
| MASE | MAE/q_abs | Unitless; training weekly absolute-difference scale |
| RMSSE | sqrt(mean(e²)/q_sq) | Unitless; training weekly squared-difference scale |

For each series at each origin, training length T and season m=7:

```text
q_abs = sum(t=m+1..T, abs(y_t - y_(t-m))) / (T-m)
q_sq  = sum(t=m+1..T, (y_t - y_(t-m))²) / (T-m)
```

Only origin-available training sales enter these scales, including recorded zeros.
The streaming implementation uses a seven-day buffer per series and checks complete
daily chronology from training start through origin. It rejects gaps, duplicates,
reordering, negative quantities and post-origin observations. Scales carry dataset,
training-start, training-end and season provenance; scoring rejects a mismatched window.

If T<=m or a scale is zero, the corresponding scaled metric is undefined. If
sum(abs(y))=0, WAPE and percentage bias are undefined, including a perfect all-zero
forecast. MAE, RMSE and bias units remain defined. Undefined values are null/None in
JSON (NaN only inside intermediate numerical tables), never zero or epsilon-adjusted.
Coverage records the defined and undefined series count separately for each metric.

## Alignment and populations

Evaluation accepts one dataset and one validation origin at a time. Dataset/series/date
business keys must align one-to-one, with exactly the declared series × 28 daily grid.
Unknown/duplicate/missing keys, wrong dates/origins/horizon steps, nonfinite values and
incompatible populations fail. There is no scorer access to the final holdout in Phase 3A.
This enforces comparable windows within a source; no raw-unit errors are pooled across
datasets with different units, histories or identifiers.

## Pooled versus macro summaries

- **Pooled MAE/RMSE/WAPE/bias:** calculate the formula once over all matched observations.
  Pooled WAPE is a ratio of summed errors to summed actuals, not the mean series WAPE.
- **Macro MAE/RMSE/WAPE/bias:** compute each series' metric, then take an arithmetic mean.
  Macro RMSE averages roots; pooled RMSE takes one root after pooling squared errors.
  Macro WAPE/percentage bias include only series where their denominators are positive.
- **Macro MASE/RMSSE:** average defined per-series scaled metrics; report eligible and
  total series. No arbitrary pooled training scale is invented. The pooled object
  intentionally contains the five unscaled/percentage metrics, not a fabricated MASE.

Equal series/day coverage makes macro and pooled MAE equal, but not generally RMSE or
WAPE. A fixture with equal absolute errors and one zero-actual series produces pooled
WAPE=100% and macro defined-series WAPE=50%; this tests the aggregation distinction,
not an empirical dataset result. Undefined series are explicitly counted.

The scorer returns the all-series result, each horizon step and each supplied demand
class. Every group has pooled and macro scores plus observation/series counts and
defined/undefined denominator coverage. Per-series records appear once in the all-series
result to avoid duplicating a large series table for every horizon. Fallback and clipped
observation counts are included. Classes must have origin-safe provenance; otherwise
all series are explicitly unclassified rather than inferred from future outcomes.

## Prediction policy and comparisons

Null scale columns are normalised without mutating the caller's data. An entirely
undefined population (including JSON null or nullable scalar inputs) remains undefined
and records its defined/undefined series counts. No epsilon or zero replaces a null scale.

Infrastructure clips negative point predictions to zero uniformly, retains raw values
and reports clipping incidence. It does not round expected sales to integers. Adapters
must flag any fallback. Phase 3B–3D now implement explicit eligibility and fallback
methods, retaining requested/actual delivery and reason for every series-origin case.

The selection objective remains the mean of the four folds' macro per-series MAE,
separately for each source. The registry's comparison eligibility gate rejects incomplete
runs and mismatched evaluation cohorts. Current benchmark reporting computes four-fold
summaries, fold dispersion, coverage and source-specific baseline-relative improvement,
with zero-baseline ratios undefined. Pooled summaries across origins use summed errors
and quantities rather than averaging roots or ratios. Weekly leaf-level
RMSSE is not official hierarchical M5 WRMSSE or a leaderboard reproduction.
