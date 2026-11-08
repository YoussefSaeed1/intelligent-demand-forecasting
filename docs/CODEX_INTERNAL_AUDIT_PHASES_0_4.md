# Codex internal scientific and technical audit — Phases 0–4

Audit date: 2026-11-08 (Africa/Cairo). Reviewed checkpoint:
`54a689b7cb07970556bbf2fc164adf934307eab8`, branch `main`, 58 committed files.
This is the development agent's internal challenge review. It is not Claude's
mandatory independent audit, which remains outstanding.

## 1. Executive audit verdict

**Ready for the separate independent audit, with documented limitations. Phase 5:
CONDITIONAL, not cleared to start.** No demonstrated critical or high scientific
defect was found within the verified coverage. This is not proof that none exists.
Findings: **0 CRITICAL, 0 HIGH, 6 MEDIUM, 2 LOW, 1 INFORMATIONAL**.

Independent arithmetic agrees with every saved Phase 3 validation evaluation
(224), every Phase 4 validation evaluation (108), and all eight frozen final cases.
That covers 45,296,160 Phase 3, 45,177,440 Phase 4 validation and 3,470,880 final
prediction records. Complete keys, horizon, seven metrics, macro/pooled arithmetic,
per-series results, horizon/class breakdowns and undefined coverage were checked.
These counts are model-specific records, not independent statistical observations.

There are demonstrated engineering weaknesses in direct-worker ownership and
date-key normalisation, plus consequential limitations in sampling, relocation,
evidence backup and historical chronology. None has demonstrated an error in the
preserved numerical results. Existing implementation and scientific evidence were
not changed. No research fitting, tuning, canonical holdout rescan, final forecast
regeneration, replacement final scoring or original ledger mutation occurred.

## 2. Methodology and evidence restrictions

The review used direct source/configuration inspection, separately written NumPy
calculations, source-bounded scans, saved-estimator validation replay and new
synthetic adversarial tests. Reusing an original verifier established consistency;
the separately authored calculation script established independent arithmetic.
Audit scripts and receipts are in [reports/internal_audit](../reports/internal_audit/).

Canonical sales scans selected only initial EDA or the four validation windows.
For final arithmetic, only checksummed `final_actuals` snapshots were decoded;
their identities were matched to the original canonical-read receipts before use.
Their two read events are recorded in the **new**, separate
`reports/internal_audit/saved_snapshot_audit_access.jsonl`. The original access
ledger was neither appended nor rewritten. The original `final audit --verify-saved`
command was intentionally not used because it appends access events.

Historical training denominators were recomputed in 64-series blocks from
checksummed, origin-only memory-mapped panels. Direct canonical validation scans
supplied the validation actuals. Full historical quantities were recomposed from
disjoint EDA, validation and saved-final partitions; canonical final targets were
not read to obtain those totals. Raw M5 overlap verification restricted CSV columns
to `d_1`–`d_1913`; `d_1914`–`d_1941` were not decoded.

## 3. Source files and evidence inspected

- Foundation: `pyproject.toml`, package/CLI/configuration modules, `.gitignore`,
  `.gitattributes`, README, academic requirements and complete environment freeze.
- Data/EDA: ingestion adapters, source discovery/validation/writer code, Phase 1
  audit records, Parquet schemas/metadata, raw CSV headers, EDA pipeline/statistics,
  persisted series/group tables, EDA findings and the frozen split protocol.
- Models/features: baseline, statistical/intermittent and global ML implementations,
  recursive encoder, sample selection, cache contracts and saved selected estimators.
- Evaluation/experiments: metrics, alignment, scales, origin capability boundaries,
  registry, sampling/projection, tuning plan/runner/selection/final authority.
- Preserved evidence: all **4,592** inventory entries, **5,233,386,883 bytes**, the
  original 853-entry audit package, 89 frozen scientific files and their snapshots,
  332 validation registry records, final manifests and twelve ledger events.
- Presentation: Phase 4 report/gates, 22 scientific image assets, offline links,
  eleven figures via existing contact sheets and the current full-size class chart.
  This was not a fresh browser render or exhaustive EDA-figure visual review.

The scripts retain exact inspected paths and calculations. The principal evidence
receipts are [integrity.json](../reports/internal_audit/integrity.json),
[independent_metrics.json](../reports/internal_audit/independent_metrics.json),
[data/EDA controls](../reports/internal_audit/data_eda/data_eda_checks.json),
[ML sample verification](../reports/internal_audit/models/sampling_verification.json),
[selected estimator inspection](../reports/internal_audit/models/selected_estimator_inspection.json),
and [protocol evidence](../reports/internal_audit/protocol/README.md).

