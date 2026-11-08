# Post-audit remediation and evidence preservation

Date: 2026-11-08. Scientific baseline:
`54a689b7cb07970556bbf2fc164adf934307eab8`.
**Verdict: READY WITH LIMITATIONS for the independent Claude audit.** Claude has
not been invoked. Phase 5 has not begun and is not authorised by these engineering
checks. No critical/high scientific-impact finding was discovered during remediation.

## Executive summary and finding status

The [original internal audit](CODEX_INTERNAL_AUDIT_PHASES_0_4.md) is preserved
unchanged, including all nine findings and its original failed-behaviour evidence.
Actionable ingestion and worker-ownership defects now have forward-looking fixes.
Portable read-only evidence resolution is implemented and actually tested at the
backup location. The original scientific assessment and its frozen fingerprint
remain unchanged; current execution code is explicitly distinguished from it.

| ID | Severity | Resolution type | Status | Verification | Remaining limitation |
|---|---|---|---|---|---|
| AUD-001 | MEDIUM | Code defect | FIXED | Atomic process-owned case lock; cross-process/competing-worker/interruption/recovery tests; archived original race reproduced | Historical runs are not rewritten; unknown abandoned owners require explicit inspection/recovery |
| AUD-002 | MEDIUM | Portability improvement | MITIGATED | Explicit Windows-root resolver; complete copied-tree verification and both actual selected cache references tested | Original manifests intentionally keep absolute paths; no clean-room training claim |
| AUD-003 | MEDIUM | Historical provenance | DOCUMENTED | Preserved hashes, snapshots, ledger and Git anchors; provenance addendum | Independently trusted historical timestamps cannot be retroactively created |
| AUD-004 | MEDIUM | Scientific limitation | DOCUMENTED | Fixed-label diagnostics by series/class/store/product/department and validation-only subgroup errors | Six labels per M5 series remain sparse; samples not changed |
| AUD-005 | MEDIUM | Evidence preservation | MITIGATED | 4,592 copied files, all hashes verified, zero missing/mismatched | LOCAL BACKUP ON THE SAME DEVICE; off-device independence unresolved |
| AUD-006 | MEDIUM | Availability assumption | DOCUMENTED | Actual frozen 27/30-column schemas exclude price/SNAP/events | Phase 3 historical price publication latency remains unverified |
| AUD-007 | LOW | Code defect | FIXED | Canonical-normalised duplicate checks, cross-batch unique index, join/timestamp/timezone tests | Full production M5 transformation deliberately not rerun; future performance not rebenchmarked |
| AUD-008 | LOW | Current documentation | FIXED | Academic checklist and README updated; exact old versions archived | Historical reports remain historical, with explicit current addenda |
| AUD-009 | INFORMATIONAL | Study/inventory scope | DOCUMENTED | Metric trade-offs, hypothetical inventory inputs and independent gate retained | No statistical/economic superiority or Phase 5 result is established |

## Root cause and code changes

Store Item formerly checked raw date strings before their conversion to canonical
date32 days. Equivalent text dates could pass that guard. The original disposable
fixture published one duplicate canonical key; the old receipt remains in
`reports/internal_audit/data_eda/adversarial_ingestion_checks.json`. The corrected
adapter checks parsed calendar dates and names duplicate canonical keys explicitly
in its failure report. It never silently deduplicates.

`CanonicalWriter` now normalises naive timestamps to calendar days, rejects invalid/
timezone-ambiguous dates and missing keys, and enforces the exact canonical
dataset/date/store/product key through a disk-backed SQLite unique index across
batches. The cache is limited to 8 MiB; key batches remain bounded. This shared
writer also catches duplicates introduced downstream of M5/calendar/price joins.
Temporary key files are cleaned; no original canonical dataset is rebuilt.

The original final worker had a check-then-create race before its job pointer was
written. Atomic JSON replacement did not own the complete case. The corrected
public entries use an exclusive filesystem-created lock, random execution token,
PID and process creation time. Cleanup verifies ownership. A dead owner is never
automatically taken over; explicit token-matched recovery proves original-process
exit and archives the old lock. Alive/uncertain owners are refused. This works
across Windows processes and does not rely on a threading lock.

