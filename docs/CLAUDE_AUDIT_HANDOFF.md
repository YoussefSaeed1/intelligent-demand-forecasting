# Independent Claude audit handoff — Phases 0–4

Prepared 2026-11-08. **The independent audit has not run.** Do not start Phase 5
or treat this internal remediation as an independent scientific sign-off.

## Project and versions

Intelligent Demand Forecasting & Inventory Optimisation. Original Phase 4 checkpoint:
`54a689b7cb07970556bbf2fc164adf934307eab8` (58 files).
The initial remediation commit is
`b9ff00d20460b6e91dcec28947d55b461ce71e59`, with message
`fix: remediate post-phase4 audit findings`. The final legacy-worker ownership
follow-up is discoverable with `git log -1 --format=fuller`; its message is
`fix: extend exclusive ownership to validation workers`.
History was not rewritten. No remote push or Claude invocation was performed.

Start with the unchanged [internal audit](CODEX_INTERNAL_AUDIT_PHASES_0_4.md), then
the [remediation report](POST_AUDIT_REMEDIATION_REPORT.md),
[source/evidence provenance](POST_AUDIT_PROVENANCE.md) and
[feature/sampling qualification](POST_AUDIT_FEATURE_AVAILABILITY.md).
Current academic state is in [ACADEMIC_REQUIREMENTS.md](ACADEMIC_REQUIREMENTS.md).

## Architecture and exact local evidence paths

All paths below are relative to the project root; the backup preserves them.

| Area | Paths |
|---|---|
| Environment/configuration | `pyproject.toml`, `configs/`, `docs/environment-phase3-freeze.txt` |
| Source acquisition/canonical quality | `src/intelligent_demand/ingestion/`, `validation/`; `reports/data_quality/` |
| EDA/protocol | `src/intelligent_demand/exploration/`, `reports/eda/proposed_splits.json`, `docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md` |
| Model families | `src/intelligent_demand/models/baselines.py`, `statistical.py`, `global_ml.py` |
| Feature/sample lineage | `src/intelligent_demand/features/recursive.py`, `evaluation/ml_audit.py`, `experiments/sampling.py` |
| Original Phase 3 registry | `artifacts/experiments/forecasting/` (224 completed records) |
| Phase 4 plan/trials | `artifacts/experiments/phase4/plan.json`, `execution_contract.json`, `trial_leaderboard.json`, `jobs/`, `resources/`, `registry/` (108 runs) |
| Frozen selection | `artifacts/experiments/phase4/frozen_selection.json` |
| Original scientific source | `artifacts/experiments/phase4/code_snapshot/` (89 files) |
| Exact before-change files | `reports/post_audit/original_source/` |
| Pre-change baseline/current change receipt | `reports/post_audit/baseline.json`, `remediation_overlay.json` |
| Original seal and final models/predictions | `artifacts/experiments/phase4/sealed_predictions.json`, `final_forecasts/`, `final_jobs/` |
| Original access controls | `artifacts/experiments/phase4/holdout_access.jsonl`, `access_consumed/`, `assessment_started.json` |
| Saved final actuals, not canonical reread | `artifacts/experiments/phase4/final_actuals/` |
| Original scoring results | `artifacts/experiments/phase4/final_evaluation.json`, `final_metrics/`, `final_hierarchy/` |
| Original audit package/inventory | `artifacts/experiments/phase4/independent_audit_package.json`, `reports/forecasting/PHASE4_EVIDENCE_INVENTORY.json` |
| Frozen scientific report and figures | `reports/forecasting/PHASE4_FORECASTING_REPORT.html`, `reports/figures/phase4/` |
| Internal audit reproductions | `reports/internal_audit/`, especially `independent_metrics.json`, model/protocol tests and data controls |
| Remediation numerical evidence | `reports/post_audit/independent_metrics.json`, `sampling_diagnostics.json`, `selected_feature_availability.json` |
| Remediation verification/quality | `reports/post_audit/final_preserved_evidence_verification.json`, `relocated_backup_verification.json`, `relocation_probe.json`, `all_worker_quality_checks.json` |
| Backup receipt/tool | `reports/preservation/phase4_local_backup_verified.json`; `src/intelligent_demand/preservation/backup.py` |
| New safeguards | `experiments/ownership.py`, edited canonical writer/Store adapter/final entry; `tests/test_post_audit_*`, `test_evidence_*` |

The original source directories in the table's abbreviated rows are under
`src/intelligent_demand/`; a model filename alone is not a root-level file.
Use the explicit relative path recorded by each manifest/inventory entry.

## Frozen authority and original results

