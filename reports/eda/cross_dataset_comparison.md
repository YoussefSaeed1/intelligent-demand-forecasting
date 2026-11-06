# Different sales structures call for separate forecasting benchmarks

## Executive summary

Store Item's EDA zero-sales rate is 0.0001%, compared with 68.84% for M5. This population difference does not imply every M5 series is intermittent. Leading-zero sensitivity and the per-series classes below matter for model choice.

| EDA statistic | Store Item | M5 |
|---|---:|---:|
| Series | 500.0000 | 30,490.0000 |
| Training-prefix observations | 843,000.0000 | 54,912,490.0000 |
| Training-prefix units | 43,666,945.0000 | 61,066,490.0000 |
| Zero-sales percentage | 0.0001 | 68.8374 |
| Median all-sales CV | 0.2877 | 2.0801 |
| Median lag-7 correlation | 0.7275 | 0.1750 |
| Median lag-365 correlation | 0.5458 | 0.0304 |
| Top-10%-of-products sales share | 0.1628 | 0.5168 |
| Class changes after leading-zero removal | 0.0000 | 1,288.0000 |

Each EDA scope ends before its first validation window. These are full-series-population training summaries, not statistics of the untouched evaluation tails. Full-history audit references remain separate in the per-dataset reports.

## Forecasting implications

Use naive, weekly seasonal naive and trailing moving-average baselines for both sources. Store Item's calendar diagnostics support testing seasonal ETS and carefully scoped SARIMA, alongside global lag/calendar ML. M5 needs stratified evaluation across defined patterns and cold-start/all-zero histories; compare Croston/SBA and TSB where intermittent/nonstationary activity makes them plausible. Category-level aggregates and per-series behaviour must not be conflated.

A global LightGBM candidate is computationally plausible for many series, with origin-safe features and explicit multi-step strategy; it is optional and was not installed or trained. Random Forest is a useful controlled ML comparator but row/lag matrices and tree memory must be budgeted. Fitting independent SARIMA searches to all 30,490 M5 series is not the default; use a predeclared training-stratified diagnostic subset if needed and report coverage.

These are candidate-family recommendations, not empirical claims of forecasting superiority. Use a common 28-day design, source-specific chronological windows, MAE/RMSE/WAPE/signed bias, and training-only weekly MASE/RMSSE scales. Compare within-source improvements over baselines rather than raw scale-dependent errors across sources. No direct model transfer is established: IDs, covariate availability, units and sparsity differ.

Full methods and exact proposed folds: [forecasting protocol](../../docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md). Model-family references: [forecasting toolbox](https://otexts.com/fpp3/toolbox.html), [intermittency and obsolescence](https://doi.org/10.1016/j.ejor.2011.05.018).