Final worker, forecast and assessment entry points now check the closed ledger
before reaching jobs, models or scoring. Original `ExperimentRegistry` attempt
ownership remains intact. Final inspection additionally reproduced two concurrent
preparation entries in archived Phase 3 and Phase 4 validation workers, without
source or model access. Their public entries now acquire the same per-case lock
before preparation or pointer creation. Controller locks, case locks and registry
attempt locks serve different purposes. No real experiment worker ran to test this.

## Regression coverage and actual validation

New regression coverage comprises 46 tests for backup safety, canonical date/key
normalisation, duplicate joins, invalid/timezone dates, valid-source preservation,
cross-process ownership, interruption, dead/live/uncertain owners, repeated calls,
sealed assessment guards and evidence relocation/traversal/hash checks.

The first complete post-fix suite passed 395 tests in 50.20 seconds. The next suite
added the explicit duplicate-report diagnostic regression: 396 tests passed in
57.75 seconds. Two further legacy-worker ownership regressions were then added.
The final complete suite passed **398 tests in 49.62 seconds**; Ruff and pip check
also passed. Final results and exact commands are recorded in
`reports/post_audit/all_worker_quality_checks.json`. No original test was removed or weakened. The initial remediation commit
`b9ff00d20460b6e91dcec28947d55b461ce71e59` remains in history; the legacy-worker
follow-up is a separate commit, without amendment or rewrite.
The audit's historical race counterexample is reproduced against archived code;
the corrected worker is tested separately for rejection of the competing owner.

Independent saved-evidence arithmetic was rerun into a **new** remediation receipt
with only its output directory changed. All 224 Phase 3 and 108 Phase 4 validation
runs plus all eight saved final cases reconcile again. The pass took 118.71 seconds
and approximately 996 MiB peak working set. No original scorer was called, no
canonical final target was reopened and no replacement scientific score was published.

## Evidence preservation and reproducibility

The expected selection fingerprint remains
`a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb`.
The original ledger remains twelve events with file SHA-256
`fa2af529b50299b50c8d77d67b0ce70f73fab35e4731a5b825dd27a20e4bc204`.
All original predictions, final actuals, score files, registries and 89 immutable
source snapshots remain byte-identical. All nine raw/canonical fingerprints match.

The pre-change baseline and eight explicit old/new source/document overlays preserve
the provenance of safe current edits. Among the 4,592 inventoried paths, the only
updated live metadata are README and `.gitignore`; their exact old bytes remain
archived and in backup. All other original inventory paths remain unchanged.
Original source snapshots additionally retain the five edited source files.
See [provenance details](POST_AUDIT_PROVENANCE.md) for the distinction between
historical evidence verification and current-code execution checks. The original
strict frozen runtime verifier was not relaxed and does not certify changed code.

Metric reconciliation is verified. Saved validation prediction reproduction remains
partial. Clean-environment end-to-end training/search reproduction is not claimed.
The new resolver preserves historical absolute paths as records, applies an explicit
read-only root mapping and offers relative/hash references for future manifests.
Actual copied-root verification and disposable relocation tests passed.

## Local backup outcome

Drive C: had approximately 265 GB free before copying. The verified inventory
contains 5,233,386,883 bytes (5.23 GB decimal). The successful destination is:

`C:/Project_Backups/Demand_Forecasting_Phase4_Evidence_verified_20261108`

**LOCAL BACKUP ON THE SAME DEVICE — not an independent off-device backup.**
Every one of the 4,592 copied entries matches its original SHA-256 and size;
missing and mismatched lists are empty. The original structure is preserved.
Originals were not moved, deleted or rewritten. The backup is outside the Git
worktree; parent and project ignore rules exclude backup folders.

The first attempt at the preferred unsuffixed name stopped with zero scientific
files copied because the utility's initial marker collided with the inventory's
original `.gitignore`. That attempt and failure receipt remain intact. The corrected
utility preserved the real `.gitignore`, used a new destination and placed its
exclusion in the backup parent. No backup was silently overwritten.