## 4. Verification coverage and evidence matrix

PASS applies only to the stated checked property. WARNING identifies a real limit
or demonstrated defect; NOT VERIFIED means no acceptance claim is made.

| Criterion | Verification method | Result | Evidence path | Confidence / limitation |
|---|---|---|---|---|
| Checkpoint, branch, file count | Direct Git inspection, parent/history and checkout hashes | PASS | `integrity.json`; checkpoint preservation record | Local checkpoint identity; no remote attestation |
| Original evidence preservation | Size/SHA-256 of every committed inventory entry | PASS | `integrity.json` | All 4,592 match; hashes do not provide backup |
| Raw/canonical fingerprints | All nine authoritative file hashes | PASS | `integrity.json` | Byte identity, not a new full-source final-target scan |
| Full rows and historical quantities | Parquet metadata plus disjoint numerical recomposition | PASS | `audit_summary.json`; data controls | Final partition comes from anchored saved snapshots |
| Business keys/date continuity | All EDA keys and every validation/final prediction grid | PASS | data controls; independent metrics | Current canonical final keys use original audit + saved snapshot evidence |
| Full raw-to-canonical final row equality freshly rescanned | Would require protected canonical targets | NOT VERIFIED | Original Phase 1 audits retained | Deliberately not repeated |
| Raw M5 overlap | Independent rowwise hashes/quantity checks over all 1,913 common days | PASS | `data_eda_checks.json`; `m5_remaining_overlap.json` | No concatenation; excludes final 28 days |
| Missing prices/source-null handling | Prefix scans, original full audit, joins/code | WARNING | data controls; Phase 1 M5 audit | Genuine missing prices preserved; publication latency unknown |
| EDA classes and denominators | All 30,990 series independently recomputed | PASS | data controls | Initial prefix and active-span sensitivity only |
| EDA no detailed future-outcome use | Predicate and downstream lineage inspection | PASS | data controls; EDA source | Aggregate integrity exceptions exist; not literal absence of all prior target reads |
| Four origins/H28 | Manifest, code and actual prediction-date checks | PASS | independent metrics | Adjacent seasonal windows, not iid replications |
| Baseline/smoothing/intermittent mathematics | Independent numerical synthetic references | PASS | `models/test_model_audit.py` | Tested histories/initialisation variants; not universal proof |
| ARIMA/SARIMA wiring and convergence rejection | Independent mocked native interface tests + code | PASS | `models/test_model_audit.py` | Native optimizer mathematics not independently rederived |
| Native ARIMA/SARIMA clean-room equivalence | No fresh research refits | NOT VERIFIED | Model audit | Existing project tests run; full external-library proof not claimed |
| Future-target and price poisoning | New RF/LGBM synthetic tests on both datasets | PASS | model synthetic tests | Application boundary, not arbitrary-code security sandbox |
| Actual ML sample/schema membership | 16 validation and two final caches, 80 validation run references | PASS | sampling verification | Many positive-history series have no sampled positive labels |
| Price-free final M5 estimator | Actual saved model, 30-column schema and manifests | PASS | selected estimator inspection | Phase 3 price-enabled scores remain conditional |
| All 332 validation metric evaluations | Independent aligned numerical recalculation | PASS | independent metrics | Scales independently recomputed from verified historical panels |
| All eight saved final metric cases | Independent snapshot-only recalculation | PASS | independent metrics | Audit of original fixed assessment, no new selection |
| Frozen selection/configurations | Fingerprint, exact files and independently reproduced minima | PASS | integrity; protocol checks | Local chronological attestation remains limited |
| Registry complete-only publication | All statuses/hashes plus new adversarial failures | PASS | integrity; protocol tests | Direct final worker has a separate ownership race |
| Direct final-worker concurrent ownership | Controlled synthetic competing workers | WARNING | protocol adversarial test | Demonstrated defect; original execution was sequential |
| Ledger order/receipt integrity | Hash chain, seals, read reservations and chronology comparisons | PASS | integrity; protocol checks | Unsigned local records cannot prove no out-of-band access |
| Installed dependency consistency | Full environment freeze plus pip check | PASS | protocol checks; technical checks | All 130 distribution pins match current installation |
| Clean install and Python-version matrix | Not installed on fresh hosts/interpreters | NOT VERIFIED | Reproducibility discussion | Current tested interpreter is Python 3.14.0 |
| Prediction reproduction | Existing validation-model replay, 17,584 records | PASS | `prediction_replay.json` | One origin, two models; M5 sampled 128 series |
| Full/final prediction reproduction | Prohibited final regeneration; no clean-room rerun | NOT VERIFIED | Reproducibility discussion | Do not extrapolate the sampled replay result |
| Figures, offline report links/hashes | Decode/parse, links and contact-sheet inspection | PASS | integrity; visual notes | Current native browser rendering remains NOT VERIFIED |
| Scientific/economic inference | Conclusions checked against reconciled evidence | WARNING | Sections 12–14 | Small M5 gain is not significance or inventory savings |

