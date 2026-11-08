# Phase 4 optimisation and final-assessment contract

This contract is declared before any real tuning run. The Phase 3 checkpoint is
`6e1a407de0b676e858ffec43bab1fae8d51dae1d`; its source data and saved experiments
remain intact. `configs/phase4.yaml` and the exclusive, hashed
`artifacts/experiments/phase4/plan.json` define the executable contract. The original
Phase 2 protocol Markdown and split manifest are not edited.

## Candidates and fixed budget

| Dataset | Family | Configurations, including initial anchor | Rationale |
|---|---|---:|---|
| Store Item | LightGBM | 6 | Phase 3 MAE 6.308040; strongest current validation candidate |
| Store Item | Random Forest | 3 | Relevant nonlinear challenger, MAE 6.885316 |
| Store Item | Additive damped Holt-Winters | 3 | Strong statistical reference, MAE 7.701650 |
| M5 | Random Forest, price-free | 4 | Test the conditional Phase 3 leader with safe availability |
| M5 | TSB | 4 | Intermittent-demand challenger; retain observed training zeros |
| M5 | LightGBM, price-free | 3 | Limited global boosting comparison across sparse/hierarchy groups |

There are **23 tuning configurations**, each independently refitted at all four
approved origins. Four additional unchanged reference cases are Store Item Seasonal
Naive/Seasonal Moving Average and M5 Seasonal Naive/MA28, also on all four origins:
27 cases / 108 fold runs. Smoke runs are the first origin of each initial family
anchor, not extra trials or a different selection population; valid results are reused.
Anchors fix initial configurations and measure the new availability contract; the
remaining configurations are seeded random samples without replacement from the
explicit discrete Cartesian spaces. Seed 42, dataset/family/axis ordering and all
realised parameter sets are frozen before search. No adaptive expansion, Optuna,
early stopping, pruning or validation-based sample selection is used.

