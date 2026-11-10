# Phase 5 sensitivity analysis

Hypothetical lost-sales simulation; sales are a potentially censored demand proxy. Full populations: Store Item 500 and M5 30,490 series at each of four original validation origins; 28 days per episode. Origins reset stock. Saved forecasts are fixed at issue, not daily refreshed. These validation windows also informed Phase 4 selection; comparisons are exploratory and validation-reused, with no significance claim. Costs are normalised hypothetical units (NCU), not realised savings.

store_item: ML has lower mean cost than MA28 in 17/17 scenarios, higher in 0/17. Difference range -752.504500 to -75.055600 NCU/series/episode. These counts are scenario descriptions, not probabilities.

store_item: among these frozen one-at-a-time cases, the largest absolute change in ML mean cost from base is lead_long: +7675.163500 NCU/series/episode. This depends on the chosen parameter ranges and is not a general importance ranking.

m5: ML has lower mean cost than MA28 in 3/17 scenarios, higher in 14/17. Difference range -5.929780 to +5.762299 NCU/series/episode. These counts are scenario descriptions, not probabilities.

m5: among these frozen one-at-a-time cases, the largest absolute change in ML mean cost from base is penalty_high: +244.139390 NCU/series/episode. This depends on the chosen parameter ranges and is not a general importance ranking.

17 scenarios were frozen before outcomes: base plus one-at-a-time lead, buffer, initial cover, holding, shortage, fixed-order, terminal, variability and review changes. Every case uses the same full matched population and demand path across policies. See configs/inventory.yaml and immutable plan.json for exact values. No new policy or forecasting winner is selected.

The full per-scenario totals, fill, stock, unmet days, orders and paired differences are in phase5_summary.json and report_data.json. Figures show all lead/buffer levels and all 17 cost comparisons. The variability stress is max(0,mu+a*(sales-mu)); clipping changes mean/zeros as well as variability. Terminal-charge and initial-stock cases qualify finite-horizon effects but do not remove them. Buffer days are hypothetical coverage, not a calibrated probability.

Per-series paired distributions are descriptive (10th, median, 90th percentiles); four-origin differences are reported individually. These are neither uncertainty intervals nor independent replications. Repeated series, shared products/stores and reused selection folds prevent an unsupported significance claim.

## Independent-audit qualification

The 17 scenarios are not 17 independent confirmations. They apply one-at-a-time parameter changes to the same four validation origins, the same fixed-origin forecasts and the same populations. Counts such as 17/17 (Store Item) and 3/17 (M5) describe those frozen cases only.

**Sensitivity scenarios share the same four origins, forecasts and populations**

| Dataset | Reference | Origins where ML is cheaper (base) | Scenarios ML cheaper, pooled (of 17) | Scenarios ML cheaper by origin 1 / 2 / 3 / 4 (of 17) | Scenario-origin cells ML cheaper |
|---|---|---|---|---|---|
| Store Item | MA28 | 3 of 4 | 17 | 17 / 17 / 17 / 1 | 52 of 68 |
| Store Item | Seasonal Naive | 3 of 4 | 16 | 16 / 17 / 1 / 15 | 49 of 68 |
| M5 | MA28 | 0 of 4 | 3 | 6 / 2 / 3 / 2 | 13 of 68 |
| M5 | Seasonal Naive | 4 of 4 | 17 | 17 / 17 / 14 / 17 | 65 of 68 |

For Store Item ML against MA28, the scenario count is 17 of 17 when origins are pooled, but ML is cheaper in 52 of 68 scenario-origin cells, because the last origin reverses almost every scenario. Against Seasonal Naive the Store Item pooled count is 16 of 17 with a base advantage of only -1.10%. See [the audit response](PHASE5_AUDIT_RESPONSE.md).