Full receipt: `reports/preservation/phase4_local_backup_verified.json`; a second
copy is `BACKUP_VERIFICATION.json` in the destination. The root also retains the
authoritative `EVIDENCE_INVENTORY.json`. Credentials, unrelated personal files,
virtual environments and test trees were excluded by inventory scope/path checks.
Same-device disk failure/theft remains a risk; no cloud upload or off-device copy
was authorised or performed. Backup utility tests include the original-ignore
collision regression, existing-destination refusal, insufficient capacity and failure
receipt preservation.

## Sampling, availability and interpretation

Fixed M5 final training still has 182,940 labels, including 123,972 zeros and
58,968 positives. All 30,490 series remain represented, but 6,878 have six zero
sampled labels; 6,864 had positive initial-prefix history. Nine products have no
positive sampled label across their stores. All ten stores and seven departments
do have positive labels. No sample or model was altered.

The all-six-zero subgroup has higher RF MAE than MA28 in each of the four validation
origins (+0.011545, +0.014844, +0.012203, +0.013072 units), while the sampled-positive
subgroup and overall mean favour RF. This descriptive association reinforces the
qualified result; it does not prove a causal sampling effect or invalidate the
predeclared mean-MAE ranking. Final outcomes were not used for this analysis or
to design a new sampling strategy. Full details and prospective-only alternatives
are in [feature/sampling qualification](POST_AUDIT_FEATURE_AVAILABILITY.md).

The actual final selected M5 RF remains price-free; future prices, SNAP and events
remain excluded. Phase 3 price-enabled evidence stays conditional. The original
final MAEs remain Store LGBM 5.434342531 and M5 RF 1.047231371; M5 MA28 remains
1.065729312 with better macro MASE. Small gains are not significance or savings.

## Exact review commands

Run from the project root using `.venv/Scripts/python.exe`:

```powershell
.venv\Scripts\python.exe -m ruff check . --no-cache
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp artifacts/test_runs/NEW_UNIQUE_REMEDIATION_RUN
.venv\Scripts\python.exe -m intelligent_demand.preservation.verify --workspace-root . --overlay reports/post_audit/remediation_overlay.json
.venv\Scripts\python.exe -m intelligent_demand.preservation.verify --workspace-root . --overlay reports/post_audit/remediation_overlay.json --inventory-root C:\Project_Backups\Demand_Forecasting_Phase4_Evidence_verified_20261108
.venv\Scripts\python.exe reports/post_audit/reproduce_legacy_workers.py --receipt reports/post_audit/NEW_LEGACY_REPRODUCTION.json
```

To create a further backup, choose a **new** destination and new receipt path:

```powershell
.venv\Scripts\python.exe -m intelligent_demand.preservation.backup --source C:\Project_Backups\Demand_Forecasting_Phase4_Evidence_verified_20261108 --inventory reports/forecasting/PHASE4_EVIDENCE_INVENTORY.json --inventory-sha256 0b1de21020f2e1d2ceaeddd10845fd723a2f6f8e75161d15fa7efb9c29f5e1ee --destination X:\NEW_PRIVATE_EVIDENCE_DESTINATION --receipt reports/preservation/NEW_VERIFICATION_RECEIPT.json
```

`X:` is an owner-selected hypothetical external/private volume, not an existing
or verified off-device destination. The original verified backup is the source
because its historical README/ignore bytes still match the unchanged inventory.
After remediation the live root must not be mislabelled an unchanged baseline copy.
Do not rerun output-producing diagnostic scripts over existing receipts; preserve
them and use new paths for any authorised repeat.

## Claude risks and readiness

The [handoff](CLAUDE_AUDIT_HANDOFF.md) gives original and remediated code, manifests,
exact safe commands and unresolved assumptions. The reviewer should challenge
locking recovery, disk-backed uniqueness, root-mapping safety, sparse labels,
operational price availability, local chronology, metric trade-offs and inventory
scenario calibration. No critical/high numerical-impact blocker was found.

**READY WITH LIMITATIONS for Claude audit.** Same-device backup, limited seasonal
coverage, sparse training, unverified historical price latency and local-only
chronological attestation remain disclosed. The independent review is still required
before Phase 5; engineering regression success alone does not provide that clearance.