Paths abbreviated in this matrix refer to `reports/internal_audit/` unless stated.

## 5. Findings by severity

### AUD-001 — MEDIUM: direct final-worker entry has no exclusive per-case ownership

- **Type/location:** demonstrated engineering defect;
  `src/intelligent_demand/tuning/final.py:91`–119, 265–273, CLI dispatch 826.
- **Evidence/reproduction:** `protocol/test_protocol_adversarial.py`, test
  `test_direct_final_worker_has_per_case_check_then_create_race`. Two workers
  both observe absent state and enter the preparation callback. The callback stops
  before source/model access. Each atomic pointer write is individually serialised
  in the fixture to exercise a valid Windows schedule without sharing conflicts;
  the worker lifetime is not locked. Two UUID attempts are retained.
- **Consequence:** check-then-act ownership can waste resources, overwrite a job
  pointer and leave an orphan attempt. Atomic replacement alone does not own a run.
- **Prior-result impact:** none demonstrated. Original cases were executed
  sequentially; the immutable eight-case bundle reconciles completely.
- **Remediation:** prospective exclusive per-case token/lock at every entry point,
  in a separately versioned implementation. Do not rerun the closed assessment.
- **Phase 5 block:** no for using preserved outputs; blocks claiming that all
  public worker entry points enforce exclusive ownership.

### AUD-002 — MEDIUM: preserved experiments depend on the original absolute root

- **Type/location:** demonstrated portability limitation;
  `experiments/config.py:54`–71, `experiments/engine.py:77`,
  `tuning/runner.py:181`, `tuning/final.py:156`, `evaluation/ml_audit.py:39`.
- **Evidence/reproduction:** all 108 Phase 4 specifications hash absolute registry/
  split paths; all eight final configurations record an absolute feature-cache path.
  Inspect those fields under a different root; the cache-audit reader follows the
  old root. Private path values are not reproduced in this report.
- **Consequence:** cloning source plus moving evidence does not transparently
  reproduce every original record. A different root changes specification identity.
- **Prior-result impact:** none demonstrated in the current location. It does not
  prove a fresh, separately identified run could not reproduce predictions.
- **Remediation:** explicit read-only root remapping outside immutable manifests,
  with original hashes retained; portable relative paths for future experiments.
- **Phase 5 block:** no locally; must be disclosed for independent-machine review.

### AUD-003 — MEDIUM: recorded chronology has no independent historical attestation

- **Type/location:** evidential limitation, not a demonstrated holdout compromise;
  `tuning/authority.py:124`–169, `tuning/selection.py:185`–205 and original plan/freeze.
- **Evidence/reproduction:** recorded plan precedes trials; recorded freeze precedes
  final fits; complete predictions precede the logged assessment reads. The new
  synthetic ledger test accepts a backdated local clock while retaining a valid
  hash chain. Plan/freeze were created at the Phase 3 revision with dirty worktrees,
  explicit byte hashes and retained snapshots; the later checkpoint anchors them now.
- **Consequence:** integrity and internally consistent order are supported; local
  files cannot independently prove historical timestamps or absence of external reads.
- **Prior-result impact:** no evidence of tampering, compromise or reselection found.
- **Remediation:** qualify the claim now; prospective external timestamp/commit and
  separated scorer access. No retrospective trusted proof can be manufactured.
- **Phase 5 block:** not alone; external audit must assess this limitation.

### AUD-004 — MEDIUM: complete series membership is sparse positive-label supervision

- **Type/location:** quantified sampling limitation, not outcome filtering;
  `features/recursive.py:203`–211; `configs/phase4.yaml:8`.
- **Evidence/reproduction:** `models/sampling_verification.json`, independently
  reproduced seed-42 strata/labels. Final M5 RF uses six labels per series; **6,878
  series (22.56%) have six zero sampled labels**, including 6,864 with positive
  initial-prefix history. Validation corresponding counts are 6,976–7,225.
- **Consequence:** a global model borrows across series, but the budget does not
  establish rich per-series supervision or general performance under full training.
- **Prior-result impact:** comparisons remain numerically valid for this declared
  bounded design. Do not describe them as full-history ML experiments.
- **Remediation:** preserve quantified caveat; any expanded/recency-sensitive sample
  study needs prospective validation and untouched assessment data, not holdout retuning.
