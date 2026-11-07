# Forecasting visualisation index

All figures use independently verified validation predictions. PNG and SVG pairs share identical plotted data.

| Figure | Purpose | Relative PNG path | Relative SVG path |
|---|---|---|---|
| phase3e_accuracy | Mean four-fold macro MAE (sales units); Pooled RMSE across all four folds (sales units); full matched populations | ../figures/phase3/phase3e_accuracy.png | ../figures/phase3/phase3e_accuracy.svg |
| phase3e_wape_bias | Pooled WAPE (%); Pooled signed bias (sales units; positive = overforecast); full matched populations | ../figures/phase3/phase3e_wape_bias.png | ../figures/phase3/phase3e_wape_bias.svg |
| phase3e_matched_subset | Mean four-fold macro MAE (sales units); statistical_subset matched populations | ../figures/phase3/phase3e_matched_subset.png | ../figures/phase3/phase3e_matched_subset.svg |
| phase3e_horizon | Horizon errors for seasonal naive, MA28, best statistical, RF and LightGBM | ../figures/phase3/phase3e_horizon.png | ../figures/phase3/phase3e_horizon.svg |
| phase3e_demand_classes | Demand-class accuracy; separate dataset colour scales and fixed initial-origin classes | ../figures/phase3/phase3e_demand_classes.png | ../figures/phase3/phase3e_demand_classes.svg |
| phase3e_runtime | Worker pipeline runtime versus accuracy; cold-cache costs included, full populations | ../figures/phase3/phase3e_runtime.png | ../figures/phase3/phase3e_runtime.svg |
| phase3e_coverage_stability | Full-population delivered coverage, explicit fallback rates and validation-origin stability | ../figures/phase3/phase3e_coverage_stability.png | ../figures/phase3/phase3e_coverage_stability.svg |
| phase3e_subset_fallbacks | Fallback observations (%); statistical_subset matched populations | ../figures/phase3/phase3e_subset_fallbacks.png | ../figures/phase3/phase3e_subset_fallbacks.svg |
| phase3e_examples | Actual versus forecast: median initial-training-volume representative per subset demand class, fold 4 | ../figures/phase3/phase3e_examples.png | ../figures/phase3/phase3e_examples.svg |
