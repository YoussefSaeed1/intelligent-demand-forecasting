# Phase 4 local checkpoint and evidence preservation

This is a version-control preservation receipt for the completed Phase 4 research,
not a new scientific audit, experiment, or holdout assessment. The Phase 3 ancestor
is `6e1a407de0b676e858ffec43bab1fae8d51dae1d`. The requested new commit message is
`chore: checkpoint phase 4 optimisation and final evaluation` on `main`.
Original Phase 4 reports retain their historical statements about being uncommitted
at completion; this later preservation record supersedes that version-control status.

## Frozen authority and untouched evidence

The original selection fingerprint is
`a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb`.
It is the canonical manifest-content fingerprint, not the SHA-256 of its JSON file.
Both values are preserved by the inventory and the original manifest.

The preservation check verifies all 89 scientific files and their immutable code
snapshots, the original 853-entry audit package, the eight sealed final cases,
224 completed Phase 3 registry evaluations and 108 completed Phase 4 fold runs.
It checks all nine raw/canonical file hashes. Fingerprinting treats target-bearing
files as opaque bytes: it neither decodes their targets nor recomputes scores.

The hash-chained final holdout ledger remains unchanged at 12 events, with exactly
one canonical read-start/read-completion pair per dataset. Its final head is
`d5044b81ccc65bbbfa4ec49b0da73c77e433683f9541fc799413ba20cbc1fe9d`.
The saved-actual snapshot hashes and final scoring file hash remain anchored to
the original read and assessment-completion receipts. No audit-read event is
appended by this preservation task.

Explicit `.gitattributes` rules preserve the existing mixed LF/CRLF scientific
text bytes across checkout regardless of `core.autocrlf`. No source, configuration,
test, frozen selection, original report, prediction or score is rewritten by this
preservation task. New preservation metadata is outside the frozen scientific code.

## What Git retains

Git retains reviewed source, configuration, tests, documentation, small report
JSON/HTML, and these additional preservation files:

- [Full evidence inventory](../reports/forecasting/PHASE4_EVIDENCE_INVENTORY.json):
  relative paths, sizes, SHA-256 and ignore status for all files in the declared
  evidence trees and all original audit-package references.
- [Verification receipt](../reports/forecasting/phase4_checkpoint_verification.json):
  actual registry, fingerprint, ledger, prediction-grid and report-integrity checks.
- [Technical checks](../reports/forecasting/phase4_checkpoint_checks.json): current
  test, Ruff, dependency and staging-security results.
- [Preservation verifier](../reports/forecasting/phase4_checkpoint_verify.py): reads
  original evidence without fitting, scoring, target decoding or ledger mutation.
- [Small evidence copies](../reports/forecasting/phase4_checkpoint_evidence/):
  byte-identical copies of `frozen_selection.json`, `plan.json`,
  `execution_contract.json`, `final_evaluation.json`, `holdout_access.jsonl`,
  `independent_audit_package.json`, `search_execution.json` and
  `trial_leaderboard.json`. Originals remain at their original locations below.

The sealed prediction manifest contains machine-specific paths. Its original
remains local; Git retains its exact file hash and public bundle fingerprint through
the inventory and verification receipt, rather than committing those private paths.
The original 853-entry inventory and ledger copies are historical snapshots; never
replace them to conceal later changes. Existing model-selection timestamps and
Git revision fields deliberately continue to identify the pre-assessment state.

## Essential files outside Git and recovery limits

All paths below are relative to the project root. The full inventory lists every
individual file, its current byte size and SHA-256. Git does **not** back up these
ignored originals. No separately verified backup was created or confirmed here;
hashes detect discrepancies but cannot recover missing evidence.

