# Forecasting experimental protocol — proposed, not executed

Phase 2 defines daily 28-step sales forecasting independently for Store Item and M5.
No forecasting estimator, feature matrix, tuning search or prediction experiment has
been executed. Date plans and metric functions are implemented and unit-tested;
the experiments below remain future work requiring explicit authorisation.

## Task, population and horizon

Use all 500 Store Item and 30,490 M5 published store/product series. Predict expected
unit sales for each of the next 28 calendar days, with no actual-target updating within
that window. Four complete weeks give identical weekday exposure and a common planning
task across sources. This is a deliberate common benchmark, not Store Item's official
90-day competition task or a claim to reproduce M5 leaderboard scoring. A 28-day task
does not identify the optimal inventory lead time or test a full annual cycle.

Daily keys are dataset/date/store/product. Keep source namespaces separate. Do not merge
histories, infer cross-source product matches, or train a transferred model without a
new compatibility and source-only evaluation design. Store Item's competition test has
no observed sales and cannot be scored. M5 evaluation/validation CSV overlap is one
history, never concatenated. Use the audited canonical files without silent corrections.

## Date-only expanding-origin design

Initial training begins at the source's first labelled date. EDA ends before validation.
Each origin uses all dates through the origin inclusively; targets begin the next day.
There is no gap. Later validation folds may use earlier folds' actual observations as
training, reflecting information available at each new origin. Every compared model
uses the same 28 dates and series for that fold. No random row-level split is permitted.

| Dataset | Initial EDA/training start | Initial training end | Final test origin | Final test |
|---|---|---|---|---|
| Store Item | 2013-01-01 | 2017-08-13 | 2017-12-03 | 2017-12-04–2017-12-31 |
| M5 | 2011-01-29 | 2016-01-03 | 2016-04-24 | 2016-04-25–2016-05-22 |

| Fold | Store Item origin | Store Item validation | M5 origin | M5 validation |
|---|---|---|---|---|
| 1 | 2017-08-13 | 2017-08-14–2017-09-10 | 2016-01-03 | 2016-01-04–2016-01-31 |
| 2 | 2017-09-10 | 2017-09-11–2017-10-08 | 2016-01-31 | 2016-02-01–2016-02-28 |
| 3 | 2017-10-08 | 2017-10-09–2017-11-05 | 2016-02-28 | 2016-02-29–2016-03-27 |
| 4 | 2017-11-05 | 2017-11-06–2017-12-03 | 2016-03-27 | 2016-03-28–2016-04-24 |

