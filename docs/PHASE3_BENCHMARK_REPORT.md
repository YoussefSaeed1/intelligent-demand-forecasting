# Phase 3 benchmark report

Status: COMPLETE; scientific and automated gates passed.

## Verified scope

Thirteen methods share full-population evaluation (500 Store Item and 30,490 M5 series). Fifteen share the frozen 53/51-series statistical subsets, including ARIMA and SARIMA. All use the four approved 28-day validation windows. Subset means are unweighted, deliberately stratified and cannot estimate population performance. Projected forecasts reuse fitted full-population models without refitting.

The independent final audit verified 224 saved evaluations and 45,296,160 forecast records, including subset projections of the same underlying forecasts. No final holdout target was used.

## Findings

store_item: lightgbm has the lowest four-fold mean macro MAE (6.308040 units), 31.10% below Seasonal Naive and 59.79% below Naive on the full matched population.

store_item: random_forest MAE 6.885316; best full-population statistical method holt_winters_additive 7.701650. ML is lower by 10.60%. These are fixed initial fits, not tuned-family ceilings.

store_item: random_forest beats holt_winters_additive in 4/4 validation origins; this descriptive count does not imply statistical significance.

store_item: lightgbm MAE 6.308040; best full-population statistical method holt_winters_additive 7.701650. ML is lower by 18.09%. These are fixed initial fits, not tuned-family ceilings.

store_item: lightgbm beats holt_winters_additive in 4/4 validation origins; this descriptive count does not imply statistical significance.

store_item, initial class smooth: lowest mean class macro MAE is lightgbm (6.308040); Seasonal Naive 9.154964, RF 6.885316, LightGBM 6.308040. Class populations are fixed, not selected by forecast errors.

store_item, matched 53-series subset: lightgbm has lowest MAE 6.508391. This is a separate descriptive comparison, not a population estimate.

store_item: lightgbm fold MAEs range 6.157555–6.492088; four adjacent windows provide no independent-season or significance claim.

store_item: lightgbm mean MAE days 1–7 is 6.402937, days 22–28 6.281160. Horizon deterioration is assessed empirically, not assumed monotonic.

store_item: the top 10% of series by initial-training volume contribute 18.53% of validation sales, 14.47% of absolute error and 19.70% of squared error for lightgbm. Pooled RMSE can therefore emphasise high-volume misses; macro MAE gives series equal weight.

store_item: undefined series-origin metrics for lightgbm: bias_percent=0, bias_units=0, mae=0, mase=0, rmse=0, rmsse=0, wape_percent=0. Nulls remain excluded only from that metric's macro mean, with coverage reported.

m5: random_forest has the lowest four-fold mean macro MAE (1.027612 units), 15.21% below Seasonal Naive and 24.03% below Naive on the full matched population.

m5: random_forest MAE 1.027612; best full-population statistical method tsb 1.042455. ML is lower by 1.42%. These are fixed initial fits, not tuned-family ceilings.

m5: random_forest beats tsb in 4/4 validation origins; this descriptive count does not imply statistical significance.

m5: lightgbm MAE 1.070783; best full-population statistical method tsb 1.042455. ML is higher by 2.72%. These are fixed initial fits, not tuned-family ceilings.

m5: lightgbm beats tsb in 0/4 validation origins; this descriptive count does not imply statistical significance.

m5, initial class all_zero: lowest mean class macro MAE is tsb (0.701693); Seasonal Naive 0.811942, RF 0.738653, LightGBM 0.707661. Class populations are fixed, not selected by forecast errors.

m5, initial class erratic: lowest mean class macro MAE is random_forest (3.543246); Seasonal Naive 4.458991, RF 3.543246, LightGBM 3.979721. Class populations are fixed, not selected by forecast errors.

m5, initial class insufficient_positive_history: lowest mean class macro MAE is moving_average_28 (0.540306); Seasonal Naive 0.608929, RF 0.579245, LightGBM 0.604942. Class populations are fixed, not selected by forecast errors.

m5, initial class intermittent: lowest mean class macro MAE is moving_average_28 (0.761734); Seasonal Naive 0.882493, RF 0.762611, LightGBM 0.782083. Class populations are fixed, not selected by forecast errors.

m5, initial class lumpy: lowest mean class macro MAE is random_forest (1.561011); Seasonal Naive 1.851397, RF 1.561011, LightGBM 1.639166. Class populations are fixed, not selected by forecast errors.

m5, initial class smooth: lowest mean class macro MAE is random_forest (2.765242); Seasonal Naive 3.458654, RF 2.765242, LightGBM 2.957744. Class populations are fixed, not selected by forecast errors.

