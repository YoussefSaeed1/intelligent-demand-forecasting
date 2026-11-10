# Independent Scientific & Technical Audit, Phases 0 to 5

Audit date: 2026-11-10. Auditor: Claude (risk-based, read-only, limited review).
Repository state audited: branch `main`, HEAD `c4e5f6370392fa63ee3d43062ddfb3fce222570d`, plus 59 staged uncommitted files (Phase 5).

**This is a targeted review, not exhaustive verification.** Items verified are marked VERIFIED. Items accepted from Codex documents are marked REPORTED. Items I could not check are in Section 10.

---

## 1. Executive verdict

**Final verdict: CONDITIONAL.** Work may proceed to Phase 6 with the conditions in Section 7.

| Question | Answer |
|---|---|
| Critical findings | 0 |
| High findings | 0 |
| Medium findings | 6 |
| Low findings | 4 |
| Informational | 2 |
| Scientific integrity preserved | Yes, within the reviewed scope. The frozen selection fingerprint, ledger hash and chain, plan and execution freezes all verify. No holdout data was read. |
| Phase 5 arithmetic correct | Yes. Independent replays matched. |
| Phase 5 conclusions supported | Partly. The numbers are right. The interpretation is supported only as hypothetical, exploratory, validation-reused analysis. Several headline statements overstate robustness (F-03, F-04). |
| Can work proceed | Yes, conditionally. |

Main concerns, in order of importance:

1. The headline "Store Item ML saves 5.9% versus MA28" is not robust. It reverses sign in the last validation origin and falls to 1.1% against the stronger seasonal-naive baseline (F-04).
2. The fixed reorder-point comparator is degenerate. Its "lowest cost" result reflects a lower stock level, not a better policy (F-03).
3. The Phase 5 checkpoint was never committed, and documents disagree about its state (F-01).
4. All evidence is on one laptop (F-02).

---

## 2. Audit scope and exclusions

**Done:**

- Read the handoff set, protocols, mathematics, configuration and Phase 5 results documents.
- Read the Phase 5 source: engine, design, plan, inputs, runner, audit. I did not review `report.py` line by line.
- Read selected forecasting source: baselines, metrics, recursive features, global ML.
- Wrote three independent scripts in the scratchpad, using no project code:
  - A scalar replay of 39 sampled cases.
  - An exact-integer re-simulation of three deterministic policies over all 8 base cohorts.
  - A validation forecast metric recomputation.
- Ran Ruff, `pip check` and the full pytest suite once.
- Checked hashes, ledger chain, backup samples and count arithmetic.

**Not done, by instruction:** no final-holdout read, no retraining, no regeneration of forecasts, no rerun of the 544 cases, no source or evidence edits, no commit, no push, no Phase 6/7 work, no Kumo install.

**Side effect to disclose:** the pytest run created `artifacts/test_runs/claude_independent_audit_20261110` (git-ignored scratch). My scripts are in the session scratchpad, not the repository. The only repository change from this audit is this report.

---

## 3. Forecasting audit (Phases 0 to 4)

### 3.1 Data integrity: partial

- VERIFIED by reading the writer: `CanonicalWriter` normalises dates, rejects timezone-aware dates, rejects missing business keys, and enforces unique `(dataset, date, store, item)` keys through a SQLite primary key. It deduplicates nothing and reconciles rows and sales totals on close. Observed Store Item data has 913,000 rows (500 series times 1,826 days).
- VERIFIED: canonical validation windows align exactly with the saved predictions for every fold (one-to-one merge, no missing or extra keys).
- REPORTED: the Codex remediation of the earlier date-key finding. The tests pass, but I did not run adversarial ingestion inputs.

### 3.2 Leakage: PASS within stated limits

- VERIFIED by reading `training_matrix`: features for a label at index *t* use `panel.values[..., t-56:t]`, and lineage validation asserts `max_source_date = target-1`.
- VERIFIED by reading `_predict`: recursion feeds back only its own clipped forecasts, and observed-activity context is frozen at the origin.
- VERIFIED: the Phase 5 history means are origin-bounded. My replay recomputed the 56-day mean from the canonical sales table and matched the saved value for every sampled case. This is independent of the cached arrays Codex used.
- Limit: chronology rests on self-recorded timestamps (F-08).

### 3.3 Models

