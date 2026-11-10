# Inventory engine

`inventory/engine.py` separates realised demand (owned by the simulator) from
`ForecastWindow` and `order_quantity`, which accept no future actuals. Forecast
windows enforce issue date, daily absolute dates, completeness, finite nonnegative
values and remaining protection coverage. Arrays are copied/read-only at that
boundary. This is an application contract, not a sandbox against malicious Python.

The vectorised engine processes bounded series batches, with an explicit future
receipt schedule, running pipeline balance, daily and episode conservation checks.
Receipts precede demand, orders follow demand, receipt offset is L+1. Shared
decision cutoff prevents using missing forecast dates. Invalid data or invariants
fail the case; no silent imputation, dropped series or alternative forecast is used.

Synthetic H3/L0 example: mean2, starting stock0, demand2/day and forecast2/day.
Orders are [2,2,0], receipts [0,2,2], fulfilled4, unmet2, fill2/3. With base h1/p10/k1,
cost22 NCU. This manually calculable fixture is not an empirical inventory result.
Tests also cover zero/seasonal/intermittent/spike demand, initial known receipts,
terminal pipeline, several outstanding orders, oversized/zero stock, zero costs,
unsupported backorders, date gaps and future-demand poisoning of earlier decisions.

Saved case summaries include all stock/cost denominators and undefined values.
The execution layer uses exclusive case locks and closed Parquet files renamed before the atomic
completion manifest is published. Failed/unpublished attempts cannot enter comparisons. Source hashes,
scenario contract and implementation hashes must match before a completed case
can be resumed. Full base events and sampled sensitivity events have explicit
coverage; per-series evaluation remains full population for every scenario.
