# Phase 3B baseline results

Status: COMPLETE; independent reconciliation gate passed.

- store_item: seasonal_moving_average has the lowest four-fold macro MAE (8.086652 units), 11.67% below seasonal naive on the same population/windows. This is validation evidence, not a final-test result.
- m5: moving_average_28 has the lowest four-fold macro MAE (1.033779 units), 14.70% below seasonal naive on the same population/windows. This is validation evidence, not a final-test result.

| Dataset | Model | Macro MAE | Pooled RMSE | Pooled WAPE % | Bias units | Macro MASE | Macro RMSSE |
|---|---|---|---|---|---|---|---|
| store_item | seasonal_moving_average | 8.086652 | 10.599769 | 13.2532 | +2.817554 | 0.972851 | 0.949943 |
| store_item | seasonal_naive | 9.154964 | 12.023970 | 15.0041 | +0.797071 | 1.111900 | 1.091963 |
| store_item | moving_average_28 | 9.538296 | 12.548730 | 15.6323 | +2.817554 | 1.126897 | 1.090525 |
| store_item | naive | 15.689214 | 20.440164 | 25.7130 | +12.858929 | 1.833140 | 1.665480 |
| store_item | zero | 61.016571 | 68.232190 | 100.0000 | -61.016571 | 7.013843 | 5.623182 |
| m5 | moving_average_28 | 1.033779 | 2.342793 | 76.2647 | -0.051500 | 1.664832 | 0.870662 |
| m5 | seasonal_moving_average | 1.071424 | 2.433870 | 79.0419 | -0.051500 | 1.707211 | 0.941723 |
| m5 | seasonal_naive | 1.212000 | 2.859958 | 89.4125 | -0.077700 | 1.877038 | 1.136993 |
| m5 | naive | 1.352632 | 3.201968 | 99.7874 | +0.222429 | 2.043041 | 1.134538 |
| m5 | zero | 1.355514 | 3.842455 | 100.0000 | -1.355514 | 1.597677 | 1.075942 |

MAE/MASE/RMSSE are means of the four fold macro values. Pooled RMSE, WAPE and bias use summed errors and actual quantities over all four validation windows. Undefined per-series denominators remain null and have explicit coverage in the gate JSON.

![Matched baseline accuracy](../reports/figures/phase3/phase3b_accuracy.png)

| Dataset | Model | Series/fold | Predictions (4 folds) | Fallback % | Worker seconds (4 runs) | Maximum sampled RSS MiB |
|---|---|---|---|---|---|---|
| store_item | seasonal_moving_average | 500 | 56,000 | 0.0000 | 2.15 | 168.98 |
| store_item | seasonal_naive | 500 | 56,000 | 0.0000 | 2.12 | 166.88 |
| store_item | moving_average_28 | 500 | 56,000 | 0.0000 | 2.26 | 169.33 |
| store_item | naive | 500 | 56,000 | 0.0000 | 3.64 | 192.09 |
| store_item | zero | 500 | 56,000 | 0.0000 | 2.15 | 166.71 |
| m5 | moving_average_28 | 30490 | 3,414,880 | 0.0000 | 179.87 | 1023.85 |
| m5 | seasonal_moving_average | 30490 | 3,414,880 | 0.0000 | 181.54 | 1087.66 |
| m5 | seasonal_naive | 30490 | 3,414,880 | 0.0000 | 181.45 | 1094.23 |
| m5 | naive | 30490 | 3,414,880 | 0.0000 | 361.74 | 1124.69 |
| m5 | zero | 30490 | 3,414,880 | 0.0000 | 180.35 | 1035.31 |

Worker times include preparation/cache checks, forecasting, scoring and publication; first-use cache creation is included. They are not isolated algorithm fit times. Memory is sampled worker RSS; it is not whole-system peak memory.

All 40 runs passed complete-key, 28-day horizon, metadata, clipping, delivery-method, per-series/macro/pooled/horizon/class metric reconciliation and unchanged raw/canonical hash checks. Store/product/hierarchy results are in `artifacts/experiments/phase3/3b_hierarchy_metrics.parquet`. Final holdout targets remain protected. Four adjacent windows cover a limited seasonal span and do not establish significance or a universal winning method.

Evidence: [independent gate](../reports/forecasting/phase3b_gate.json), [method definitions](BASELINE_MODELS.md), and the ignored local experiment registry.
