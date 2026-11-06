# Planned Power BI deliverables

No PBIX, dashboard or calculated result exists yet. Build only after validated outputs.

| Page | Planned content |
|---|---|
| Executive Overview | Source/time/series coverage, forecast summary and qualified scenario KPIs |
| Forecasting Performance | Actual versus prediction, MAE/RMSE/WAPE/bias, model and horizon comparisons |
| Inventory Planning | Simulated stock, orders, shortages, fill rate and scenario assumptions |
| Business Impact | Scenario costs and policy tradeoffs with sensitivity ranges |

Export UTF-8 CSV for broad compatibility to reports/exports; optionally Parquet where the
chosen Power BI connector supports it. Document connector and refresh steps at build time.
Planned star model: dimensions for date, dataset-series, model/run, policy/scenario;
facts for forecasts (origin/target/horizon/series/model/run), evaluations (declared
aggregation grain), simulated inventory (scenario/policy/date/series). Use explicit
relationships and role-playing origin/target dates; avoid many-to-many joins and summing
overlapping-origin forecasts. Ensure keys include dataset namespace.

Export schema, units, coverage, metric definitions and generation configuration alongside
files. Recompute WAPE from numerator/denominator totals rather than averaging percentages.
Show observed versus assumed inputs and simulated labels on inventory/business pages.
Restrict redistribution of data and PBIX contents according to verified source terms.
