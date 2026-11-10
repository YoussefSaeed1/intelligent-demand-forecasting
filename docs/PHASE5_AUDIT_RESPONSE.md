# Phase 5 response to the independent Claude audit

Prepared after the independent audit dated 2026-11-10 ([report](CLAUDE_INDEPENDENT_AUDIT_PHASES_0_5.md)).
Audit verdict: **CONDITIONAL**. Findings: 0 Critical, 0 High, 6 Medium, 4 Low, 2 Informational.

This response changes reporting, documentation and the Git checkpoint only. No simulation, forecast,
model, ledger, frozen manifest, plan, execution contract or scientific result was changed, rerun or
regenerated. Original numeric sections of every Phase 5 document and of the offline HTML report are
retained verbatim; corrections are added in labelled sections that govern interpretation. Pre-edit
copies of every edited file are preserved in `reports/inventory/original_documents/phase5_pre_audit/`
and declared in `reports/preservation/PHASE5_AUDIT_REMEDIATION_OVERLAY.json`.

## 1. Audit-corrected headline comparison

All values are hypothetical simulated costs in normalised cost units (NCU) per series per 28-day
episode, never realised savings. They were re-aggregated from the persisted per-series outputs of all
544 completed cases and reconciled with the saved audit summary by
`reports/inventory/post_audit_reconcile.py`
(output: `reports/inventory/post_audit_reconciliation.json`, 4,896 metric comparisons, no disagreement).

**Store Item: base mean cost, NCU per series per 28-day episode, by validation origin**

| Origin | Selected ML | MA28 | Seasonal Naive | Fixed ROP | ML - MA28 | ML - Seasonal Naive |
|---|---|---|---|---|---|---|
| 1 | 6,518.59 | 7,434.37 | 6,718.90 | 3,762.24 | -915.78 | -200.30 |
| 2 | 6,047.87 | 6,645.96 | 6,206.06 | 3,583.32 | -598.09 | -158.19 |
| 3 | 5,623.94 | 5,999.86 | 5,511.11 | 2,993.98 | -375.92 | +112.83 |
| 4 | 5,963.37 | 5,578.16 | 5,986.80 | 2,766.21 | +385.21 | -23.43 |
| Pooled, all four | 6,038.44 | 6,414.59 | 6,105.72 | 3,276.44 | -376.14 (-5.86%) | -67.27 (-1.10%) |

**M5: base mean cost, NCU per series per 28-day episode, by validation origin**

| Origin | Selected ML | MA28 | Seasonal Naive | Fixed ROP | ML - MA28 | ML - Seasonal Naive |
|---|---|---|---|---|---|---|
| 1 | 218.86 | 218.46 | 235.62 | 201.41 | +0.40 | -16.76 |
| 2 | 218.37 | 216.01 | 227.84 | 204.06 | +2.35 | -9.47 |
| 3 | 233.27 | 231.61 | 239.14 | 209.93 | +1.66 | -5.87 |
| 4 | 224.79 | 221.61 | 236.74 | 205.14 | +3.18 | -11.95 |
| Pooled, all four | 223.82 | 221.92 | 234.83 | 205.14 | +1.90 (+0.85%) | -11.01 (-4.69%) |

**Store Item: base cost, service and stock (pooled over the four origins)**

| Policy | Mean cost | Cost per demanded unit | Pooled fill % | Average on-hand | Stockout days / episode |
|---|---|---|---|---|---|
| Selected ML | 6,038.44 | 3.5344 | 98.38 | 205.08 | 0.972 |
| MA28 | 6,414.59 | 3.7546 | 98.38 | 218.52 | 0.971 |
| Seasonal Naive | 6,105.72 | 3.5738 | 98.38 | 207.48 | 0.972 |
| Fixed ROP | 3,276.44 | 1.9178 | 97.68 | 102.12 | 2.266 |

**M5: base cost, service and stock (pooled over the four origins)**

| Policy | Mean cost | Cost per demanded unit | Pooled fill % | Average on-hand | Stockout days / episode |
|---|---|---|---|---|---|
| Selected ML | 223.82 | 5.8971 | 83.92 | 5.54 | 2.149 |
| MA28 | 221.92 | 5.8471 | 83.40 | 5.40 | 2.205 |
| Seasonal Naive | 234.83 | 6.1872 | 82.75 | 5.81 | 2.318 |
| Fixed ROP | 205.14 | 5.4048 | 79.56 | 4.20 | 2.639 |

**Sensitivity scenarios share the same four origins, forecasts and populations**

