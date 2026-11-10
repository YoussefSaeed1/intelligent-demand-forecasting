# Phase 5 independent audit handoff

> **Status update after the independent audit.** The broader independent audit requested below was
> completed on 2026-11-10 (verdict CONDITIONAL; 0 Critical, 0 High, 6 Medium, 4 Low, 2 Informational).
> See [the audit](CLAUDE_INDEPENDENT_AUDIT_PHASES_0_5.md) and
> [PHASE5_AUDIT_RESPONSE.md](PHASE5_AUDIT_RESPONSE.md). The checkpoint statements in this document
> are corrected below. Everything else is the original handoff.

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


## Verified backup and authorised Git checkpoint

This section records the checkpoint after the original Phase 5 completion report.
It supersedes earlier historical statements that no Phase 5 backup or commit exists.
Phase 5A?5D are complete under internal gates. The broader independent Claude review has since been
completed (CONDITIONAL). Phase 6 and Phase 7 have not started.

Backup: `C:/Project_Backups/Demand_Forecasting_Phase5_Evidence_verified_20261108`. Verified 2026-11-08T19:02:22.778761+00:00; **2,593 evidence files**, **1,611,791,130 bytes**,
including the original 2,252-file Phase 5 inventory and documented replay dependencies.
Two additional backup-root files are declared verification sidecars, not unexpected evidence.
All file sets, sizes and SHA-256 values reconciled, with zero missing/mismatched files.
[Verification manifest](../reports/preservation/PHASE5_LOCAL_BACKUP_VERIFICATION.json),
[preservation report](PHASE5_BACKUP_PRESERVATION.md),
[supplement](../reports/preservation/PHASE5_BACKUP_SUPPLEMENT.json).

This is a **LOCAL BACKUP ON THE SAME DEVICE**, not an independent off-device backup.
It does not protect against complete SSD failure, theft or loss of the laptop.
The original Phase 4 backup is unchanged. Git stores implementation, tests, configuration,
documents and small manifests. Parquet/NumPy inputs/results, detailed audit tables,
figures, logs and backup contents remain local-only; they have verified backup copies.
Credentials, virtual environments, unused feature matrices/prices and unrelated data
were excluded. Required Phase 5 calibration/sparse-label cache arrays were retained.

The backup preserves the original handoff at its original relative path. Its exact source
bytes and the earlier Git attributes are archived in
`reports/preservation/phase5_precheckpoint_original/`. An explicit
[checkpoint document overlay](../reports/preservation/PHASE5_CHECKPOINT_DOCUMENT_OVERLAY.json)
records the current metadata versions; no experiment result or frozen policy code changed.
Git attributes preserve frozen bytes across checkout despite local autocrlf settings.

Safe backup verification from the current project (no experiment regeneration):
```powershell
.venv\Scripts\python.exe -m intelligent_demand.preservation.phase5_post_audit `
    --destination 'C:/Project_Backups/Demand_Forecasting_Phase5_Evidence_verified_20261108' `
    --source-overlay reports/preservation/PHASE5_AUDIT_REMEDIATION_OVERLAY.json
.venv\Scripts\python.exe -m intelligent_demand.preservation.verify `
    --workspace-root . --overlay reports/inventory/post_audit_documentation_overlay.json
# The original phase5 verify command and documentation_overlay.json describe the pre-audit
# documents; they fail by design now that the reviewed documents were corrected.
```
Use the inventory results document for permitted simulation/report commands. Restoration
requires the recorded environment and original logical/absolute path mapping; clean-room
execution from a relocated backup was not tested. Do not retrain, retune, regenerate forecasts
or access final holdout targets to verify this copy. Original scientific limitations remain:
sales proxy/censoring, hypothetical costs, finite fixed-origin episodes, reused validation,
retrospective sparse grouping and fractional ceiling sensitivity. The earlier Windows
fixture access-denied incident was resolved by fresh unchanged test retries; automated
browser rendering remains unverified.

At the time this handoff was written the Phase 5 files were staged but not committed. The
checkpoint is now one local commit with the message
`feat: complete phase 5 and document independent audit findings`, replacing the earlier planned
message. Find it with `git log -1`. Its hash is not written into committed files to avoid a
self-referential edit; a git-ignored local receipt
`artifacts/experiments/phase5_checkpoint_postcommit_receipt.json` records it. No amend, push or
history rewrite was performed or is authorised.
