# Phase 5 inventory results

Hypothetical lost-sales simulation; sales are a potentially censored demand proxy. Full populations: Store Item 500 and M5 30,490 series at each of four original validation origins; 28 days per episode. Origins reset stock. Saved forecasts are fixed at issue, not daily refreshed. These validation windows also informed Phase 4 selection; comparisons are exploratory and validation-reused, with no significance claim. Costs are normalised hypothetical units (NCU), not realised savings.

## Audit-corrected comparison (governs interpretation)

An independent Claude audit of Phases 0 to 5 (2026-11-10) returned **CONDITIONAL** with 0 Critical, 0 High, 6 Medium, 4 Low and 2 Informational findings. See [the audit](CLAUDE_INDEPENDENT_AUDIT_PHASES_0_5.md) and the [disposition of each finding](PHASE5_AUDIT_RESPONSE.md). No simulation result was changed.

Every figure below is a hypothetical simulated cost difference in normalised cost units (NCU), not a realised saving. All numbers were re-aggregated from the persisted per-series outputs of all 544 completed cases and reconciled with the saved audit summary ([reconciliation](../reports/inventory/post_audit_reconciliation.json)). The original findings below are retained unchanged; where emphasis differs, this section governs.

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

**Reporting rules adopted after the audit**

1. Selected ML, MA28 and Seasonal Naive are always reported together, with differences by validation origin as well as pooled.
2. The 17 sensitivity scenarios reuse the same four origins, fixed-origin forecasts and populations. They are parameter sensitivity checks, not independent confirmations. For Store Item ML against MA28 the scenario count is 17 of 17, yet the result is cheaper in 52 of 68 scenario-origin cells, because origin 4 reverses almost every scenario.
3. Store Item ML against MA28 reverses sign at the last origin (+385.21 NCU). ML is cheaper at 3 of 4 origins.
4. Store Item ML against Seasonal Naive has only a small average advantage (-67.27 NCU, -1.10%), and ML is costlier at origin 3 (+112.83).
5. M5 ML is costlier than MA28 at all four origins (+1.90 NCU, +0.85%) while giving higher pooled fill (+0.52 points). It is cheaper than Seasonal Naive at all four origins (-11.01 NCU).
6. Fixed Reorder Point is a low-stock, low-service comparator, not a better policy. On Store Item it orders at essentially every review (99.9% of series-episodes; 20.00 of 20 eligible reviews), so its inventory position (7.3 mean days) never reaches the 11-day trigger. On M5 it behaves as a threshold rule: it orders at 10.5 of 20 reviews and only 11.0% of series order at every review. Its lower cost reflects lower stock and lower fill (fill below ML in 15 of 17 Store Item and 17 of 17 M5 scenarios).
7. Selection optimism is asymmetric. Selected ML was chosen from 12 (Store Item) and 11 (M5) tuning configurations ranked on the same four validation origins used here. MA28 and Seasonal Naive are fixed rules with no tuned parameters. Store Item retained its initial LightGBM configuration, so its optimism comes from selection among configurations rather than from a tuning gain. The size of the bias is not quantifiable: the final holdout was consumed once and no fresh window exists. Any bias favours ML.
8. M5 sparse sampling: the Random Forest's validation MAE advantage over MA28 (1.33% on average) comes from series outside the 6,878-series retrospective group whose six sampled training labels are all zero. In that group MA28 has the lower MAE at all four origins, and ML costs more than MA28 at all four origins. Outside the group ML also costs more than MA28 at 3 of 4 origins, so sparse series do not fully explain the M5 result. The group is derived from final-training labels and is report-only.
9. All costs are hypothetical normalised units (NCU) from a validation-reused simulation. They are not realised savings and must never be reported as savings.

## Original Phase 5 results (unchanged)

Base: L=7 full intervening days; R=1; buffer=3 training-mean days; initial=7 days; h=1 NCU/unit/day, p=10 NCU/unmet unit, k=1 NCU/order. Empty initial pipeline. End-day orders arrive start t+L+1. All policies stop new orders when the remaining L+R forecast dates are unavailable; remaining demand is still scored.

store_item: selected ML costs 6038.442500 NCU/series/episode versus MA28 6414.586500; ML-minus-MA28 -376.144000 (-5.864%). Pooled fill 98.382816% versus 98.382904%. Lowest base cost: Fixed ROP (3276.439000). Four origin ML-minus-MA28 mean-cost differences: -915.780000, -598.086000, -375.922000, +385.212000.

m5: selected ML costs 223.819892 NCU/series/episode versus MA28 221.922516; ML-minus-MA28 +1.897376 (+0.855%). Pooled fill 83.918902% versus 83.403339%. Lowest base cost: Fixed ROP (205.137201). Four origin ML-minus-MA28 mean-cost differences: +0.397114, +2.354608, +1.662414, +3.175369.

| dataset | policy | mean_cost | pooled_fill_rate | average_on_hand | stockout_days_per_episode |
|---|---|---|---|---|---|
| store_item | fixed_reorder_point | 3276.439000 | 0.976764 | 102.123393 | 2.266000 |
| store_item | moving_average_28 | 6414.586500 | 0.983829 | 218.519982 | 0.971000 |
| store_item | seasonal_naive | 6105.716500 | 0.983826 | 207.482732 | 0.972000 |
| store_item | selected_ml | 6038.442500 | 0.983828 | 205.078536 | 0.971500 |
| m5 | fixed_reorder_point | 205.137201 | 0.795634 | 4.203696 | 2.639078 |
| m5 | moving_average_28 | 221.922516 | 0.834033 | 5.402170 | 2.205067 |
| m5 | seasonal_naive | 234.832781 | 0.827529 | 5.813157 | 2.318498 |
| m5 | selected_ml | 223.819892 | 0.839189 | 5.540203 | 2.148639 |