The spaces include RF tree count/depth/minimum leaf/features/split; LightGBM leaves,
depth, learning rate, rounds, minimum leaf, feature/bagging fraction and L1/L2;
Holt-Winters alpha/beta/gamma/damping; and TSB size/occurrence smoothing. Exact values
are in the YAML. Bagging frequency is one only when bagging fraction is below one;
otherwise zero. RF retains the Phase 3 512-leaf cap and bootstrap fraction 0.7.
All configurations are validated before trial creation. Library parameter semantics:
[RF documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)
and [LightGBM documentation](https://lightgbm.readthedocs.io/en/v4.6.0/Parameters.html).
Installed versions remain scikit-learn 1.9.1 and LightGBM 4.6.0; no upgrade is requested.

ARIMA/SARIMA are not searched: Phase 3's fixed-order subset comparisons did not beat
strong matched simple baselines and extending them across 30,490 series is costly.
Other intermittent methods remain Phase 3 references rather than duplicating TSB's
bounded smoothing search. No ensemble or class-based model switching is introduced.

## Objective and populations

The primary objective is the arithmetic mean of four fold macro per-series MAEs,
separately per dataset. Every series has equal weight, with no horizon or volume
reweighting. All trials use exactly the original four expanding origins, every
500/30,490 series, and all 28 consecutive target days. Secondary metrics retain
pooled RMSE/WAPE/signed bias, weekly training-only MASE/RMSSE with undefined counts,
origin/horizon/class/hierarchy breakdowns, native/fallback coverage and resources.
Pooled metrics across origins use summed errors/quantities, not averaged roots/ratios.
No cross-dataset raw-unit ranking or official M5 WRMSSE is claimed.

Select the minimum primary score across complete eligible tuning/reference cases.
Scores within 1e-12 use the predeclared simplicity order and then configuration ID.
There is no post-score business-value threshold or retrospective objective change.
At least two complete tuning configurations per declared family and all reference
cases are required before freezing. Every allocated trial is accounted for; failed
or interrupted cases never enter rankings, and partial folds cannot form a score.
M5's small Phase 3 RF gain is not presumed significant: compare paired origin means,
series-level win rates, classes and resource costs. A simple baseline may win.

## Training and covariate availability

Sampling remains equal per series and time strata, seed 42, label positions 56..T−1
only, independent of observed quantities and validation outcomes. Store Item uses
150,000 labels (300 per series); M5 uses 182,940 (six per series from the 183,000 cap).
No sample-size search is included: this isolates hyperparameters and bounds memory.
All series, initial classes and zeros remain eligible; all available prior history
may construct features. Sparse individual M5 sampling remains a material limitation.

All Phase 4 ML candidates and final refits are **price-free**. M5 has 30 features,
Store Item 27. Future prices, events and SNAP remain excluded. Phase 3 price-enabled
M5 values are conditional historical research references and are not eligible final
models. No claim of verified historical price publication latency is made.
Date features are deterministic; ID mappings are target-free within the fixed
published universe. Lag/rolling state uses own clipped prior predictions throughout
the 28-day recursion. Observed occurrence/intermittency context is frozen at the true
origin; forecast point estimates never become observed demand occurrences.

## Resource and stopping contract

One expensive worker at a time, CPU only, at most four threads, 2,048 MiB worker RSS,
at least 512 MiB available memory before launch and 10 GiB free disk. Each fold has
1,800 seconds and at most two attempts. Active sequential search-worker wall time is
capped at 10,800 seconds (three hours); downtime while safely stopped does not consume
compute budget. This is tighter than Phase 2's proposed family limits. Phase 3 measured
about 104 seconds/M5 RF fold and 59 seconds/LightGBM fold, plus inexpensive Store Item
and batched statistical runs; larger trees and cold caches justify margin. These are
pipeline costs, not isolated estimator fit times. No hard cap is silently enlarged.

Source/panel/feature caches have source/origin/seed/schema/code keys and checksums.
Completed outputs are reused only after validation; attempts, failure reasons, resource
logs and original completed results remain inspectable. Hard-kill recovery requires
proof that the owning process has stopped. A resource failure stops the affected job;
an equivalent engineering correction and one remaining declared attempt may resume it.
Repeated infeasibility, insufficient complete cases, source mismatch or leakage blocks
dependent selection. No partial leaderboard may be presented as the completed search.

## Final freeze and one-time assessment

Phase 4A freezes the search contract before training; Phase 4B must pass independent
persisted-prediction reconciliation and tests before any final-window capability exists.
Then exclusively publish the exact selected models, parameters, feature availability,
sampling/refit procedure, metrics, fallback policy, source/code fingerprints and final
comparator list in `frozen_selection.json`, with its content hash and pre-access UTC
timestamp. Copy the exact scientific code/config bytes into a checksummed local snapshot.
This supplies immutable provenance without needing a Git freeze commit. No final Phase 4
commit is authorised. Ordinary readers continue rejecting final target reads.

Final predeclared comparator policy: Store Item Seasonal Naive, Seasonal Moving Average
and the best Holt-Winters candidate; M5 Seasonal Naive, MA28, the best TSB and best
price-free RF. Include each selected model and remove exact duplicate trial IDs. Exact
cases, not an outcome-dependent choice after testing, are listed before access.

Refit through Store Item 2017-12-03 and M5 2016-04-24 with the same sample budgets,
seed, features, eligibility and clipping. Produce exactly 28 forecasts per series for
every selected model/comparator. Seal **both datasets' entire forecast/model bundle**
with hashes before unlocking either dataset's targets. Do not regenerate forecasts
after a target access event. Historical training scales are persisted before scoring.

A dedicated capability validates the unchanged search/selection/final bundle and
records a hash-chained, fsynced, append-only access event before each dataset's only
canonical holdout scan. Persist scored actuals separately for transparent metric
reconciliation/reporting. Later reads of that immutable assessment snapshot are logged
as audit/report access, not new selection assessments. Never erase or reset access
history. A post-access technical failure is preserved and cannot trigger refitting,
new predictions, model replacement or tuning. Underperformance is reported honestly.

## Milestones and preserved limitations

4A: configuration/boundary/sampling/availability tests, Ruff, pip check, frozen protocol,
source hashes and plan hash. 4B: every trial accounted for, complete matched four-fold
scores independently recomputed, safe feature inputs and invalid-trial exclusion.
4C: pre-access freeze and immutable predictions, once-only access ledger, complete
keys, training-only denominators, independent final metric reconciliation. 4D: academic
report, figures, reproducibility commands, limitations and independent-audit package.

Validation tuning estimates are search-selected; only the frozen final assessment is
held out. Four adjacent windows have limited seasonal coverage and do not justify iid
significance tests. Observed sales can be stock constrained. Accuracy is not inventory
savings, subset experiments do not estimate populations, and direct cross-dataset
transfer is unsupported. No Phase 5, deployment, dashboard or Claude audit starts here.
The independent Claude review remains mandatory after Phase 4 and before Phase 5.
