# Phase 5 inventory results

Hypothetical lost-sales simulation; sales are a potentially censored demand proxy. Full populations: Store Item 500 and M5 30,490 series at each of four original validation origins; 28 days per episode. Origins reset stock. Saved forecasts are fixed at issue, not daily refreshed. These validation windows also informed Phase 4 selection; comparisons are exploratory and validation-reused, with no significance claim. Costs are normalised hypothetical units (NCU), not realised savings.

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
    --workspace-root . --overlay reports/inventory/documentation_overlay.json
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
