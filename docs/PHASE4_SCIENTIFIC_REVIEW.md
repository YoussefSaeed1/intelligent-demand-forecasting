# Phase 4 scientific interpretation of the frozen assessment

This interpretation uses the completed, fixed assessment. It does not change
model choices, features, parameters, comparators or forecasts. Independent here
describes separate arithmetic checks; the mandatory external Claude audit has
**not** been performed.

## Validation and selection

All 27 cases and 108 four-origin fold evaluations passed independent prediction,
metric, feature, label, sample-position, key and coverage reconciliation:
45,177,440 validation forecasts. Store Item's initial LightGBM configuration
remained best at MAE 6.308039822; the five alternative configurations did not
improve it. Do not describe the final Store Item model as an additional tuning gain.

Price-free M5 RF trial 02 achieved validation MAE 1.020066985 against MA28 at
1.033779225, a 1.326419% reduction. RF has the lower mean error in all four
origins, with RF-minus-MA28 differences −0.016259711, −0.013763500,
−0.011180470 and −0.013645279 units. MA28 nevertheless wins a majority of
individual series in every validation origin (50.15–53.20%). This supports a
small mean-MAE advantage, not universal series-level or economic superiority.

The pre-target freeze was published at **2026-11-07T12:41:37.811576+00:00**:
`a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb`.
It preserves 89 scientific source/configuration/test/protocol files and exact
package versions. Git remains at the Phase 3 checkpoint; no freeze commit was needed.

## Final holdout — unchanged selections

| Dataset / frozen method | Macro MAE | Pooled RMSE | Pooled WAPE % | Macro MASE | Macro RMSSE |
|---|---:|---:|---:|---:|---:|
| Store Item selected LightGBM | 5.434342531 | 7.066975972 | 12.258462 | 0.656739 | 0.644564 |
| Store Item Seasonal Naive | 12.814642857 | 16.701995176 | 28.906498 | 1.504507 | 1.433304 |
| M5 selected price-free RF | 1.047231371 | 2.201063154 | 72.582278 | 1.637036 | 0.897646 |
| M5 MA28 | 1.065729312 | 2.242952960 | 73.864346 | 1.610618 | 0.904875 |
| M5 TSB | 1.063192967 | 2.208269198 | 73.688556 | 1.624712 | 0.915955 |

Store Item LightGBM reduces final MAE by 57.592712% relative to Seasonal Naive.
M5 RF reduces final MAE by 1.735707% relative to MA28. Both retain their
preselected roles; final performance was not used to substitute a model.

**The M5 ranking depends on the metric.** MA28 has better macro MASE than RF
(1.610618 versus 1.637036), despite RF's better MAE, pooled RMSE, WAPE and macro
RMSSE. TSB also has better macro MASE than RF. Scaling changes the relative
influence of series; the predeclared primary objective remains unchanged.
Do not claim RF dominates every loss function or every demand pattern.

A descriptive check of the same saved final per-series MAEs gives 15,655 RF wins
and 14,835 MA28 wins, with no ties within 1e-12 (51.3447% favour RF). This single
holdout window differs from the validation series-majority pattern. It is not an
independent significance test or evidence of stable dominance across future seasons.

M5 has 812 series with zero total actual sales in the final window. Their
per-series WAPE and percentage bias remain undefined; they are retained in MAE,
RMSE and complete forecast coverage. All final MASE/RMSSE scales are defined.
Every final method delivered the complete population without fallback.

## Actual final ML sample coverage

| Dataset | Series / stores / products | Labels | Per series | Eligible-label share | Zero labels |
|---|---|---:|---:|---:|---:|
| Store Item | 500 / 10 / 50 | 150,000 | 300 | 17.221584% | 1 |
| M5 | 30,490 / 10 / 3,049 | 182,940 | 6 | 0.323102% | 123,972 (67.766481%) |

Seeded positions reproduce exactly. Final sample date ranges are 2013-02-26–
2017-12-03 and 2011-03-26–2016-04-24, with 56 strictly prior dates required.
M5 temporal-quarter label counts are 45,726 / 45,846 / 45,600 / 45,768;
Store Item counts are 37,587 / 37,413 / 37,585 / 37,415. All initial demand classes
remain represented. Zero-demand histories are retained; this is bounded supervised
training across complete series populations, not training on every eligible label.

## Integrity and limits

Both datasets' eight complete model/comparator forecast bundles were sealed before
the first canonical target read: 3,470,880 forecasts, zero duplicate keys and all
28 steps. Each canonical holdout was scanned once. Later audited actual-snapshot
reads are explicitly logged and anchored to the original canonical-read receipt.
The assessment took 26.61 seconds with peak OS working set 1,033.76 MiB.

All nine raw/canonical source hashes and the original protocol remain unchanged.
Phase 3 experiment artifacts were preserved. The only post-assessment presentation
repair wraps crowded M5 class tick labels; its helper, input metric hashes and
before/after figure hashes are recorded separately. No frozen scientific code,
model, prediction or metric artifact was altered.

The internal review found no remaining critical/high scientific defect within this
research scope. Preserve the price-availability, limited seasonal coverage,
bounded-training, observed-sales and no-inventory-savings caveats in
[PHASE4_LIMITATIONS.md](PHASE4_LIMITATIONS.md). Browser rendering remains unverified
because automated local file navigation was blocked; image decoding, relative
links, SVG parsing and visual figure inspection passed. The separate Claude audit
remains mandatory before Phase 5, which has not started.
