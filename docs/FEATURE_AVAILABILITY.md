# Phase 3D feature availability

The immutable Phase 2 protocol governs every origin. All sales histories end at
the origin; validation targets are read only after predictions have been sealed.
No protected final holdout targets are used. Features are constructed in bounded
8,192-row batches, with an explicit schema checked at every recursive step.

| Features | Availability | Training and 28-day inference policy |
|---|---|---|
| Store/product/category/department/state identifiers | Static | Deterministic mappings of the fixed benchmark universe; no target summaries |
| Lags 1, 7, 14, 28, 56 | Historical observed, then recursively predicted | Training target t uses values strictly before t; inference appends its own clipped predictions |
| Means 7/28/56 and population standard deviations 7/28 | Historical observed, then recursively predicted | Shifted by one day; recomputed on the available recursive state |
| Zero fractions 28/56, positive count 56, ADI 56, positive CV² 56, last-positive age capped at 56 | Historical observed | Computed before each training target; frozen at the true origin throughout inference so point predictions are not treated as observed demand occurrences |
| Weekday, day of month, month, weekend, weekly/annual sine and cosine, elapsed calendar days | Known future | Derived only from target date; leap-year annual period is 366 days |
| M5 observed-price mean and missing fraction over 28 daily records | Historical observed, with conservative availability assumption | For training target index t, uses indices t−34 through t−7 inclusive; the last source week has finished by t−1. Snapshot is frozen at the true inference origin |
| Future observed prices | Unknown future | Excluded |
| Events and SNAP | Advance availability unverified | Excluded; source files do not establish an operational publication schedule |
| EDA patterns, totals, means and intermittency summaries | Target derived | Excluded from model features; initial-origin classes are used only for reporting and frozen statistical sampling |

Historical M5 price records are assumed available after their source week has
completed. Actual publication latency is not supplied, so operational availability
cannot be proven. The seven-day lag avoids using prices from an unfinished source
week. Only known prices enter the mean; absent prices remain NaN, with an explicit
missing fraction. There is no zero filling, backfilling or modification of the
12,299,413 missing historical source prices. Store Item has no price features.

The final integrity review independently checked the actual M5 week calendar for
all eligible training target dates and all four inference origins. All referenced
price weeks end before their respective forecasting origins. **This verifies week
completion, not publication latency.** M5 price-enabled results are conditional
research-benchmark evidence, not approval of a live availability contract. Operational
claims need publication evidence or a separately authorised price-free comparison;
neither is silently assumed or performed here.

Undefined ADI (no positive observations), positive CV² (fewer than two positives),
and price means (no observed price) remain NaN, handled natively by the estimators.
All other features must be finite. Sales histories are nonnegative and complete;
the source observations are not imputed or rewritten.

Training rows are sampled independently of outcomes with seed 42, equally across
series and time strata within the expanding history. The first 56 target dates
are ineligible because of lag prerequisites. Each Store Item series contributes
300 rows (150,000 total); each M5 series contributes six (182,940 total). This is
bounded training, **not reduced evaluation**: every series receives all 28 forecasts
at all four approved origins. Cache manifests retain origin/source/code/schema
hashes, target bounds and immutable checksummed feature/label/position arrays.

Implementation: `features/recursive.py`; adversarial and arithmetic checks:
`tests/test_ml_forecasting.py`. Future-target poisoning must leave forecasts
unchanged. Frozen observed context and recursive lag updates are tested separately.
