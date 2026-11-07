# Phase 3C statistical results

Status: COMPLETE; independent and automated quality gates passed.

Full-population and statistical-subset results below are separate comparisons. The unweighted stratified subsets contain 53 Store Item and 51 M5 series; their means must not be extrapolated to the populations. All comparisons use all four unchanged 28-day validation windows.

| Dataset | Population | Requested model | Series/fold | Macro MAE | Pooled RMSE | WAPE % | Bias units | Fallback % |
|---|---|---|---|---|---|---|---|---|
| store_item | full | holt_winters_additive | 500 | 7.701650 | 10.242293 | 12.6222 | -0.859491 | 0.0000 |
| store_item | full | seasonal_moving_average | 500 | 8.086652 | 10.599769 | 13.2532 | +2.817554 | 0.0000 |
| store_item | full | seasonal_naive | 500 | 9.154964 | 12.023970 | 15.0041 | +0.797071 | 0.0000 |
| store_item | full | sba | 500 | 9.195172 | 12.160157 | 15.0700 | -2.151480 | 0.0000 |
| store_item | full | moving_average_28 | 500 | 9.538296 | 12.548730 | 15.6323 | +2.817554 | 0.0000 |
| store_item | full | croston | 500 | 9.892034 | 12.959967 | 16.2120 | +4.389086 | 0.0000 |
| store_item | full | tsb | 500 | 9.892034 | 12.959967 | 16.2120 | +4.389086 | 0.0000 |
| store_item | full | ses | 500 | 9.892034 | 12.959967 | 16.2120 | +4.389086 | 0.0000 |
| store_item | full | holt | 500 | 10.440839 | 13.736397 | 17.1115 | +3.871962 | 0.0000 |
| store_item | full | naive | 500 | 15.689214 | 20.440164 | 25.7130 | +12.858929 | 0.0000 |
| store_item | full | zero | 500 | 61.016571 | 68.232190 | 100.0000 | -61.016571 | 0.0000 |
| m5 | full | moving_average_28 | 30490 | 1.033779 | 2.342793 | 76.2647 | -0.051500 | 0.0000 |
| m5 | full | tsb | 30490 | 1.042455 | 2.365638 | 76.9047 | -0.027338 | 0.0213 |
| m5 | full | ses | 30490 | 1.054442 | 2.386738 | 77.7891 | -0.003226 | 0.0213 |
| m5 | full | seasonal_moving_average | 30490 | 1.071424 | 2.433870 | 79.0419 | -0.051500 | 0.0000 |
| m5 | full | sba | 30490 | 1.087810 | 2.370838 | 80.2507 | -0.051973 | 0.0320 |
| m5 | full | holt_winters_additive | 30490 | 1.111869 | 2.547450 | 82.0256 | -0.023811 | 0.0213 |
| m5 | full | croston | 30490 | 1.122368 | 2.410585 | 82.8002 | +0.092865 | 0.0320 |
| m5 | full | holt | 30490 | 1.171588 | 2.715957 | 86.4313 | +0.081622 | 0.0213 |
| m5 | full | seasonal_naive | 30490 | 1.212000 | 2.859958 | 89.4125 | -0.077700 | 0.0000 |
| m5 | full | naive | 30490 | 1.352632 | 3.201968 | 99.7874 | +0.222429 | 0.0000 |
| m5 | full | zero | 30490 | 1.355514 | 3.842455 | 100.0000 | -1.355514 | 0.0000 |
| store_item | statistical_subset | seasonal_moving_average | 53 | 8.318144 | 10.980170 | 12.9559 | +2.909198 | 0.0000 |
| store_item | statistical_subset | sarima_100_100_7 | 53 | 8.932206 | 11.781811 | 13.9123 | -4.814757 | 0.0000 |
| store_item | statistical_subset | seasonal_naive | 53 | 9.401954 | 12.458827 | 14.6440 | +0.650943 | 0.0000 |
| store_item | statistical_subset | moving_average_28 | 53 | 9.984273 | 13.166954 | 15.5510 | +2.909198 | 0.0000 |
| store_item | statistical_subset | arima_100 | 53 | 12.192876 | 16.339568 | 18.9910 | -8.244885 | 0.0000 |
| store_item | statistical_subset | naive | 53 | 16.146226 | 20.966835 | 25.1485 | +13.598383 | 0.0000 |
| store_item | statistical_subset | zero | 53 | 64.203504 | 71.815828 | 100.0000 | -64.203504 | 0.0000 |
| m5 | statistical_subset | moving_average_28 | 51 | 2.147421 | 4.546687 | 61.1104 | -0.062850 | 0.0000 |
| m5 | statistical_subset | seasonal_moving_average | 51 | 2.159926 | 4.635540 | 61.4662 | -0.062850 | 0.0000 |
| m5 | statistical_subset | sarima_100_100_7 | 51 | 2.431020 | 5.361068 | 69.1809 | -0.269409 | 9.8039 |
| m5 | statistical_subset | arima_100 | 51 | 2.517115 | 5.721930 | 71.6309 | -0.339455 | 10.2941 |
| m5 | statistical_subset | seasonal_naive | 51 | 2.601891 | 6.809097 | 74.0434 | -0.058123 | 0.0000 |
| m5 | statistical_subset | naive | 51 | 2.714636 | 6.032823 | 77.2519 | +0.289916 | 0.0000 |
| m5 | statistical_subset | zero | 51 | 3.514006 | 8.971984 | 100.0000 | -3.514006 | 0.0000 |

