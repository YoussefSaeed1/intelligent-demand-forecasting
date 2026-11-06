# Phase 2 visualisation index

29 figures / 58 files: 29 PNG and 29 SVG. All existing image files open and
match verification copies rendered from the saved EDA tables. No full analysis
or canonical transformation was rerun. Targeted figures were enhanced from saved tables.

[Open the offline visual report](EDA_VISUAL_REVIEW.html).
[Machine-readable checks](visualisation_audit.json).

Paths below are relative to this index. The images depend on the neighbouring
`reports/figures/phase2/` directory; keep that directory when moving the report.

## Store Item

| Figure | Purpose | Dataset | PNG relative path | SVG relative path |
|---|---|---|---|---|
| Daily sales distribution | Exact daily-unit frequencies and the cumulative distribution of positive sales. | Store Item | [PNG](../figures/phase2/store_item_distribution.png) | [SVG](../figures/phase2/store_item_distribution.svg) |
| Daily and monthly sales | Daily aggregate units, trailing 28-day mean and complete calendar-month totals. | Store Item | [PNG](../figures/phase2/store_item_trends.png) | [SVG](../figures/phase2/store_item_trends.svg) |
| Weekly and annual calendar structure | Within-week ratios with pointwise bootstrap intervals and normalised monthly profiles. | Store Item | [PNG](../figures/phase2/store_item_calendar_patterns.png) | [SVG](../figures/phase2/store_item_calendar_patterns.svg) |
| Demand-pattern classifications | Store Item positive-size variability and smooth-population facts; M5 ADI/CV² scatter. | Store Item | [PNG](../figures/phase2/store_item_intermittency.png) | [SVG](../figures/phase2/store_item_intermittency.svg) |
| Zero-sales frequency and variability | Series-level zero percentages and the distribution of defined positive all-sales CVs. | Store Item | [PNG](../figures/phase2/store_item_zeros_variability.png) | [SVG](../figures/phase2/store_item_zeros_variability.svg) |
| Product sales concentration | Cumulative sales shares ordered by product volume and the ten highest-volume products. | Store Item | [PNG](../figures/phase2/store_item_concentration.png) | [SVG](../figures/phase2/store_item_concentration.svg) |
| Store-level comparisons | Units per store-product day and zero-sales percentages, with equal historical exposure. | Store Item | [PNG](../figures/phase2/store_item_stores.png) | [SVG](../figures/phase2/store_item_stores.svg) |
| Trend, annual structure and autocorrelation | Log aggregate sales/trend, approximate annual component and first-differenced log ACF. | Store Item | [PNG](../figures/phase2/store_item_diagnostics.png) | [SVG](../figures/phase2/store_item_diagnostics.svg) |
| Rolling volatility and zero-sales breadth | Aggregate 28-day coefficient of variation and the daily percentage of zero-selling series. | Store Item | [PNG](../figures/phase2/store_item_volatility.png) | [SVG](../figures/phase2/store_item_volatility.svg) |
| Representative demand histories | Deterministic examples with explicit windows; zero/single-positive M5 cases show full training histories. | Store Item | [PNG](../figures/phase2/store_item_representatives.png) | [SVG](../figures/phase2/store_item_representatives.svg) |
| Unusual sales and the empirical tail | Full-population tail probabilities and clearly labelled retained extreme examples. | Store Item | [PNG](../figures/phase2/store_item_extremes.png) | [SVG](../figures/phase2/store_item_extremes.svg) |

2013-01-01–2017-08-13; all 500 series.

## M5