- VERIFIED: MA28, seasonal naive and their definitions. My replay confirmed that saved MA28 forecasts equal the mean of the last 28 days and that saved seasonal-naive forecasts equal the last 7 days tiled, in all 20 sampled comparisons. Fallback observations in Phase 5 sources: 0.
- VERIFIED by reading: Store Item LightGBM and M5 Random Forest share one feature definition between training and inference (`FeatureEncoder.matrix`).
- NOT VERIFIED: native ARIMA/SARIMA and other discarded models, and the optimiser internals of LightGBM and scikit-learn.

### 3.4 Model selection

- VERIFIED: the selection fingerprint `a71ab187…3fdb` reproduces from `frozen_selection.json` by SHA-256 of sorted compact JSON.
- VERIFIED: the ledger file hash is `fa2af529…c204`. All 12 event self-hashes reproduce and the `previous_sha256` chain is consistent.
- VERIFIED: the selected trials are `store_item_lightgbm_00` and `m5_random_forest_02`.
- Selection optimism is real (F-05): four expanding origins were used for tuning and for ranking, with no nested validation.

### 3.5 Metrics: VERIFIED against permitted evidence

I recomputed the selected models' validation metrics from raw saved predictions and canonical validation sales, without using Codex code.

| Dataset | Leaderboard fold MAE | My recomputed fold MAE | Leaderboard pooled RMSE | Mine |
|---|---|---|---|---|
| Store Item LGBM | 6.4921, 6.2601, 6.1576, 6.3224 | identical to 5 decimals | 8.1785 | 8.179 |
| M5 RF | 0.9987, 1.0195, 1.0346, 1.0275 | identical to 5 decimals | 2.3115 | 2.3115 |

Bias and WAPE also reconcile. MAE, RMSE and WAPE definitions in `metrics.py` are correct. MASE and RMSSE were not independently recomputed (NOT VERIFIED). Final-holdout scores were not recomputed, by instruction.

### 3.6 Sparse-demand limitation: VERIFIED and extended

Validation MAE, M5, sampled-all-zero subgroup versus the rest:

| Origin | Subgroup n | ML MAE | MA28 MAE | Rest: ML | Rest: MA28 |
|---|---|---|---|---|---|
| 1 | 6,878 | 0.4272 | 0.4178 | 1.1652 | 1.1889 |
| 2 | 6,878 | 0.4574 | 0.4397 | 1.1832 | 1.2062 |
| 3 | 6,878 | 0.4725 | 0.4577 | 1.1983 | 1.2171 |
| 4 | 6,878 | 0.4758 | 0.4632 | 1.1882 | 1.2095 |

The origin-specific masks (7,225, 7,179, 7,166 and 6,976 series) show the same pattern. The documented claim holds.

Implications:

- The RF's overall MAE advantage over MA28 (about 1.3%) comes entirely from the other 77% of series.
- It is a sampling effect: six labels per series gives sparse positives.
- It is descriptive, not causal, and no post-holdout re-selection should be done.

New observation from Phase 5 (F-06): sparse series are not the sole reason M5 ML loses on cost. Outside the subgroup, ML is costlier than MA28 in 3 of 4 origins.

---

## 4. Inventory simulation audit (Phase 5)

### 4.1 Mathematics: PASS

- VERIFIED: I wrote a separate simulator from the protocol text and compared it with saved results. All 39 cases matched, with zero failures:
  - Four policies on Store Item and M5.
  - One intermittent series, one zero-demand-in-window series, and one fractional-mean series.
  - Seven sensitivity scenarios: variability high and low, weekly review, long and short lead, terminal charge, zero initial stock, plus penalty, buffer, initial-cover and ordering-cost variants.
  - Daily events on the base and retained series matched to 0.0 absolute difference.
- VERIFIED: the timing convention. An end-of-day order on day *t* arrives on day *t+L+1*. The protection period is *L+R*. The review cutoff is `day + P < 28`. Reading the engine, the tests and my replay all agree.
- VERIFIED: **floating-point ceiling risk is negligible.** I re-simulated MA28, seasonal naive and fixed ROP for all 8 base cohorts in exact integer arithmetic (everything scaled by 56). Saved results differ in 0 to 3 of 500 Store Item series and 9 to 18 of 30,490 M5 series. The mean cost deviation is at most 0.06 NCU per series on Store Item and 0.003 on M5. The affected cases are mostly the initial-stock `ceil(7·mean)` boundary, which is common to all policies. This is far below the +1.897 M5 headline difference.

### 4.2 Information availability: PASS