| Local evidence path | Contents | Recovery without reopening canonical holdout |
|---|---|---|
| `artifacts/experiments/phase4/frozen_selection.json` and other root manifests | Original authority, plan, execution, search and scoring records | The eight committed small copies recover their exact original bytes. Restore other originals from a verified backup; do not refreeze or fabricate provenance. |
| `artifacts/experiments/phase4/sealed_predictions.json` | Original sealed bundle and model configuration references | Not reconstructed by this task. Restore its exact original bytes; the committed inventory verifies its identity. |
| `artifacts/experiments/phase4/holdout_access.jsonl`, `access_consumed/`, `assessment_started.json` | Once-only ledger and access reservations | Ledger has a committed exact copy. Reservation records are inventoried and local only; restore originals. Never reset reservations to rerun assessment. |
| `artifacts/experiments/phase4/final_forecasts/`, `final_jobs/` | Final fitted models, sealed predictions, scales, delivery and pre-target proofs | Preserve or restore originals. Routine final refitting or forecast regeneration is prohibited after target access, even if technically possible. |
| `artifacts/experiments/phase4/final_actuals/` | Original saved scoring actuals and receipt manifests | Preserve or restore originals. These snapshots cannot be recovered from Git hashes; do not reopen canonical holdout to recreate them. |
| `artifacts/experiments/phase4/final_metrics/`, `final_hierarchy/` | Final scores and grouped leaf diagnostics | Recomputable in principle from preserved predictions, scales and saved actuals, without canonical rescan. No recomputation was performed; approved saved-actual readers log access. Restore originals to retain exact provenance. |
| `artifacts/experiments/phase4/registry/`, `jobs/`, `resources/` | All tuning fold specifications, states, metrics, predictions and runtime receipts | Historical records cannot be recreated exactly. New validation-only runs could reproduce calculations without final targets but would have new provenance; none were run here. |
| `artifacts/experiments/phase4/feature_cache/`, `cache/` | Bounded training arrays and origin-bound panels | Derivable from origin-restricted histories/settings without final targets. Do not use final caches to restart prohibited final fits. |
| `artifacts/experiments/phase4/code_snapshot/` | Exact pre-assessment scientific code/configuration/test bytes | The tracked files plus explicit line-ending rules preserve these bytes; the original snapshots remain local and are independently hashed. |
| `artifacts/experiments/phase4/report_only_helpers/` | Archived executed presentation helper | Preserve originals; current tracked helper has a separately documented formatting-only difference. |
| `artifacts/experiments/phase3/`, `artifacts/experiments/forecasting/` | Preserved prior registry, predictions and reused caches | Validation calculations can be reproduced without final targets. Original fitted objects, UUIDs, timings and ledger provenance require the original files or a verified backup. |
| `reports/figures/phase4/` | Eleven PNG/SVG scientific figure pairs and two QA contact sheets | Figures can be rebuilt from preserved summaries/predictions and saved actuals without canonical rescan; report generation may append saved-actual access events. No figures were regenerated here. |
| `data/raw/`, `data/processed/` | Original source CSVs and canonical Parquet | All nine authoritative hashes verified unchanged. Raw acquisition and canonical transformation are separate workflows; no download or transformation occurred. Do not use recovery as permission for another final assessment. |

The inventory excludes virtual environments, test temporary directories, generic
tool caches and credential stores. Git's ignored-path inspection also covered their
rules, but their contents are not scientific evidence and were not copied. Some
old temporary directories deny enumeration; no essential evidence path was skipped.

## Checks and safe future verification

The complete suite passed **352 tests in 64.69 seconds** during this checkpoint.
Ruff and `pip check` passed. The original 22 scientific figure files decode/parse,
their hashes match and relative report/document links resolve. Prior browser
rendering limitations remain; this task does not claim a new visual/browser audit.
Full results, inventory hash and staging-security metadata are linked above.

Run the preservation verifier from the project root to repeat read-only checks:

```powershell
.venv\Scripts\python.exe reports/forecasting/phase4_checkpoint_verify.py
```

Optional `--inventory NEW_PATH --receipt NEW_PATH` writes new exclusively created
preservation records. It refuses to replace existing receipts. This is a fingerprint
and lifecycle verification, not an independent metric or scientific audit.

No push, upload, repository/global identity change, history rewrite, evidence
relocation/deletion, scientific internal audit, Claude invocation or Phase 5 work
is part of this checkpoint. The mandatory independent audit remains outstanding.