| Figure | Purpose | Dataset | PNG relative path | SVG relative path |
|---|---|---|---|---|
| Daily sales distribution | Exact daily-unit frequencies and the cumulative distribution of positive sales. | M5 | [PNG](../figures/phase2/m5_distribution.png) | [SVG](../figures/phase2/m5_distribution.svg) |
| Daily and monthly sales | Daily aggregate units, trailing 28-day mean and complete calendar-month totals. | M5 | [PNG](../figures/phase2/m5_trends.png) | [SVG](../figures/phase2/m5_trends.svg) |
| Weekly and annual calendar structure | Within-week ratios with pointwise bootstrap intervals and normalised monthly profiles. | M5 | [PNG](../figures/phase2/m5_calendar_patterns.png) | [SVG](../figures/phase2/m5_calendar_patterns.svg) |
| Demand-pattern classifications | Store Item positive-size variability and smooth-population facts; M5 ADI/CV² scatter. | M5 | [PNG](../figures/phase2/m5_intermittency.png) | [SVG](../figures/phase2/m5_intermittency.svg) |
| Zero-sales frequency and variability | Series-level zero percentages and the distribution of defined positive all-sales CVs. | M5 | [PNG](../figures/phase2/m5_zeros_variability.png) | [SVG](../figures/phase2/m5_zeros_variability.svg) |
| Product sales concentration | Cumulative sales shares ordered by product volume and the ten highest-volume products. | M5 | [PNG](../figures/phase2/m5_concentration.png) | [SVG](../figures/phase2/m5_concentration.svg) |
| Store-level comparisons | Units per store-product day and zero-sales percentages, with equal historical exposure. | M5 | [PNG](../figures/phase2/m5_stores.png) | [SVG](../figures/phase2/m5_stores.svg) |
| Trend, annual structure and autocorrelation | Log aggregate sales/trend, approximate annual component and first-differenced log ACF. | M5 | [PNG](../figures/phase2/m5_diagnostics.png) | [SVG](../figures/phase2/m5_diagnostics.svg) |
| Rolling volatility and zero-sales breadth | Aggregate 28-day coefficient of variation and the daily percentage of zero-selling series. | M5 | [PNG](../figures/phase2/m5_volatility.png) | [SVG](../figures/phase2/m5_volatility.svg) |
| Representative demand histories | Deterministic examples with explicit windows; zero/single-positive M5 cases show full training histories. | M5 | [PNG](../figures/phase2/m5_representatives.png) | [SVG](../figures/phase2/m5_representatives.svg) |
| Unusual sales and the empirical tail | Full-population tail probabilities and clearly labelled retained extreme examples. | M5 | [PNG](../figures/phase2/m5_extremes.png) | [SVG](../figures/phase2/m5_extremes.svg) |
| All M5 demand classes | Log-position counts with exact counts and percentages, including minority histories. | M5 | [PNG](../figures/phase2/m5_classification.png) | [SVG](../figures/phase2/m5_classification.svg) |
| Historical price coverage and sales activity | Full-history price gaps by date/store/year, plus the training-only activity partition. | M5 | [PNG](../figures/phase2/m5_price_missingness.png) | [SVG](../figures/phase2/m5_price_missingness.svg) |
| Price coverage by product and series | Product missing-price rates and their descriptive relationship to series zero-sales rates. | M5 | [PNG](../figures/phase2/m5_price_products.png) | [SVG](../figures/phase2/m5_price_products.svg) |
| Calendar events and product categories | Ten lowest-mean named events and category-level trailing means adjusted by series count. | M5 | [PNG](../figures/phase2/m5_events_groups.png) | [SVG](../figures/phase2/m5_events_groups.svg) |
| SNAP versus non-SNAP calendar days | Within-state units per store-day, with the actual flagged/non-flagged exposures. | M5 | [PNG](../figures/phase2/m5_snap.png) | [SVG](../figures/phase2/m5_snap.svg) |
| Department-level demand | Daily rates per department series and monthly mean daily rates, not raw unequal totals. | M5 | [PNG](../figures/phase2/m5_departments.png) | [SVG](../figures/phase2/m5_departments.svg) |

2011-01-29–2016-01-03; all 30,490 series.

## Both datasets

| Figure | Purpose | Dataset | PNG relative path | SVG relative path |
|---|---|---|---|---|
| Different sales structures across datasets | Compare zero-sales frequency, median series CV and product concentration. | Both datasets | [PNG](../figures/phase2/cross_dataset_comparison.png) | [SVG](../figures/phase2/cross_dataset_comparison.svg) |

Store Item: 2013-01-01–2017-08-13; M5: 2011-01-29–2016-01-03.

## Findings from the visual review

No image files or expected PNG/SVG pairs are missing. Data bindings passed
exact PNG pixel comparison and normalised SVG artist-content comparison.

Remaining interpretation limits are documented in the HTML; presentation defects were addressed:

