# Frozen Phase 4 model selection

Frozen before final target access at 2026-11-07T12:41:37.811576+00:00 UTC; manifest SHA-256 `a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb`. Git revision `6e1a407de0b676e858ffec43bab1fae8d51dae1d` plus immutable checksummed scientific code/config snapshot. No Git commit or push was needed.

## store_item

Selected: `store_item_lightgbm_00`. Final origin 2017-12-03; 28 targets 2017-12-04–2017-12-31; 500 series.

- selected: `store_item_lightgbm_00` / lightgbm; validation MAE 6.308039822; configuration `f17ad7740cef3af3745e2253a113492539abbe5f5850046cc29609b62b6c9e02`.
- comparator: `store_item_seasonal_naive_reference` / seasonal_naive; validation MAE 9.154964286; configuration `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a`.
- comparator: `store_item_seasonal_moving_average_reference` / seasonal_moving_average; validation MAE 8.086651786; configuration `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a`.
- comparator: `store_item_holt_winters_additive_01` / holt_winters_additive; validation MAE 7.043324263; configuration `b037ae42bc706d5b5ab8c2624ad26c6f16549b741fb433867c521ac1171af4e3`.

Exact immutable hyperparameters:

```json
[
  {
    "trial_id": "store_item_lightgbm_00",
    "dataset": "store_item",
    "model": "lightgbm",
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
    "configuration_sha256": "f17ad7740cef3af3745e2253a113492539abbe5f5850046cc29609b62b6c9e02",
    "seed": 42,
    "primary_score": 6.308039821969917,
    "fold_mae": [
      6.492088088665719,
      6.260136069670047,
      6.157554588806195,
      6.322380540737706
    ],
    "runs": [
      "d5bd01d101044ed3b5e6de750be81258",
      "1795b33281564f988d8a4c8bd8cd2e1c",
      "35b0c68d702a4c8a98a7e173f7bdae70",
      "648a564d6cb24fa7abe0014b4b78bd9d"
    ],
    "role": "selected"
  },
  {
    "trial_id": "store_item_seasonal_naive_reference",
    "dataset": "store_item",
    "model": "seasonal_naive",
    "parameters": {},
    "configuration_sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    "seed": 42,
    "primary_score": 9.154964285714286,
    "fold_mae": [
      9.153214285714286,
      8.783928571428573,
      8.577285714285713,
      10.105428571428572
    ],
    "runs": [
      "e129d3b8bb004142b8588851c9a1d39c",
      "8802f7798ebd473f9dee3ed8fdad901e",
      "ca791e5a4867454083b63c6c3fe63f0c",
      "3b8f85d849fb45aa930345470359853e"
    ],
    "role": "comparator"
  },
  {
    "trial_id": "store_item_seasonal_moving_average_reference",
    "dataset": "store_item",
    "model": "seasonal_moving_average",
    "parameters": {},
    "configuration_sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    "seed": 42,
    "primary_score": 8.086651785714285,
    "fold_mae": [
      9.131964285714286,
      7.773892857142857,
      7.099678571428571,
      8.341071428571427
    ],
    "runs": [
      "5b1e2c70809b4be5b3f6b7cf4eddae8e",
      "e6b4b9bcb8d54813930b24dea5b6a008",
      "418d1da195fe417c9d82b38c9fa21bb6",
      "6bd2be5e964b4edd8f2c677c7cf9b6b2"
    ],
    "role": "comparator"
  },
  {
    "trial_id": "store_item_holt_winters_additive_01",
    "dataset": "store_item",
    "model": "holt_winters_additive",
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
    "configuration_sha256": "b037ae42bc706d5b5ab8c2624ad26c6f16549b741fb433867c521ac1171af4e3",
    "seed": 42,
    "primary_score": 7.043324262632043,
    "fold_mae": [
      6.872005886334718,
      6.609829902192527,
      6.770359515583637,
      7.921101746417289
    ],
    "runs": [
      "b44ade3cfd814d639d130d1cf7c8d0dc",
      "0f0198a83e5842db9cc2d973ec1596aa",
      "f73022a9f85244d78e2f8428f67ff98b",
      "9c143ff7aa84480eb2a77ba1918fac30"
    ],
    "role": "comparator"
  }
]
```

