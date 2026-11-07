# Intelligent Demand Forecasting & Inventory Optimisation

Individual postgraduate Data Science diploma graduation project, Cairo University.
**Status: Phase 3B–3E complete; fixed initial forecasting benchmarks validated. Phase 4 not started.**
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
targets, and execute no models. Final holdout target access remains unavailable.

Actual experiments use an explicit sequential command, reusing valid completed runs:

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand.experiments.benchmark run --phase 3b
.\.venv\Scripts\python.exe -m intelligent_demand.experiments.benchmark run --phase 3c
.\.venv\Scripts\python.exe -m intelligent_demand.experiments.benchmark run --phase 3d
```

Each next milestone requires the previous independent audit and automated gate.
Read [baseline results](docs/BASELINE_RESULTS.md),
[statistical results](docs/STATISTICAL_RESULTS.md), [ML results](docs/ML_RESULTS.md),
and [feature availability](docs/FEATURE_AVAILABILITY.md). No systematic tuning or
final holdout evaluation has occurred. Large models, predictions, caches and figures
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
Phase 4 and protected final holdout evaluation remain unstarted.

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
  tuning/                 Future chronological hyperparameter search
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

Next: review the final Phase 3 validation evidence before authorising Phase 4.
The independent Claude audit remains mandatory after Phase 4 and before Phase 5.
See [ROADMAP.md](docs/ROADMAP.md). Phase 4 has not started.

Verified setup results and environment limitations: [VALIDATION.md](docs/VALIDATION.md).