m5, matched 51-series subset: moving_average_28 has lowest MAE 2.147421. This is a separate descriptive comparison, not a population estimate.

m5: random_forest fold MAEs range 1.000623–1.046144; four adjacent windows provide no independent-season or significance claim.

m5: random_forest mean MAE days 1–7 is 1.005928, days 22–28 1.027402. Horizon deterioration is assessed empirically, not assumed monotonic.

m5: the top 10% of series by initial-training volume contribute 46.16% of validation sales, 33.43% of absolute error and 71.59% of squared error for random_forest. Pooled RMSE can therefore emphasise high-volume misses; macro MAE gives series equal weight.

m5: undefined series-origin metrics for random_forest: bias_percent=9409, bias_units=0, mae=0, mase=26, rmse=0, rmsse=26, wape_percent=9409. Nulls remain excluded only from that metric's macro mean, with coverage reported.

## Matched model comparisons

| Dataset | Population | Model | Series/fold | Macro MAE | Pooled RMSE | WAPE % | Bias units | Macro MASE | Macro RMSSE | Fallback % |
|---|---|---|---|---|---|---|---|---|---|---|
| m5 | full | random_forest | 30490 | 1.027612 | 2.308980 | 75.8098 | -0.020690 | 1.754438 | 0.869240 | 0.0000 |
| m5 | full | moving_average_28 | 30490 | 1.033779 | 2.342793 | 76.2647 | -0.051500 | 1.664832 | 0.870662 | 0.0000 |
| m5 | full | tsb | 30490 | 1.042455 | 2.365638 | 76.9047 | -0.027338 | 1.672317 | 0.874782 | 0.0213 |
| m5 | full | ses | 30490 | 1.054442 | 2.386738 | 77.7891 | -0.003226 | 1.699567 | 0.892535 | 0.0213 |
| m5 | full | lightgbm | 30490 | 1.070783 | 2.451283 | 78.9946 | -0.003709 | 1.794896 | 0.885499 | 0.0000 |
| m5 | full | seasonal_moving_average | 30490 | 1.071424 | 2.433870 | 79.0419 | -0.051500 | 1.707211 | 0.941723 | 0.0000 |
| m5 | full | sba | 30490 | 1.087810 | 2.370838 | 80.2507 | -0.051973 | 1.744396 | 0.901449 | 0.0320 |
| m5 | full | holt_winters_additive | 30490 | 1.111869 | 2.547450 | 82.0256 | -0.023811 | 1.795516 | 0.950492 | 0.0213 |
| m5 | full | croston | 30490 | 1.122368 | 2.410585 | 82.8002 | +0.092865 | 1.798699 | 0.910573 | 0.0320 |
| m5 | full | holt | 30490 | 1.171588 | 2.715957 | 86.4313 | +0.081622 | 1.864344 | 0.973206 | 0.0213 |
| m5 | full | seasonal_naive | 30490 | 1.212000 | 2.859958 | 89.4125 | -0.077700 | 1.877038 | 1.136993 | 0.0000 |
| m5 | full | naive | 30490 | 1.352632 | 3.201968 | 99.7874 | +0.222429 | 2.043041 | 1.134538 | 0.0000 |
| m5 | full | zero | 30490 | 1.355514 | 3.842455 | 100.0000 | -1.355514 | 1.597677 | 1.075942 | 0.0000 |
| m5 | statistical_subset | moving_average_28 | 51 | 2.147421 | 4.546687 | 61.1104 | -0.062850 | 26.415785 | 2.144627 | 0.0000 |
| m5 | statistical_subset | seasonal_moving_average | 51 | 2.159926 | 4.635540 | 61.4662 | -0.062850 | 26.512844 | 2.238187 | 0.0000 |
| m5 | statistical_subset | tsb | 51 | 2.178311 | 4.691671 | 61.9894 | +0.035344 | 26.209906 | 2.157618 | 5.3922 |
| m5 | statistical_subset | ses | 51 | 2.191595 | 4.719874 | 62.3674 | +0.093700 | 27.388041 | 2.154842 | 5.3922 |
| m5 | statistical_subset | sba | 51 | 2.201789 | 4.600412 | 62.6575 | -0.248413 | 28.263793 | 2.352614 | 9.8039 |
| m5 | statistical_subset | random_forest | 51 | 2.232426 | 5.567166 | 63.5294 | +0.193356 | 29.559020 | 2.111502 | 0.0000 |
| m5 | statistical_subset | holt_winters_additive | 51 | 2.257689 | 4.725020 | 64.2483 | +0.009379 | 29.125204 | 2.274406 | 5.3922 |
| m5 | statistical_subset | lightgbm | 51 | 2.266888 | 5.047845 | 64.5101 | +0.012822 | 29.414021 | 2.171672 | 0.0000 |
| m5 | statistical_subset | croston | 51 | 2.277661 | 4.726793 | 64.8167 | +0.114197 | 28.281343 | 2.360052 | 9.8039 |
| m5 | statistical_subset | sarima_100_100_7 | 51 | 2.431020 | 5.361068 | 69.1809 | -0.269409 | 28.270091 | 2.367653 | 9.8039 |
| m5 | statistical_subset | holt | 51 | 2.489309 | 5.426109 | 70.8396 | +0.262468 | 30.085030 | 2.347550 | 5.3922 |
| m5 | statistical_subset | arima_100 | 51 | 2.517115 | 5.721930 | 71.6309 | -0.339455 | 28.369918 | 2.402239 | 10.2941 |
| m5 | statistical_subset | seasonal_naive | 51 | 2.601891 | 6.809097 | 74.0434 | -0.058123 | 29.168566 | 2.579908 | 0.0000 |
| m5 | statistical_subset | naive | 51 | 2.714636 | 6.032823 | 77.2519 | +0.289916 | 27.307678 | 2.469013 | 0.0000 |
| m5 | statistical_subset | zero | 51 | 3.514006 | 8.971984 | 100.0000 | -3.514006 | 26.408585 | 2.571068 | 0.0000 |
| store_item | full | lightgbm | 500 | 6.308040 | 8.178519 | 10.3382 | +0.037028 | 0.768766 | 0.754176 | 0.0000 |
| store_item | full | random_forest | 500 | 6.885316 | 8.990947 | 11.2843 | +0.545272 | 0.837251 | 0.821911 | 0.0000 |
| store_item | full | holt_winters_additive | 500 | 7.701650 | 10.242293 | 12.6222 | -0.859491 | 0.935200 | 0.921467 | 0.0000 |
| store_item | full | seasonal_moving_average | 500 | 8.086652 | 10.599769 | 13.2532 | +2.817554 | 0.972851 | 0.949943 | 0.0000 |
| store_item | full | seasonal_naive | 500 | 9.154964 | 12.023970 | 15.0041 | +0.797071 | 1.111900 | 1.091963 | 0.0000 |
| store_item | full | sba | 500 | 9.195172 | 12.160157 | 15.0700 | -2.151480 | 1.089614 | 1.065296 | 0.0000 |
| store_item | full | moving_average_28 | 500 | 9.538296 | 12.548730 | 15.6323 | +2.817554 | 1.126897 | 1.090525 | 0.0000 |
| store_item | full | croston | 500 | 9.892034 | 12.959967 | 16.2120 | +4.389086 | 1.169177 | 1.125963 | 0.0000 |
| store_item | full | tsb | 500 | 9.892034 | 12.959967 | 16.2120 | +4.389086 | 1.169177 | 1.125963 | 0.0000 |
| store_item | full | ses | 500 | 9.892034 | 12.959967 | 16.2120 | +4.389086 | 1.169177 | 1.125963 | 0.0000 |
| store_item | full | holt | 500 | 10.440839 | 13.736397 | 17.1115 | +3.871962 | 1.238648 | 1.192145 | 0.0000 |
| store_item | full | naive | 500 | 15.689214 | 20.440164 | 25.7130 | +12.858929 | 1.833140 | 1.665480 | 0.0000 |
| store_item | full | zero | 500 | 61.016571 | 68.232190 | 100.0000 | -61.016571 | 7.013843 | 5.623182 | 0.0000 |
| store_item | statistical_subset | lightgbm | 53 | 6.508391 | 8.481212 | 10.1371 | -0.132496 | 0.771729 | 0.757506 | 0.0000 |
| store_item | statistical_subset | random_forest | 53 | 7.149214 | 9.406636 | 11.1352 | +0.389910 | 0.844683 | 0.828908 | 0.0000 |
| store_item | statistical_subset | holt_winters_additive | 53 | 7.973448 | 10.645761 | 12.4190 | -0.838576 | 0.941530 | 0.927839 | 0.0000 |
| store_item | statistical_subset | seasonal_moving_average | 53 | 8.318144 | 10.980170 | 12.9559 | +2.909198 | 0.975568 | 0.952341 | 0.0000 |
| store_item | statistical_subset | sarima_100_100_7 | 53 | 8.932206 | 11.781811 | 13.9123 | -4.814757 | 1.046486 | 1.031599 | 0.0000 |
| store_item | statistical_subset | seasonal_naive | 53 | 9.401954 | 12.458827 | 14.6440 | +0.650943 | 1.109570 | 1.091582 | 0.0000 |
| store_item | statistical_subset | sba | 53 | 9.595132 | 12.769922 | 14.9449 | -2.319934 | 1.104238 | 1.082829 | 0.0000 |
| store_item | statistical_subset | moving_average_28 | 53 | 9.984273 | 13.166954 | 15.5510 | +2.909198 | 1.146167 | 1.108180 | 0.0000 |
| store_item | statistical_subset | tsb | 53 | 10.337029 | 13.544344 | 16.1004 | +4.556018 | 1.187668 | 1.142167 | 0.0000 |
| store_item | statistical_subset | croston | 53 | 10.337029 | 13.544344 | 16.1004 | +4.556018 | 1.187668 | 1.142167 | 0.0000 |
| store_item | statistical_subset | ses | 53 | 10.337029 | 13.544344 | 16.1004 | +4.556018 | 1.187668 | 1.142167 | 0.0000 |
| store_item | statistical_subset | holt | 53 | 10.957767 | 14.407528 | 17.0672 | +4.080545 | 1.263107 | 1.214054 | 0.0000 |
| store_item | statistical_subset | arima_100 | 53 | 12.192876 | 16.339568 | 18.9910 | -8.244885 | 1.386303 | 1.347585 | 0.0000 |
| store_item | statistical_subset | naive | 53 | 16.146226 | 20.966835 | 25.1485 | +13.598383 | 1.846078 | 1.682422 | 0.0000 |
| store_item | statistical_subset | zero | 53 | 64.203504 | 71.815828 | 100.0000 | -64.203504 | 7.173098 | 5.737074 | 0.0000 |