- VERIFIED by code: `order_quantity` receives position, mean, window and date only. No future actuals enter any decision. A poison-the-future test exists.
- VERIFIED: forecasts are the saved fixed-origin H28 validation forecasts. The origin equals the validation start minus one day for all 8 cohorts, and every cohort has exactly 28 horizon steps with no fallback rows.
- VERIFIED: the common cutoff means every ordering decision has full protection coverage.
- VERIFIED: the 56-day mean uses data up to the origin only. Initial stock and buffer derive from it. The M5 pattern labels and the retrospective sparse mask are used for reporting only. Neither enters any policy.
- Not leakage but a handicap: forecast policies cannot use demand observed after the origin except through inventory position. This applies equally to all policies.

### 4.3 Policy fairness: PASS with one caveat

All policies share demand paths, initial stock, lead time, costs, review period, horizon and the lost-sales convention. VERIFIED by the audit's equality checks and my replay. Caveats:

- Store Item MA28 forecasts come from the Phase 3 registry while the others come from Phase 4. The forecasts are deterministic and I verified their definitions, so this has no effect.
- The fixed ROP comparator is degenerate (F-03).

### 4.4 Cost and service accounting: PASS with documented limits

- VERIFIED: holding is charged on closing stock, shortage on unmet units, fixed order cost per positive order, and variable order cost at placement. Terminal charge applies to final stock plus pipeline.
- VERIFIED: base terminal pipeline is zero in every sampled case. The cutoff ensures orders arrive within the episode, so base costs are not distorted by unreceived orders.
- Terminal stock is not salvaged (F-09). This is disclosed.

### 4.5 Independent numerical verification

- The Codex scalar reference shares the input adapter with production. Its state machine is independently written, but it was amended after a mismatch (F-11).
- My replay used neither the adapter nor any project import. It reloaded canonical sales, forecasts and fold definitions directly, so it independently covers that adapter risk as well for the sampled series.
- Count arithmetic VERIFIED: 544 cases, 8,429,280 series episodes, 13,969,536 event rows and 3,264 scalar replays all follow from the design, and the saved status files sum to them. All 544 cases show `completed` with one attempt and zero fallback observations.
- Not independently recomputed: the ML policy cost over the full population (only sampled series), and the 3,264 Codex replays themselves.

### 4.6 Scientific results

**Headline numbers VERIFIED** from raw per-series outputs, including one case recomputed straight from Parquet:

| Dataset | ML | MA28 | ML minus MA28 | ML minus seasonal naive |
|---|---|---|---|---|
| Store Item | 6,038.44 | 6,414.59 | −376.14 (−5.86%) | −67.27 (−1.10%) |
| M5 | 223.82 | 221.92 | +1.90 (+0.85%) | −11.01 (−4.69%) |

Scenario counts VERIFIED: ML beats MA28 in 17/17 Store Item and 3/17 M5 scenarios. The M5 scenarios are `lead_short`, `holding_low` and `penalty_high`.

Per-origin ML minus MA28:

| Dataset | Origin 1 | Origin 2 | Origin 3 | Origin 4 |
|---|---|---|---|---|
| Store Item | −915.8 | −598.1 | −375.9 | **+385.2** |
| M5 | +0.40 | +2.35 | +1.66 | +3.18 |

Assessment:

- Costs are normalised consistently as NCU per series per episode. The two datasets are not comparable (6,038 versus 224).
- Comparisons are paired by series. Populations are identical across policies.
- Selection and reuse bias is disclosed in the documents, but its direction and size are not discussed (F-05).
- The service-cost trade-off is reported accurately. Store Item fill rates are nearly identical for ML, MA28 and seasonal naive (98.383%). Fixed ROP fills 97.68% and is cheapest in 14 of 17 scenarios on both datasets.
- No document claims realised savings. That is correct and must stay.

---

## 5. Reproducibility and preservation

