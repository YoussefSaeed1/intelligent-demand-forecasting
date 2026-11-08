# Phase 4 tuning results — validation only

All 27 cases (23 tuning, four unchanged references), 108 fold runs and 45,177,440 forecasts passed independent NumPy reconciliation. No final targets were accessed in tuning.

## Best configuration per family

| dataset | trial | MAE | pooled RMSE | WAPE % | bias units | MASE | RMSSE | seconds | peak MiB |
|---|---|---|---|---|---|---|---|---|---|
| store_item | store_item_holt_winters_additive_01 | 7.043324262632043 | 9.320687258183877 | 11.543297333376483 | -0.33368510017250635 | 0.8544313604922111 | 0.8449193703050857 | 10.31037149997428 | 172.74609375 |
| store_item | store_item_lightgbm_00 | 6.308039821969917 | 8.178518665758851 | 10.338240373526027 | 0.037027736588672734 | 0.7687659028238478 | 0.7541757898510983 | 23.537820000201464 | 259.21484375 |
| store_item | store_item_random_forest_01 | 6.8774277806848385 | 8.991606148487843 | 11.271409749293838 | 0.4553240208487165 | 0.8347689807671183 | 0.8190772601354528 | 51.33503660024144 | 259.39453125 |
| store_item | store_item_seasonal_moving_average_reference | 8.086651785714285 | 10.59976941292323 | 13.253205803575609 | 2.8175535714285713 | 0.972851289508741 | 0.9499425181945883 | 10.239774100016803 | 171.625 |
| store_item | store_item_seasonal_naive_reference | 9.154964285714286 | 12.02397010736708 | 15.004062128321111 | 0.7970714285714285 | 1.1119000170860696 | 1.091962730487542 | 10.219182599917985 | 168.2890625 |
| m5 | m5_lightgbm_00 | 1.0731372984028256 | 2.463333749773573 | 79.16827012029896 | 0.0013846596863889382 | 1.8068962525903627 | 0.8870628982214224 | 141.856918200152 | 1212.421875 |
| m5 | m5_moving_average_28_reference | 1.0337792250386544 | 2.342793087218419 | 76.26471752908185 | -0.05150049196457855 | 1.6648321715405545 | 0.8706623341013364 | 77.7514551000204 | 1125.83203125 |
| m5 | m5_random_forest_02 | 1.0200669850841517 | 2.3115124029178165 | 75.25312812827721 | -0.03795128803732497 | 1.7128139754767135 | 0.8664789060806025 | 248.61277980008163 | 1232.36328125 |
| m5 | m5_seasonal_naive_reference | 1.2119995431757487 | 2.859957945565858 | 89.41251726374992 | -0.07769965562479501 | 1.8770378695309473 | 1.1369927187882933 | 71.11183509987313 | 1129.76171875 |
| m5 | m5_tsb_01 | 1.0341311023582396 | 2.3301273845860564 | 76.29067648021287 | -0.023465921500201277 | 1.6783337616831469 | 0.8807509387918842 | 87.40021590003744 | 1088.48046875 |

## Origin-by-origin macro MAE

| trial | origin 1 | origin 2 | origin 3 | origin 4 |
|---|---|---|---|---|
| store_item_holt_winters_additive_01 | 6.872005886334718 | 6.609829902192527 | 6.770359515583637 | 7.921101746417289 |
| store_item_lightgbm_00 | 6.492088088665719 | 6.260136069670047 | 6.157554588806195 | 6.322380540737706 |
| store_item_random_forest_01 | 6.976893814365068 | 6.49096141605754 | 6.441741282268318 | 7.600114610048427 |
| store_item_seasonal_moving_average_reference | 9.131964285714286 | 7.773892857142857 | 7.099678571428571 | 8.341071428571427 |
| store_item_seasonal_naive_reference | 9.153214285714286 | 8.783928571428573 | 8.577285714285713 | 10.105428571428572 |
| m5_lightgbm_00 | 1.0313267887432076 | 1.0726866074323465 | 1.088227689464696 | 1.1003081079710528 |
| m5_moving_average_28_reference | 1.014950033801648 | 1.0332807343993682 | 1.0457541281517526 | 1.0411320038018488 |
| m5_random_forest_02 | 0.9986903229382016 | 1.0195172344666987 | 1.0345736584988314 | 1.0274867244328751 |
| m5_seasonal_naive_reference | 1.2055755985569039 | 1.1994494682097177 | 1.210618235487045 | 1.2323548704493277 |
| m5_tsb_01 | 1.0101687994289086 | 1.0368755531147937 | 1.0431494049193253 | 1.0463306519699302 |

## Demand-class validation

