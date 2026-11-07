# Phase 3 progress

## Authorised Phase 3 execution

The master prompt authorises sequential implementation and execution of Phases 3B–3E,
with mandatory quality gates, initially leaving changes uncommitted. The subsequent
final integrity review request authorises a secure local checkpoint after its gates.
Phase 4 remains out of scope.

| Milestone | Current status |
|---|---|
| 3A infrastructure | COMPLETE; checkpoint 23c1ddeaca0cf6cced2bdf161904f8fb114d4646 verified with a clean starting tree |
| 3B baselines | COMPLETE: all 40 runs / 17,354,400 predictions independently reconciled; 260 tests, Ruff, pip and CLI gates passed |
| 3C statistical/intermittent | COMPLETE: 64 original fits plus 40 matched baseline projections independently reconciled; 297 tests and all required gates passed |
| 3D global ML | COMPLETE: 16 full-population runs; every sampled training feature/label and 6,941,760 predictions independently reconciled; 318 tests and all gates passed |
| 3E comprehensive comparison | COMPLETE: 224 independently verified evaluations, including 104 no-refit projections; 45,296,160 forecast records; 318 tests and all scientific/automated gates passed |

The original 203 tests passed before any implementation changes. Baseline arithmetic,
cache, future-poison, saved-file corruption and comparison-contract regressions expand
the suite to 318 passing tests at the final gate. ML adds independent feature/cache,
recursive-state and future-poison checks. Source hashes and resource evidence remain locally
inspectable under ignored `artifacts/experiments/phase3/`. Real final holdout targets
remain inaccessible; raw and canonical files are never rewritten.

Current baseline rules: [BASELINE_MODELS.md](BASELINE_MODELS.md).

Final reports: [benchmark](PHASE3_BENCHMARK_REPORT.md),
[comparisons](PHASE3_MODEL_COMPARISON.md), [limitations](PHASE3_LIMITATIONS.md),
and [offline HTML](../reports/forecasting/PHASE3_BENCHMARK_REPORT.html).
The final audit streamed hierarchy summaries per run to keep memory bounded;
peak OS working set was 1,309.64 MiB. Original experiment worker times totalled
3,713.01 seconds (3B 1,097.28; 3C 1,853.66; 3D 762.07), including preparation,
scoring and persistence. Maximum experiment RSS/working set was 1,447.89 MiB.
These are measured worker costs, not elapsed time for the whole interactive task.

No original experiment is incomplete. One preliminary final audit was stopped
proactively to stream growing hierarchy output; the complete replacement audit passed
without refitting any model. Browser preview through automation is unavailable because
its URL policy blocks local `file://` pages; image inspection and local link checks
are separate verified gates. The subsequent review authorises the local checkpoint;
Phase 4 is NOT STARTED.

## Final scientific integrity review and authorised checkpoint

The independent review recalculated all 224 evaluations directly from persisted
predictions and canonical validation observations. All 56 model summary rows and
56 HTML comparison rows reconciled. Persisted ML sample positions exactly reproduce
seed 42 at every origin, with every series/store/product/class represented; all
sampled labels and features reconcile to historical values. No actual-data model
was retrained. The final current suite has **320 passing tests** (49.76 seconds),
with Ruff and pip check passing.

Store Item LightGBM improves MAE by 31.097057% over Seasonal Naive. M5 RF improves
mean MAE by 0.596551% over MA28, wins three origin means and loses the third;
MA28 wins a majority of individual series in all four. Price-week completion is
verified, but actual publication latency remains an explicit conditional assumption.
No critical/high scientific defect remains in the declared research benchmark.

The user now authorises the local commit
`chore: checkpoint validated phase 3 forecasting experiments` after staged-file
security checks. No push, rewrite or Phase 4 execution is authorised. See
[scientific findings](PHASE3_INTEGRITY_REVIEW.md). The report-QA command now accepts
authorised descendant checkpoints while retaining ancestry and frozen-protocol checks.

## Phase 3A checkpoint record — final integrity review passed

Implemented: strict experiment configuration; unchanged saved protocol validation;
origin-bounded Parquet access; documented future-feature availability; local/global
model interfaces with empty production registration; complete atomic prediction output;
training-only seasonal scales; pooled/macro/horizon/class scoring and coverage; local
run/attempt registry; status, interruption and restart handling; reproducibility metadata;
read-only CLI plan/registration/status commands.

The existing 85-test baseline is retained. Added synthetic tests cover frozen split
boundaries, leap day, exact horizon, bad configurations, target visibility, future-data
requests, feature availability, static/population joins, zero scales, alignment, clipping,
JSON nulls, grouped metrics, registry state and ownership, path confinement, interruption,
new-attempt restart, changed-source cache rejection and deterministic metadata.

Final integrity suite, 2026-11-07: **203 tests passed** (the existing 85 plus 118
infrastructure checks; 44 added during final review), in 38.70 seconds, with no warnings.
Ruff passed and pip check found no broken requirements. Read-only plan/model-list commands and a
synthetic pending-run status command passed CLI smoke checks; invalid run IDs are
rejected. Evidence is retained locally in `artifacts/experiments/phase3a_validation.json`
and `phase3a_cli_smoke.json` from implementation; final review evidence uses the
`phase3a_integrity_*` and `phase3a_git_*_review.json` files in that ignored directory.
Fixture lifecycle hooks return prewritten test payloads;
no forecasting estimator is fitted and no real validation benchmark is executed.

## Constraints at the Phase 3A checkpoint

- Source of truth: FORECASTING_EXPERIMENTAL_PROTOCOL.md and reports/eda/proposed_splits.json;
  neither is replaced or silently changed.
- Four expanding validation origins; 28 days per origin; final holdouts remain protected.
- No real validation benchmark, final-target inspection, EDA rerun, raw/canonical rewrite,
  forecasting implementation, tuning, inventory, dashboard or deployment work.
- The user authorised a local Phase 3A checkpoint after all review gates pass; no push.
  Existing checkpoints remain in history.
- The independent Claude audit remains after Phase 4 and before Phase 5; critical/high
  findings must be resolved and independently revalidated.

## Remaining work recorded at the Phase 3A checkpoint

Phase 3B infrastructure is ready for explicit authorisation; it has **not started**.
Naive, Seasonal Naive, Moving Average and Zero Forecast can use the existing historical
stream, local/global lifecycle and strict horizon writer. Full population row budgets
cover both sources; real-scale execution remains unmeasured. Actual forecasting adapters,
lag/rolling feature construction, recursive
forecast logic, model-specific preprocessing, fallback implementations and real benchmark
outputs remain future work. Phase 3C–3E are also unstarted. Adapter-specific resource
limits and real-scale runtime/memory must be measured when those methods are authorised.

The capability API enforces trusted adapter boundaries, not arbitrary-code isolation.
Availability evidence and use of fold-local preprocessing must still be reviewed in
future adapters. Hard-kill recovery needs explicit stopped-owner confirmation; it never
automatically steals a live lock. Safe resume restarts an attempt from scratch; it is
not a fitted-model checkpoint mechanism.

Architecture and commands: [FORECASTING_ENGINE.md](FORECASTING_ENGINE.md).
Metric/coverage contract: [METRIC_DEFINITIONS.md](METRIC_DEFINITIONS.md).
Final integrity findings: [PHASE3A_INTEGRITY_REVIEW.md](PHASE3A_INTEGRITY_REVIEW.md).
