# Store Item: sales patterns and forecasting implications

## Executive summary

- Across all 500 series, 0.0001% of EDA observations are zero sales.
- The largest full-window descriptive class is smooth (500 series). Removing leading zeros changes 0 class assignments.
- The top 10% of products account for 16.28% of EDA sales units.

## Scope and holdout protection

All series are included; EDA targets cover **2013-01-01–2017-08-13** (843,000 observations). Four later 28-day validation windows and the final 28-day holdout were reserved before detailed exploration. Full-history figures below are Phase 1 reconciliation references, not model-selection evidence.

Full-history reference: 913,000 rows and 47,704,512 units, independently rechecked while scanning.

## Distribution, scale and concentration

EDA sales total: **43,666,945 units**. Exact empirical unit quantiles (inverse CDF): `{'0.5': 46, '0.9': 92, '0.95': 107, '0.99': 134, '0.999': 164, '1.0': 231}`. Median series coefficient of variation of all daily sales is 0.288. Largest observed quantities are retained in the largest_observations table; they are not automatically labelled errors or removed.

![Sales distribution](../figures/phase2/store_item_distribution.png)
![Daily and monthly trends](../figures/phase2/store_item_trends.png)
![Product concentration](../figures/phase2/store_item_concentration.png)
![Store comparisons](../figures/phase2/store_item_stores.png)

## Calendar structure, trend and volatility

Within complete weeks, Sunday has the highest average sales ratio (1.192); Monday has the lowest (0.791). The table contains 95% pointwise intervals from 500 moving-block bootstrap replicates (4 weeks/block, fixed seed). These describe historical stability under block-resampling assumptions, not causal weekday effects or confirmatory multiple tests.

Aggregate diagnostic weekly strength is 0.976; annual strength after weekly removal is 0.993. These are log1p aggregate STL variance-ratio diagnostics, not forecast scores. The 365-day annual approximation does not exactly align leap days. Monthly indices use complete years and normalise by each year's daily mean to reduce level-trend confounding.

Median per-series lag-7 correlation: 0.727; lag-365: 0.546. Level correlations can reflect trend. The aggregate ACF figure also shows first-differenced log sales, with no misleading iid significance bands.

![Calendar patterns](../figures/phase2/store_item_calendar_patterns.png)
![Diagnostics](../figures/phase2/store_item_diagnostics.png)
![Volatility](../figures/phase2/store_item_volatility.png)

## Series-level intermittency

ADI is observed days divided by positive-sale days. CV² uses sample variance of positive sale sizes divided by their squared mean (ddof=1). Thresholds are 1.32 and 0.49; equality enters the high group. All-zero and one-positive histories remain separate undefined cases. This descriptive daily-sales convention is inspired by Syntetos–Boylan–Croston, not a universal model-selection rule; pre-launch zeros, censoring and temporal aggregation can change classes.

| Pattern | Full EDA window | First-positive-to-EDA-end sensitivity |
|---|---:|---:|
| smooth | 500 | 500 |
| erratic | 0 | 0 |
| intermittent | 0 | 0 |
| lumpy | 0 | 0 |
| all_zero | 0 | 0 |
| insufficient_positive_history | 0 | 0 |

The active-span sensitivity removes leading zeros analytically, without changing source observations or asserting actual availability. No trailing-zero truncation is used.

![Intermittency](../figures/phase2/store_item_intermittency.png)
![Zeros and variability](../figures/phase2/store_item_zeros_variability.png)
![Representative illustrations](../figures/phase2/store_item_representatives.png)

Illustrations select the median-ranked series within each class, ordered by zero percentage, mean units and series ID. They are not a random sample or the basis of population findings; all per-series statistics use the full published series population.

## Evidence and reproducibility

All chart inputs and analytical tables are in `tables/store_item/` as compressed Parquet. The adjacent results JSON records scope, settings, split dates, reconciliations and source hashes. Figures are exported as PNG and SVG. Inputs are hashed before and after; no raw/canonical file changes.

Methods: [Syntetos–Boylan–Croston classification](https://doi.org/10.1057/palgrave.jors.2601841); [forecast accuracy and rolling-origin evaluation](https://otexts.com/fpp3/toolbox.html). No forecasting model or hyperparameter search was run.
