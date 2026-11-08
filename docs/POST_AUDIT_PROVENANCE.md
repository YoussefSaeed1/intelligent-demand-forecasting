# Historical assessment and forward-looking remediation

The completed scientific assessment remains the Phase 4 checkpoint
`54a689b7cb07970556bbf2fc164adf934307eab8`. Its original selection content fingerprint
is `a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb`.
No manifest, model, sealed prediction, scoring snapshot, registry record or original
access-ledger entry was replaced by remediation.

## Two explicitly different code states

The original runtime verifier compares the current implementation byte-for-byte
with 89 pre-assessment source/configuration/test/protocol files. It correctly
rejects the modified checkout. We did not weaken that verifier or update the freeze
to make new code appear old. Closed final worker/forecast/assessment commands now
also refuse access before creating jobs or reaching fitting/scoring paths.

The forward-looking corrections change three existing source files:

- `ingestion/store_item.py`: duplicate keys use canonical calendar dates.
- `validation/quality.py`: normalized canonical keys are checked across all batches
  with a bounded-cache, disk-backed unique index, before publication.
- `tuning/final.py`: exclusive case ownership and early closed-assessment refusal.

Three current documentation/ignore files also change. The six exact original files
are preserved in `reports/post_audit/original_source/`. Original scientific code is
additionally unchanged in `artifacts/experiments/phase4/code_snapshot/` and the
verified local backup. Scoped Git attributes retain original text bytes on checkout.

`reports/post_audit/baseline.json` records the state before remediation.
`reports/post_audit/remediation_overlay.json` lists only the six reviewed old/new
hashes and the exact preserved original copies. This is a change receipt, not
permission for another final execution. New modules/tests are separate additions.

The historical inventory contains 4,592 entries. **4,590 original live inventory
paths remain unchanged**. Its two current metadata paths, `README.md` and
`.gitignore`, now have forward-facing updates; their exact inventoried bytes remain
in the verified backup and archived originals. The three changed runtime source
files are checked against their original immutable snapshots and archived copies.
No original scientific evidence is silently substituted with a current version.

Use the explicit historical read-only verifier after remediation:

```powershell
.venv\Scripts\python.exe -m intelligent_demand.preservation.verify --workspace-root . --overlay reports/post_audit/remediation_overlay.json
```

It checks the original inventory, snapshot hashes, selection content fingerprint,
both registries, all nine dataset hashes, scoring-snapshot receipt bindings and the
original twelve-event ledger. It never decodes targets, appends ledger events,
fits models or publishes scores. Do not use the original final audit command under
a no-ledger-mutation rule: that original reader intentionally appends audit events.

## What chronology can establish

Content hashes establish current consistency with the retained records. The local
recorded optimisation plan predates recorded trials; the recorded selection freeze
predates recorded final fits; all eight complete predictions were recorded sealed
before the logged assessment target reads. The Phase 4 Git checkpoint anchors the
retained files at its commit, and the new remediation commit records the later code
changes without rewriting history.

The original plan/freeze were produced from a dirty checkout at the Phase 3 revision.
Local clocks, unsigned manifests and a hash chain do not independently authenticate
past wall-clock time or prove absence of out-of-band reads. No retrospective trusted
timestamp is fabricated. Earlier full-history aggregate quality checks are documented
exceptions; the once-only claim concerns the final assessment reader, not every
historical data-quality read. Future projects can precommit manifests, obtain an
independent timestamp and separate scorer permissions prospectively.

## Backup and relocation

The verified destination is
`C:/Project_Backups/Demand_Forecasting_Phase4_Evidence_verified_20261108`.
All 4,592 entries and 5,233,386,883 bytes match their original inventory hashes.
This is a **LOCAL BACKUP ON THE SAME DEVICE**, not an independent off-device backup.
The failed initial destination was retained without overwrite; it copied zero
evidence files. Credentials, virtual environments and unrelated files were not
selected. Both the destination's parent exclusion rule and project ignore rules
exclude backup directories from Git; the verified copy remains outside the repo.

Physical relocation was tested by verifying the complete copied tree at its new
root, and both real selected-model historical absolute cache references resolve
there with unchanged hashes. Disposable tests also exercise relative paths,
explicit Windows-root remapping, traversal/UNC/reparse rejection and hash failures.
Old manifests retain their original paths; the resolver applies a separate explicit
mapping. New `EvidenceResolver.reference()` records relative logical IDs and hashes
for future manifests. This does not claim clean-environment training reproduction.

Metric reconciliation remains verified; saved validation prediction reproduction is
partial; clean-room full experimental reproduction remains unverified. Disk loss,
theft or ransomware can affect both local copies. An off-device backup remains an
owner-authorised future preservation step, not a completed action here.
