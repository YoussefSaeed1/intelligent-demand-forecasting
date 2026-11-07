# Phase 3 final scientific integrity review — 2026-11-07

Assessment: **Ready within the reviewed research-benchmark scope, with explicit caveats.** No critical or high-severity scientific defect remains. Phase 4 is not started. The separately requested local checkpoint is authorised after the security review.

## Evidence and independent method

The new `evaluation/final_review.py` joins each persisted prediction file to freshly read canonical validation rows, verifies its exact schema/keys/origin and compares raw/clipped predictions and delivery classifications. It calculates per-series MAE, four-origin macro MAE, pooled squared-error RMSE and ratio-of-sums WAPE without calling the original scorer, prior audit metric helper or report aggregation helper. All 224 evaluations and 45,296,160 forecast records passed, including exact parent/subset prediction equality. None was refitted. The 56 summary rows and all 56 HTML table rows agree with these recalculations at their displayed precision.

The successful read-only review took 238.65 seconds with peak OS working set 1465.91 MiB. A first review attempt stopped on a Pandas object-versus-datetime comparison in the new helper; both dates were then normalised identically, with strict persisted Arrow schema and exact values retained. No source or forecast file was changed.

## Recalculated full-population comparisons

| Dataset | Model | Four-origin macro MAE | Pooled RMSE | Pooled WAPE % |
|---|---|---|---|---|
| store_item | seasonal_naive | 9.154964286 | 12.023970107 | 15.004062 |
| store_item | lightgbm | 6.308039822 | 8.178518666 | 10.338240 |
| store_item | random_forest | 6.885315930 | 8.990946670 | 11.284338 |
| m5 | seasonal_naive | 1.211999543 | 2.859957946 | 89.412517 |
| m5 | moving_average_28 | 1.033779225 | 2.342793087 | 76.264718 |
| m5 | random_forest | 1.027612203 | 2.308980235 | 75.809759 |
| m5 | lightgbm | 1.070783081 | 2.451282619 | 78.994593 |

Store Item LightGBM improves MAE by **31.097057%** against Seasonal Naive and leads the current fixed-configuration comparisons. M5 RF improves on MA28 by **0.596551%**, an absolute 0.006167022 units per daily observation. RF leads the primary full-population validation objective conditionally on the documented historical-price assumption; it is not a universally superior series-level method.

| Fold / origin | RF MAE | MA28 MAE | RF minus MA28 | Series favouring RF | Series favouring MA28 | Median series difference |
|---|---|---|---|---|---|---|
| 1 / 2016-01-03 | 1.000623350 | 1.014950034 | -0.014326684 | 14710 | 15780 | +0.001886584 |
| 2 / 2016-01-31 | 1.032886007 | 1.033280734 | -0.000394727 | 12852 | 17638 | +0.009579917 |
| 3 / 2016-02-28 | 1.046143873 | 1.045754128 | +0.000389745 | 13337 | 17153 | +0.007554207 |
| 4 / 2016-03-27 | 1.030795582 | 1.041132004 | -0.010336422 | 14786 | 15704 | +0.001672668 |

RF wins three origin means; MA28 wins the third. MA28 has lower errors on a majority of series in every origin, and the median RF-minus-MA28 difference is positive in every origin. RF improvements on other series are larger in magnitude. This supports a narrow mean-MAE lead, not broad dominance. No significance test, economic loss function, inventory simulation or final holdout establishes practical business value; adjacent folds cannot be treated as independent replications. Keep MA28 as a strong, cheaper reference.

## Full population versus matched subsets

| Dataset | Population | Model | Macro MAE |
|---|---|---|---|
| store_item | full | lightgbm | 6.308039822 |
| store_item | full | random_forest | 6.885315930 |
| store_item | full | moving_average_28 | 9.538295918 |
| store_item | statistical_subset | lightgbm | 6.508390773 |
| store_item | statistical_subset | random_forest | 7.149213609 |
| store_item | statistical_subset | moving_average_28 | 9.984272719 |
| m5 | full | lightgbm | 1.070783081 |
| m5 | full | random_forest | 1.027612203 |
| m5 | full | moving_average_28 | 1.033779225 |
| m5 | statistical_subset | lightgbm | 2.266888325 |
| m5 | statistical_subset | random_forest | 2.232426296 |
| m5 | statistical_subset | moving_average_28 | 2.147421469 |