MAE/MASE/RMSSE average the four fold macro values. Pooled RMSE is the square root of summed squared errors divided by total observations; pooled WAPE is summed absolute error divided by total actual units. Bias is predicted minus actual. Undefined scales and zero-actual ratios stay null. Every method delivered the complete declared grid; explicit fallbacks remain in delivered-system scores. Native-only scores in the gate use different counted populations and are not used for unmatched rankings.

## Demand classes, horizons and hierarchy

Classes are frozen from initial-training data, never retrospectively reclassified using validation. The class, horizon and origin tables retain exact counts and defined/undefined metrics. Store/product/category/department/state tables contain grouped leaf-series errors, not aggregate-node forecast errors or official M5 WRMSSE. Cross-dataset evidence supports methodological comparison; different periods, scale, product definitions and feature availability do not justify direct model transfer.

## Resources and failures

| Dataset | Population | Model | 4-run worker seconds | Max recorded RSS MiB | Estimator-fit seconds (ML only) |
|---|---|---|---|---|---|
| m5 | full | croston | 204.18 | 1112.07 | not recorded |
| m5 | full | holt | 192.62 | 1089.74 | not recorded |
| m5 | full | holt_winters_additive | 194.23 | 1160.85 | not recorded |
| m5 | full | lightgbm | 237.68 | 1331.54 | 25.29 |
| m5 | full | moving_average_28 | 179.87 | 1023.85 | not recorded |
| m5 | full | naive | 361.74 | 1124.69 | not recorded |
| m5 | full | random_forest | 415.20 | 1447.89 | 141.22 |
| m5 | full | sba | 204.58 | 1086.25 | not recorded |
| m5 | full | seasonal_moving_average | 181.54 | 1087.66 | not recorded |
| m5 | full | seasonal_naive | 181.45 | 1094.23 | not recorded |
| m5 | full | ses | 192.78 | 1064.44 | not recorded |
| m5 | full | tsb | 208.71 | 1084.35 | not recorded |
| m5 | full | zero | 180.35 | 1035.31 | not recorded |
| m5 | statistical_subset | arima_100 | 59.74 | 634.39 | not recorded |
| m5 | statistical_subset | sarima_100_100_7 | 154.22 | 604.39 | not recorded |
| store_item | full | croston | 2.41 | 168.94 | not recorded |
| store_item | full | holt | 2.31 | 169.80 | not recorded |
| store_item | full | holt_winters_additive | 2.40 | 171.04 | not recorded |
| store_item | full | lightgbm | 16.03 | 262.21 | 10.40 |
| store_item | full | moving_average_28 | 2.26 | 169.33 | not recorded |
| store_item | full | naive | 3.64 | 192.09 | not recorded |
| store_item | full | random_forest | 93.15 | 258.28 | 83.02 |
| store_item | full | sba | 2.27 | 170.30 | not recorded |
| store_item | full | seasonal_moving_average | 2.15 | 168.98 | not recorded |
| store_item | full | seasonal_naive | 2.12 | 166.88 | not recorded |
| store_item | full | ses | 2.39 | 168.08 | not recorded |
| store_item | full | tsb | 2.54 | 167.73 | not recorded |
| store_item | full | zero | 2.15 | 166.71 | not recorded |
| store_item | statistical_subset | arima_100 | 51.08 | 239.42 | not recorded |
| store_item | statistical_subset | sarima_100_100_7 | 377.18 | 246.67 | not recorded |