- **Phase 5 block:** no for qualified scenarios; blocks broad/full-history claims.

### AUD-005 — MEDIUM: essential ignored evidence has no confirmed independent backup

- **Type/location:** preservation risk, not observed loss;
  `.gitignore:39`–49 and `docs/PHASE4_CHECKPOINT_PRESERVATION.md:62`–67.
- **Evidence/reproduction:** all inventory paths exist and match; most evidence is
  ignored. A Git-only checkout lacks final estimators, prediction files, scoring
  snapshots and caches. Small committed manifest copies and hashes cannot recover them.
- **Consequence:** local disk loss could make metric/model evidence unrecoverable;
  reopening the closed canonical holdout is not an authorised recovery strategy.
- **Prior-result impact:** none currently; all 4,592 files are present and verified.
- **Remediation:** arrange a separate authorised backup preserving bytes/relative
  paths, then verify against the inventory. No backup/upload was performed here.
- **Phase 5 block:** no numerical blocker, but preservation should precede further
  changes or evidence transfer. This commit must not be described as a data backup.

### AUD-006 — MEDIUM: Phase 3 historical-price availability is conditional

- **Type/location:** disclosed operational assumption, not established future leakage;
  `features/recursive.py:60`–79; `docs/FEATURE_AVAILABILITY.md:19`–32.
- **Evidence/reproduction:** Phase 3 M5 schemas retain two price summaries over
  target indices t−34 through t−7. Completed source weeks do not establish actual
  publication latency. Compare those 32-column schemas with Phase 4's 30 columns.
- **Consequence:** Phase 3 price-enabled scores cannot support unqualified operational
  availability claims. Missing prices and missing-price indicators are not evidence
  that a record was published by the forecast origin.
- **Prior-result impact:** conditional Phase 3 references remain conditional; all
  Phase 4 ML candidates and the actual selected final RF exclude price information.
- **Remediation:** retain conditional labels; obtain publication evidence only for
  a prospective price-enabled operational study. Do not replace current results.
- **Phase 5 block:** no for the frozen price-free method; blocks operational claims
  based on the earlier price-enabled variant without further evidence.

### AUD-007 — LOW: source duplicate guard compares date strings before normalisation

- **Type/location:** demonstrated ingestion defect;
  `ingestion/store_item.py:31`–37 and `validation/pipeline.py:106` onward.
- **Evidence/reproduction:** run
  `reports/internal_audit/data_eda/adversarial_ingestion_checks.py` with new
  `--run-name` and `--receipt`. Strings `2013-1-1` and `2013-01-01` parse to the
  same date but bypass raw-string key checking. The synthetic profile reports zero
  source duplicate keys and publishes one duplicate canonical business key.
- **Consequence:** a malformed replacement source can pass this profiling guard;
  independent persisted-key validation remains necessary.
- **Prior-result impact:** none demonstrated: real source hashes and existing
  independent key audits match; all current EDA and prediction grids are unique.
- **Remediation:** normalise date keys before duplicate checking and verify canonical
  uniqueness before publication in a future ingestion revision. Frozen source was
  not changed during this audit.
- **Phase 5 block:** no for the already verified datasets; fix before new ingestion.

### AUD-008 — LOW: academic checklist still describes completed Phase 4 work as future

- **Type/location:** demonstrated documentation inconsistency;
  `docs/ACADEMIC_REQUIREMENTS.md:18`–19 and 22.
- **Evidence/reproduction:** checklist calls optimisation and final test future and
  says no new commit, while checkpoint, actual trials and frozen assessment exist.
  Other older protocol documents are explicitly historical and should remain so.
- **Consequence:** an examiner reading the checklist alone can misjudge project state.
- **Prior-result impact:** none; scientific records and primary conclusions are intact.
- **Remediation:** use this dated audit as the current-state addendum; later update
  the checklist with historical/current labels without rewriting original evidence.
- **Phase 5 block:** no; resolve presentation consistency before academic submission.

### AUD-009 — INFORMATIONAL: forecasting evidence is not inventory or universal superiority

- **Type/location:** study-scope constraint;
  `docs/PHASE4_LIMITATIONS.md:3`–25; `docs/INVENTORY_SIMULATION.md:3`–27.
- **Evidence/reproduction:** two datasets, four adjacent validation windows, one
  final H28 window, no stock availability/lead-time/cost inputs and no dependence-
  aware significance analysis. Reconciled M5 MAE and MASE rankings differ.
- **Consequence:** numerical accuracy supports bounded historical comparisons,
  not significance, causal mechanisms, universal transfer or realised savings.
