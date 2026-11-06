# Phase 3 progress

## Phase 3A — final integrity review passed

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

## Preserved constraints

- Source of truth: FORECASTING_EXPERIMENTAL_PROTOCOL.md and reports/eda/proposed_splits.json;
  neither is replaced or silently changed.
- Four expanding validation origins; 28 days per origin; final holdouts remain protected.
- No real validation benchmark, final-target inspection, EDA rerun, raw/canonical rewrite,
  forecasting implementation, tuning, inventory, dashboard or deployment work.
- The user authorised a local Phase 3A checkpoint after all review gates pass; no push.
  Existing checkpoints remain in history.
- The independent Claude audit remains after Phase 4 and before Phase 5; critical/high
  findings must be resolved and independently revalidated.

## Remaining work and readiness

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
