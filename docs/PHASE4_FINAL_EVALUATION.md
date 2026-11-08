# Phase 4 final scientific forecasting report

Daily H28 point forecasting on Store Item (500 series; 913,000 historical rows; 2013–2017) and M5 (30,490 series; 59,181,090 historical rows; 2011–2016). Assess whether compact global ML and statistical candidates improve over simple baselines under origin-bounded information. All comparisons are full-population.

## Experimental method

The four original expanding validation origins are unchanged. A seed-42 finite random search evaluated 23 tuning configurations and four unchanged references, each on four origins. Primary selection is the equal-origin mean of equal-series MAE. Secondary errors use full-history seasonal-7 training scales; pooled RMSE and WAPE aggregate squared/absolute errors and actual totals. No early stopping, adaptive budget expansion, holdout screening or population mismatch was used. Store Item families: LightGBM, Random Forest, Holt-Winters; references: Seasonal Naive and Seasonal Moving Average. M5: price-free RF/LightGBM and TSB; references: SN and MA28.

| dataset | series | labels | labels per series | eligible final labels | sample % |
|---|---|---|---|---|---|
| store_item | 500 | 150000 | 300 | 871000 | 17.22158438576349 |
| m5 | 30490 | 182940 | 6 | 56619930 | 0.32310177705977383 |

## Frozen final assessment

Manifest a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb at 2026-11-07T12:41:37.811576+00:00 UTC fixes exact models, features, sample rules and comparators. Final origins are 2017-12-03 and 2016-04-24. Both datasets' entire forecast/model bundle was sealed before the first target scan. Each canonical holdout was read once; subsequent audit and report calculations use checksummed actual snapshots with logged access. The selected designation remains fixed even when a comparator performs better.

| dataset | trial | role | mae | mase | rmsse | pooled_bias_percent | pooled_bias_units | pooled_mae | pooled_rmse | pooled_wape_percent | series | observations | fallback | clipped | fallback_percent | undefined_mase | undefined_rmsse | undefined_wape | fit_seconds | prediction_seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| m5 | m5_random_forest_02 | selected | 1.0472313706239513 | 1.6370356807541435 | 0.8976460386236976 | -3.6386699631179837 | -0.05249944558461861 | 1.0472313706239513 | 2.2010631536752236 | 72.5822775896259 | 30490 | 853720 | 0 | 0 | 0.0 | 0 | 0 | 812 | 31.476432999945246 | 13.358177199959755 |
| m5 | m5_seasonal_naive_reference | comparator | 1.2439722625685237 | 1.8101435299554276 | 1.1782638799940646 | -7.359201925044083 | -0.10618001218198005 | 1.2439722625685237 | 2.6768948977123297 | 86.2181391890005 | 30490 | 853720 | 0 | 0 | 0.0 | 0 | 0 | 812 | 0.05828629992902279 | 6.047488000011072 |
| m5 | m5_moving_average_28_reference | comparator | 1.0657293123874672 | 1.6106176061344133 | 0.9048751402500037 | -3.908053815503619 | -0.056386168767277325 | 1.0657293123874674 | 2.242952959753161 | 73.86434646339954 | 30490 | 853720 | 0 | 0 | 0.0 | 0 | 0 | 812 | 0.059387800050899386 | 6.15830739994999 |
| m5 | m5_tsb_01 | comparator | 1.0631929665576478 | 1.6247120192718778 | 0.9159553271632571 | -1.8750779096360863 | -0.02705399271757701 | 1.0631929665576478 | 2.208269197884313 | 73.6885555520047 | 30490 | 853720 | 0 | 0 | 0.0 | 0 | 0 | 812 | 3.6290217000059783 | 5.9661561999237165 |
| store_item | store_item_lightgbm_00 | selected | 5.434342530628236 | 0.6567390423570336 | 0.6445638871980043 | -0.6576168641383607 | -0.2915304806728343 | 5.434342530628236 | 7.06697597219678 | 12.258461912447542 | 500 | 14000 | 0 | 0 | 0.0 | 0 | 0 | 0 | 2.56372060009744 | 0.10503279999829829 |
| store_item | store_item_seasonal_naive_reference | comparator | 12.814642857142857 | 1.504507045860958 | 1.433303572448867 | 20.705273113678 | 9.178928571428571 | 12.814642857142857 | 16.701995175940596 | 28.906497980307392 | 500 | 14000 | 0 | 0 | 0.0 | 0 | 0 | 0 | 0.012240099953487515 | 0.04805169999599457 |
| store_item | store_item_seasonal_moving_average_reference | comparator | 15.807285714285713 | 1.820069244472586 | 1.5853869319500067 | 35.19066639382959 | 15.6005 | 15.807285714285713 | 18.891610949988205 | 35.65712112838542 | 500 | 14000 | 0 | 0 | 0.0 | 0 | 0 | 0 | 0.011712500010617077 | 0.047975099994800985 |
| store_item | store_item_holt_winters_additive_01 | comparator | 10.651093200657884 | 1.243443621111095 | 1.1269063023088488 | 22.426480746564042 | 9.9419632743334 | 10.651093200657884 | 13.29905468539764 | 24.02609323764868 | 500 | 14000 | 0 | 0 | 0.0 | 0 | 0 | 0 | 0.03312069992534816 | 0.0496112999971956 |

## Validation versus final holdout

| dataset | trial | role | validation MAE | final MAE | baseline gain % |
|---|---|---|---|---|---|
| m5 | m5_random_forest_02 | selected | 1.0200669850841517 | 1.0472313706239513 | 1.735707327227054 |
| m5 | m5_seasonal_naive_reference | comparator | 1.2119995431757487 | 1.2439722625685237 | -16.72497397878203 |
| m5 | m5_moving_average_28_reference | comparator | 1.0337792250386544 | 1.0657293123874672 | 0.0 |
| m5 | m5_tsb_01 | comparator | 1.0341311023582396 | 1.0631929665576478 | 0.23799156130344112 |
| store_item | store_item_lightgbm_00 | selected | 6.308039821969917 | 5.434342530628236 | 57.592711781279625 |
| store_item | store_item_seasonal_naive_reference | comparator | 9.154964285714286 | 12.814642857142857 | 0.0 |
| store_item | store_item_seasonal_moving_average_reference | comparator | 8.086651785714285 | 15.807285714285713 | -23.35330676402552 |
| store_item | store_item_holt_winters_additive_01 | comparator | 7.043324262632043 | 10.651093200657884 | 16.883417513887355 |

## Interpretation

store_item: the frozen selection `store_item_lightgbm_00` has final MAE 5.434342531. The lowest observed final MAE among predeclared candidates is `store_item_lightgbm_00` (5.434342531); this descriptive comparison does not replace the frozen selection or authorise retuning.

m5: the frozen selection `m5_random_forest_02` has final MAE 1.047231371. The lowest observed final MAE among predeclared candidates is `m5_random_forest_02` (1.047231371); this descriptive comparison does not replace the frozen selection or authorise retuning.

## Threats to validity and limitations

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

See PHASE4_TUNING_RESULTS.md for exact trial configurations, anchor gains and paired M5 stability; PHASE4_REPRODUCIBILITY.md for saved-artifact commands.

See the authored [scientific review](PHASE4_SCIENTIFIC_REVIEW.md) for exact metric trade-offs, actual final sample coverage and qualified interpretation. MA28 has better M5 macro MASE than the selected RF; the frozen primary-MAE selection was not changed.