Selection content fingerprint:
`a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb`.
Original ledger file SHA-256:
`fa2af529b50299b50c8d77d67b0ce70f73fab35e4731a5b825dd27a20e4bc204`.
It still has twelve events and one logged assessment read per dataset.
The actual selected models remain Store Item LGBM anchor 00 and price-free M5 RF 02.
No feature, label, configuration, winner or final score was replaced.

Do not reopen canonical final targets: Store Item 2017-12-04–31 or M5
2016-04-25–05-22. Do not fit/tune/reselect, regenerate final forecasts, call the
original final scorer or append/reset the original access ledger. Snapshot-only
arithmetic is an audit of saved evidence; any authorised snapshot reads should use
a separate reviewer access receipt when the original ledger must remain unchanged.

Current code includes forward fixes and intentionally differs from the original
89-file freeze. The original strict runtime verifier remains strict and rejects
that difference. Do not weaken it or edit the old freeze. Use the explicit
historical verifier, which checks both exact originals and declared current overlays.

## Safe independent verification commands

From the project root with its existing environment:

```powershell
git status --short --branch
git log -3 --oneline
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m ruff check . --no-cache
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp artifacts/test_runs/NEW_UNIQUE_CLAUDE_REVIEW
.venv\Scripts\python.exe -m intelligent_demand.preservation.verify --workspace-root . --overlay reports/post_audit/remediation_overlay.json
.venv\Scripts\python.exe -m intelligent_demand.preservation.verify --workspace-root . --overlay reports/post_audit/remediation_overlay.json --inventory-root C:\Project_Backups\Demand_Forecasting_Phase4_Evidence_verified_20261108
```

These commands do not fit research models or decode canonical final targets. Tests
use small synthetic model fixtures only. The verifier also hashes target-bearing
files as opaque bytes and checks statuses, lineage, receipt hashes and snapshots.
Do not invoke old `final forecast`, `worker`, `assess` or `audit --verify-saved` as
verification commands; the latter writes original audit-read events, while execution
commands must remain closed. Do not rerun output-producing scripts over old receipts.

For an independently written numerical review, inspect
`reports/post_audit/reconcile_saved_after.py`: it uses canonical validation windows
only and existing immutable final actual snapshots, without original scoring helpers.
Its historical counterpart and results remain in `reports/internal_audit/`. A later
authorised rerun needs a new output directory/access receipt; it must not replace
existing evidence. Sampling diagnostics use only old labels and validation scores,
never final outcomes for redesign.

## Remaining findings to challenge

The original audit counted six medium, two low and one informational finding, no
demonstrated critical/high. In remediation: ownership/date-key/current-doc findings
are fixed; relocation and backup risks are mitigated; chronology, sparse sampling,
conditional prices and study scope remain documented. Independently validate these
statuses rather than accepting passing tests as scientific proof.

- Check exclusivity at the worker entry, explicit dead-owner recovery, safe cleanup
  and distinction between atomic file publication and run ownership.
- Check exact canonical key representation after date/type changes and joins,
  malformed/tz input rejection, no deduplication and bounded temporary-index behavior.
- Examine the root remapping safety and immutable metadata; relocation verification
  does not demonstrate a clean training reproduction across machines.
- M5 six-label supervision gives 6,878 all-zero sampled series, with MA28 outperforming
  RF in the all-zero-sample validation subgroup despite RF's better overall MAE.
- Confirm final schemas exclude price/SNAP/events and keep Phase 3 price availability
  conditional. Review shifted/recursive features and undefined denominators.
- Local chronology is internally consistent, not independently timestamped proof.
  Prior aggregate quality reads are documented exceptions to absolute target isolation.
- M5 RF's small MAE gain does not dominate macro MASE or establish significance,
  economic benefits or universal intermittent-demand superiority.

## Backup and verification limits

Actual verified copy:
`C:/Project_Backups/Demand_Forecasting_Phase4_Evidence_verified_20261108`.
**LOCAL BACKUP ON THE SAME DEVICE; not an independent off-device backup.**
All 4,592 original entries (5,233,386,883 bytes) verified with zero missing/mismatch.
The unsuffixed failed attempt remains untouched with zero evidence copied. No cloud
upload occurred. A source checkout alone still does not include large ignored models,
predictions, actual snapshots and caches; the copied local evidence must accompany
review. Off-device disaster recovery remains unresolved.

Metric reconciliation is complete within retained evidence; validation prediction
replay is sampled; clean installation/full experimental reproduction, exhaustive
native optimizer proofs, independent trusted historical chronology and new browser
rendering remain unverified. The original frozen HTML and figures remain unchanged.
Do not claim the independent audit is complete, and do not begin Phase 5 until its
required gate is satisfied and any critical/high findings are resolved prospectively.
