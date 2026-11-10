# Intelligent Demand Forecasting & Inventory Optimisation

Individual postgraduate Data Science diploma graduation project, Cairo University.
**Status: Phases 0 to 5 complete and independently audited (verdict CONDITIONAL; 0 Critical, 0 High). Phase 6 has not started.**
Source files and generated experiment outputs are held locally outside Git. Baseline,
statistical and global ML milestones and final consolidation passed their gates. Offline tests are separate
from real-data evidence; see [VALIDATION.md](docs/VALIDATION.md).

## Problem and research objectives

Retail planning must balance uncertain future sales with stock availability and inventory
cost. This project will compare reproducible daily forecasting approaches on two published
datasets and investigate their implications under explicitly assumed inventory scenarios.
Observed sales may be constrained by availability; they are not necessarily latent demand.

The academic priorities are data provenance and quality, preprocessing, baselines,
systematic hyperparameter search, chronological evaluation, comparison, interpretation,
and reproducibility. Cross-dataset comparisons require compatible tasks and definitions.

## Datasets and acquisition

- [Store Item Demand Forecasting Challenge](https://www.kaggle.com/competitions/demand-forecasting-kernels-only/data)
- [M5 Forecasting Accuracy](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data)

Store Item supplies 500 daily store/product series; M5 supplies 30,490 Walmart series.
Both source layouts, canonical outputs and exact quantities passed independent local
audits. They provide separate benchmarks; direct model transfer is not established.

Use the official Kaggle client after configuring user-level authentication and manually
reviewing competition rules. [DATASETS.md](docs/DATASETS.md) contains secure setup,
expected files, verification and troubleshooting. Local source schemas now pass validation;
detailed data-use restrictions still require the user's recorded review of competition rules.

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand check-access --dataset all
.\.venv\Scripts\python.exe -m intelligent_demand download-data --dataset all
.\.venv\Scripts\python.exe -m intelligent_demand discover-data --dataset all
.\.venv\Scripts\python.exe -m intelligent_demand profile-data --dataset all
.\.venv\Scripts\python.exe -m intelligent_demand audit-store-item
```

Select `store_item` or `m5` instead of `all` to process one source. Downloads stage and
validate the archive, skip existing structurally valid files by default, compare stored
hashes when available, and replace raw files only with explicit `--force`. No rules are
accepted automatically. Profiling publishes reconciled observed daily sales to
`data/processed/<dataset>/daily_sales.parquet`. It does not clean, impute or model.
Reports and status JSON live in `reports/data_quality/`; selected small validation
reports are allowlisted in Git. Raw data, Parquet outputs and large generated tables
remain ignored. Five selected Phase 2 figures (comparison, price coverage, M5 classes,
SNAP and departments, PNG/SVG) are retained; other figures stay local and can be regenerated.

## Phase 2 EDA and proposed experiments

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand eda --dataset all --settings configs/eda.yaml
```

This command reads verified Parquet without rewriting it. All series enter training-
prefix EDA; four 28-day validation windows and the final 28 days are reserved before
detailed target exploration. Full-history exceptions are integrity reconciliation and
label-free price coverage. The enhanced presentation produces 39 reusable tables and
29 PNG/SVG figure pairs,
dataset/comparison reports and validation evidence under `reports/eda/` and
`reports/figures/phase2/`. The original 24-figure analytical run took 132.60 seconds and peaked at
1.123 GiB worker working set. No forecasting models are trained.

Read [EDA findings](docs/EDA_FINDINGS.md) and the
[proposed forecasting protocol](docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md) for actual
results, exact splits, model candidates, metrics, leakage rules and limitations.

Review all charts in the [offline HTML report](reports/eda/EDA_VISUAL_REVIEW.html),
with its [figure index](reports/eda/VISUALISATION_INDEX.md) and
[visual QA summary](reports/eda/VISUAL_QA_SUMMARY.md). Open the HTML in a browser;
keep `reports/eda/` and `reports/figures/` together. No server or internet is needed.

To refresh only figures and the report from existing validated summaries, without
rerunning full EDA, downloading data or rewriting canonical Parquet:

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand.exploration.visual_review --refresh-figures
```

Omit `--refresh-figures` to verify the existing images against comparison renders.
The added SNAP/department/extreme-value views use existing training summaries; event
and SNAP associations remain descriptive, and the final evaluation targets stay protected.

## Proposed methodology

Acquire and hash source files; profile keys, dates, missingness, zeros and duplicates;
validate dataset-specific transformations into a provisional long daily schema; perform
training-only EDA; construct leakage-safe lag/calendar features; establish naive and weekly
seasonal naive baselines; compare suitable exponential smoothing/ARIMA-family and
scikit-learn models and CPU LightGBM with fixed initial configurations.
Use systematic search on rolling validation folds, freeze choices, then assess the final
chronological holdout. See [experimental design](docs/EXPERIMENTAL_DESIGN.md).

## Phase 3 forecasting

The model registry, origin-bounded data access, complete prediction persistence,
pooled/macro metrics, coverage and restart-safe local experiment registry are implemented.
Five baselines, eight statistical/intermittent methods and two global ML methods are
implemented and executed under independent milestone gates. Statistical ARIMA/SARIMA
use declared training-only 53/51-series subsets; the other methods evaluate all
500/30,490 series. ML training is resource bounded, while evaluation remains complete.

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand forecast-plan
.\.venv\Scripts\python.exe -m intelligent_demand forecast-models
```

These read-only commands validate the original four 28-day validation origins and list
all 15 model definitions. They read configuration/protocol metadata, not canonical
targets, and execute no models. Their ordinary target reader still cannot access protected final targets; the separately authorised Phase 4C assessment is complete.

The original Phase 3 execution used these sequential commands. For review, use the saved-evidence commands in the Phase 4 reproducibility guide instead:

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand.experiments.benchmark run --phase 3b
.\.venv\Scripts\python.exe -m intelligent_demand.experiments.benchmark run --phase 3c
.\.venv\Scripts\python.exe -m intelligent_demand.experiments.benchmark run --phase 3d
```

Each next milestone requires the previous independent audit and automated gate.
Read [baseline results](docs/BASELINE_RESULTS.md),
[statistical results](docs/STATISTICAL_RESULTS.md), [ML results](docs/ML_RESULTS.md),
and [feature availability](docs/FEATURE_AVAILABILITY.md). At the Phase 3 checkpoint, systematic tuning and
final holdout evaluation had not yet occurred. The completed Phase 4 results are linked below. Large models, predictions, caches and figures
remain local and ignored. The subsequent final scientific integrity review authorises
a secure local Phase 3 checkpoint; no push or upload is authorised.

Open the [offline forecasting benchmark report](reports/forecasting/PHASE3_BENCHMARK_REPORT.html)
in your browser, keeping the `reports/forecasting/` and `reports/figures/` directories
together. The [scientific report](docs/PHASE3_BENCHMARK_REPORT.md),
[model comparison](docs/PHASE3_MODEL_COMPARISON.md) and
[limitations](docs/PHASE3_LIMITATIONS.md) retain actual values, populations and caveats.
Final validation: 318 tests; Ruff and pip check passed; 224 saved evaluations
independently reconciled; all nine source hashes unchanged. Browser automation cannot
preview local file URLs, but PNG/SVG decoding, visual inspection and relative-link
validation are performed locally.

The subsequent [final scientific integrity review](docs/PHASE3_INTEGRITY_REVIEW.md)
recalculated all saved comparisons and audited exact training-sample reproducibility.
The current suite has **320 passing tests**. M5 RF's small mean lead over MA28 does
not extend to a majority of individual series; price publication latency remains a
conditional research assumption. A secure local checkpoint is authorised after review;
That review preceded the now-completed, separately authorised Phase 4 assessment.

See [forecasting engine](docs/FORECASTING_ENGINE.md),
[metric definitions](docs/METRIC_DEFINITIONS.md) and
[Phase 3 progress](docs/PHASE3_PROGRESS.md). The existing experimental protocol is preserved.
The [integrity review](docs/PHASE3A_INTEGRITY_REVIEW.md) records the fixes, validation
results and capacity limits for the authorised local checkpoint.

Inventory work will compare baseline and forecast-driven policies with assumed lead times
and costs. It will report scenario outcomes, not actual business savings. Power BI exports
and four planned pages are described in [powerbi/README.md](powerbi/README.md).

## Technology and local setup

Python 3.11 is preferred; packaging allows 3.11–3.14. The initial machine has a usable
Python 3.14.0 interpreter; portability to 3.11 requires a separate validation run.
Runtime: pandas, NumPy, SciPy, scikit-learn, statsmodels, matplotlib, seaborn, PyArrow,
PyYAML, python-dotenv and the official Kaggle package. Development: JupyterLab, Pytest and Ruff.
Optional extras:
boosting (LightGBM), tuning (Optuna), explain (SHAP), tracking (MLflow).

Run from the project root in PowerShell; activation is unnecessary:

```powershell
# On a machine with the Python launcher and Python 3.11 installed:
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m intelligent_demand --config configs/default.yaml
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

If `.venv` already exists, skip creation. Select `.venv/Scripts/python.exe` in VS Code.
Install the Python and Ruff VS Code extensions manually if needed. `.env.example` contains
comments only. Project settings have no environment overrides; the official Kaggle client
separately inherits authentication from the terminal environment or user-level storage.
Configuration lives in `configs/default.yaml`; paths resolve from its parent project directory.

## Structure

```text
configs/                  Central experiment settings
data/{raw,interim,processed}/{store_item,m5}/  Ignored local data
src/intelligent_demand/
  config.py, __main__.py   Validated configuration and dataset-free check
  ingestion/              Official-client acquisition, file inventory and source adapters
  validation/             Incremental quality checks, reports and Parquet reconciliation
  preprocessing/          Future dataset-specific cleaning
  exploration/            Population EDA, figures, reports and saved-output validation
  features/               Shifted, origin-safe recursive features and validated caches
  models/                 Baselines, statistical/intermittent, RF and LightGBM adapters
  tuning/                 Frozen seeded search, final selection authority and one-time assessment
  evaluation/             Validated folds, prediction publication, grouped metrics and coverage
  experiments/            Origin data capabilities, configuration, registry and orchestration
  inventory/              Future scenario simulation
  reporting/              Verified benchmark reports, figures and offline HTML
  utils/                  Future shared utilities only when justified
notebooks/                Future numbered exploratory notebooks
artifacts/{models,experiments}/  Ignored generated artefacts
reports/{figures,exports}/      Ignored generated outputs
powerbi/                  Reporting plan; no dashboard yet
tests/                    Configuration, ingestion, independent audits and EDA/metric tests
docs/                     Proposal, design, provenance and roadmap
```

## Reproducibility

Keep raw inputs immutable and outside Git; record checksums, source version, acquisition
date and restrictions. Record code revision, Python/package versions, configuration,
seeds, split dates, horizon and selected series for every future experiment. Do not tune
on the test set. Dependency ranges in pyproject are not a lock; the verified environment
snapshot in `docs/environment-freeze.txt`, when available, records this setup only.
No licence is granted for source datasets by this repository. Academic requirements
and optional enhancements are tracked separately in [ACADEMIC_REQUIREMENTS.md](docs/ACADEMIC_REQUIREMENTS.md).

Current scope: Phase 5 hypothetical inventory simulation is complete. It was authorised under the
[limited conditional forecasting gate](docs/CLAUDE_FOCUSED_FORECASTING_GATE.md) and then
reviewed by a broader independent Claude audit of Phases 0 to 5
([report](docs/CLAUDE_INDEPENDENT_AUDIT_PHASES_0_5.md), verdict CONDITIONAL). Phase 6 may proceed
only under the reporting conditions in [the audit response](docs/PHASE5_AUDIT_RESPONSE.md).
Off-device backup remains outstanding before academic submission.
See [ROADMAP.md](docs/ROADMAP.md) and the Phase 5 gate receipts for actual progress.

Verified setup results and environment limitations: [VALIDATION.md](docs/VALIDATION.md).

## Phase 4 optimisation and final assessment

All 27 fixed cases (23 tuning configurations and four references), 108 validation
fold runs and 45,177,440 forecasts passed independent reconciliation. Primary
selection used four-origin macro MAE on full populations, with seed 42 and a
fixed budget. All Phase 4 ML is price-free. The frozen final choices are Store
Item LightGBM and M5 Random Forest; 3,470,880 forecasts across eight selected
model/comparator evaluations were sealed before either holdout was opened. Each
canonical holdout was read once, with subsequent saved-actual audit reads logged.

| Selected method | Final macro MAE | Pooled RMSE | Pooled WAPE % |
|---|---:|---:|---:|
| Store Item LightGBM | 5.434343 | 7.066976 | 12.258462 |
| M5 price-free Random Forest | 1.047231 | 2.201063 | 72.582278 |

M5 RF improves final MAE by 1.735707% over MA28; MA28 has better macro MASE.
These are predictive benchmark results, not proof of significance or inventory
savings. Store Item retained its initial LightGBM configuration; additional search
did not improve its validation MAE. No post-holdout model changes were made.

The complete suite passed **352 tests**; Ruff, pip check, source/protocol hashes,
forecast grids, ledger and independent metric checks passed. The offline report
contains 11 PNG/SVG figure pairs and verified local links. Automated browser
rendering was unavailable under the local-file navigation policy.

- [Offline scientific report](reports/forecasting/PHASE4_FORECASTING_REPORT.html)
- [Tuning results](docs/PHASE4_TUNING_RESULTS.md)
- [Frozen selection](docs/PHASE4_FROZEN_MODEL_SELECTION.md)
- [Final assessment](docs/PHASE4_FINAL_EVALUATION.md)
- [Scientific interpretation and metric trade-offs](docs/PHASE4_SCIENTIFIC_REVIEW.md)
- [Feature availability](docs/PHASE4_FEATURE_AVAILABILITY.md)
- [Safe reproducibility commands](docs/PHASE4_REPRODUCIBILITY.md)
- [Completion checklist](docs/PHASE4_COMPLETION_CHECKLIST.md)
- [Independent audit package guide](docs/PHASE4_AUDIT_PACKAGE.md)

Phase 4 development was subsequently checkpointed locally at
`54a689b7cb07970556bbf2fc164adf934307eab8`. Raw/canonical datasets,
models, predictions and training caches remain local and ignored. No Phase 5,
Claude invocation, Git push or new repository creation was performed.

The subsequent [internal audit](docs/CODEX_INTERNAL_AUDIT_PHASES_0_4.md) and
[post-audit remediation](docs/POST_AUDIT_REMEDIATION_REPORT.md) preserve that
scientific baseline while adding forward-looking ingestion/ownership safeguards.
Use the [read-only evidence verification and handoff](docs/CLAUDE_AUDIT_HANDOFF.md)
for the preserved assessment; modified runtime code is not the historical frozen
program. A verified local backup on the same device is recorded; off-device backup
remains outstanding. The subsequent limited conditional review permitted Phase 5; the broader
independent audit of Phases 0 to 5 has since been completed (see the Phase 5 section).


## Phase 5 hypothetical inventory simulations

The frozen design evaluates four policies on all 500 Store Item and 30,490 M5
series, at each of four original validation origins. Seventeen predefined
scenarios give 544 cases. Selected ML is unchanged LightGBM / price-free RF;
no forecasting model was fitted, tuned or reselected and no final holdout
was used. Costs, lead times, initial stocks and buffers are hypothetical.
Fixed-origin 28-day forecasts support finite episodes, not daily reforecasting.
Base results show stockholding/service trade-offs; ML does not uniformly
minimise cost. These validation windows were reused after forecasting selection.
After the independent audit, headline comparisons always show selected ML, MA28 and Seasonal Naive
by validation origin; the 17 scenarios are not independent confirmations; and simulated cost
differences are never realised savings.

- [Offline inventory report](reports/inventory/PHASE5_INVENTORY_REPORT.html)
- [Inventory results and safe commands](docs/PHASE5_INVENTORY_RESULTS.md)
- [Design and timing](docs/INVENTORY_SIMULATION_PROTOCOL.md)
- [Sensitivity analysis](docs/PHASE5_SENSITIVITY_ANALYSIS.md)
- [Limitations](docs/PHASE5_LIMITATIONS.md)
- [Actual completion gates](docs/PHASE5_COMPLETION_CHECKLIST.md)
- [Broader independent audit handoff](docs/PHASE5_CLAUDE_AUDIT_HANDOFF.md)
- [Independent audit of Phases 0 to 5](docs/CLAUDE_INDEPENDENT_AUDIT_PHASES_0_5.md)
- [Audit response, finding dispositions and corrected comparisons](docs/PHASE5_AUDIT_RESPONSE.md)

Phase 5 and the audit response are checkpointed in one local commit
(`feat: complete phase 5 and document independent audit findings`; find it with `git log -1`).
Nothing was pushed. No Phase 6/7 work is authorised here. Detailed inventory outputs remain
local and Git-ignored; the local inventory records their hashes but is not an independent
backup. Both evidence backups are on the same laptop, so off-device protection is still required
before academic submission. Phase 4 original evidence and its same-device backup are unchanged.
Use `reports/inventory/post_audit_documentation_overlay.json` with the read-only evidence
verifier, and `intelligent_demand.preservation.phase5_post_audit` with
`reports/preservation/PHASE5_AUDIT_REMEDIATION_OVERLAY.json` for the Phase 5 backup; the earlier
overlays are preserved and describe the pre-audit documents.
