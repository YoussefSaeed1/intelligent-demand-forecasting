# Phase 3A final integrity review

Review date: 2026-11-07. Scope: infrastructure correctness, adversarial synthetic tests,
read-only CLI checks, documentation consistency and a secure local Git checkpoint.
Phase 3B is unstarted. No forecasting methods, real validation scores or final holdout
reads were produced. Existing raw/canonical datasets and Phase 2 analyses were not rewritten.

## Findings and corrections

| Area | Evidence and result |
|---|---|
| Origin boundaries | Readers previously trusted duck-typed fold objects. Public data, prediction, scoring and specification boundaries now require the concrete frozen protocol fold and revalidate its dates. Synthetic future/holdout poison rows stay invisible for all eight origins; modified and forged folds fail. |
| Public model inputs | Fit requires an origin capability and rechecks it; predict requires the fitted origin, 28 steps and a complete availability-checked grid without target columns. Equivalent date strings are normalised before duplicate-key validation. |
| Final holdout | Source readers reject any window reaching the immutable final holdout boundary. The engine reads validation labels only after complete predictions are sealed. These are trusted adapter contracts, not arbitrary-Python isolation. |
| Metric scales | Streaming seasonal differences use complete chronological training through the origin only, with divisor T minus 7. Source/date/season provenance is checked before scoring. All-null object/nullable scale columns now stay undefined instead of raising a numeric-type error. No epsilon or imputed scale is used. |
| Prediction validation | Exact series/date coverage, unique keys across batches, 28-day alignment, finite numeric quantities, raw/clipped values and fallback flags are enforced. Boolean quantities and invalid batch sizes are now rejected explicitly. |
| Registry completion | A completed manifest previously could pass verification with an empty output map. All three mandatory outputs and a valid recorded attempt are now required and checksum-verified; missing, partial, changed, malformed and escaped outputs fail. |
| Comparison eligibility | The new read-only comparison gate rejects pending, running, failed and interrupted runs, as well as mismatched protocol/source/population/settings/code cohorts. It verifies completed outputs before returning candidates. No score ranking or selection was implemented. |
| Failure/interruption | Existing tests verify caught failure/interruption status, exclusive ownership, explicit stopped-owner recovery and restart into a new attempt without partial reuse. A failed final status publication cannot enter comparison. |
| Atomic publication | JSON manifests already flush and fsync before replacement. Prediction Parquet now does so too. Injected rename failures preserve the previous manifest or leave only the unpublished Parquet partial. Completion remains the final manifest write after all outputs exist. |

## Phase 3B interface readiness

| Later method | Available interface | Remaining implementation decision |
|---|---|---|
| Naive | Origin-inclusive chronological observed history, fresh local/global adapters, aligned output writer | Implement and test the forecast rule and any declared fallback |
| Seasonal Naive | Same history, daily dates and deterministic 28-day future grid | Implement weekly repetition across all 28 steps without future actuals |
| Moving Average | Projected bounded historical stream and origin cutoff | Predeclare window(s) and implement the rule without tuning on protected targets |
| Zero Forecast | Population identifiers, future calendar grid and output contract | Implement the constant-output adapter and retain complete coverage |

No blocking interface was found for those four methods. No model was registered or
implemented. The default evaluation budget of 1,000,000 rows covers each full fold:

| Dataset | Series | Days | Forecast rows per fold | Coverage bitmap bytes |
|---|---:|---:|---:|---:|
| Store Item | 500 | 28 | 14,000 | 14,000 |
| M5 | 30,490 | 28 | 853,720 | 853,720 |

Capacity tests allocate those coverage bitmaps and reject incomplete publication; they
do not produce full-population forecasts. History is streamed and scales retain seven
observations per series. Evaluation joins and summaries remain bounded by the row cap,
but their actual full-scale runtime and peak memory were not measured in this review.

## Validation and checkpoint gate

- Pytest: **203 passed in 38.70 seconds**, no warnings; 44 additional review checks
  beyond the previous 159. All fixtures are synthetic and offline.
- Ruff: passed. `pip check`: no broken requirements found.
- CLI: help/default, eight-origin plan, empty production registry, synthetic pending-run
  status and invalid/nonexistent run rejection checked without real sales access.
- Documentation: current component links and all eight documented windows checked;
  the scientific protocol Markdown and saved split manifest match the existing Git version.
- Git: stage only reviewed source, configuration, tests and small Markdown documents;
  check staged content for credentials, excluded files, binary/large outputs and whitespace
  before the authorised local commit. Detailed local evidence is ignored under
  `artifacts/experiments/`; no dataset, credential or experiment output is to be committed.

The initial full run caught a test-fixture parsing mismatch before its intended duplicate
check; the fixture was corrected to equivalent accepted daily date spellings. The final
complete suite above passed. Both initial and final logs are retained locally.

## Limits retained

Future model implementations still need adapter-specific correctness, fallback and
resource tests. A future ranking implementation must use verified eligible results and
require all four matching folds per candidate; no ranking code exists in Phase 3A.
Availability declarations need honest, reviewed evidence. The API is not a filesystem
sandbox. Hard-kill recovery requires explicit confirmation that the recorded owner has
stopped, and resume restarts the entire attempt. Atomic file publication and completion
manifests do not claim a multi-file database transaction or full power-loss recovery.
The independent Claude audit remains mandatory after Phase 4 and before Phase 5.

Architecture: [FORECASTING_ENGINE.md](FORECASTING_ENGINE.md).
Metrics: [METRIC_DEFINITIONS.md](METRIC_DEFINITIONS.md).
Progress: [PHASE3_PROGRESS.md](PHASE3_PROGRESS.md).