- ADI/CV² thresholds and aggregate seasonality are descriptive, not guarantees of individual-series forecastability.
- M5's 45 zero-CV² histories need a labelled positive display floor on a log scatter; 21 undefined histories appear in the separate classification figure.
- SNAP and event comparisons are descriptive: date composition, holidays, assortment and other confounders are uncontrolled.
- Department rates use a fixed published series universe, not independently observed assortment or stock availability; boundary heatmap months may be partial.
- Retained extreme examples are not an exhaustive tie list or proof of invalid data; only the histogram tail is a full-population distribution.
- Representative panels have independent y-scales and explicitly different windows. They are illustrations, not sampling-based population estimates.
- Historical price coverage extends through 2016-05-22 without inspecting reserved sales targets. The 465 reserved-period price gaps have no activity interpretation.
- Observed sales may be constrained demand. No measured inventory savings, causal effects, forecasting winner or direct cross-source transfer is established.

## Chart inputs

Figures use saved Parquet tables, not newly sampled or fabricated observations.

- **store_item_distribution**: [distribution](tables/store_item/distribution.parquet), [largest_observations](tables/store_item/largest_observations.parquet).
- **store_item_trends**: [daily](tables/store_item/daily.parquet), [monthly](tables/store_item/monthly.parquet).
- **store_item_calendar_patterns**: [weekdays](tables/store_item/weekdays.parquet), [month_year](tables/store_item/month_year.parquet).
- **store_item_intermittency**: [series](tables/store_item/series.parquet), [patterns](tables/store_item/patterns.parquet).
- **store_item_zeros_variability**: [series](tables/store_item/series.parquet).
- **store_item_concentration**: [products](tables/store_item/products.parquet).
- **store_item_stores**: [stores](tables/store_item/stores.parquet).
- **store_item_diagnostics**: [components](tables/store_item/components.parquet), [acf](tables/store_item/acf.parquet).
- **store_item_volatility**: [daily](tables/store_item/daily.parquet).
- **store_item_representatives**: [representative_series](tables/store_item/representative_series.parquet), [series](tables/store_item/series.parquet).
- **store_item_extremes**: [distribution](tables/store_item/distribution.parquet), [largest_observations](tables/store_item/largest_observations.parquet), [series](tables/store_item/series.parquet).
- **m5_distribution**: [distribution](tables/m5/distribution.parquet), [largest_observations](tables/m5/largest_observations.parquet).
- **m5_trends**: [daily](tables/m5/daily.parquet), [monthly](tables/m5/monthly.parquet).
- **m5_calendar_patterns**: [weekdays](tables/m5/weekdays.parquet), [month_year](tables/m5/month_year.parquet).
- **m5_intermittency**: [series](tables/m5/series.parquet), [patterns](tables/m5/patterns.parquet).
- **m5_zeros_variability**: [series](tables/m5/series.parquet).
- **m5_concentration**: [products](tables/m5/products.parquet).
- **m5_stores**: [stores](tables/m5/stores.parquet).
- **m5_diagnostics**: [components](tables/m5/components.parquet), [acf](tables/m5/acf.parquet).
- **m5_volatility**: [daily](tables/m5/daily.parquet).
- **m5_representatives**: [representative_series](tables/m5/representative_series.parquet), [series](tables/m5/series.parquet).
- **m5_extremes**: [distribution](tables/m5/distribution.parquet), [largest_observations](tables/m5/largest_observations.parquet), [series](tables/m5/series.parquet).
- **m5_classification**: [patterns](tables/m5/patterns.parquet), [series](tables/m5/series.parquet).
- **m5_price_missingness**: [price_by_date_full_quality](tables/m5/price_by_date_full_quality.parquet), [price_by_store_full_quality](tables/m5/price_by_store_full_quality.parquet), [price_by_year_full_quality](tables/m5/price_by_year_full_quality.parquet), [price_by_series_eda](tables/m5/price_by_series_eda.parquet).
- **m5_price_products**: [price_by_product_full_quality](tables/m5/price_by_product_full_quality.parquet), [price_by_series_eda](tables/m5/price_by_series_eda.parquet), [series](tables/m5/series.parquet).
- **m5_events_groups**: [calendar_events](tables/m5/calendar_events.parquet), [cat_id_daily](tables/m5/cat_id_daily.parquet), [series](tables/m5/series.parquet).
- **m5_snap**: [snap_associations](tables/m5/snap_associations.parquet).
- **m5_departments**: [dept_id_daily](tables/m5/dept_id_daily.parquet), [series](tables/m5/series.parquet).
- **cross_dataset_comparison**: [store_item_results](store_item_results.json), [m5_results](m5_results.json).
