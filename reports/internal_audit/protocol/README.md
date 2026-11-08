# Protocol and engineering audit evidence

This bounded audit inspected optimisation design, experiment publication/lifecycle,
model selection, final access chronology, configuration portability and environment
records. It did not train, tune, regenerate forecasts, decode canonical holdout
targets, recompute holdout scores, or alter original access records.

## Reproduction

```powershell
.venv\Scripts\python.exe -m pytest reports/internal_audit/protocol/test_protocol_adversarial.py -q -p no:cacheprovider --basetemp artifacts/test_runs/NEW_UNIQUE_AUDIT_NAME
.venv\Scripts\python.exe -m ruff check reports/internal_audit/protocol --no-cache
.venv\Scripts\python.exe -m intelligent_demand forecast-plan
.venv\Scripts\python.exe -m intelligent_demand forecast-models
```

The five final synthetic checks passed in 1.02 seconds. They establish: exactly one
winner under eight simultaneous immutable publishers; failed and interrupted
attempts cannot be retrieved/ranked as complete; payload modification is detected
by the ledger chain; local clock rollback is accepted by an otherwise valid chain;
and the direct final-worker entry point has the race described below. A passing
test that reproduces an accepted defect is not a pass for that property.

The first development run of the new race fixture omitted a synthetic manifest
field and failed with `KeyError` before reaching its intended check. That fixture
was corrected. No project implementation or scientific artefact was involved.
`synthetic_checks.log` and `synthetic_checks_final.log` retain the subsequent runs.

The five CLI checks in `cli_smoke.json` exited successfully. The two JSON commands
reported `models_executed: 0`. The other three were help commands. No scientific
results were produced by the smoke checks.

`manifest_protocol_checks.json` records direct inspection of all 108 optimisation
specifications/resource receipts and independently reconstructs selection from the
27 persisted candidate scores using a separately written minimum/tie-order
calculation. Full prediction-based numerical recalculation is owned by the lead
audit and is not claimed by this sub-review.

## PROTO-01 — direct final-worker ownership race

- **Severity:** MEDIUM, demonstrated engineering defect.
- **Location:** `src/intelligent_demand/tuning/final.py:91`–`119`; the global
  controller lock is at `265`–`273` and used by `forecast_all`, but the public
  `worker` CLI action invokes `forecast_worker` directly (`826`).
- **Evidence:** `test_direct_final_worker_has_per_case_check_then_create_race`
  synchronises two workers after both have genuinely observed an absent job and
  attempt directory. Both create different UUID attempt directories and enter the
  source-preparation callback while live. The callback intentionally stops before
  any source/model access. Both synthetic attempts are preserved as failed.
- **Consequence:** direct concurrent worker invocation can bypass the intended
  single-worker case ownership and overwrite the job pointer during start-up;
  it can waste resources or leave an orphaned attempt. This is a check-then-act
  race, not failure of the individual atomic JSON replacement.
- **Impact on reported results:** no demonstrated impact. The original eight final
  jobs are sequential, and actual optimisation receipts show 108 complete runs,
  no recorded retries, 2,064.905347 worker seconds and 1,239.710938 MiB peak RSS.
- **Remediation:** use an exclusive per-case lock/reservation at every worker entry
  point in a separately versioned future implementation; preserve interrupted
  attempts and ownership tokens. Do not reopen or rerun the completed final
  assessment to test a remedy.
- **Blocks Phase 5:** not by itself. It does not invalidate existing sealed evidence;
  the mandatory external scientific audit remains a separate gate.

## PROTO-02 — relocation of preserved experiments is not transparent

- **Severity:** MEDIUM, demonstrated reproducibility limitation.
- **Location:** `experiments/config.py:54`–`55` and `66`–`71` resolve relative
  configured paths to absolute paths, which `experiments/engine.py:77` hashes into
  experiment specifications. Phase 4 `runner.py:181` and `final.py:156` store an
  absolute feature-cache path. `evaluation/ml_audit.py:39` resolves training
  arrays from that saved absolute field.