All 13 full-population methods use identical 500/30,490-series evaluation grids. All 15 subset methods use the same frozen 53/51 series, dates and observations. M5 MA28 wins the subset (2.147421469), while RF is 2.232426296. The reversal is descriptive: deliberately stratified unweighted subsets are not population estimators. ARIMA/SARIMA have fixed initial orders and explicit fallbacks; their subset scores cannot reject their entire families or be ranked against unmatched population means. Projected global models retain full-population training context, so matched evaluation is not identical training data.

## Persisted ML training sample audit

| Dataset/fold | Rows | Rows/series | Label dates / eligible | Target range | Zero labels | All-zero 56-day histories |
|---|---|---|---|---|---|---|
| store_item/1 | 150000 | 300 | 1630/1630 | 2013-02-26–2017-08-13 | 0 | 0 |
| store_item/2 | 150000 | 300 | 1658/1658 | 2013-02-26–2017-09-10 | 0 | 0 |
| store_item/3 | 150000 | 300 | 1686/1686 | 2013-02-26–2017-10-08 | 0 | 0 |
| store_item/4 | 150000 | 300 | 1714/1714 | 2013-02-26–2017-11-05 | 0 | 0 |
| m5/1 | 182940 | 6 | 1745/1745 | 2011-03-26–2016-01-03 | 125438 | 50897 |
| m5/2 | 182940 | 6 | 1773/1773 | 2011-03-26–2016-01-31 | 125104 | 50309 |
| m5/3 | 182940 | 6 | 1801/1801 | 2011-03-26–2016-02-28 | 124818 | 49722 |
| m5/4 | 182940 | 6 | 1829/1829 | 2011-03-26–2016-03-27 | 124314 | 49112 |

For both estimators and all eight dataset/origin samples, persisted position arrays exactly reproduce seed 42 and the equal series/time-stratum design. Every label and all 27/32 features reconcile to strictly historical source values. Every series contributes 300 Store Item or six M5 rows; all 10 stores and all 50/3,049 products are represented, along with every initial demand class. There is no outcome filter. All eligible dates appear somewhere in each aggregate sample, but a single M5 series has only six labels and therefore no guaranteed monthly or weekly balance.

M5 zero labels are 68.57%, 68.39%, 68.23% and 67.95%; 16/10/0/0 entirely zero training series remain represented with 96/60/0/0 labels. Store Item has no sampled zero labels: its single source zero on 2014-01-15 was not selected by the outcome-independent random label positions. It was not removed from history. Only 17.50–18.40% of eligible Store Item labels and 0.328–0.344% of eligible M5 labels are sampled. Fixed sample budgets shrink the training fraction as origins expand. Results do not measure all-row training potential. The first 56 target labels are ineligible for lag prerequisites.

## Feature availability and recursion

| Feature group | Information status | Verified rule / remaining assumption |
|---|---|---|
| Lags 1/7/14/28/56, shifted means 7/28/56, std 7/28 | Historical observed, then own predictions | Training sources predate their label; recursive updates use clipped point predictions, never validation actuals |
| Zero fractions, count, ADI, positive CV², last-positive age | Historical observed | Computed from 56 prior days at each training row; frozen at the true inference origin; undefined values remain NaN |
| Weekday, month, day, weekend, sine/cosine, calendar trend | Known future | Only deterministic target dates; no sales-derived calendar encodings |
| Store/product/category/department/state IDs | Static within fixed benchmark universe | Target-free sorted identifier mappings; RF ordinal codes versus native LightGBM categories; no EDA target totals/classes as features |
| M5 price mean and missing fraction | Conditionally available historical observations | 28 records t−34..t−7; frozen snapshot for recursion; every source week completed; actual publication latency unverified |
| SNAP/events/future prices | Unavailable or advance availability unsupported | Excluded from the actual feature schemas |