These nonoverlapping target windows are generated from actual coverage by
`evaluation/design.py`, with H=28 and four folds in `configs/eda.yaml`; exact output is
[proposed_splits.json](../reports/eda/proposed_splits.json). The fixed design was applied
before target EDA. Four adjacent origins cover a limited seasonal range; report this
limitation and fold dispersion. They are not four independent random replications.
The [forecasting toolbox](https://otexts.com/fpp3/toolbox.html) describes chronological,
multi-step time-series cross-validation and simple forecast benchmarks.

Final test targets remain quarantined from detailed EDA, feature selection, search and
model choice. Previously known Phase 1 integrity totals and label-free price coverage
are explicitly documented exceptions, not evidence of test forecasting performance.
After validation fixes all choices, refit through the final origin and evaluate once
in Phase 4. Do not revise the selected model from the final result. Any necessary
post-test investigation is labelled exploratory and requires a new holdout to establish
fresh confirmatory performance.

## Feature and information contracts for later implementation

- All sales lags and rolling summaries are shifted and computed from origin-available
  observations. Fit scaling, encoders, imputers and feature selection separately in
  each fold. Never compute full-history statistics before splitting.
- Primary ML strategy: fit a one-step global regressor separately per dataset, then
  recurse for 28 days using its own predictions for post-origin lag values. No actual
  sales inside the forecast window enter later steps. Optional direct/horizon models
  are separate declared experiments with origin-available features and equal windows.
- Date/weekday/month and deterministic calendar rules are known ahead. M5 event/SNAP
  fields require a documented publication-availability assumption before use; including
  a future row in a competition calendar alone does not prove operational availability.
- Default price features use observations recorded by the origin, with explicit missing
  indicators. No future observed sell price, backwards fill, zero-price substitution or
  future first-sale/last-sale marker is allowed. A separately labelled known-future-price
  scenario requires evidence, not an implicit assumption. Store Item has no price field.
- Hierarchy/IDs may be used as static attributes if their existence is known at origin.
  The published benchmark universe is fixed for evaluation; metadata does not reveal
  future targets. Report cold-start coverage and this published-universe assumption.
- Define ADI/CV² strata using initial EDA training for fixed comparisons, or origin
  training for explicitly dynamic strata. Never classify using validation/test outcomes.
- Generate point forecasts without integer rounding. Predeclare nonnegative clipping
  for every method; retain raw prediction diagnostics and report clipping incidence.
  No outlier deletion or price/sales imputation is authorised by this protocol.

## Model families and feasibility

| Planned family | Rationale from EDA | Required limits / fallback |
|---|---|---|
| Naive | Essential persistence reference for both sources | Last observed value repeated across H |
| Weekly seasonal naive | Strong weekday contrasts, particularly Store Item | Repeat the last known 7-day pattern, including post-day-7 recursion |
| Moving average | Simple level smoothing reference | Trailing 7 or 28 days; select on validation only |
| ETS | Regular Store Item level/weekly pattern; selected regular M5 histories | Weekly seasonality; additive form admits zeros; no multiplicative zero workaround |
| ARIMA/SARIMA | Serial dependence and weekly structure justify a bounded comparator | Small weekly orders; no default 365-day seasonal state/search over every M5 series |
| Croston / SBA | M5's intermittent/lumpy groups justify occurrence/size benchmarks | Positive-history requirements and class-specific scores; not assumed universally best |
| TSB | Potentially changing occurrence rates or obsolescence | Update probability each period, retain zeros; validate smoothing parameters |
| Random Forest | Nonlinear lag/calendar comparator | Bounded depth/trees, projected training matrix, limited threads; record memory/time |
| Global LightGBM | Many related M5 series and sparse demand | Optional dependency; separate dataset models, leakage-safe recursive features, explicit budgets |

The original [ADI/CV² paper](https://doi.org/10.1057/palgrave.jors.2601841) supports
descriptive pattern conventions, not an empirical winner on these files. The
[TSB paper](https://doi.org/10.1016/j.ejor.2011.05.018) motivates updating occurrence
probability during zero runs. Store Item's 500 smooth series justify seasonal/statistical
comparators; M5's 16 all-zero and 5 single-positive EDA histories require explicit
eligibility/fallback behaviour. For insufficient history or a numerical fitting failure,
use the predeclared weekly seasonal naive fallback (zero for an all-zero known history),
flag the fallback and report both delivered-system and native-method coverage. Keep
all series in the primary benchmark; do not drop difficult future targets.

Global sharing is within each source. A few representative traces are not a basis for
full-population model claims. If an expensive M5 statistical comparator cannot cover
all series, predeclare a reproducible training-pattern/store-stratified subset and seed
before generating its scores. Evaluate every compared method on that same subset and
report the separate population coverage. Keep a full-population baseline/global track.

## Selection and optimisation plan

Primary selection objective: mean across four folds of macro per-series MAE, separately
for each dataset. This gives each series equal weight within a source. Report pooled
WAPE/RMSE and pattern/store/horizon scores as secondary outcomes, not substitute search
objectives chosen after seeing rankings. Refit each candidate at each origin.

Proposed initial search budget for Phase 4: at most 30 seeded random configurations per
global ML family and source, plus fixed baseline candidates. Bound per-series statistical
search to a small documented order/smoothing grid. Before execution, freeze actual
parameter spaces, early-stopping rules and resource caps in experiment config. Initial
resource caps: four CPU threads, two simultaneous workers maximum, 8 GiB combined worker
working set, 4 hours per Store Item family and 12 hours per M5 family. Stop cleanly at
the recorded cap; report evaluated trials and failures rather than imply exhaustive
search. No RTX/GPU speedup is presumed. LightGBM is not required to be installed in Phase 2.
Official [Random Forest documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)
and [LightGBM tuning guidance](https://lightgbm.readthedocs.io/en/stable/Parameters-Tuning.html)
inform later bounded implementation. These budgets are proposed and unexecuted.

Use the same folds for every selected configuration. The final test supplies no early
stopping, feature choice or hyperparameter feedback. Save seed 42, revision/dirty status,
exact source and feature-code hashes, packages, settings, input hashes, eligible series,
trial scores, failures, elapsed time and peak worker memory for every future experiment.
Repeated search on four folds creates selection bias; use the held-out test for the
final assessment and avoid certainty claims from validation scores alone.

## Metric definitions and aggregation

Let error e=p−y; positive bias means overforecasting. Compute metrics on aligned daily
keys with complete target/prediction coverage. A missing prediction is a failure or
declared fallback, not an omitted convenient case; missing actuals are explicitly
reported and cannot be invented. Current independent gates found no missing targets.

| Metric | Definition | Interpretation / limitation |
|---|---|---|
| MAE | mean(abs(e)) | Units; robust relative to squared errors, scale-dependent |
| RMSE | sqrt(mean(e²)) | Units; emphasises large misses, scale-dependent |
| WAPE | 100 × sum(abs(e))/sum(abs(y)) | Pooled absolute error per actual unit; dominated by high-volume series |
| Bias units | mean(e) | Signed units; opposing errors can cancel |
| Bias percent | 100 × sum(e)/sum(abs(y)) | Signed aggregate error per actual unit; cancellation remains |
| MASE | MAE/q_abs | Weekly scale-free error where training scale is positive |
| RMSSE | sqrt(mean(e²)/q_sq) | Weekly squared-scale error where training scale is positive |

For each series and origin, with training length T and m=7,
q_abs = sum(t=m+1..T, abs(y_t−y_(t−m)))/(T−m) and
q_sq = sum(t=m+1..T, (y_t−y_(t−m))²)/(T−m).
Use only that origin's training observations, including recorded zeros. If T<=m or
the corresponding scale is zero, report the scaled metric as undefined, with count
and coverage. If sum(abs(y))=0, WAPE and percentage bias are undefined even for perfect
zero predictions; MAE, RMSE and bias units remain valid. Never add an epsilon or replace
undefined metrics with zero. The [MASE paper](https://doi.org/10.1016/j.ijforecast.2006.03.001)
motivates training-based scaling. Definitions and edge cases are implemented in
`evaluation/metrics.py`, without generating any forecast.

Report each fold and final holdout separately. Macro MAE/RMSE/bias are arithmetic means
of per-series metrics; macro RMSE is a mean of roots, not pooled RMSE. Pooled RMSE takes
one root over all matched squared errors. Pooled WAPE is one ratio of aggregate sums;
it is not a simple mean of series WAPEs. Optional macro WAPE averages only defined
series and must publish that denominator and undefined count. Report macro MASE/RMSSE
over defined series, together with eligible/total counts. Every summary includes
series, observation and fallback coverage and horizon-step/initial-pattern breakdowns.

Do not pool unit errors across sources. Compare within-source improvements over the
same baseline, e.g. 1−model MAE/baseline MAE, flagging zero-baseline ratios undefined.
Replicated rankings across these two histories support methodological comparison,
not universal generalisation or direct transfer. The weekly leaf-level RMSSE above
is not official hierarchical M5 WRMSSE; no official leaderboard claim is authorised.
If confidence intervals for model differences are later added, pair the same targets
and account for date/series dependence; four folds do not justify an iid t-test.

## Acceptance gates and independent review

Before Phase 3: review Phase 2 evidence and explicitly authorise model implementation.
Before Phase 4 scoring: test availability/recursive feature boundaries and denominators;
freeze candidate spaces, objective, fallback and resource rules. After Phase 4 (Model
Optimisation & Evaluation), commission the independent Claude technical audit before
Phase 5. It covers integrity, features, leakage, experimental methodology, tuning,
statistical validity, code and reproducibility. Investigate and resolve all critical
and high-severity findings, then independently revalidate them before proceeding.
That future audit has not been conducted during Phase 2.
