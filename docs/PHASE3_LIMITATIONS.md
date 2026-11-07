# Phase 3 limitations

- Results concern observed daily sales, which may be stock constrained. Zeros do
  not establish product availability or latent demand. No inventory savings are claimed.
- Validation contains four adjacent 28-day windows per dataset, with different
  years/seasons between datasets. There is no significance test, independent-season
  confidence interval or universal winner claim. Protected final holdouts remain unused.
- Configurations are fixed initial choices. No systematic hyperparameter search,
  validation-driven feature search, early stopping or Phase 4 work has occurred.
- ARIMA/SARIMA use reproducible training-only stratified subsets: 53 Store Item and
  51 M5 series. Minority strata are deliberately represented. Unweighted subset
  means are not population estimates; comparisons use exactly matching observations.
  Global-model projections retain their full-population training context; matching
  evaluation observations does not mean identical training-row budgets or that global
  models were refitted only on the subset.
- ML fits 150,000 Store Item and 182,940 M5 rows per origin, equally across series
  and time strata. All 500/30,490 series enter evaluation. M5 contributes only six
  labels per series to each global fit; this is a resource-bounded initial comparator.
  The first 56 training targets lack lag prerequisites and are not sampled.
- RF treats identifier codes as ordinal. LightGBM treats them as categorical.
  Equal configurations do not guarantee equal representational capacity or a fair
  claim about each family's optimised performance. Squared-error training and MAE
  selection can prefer different point summaries on sparse demand.
- Recursive lag/rolling state uses prior predictions, creating train/inference
  distribution shift and error propagation. Observed activity statistics and price
  snapshots freeze at the true origin; predictions are never observed occurrences.
- Historical M5 prices include 12,299,413 missing values. Missing source prices stay
  missing. Observed-only historical summaries use completed weeks with a seven-day
  lag, assuming availability after week completion; actual publication latency is
  unknown. Future prices, events and SNAP are excluded because advance availability
  is unverified. This omits potentially useful covariates without inventing them.
- Undefined MASE/RMSSE or percentage metrics remain null, with explicit defined
  and undefined counts. No epsilon or zero filling disguises a zero denominator.
  Defined-only macro means and pooled metrics answer different questions.
- Statistical degenerate/convergence failures use explicitly recorded fallbacks;
  scores describe the complete delivered system. Native-only diagnostics have
  different populations and are not interchangeable with full rankings.
- Hierarchy tables summarise leaf-series errors grouped by store/product/category/
  department/state. They are not aggregated-node forecasts, coherent hierarchical
  forecasts or official competition WRMSSE.
- Runtime points are original worker wall times including source/cache checks,
  preparation, inference, scoring and persistence. Cold work is charged to the
  first method. Older baseline runs lack stage timings; they are preserved rather
  than rerun for favourable timings. Resource peaks are sampled RSS/OS working-set
  evidence, not total system peak memory. No GPU benchmark was performed.
- Separate source-specific fits support methodological comparison, not direct
  cross-dataset model transfer. Product universes, calendars, volumes and available
  features differ. Transfer was not tested or assumed valid.
- The local capability API protects trusted adapters; it is not a sandbox for
  arbitrary malicious Python code. Source hashes and frozen split checks complement
  interface review, future-poison tests and persisted-file audits.
- Large technical outputs, fitted models and caches remain local and ignored by
  Git. Reproducibility also needs the verified local sources and pinned recorded
  package versions. No project files are uploaded. A secure local checkpoint is
  authorised by the subsequent final scientific integrity review request.

The independent Claude audit remains mandatory **after Phase 4 and before Phase 5**.
Critical/high findings must be resolved and independently revalidated. This Phase 3
review does not satisfy that future independent audit.