- **Evidence:** all 108 Phase 4 specifications contain absolute registry and split
  manifest paths; all eight final sealed configurations contain an absolute
  `feature_cache` path. Values are deliberately not copied into this note.
- **Reproduction:** inspect the named fields in one persisted specification and
  compare them with `load_experiment_config` results under a different project
  root; metadata identities differ. The saved cache-audit reader follows the old
  root unless a separate remapping layer is supplied.
- **Consequence:** a new checkout alone is insufficient to reuse/verify all original
  cache-dependent records after relocating the evidence tree. This is not proof
  that a fresh run could not reproduce predictions, and such a run was not made.
- **Impact on reported results:** none demonstrated in the current location.
- **Remediation:** document the required evidence-root location and design an
  explicit read-only relocation map outside immutable manifests, retaining and
  verifying original fingerprints. Do not silently edit original hashed records.
- **Blocks Phase 5:** not alone; disclose before handing evidence to another machine.

## PROTO-03 — chronology has local rather than independent attestation

- **Severity:** MEDIUM, documented evidential limitation, not proven leakage.
- **Location:** `tuning/authority.py:124`–`169`; `tuning/selection.py:185`–`205`;
  original `plan.json`, `frozen_selection.json`, `holdout_access.jsonl`.
- **Evidence:** the recorded plan predates all recorded trial fits; the recorded
  freeze predates all final fits; all final predictions are recorded as sealed
  before the first canonical access. Plan/freeze were made with dirty worktrees
  at the Phase 3 revision, with explicit code hashes and snapshots retained.
  The synthetic clock-rollback fixture shows a hash-valid ledger does not enforce
  independently trusted wall-clock chronology.
- **Consequence:** checksums and the hash chain demonstrate consistency with the
  retained checkpoint; local files cannot prove absence of out-of-band prior reads
  or independently authenticate historical timestamps.
- **Impact on results:** no evidence of compromise or post-holdout reselection was
  found. This limits the strength of the provenance claim, rather than reversing it.
- **Remediation:** disclose this qualification. Future experiments can commit and
  externally timestamp an immutable pre-access manifest and separate scorer access;
  no retrospective trusted timestamp can be invented for the completed study.
- **Blocks Phase 5:** not alone; independent review must assess the retained chain.

## Other assessed controls

- Fixed 27-case membership, settings, seed, primary four-origin macro MAE and
  1e-12 tie policy are checked by `plan.py:346`–`365` and selection code.
  Independent direct minimum selection reproduces unique winners
  `store_item_lightgbm_00` and `m5_random_forest_02`.
- Registry `completed()` validates owned attempts and all output checksums;
  failed/interrupted cases are excluded. Atomic exclusive publication and
  interruption exclusion are verified with new synthetic tests.
- All 108 actual resource records are complete, with zero recorded prior retries.
  Runtime measures active sequential worker cost, not controlled hardware
  benchmarking or total elapsed project time.
- Broad dependency bounds in `pyproject.toml` are not themselves evidence of a
  broken environment. `docs/environment-phase3-freeze.txt` has 130 exact pins;
  all 130 installed distributions match, with zero missing/extra/version mismatches.
  The original selection also records eight core package/interpreter versions.
  Clean installation and the advertised Python 3.11–3.14 compatibility matrix
  remain **NOT VERIFIED**; no network installation was undertaken.
- Original `final audit --verify-saved` appends saved-actual read events through
  `final.py:491`–`515`. It must not be used under this audit's explicit instruction
  to preserve the original ledger. The lead uses independent read-only snapshot
  reconciliation instead.
- Ignored final models, predictions and actual snapshots have no independently
  confirmed backup; hashes and manifest copies do not provide recovery. This was
  already disclosed by `docs/PHASE4_CHECKPOINT_PRESERVATION.md:62`–`67` and remains
  an evidence-preservation risk rather than a newly discovered loss.
- Existing scientific conclusions preserve M5's MAE/MASE trade-off, limited
  seasonal windows, sparse ML samples and absence of statistical/economic proof.
  No full end-to-end clean-environment reproduction or independently trusted
  historical access attestation is claimed by this bounded sub-review.
