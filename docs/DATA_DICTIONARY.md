# Verified Phase 1 canonical data dictionary

The following project-defined fields and source mappings were verified on the local
Store Item and M5 files on 2026-11-06. Canonical grain is one observed daily sales value
per dataset/store/product/date. Future source versions require renewed validation;
forecast and inventory output contracts below remain proposals.

| Field | Verified Parquet type | Meaning and constraint |
|---|---|---|
| dataset_id | string | Source namespace; required |
| series_id | string | Stable source-specific series key; required |
| date | date32[day] | Source daily calendar date, without time-of-day/timezone inference |
| sales_units | float64 | Observed finite, nonnegative integral unit sales in both current datasets |
| store_id | string | Nonmissing source-specific store identifier |
| item_id | string | Nonmissing source-specific product identifier |
| category_id | nullable string | Optional source hierarchy identifier |
| unit_price | nullable float64 | Observed historical price where supplied; not assumed available ahead |
| is_observed | boolean | Separates observed values from explicit missing/reindexed rows |

Unique key: (dataset_id, series_id, date). Preserve raw identifiers as strings; namespace
keys to avoid source collisions. Missing records are not zero sales. No reindexed,
imputed or unlabelled rows were emitted in Phase 1; is_observed is true for all current
canonical rows. Any future reindexing contract must distinguish absent observations.
Do not merge series across sources using item/store labels. Preserve source hierarchy
and calendar metadata in separate validated lookup tables where needed.

Target is sales, not unconstrained demand. Availability, lead times, costs and stock
balances must not be invented as observed fields. Future covariates need an availability
timestamp or explicit known-in-advance policy; observed future prices cannot be assumed known.

Planned prediction contract: dataset_id, series_id, forecast_origin, target_date,
horizon_step, model_id, run_id, prediction, actual (nullable). Inventory outputs use a
separate scenario_id with assumptions and simulated status. These contracts also remain
provisional until the reporting phase; no output records exist yet.

## Verified source mappings and coverage

Canonical Parquet uses string identifiers, date32, float64 sales_units/unit_price and
boolean is_observed. Store Item train.csv contains date/store/item/sales; test.csv contains
id/date/store/item and no sales labels. Independent typed CSV parsing validated date32
dates and int64 identifiers/sales; the CSV files themselves remain text files.
M5 histories contain id/item_id/dept_id/cat_id/store_id/state_id and d_N sales columns,
with verified calendar and weekly price joins.
Source identifiers are strings; series_id length-prefixes store_id before appending
item_id, preventing delimiter collisions. Dataset identity namespaces keys.

Store Item category_id/unit_price are null; M5 category_id comes from cat_id and
unit_price from the validated store/item/week join. All emitted sales are observed;
missing dates are not inserted. Historical prices are not assumed available future
predictors. Both independent persisted-file gates passed and remain bound to current hashes.

| Contract | Store Item | M5 |
|---|---|---|
| Labelled source / target | train.csv.sales | Evaluation history d_1 through d_1941, mapped by calendar.d |
| Historical dates | 2013-01-01–2017-12-31 | 2011-01-29–2016-05-22 |
| Series / days / rows | 500 / 1,826 / 913,000 | 30,490 / 1,941 / 59,181,090 |
| Core-field nulls / duplicate business keys | 0 / 0 | 0 / 0 |
| category_id | All 913,000 null: not supplied | Source cat_id, nonmissing |
| unit_price | All 913,000 null: not supplied | Weekly price join; 12,299,413 null observations retained |
| Competition test | 45,000 unlabelled rows, 2018-01-01–2018-03-31; excluded | No unlabelled future sales added to canonical history |

Store Item has every date for every one of its 10×50 store/product combinations, with
zero interior or boundary gaps. Its single observed zero (store 6, item 4, 2014-01-15)
is retained unchanged. M5 also has complete observed series/day coverage; missing prices
are covariate gaps, not missing sales. Neither zero sales nor is_observed proves stock
availability or uncensored demand. Source namespaces have no validated store/product
identity correspondence across datasets.
