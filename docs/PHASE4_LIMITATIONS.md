# Phase 4 limitations

Observed sales may be constrained by availability and are not latent demand.
M5 price publication latency is unverified: every Phase 4 ML candidate is price-free;
Phase 3 price-enabled M5 scores remain conditional research references.
SNAP, events and future prices are excluded. Equal seeded series/time-stratified ML
sampling uses 150,000 Store Item labels and 182,940 M5 labels per origin, with no
outcome filtering; all series and zero-demand histories remain eligible. This is
300 and 6 labels per series respectively, not full-history supervised training.
Four validation windows and one final 28-day window cover limited seasonal regimes.
Search-selected validation gains are optimistic estimates after model selection.
Origin spread is descriptive variability, not a confidence interval. Correlated
series and only four origins do not establish statistical significance. Grouped
leaf errors by hierarchy are not aggregate-node forecasts or official WRMSSE.
Undefined scale/actual denominators stay null and their coverage is reported.
Accuracy does not demonstrate inventory savings or economic superiority.
Runtime is measured worker cost with verified cache reuse; hardware load and cache
warmth vary, so these observations are not controlled hardware benchmarks.
Direct cross-dataset transfer is untested; compare methodology and relative baseline
performance rather than absolute sales-unit errors. Historical Phase 3 statistical
subset results cannot establish population performance; Phase 4 comparisons use
the complete approved populations. Holdout results cannot be used for retuning.
An independent Claude audit is still mandatory after Phase 4 and before Phase 5;
it must review scientific integrity without redesigning models to fit the holdout.

See the authored [scientific review](PHASE4_SCIENTIFIC_REVIEW.md) for exact metric trade-offs, actual final sample coverage and qualified interpretation. MA28 has better M5 macro MASE than the selected RF; the frozen primary-MAE selection was not changed.
