# Phase 5 independent audit handoff

Scope: broader scientific and technical audit before Phase 6 and Phase 7. No Claude call was made by this implementation.

Read INVENTORY_SIMULATION_PROTOCOL.md, INVENTORY_POLICY_MATHEMATICS.md, PHASE5_ASSUMPTIONS.md and INVENTORY_ENGINE.md for timing, policy mathematics, training-only calibration and fixed-origin availability. Review inventory/{design,plan,inputs,engine,runner,audit,report}.py and the three test_inventory_*.py files. Simulator policy decisions receive current position, historical means and frozen forecasts; future actuals and reporting labels are outside that interface. End-day t order arrives t+L+1; protection L+R; daily conservation is enforced.

Frozen plan: `63efc59ed0dc2b35b2ad3067fb790c0b42d0c1f279e3f8142519b78c07cce76e`; execution: `b55ba4a0c9c8fafb2ee3997f38d2f31efea99f4157033e70288814a2006c87c3`. Stored under artifacts/inventory/phase5. Each of 544 cases has atomic completion status and hashed per-series/event outputs; non-completed/tampered cases are rejected. Source model run IDs/configurations and fallback observations remain explicit. No final holdout was used.

[Results](PHASE5_INVENTORY_RESULTS.md), [sensitivities](PHASE5_SENSITIVITY_ANALYSIS.md), [limitations](PHASE5_LIMITATIONS.md), [completion gate](PHASE5_COMPLETION_CHECKLIST.md), [offline report](../reports/inventory/PHASE5_INVENTORY_REPORT.html), [audit machine results](../reports/inventory/phase5_summary.json). Reproduction commands are in the results document. Large artefacts remain local and ignored; Git alone is insufficient. See the Phase 5 local evidence inventory for paths/bytes/hashes.

Scrutinise: common protection cutoff versus useful operating horizon; fairness and dominance of initial stock/terminal effects; hypothetical buffer versus true service targets; stockholding/service trade-offs and ROP interpretation; validation reuse; sparse subgroup chronology; scalar-reference independence and shared adapter risk; phase-origin source guards and original ledger preservation; resume/atomic status failures; report aggregation and plots. Explicitly distinguish internally checked gates from independent scientific approval. Do not rerun final forecasting or decode final targets during this audit.


Final verification: 439 tests passed (100.93s); Ruff, pip check and CLI smoke passed.
[Protected evidence receipt](../reports/inventory/protected_evidence_verification.json),
[metric reconciliation](../reports/inventory/metric_validation.json),
[report validation](../reports/inventory/report_validation.json), and
[local evidence inventory](../reports/inventory/PHASE5_EVIDENCE_INVENTORY.json).
The inventory is not a backup. Phase5 results/figures are local and ignored; their
validation-only regeneration needs original ignored dependencies. No Phase5 backup
or independent off-device protection is claimed. The existing Phase4 same-device
backup was not modified.

Base ML-minus-MA28 cost: Store Item -376.144 NCU/series/episode (-5.864%);
M5 +1.897376 (+0.855%). Fixed ROP has lower base cost on both with lower fill.
Store Item ML mean cost is lower than MA28 in 17/17 frozen scenarios; M5 in 3/17.
These scenario counts are not probabilities. All 6,878 retrospective sparse series
are included; primary origin-specific zero-label counts are 7,225/7,179/7,166/6,976.
No forecast fallback observations were present in these saved sources.