- **Prior-result impact:** no reversal; these qualifications already accompany the
  main reports and remain mandatory.
- **Remediation:** preserve scope and hypothetical-scenario labels; predeclare any
  future policy calibration using training/validation evidence only.
- **Phase 5 block:** missing scenario contracts block a responsible implementation;
  explicitly hypothetical inputs can address that after independent audit approval.

## 6. Data quality and EDA assessment

| Dataset | Full rows | Series | Historical coverage | Reconciled units |
|---|---:|---:|---|---:|
| Store Item | 913,000 | 500 | 2013-01-01–2017-12-31 | 47,704,512 |
| M5 | 59,181,090 | 30,490 | 2011-01-29–2016-05-22 | 66,927,173 |

The independent EDA-prefix scans verified Store Item 843,000 rows/43,666,945 units
and M5 54,912,490 rows/61,066,490 units. Canonical schema is typed daily date32,
double sales, string identifiers and boolean observed flags; integer quantities
remain exactly representable. No prefix missing/duplicate keys or negative sales
were found. All-series ADI and positive-size population CV² reproduce saved tables,
including the separate leading-zero/active-span sensitivity and insufficient-positive
history class. Date denominators and additive daily/store/product/category/department
totals reconcile. Seasonal diagnostic code uses training-prefix aggregate series;
descriptive seasonal strength is not a forecasting-performance result.

Store Item's single zero observation (2014-01-15, store 6/item 4) is preserved.
Its unlabeled 45,000 competition-test rows are not observed sales or canonical
training labels. Null category/price fields are structural unavailable covariates.
The missing-calendar-source warning does not imply missing sales dates.

M5 raw validation/evaluation files overlap over all 1,913 common days and must not
be concatenated. Both prefix and remaining 112 pre-holdout days independently match
for every series. The original full audit records 12,299,413 missing historical
price observations, including 12,298,948 in the EDA prefix. Null prices were retained;
the current audit did not redo final-date price joins. Original join/cardinality
evidence plus unchanged canonical bytes supports the preserved full-file result.

**EDA isolation qualification:** `exploration/pipeline.py:187`–224 decodes full
sales for aggregate integrity counts/totals/zeros, a documented exception in
`EDA_FINDINGS.md:12`–16. Actual analysis panels, demand classes and selection metadata
use only the initial prefix. The full-history reference is used for reporting,
not features/classification/search. Therefore “no detailed future-target analysis
or model-choice feedback found” is supported; “no future target was ever read before
freeze” is not. Phase 1 quality work also necessarily predates the assessment.
Outliers remain observations; SNAP/event differences are observational descriptions,
not causal effects or assumed available future regressors.

## 7. Forecasting implementation assessment

Five baselines match separate day-index arithmetic, including weekly repetition
beyond day seven and four-week same-weekday averaging. SES matches its closed-form
weighted sum; Holt matches a separate linear-state recursion; damped additive
Holt-Winters matches scalar error-state equations over eight lengths and two demand
regimes. Croston/SBA match positive-event smoothing and correction; TSB matches a
Bernoulli convolution with zero-period probability updates. These validate the
implemented initialisation variants, not uniqueness among textbook conventions.

ARIMA(1,0,0) and SARIMA(1,0,0)(1,0,0)[7] wrappers pass independent order/intercept,
H28 and failed-convergence interface checks. Native library optimizer mathematics
was not independently rederived or exhaustively refitted. Original suite tests also
exercise native/synthetic behavior. Short/all-zero rules, clipped nonnegative
delivery, native/fallback labels and persisted output alignment were inspected.
Complete persisted prediction grids and fallback flags were recalculated for every
evaluated run; a native-family label was not accepted as proof of native delivery.

## 8. ML sampling, availability and leakage

All 16 unique validation ML caches across 80 non-derived run references and the two
selected final caches have reproducible seed-42 strata, array hashes and origin-
bounded labels. Phase 3 and Phase 4 use the same positions within each origin.
Store Item retains 150,000 labels (300 per series); M5 retains 182,940 (six per
series), approximately 0.3231% of final eligible labels. Zeros and all stores,
products/classes remain eligible; AUD-004 qualifies positive-outcome representation.

