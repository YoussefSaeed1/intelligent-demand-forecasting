# Phase 3D global machine learning

Two fixed global regressors are fitted separately for each dataset and each of
the four approved expanding origins. The 28-day strategy is recursive: later
lag/rolling features use only earlier clipped point predictions. Validation
actuals never update the state. Raw predictions and clipping flags remain saved.
Observed activity and historical-price snapshots stay frozen at the true origin.
See [feature availability](FEATURE_AVAILABILITY.md) for the precise contracts.

## Fixed configurations

`configs/ml.yaml` is the versioned source of truth; seed 42 is fixed.

- Random Forest: 80 squared-error trees, depth at most 12, at most 512 leaves,
  minimum leaf size 20, feature fraction 0.8, bootstrap sample fraction 0.7.
  Four threads fit the forest; one thread predicts for deterministic summation.
  Static identifiers are ordinal codes, a limitation of this initial comparator.
- LightGBM 4.6.0: CPU regression, 200 rounds, learning rate 0.05, 31 leaves,
  minimum leaf size 50, minimum categorical group size 20, 63 histogram bins,
  four threads, deterministic column-wise processing, fixed random seeds.
  Static identifiers are declared categorical. No validation early stopping.

No tuning, feature selection against validation scores or systematic search is
performed. Both use squared-error training objectives; the approved evaluation
criterion remains four-fold mean macro per-series MAE. Model comparisons use
identical validation observations, not training-objective values.

## Bounded training and full evaluation

Store Item fits 150,000 sampled rows per origin (300 from each of 500 series).
M5 fits 182,940 (six from each of 30,490 series). Training uses equal series/time
strata with seed 42, not outcome-dependent sampling. All available prior values
remain eligible feature history. Evaluation covers the full 500/30,490 series,
28 days, four origins. These initial resource-bounded fits are not claims about
performance from training on every historical row.

The sequential supervisor limits each worker to 2 GiB RSS, four threads, and
1,800 seconds. At least 512 MiB system memory must remain available. Feature
arrays are float32, checksummed and memory mapped; construction uses 8,192-row
batches. Current scikit-learn NaN validation needs writable input, so the forest
receives a bounded working copy without altering its immutable feature cache.

Nonfinite native predictions trigger an explicit whole-series/window Seasonal
Naive fallback, with requested/actual method and reason saved. Shape/schema
failures stop the run. Finite negative predictions are clipped by the common
policy and clipped values enter recursive state. No rounding is applied.

## Persistence and verification

RF uses local joblib; LightGBM uses its text format. The fitted encoder schema,
static mappings, model metadata and reload proof accompany each run. Reloaded
models must reproduce 16 training-feature probes within 1e−12. Public lifecycle
tests also check repeated recursive predictions and future-target poisoning for
both datasets and both estimators. Only this project's trusted local models are
loaded. Atomic registry completion requires all declared output hashes.

Execution (valid completed runs are reused):

```powershell
.venv\Scripts\python.exe -m intelligent_demand.experiments.benchmark run --phase 3d
.venv\Scripts\python.exe -m intelligent_demand.evaluation.benchmark_audit --phase 3d
```

Actual validation results and resources are reported separately after the
independent Phase 3D gate passes; this document specifies the initial design.