| Dataset | Reference | Origins where ML is cheaper (base) | Scenarios ML cheaper, pooled (of 17) | Scenarios ML cheaper by origin 1 / 2 / 3 / 4 (of 17) | Scenario-origin cells ML cheaper |
|---|---|---|---|---|---|
| Store Item | MA28 | 3 of 4 | 17 | 17 / 17 / 17 / 1 | 52 of 68 |
| Store Item | Seasonal Naive | 3 of 4 | 16 | 16 / 17 / 1 / 15 | 49 of 68 |
| M5 | MA28 | 0 of 4 | 3 | 6 / 2 / 3 / 2 | 13 of 68 |
| M5 | Seasonal Naive | 4 of 4 | 17 | 17 / 17 / 14 / 17 | 65 of 68 |

**Fixed reorder point behaviour (base scenario, series with positive history mean)**

| Dataset | Series-episodes ordering at every eligible review | Mean orders per episode (of 20) | Mean inventory position (mean days of demand; trigger = 11) | Scenarios where Fixed ROP is cheapest (of 17) | Scenarios where its fill is below ML (of 17) |
|---|---|---|---|---|---|
| Store Item | 99.9% | 20.00 | 7.33 | 14 | 15 |
| M5 | 11.0% | 10.49 | 11.34 | 14 | 17 |

**M5 retrospective sparse-sampling group (six all-zero sampled training labels; report-only)**

| Origin | Sparse-group series | MAE in group: ML / MA28 | MAE elsewhere: ML / MA28 | Cost ML - MA28 in group | Cost ML - MA28 elsewhere |
|---|---|---|---|---|---|
| 1 | 6,878 | 0.4272 / 0.4178 | 1.1651 / 1.1889 | +2.12 | -0.11 |
| 2 | 6,878 | 0.4574 / 0.4397 | 1.1832 / 1.2062 | +2.72 | +2.25 |
| 3 | 6,878 | 0.4725 / 0.4577 | 1.1983 / 1.2170 | +2.59 | +1.39 |
| 4 | 6,878 | 0.4758 / 0.4632 | 1.1882 / 1.2095 | +2.25 | +3.44 |

## 2. Reporting rules (binding for Phase 6 and the dissertation)

1. Selected ML, MA28 and Seasonal Naive are always reported together, with differences by validation origin as well as pooled.
2. The 17 sensitivity scenarios reuse the same four origins, fixed-origin forecasts and populations. They are parameter sensitivity checks, not independent confirmations. For Store Item ML against MA28 the scenario count is 17 of 17, yet the result is cheaper in 52 of 68 scenario-origin cells, because origin 4 reverses almost every scenario.
3. Store Item ML against MA28 reverses sign at the last origin (+385.21 NCU). ML is cheaper at 3 of 4 origins.
4. Store Item ML against Seasonal Naive has only a small average advantage (-67.27 NCU, -1.10%), and ML is costlier at origin 3 (+112.83).
5. M5 ML is costlier than MA28 at all four origins (+1.90 NCU, +0.85%) while giving higher pooled fill (+0.52 points). It is cheaper than Seasonal Naive at all four origins (-11.01 NCU).
6. Fixed Reorder Point is a low-stock, low-service comparator, not a better policy. On Store Item it orders at essentially every review (99.9% of series-episodes; 20.00 of 20 eligible reviews), so its inventory position (7.3 mean days) never reaches the 11-day trigger. On M5 it behaves as a threshold rule: it orders at 10.5 of 20 reviews and only 11.0% of series order at every review. Its lower cost reflects lower stock and lower fill (fill below ML in 15 of 17 Store Item and 17 of 17 M5 scenarios).
7. Selection optimism is asymmetric. Selected ML was chosen from 12 (Store Item) and 11 (M5) tuning configurations ranked on the same four validation origins used here. MA28 and Seasonal Naive are fixed rules with no tuned parameters. Store Item retained its initial LightGBM configuration, so its optimism comes from selection among configurations rather than from a tuning gain. The size of the bias is not quantifiable: the final holdout was consumed once and no fresh window exists. Any bias favours ML.
8. M5 sparse sampling: the Random Forest's validation MAE advantage over MA28 (1.33% on average) comes from series outside the 6,878-series retrospective group whose six sampled training labels are all zero. In that group MA28 has the lower MAE at all four origins, and ML costs more than MA28 at all four origins. Outside the group ML also costs more than MA28 at 3 of 4 origins, so sparse series do not fully explain the M5 result. The group is derived from final-training labels and is report-only.
9. All costs are hypothetical normalised units (NCU) from a validation-reused simulation. They are not realised savings and must never be reported as savings.

## 3. Disposition of each audit finding

