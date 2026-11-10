# Phase 5 limitations

Hypothetical lost-sales simulation; sales are a potentially censored demand proxy. Full populations: Store Item 500 and M5 30,490 series at each of four original validation origins; 28 days per episode. Origins reset stock. Saved forecasts are fixed at issue, not daily refreshed. These validation windows also informed Phase 4 selection; comparisons are exploratory and validation-reused, with no significance claim. Costs are normalised hypothetical units (NCU), not realised savings.

- Observed sales can be supply-censored; latent customer demand and actual lost sales are unknown.
- All inventory states, lead times, costs and buffers are hypothetical; unlimited deterministic supply omits supplier constraints, minimum order sizes, capacity and disruptions.
- Fixed-origin H28 forecasts and a common late-order cutoff support finite episodes only. Initial stock resets and empty pipelines are artificial; terminal stock is not salvaged in base costs. Orders beyond supported protection dates are prohibited even for ROP.
- Equal stock is fair within a scenario, but initialization and endpoint handling can dominate the result. Terminal exposure is only a declared sensitivity, not a valuation model.
- Buffers use trailing 56-day historical means; no calibrated target service probability or out-of-sample residual distribution is claimed. First origin needs no later residuals.
- Four original validation windows were reused after model selection; results are exploratory, not independently held-out policy effectiveness. No final holdout target was read or scored.
- Demand-pattern labels are existing training-prefix EDA. The final-training 6,878 sparse-label mask is retrospective for earlier origins and report-only. Origin-specific zero-label masks are separately provided. All-zero labels do not imply an all-zero historical series.
- Per-series correlations reflect volume, error, bias and policy scale; they are not causal evidence. Four origin ranges and percentiles are descriptive, not confidence intervals.
- Cost trade-offs can favour low-stock policies at lower service. Aggregate cost alone cannot establish operational superiority or deployment suitability.
- Variability stresses alter mean/zeros too; one-at-a-time tests do not estimate a joint distribution of business uncertainty. No backorder model or oracle benchmark is implemented.
- Git excludes large local inputs/results/figures. The preserved Phase 4 backup is local on the same device; Phase 5 outputs have not been independently backed up off-device.
- HTML links and image decoding are checked locally; automated browser rendering is unavailable under the existing local-file policy.

Deployment would require verified stock/pipeline/stockout histories, unconstrained-demand information, supplier distributions, lead-time/capacity constraints, measured economic costs and service objectives, and a fresh prospective operational test with approved forecast refresh cadence. Broader independent Claude review remains required before Phase 6/7; the prior limited conditional review is not comprehensive certification.