All 120 original fits ran sequentially under predefined budgets. Resource tables retain original worker wall times and recorded RSS/working-set peaks; projections incur no refitting. Wall times include source/cache checks, preparation, inference, persistence and scoring. Cold preparation is charged to the first method; older baseline runs have no separate stage timings, so these points do not establish intrinsic algorithm speed. Later ML runs retain separate feature-preparation and estimator-fit timing.

- store_item/arima_100: no fallbacks (series-origin cases).
- store_item/sarima_100_100_7: no fallbacks (series-origin cases).
- m5/arima_100: {'all_zero_history': 11, 'insufficient_history': 9, 'RuntimeError:failed_convergence': 1} (series-origin cases).
- m5/sarima_100_100_7: {'all_zero_history': 11, 'insufficient_history': 9} (series-origin cases).

## Fixed initial methodology and Phase 4 candidates

Preserve Naive, Seasonal Naive, MA28 and seasonal moving average as reference methods. Prioritise each dataset's strongest validated statistical and ML candidates with declared search spaces and budgets; inspect bias, sparse-demand coverage and origin stability as well as MAE. Retain intermittent-demand comparators for M5. Fixed initial RF/LightGBM training is bounded (150,000/182,940 rows per origin); sample-size, categorical representation and multi-step strategy are explicit future optimisation questions. No systematic search or final test evaluation has run.