| Actual feature group | Availability at origin | Audit assessment |
|---|---|---|
| Store/item and M5 hierarchy IDs | Static published benchmark universe | Target-free deterministic mappings; RF treats integer codes ordinally, LGBM categorical |
| Lags 1/7/14/28/56; means 7/28/56; std 7/28 | Historical observed | Strictly shifted before each label; recursively use own clipped forecasts after origin |
| Zero fractions, positive count, ADI/CV², capped age | Historical observed | Shifted in training; frozen at true forecast origin during recursion |
| Weekday/day/month/weekend, periodic calendar terms, elapsed days | Known future | Date-derived; no outcomes required |
| Historical price summaries in Phase 3 M5 | Availability unverified | Completed-week lag is conditional, not proven publication timing |
| Historical/future prices in Phase 4 | Excluded | All candidates and actual selected M5 RF have no price columns |
| SNAP/events | Availability unverified; excluded from ML | No final selected feature uses them |
| Future actual sales | Unknown future; prohibited | New synthetic poison fixtures leave both RF/LGBM outputs unchanged |
| Initial demand classes/total volumes | Training-prefix reporting/sampling metadata | Not model feature columns or target encodings |

The actual final saved RF has 160 trees, depth cap 16, minimum leaf 20, minimum
split 20, feature fraction .8, seed 42 and 30 inputs. The final saved LGBM has
200 iterations and 27 inputs. Their bytes match the sealed hashes. Public model
capabilities restrict dates/fields and revalidate boundaries, but are not a security
sandbox against malicious Python with direct filesystem access. Recursive observed
activity stays frozen while means/lags evolve; that deliberate distribution shift
is a methodological limit, not demonstrated future leakage.

## 9. Experimental and hyperparameter optimisation validity

The actual four expanding origins and H28 grids match the frozen protocol. All
full-population comparisons cover 500/30,490 series. Phase 3 ARIMA/SARIMA use
training-prefix stratified subsets, with baseline projections on those same keys;
subset results are not population estimates. The independent recalculation accepts
each run's explicit hashed series membership and uses matched targets and dates.
Registry statuses/owned outputs are verified; incomplete attempts cannot be ranked.

Phase 4 has 23 tuning configurations plus four references: 27 cases × four origins
=108 completed runs. The recorded plan precedes trial execution, settings and exact
membership reproduce, seed/budgets and primary mean-four-origin macro MAE are fixed.
No early-stopping feedback or final-target search use was found. Independent metrics
and an independently written minimum/tie-order calculation reproduce unique winners
`store_item_lightgbm_00` and `m5_random_forest_02`. Store Item's anchor stayed best;
additional tuning did not improve it. All 108 resource receipts are complete, with
zero recorded retries, 2,064.905347 active worker seconds and 1,239.710938 MiB peak.
Those times are not controlled hardware benchmarks or total elapsed project time.

Finite search on the same four origins introduces selection optimism; there is no
nested-validation or formal multiplicity correction claim. Final assessment supplies
a separate fixed check but only one seasonal window per source.

## 10. Frozen selection and holdout integrity

Expected and observed content fingerprint:
`a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb`.
All 89 scientific current files, snapshots and Git checkout-filtered bytes match.
Protocol and nine authoritative source/canonical hashes remain unchanged.

The recorded freeze is `2026-11-07T12:41:37.811576+00:00`; the complete bundle
fingerprint is `a06bcb32586c359d701b622fd5e2f9090d6ff988e51e98c700a859574abf20f5`.
All eight predeclared cases were sealed before either **assessment** canonical read.
Recorded target windows are Store Item 2017-12-04–31 and M5 2016-04-25–05-22.

The ledger still contains twelve events and exactly one assessment read-start /
read-completion pair per dataset. File SHA-256 remains
`fa2af529b50299b50c8d77d67b0ce70f73fab35e4731a5b825dd27a20e4bc204`;
head remains `d5044b81ccc65bbbfa4ec49b0da73c77e433683f9541fc799413ba20cbc1fe9d`.
Saved actuals and final scoring hashes match their original receipts. No failed
assessment event, post-final reselection, changed sealed forecast or changed score
was found. AUD-003 limits historical attestation; Section 6 qualifies earlier QC reads.

## 11. Independent metric reconciliation

Errors use prediction minus actual. Per-series MAE/RMSE/bias and weekly training
MASE/RMSSE were independently recalculated, as were ratio-of-totals WAPE and pooled
RMSE. Macro RMSE is a mean of per-series roots and is not pooled RMSE. No epsilon
was inserted for an undefined denominator. All saved horizon/class/per-series
outputs agree within rtol 1e−9 / atol 1e−10; trial objectives also reconcile.

