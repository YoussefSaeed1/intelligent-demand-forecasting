# Independent audit package — Phase 4

The required independent Claude audit occurs **after Phase 4 and before Phase 5**.
Preparing this package does not perform or satisfy that independent review.
No Phase 5 inventory, deployment or dashboard work is authorised by Phase 4.

## Architecture and implementation inventory

| Component | Responsibility and evidence |
|---|---|
| `tuning/plan.py`, `configs/phase4.yaml` | Strict compact spaces, deterministic seed, exact candidates, objective, resources and comparator contract |
| `tuning/runner.py` | Sequential budgeted workers; four-origin completeness; atomic UUID attempts; verified reuse of existing Phase 3 origin panels |
| `experiments/engine.py`, `registry.py` | Origin-safe validation lifecycle; prediction-before-target scoring; owned atomic publication; failed/incomplete exclusion |
| `models/baselines.py` | Naive/seasonal/moving-average/zero reference adapters; Phase 4 frozen references use existing implementations |
| `models/statistical.py` | Fixed training-only Holt-Winters and TSB smoothing, explicit native/fallback delivery |
| `models/global_ml.py`, `features/recursive.py` | Bounded RF/CPU LightGBM; shifted features; deterministic samples; price-free encoder; recursive state and reload proof |
| `tuning/reconcile.py`, `evaluation/benchmark_audit.py`, `ml_audit.py` | Independent NumPy errors, complete persisted keys, source labels/features, historical scales and grouping checks |
| `tuning/selection.py`, `authority.py` | Passed-4B-only final capability; exact model/comparator freeze; immutable code snapshot; hash-chained access ledger |
| `tuning/final.py` | Fresh final refits; both populations' entire prediction bundle sealed first; one canonical assessment per dataset; saved-actual audit reads logged |
| `reporting/phase4_report.py` | Offline figures/report, saved-evidence summaries and audit manifest; no fitting or canonical holdout read |

## Local package and evidence paths

`artifacts/experiments/phase4/independent_audit_package.json` is a checksummed
inventory of local evidence, not a compressed duplicate of large files. It contains
source hashes and references to the original registry predictions, final predictions,
model artifacts, model metadata, feature schemas, immutable code/config snapshot,
frozen plan/selection, final metrics and access ledger. Its hashes are point-in-time;
legitimate subsequent audit reads extend the ledger without changing old events.

Training arrays remain at the model metadata's exact `feature_cache_contract` key
under the Phase 4 feature cache. Panel caches are origin-bound and checksummed;
validation panels may reference verified original Phase 3 caches. Nothing in this
package copies, uploads or deletes datasets, training caches or previous evidence.

Additional human-readable evidence:

- `PHASE4_OPTIMISATION_PROTOCOL.md`: predeclared contract and candidate rationale.
- `PHASE4_TUNING_RESULTS.md`: all matched validation comparisons and M5 RF/MA28 wins.
- `PHASE4_FROZEN_MODEL_SELECTION.md`: exact pre-holdout configurations and hashes.
- `PHASE4_FEATURE_AVAILABILITY.md`: each feature's availability and recursive policy.
- `PHASE4_FINAL_EVALUATION.md`: fixed final assessment and qualified interpretation.
- `PHASE4_LIMITATIONS.md`: scientific limitations and threats to validity.
- `PHASE4_REPRODUCIBILITY.md`: safe verification and saved-evidence commands.
- `../reports/forecasting/phase4{a,b,c,d}_gate.json`: actual gate evidence.
- `../reports/forecasting/PHASE4_FORECASTING_REPORT.html`: offline academic report.

## Review scope

Independently inspect boundaries, shifted labels/features, sample representation,
zero-demand retention, recursive updates, undefined denominators, full populations,
selection multiplicity, small gains, fallbacks, sealed artifact hashes, and access
order. Separate arithmetic correctness from statistical or business significance.
Confirm the final selection predates target access and has never been replaced.

Do not redesign or retune models using holdout errors. Any correction must preserve
scientific provenance, keep the original results visible, and distinguish an
engineering correction from a new experiment. Resolve critical/high findings and
independently revalidate before Phase 5. No external Claude invocation occurs here.