| trial | pattern | series | four-origin MAE |
|---|---|---|---|
| store_item_holt_winters_additive_01 | smooth | 500 | 7.043324262632043 |
| store_item_lightgbm_00 | smooth | 500 | 6.308039821969917 |
| store_item_random_forest_01 | smooth | 500 | 6.8774277806848385 |
| store_item_seasonal_moving_average_reference | smooth | 500 | 8.086651785714285 |
| store_item_seasonal_naive_reference | smooth | 500 | 9.154964285714286 |
| m5_lightgbm_00 | all_zero | 16 | 0.7106724535069346 |
| m5_lightgbm_00 | erratic | 489 | 3.9721324230609465 |
| m5_lightgbm_00 | insufficient_positive_history | 5 | 0.6178840074346166 |
| m5_lightgbm_00 | intermittent | 23044 | 0.7851626996030243 |
| m5_lightgbm_00 | lumpy | 5953 | 1.639498229638437 |
| m5_lightgbm_00 | smooth | 983 | 2.9602249068589637 |
| m5_moving_average_28_reference | all_zero | 16 | 0.7042809311224489 |
| m5_moving_average_28_reference | erratic | 489 | 3.6739167292683943 |
| m5_moving_average_28_reference | insufficient_positive_history | 5 | 0.5403061224489796 |
| m5_moving_average_28_reference | intermittent | 23044 | 0.7617344005168463 |
| m5_moving_average_28_reference | lumpy | 5953 | 1.5659552120865143 |
| m5_moving_average_28_reference | smooth | 983 | 2.8828833796997944 |
| m5_random_forest_02 | all_zero | 16 | 0.7251630306688535 |
| m5_random_forest_02 | erratic | 489 | 3.5462278057710983 |
| m5_random_forest_02 | insufficient_positive_history | 5 | 0.558594772998544 |
| m5_random_forest_02 | intermittent | 23044 | 0.7549645173629091 |
| m5_random_forest_02 | lumpy | 5953 | 1.550471757066888 |
| m5_random_forest_02 | smooth | 983 | 2.773123792378396 |
| m5_seasonal_naive_reference | all_zero | 16 | 0.8119419642857142 |
| m5_seasonal_naive_reference | erratic | 489 | 4.458990651475315 |
| m5_seasonal_naive_reference | insufficient_positive_history | 5 | 0.6089285714285715 |
| m5_seasonal_naive_reference | intermittent | 23044 | 0.882492653805143 |
| m5_seasonal_naive_reference | lumpy | 5953 | 1.8513969547167093 |
| m5_seasonal_naive_reference | smooth | 983 | 3.4586542653684056 |
| m5_tsb_01 | all_zero | 16 | 0.7150085352760419 |
| m5_tsb_01 | erratic | 489 | 3.638325142922116 |
| m5_tsb_01 | insufficient_positive_history | 5 | 0.561233188015751 |
| m5_tsb_01 | intermittent | 23044 | 0.7637411499148352 |
| m5_tsb_01 | lumpy | 5953 | 1.5650433251024256 |
| m5_tsb_01 | smooth | 983 | 2.86970095680275 |

## Independently verified training samples

| dataset | fold | labels | labels_per_series | series | stores | products | zero_label_percent | earliest_label | latest_label | eligible_label_fraction |
|---|---|---|---|---|---|---|---|---|---|---|
| store_item | 1 | 150000 | 300 | 500 | 10 | 50 | 0.0 | 2013-02-26 | 2017-08-13 | 0.18404907975460122 |
| store_item | 2 | 150000 | 300 | 500 | 10 | 50 | 0.0 | 2013-02-26 | 2017-09-10 | 0.18094089264173704 |
| store_item | 3 | 150000 | 300 | 500 | 10 | 50 | 0.0 | 2013-02-26 | 2017-10-08 | 0.17793594306049823 |
| store_item | 4 | 150000 | 300 | 500 | 10 | 50 | 0.0 | 2013-02-26 | 2017-11-05 | 0.1750291715285881 |
| m5 | 1 | 182940 | 6 | 30490 | 10 | 3049 | 68.567836449109 | 2011-03-26 | 2016-01-03 | 0.0034383954154727794 |
| m5 | 2 | 182940 | 6 | 30490 | 10 | 3049 | 68.38526292773587 | 2011-03-26 | 2016-01-31 | 0.00338409475465313 |
| m5 | 3 | 182940 | 6 | 30490 | 10 | 3049 | 68.22892751721876 | 2011-03-26 | 2016-02-28 | 0.003331482509716824 |
| m5 | 4 | 182940 | 6 | 30490 | 10 | 3049 | 67.95342735323057 | 2011-03-26 | 2016-03-27 | 0.0032804811372334607 |