![Matched statistical comparisons](../reports/figures/phase3/phase3c_accuracy.png)

## Native delivery and fallbacks

- store_item / ses: 2000/2000 native series-origin cases; fallback cases none.
- store_item / holt: 2000/2000 native series-origin cases; fallback cases none.
- store_item / holt_winters_additive: 2000/2000 native series-origin cases; fallback cases none.
- store_item / croston: 2000/2000 native series-origin cases; fallback cases none.
- store_item / sba: 2000/2000 native series-origin cases; fallback cases none.
- store_item / tsb: 2000/2000 native series-origin cases; fallback cases none.
- store_item / arima_100: 212/212 native series-origin cases; fallback cases none.
- store_item / sarima_100_100_7: 212/212 native series-origin cases; fallback cases none.
- m5 / ses: 121934/121960 native series-origin cases; fallback cases all_zero_history: 26.
- m5 / holt: 121934/121960 native series-origin cases; fallback cases all_zero_history: 26.
- m5 / holt_winters_additive: 121934/121960 native series-origin cases; fallback cases all_zero_history: 26.
- m5 / croston: 121921/121960 native series-origin cases; fallback cases all_zero_history: 26, insufficient_history: 13.
- m5 / sba: 121921/121960 native series-origin cases; fallback cases all_zero_history: 26, insufficient_history: 13.
- m5 / tsb: 121934/121960 native series-origin cases; fallback cases all_zero_history: 26.
- m5 / arima_100: 183/204 native series-origin cases; fallback cases RuntimeError:failed_convergence: 1, all_zero_history: 11, insufficient_history: 9.
- m5 / sarima_100_100_7: 184/204 native series-origin cases; fallback cases all_zero_history: 11, insufficient_history: 9.

These are counts across four origins, not distinct series. Complete delivered-system scores include every declared fallback. Native-only diagnostics remain in the gate JSON and have a different, explicitly counted population; they are not used for unmatched rankings.

## Resources and limitations

Executed 64 statistical runs sequentially, 1853.66 worker seconds in total. Maximum recorded working set/RSS was 1160.85 MiB. Times include preparation, forecasting, scoring and publication; cached and first-use work differ. Later runs also retain stage timings. Projected baselines reuse completed Phase 3B forecasts and must not be described as newly fitted low-cost runs.

Smoothing parameters and ARIMA orders are fixed initial choices, not optimised models. The documented statsmodels seasonal recycling discrepancy is avoided by forecasting from validated component states. Leading zeros and missing historical prices remain unchanged; no future prices or final-test labels were used. Adjacent validation folds do not establish statistical significance or universal method superiority.

Evidence: [methods and eligibility](STATISTICAL_MODELS.md), [independent gate](../reports/forecasting/phase3c_gate.json).
