# Phase 5 sensitivity analysis

Hypothetical lost-sales simulation; sales are a potentially censored demand proxy. Full populations: Store Item 500 and M5 30,490 series at each of four original validation origins; 28 days per episode. Origins reset stock. Saved forecasts are fixed at issue, not daily refreshed. These validation windows also informed Phase 4 selection; comparisons are exploratory and validation-reused, with no significance claim. Costs are normalised hypothetical units (NCU), not realised savings.

store_item: ML has lower mean cost than MA28 in 17/17 scenarios, higher in 0/17. Difference range -752.504500 to -75.055600 NCU/series/episode. These counts are scenario descriptions, not probabilities.

store_item: among these frozen one-at-a-time cases, the largest absolute change in ML mean cost from base is lead_long: +7675.163500 NCU/series/episode. This depends on the chosen parameter ranges and is not a general importance ranking.

m5: ML has lower mean cost than MA28 in 3/17 scenarios, higher in 14/17. Difference range -5.929780 to +5.762299 NCU/series/episode. These counts are scenario descriptions, not probabilities.

m5: among these frozen one-at-a-time cases, the largest absolute change in ML mean cost from base is penalty_high: +244.139390 NCU/series/episode. This depends on the chosen parameter ranges and is not a general importance ranking.

17 scenarios were frozen before outcomes: base plus one-at-a-time lead, buffer, initial cover, holding, shortage, fixed-order, terminal, variability and review changes. Every case uses the same full matched population and demand path across policies. See configs/inventory.yaml and immutable plan.json for exact values. No new policy or forecasting winner is selected.

The full per-scenario totals, fill, stock, unmet days, orders and paired differences are in phase5_summary.json and report_data.json. Figures show all lead/buffer levels and all 17 cost comparisons. The variability stress is max(0,mu+a*(sales-mu)); clipping changes mean/zeros as well as variability. Terminal-charge and initial-stock cases qualify finite-horizon effects but do not remove them. Buffer days are hypothetical coverage, not a calibrated probability.

Per-series paired distributions are descriptive (10th, median, 90th percentiles); four-origin differences are reported individually. These are neither uncertainty intervals nor independent replications. Repeated series, shared products/stores and reused selection folds prevent an unsupported significance claim.