## m5

Selected: `m5_random_forest_02`. Final origin 2016-04-24; 28 targets 2016-04-25–2016-05-22; 30,490 series.

- selected: `m5_random_forest_02` / random_forest; validation MAE 1.020066985; configuration `fb5592e84ff97c25563d9fdde4ae04390c3e0c9f131b8a6c625aa61ff6937477`.
- comparator: `m5_seasonal_naive_reference` / seasonal_naive; validation MAE 1.211999543; configuration `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a`.
- comparator: `m5_moving_average_28_reference` / moving_average_28; validation MAE 1.033779225; configuration `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a`.
- comparator: `m5_tsb_01` / tsb; validation MAE 1.034131102; configuration `894e79e5dcbd2c763488e6396b74724b7cfd5e3afa045137b1a4d57b4cfbf9db`.

Exact immutable hyperparameters:

```json
[
  {
    "trial_id": "m5_random_forest_02",
    "dataset": "m5",
    "model": "random_forest",
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
    "configuration_sha256": "fb5592e84ff97c25563d9fdde4ae04390c3e0c9f131b8a6c625aa61ff6937477",
    "seed": 42,
    "primary_score": 1.0200669850841517,
    "fold_mae": [
      0.9986903229382016,
      1.0195172344666987,
      1.0345736584988314,
      1.0274867244328751
    ],
    "runs": [
      "444945b171c94886ad2192bade5253b9",
      "57208a591210486fa09911f9f9571c7c",
      "2e769d25c5f64aa297971b111d10a75f",
      "a504b751121f4392b0aa317e28ef7121"
    ],
    "role": "selected"
  },
  {
    "trial_id": "m5_seasonal_naive_reference",
    "dataset": "m5",
    "model": "seasonal_naive",
    "parameters": {},
    "configuration_sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    "seed": 42,
    "primary_score": 1.2119995431757487,
    "fold_mae": [
      1.2055755985569039,
      1.1994494682097177,
      1.210618235487045,
      1.2323548704493277
    ],
    "runs": [
      "637d2c14c06b4ab897bb93564035eb54",
      "9c215d24c8584293b9ce007cc9f675e4",
      "add26a2b00834c48ba5e633dc21421b9",
      "e029277664f94d28836eac5d9be581f8"
    ],
    "role": "comparator"
  },
  {
    "trial_id": "m5_moving_average_28_reference",
    "dataset": "m5",
    "model": "moving_average_28",
    "parameters": {},
    "configuration_sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    "seed": 42,
    "primary_score": 1.0337792250386544,
    "fold_mae": [
      1.014950033801648,
      1.0332807343993682,
      1.0457541281517526,
      1.0411320038018488
    ],
    "runs": [
      "1712dcaefa284d9da396209f2b7abab2",
      "90bfa20842504c3c9a86c09332333883",
      "674ff4bb75db41df99d62d0d273f50ab",
      "c1a37a350afb496fbf9be7e71aae53db"
    ],
    "role": "comparator"
  },
  {
    "trial_id": "m5_tsb_01",
    "dataset": "m5",
    "model": "tsb",
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
    "configuration_sha256": "894e79e5dcbd2c763488e6396b74724b7cfd5e3afa045137b1a4d57b4cfbf9db",
    "seed": 42,
    "primary_score": 1.0341311023582396,
    "fold_mae": [
      1.0101687994289086,
      1.0368755531147937,
      1.0431494049193253,
      1.0463306519699302
    ],
    "runs": [
      "c892512d60fb4e9c99bc67bc8e9c6569",
      "a557e5d3822f4dae847e115e7635cdc3",
      "205615466fa5472db76f8aa88696c56e",
      "27b1cc02df034782b4b75376b408cc38"
    ],
    "role": "comparator"
  }
]
```

All model choices, comparators, sampling, features, metrics, eligibility, fallbacks and source/code fingerprints are fixed in the machine-readable manifest. Both datasets' model artifacts, scales and predictions must be sealed before any target read. No refit, regeneration or replacement after access. Phase 5 and Claude audit remain unstarted.