Every cached position array exactly reproduces seed-42 draws within equal time strata for every series. Initial demand classes and all stores/products are retained; quartile counts and class coverage are in the machine-readable gate. Zero labels remain in the samples. Four-origin worker cost totals 2064.9 seconds; largest observed worker RSS is 1239.7 MiB. Trial statuses must all be completed before this report is permitted; failed and interrupted attempts cannot supply a partial ranking.

## Improvements over price-free initial anchors

| dataset | family | anchor MAE | best MAE | gain % |
|---|---|---|---|---|
| store_item | holt_winters_additive | 7.7016504241642 | 7.043324262632043 | 8.54785825472726 |
| store_item | lightgbm | 6.308039821969917 | 6.308039821969917 | 0.0 |
| store_item | random_forest | 6.885315930372303 | 6.8774277806848385 | 0.11456481833561627 |
| m5 | lightgbm | 1.0731372984028256 | 1.0731372984028256 | 0.0 |
| m5 | random_forest | 1.0267481939178014 | 1.0200669850841517 | 0.6507154210961819 |
| m5 | tsb | 1.042454921001442 | 1.0341311023582396 | 0.7984823588540468 |

M5 Phase 3 price-enabled RF/LightGBM are conditional references; the matched Phase 4 price-free anchors above isolate tuning from price availability changes.

## M5 paired RF versus MA28

| fold | rf_minus_ma28_mae | rf_series_win_percent | ma28_series_win_percent | tie_percent |
|---|---|---|---|---|
| 1 | -0.016259710863446384 | 48.17973105936373 | 51.73827484421122 | 0.0819940964250574 |
| 2 | -0.0137634999326695 | 46.73335519842571 | 53.20432928829124 | 0.062315513283043626 |
| 3 | -0.011180469652921302 | 48.8520826500492 | 51.042964906526734 | 0.10495244342407348 |
| 4 | -0.013645279368973504 | 49.79009511315186 | 50.15414890127911 | 0.05575598556903903 |

Negative RF-minus-MA28 values favour RF; series wins weight every series equally. Four origins give descriptive stability evidence, not significance or business value.

The best price-free RF reduces mean validation MAE by 1.326419% versus MA28. RF has lower origin-mean errors in 4 of four windows; MA28 wins a majority of individual series in 4 of four windows. Mean improvement therefore does not establish broad series-level dominance.

Protocol-selected cases: `{'store_item': 'store_item_lightgbm_00', 'm5': 'm5_random_forest_02'}`. Selection uses four-origin macro MAE; only exact 1e-12 ties invoke the frozen simplicity order.

## Exact best configurations