| Frozen final case | Macro MAE | Pooled RMSE | Pooled WAPE % | Macro MASE | Macro RMSSE | Pooled bias units |
|---|---:|---:|---:|---:|---:|---:|
| Store Item LightGBM | 5.434343 | 7.066976 | 12.258462 | 0.656739 | 0.644564 | −0.291530 |
| Store Item Seasonal Naive | 12.814643 | 16.701995 | 28.906498 | 1.504507 | 1.433304 | 9.178929 |
| Store Item Seasonal Moving Average | 15.807286 | 18.891611 | 35.657121 | 1.820069 | 1.585387 | 15.600500 |
| Store Item Holt-Winters | 10.651093 | 13.299055 | 24.026093 | 1.243444 | 1.126906 | 9.941963 |
| M5 Random Forest | 1.047231 | 2.201063 | 72.582278 | 1.637036 | 0.897646 | −0.052499 |
| M5 Seasonal Naive | 1.243972 | 2.676895 | 86.218139 | 1.810144 | 1.178264 | −0.106180 |
| M5 MA28 | 1.065729 | 2.242953 | 73.864346 | 1.610618 | 0.904875 | −0.056386 |
| M5 TSB | 1.063193 | 2.208269 | 73.688556 | 1.624712 | 0.915955 | −0.027054 |

Every final case has a complete 28-day grid: 14,000 Store Item or 853,720 M5
records, zero duplicate keys and zero fallback/clipped observations. M5 has 812
zero-actual series windows with undefined per-series WAPE/percentage bias; their
other applicable metrics and observations remain included. All final scaled
denominators are defined. Exact unrounded values and every validation case are in
`independent_metrics.json`.

Validation Store Item LGBM mean MAE is 6.308039821970. M5 RF is 1.020066985084,
against MA28 1.033779225039, a 1.326419% reduction. RF-minus-MA28 fold MAEs are
−0.016259711, −0.013763500, −0.011180470, −0.013645279. MA28 wins a majority
of individual series in each validation origin. Final reductions are 57.592712%
for Store Item LGBM versus SN and 1.735707% for M5 RF versus MA28. MA28 and TSB
have better M5 macro MASE; RF is not dominant under every loss.

The independent metric pass took 109.43 seconds, peak OS working set 1,082,220,544
bytes (approximately 1,032 MiB). Data/EDA controls used approximately 764 MiB.
No full 59-million-row M5 table was materialised in memory.

## 12. Reproducibility levels achieved

1. **Level 1 — metric reconciliation: VERIFIED within preserved evidence.** All
   332 validation runs and eight final cases reconcile with independent arithmetic,
   source-bounded validation targets and anchored saved final actuals.
2. **Level 2 — prediction reproduction: PARTIALLY VERIFIED.** Saved validation LGBM
   reproduced all 500 Store Item series at origin 2017-08-13 (14,000 records);
   saved RF reproduced 128 deterministic M5 series at origin 2016-01-03 (3,584
   records). Maximum absolute difference is **zero** for both complete recursive
   H28 paths. No refit occurred. This does not verify every model/origin or final
   replay. Original first-16-row reload probes alone were weaker evidence, often
   spanning only one Store Item or three M5 series.
3. **Level 3 — clean end-to-end experiment reproduction: NOT VERIFIED.** No clean
   machine install or full fitting/search rerun was attempted; final reruns are
   prohibited. All 130 installed distribution pins match the environment freeze,
   and Python 3.14.0 tests pass. The advertised Python 3.11–3.14 matrix is not tested
   here. Absolute roots, OS/library behavior and missing independent backups limit
   portability/recovery. Reproducible source and coherent manifests do not certify
   clean-room prediction identity or every original UUID/timing record.

## 13. Scientific interpretation and uncertainty

LGBM is the leading tested Store Item candidate for these periods and this budget;
the strong relative error reduction is not evidence of universal cross-source
transfer. M5 RF has a small mean-MAE advantage; its practical value depends on
complexity, error scale, affected series and future operational objective. Lower
macro MASE for MA28 demonstrates ranking sensitivity. Demand-class errors are
heterogeneous, so no universal intermittent-demand winner is justified.

No formal dependence-aware significance analysis was performed. Four adjacent
origins and correlated series are not iid repetitions; descriptive fold spread or
series win percentages cannot establish significance. Grouped leaf errors are not
hierarchical aggregate-node errors or official M5 WRMSSE. Two historical retail
datasets and narrow seasonal evaluation periods constrain generalisation. No
inventory savings, causal SNAP/event effect or uncensored demand is established.

## 14. Inventory simulation readiness

The existing outputs can support **future explicitly hypothetical, fixed-policy
scenario comparisons**, after independent audit approval. They do not contain real
on-hand inventory, pipeline orders, lead-time distributions, review intervals,
supplier capacity, minimum order sizes, lost-sales/backorder behavior, service
targets or holding/purchasing/shortage cost records. Do not invent those as facts.

