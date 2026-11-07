# Phase 3C statistical and intermittent-demand methods

Phase 3B's complete independent gate passed before statistical production execution.
All methods use the unchanged four expanding origins and generate 28 daily point
forecasts without validation updating. Fixed initial settings are in
`configs/statistical.yaml`; no order search or systematic tuning is performed.

## Methods and initialisation

| Identifier | Configuration and initialisation | Evaluation population |
|---|---|---|
| ses | alpha=0.2; first observation initialises level; update through origin | Full |
| holt | alpha=0.2, trend smoothing=0.05; initial level first value, trend first difference | Full |
| holt_winters_additive | Weekly additive, damped trend phi=0.98, alpha=0.2, trend smoothing=0.05, seasonal gamma=0.05; first two weeks initialise components | Full |
| croston | Size and interval smoothing alpha=0.2; first positive size and first waiting interval initialise states | Full |
| sba | Croston with multiplicative correction 1-alpha/2 | Full |
| tsb | Positive-size alpha=0.2, occurrence beta=0.1; initial probability 1/first-positive period | Full |
| arima_100 | ARIMA(1,0,0) with intercept, stationarity enforced, maximum 80 likelihood iterations | Frozen statistical subset |
| sarima_100_100_7 | SARIMA(1,0,0)x(1,0,0,7) with intercept, stationarity enforced, maximum 80 likelihood iterations | Frozen statistical subset |

Six lightweight methods use vectorised independent series states. The global adapter
scope denotes one batch execution object, not shared statistical parameters across series.
ARIMA/SARIMA estimate coefficients separately per selected series using statsmodels
SARIMAX. This coefficient estimation is not hyperparameter/order optimisation.

For additive damped seasonal smoothing, let e=y-(l_previous+phi*b_previous+s_old).
The updates are l=l_previous+phi*b_previous+alpha*e,
b=phi*b_previous+alpha*trend_smoothing*e, s=s_old+gamma*e.
Forecasts use l + sum(phi^j,j=1..h)*b plus the most recent matching weekly seasonal state.
Thus horizon 7 uses the final observed day's updated seasonal state. The first 14
observations initialise components and all remaining training observations update them.
SES and Holt initialise from their first observations and use all remaining history.
See [FPP3 exponential smoothing](https://otexts.com/fpp3/exponential-smoothing.html).

Croston updates positive size and inter-arrival interval only on observed positive
sales; intervals include leading recorded zeros. SBA applies its fixed bias correction.
TSB updates occurrence probability every observed training day, and size only on positive
days. Its 28-step forecast holds the final probability/size expectation constant: an
unobserved future day is not treated as an observed zero. The hand-calculated fixture
`[0,0,2,0,0,4,0]` yields 0.8 (Croston), 0.72 (SBA) and 0.74088 (TSB).
Reference: [original TSB paper](https://pure.rug.nl/ws/portalfiles/portal/145394864/Intermittent_demand_Linking_forecasting_to_inventory_obsolescence.pdf).

## Eligibility, numerical failures and delivery

All-zero training histories deliver explicit zero forecasts. Croston/SBA require at
least two positives; TSB permits a single positive. Holt needs two observations and
weekly seasonal smoothing needs two complete cycles. ARIMA/SARIMA need at least 56
observations and two positives. Insufficient history, failed convergence or invalid
native results use the predeclared weekly seasonal naive fallback (naive below seven
observations), with requested method, actual method, reason and warning types persisted
per series. Corrupt/missing historical targets are quality failures, never fallbacks.

Every delivered series remains in evaluation. Common nonnegative clipping preserves raw
forecasts and reports clipping incidence; negative finite native forecasts are not
silently relabelled as another method. Native-only metrics and explicit delivery counts
supplement complete delivered-system metrics. A run with no native statistical forecasts
cannot be presented as a successfully fitted method.

## Reproducible computational population

Selected **53 of 500 Store Item series** and **51 of 30,490 M5 series** are frozen in
`artifacts/experiments/phase3/*_statistical_subset.json`. Selection uses only initial
training descriptors: seed 42, one member per nonempty pattern/store stratum, then
augmentation for missing volume-band/category/department/state marginals. Store Item
also covers all 50 products. These sets are fixed before statistical fits and reused
for all four origins. No model errors, convergence outcomes or future labels influence
selection. IDs, descriptor-file hashes and membership hashes are saved.

The unweighted subset deliberately represents minority strata and is not an unbiased
population estimate. Full-population and subset rankings remain separate. Baseline
predictions are projected from completed Phase 3B outputs onto exactly these IDs/dates;
no baseline refitting is necessary. Derived runs retain parent prediction hashes and
lineage, and become ineligible if their parent output is changed.

## Reference-library discrepancy resolved before production

The installed statsmodels 0.15.0 Holt-Winters `forecast()` recycled an older final
seasonal element in the seeded 100-observation regression fixture. Differences occurred
at horizons 7, 14, 21 and 28, with maximum 0.05626157766847939 units. Its retained level,
trend and seasonal states agree with this implementation; forecasting from those states
and the published equation agrees to 7.105427357601002e-15. The implementation retains
the updated final seasonal state and has explicit weekly-wrap tests. This is a
version-specific reference discrepancy, not a change to the approved evaluation design.

## Execution, budgets and evidence

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand.experiments.benchmark run --phase 3c
.\.venv\Scripts\python.exe -m intelligent_demand.evaluation.benchmark_audit --phase 3c
```

One worker runs at a time, four threads maximum, 2 GiB RSS and 1,800 seconds per model,
dataset and origin. Completed runs are reused; failed/interrupted attempts remain
excluded and restart separately. Detailed states, delivery records, predictions, metrics
and measured resources remain under ignored local artifacts. The completed independent
gate and actual results report are published only after all required runs reconcile.