| Item | Status |
|---|---|
| Phase 5 Git checkpoint | **NOT completed.** HEAD is still the Phase 4 follow-up commit. No Phase 5 commit exists. 59 files are staged, not committed. The "post-commit receipt" file does not exist. |
| Document consistency | Contradictory. The handoff describes an authorised checkpoint and commit message. The completion checklist says changes are "unstaged/uncommitted". They are staged. |
| Frozen plan hash `63efc59e…` | VERIFIED, self-hash reproduces. |
| Execution hash `b55ba4a0…` | Present. Design files and inventory source files are unchanged since freeze (VERIFIED). |
| Phase 5 local backup | **Completed as a same-device copy.** The manifest records 2,593 files, 1,611,791,130 bytes, status passed, zero missing or mismatched. 12 of 12 randomly sampled files matched their recorded hashes. The directory holds 2,595 files, consistent with the two declared sidecars. I did not rehash the full 1.6 GB. |
| Evidence inventory | 2,252 files. 12 of 12 sampled entries rehashed correctly. 2,182 are under `artifacts/inventory/phase5`, which is git-ignored. |
| Tests and lint | VERIFIED by me: 439 passed in 55 s, Ruff clean, `pip check` clean. |
| Seeds and scenarios | Seed 42 and the 17-scenario matrix are in the frozen config and plan. The simulation itself is deterministic. |
| Environment | Version snapshot from a Windows, Python 3.14 environment. The file itself says it is not a portable lock. Clean-room reproduction was never tested (F-10). |

**Local-only evidence (not in Git):** all Phase 5 case outputs, per-series and event Parquet, detailed audit summaries (`phase5_summary.json` is ignored), figures, logs, and the Phase 3 and 4 models, predictions and caches that the simulation reads. A reviewer with only the repository cannot reproduce Phase 5.

**The backups are on the same laptop.** They do not protect against drive failure, theft or loss. No off-device copy exists.

**Could a future reviewer reproduce the conclusions from preserved material?** Yes, on this machine or from the local backup with the same path mapping, the Phase 5 results can be re-verified without any training or holdout access. From a clean machine, no.

---

## 6. Findings

| ID | Severity | Phase | Status | Blocks next phase |
|---|---|---|---|---|
| F-01 | MEDIUM | 5 | Verified defect (process) | Recommended before Phase 6 |
| F-02 | MEDIUM | 0 to 5 | Verified risk | Recommended before submission |
| F-03 | MEDIUM | 5 | Verified | No, but wording constraint |
| F-04 | MEDIUM | 5 | Verified | No, but wording constraint |
| F-05 | MEDIUM | 4, 5 | Documented limitation, magnitude unquantified | No, but wording constraint |
| F-06 | MEDIUM | 3 to 5 | Documented limitation, extended | No |
| F-07 | LOW | 5 | Verified | No |
| F-08 | LOW | 4 | Documented limitation | No |
| F-09 | LOW | 5 | Documented limitation | No |
| F-10 | LOW | 0 to 5 | Documented limitation | No |
| F-11 | INFO | 5 | Resolved by my checks | No |
| F-12 | INFO | 5 | Documented | No |

### F-01 MEDIUM: Phase 5 checkpoint not committed; documents contradict each other

- **Evidence:** `git log` shows no Phase 5 commit and HEAD is `c4e5f63`. `git status` shows 53 added and 6 modified staged files. `artifacts/experiments/phase5_checkpoint_postcommit_receipt.json` does not exist. `docs/PHASE5_CLAUDE_AUDIT_HANDOFF.md` describes an authorised checkpoint, and `PHASE5_COMPLETION_CHECKLIST.md` says changes are unstaged.
- **Impact:** the handoff reads as if the checkpoint is done. A disk loss or an accidental `git reset` before the commit would lose the staged state. Frozen bytes rely on `.gitattributes` EOL rules that have not yet been exercised by a commit and fresh checkout.
- **Remediation:** the owner decides whether to commit. After committing, correct the two documents to say the same thing. Consider a fresh-clone check that the frozen text files keep their hashes.

### F-02 MEDIUM: evidence has no off-device copy (inherits Codex AUD-005)

- **Evidence:** the backup receipt itself says "LOCAL BACKUP ON THE SAME DEVICE". `.gitignore` excludes `artifacts/**`, `*.parquet`, and `reports/figures/**`.
- **Impact:** about 5.2 GB of Phase 4 evidence and 1.6 GB of Phase 5 evidence, the only copy of the frozen models and predictions, share a failure domain with the working copy.
- **Remediation:** the owner should place a verified copy off-device (external drive or cloud) before submission. I did not do this.

### F-03 MEDIUM: fixed reorder-point comparator is degenerate

