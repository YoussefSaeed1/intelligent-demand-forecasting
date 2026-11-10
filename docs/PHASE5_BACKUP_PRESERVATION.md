# Phase 5 backup preservation

Status: VERIFIED. Created 2026-11-08T19:00:55.787339+00:00; copying completed 2026-11-08T19:02:22.778761+00:00.

Destination: `C:/Project_Backups/Demand_Forecasting_Phase5_Evidence_verified_20261108` (outside the project). This is a
**LOCAL BACKUP ON THE SAME DEVICE**, not an independent off-device backup.
It does not protect against complete SSD failure, device theft or laptop loss.
The pre-existing Phase 4 backup was not modified.

## Scope and verification

- Primary: `reports/inventory/PHASE5_EVIDENCE_INVENTORY.json`, SHA-256
  `e9c80f550e93fcec336bc652ef5e382bf42d4342e2c1fac640806ee0ee0a21db`;
  2,252 original evidence files, 487,705,384 bytes.
- [Supplement](../reports/preservation/PHASE5_BACKUP_SUPPLEMENT.json): 340 additional
  necessary dependencies, plus the supplement itself. Includes saved input-run evidence,
  origin-bound calibration values, sparse-label/position arrays, canonical input byte copies,
  source code, environment/configuration, original logs, inventory and final gate.
- [Combined manifest](../reports/preservation/PHASE5_BACKUP_SOURCE_MANIFEST.json), SHA-256
  `73aa33b40e02e60ff4b6db7cf0fa05d1f1afd6526794fc020f9da537b7739737`: **2,593 verified files, 1,611,791,130 bytes**.
- Physical destination: 2595 files / 1613113471 bytes,
  including exactly two declared root sidecars: EVIDENCE_INVENTORY.json and
  BACKUP_VERIFICATION.json. No unexpected scientific files.
- All expected/source/destination paths, file sizes and every SHA-256 were checked.
  Missing:0; mismatched:0; unexpected:0. Source files were rehashed after copying.
- [Machine verification](../reports/preservation/PHASE5_LOCAL_BACKUP_VERIFICATION.json).
  Original copying preserved every file's relative path and contents; nothing moved/deleted.
- Independently counted persisted Parquet metadata:544 completed cases,8,429,280 series
  episodes and13,969,536 retained events. Frozen representatives account for3,264 declared
  scalar replays; prior audited receipts/logs are preserved, not recomputed.
- [Phase 4 preflight](../reports/preservation/PHASE5_PHASE4_PREFLIGHT.json): all4,592
  historical entries,89 snapshots,332 registry runs and nine input fingerprints passed.
  Frozen selection and the original12-event ledger are unchanged.

No required Phase 5 evidence is missing or unavailable. Raw CSVs, virtual environments,
credentials, temporary test trees, unused ML feature matrices and unused cached prices
were excluded; they are not consumed by the frozen Phase 5 input adapter. Complete
unrelated Phase 4 trials/final holdout outputs remain in their separate protected inventory
and original verified Phase 4 backup; they were not duplicated indiscriminately here.
Canonical Parquet files were copied and hashed as bytes, never analysed as final targets.

## Checkpoint metadata and reproducibility

Only after the complete backup gate passed, the handoff was appended with checkpoint
metadata and Git attributes were extended to preserve frozen bytes across checkout.
Exact pre-update versions remain archived under
`reports/preservation/phase5_precheckpoint_original/`. The
[explicit document overlay](../reports/preservation/PHASE5_CHECKPOINT_DOCUMENT_OVERLAY.json)
maps the two current metadata files to immutable original bytes for backup verification.
This versioning is not an exception for experimental outputs: every scientific result,
policy/configuration, prediction and ledger hash remains strict.

The new preservation report, current metadata overlay and copy-verification receipt
are checkpoint records created after the snapshot; they are stored in Git. The backup
retains the original handoff rather than replacing it with the updated version.
The final commit hash belongs in the final response and a local ignored post-commit receipt,
not in its own committed handoff. No additional commit/amend is needed.

Verification commands are in [the handoff](PHASE5_CLAUDE_AUDIT_HANDOFF.md). Permitted
inventory regeneration needs the copied local dependencies, appropriate environment and
original path mapping, without new forecasts or final-holdout evaluation. Relocated
clean-room execution has not been demonstrated. Existing scientific limitations and the
prior platform/browser warnings remain documented. Phase 6/7 and Claude invocation
have not started. No external upload or remote Git operation occurred.