Calendar-only checks prove source-week completion for all 7,148 eligible M5 target dates across origins. The last inference source weeks end 2016-01-01, 01-29, 02-26 and 03-25, each before its origin. This is not proof of publication time. Price-enabled M5 results are explicitly conditional research evidence; live availability is not approved. Obtain release evidence or use a separately authorised price-free experiment before operational claims. Missing prices remain NaN/explicit missing fractions, not zeros or backfills. Static universe knowledge is also a benchmark contract, not a test of unseen future products.

## Coverage, fallbacks and conclusions

All declared series/date grids are complete with zero duplicate keys. Delivery classifications agree for all 224 evaluations and projected raw predictions match their parents exactly. ML has zero fallback cases; 21,038 full-population M5 LightGBM predictions retain negative raw values and explicit common-policy clipping flags. Statistical all-zero, insufficient-positive and convergence fallbacks are kept in delivered-system scores; native-only diagnostics have different populations and cannot be used for unmatched rankings.

Intermittent-demand evidence does not justify a single family winner. In the existing verified class breakdown MA28 leads intermittent and insufficient-positive-history M5 classes, RF leads smooth/erratic/lumpy, and TSB leads the initially all-zero class. These classes are frozen initial-training descriptors, not classes retrospectively computed from validation. Store Item LightGBM is the leading current validation candidate; M5 RF is the conditional full-population candidate, with MA28 a close and important reference. Final holdout evaluation after choices freeze is still required.

## Severity and readiness

| Severity | Remaining issue | Disposition |
|---|---|---|
| Critical / high | None demonstrated in reviewed scientific gates | Checkpoint permitted for the declared research scope |
| Medium assumption | Historical price publication latency unavailable | Conditional M5 research results; operational availability unresolved, not silently approved |
| Medium limitation | Very sparse M5 training labels, fixed parameters and deliberate statistical subsets | No population extrapolation or family-ceiling claims |
| Medium interpretation | Small RF gain, majority-series reversal and adjacent folds | No significance or business-value claim; retain MA28 |
| Low reproducibility defect — fixed | QA previously rejected authorised descendant commits | Ancestry/frozen-protocol checks retained; optional ignored evidence output supports clean checkpoint verification |
| Low presentation limitation | Automated browser preview blocked by file URL policy | Unchanged image evidence reused; current image parsing, 34 local links and 56 HTML values checked; no workaround/upload |

Validation: **320 tests passed in 49.76 seconds**; Ruff and pip check passed separately. Raw/canonical hashes are unchanged (nine files); original protocol Markdown and split manifest are unchanged. Origin capability checks, cache bounds, sampled labels/features and future-poison tests show no protected final targets supplied to fitting or scoring. Whole-file byte hashes are integrity operations, not target analysis. No actual-data model was retrained.

Phase 4 is ready for separate authorisation within this research scope; it has not started. The mandatory independent Claude audit remains after Phase 4 and before Phase 5. This internal review does not replace it.

Reproduce without fitting: `python -m intelligent_demand.evaluation.final_review`; then `python -m intelligent_demand.reporting.phase3_qa --output artifacts/experiments/phase3/checkpoint_post_commit_qa.json`. The review needs existing local source, prediction, feature-cache and registry files. Fresh reconstruction from immutable sources uses the documented EDA, benchmark, audit and gate commands; missing fitted runs require explicitly invoking the experiment runner. No ignored output was deleted to test regeneration.

Evidence: [direct audit JSON](../reports/forecasting/phase3_integrity_review.json), [price audit](../reports/forecasting/phase3_price_availability_review.json), [feature contract](FEATURE_AVAILABILITY.md), [original results](PHASE3_BENCHMARK_REPORT.md), and the ignored local test/security logs.