- **Evidence:** the policy is `s = mu·(L+R) + 3·mu = 11·mu` with `Q = ceil(mu·R)` (`engine.py:68-70`). Saved base results show the policy orders on all 20 allowed review days in about 100% of Store Item series (mean 20.0 orders). Mean inventory position is about 7.6 times the daily mean, which is below the reorder point of 11, so the trigger never switches off. On M5, about 10% of series order every day, and the rest order roughly half the days.
- **Impact:** the rule behaves as "replenish one day of demand every day". It holds roughly the 7-day initial cover, while the forecast policies build to an order-up-to level of about 11 days. Its low cost (3,276 versus 6,039 on Store Item) mostly reflects this lower stock target, bought with lower fill (97.68% versus 98.38%). It is not evidence that a simple rule beats forecasting, and not a tuned comparator.
- **Remediation:** do not describe fixed ROP as the "best" or "winning" policy. Describe it as a low-stock, lower-service comparator. Optionally, in later work only, add a properly parameterised (s, S) baseline, chosen on validation.

### F-04 MEDIUM: the headline ML result is less robust than its presentation

- **Evidence (all recomputed):**
  - Store Item ML minus MA28 changes sign at origin 4 (+385.2). In that origin 473 of 500 series are costlier under ML.
  - ML's MAE is better than MA28's at all four origins (6.32 versus 9.02 at origin 4), yet its cost is worse. Cost depends on forecast level against the order-up-to target, not just MAE.
  - Against seasonal naive (the stronger Store Item baseline), the base difference is −67.27 (−1.10%) and ML loses at origin 3 (+112.8).
  - The "17/17 scenarios" count uses the same four origins and the same forecasts in every scenario. It is not 17 independent confirmations.
  - M5 ML has better MAE than MA28 but is costlier in 14 of 17 scenarios.
- **Impact:** a reader could take "−5.9%" or "17/17" as strong evidence of ML value. The documents do say scenario counts are not probabilities and that there is no significance claim, but the narrative headlines still lead with the MA28 comparison.
- **Remediation:** in the dissertation and dashboard, always show the per-origin results and the seasonal-naive comparison beside the MA28 comparison. Do not use the 17/17 count as a robustness argument. Do not call the result a saving.

### F-05 MEDIUM: selection optimism from reusing validation origins

- **Evidence:** `PHASE5_LIMITATIONS.md` states the four windows informed Phase 4 selection. MA28 and seasonal naive have no tuned parameters. The ML models had hyperparameters and trial identity chosen on these windows.
- **Impact:** ML is systematically favoured in Phase 5. The size is unknown because no nested validation exists. It cannot be measured now without a fresh window, and the holdout has been spent.
- **Remediation:** state the direction of the bias explicitly. The M5 result (ML not cheaper despite this advantage) is the more informative one.

### F-06 MEDIUM (documented limitation): M5 sparse-demand weakness

- **Evidence:** Section 3.6, plus Phase 5 cost: in the 6,878-series subgroup ML is costlier than MA28 by +2.12, +2.72, +2.59 and +2.25 NCU at the four origins. Outside it the difference is −0.11, +2.25, +1.39 and +3.44.
- **Impact:** the M5 model does not generalise to intermittent demand better than a 28-day mean, and the sparse subgroup does not fully explain this. Any statement that RF suits intermittent demand is unsupported.
- **Remediation:** report as a limitation. Do not re-select models.

### F-07 LOW: mean cost is volume-weighted, with many ties

- **Evidence:** M5 median paired ML minus MA28 difference is 0.0 at every origin, with 7,450 to 7,650 exactly tied series per origin.
- **Impact:** the mean is driven by a small number of high-volume series. There is no scale-normalised view such as cost per unit demand.
- **Remediation:** add median, tie counts and a per-unit-demand view to the written results. The report data already holds some of this.

### F-08 LOW: chronology is self-recorded; freeze recorded a dirty tree

- **Evidence:** `frozen_selection.json` has `git_dirty: true` at revision `6e1a407` (the Phase 3 checkpoint). The ledger shows freeze at 12:41:51Z and first canonical read at 12:44:48Z on 2026-11-07. All four final assessments finished within about 30 seconds. The ledger is internally consistent, but a hash chain proves order only if the clock and the writer are trusted.
- **Impact:** this is not independent proof that nothing was tuned after the holdout was seen. Mitigated by the 89-file code snapshot hashes and by one logged read per dataset.
- **Remediation:** none required. State it as a limitation, as the documents already do.

### F-09 LOW: finite-episode artefacts

