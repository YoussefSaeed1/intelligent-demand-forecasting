# Intelligent Demand Forecasting & Inventory Optimisation

Individual postgraduate Data Science diploma graduation project, Cairo University.
**Status: Phase 1 closed; Store Item and M5 passed independent persisted-file audits.**
Source files are held locally outside Git. No forecasting models, experimental model
results, inventory simulation or dashboards are included. Offline tests are separate
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

Dataset A is planned as the store/item forecasting benchmark. Dataset B's official
Kaggle listing describes a Walmart retail unit-sales task. It will provide a second
independent forecasting benchmark; exact file layouts and hierarchy will be verified locally.

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
Reports and status JSON live in `reports/data_quality/` and are ignored by Git.

## Proposed methodology

Acquire and hash source files; profile keys, dates, missingness, zeros and duplicates;
validate dataset-specific transformations into a provisional long daily schema; perform
training-only EDA; construct leakage-safe lag/calendar features; establish naive and weekly
seasonal naive baselines; compare suitable exponential smoothing/ARIMA-family and
scikit-learn models. Consider LightGBM later if justified by resources and evidence.
Use systematic search on rolling validation folds, freeze choices, then assess the final
chronological holdout. See [experimental design](docs/EXPERIMENTAL_DESIGN.md).

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
  exploration/            Future reusable EDA helpers
  features/               Future leakage-safe feature construction
  models/                 Future baseline, statistical and ML forecasting
  tuning/                 Future chronological hyperparameter search
  evaluation/             Future backtests and metrics
  inventory/              Future scenario simulation
  reporting/              Future export contracts
  utils/                  Future shared utilities only when justified
notebooks/                Future numbered exploratory notebooks
artifacts/{models,experiments}/  Ignored generated artefacts
reports/{figures,exports}/      Ignored generated outputs
powerbi/                  Reporting plan; no dashboard yet
tests/                    Configuration boundary tests
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

Next: review the verified schema, null-price policy and quality warnings before authorising
Phase 2. See [ROADMAP.md](docs/ROADMAP.md). Phase 2 has not started.

Verified setup results and environment limitations: [VALIDATION.md](docs/VALIDATION.md).
