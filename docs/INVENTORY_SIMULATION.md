# Future inventory simulation design

No simulator is implemented in Phase 0. Observed inputs will be verified sales histories
and out-of-sample forecasts. Operational assumptions will be explicitly configured:
lead-time distribution, review interval, initial stock and pipeline, service target,
holding and shortage costs, ordering constraints, lost-sales versus backorder treatment.
Do not assume these are present in the source data.

Define inventory position as on-hand + on-order - backorders. Explore reorder-point
or periodic-review policies using lead-time forecast demand plus safety stock calibrated
only from prior training/validation errors. Define the precise daily event order before
implementation: receive due orders, serve realised sales proxy, record shortages/costs,
review stock and place orders with delivery timestamps. Specify warmup and terminal
inventory treatment; use identical starting conditions and scenario paths for policies.

Compare baseline and forecast-driven policies on stockout frequency, unit fill rate
(units served / requested units), average on-hand inventory, holding cost, shortage cost
and total defined cost. Zero requested units makes fill rate undefined. Distinguish
cycle service level from unit fill rate. Demand during lead time and safety stock must
respect forecast-origin information; never calibrate on future realised errors.

Sweep lead times, cost ratios, service targets and initial stock assumptions. Report
scenario_id, assumptions, units, forecast run_id, policy and uncertainty. Historical sales
are a demand proxy and may be censored. Outputs are hypothetical scenario outcomes,
not actual inventory performance or realised savings.