- **Evidence:** the empty initial pipeline with 7-day initial cover makes long-lead scenarios dominated by early stockouts (`lead_long` raises ML mean cost by 7,675 on Store Item). Terminal stock is not salvaged. Orders stop 8 days before the end.
- **Impact:** absolute costs and some scenario rankings are artefacts of the episode design. The documents disclose this.
- **Remediation:** none beyond keeping the caveat next to any scenario result.

### F-10 LOW: environment not portable; clean-room reproduction untested

- **Evidence:** the freeze file says it is a snapshot, not a portable lock. Python is 3.14 on Windows. `pyproject.toml` allows 3.11 to below 3.15.
- **Impact:** a different machine may not reproduce bit-identical forecasts. Phase 5 itself is deterministic given the saved inputs.
- **Remediation:** note in the dissertation that reproduction is of saved artefacts, not retraining.

### F-11 INFORMATIONAL: scalar reference partly shared and amended

- **Evidence:** `audit.py` says "same approved input adapter". The reference was changed after the first replay disagreed at a fractional ceiling boundary.
- **Resolution:** my independent replay and the exact-integer check (Section 4.1) show production results are right and the amendment was benign.

### F-12 INFORMATIONAL: variability stress changes more than variance

- Stressed demand is `max(0, mu + a·(sales − mu))` and forecasts are not regenerated. Forecast MAE in stressed cases is measured against stressed demand. This is disclosed, and the scenarios should not be read as a variance intervention.

---

## 7. Remediation priorities

Before Phase 6 (conditions of the CONDITIONAL verdict):

1. **Owner decision on the checkpoint (F-01).** Commit or deliberately defer, then make the handoff and checklist agree.
2. **Wording rules for all later outputs (F-03, F-04, F-05).** Show per-origin ML, MA28 and seasonal-naive results together. Never present the 17/17 count as robustness. Never call simulated cost differences savings. Describe fixed ROP as a low-stock comparator.

Before submission:

3. **Off-device copy of both backups (F-02).**
4. **Add the median, ties and per-unit-demand view (F-07).**

Optional:

5. A properly tuned (s, S) comparator, only as clearly labelled follow-up work (F-03).

---

## 8. Phase 6/7 readiness

| Area | Readiness |
|---|---|
| Phase 5 numbers for dashboard export | Ready. Arithmetic verified, and exports can come from the saved summaries. |
| Phase 5 narrative | Ready only under the wording rules above. |
| Forecasting results | Ready as reported, with F-05, F-06 and F-08 stated. |
| Preservation | Not ready for submission until F-01 and F-02 are resolved. |
| Scientific changes | None required, and none should be made. |

Phase 6 (BI and academic submission) can start now on the saved, verified numbers. This review does not certify anything beyond its scope.

---

## 9. NVIDIA Kumo feasibility note (not an experiment)

- **NOT VERIFIED:** I could not confirm from project information what Kumo is, who makes it, or what it supports. I did not search for it, install it or run it. Capabilities, data requirements, licensing and hardware needs are all NOT VERIFIED.
- **Fit to this project:** the problem is a daily demand panel with 28-day recursive forecasts and four expanding validation origins. A new model could in principle be run on the same validation windows.
- **Why it would not help scientifically:** the final holdout has been consumed once. Any new model could only be compared on the four validation windows that already informed selection. That comparison would carry the same optimism as F-05 and could not support a clean claim. It would also reopen frozen conclusions without a clean evaluation set.
- **Recommendation:** do not add it before submission. If wanted later, treat it as a clearly labelled side experiment in a separate output directory, with a new access receipt, and no change to the frozen results.

---

## 10. Explicitly NOT VERIFIED

- Final-holdout scores and any recomputation from final actuals (not opened, by instruction).
- MASE and RMSSE recomputation.
- Full-population ML policy cost, and the Codex 3,264 scalar replays, beyond my 39 sampled replays and the integer re-simulation of three deterministic policies.
- Every line of `report.py`, the HTML report, and all figures. Browser rendering is also unverified.
- Statistical and discarded models (ARIMA family, Holt-Winters, TSB), and native optimiser internals.
- Raw data acquisition and canonical data quality beyond the writer's logic.
- Full rehash of the 1.6 GB Phase 5 backup and the 5.2 GB Phase 4 backup (spot checks only).
- Independent proof of historical chronology.
- Clean-machine reproduction, and the behaviour of `.gitattributes` after a real commit and fresh checkout.
- Why Store Item ML loses at origin 4 despite better MAE (not investigated).
- Kumo identity and capabilities.