Before implementation, predeclare scenario inputs and units, event order, warmup,
terminal stock, inventory position, same scenario paths across policies, fill-rate
versus cycle-service definitions, and treatment of zero-demand denominators. Calibrate
error buffers only on earlier training/validation errors. Do not choose policies,
costs, buffers or service thresholds to win on the already inspected final window.
Account for H28: lead-time demand beyond available forecast coverage is unsupported
without a separate prospective design. Sales are a potentially censored demand proxy.
No simulator, safety-stock optimisation or Phase 5 model was implemented here.

## 15. Prioritised remediation plan

1. Give this report, frozen code/evidence inventory and new receipts to the mandatory
   independent reviewer. Investigate any critical/high finding before Phase 5.
2. Preserve a separately authorised, hash-verified backup of essential ignored
   evidence. Prepare explicit read-only relocation rules for another machine.
3. Carry the sparse-positive-label, conditional historical-price and local chronology
   caveats into academic claims; no post-holdout retuning or new winner selection.
4. Correct direct-worker locking and normalised-key ingestion only in a separately
   versioned future implementation, preserving the closed assessment and old source
   snapshot. Add regression tests without replacing historical predictions.
5. Update current-status academic documentation after evidence review, retaining
   historical documents as historical. Define Phase 5 scenario contracts only after
   its independent gate; no actual business-savings claim follows from MAE alone.

**Corrections in this audit:** only new audit scripts/tests were corrected during
their development. An initial new concurrency fixture was timing-sensitive under
Windows pointer publication and produced a barrier failure; its final controlled
schedule preserves the ownership challenge and passes. New script formatting
violations were corrected and Ruff rerun. Original implementation, results,
manifests, datasets, hashes and ledger were not edited. Their discovered defects
remain documented; no scientific-result-affecting remediation was attempted.

## 16. Actual commands and outcomes

| Command / check | Actual outcome |
|---|---|
| `python -m pytest -q -p no:cacheprovider --basetemp artifacts/test_runs/internal_audit_20261108_01` | **352 passed, 52.23 s** |
| `python -m pytest reports/internal_audit/models/test_model_audit.py reports/internal_audit/protocol/test_protocol_adversarial.py -q -p no:cacheprovider --basetemp artifacts/test_runs/internal_audit_adversarial_20261108_02` | **23 passed, 5.05 s**; separate new audit suite |
| `python -m ruff check . --no-cache` | Passed after formatting corrections in new audit helpers |
| `python -m pip check` | No broken requirements found |
| `python reports/internal_audit/verify_integrity.py` | All 4,592 inventory files, 89 frozen current/snapshot/checkout files, nine sources, both registries, gates, seals and original ledger passed |
| `python reports/internal_audit/reconcile_saved.py` | All 332 validation and eight saved final cases passed; no original scorer/ledger writer invoked |
| `python reports/internal_audit/replay_validation.py` | 17,584 validation records reproduced exactly; no fit or final replay |
| `python reports/internal_audit/data_eda/verify_data_eda.py` | All EDA series/classes/coverage/group controls passed; full final scan not repeated |
| `python reports/internal_audit/models/verify_samples.py` | Recorded positions/labels/schema/hashes reproduced in 16 validation + two final caches |
| `python -m intelligent_demand forecast-plan`, `forecast-models`; module/runner/final `--help` | Five CLI smoke checks passed; models executed zero |
| Image parse/decode, hash and relative-link checks | 22 scientific assets passed, 24 local HTML file links; browser render not repeated |

Commands use `.venv/Scripts/python.exe`. Audit output-producing scripts use exclusive
creation; do not rerun over existing receipts. Preserve old outputs and choose new
paths/run names for any later authorised review. Logs, including initial new-fixture
failure, remain under ignored `artifacts/experiments/internal_audit_*20261108.log`.

## 17. Explicit gaps and final readiness recommendation

Fresh installation/cross-version execution, exhaustive native optimizer mathematics,
all-model prediction replay, protected final forecast replay, independently trusted
historical timestamps, a separately verified evidence backup, a fresh browser render,
and operational inventory benefits are **NOT VERIFIED**. No critical/high defect was
demonstrated, but these are not silently converted into passes.

**Proceed to Claude's separate independent audit when authorised. Phase 5 remains
CONDITIONAL and must not begin before that audit's gate is satisfied.** A new
critical/high scientific finding would change this recommendation to BLOCKED until
resolved without erasing or repeating the closed final assessment.

Git remains at the reviewed Phase 4 checkpoint. Only this new audit document and
new `reports/internal_audit/` material are added; no automatic commit, push or history
rewrite occurred. No Claude invocation or Phase 5 work was performed.
