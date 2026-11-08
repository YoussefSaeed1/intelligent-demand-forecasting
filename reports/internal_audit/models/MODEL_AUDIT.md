# Independent model and ML audit component

Scope: source inspection of all five baseline, six lightweight statistical/
intermittent, two ARIMA-family and two global ML adapters; independent synthetic
references; actual persisted ML sample positions/labels/schema; selected saved
estimator structure. No original implementation or evidence was modified, no real
model was fitted, no final predictions regenerated, no canonical/saved final
actuals decoded, and no original ledger event appended.

## Verified controls

- 18 new adversarial/reference tests passed in 4.80 seconds. New audit files pass
  Ruff. These tests are separate from the original complete suite run by the lead.
- All five baselines match independent day-index arithmetic. SES matches a
  closed-form weighted sum; Holt matches a linear state transition; additive damped
  Holt-Winters matches an independent scalar error-state recurrence across eight
  different history lengths and two demand regimes. Croston/SBA match closed-form
  positive-event smoothing; TSB matches a closed-form Bernoulli convolution.
- Both ARIMA wrappers pass an independently mocked interface test for fixed orders,
  intercept, native convergence rejection and 28-step calls. Native optimizer
  mathematical equivalence was not independently rederived in this audit. Production
  values were not refitted. Existing unit tests include finite native-fit checks.
- Four new synthetic poison tests cover RF and LightGBM on both datasets. Changing
  all future synthetic sales and, for M5, all price observations leaves price-free
  training/prediction unchanged exactly. No real final forecasts were regenerated.
- Sixteen unique validation training caches were independently checked across 80
  actual non-derived ML run references. Two final-training caches were also checked.
  Every seed-42 time-stratum position reproduces independently from its manifest;
  all arrays match their stored byte hashes; no sampled label extends past origin.
- Store Item has 300 labels per series, 150,000 total; M5 has six per series,
  182,940 total. Every 500/30,490 series is represented, including zeros, all stores,
  products and initial demand classes. No outcome-dependent filtering was found.
- Phase 3 M5 schemas have 32 features including two conditional historical-price
  features. All Phase 4 M5 schemas have 30 price-free features. Store Item has 27.
  No event/SNAP/unknown-future feature enters a final selected model.
- Actual saved selected RF has 160 trees, depth cap 16, minimum leaf 20,
  minimum split 20, feature fraction .8, seed 42, 30 inputs and one prediction
  thread. Saved selected LightGBM has 200 trees/iterations and 27 inputs. Both
  objects match sealed file hashes. No prediction call was made on these objects.

## Findings / limitations

### MODEL-01 — MEDIUM: bounded M5 samples give many active series no positive labels

Type: demonstrated limitation, not outcome filtering or a leakage defect.

- Location: `src/intelligent_demand/features/recursive.py:203`–211;
  `configs/phase4.yaml:8`; `docs/ML_FORECASTING.md:31`.
- Evidence: `sampling_verification.json`. Final selected M5 RF training contains
  6,878 series with all six sampled labels zero (22.56% of 30,490); 6,864 of those
  series had positive demand in their initial EDA history. Corresponding validation
  counts range from 6,976 to 7,225. All series remain present, so this is a limitation
  of positive-outcome representation, rather than omitted series or altered sales.
- Reproduction: run `python reports/internal_audit/models/verify_samples.py` in a
  fresh evidence output location (the current script exclusively creates its output;
  preserve the existing result). Inspect final-training records and the persisted
  labels reshaped as `(30490, 6)`.
- Consequence: a global model can borrow information across series, but the bounded
  design does not demonstrate richly supervised per-series learning; model-family
  conclusions depend on the fixed sparse sampling/budget and should not generalise
  to full-history training. Training-label coverage is not the same as positive-label
  coverage. Current validation/final comparisons and their numerical values remain
  valid for the declared bounded design.
- Remediation: retain original results; add this quantified limitation to the audit
  interpretation. Any expanded/recency-sensitive sampling study needs a prospective
  protocol and new untouched assessment data; do not retune against this holdout.
