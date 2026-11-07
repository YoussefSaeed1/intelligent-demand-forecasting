# Phase 3D ML results

Status: COMPLETE; independent and automated gates passed.

Orange bars identify ML; all 13 methods share each full evaluation population. ARIMA/SARIMA are reserved for the matched statistical-subset comparison.

| Dataset | Model | Macro MAE | Pooled RMSE | WAPE % | Bias units | Fallback % |
|---|---|---|---|---|---|---|
| store_item | lightgbm | 6.308040 | 8.178519 | 10.3382 | +0.037028 | 0.0000 |
| store_item | random_forest | 6.885316 | 8.990947 | 11.2843 | +0.545272 | 0.0000 |
| store_item | holt_winters_additive | 7.701650 | 10.242293 | 12.6222 | -0.859491 | 0.0000 |
| store_item | seasonal_moving_average | 8.086652 | 10.599769 | 13.2532 | +2.817554 | 0.0000 |
| store_item | seasonal_naive | 9.154964 | 12.023970 | 15.0041 | +0.797071 | 0.0000 |
| store_item | sba | 9.195172 | 12.160157 | 15.0700 | -2.151480 | 0.0000 |
| store_item | moving_average_28 | 9.538296 | 12.548730 | 15.6323 | +2.817554 | 0.0000 |
| store_item | croston | 9.892034 | 12.959967 | 16.2120 | +4.389086 | 0.0000 |
| store_item | tsb | 9.892034 | 12.959967 | 16.2120 | +4.389086 | 0.0000 |
| store_item | ses | 9.892034 | 12.959967 | 16.2120 | +4.389086 | 0.0000 |
| store_item | holt | 10.440839 | 13.736397 | 17.1115 | +3.871962 | 0.0000 |
| store_item | naive | 15.689214 | 20.440164 | 25.7130 | +12.858929 | 0.0000 |
| store_item | zero | 61.016571 | 68.232190 | 100.0000 | -61.016571 | 0.0000 |
| m5 | random_forest | 1.027612 | 2.308980 | 75.8098 | -0.020690 | 0.0000 |
| m5 | moving_average_28 | 1.033779 | 2.342793 | 76.2647 | -0.051500 | 0.0000 |
| m5 | tsb | 1.042455 | 2.365638 | 76.9047 | -0.027338 | 0.0213 |
| m5 | ses | 1.054442 | 2.386738 | 77.7891 | -0.003226 | 0.0213 |
| m5 | lightgbm | 1.070783 | 2.451283 | 78.9946 | -0.003709 | 0.0000 |
| m5 | seasonal_moving_average | 1.071424 | 2.433870 | 79.0419 | -0.051500 | 0.0000 |
| m5 | sba | 1.087810 | 2.370838 | 80.2507 | -0.051973 | 0.0320 |
| m5 | holt_winters_additive | 1.111869 | 2.547450 | 82.0256 | -0.023811 | 0.0213 |
| m5 | croston | 1.122368 | 2.410585 | 82.8002 | +0.092865 | 0.0320 |
| m5 | holt | 1.171588 | 2.715957 | 86.4313 | +0.081622 | 0.0213 |
| m5 | seasonal_naive | 1.212000 | 2.859958 | 89.4125 | -0.077700 | 0.0000 |
| m5 | naive | 1.352632 | 3.201968 | 99.7874 | +0.222429 | 0.0000 |
| m5 | zero | 1.355514 | 3.842455 | 100.0000 | -1.355514 | 0.0000 |

![Full-population comparisons](../reports/figures/phase3/phase3d_accuracy.png)

| Dataset | ML model | 4-run worker seconds | Maximum recorded RSS MiB |
|---|---|---|---|
| store_item | random_forest | 93.15 | 258.28 |
| store_item | lightgbm | 16.03 | 262.21 |
| m5 | random_forest | 415.20 | 1447.89 |
| m5 | lightgbm | 237.68 | 1331.54 |

Worker times include cache/preparation, fitting, all 28 recursive steps, persistence and scoring. They are not isolated fit times. Stage timings and estimator-fit times are retained in each run. All 16 runs passed complete persisted-prediction reconciliation, model reload checks, and independent comparison of every sampled training label and feature against historical source data. Training uses 150,000/182,940 rows per origin; evaluation uses every 500/30,490 series. No tuning or final holdout access occurred.

See [fixed models](ML_FORECASTING.md), [availability assumptions](FEATURE_AVAILABILITY.md), and [independent gate](../reports/forecasting/phase3d_gate.json).
