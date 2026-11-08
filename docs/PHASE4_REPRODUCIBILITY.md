# Phase 4 reproducibility and safe verification

Run from the project root with the existing `.venv` interpreter. Data, models,
predictions, training arrays and local audit manifests remain ignored by Git.
No download or source transformation is needed. Preserve the Phase 3 checkpoint
`6e1a407de0b676e858ffec43bab1fae8d51dae1d` and all original outputs.

## Environment and tests

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m ruff check src tests --no-cache
# Use a new empty project-local basetemp name on every run.
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp artifacts/test_runs/review_new
.venv\Scripts\python.exe -m intelligent_demand --help
.venv\Scripts\python.exe -m intelligent_demand.tuning.runner --help
.venv\Scripts\python.exe -m intelligent_demand.tuning.final --help
```

LightGBM is installed through the project's `boosting` extra. Actual installed
versions and measured resources are retained in `reports/forecasting/phase4_preflight.json`.
Local test directories avoid Windows permissions inherited by older temporary files.

## Verify plan and data without rerunning search

```powershell
.venv\Scripts\python.exe -c "from intelligent_demand.tuning.plan import load_plan; p=load_plan(); print(p['contract_sha256']); print(len(p['trials']))"
.venv\Scripts\python.exe -c "from intelligent_demand.experiments.benchmark import verify_sources; print('Verified source files:', len(verify_sources()))"
.venv\Scripts\python.exe -c "from intelligent_demand.tuning.runner import execution_contract; print(execution_contract()['execution_sha256'])"
```

`load_plan()` checks the immutable settings hash, seed, exact realized trial
membership, original four origins, metadata and protocol hashes. It does not
resample or run a trial. The plan contains 23 tuning cases plus four references;
each has four authoritative full-population folds. Validation execution hashes
are separately frozen from the later complete final-assessment code snapshot.

## Independently recompute saved validation evidence

```powershell
.venv\Scripts\python.exe -m intelligent_demand.tuning.reconcile --verify-saved
```

This verifies all completed registry artifacts, reads only the original validation
targets through the origin-restricted reader, and recomputes metrics with NumPy.
It checks bounded historical training arrays and labels against origin-safe
histories. It performs no fit, target-based model selection, canonical holdout
scan or quality-gate rewrite. It may take several minutes and verifies full
populations, including undefined-denominator coverage. Do not use the mutating
initial `reconcile` command after freezing the selection.

## Verify final freeze, forecasts and saved final metrics

```powershell
.venv\Scripts\python.exe -c "from intelligent_demand.tuning.authority import verify_frozen; print(verify_frozen()['manifest_sha256'])"
.venv\Scripts\python.exe -m intelligent_demand.tuning.final verify
.venv\Scripts\python.exe -m intelligent_demand.tuning.final audit --verify-saved
.venv\Scripts\python.exe -c "from intelligent_demand.tuning.authority import ledger_events; from collections import Counter; print(Counter((e['event'],e['dataset']) for e in ledger_events()))"
```

The final audit reads the checksummed saved assessment actuals and immutable
predictions. Every saved-actual audit read appends a hash-chained access event;
it does not rescan the canonical holdout or create a new assessment. The original
4C quality gate and model selection are preserved. An audit-package ledger-head
hash is a point-in-time receipt; later legitimate audit reads extend that head.

## Recreate report summaries and figures

```powershell
.venv\Scripts\python.exe -m intelligent_demand.reporting.phase4_report tuning
.venv\Scripts\python.exe -m intelligent_demand.reporting.phase4_report final
.venv\Scripts\python.exe reports/forecasting/phase4_visual_adjustments.py
```

These commands use completed trial results and the same saved final assessment;
they never train a model, replace the frozen winner or read canonical holdout
targets. Final reporting logs its saved-actual reads. Open
`reports/forecasting/PHASE4_FORECASTING_REPORT.html` locally; all assets and links
are relative, and no internet service, external font or CDN is needed.

## Execution history, not review instructions

The original authorised execution used the following order: quality 4A → runner
`search --smoke` → `search` → independent validation reconciliation → full tests
and quality 4B → tuning report → selection freeze → final `forecast` → final
`verify` → one `assess` → independent final `audit` → quality 4C → reporting and
quality 4D. Exact logs and UUID attempts are under `artifacts/experiments/phase4`.

**Do not rerun final `forecast`, `worker` or `assess` for review.** After holdout
access, fitting and generation are prohibited; canonical target access is reserved
once per dataset. Never remove access reservations, reset the ledger or modify
frozen manifests to obtain another attempt. Underperformance is evidence, not a
reason to retune. A technical post-access defect must retain full provenance and
receive independent review before any narrowly justified correction.

The final visual QA found overlapping long M5 class labels. The separate report-only helper wraps those tick labels while retaining the same saved metric values, bars and groups. Its receipt retains input hashes and before/after image hashes. The frozen scientific package and all models/predictions remain unchanged; this is a presentation correction, not a post-holdout experiment.