Full matched populations are evaluated for every scenario. Base events cover all series; sensitivity daily events retain only the six predeclared representatives per dataset, while per-series summaries cover everyone. Original run/model IDs, fallback counts, source hashes and timings are in case status manifests. ML policy names refer to the unchanged Store Item LightGBM and price-free M5 RF frozen choices.

Independent audit: 544 cases; 8429280 series episodes; 13969536 retained daily events; 3264 separate scalar replays. The input adapter is shared; state-machine arithmetic is independently implemented.

[Offline report](../reports/inventory/PHASE5_INVENTORY_REPORT.html), [machine results](../reports/inventory/phase5_summary.json), [chart data](../reports/inventory/report_data.json).

## Reproducibility

```powershell
.venv\Scripts\python.exe -m ruff check . --no-cache
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider `
    --basetemp artifacts/test_runs/phase5_review_unique
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m intelligent_demand.inventory.plan
.venv\Scripts\python.exe -m pytest `
    tests/test_inventory_design.py tests/test_inventory_engine.py `
    tests/test_inventory_integrity.py -q -p no:cacheprovider `
    --basetemp artifacts/test_runs/phase5_reference_unique
.venv\Scripts\python.exe -m intelligent_demand.inventory.runner smoke
.venv\Scripts\python.exe -m intelligent_demand.inventory.runner base
.venv\Scripts\python.exe -m intelligent_demand.inventory.audit base
.venv\Scripts\python.exe -m intelligent_demand.inventory.runner sensitivity
.venv\Scripts\python.exe -m intelligent_demand.inventory.audit all
.venv\Scripts\python.exe -m intelligent_demand.inventory.report
.venv\Scripts\python.exe -m intelligent_demand.inventory.report validate
.venv\Scripts\python.exe -m intelligent_demand.preservation.verify `
    --workspace-root . --overlay reports/inventory/post_audit_documentation_overlay.json
```
Use fresh test temporary directories. Existing completed cases are hash-checked and reused;
immutable gates/audit receipts use exclusive creation and intentionally refuse overwrites.
For an independent audit repeat, call the audit CLI with `--receipt-directory` pointing to
a new empty directory. Never delete originals to make a rerun work. Smoke/audit gate receipts
are preserved. Rebuilding report.py overwrites derived charts/reports only, never scientific
inputs or simulation results. A fresh machine needs local ignored inputs listed in plan.json;
Git alone cannot reconstruct them. No command here fits or tunes a forecasting model or opens
the final holdout. Verify SHA-256 of plan/design/code and all input predictions; runner and
audit enforce these contracts. No forecast is advanced or regenerated during an episode.


## Demand-pattern details

| dataset | pattern | series_episodes | ml_minus_ma28_cost | ml_pooled_fill | ma28_pooled_fill |
|---|---|---|---|---|---|
| m5 | all_zero | 64 | 9.234375 | 0.588364 | 0.533091 |
| m5 | erratic | 1956 | -1.907464 | 0.860944 | 0.854124 |
| m5 | insufficient_positive_history | 20 | 5.900000 | 0.532394 | 0.470423 |
| m5 | intermittent | 92176 | 1.011131 | 0.832225 | 0.827914 |
| m5 | lumpy | 23812 | 3.875483 | 0.807127 | 0.799770 |
| m5 | smooth | 3932 | 12.446846 | 0.909906 | 0.906654 |
| store_item | smooth | 2000 | -376.144000 | 0.983828 | 0.983829 |

The M5 primary sparse-training masks are origin-specific. The separate 6,878-series final-training zero-label mask is retrospective and report-only. Coverage and paired per-series mean/median/10th/90th differences are in report_data.json. They are descriptive distributions, not confidence intervals.

Audit correction: the first sensitivity replay reassociated S-IP as S-stock-pipeline. Fractional stress arithmetic around ceil produced a one-unit boundary disagreement. The separate reference now follows the declared IP=stock+pipeline grouping; all 3,264 scalar episodes reconcile without changing production code/results or widening tolerances. Raw floating-point ceiling remains the deterministic numerical convention; near-integer fractional cases can be sensitive at the one-unit level. The failed diagnostic log is retained.


Additional persisted metric reconciliation:
```powershell
.venv\Scripts\python.exe -m intelligent_demand.inventory.audit metrics
```
The original receipt is exclusive: retain it; do not overwrite it to repeat a check.
Local evidence inventory creation (after completion documents are final):
```powershell
.venv\Scripts\python.exe -m intelligent_demand.inventory.audit inventory
```
This inventories paths, sizes and SHA-256 hashes; it does not copy or back up files.
Detailed summary JSON, event/series Parquet and figures remain ignored locally.
Original source dependency hashes are in the frozen Phase 5 plan and preserved
Phase 4 evidence inventory. Regenerating these inventory results needs those local
inputs but does not need final-holdout access or new forecast training.