- Blocks Phase 5: no specific computational blocker, provided this limitation is
  retained and the separate independent-audit gate is satisfied. Blocks claims of
  full-history or universally representative per-series ML superiority.

### MODEL-02 — MEDIUM: persistence probe is not full prediction reproduction

Type: demonstrated verification-coverage gap, not demonstrated corruption.

- Location: `src/intelligent_demand/models/global_ml.py:54`, 167–200.
- Evidence: the reload contract compares only the first 16 training-feature rows.
  Stored final selected positions show these cover one Store Item series of 500
  and three M5 series of 30,490. The saved schema plus estimator structure and file
  checksums were independently inspected here, but that does not prove every
  recursive path after reload.
- Reproduction: inspect the first 16 persisted position rows associated with the
  selected model metadata's `feature_cache_contract`; count distinct row indices.
  `global_ml.py` creates the probe from `x[:16]`, not a population/horizon sample.
- Consequence: source and metric reconciliation must not be presented as complete
  model-reload/end-to-end reproduction. Existing model values are not shown wrong.
- Remediation: keep original final outputs intact. For future validation-only work,
  add stratified reload probes spanning feature regimes and compare a complete
  recursive validation horizon through a supported model-loading path. Do not
  regenerate protected final predictions during this audit.
- Blocks Phase 5: blocks a claim that full prediction reproduction was established;
  not by itself an inventory-scenario implementation blocker.

### MODEL-03 — MEDIUM: Phase 3 historical-price availability remains conditional

Type: documented unresolved operational assumption, not demonstrated future leakage.

- Location: `src/intelligent_demand/features/recursive.py:60`–79;
  `docs/FEATURE_AVAILABILITY.md:19`–32.
- Evidence: Phase 3 M5 training/inference reads prices at target indices t−34 to
  t−7 inclusive. This uses completed weeks, but no publication timestamp evidence
  proves the prices were operationally available. Actual Phase 3 schemas retain
  the two price features. All Phase 4 candidate/final schemas and actual selected
  M5 RF are price-free, so this does not contaminate their primary claim.
- Reproduction: compare Phase 3 vs Phase 4 feature schemas and feature-count entries
  in `sampling_verification.json`; inspect the source index expression.
- Consequence/impact: retain Phase 3 price-enabled comparisons as conditional
  research references; they do not establish operational forecasting results.
  No change to price-free Phase 4 numerical conclusions is required.
- Remediation: preserve the conditional label and exclude those results from claims
  requiring established operational availability. Obtain publication evidence only
  for a prospective operational price-feature experiment.
- Blocks Phase 5: not for scenarios using the frozen price-free selected model;
  blocks operational claims for the earlier price-enabled variant.

## Further limits

RF treats static ID codes as ordinal numbers; LightGBM declares them categorical.
This is correctly disclosed in the original ML documentation. Rolling means/std
update recursively from clipped predicted points; occurrence/ADI/CV²/age summaries
remain frozen at the true origin. This avoids inventing observed occurrences but
creates a deliberate multi-step distribution shift, not a causal occurrence model.
No synthetic or production model was tested as a hostile arbitrary Python program;
the capability interface is an application-integrity boundary, not a security sandbox.

## Replayable evidence

```powershell
.venv\Scripts\python.exe -m pytest -q reports/internal_audit/models/test_model_audit.py -p no:cacheprovider --basetemp artifacts/test_runs/NEW_UNIQUE_AUDIT_DIRECTORY
.venv\Scripts\python.exe -m ruff check reports/internal_audit/models --no-cache
.venv\Scripts\python.exe reports/internal_audit/models/verify_selected_estimators.py
```

`verify_samples.py` independently creates `sampling_verification.json` with exclusive
creation. It never replaces an existing output. `sample_audit.json` and
`sampling_representation.json` retain earlier focused calculations; the combined
`sampling_verification.json` is the complete replayable sample check.