| ID | Severity | Finding | Disposition | Status |
|---|---|---|---|---|
| F-01 | Medium | Checkpoint not committed; documents contradict each other | README, roadmap, academic requirements, completion checklist, handoff and progress note corrected. Reviewed files committed in one local commit; the hash is not written into committed files. A git-ignored local receipt records it. | Resolved by this checkpoint |
| F-02 | Medium | No off-device evidence copy | Both backups are local to the same laptop. No copy was made and neither backup was modified. Owner action needed. | **Open**; blocks academic submission, not the start of Phase 6 |
| F-03 | Medium | Fixed ROP is a degenerate comparator | Described everywhere as a low-stock, low-service comparator, with the Store Item and M5 behaviour reported separately (see section 4). No tuned (s, S) comparator was added because that needs a new experiment. | Documented; optional future experiment |
| F-04 | Medium | Headline ML result less robust than presented | Per-origin tables, Seasonal Naive comparison, scenario non-independence and the Store Item sign reversal added to results, sensitivity, limitations and the HTML report. | Resolved in reporting |
| F-05 | Medium | Selection optimism from reused validation origins | Asymmetric tuning disclosed with configuration counts. The bias cannot be quantified because the final holdout is consumed. | Documented limitation |
| F-06 | Medium | M5 sparse-demand weakness | Subgroup table and wording added; no re-selection. | Documented limitation |
| F-07 | Low | Volume-weighted mean cost, many ties | Median, tie counts and cost per demanded unit added from saved per-series outputs. | Resolved in reporting |
| F-08 | Low | Chronology self-recorded; freeze recorded a dirty tree | Unchanged and still disclosed. | Accepted limitation |
| F-09 | Low | Finite-episode artefacts | Caveats retained and attached to scenario results. | Accepted limitation |
| F-10 | Low | Environment snapshot not portable; clean-room run untested | No change. | Open, optional |
| F-11 | Info | Scalar reference shares the input adapter and was amended | Independent replays and exact-integer re-simulation passed; nothing further. | Closed |
| F-12 | Info | Variability stress changes mean and zeros | Already documented. | Closed |

## 4. Correction to one detail of the audit

The audit described the fixed reorder point as ordering at essentially every review and holding about
7.6 mean days of inventory position. The full reconciliation shows this applies to Store Item only:
99.9% of series-episodes order at every eligible review and the pooled mean position is
7.33 mean days (the audit's 7.6 was an approximation from two origins). On M5 the policy behaves as a
genuine threshold rule: 10.5 orders per 20 reviews, only
11.0% of series ordering at every review, and a mean position of
11.3 mean days. The finding stands (lower cost reflects lower stock and service), but the
wording now distinguishes the two datasets.

## 5. Unresolved items and gating

- **Open, blocks submission:** F-02, an off-device copy of the Phase 4 and Phase 5 evidence backups.
- **Open, optional:** F-10 clean-room reproduction, and a tuned (s, S) comparator under F-03.
- **Accepted limitations:** F-05, F-06, F-08, F-09.
- **Phase 6 may start** under the audit's conditions: the commit exists, the corrected wording above
  governs every dashboard page and written result, and no simulated cost difference is called a saving.
  Phase 6 and Phase 7 have not started.

## 6. Verification record

Machine-readable results are in `reports/inventory/post_audit_verification.json`, written after the
checks below ran:

- Full test suite, Ruff and dependency check.
- Frozen design, plan, execution and inventory source hashes unchanged since freeze.
- Phase 4 selection fingerprint, holdout ledger hash and hash chain.
- Phase 4 read-only evidence verifier with the new documentation overlay.
- Phase 5 backup verifier: every source file against its backup copy, using the new overlay for the
  edited documents.
- Offline HTML report: relative links only, ten figures, no scripts.

Read-only commands (no training, simulation, forecast regeneration or holdout access):

```powershell
.venv\Scripts\python.exe reports/inventory/post_audit_reconcile.py   # refuses to overwrite its output
.venv\Scripts\python.exe -m intelligent_demand.preservation.phase5_post_audit `
    --destination 'C:/Project_Backups/Demand_Forecasting_Phase5_Evidence_verified_20261108' `
    --source-overlay reports/preservation/PHASE5_AUDIT_REMEDIATION_OVERLAY.json
.venv\Scripts\python.exe -m intelligent_demand.preservation.verify `
    --workspace-root . --overlay reports/inventory/post_audit_documentation_overlay.json
```

The pre-audit versions of the ten edited files are kept byte-for-byte in
`reports/inventory/original_documents/phase5_pre_audit/`. Each matches the hash in the Phase 5 backup
manifest, so the backup still holds the originals. `report_validation.json` records the hash of the
pre-audit HTML report and was deliberately left unchanged.
