# Phase 6 local checkpoint

This checkpoint preserves the owner's current Power BI Desktop layout. No report builder,
PBIR/TMDL generator, export writer, refresh, forecasting or inventory experiment was run.
The current PBIR definitions are authoritative; rebuilding from the layout template can
replace manual Desktop adjustments and is outside this checkpoint's scope.

## Verified scope

- Five report pages, 86 visuals, 69 DAX measures, 19 model tables and 28 relationships.
- Layer A: 7/7 current source checks pass. Layers A/E together: 13 pass, one documented
  cosmetic warning, zero failures. PBIR validation checked 94 files; 146 field references resolve.
- E06: four auto-sized caveat footers extend approximately 0.4 px beyond the 720 px canvas.
  Preserved as the owner's manual layout; not treated as a scientific or functional failure.
- Seven focused BI specification tests pass; Ruff and pip check pass.
- All 4,592 protected Phase4 inventory entries, 89 source snapshots, 332 registry records and
  nine raw/canonical fingerprint entries verified. Selection and 12-event ledger unchanged;
  no holdout target decoding, fits, scientific scoring or ledger writes.
- Current TMDL measure names and relationship endpoints match the metadata configuration;
  all eight reporting-lineage hashes and 18 reporting CSVs authenticate.
- The owner reports successful Desktop navigation, slicer and visual tests. Those manual
  interactions were not independently repeated by this checkpoint.

[Current source/report checks](../reports/powerbi/checkpoint_validation.json),
[model consistency](../reports/powerbi/checkpoint_model_consistency.json), and
[protected scientific evidence](../reports/powerbi/checkpoint_scientific_integrity.json).
The historical full 43-rule results remain in PHASE6_QA_RESULTS.md. The latest existing
qa_results.json contains Layer A only and was preserved. Live C/D engine reconciliation
was not rerun here; this checkpoint does not claim a new 43-rule full-engine evaluation.

## Preservation

The owner-provided historical report backup in Claude's temporary scratchpad was independently
verified: 97 files, 183,331 bytes, zero missing/mismatched/extra files. It predates the current
Desktop-saved bytes and was retained unchanged; temporary storage can be cleared.

The current editable project has a separate verified snapshot:
`C:/Project_Backups/Demand_Forecasting_Phase6_PBIP_verified_20261110`.
It contains 129 source files / 292,850 bytes, plus two declared verification sidecars.
Every SHA-256, size and file set reconciles. PBIX binaries and local caches/settings are
excluded; shareable editorSettings.json is retained. This is a **LOCAL BACKUP ON THE SAME
DEVICE**, not protection against device loss or SSD failure. Reporting CSVs and prior
scientific evidence remain local and ignored, authenticated by their existing manifests.

[Definition inventory](../reports/powerbi/checkpoint_definition_inventory.json) and
[preservation receipt](../reports/powerbi/checkpoint_preservation.json).
Narrow Git attributes preserve Desktop definition bytes and the hash-bound Power BI
configuration across checkout; no report definition contents were changed.
DataRoot in expressions.tmdl retains the current local path to preserve refresh behaviour;
change that parameter deliberately when relocating the project.

## Git and next phase

Commit message: `feat: complete phase 6 enterprise power bi dashboard`.
The commit hash is reported to the owner and in the ignored local post-commit receipt,
`artifacts/experiments/phase6_checkpoint_20261110/postcommit.json`, avoiding a self-reference.
No push, amend or history rewrite. The isolated
`experiments/kumo_forecast/KUMO_FEASIBILITY_REPORT.md` stays untracked and excluded.

Phase 7 has not started. The dashboard/reporting contract is ready for the owner-authorised
integration step described in PHASE7_INTEGRATION_HANDOFF.md. Existing scientific limits,
validation reuse and hypothetical NCU interpretation remain; off-device preservation is
still outstanding before academic submission.


Whitespace inspection also reports existing blank final lines in 24 Desktop-authored TMDL
files. They were reviewed and preserved byte-for-byte rather than trimmed. Git may emit
LF-to-CRLF checkout notices for unbound helper/documentation files; the PBIP definitions
and hash-bound Power BI configuration are explicitly byte-preserved and checkout-tested.
