# Phase 5 hypothetical assumptions

No observed stock, orders, lead times, costs, service targets or uncensored demand
are supplied by these datasets. configs/inventory.yaml is the explicit source of
hypothetical assumptions; it is frozen before simulation results. See the protocol
and policy mathematics for exact timing. No claimed probability service target is
attached to days-of-cover buffers. Unlimited deterministic supply, lost sales,
integer orders and common initial stock are assumptions, not measurements.

Base lead7/review1/buffer3/initial7 days; leads1/14; buffers0/7; initial0/14;
holding0.2/2; shortage2/50; fixed order0/5; terminal1; variability0.5/1.5;
review7. Other base values stay fixed, giving17 scenarios. No post-result tuning.
Changing holding/penalty levels changes NCU scales/trade-offs, not actual business
prices. Demand-stress variants may change mean and zeros as well as variability.

The supplied focused gate is retained unchanged. Its conditional permission is
not a comprehensive audit: its numbers were not independently recomputed by that
reviewer, and its ARIMA subset count is not the Phase 5 population. Full 500/30,490
populations and actual saved manifests govern Phase 5. The post-remediation internal
numeric checks remain available but do not become an external certification.

Use origin-specific zero-label masks for primary sparse-group analysis. The 6,878
series identified from final-origin training are a separate retrospective descriptive
stratum: that classification was not known at earlier validation origins and must
not enter policies, calibration or population selection. No final outcomes are read.
