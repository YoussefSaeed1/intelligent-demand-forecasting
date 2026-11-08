# Phase 4 feature availability

Phase 3's conditional price-enabled historical evidence remains documented in
`FEATURE_AVAILABILITY.md`. Every Phase 4 ML candidate and final refit is price-free.
The exact persisted encoder has 27 Store Item columns or 30 M5 columns.

| Feature group | Source at label time t / forecast origin O | Final recursive policy |
|---|---|---|
| Lags 1, 7, 14, 28, 56 | Observed targets strictly before t | Observed through O; then only own clipped point predictions |
| Means 7, 28, 56; standard deviations 7, 28 | Shifted historical targets, population standard deviation | Recomputed using the evolving available recursive state |
| Zero fractions 28/56; positive count 56; ADI 56; positive CV² 56; capped last-positive age 56 | Observed strictly before t | Frozen at O for all 28 steps; predicted points are not treated as observed occurrences |
| Weekday, day, month, weekend, weekly/annual sine/cosine, elapsed calendar days | Deterministic target date | Known without future outcomes; annual period handles leap years |
| Store/item codes; M5 category/department/state codes | Fixed benchmark identifiers, deterministic target-free mappings | Same frozen encoder; no target encoding or future aggregates |
| Historical/future prices | Publication latency unverified | Excluded, including missing-price indicator and historical price summaries |
| Events and SNAP | Advance publication unavailable in source evidence | Excluded |
| Initial-prefix demand classes and sales totals | Reporting metadata only | Excluded from features; class labels remain frozen for grouped assessment |

Undefined historical ADI/CV² remain NaN and are handled by the estimator; this
does not impute source sales. Training rows are sampled independently of outcomes
with seed 42 across equal per-series time strata after the first 56 dates.
Zero-demand histories are not filtered. Training labels and all feature columns
are independently reconciled to original origin-bounded panels before approval.

Tests poison future targets and all historical/future prices. Phase 4 price-free
forecasts are unchanged by the latter; any modified canonical file hash revokes
the final freeze. Public model interfaces receive an origin-bounded capability,
not an unrestricted target reader. This is an application integrity boundary,
not a security sandbox against arbitrary malicious Python or filesystem edits.