The mandatory independent Claude audit remains after Phase 4 and before Phase 5. Inventory, dashboards, applications and deployment have not started.

## Figures and inspectable evidence

### Mean four-fold macro MAE (sales units); Pooled RMSE across all four folds (sales units); full matched populations

![Mean four-fold macro MAE (sales units); Pooled RMSE across all four folds (sales units); full matched populations](../reports/figures/phase3/phase3e_accuracy.png)

### Pooled WAPE (%); Pooled signed bias (sales units; positive = overforecast); full matched populations

![Pooled WAPE (%); Pooled signed bias (sales units; positive = overforecast); full matched populations](../reports/figures/phase3/phase3e_wape_bias.png)

### Mean four-fold macro MAE (sales units); statistical_subset matched populations

![Mean four-fold macro MAE (sales units); statistical_subset matched populations](../reports/figures/phase3/phase3e_matched_subset.png)

### Horizon errors for seasonal naive, MA28, best statistical, RF and LightGBM

![Horizon errors for seasonal naive, MA28, best statistical, RF and LightGBM](../reports/figures/phase3/phase3e_horizon.png)

### Demand-class accuracy; separate dataset colour scales and fixed initial-origin classes

![Demand-class accuracy; separate dataset colour scales and fixed initial-origin classes](../reports/figures/phase3/phase3e_demand_classes.png)

### Worker pipeline runtime versus accuracy; cold-cache costs included, full populations

![Worker pipeline runtime versus accuracy; cold-cache costs included, full populations](../reports/figures/phase3/phase3e_runtime.png)

### Full-population delivered coverage, explicit fallback rates and validation-origin stability

![Full-population delivered coverage, explicit fallback rates and validation-origin stability](../reports/figures/phase3/phase3e_coverage_stability.png)

### Fallback observations (%); statistical_subset matched populations

![Fallback observations (%); statistical_subset matched populations](../reports/figures/phase3/phase3e_subset_fallbacks.png)

### Actual versus forecast: median initial-training-volume representative per subset demand class, fold 4

![Actual versus forecast: median initial-training-volume representative per subset demand class, fold 4](../reports/figures/phase3/phase3e_examples.png)

Technical evidence: `reports/forecasting/phase3e_gate.json`; per-origin/class/horizon/resource/volume/coverage tables, hierarchy tables and complete per-run errors under ignored `artifacts/experiments/phase3/`. Dataset and protocol hashes remain unchanged. Source-backed report generation: `python -m intelligent_demand.reporting.phase3_report`.
