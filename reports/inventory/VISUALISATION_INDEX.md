# Phase 5 figure index

Hypothetical lost-sales simulation; sales are a potentially censored demand proxy. Full populations: Store Item 500 and M5 30,490 series at each of four original validation origins; 28 days per episode. Origins reset stock. Saved forecasts are fixed at issue, not daily refreshed. These validation windows also informed Phase 4 selection; comparisons are exploratory and validation-reused, with no significance claim. Costs are normalised hypothetical units (NCU), not realised savings.

- **Total simulated cost** — both datasets. [PNG](../figures/phase5/01_total_cost.png) / [SVG](../figures/phase5/01_total_cost.svg). Axes start at zero; dataset scales differ. Dots are origins, not confidence intervals.

- **Cost breakdown** — both datasets. [PNG](../figures/phase5/02_cost_breakdown.png) / [SVG](../figures/phase5/02_cost_breakdown.svg). Base terminal charge is zero. Initial acquisition is common and excluded; small ordering costs may be visually thin.

- **Fill rate versus stockholding** — both datasets. [PNG](../figures/phase5/03_fill_inventory.png) / [SVG](../figures/phase5/03_fill_inventory.svg). Full 0–1 fill scale. Fill is not cycle service probability; zero-demand series have undefined individual fill.

- **Stockout days** — both datasets. [PNG](../figures/phase5/04_stockout_days.png) / [SVG](../figures/phase5/04_stockout_days.svg). A day with unmet demand in the hypothetical simulator is not an observed historical stockout.

- **Performance by demand pattern** — both datasets. [PNG](../figures/phase5/05_demand_patterns.png) / [SVG](../figures/phase5/05_demand_patterns.svg). Classes use pre-existing training-prefix EDA, with separate all-zero and insufficient-history groups. Group sizes are in the machine summary.

- **Lead-time sensitivity** — both datasets. [PNG](../figures/phase5/06_lead_sensitivity.png) / [SVG](../figures/phase5/06_lead_sensitivity.svg). Buffer is not a calibrated target service level. Lead changes also change the common last supported ordering date.

- **Hypothetical buffer sensitivity** — both datasets. [PNG](../figures/phase5/07_buffer_sensitivity.png) / [SVG](../figures/phase5/07_buffer_sensitivity.svg). Buffer is not a calibrated target service level. Lead changes also change the common last supported ordering date.

- **Accuracy versus inventory outcome** — both datasets. [PNG](../figures/phase5/08_accuracy_inventory.png) / [SVG](../figures/phase5/08_accuracy_inventory.svg). Association is descriptive, affected by origin volume, bias and scale. No causal or significance inference from 12 points per dataset.

- **Inventory trajectories** — both datasets. [PNG](../figures/phase5/09_trajectories.png) / [SVG](../figures/phase5/09_trajectories.svg). Closing stock and demand have different meanings despite shared unit scale. Complete base events exist for every series/origin; other origins remain inspectable in Parquet.

- **Policy robustness** — both datasets. [PNG](../figures/phase5/10_robustness.png) / [SVG](../figures/phase5/10_robustness.svg). Colour ranges are symmetric about zero separately by dataset. Scenarios are one-at-a-time stresses, not a joint uncertainty distribution or new tuning search.