```json
[
  {
    "trial_id": "store_item_holt_winters_additive_01",
    "parameters": {
      "alpha": 0.1,
      "arima_order": [
        1,
        0,
        0
      ],
      "damping_phi": 0.98,
      "maximum_likelihood_iterations": 80,
      "occurrence_beta": 0.1,
      "sarima_order": [
        1,
        0,
        0
      ],
      "sarima_seasonal_order": [
        1,
        0,
        0,
        7
      ],
      "schema_version": 1,
      "season": 7,
      "seasonal_gamma": 0.02,
      "subset_primary_strata": [
        "pattern",
        "store_id"
      ],
      "subset_seed": 42,
      "subset_volume_bands": 3,
      "trend_beta": 0.05
    },
    "configuration_sha256": "b037ae42bc706d5b5ab8c2624ad26c6f16549b741fb433867c521ac1171af4e3"
  },
  {
    "trial_id": "store_item_lightgbm_00",
    "parameters": {
      "feature_batch_rows": 8192,
      "feature_history_days": 56,
      "lightgbm": {
        "bagging_fraction": 1.0,
        "bagging_freq": 0,
        "deterministic": true,
        "device_type": "cpu",
        "feature_fraction": 1.0,
        "force_col_wise": true,
        "lambda_l1": 0.0,
        "lambda_l2": 0.0,
        "learning_rate": 0.05,
        "max_bin": 63,
        "max_depth": -1,
        "min_data_in_leaf": 50,
        "min_data_per_group": 20,
        "num_boost_round": 200,
        "num_leaves": 31,
        "objective": "regression",
        "verbosity": -1
      },
      "random_forest": {
        "criterion": "squared_error",
        "max_depth": 12,
        "max_features": 0.8,
        "max_leaf_nodes": 512,
        "max_samples": 0.7,
        "min_samples_leaf": 20,
        "n_estimators": 80
      },
      "schema_version": 1,
      "strategy": "recursive_28",
      "use_historical_prices": false
    },
    "configuration_sha256": "f17ad7740cef3af3745e2253a113492539abbe5f5850046cc29609b62b6c9e02"
  },
  {
    "trial_id": "store_item_random_forest_01",
    "parameters": {
      "feature_batch_rows": 8192,
      "feature_history_days": 56,
      "lightgbm": {
        "deterministic": true,
        "device_type": "cpu",
        "force_col_wise": true,
        "learning_rate": 0.05,
        "max_bin": 63,
        "min_data_in_leaf": 50,
        "min_data_per_group": 20,
        "num_boost_round": 200,
        "num_leaves": 31,
        "objective": "regression",
        "verbosity": -1
      },
      "random_forest": {
        "criterion": "squared_error",
        "max_depth": 12,
        "max_features": 0.6,
        "max_leaf_nodes": 512,
        "max_samples": 0.7,
        "min_samples_leaf": 40,
        "min_samples_split": 20,
        "n_estimators": 80
      },
      "schema_version": 1,
      "strategy": "recursive_28",
      "use_historical_prices": false
    },
    "configuration_sha256": "1bb9c417304ea1c2813a32c2afaae8d930cdd50cdeb107e9a9a694c3005cfb96"
  },
  {
    "trial_id": "store_item_seasonal_moving_average_reference",
    "parameters": {},
    "configuration_sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
  },
  {
    "trial_id": "store_item_seasonal_naive_reference",
    "parameters": {},
    "configuration_sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
  },
  {
    "trial_id": "m5_lightgbm_00",
    "parameters": {
      "feature_batch_rows": 8192,
      "feature_history_days": 56,
      "lightgbm": {
        "bagging_fraction": 1.0,
        "bagging_freq": 0,
        "deterministic": true,
        "device_type": "cpu",
        "feature_fraction": 1.0,
        "force_col_wise": true,
        "lambda_l1": 0.0,
        "lambda_l2": 0.0,
        "learning_rate": 0.05,
        "max_bin": 63,
        "max_depth": -1,
        "min_data_in_leaf": 50,
        "min_data_per_group": 20,
        "num_boost_round": 200,
        "num_leaves": 31,
        "objective": "regression",
        "verbosity": -1
      },
      "random_forest": {
        "criterion": "squared_error",
        "max_depth": 12,
        "max_features": 0.8,
        "max_leaf_nodes": 512,
        "max_samples": 0.7,
        "min_samples_leaf": 20,
        "n_estimators": 80
      },
      "schema_version": 1,
      "strategy": "recursive_28",
      "use_historical_prices": false
    },
    "configuration_sha256": "f17ad7740cef3af3745e2253a113492539abbe5f5850046cc29609b62b6c9e02"
  },
  {
    "trial_id": "m5_moving_average_28_reference",
    "parameters": {},
    "configuration_sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
  },
  {
    "trial_id": "m5_random_forest_02",
    "parameters": {
      "feature_batch_rows": 8192,
      "feature_history_days": 56,
      "lightgbm": {
        "deterministic": true,
        "device_type": "cpu",
        "force_col_wise": true,
        "learning_rate": 0.05,
        "max_bin": 63,
        "min_data_in_leaf": 50,
        "min_data_per_group": 20,
        "num_boost_round": 200,
        "num_leaves": 31,
        "objective": "regression",
        "verbosity": -1
      },
      "random_forest": {
        "criterion": "squared_error",
        "max_depth": 16,
        "max_features": 0.8,
        "max_leaf_nodes": 512,
        "max_samples": 0.7,
        "min_samples_leaf": 20,
        "min_samples_split": 20,
        "n_estimators": 160
      },
      "schema_version": 1,
      "strategy": "recursive_28",
      "use_historical_prices": false
    },
    "configuration_sha256": "fb5592e84ff97c25563d9fdde4ae04390c3e0c9f131b8a6c625aa61ff6937477"
  },
  {
    "trial_id": "m5_seasonal_naive_reference",
    "parameters": {},
    "configuration_sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
  },
  {
    "trial_id": "m5_tsb_01",
    "parameters": {
      "alpha": 0.1,
      "arima_order": [
        1,
        0,
        0
      ],
      "damping_phi": 0.98,
      "maximum_likelihood_iterations": 80,
      "occurrence_beta": 0.2,
      "sarima_order": [
        1,
        0,
        0
      ],
      "sarima_seasonal_order": [
        1,
        0,
        0,
        7
      ],
      "schema_version": 1,
      "season": 7,
      "seasonal_gamma": 0.05,
      "subset_primary_strata": [
        "pattern",
        "store_id"
      ],
      "subset_seed": 42,
      "subset_volume_bands": 3,
      "trend_beta": 0.05
    },
    "configuration_sha256": "894e79e5dcbd2c763488e6396b74724b7cfd5e3afa045137b1a4d57b4cfbf9db"
  }
]
```

## Limitations

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
