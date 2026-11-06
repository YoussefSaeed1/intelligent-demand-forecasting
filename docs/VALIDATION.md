# Phase 0 validation — 2026-11-06

Environment: Windows, Python 3.14.0, editable intelligent-demand 0.1.0.
Python 3.11 is preferred but was not available as a working interpreter on this machine.
The WindowsApps launcher could not execute; a local Python 3.14 installation created
the project virtual environment. Python 3.11 compatibility has not been tested.

| Check | Actual outcome |
|---|---|
| Virtual environment | Created successfully in .venv |
| Core and development installation | pip install -e ".[dev]" completed successfully |
| Dataset-free CLI/configuration | Passed; loaded default YAML and reported provisional 28-day horizon |
| Ruff | All checks passed |
| Pytest | 5 passed |
| Dependency consistency | pip check: No broken requirements found |
| Package imports | All 13 requested core/development packages and intelligent_demand imported successfully; statsmodels.api included |
| Syntax compilation | compileall completed successfully |
| Git exclusions | Verified data at all three stages, virtualenv, .env/.env.local, kaggle.json, model artefacts and generated exports ignored |
| Trackable exceptions | .env.example, README.md and data directory .gitkeep files are not ignored |
| Raw/generated content | Only .gitkeep markers exist in data, artifacts and report output directories |
| Power BI | Directory and reporting plan present; no dashboard created |

The initial sandboxed pip attempt failed with a network socket permission error
(WinError 10013). The permitted retry completed. No installation blocker remains.
Git was initialised with no commits. The sandbox account differs from the workspace
owner, so Git inspection used a command-scoped safe.directory setting for this workspace;
no global trust setting was changed.

Exact installed direct and transitive versions are in environment-freeze.txt, excluding
the local editable project path. This is a Windows/Python 3.14 snapshot, not a universal
lockfile. It includes the transitive prerelease wrapt==2.6.0.dev1 selected by pip.
No numerical forecasting compatibility or optional modelling extras have been tested.
LightGBM, Optuna, SHAP and MLflow were not requested by the installation command.

## Repeat checks from the project root (PowerShell)

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand --config configs/default.yaml
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

To complete or repeat installation in the existing environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

No datasets were acquired, rules accepted, models trained, EDA performed, simulation
implemented or Power BI dashboard built. Kaggle schema and terms verification remain
Phase 1 work; see DATASETS.md.

## Phase 1 integration validation — 2026-11-06

The Phase 0 observations above are historical. Current environment: Python 3.14.0,
official Kaggle 2.2.5, editable intelligent-demand 0.1.0 with refreshed dependency metadata.
Kaggle was installed in the existing .venv; no additional environment was created.
The first sandboxed installation hit DNS/network restrictions; the permitted retry
installed Kaggle and its required dependencies. The environment snapshot was refreshed.

| Gate | Actual result |
|---|---|
| Official Kaggle installation | Passed; kaggle==2.2.5; dependency recorded in pyproject.toml |
| Authenticated read-only operation | Blocked: authentication unavailable or rejected; raw client output suppressed |
| Store Item competition access | Unknown until authentication works; no rule acceptance inferred |
| M5 competition access | Unknown until authentication works; no rule acceptance inferred |
| Download command, both datasets | Executed; blocked at authentication, no files downloaded |
| Local dataset discovery | Executed; neither source has expected CSVs |
| Real-data profiling | Command executed; blocked by missing inputs, no empirical metrics |
| Canonical Parquet publication | Not executed on real data; no source inputs available |
| Offline source transformations | Passed on explicitly labelled miniature unit-test fixtures |
| Ruff | All checks passed |
| Pytest | 45 passed with no warnings in the verified final run |
| pip check | No broken requirements found |
| CLI smoke checks | Default config, main help, download help, discovery and blocked-status paths checked |
| Syntax compilation | Passed for src and tests |
| Git exclusions | Data, acquisition manifests, reports/data_quality, tokens and test temporary files excluded |

The unit suite uses mocked network calls and requires no Kaggle authentication. It covers
dataset selection, header validation, existing hashes, skip/force/partial acquisition,
download failure preservation, ZIP traversal/links/Windows aliases/collisions, sanitised
authentication and competition-permission errors, missing source inputs, invalid sales,
calendar and price cardinality, overlapping M5 histories, and canonical reconciliation.
Fixture output is not a downloaded dataset or an empirical project result.

The Windows sandbox/default temporary directory had permission failures. The successful
test command used normal user permissions and a dedicated verified path under .venv:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp=.venv/pytest-phase1
```

Pytest owns and clears that test directory. No credentials were exposed,
rules accepted, forecasting models trained, Phase 2 work started, inventory simulation
implemented or dashboard built.

Generated local evidence is in reports/data_quality/: check-access.json,
download-data.json, discover-data.json, profile-data.json, store_item.json/.md and
m5.json/.md. These are ignored status/quality files. There are no verified dataset file
sizes or hashes because no source files exist. Exact remaining action: configure one
official authentication method in docs/DATASETS.md, manually confirm competition access,
then rerun check-access, download-data and profile-data. Full-scale M5 performance and
actual source schema compatibility remain untested until data is available.

## M5 real-data debugging and acceptance — 2026-11-06

This section supersedes the earlier blocked execution status above. Both datasets are
now present locally. Store Item's existing real-data report passed with warnings;
this debugging iteration ran M5 only and did not redownload either source.

### Root cause and evidence

The displayed missing-source report was stale. Its modification time was
2026-11-06 12:48:15 UTC; successful M5 acquisition was recorded at 12:53:50 UTC.
The four CSVs were present at the configured raw path and passed the existing strict
header/first-row checks. Their SHA-256 values matched the acquisition manifest.
There was no directory, archive nesting or schema-discovery defect to fix.

The pipeline previously wrote individual and aggregate reports only on completion.
A long run therefore left old missing-file reports visible. Unexpected exceptions
could also leave them stale. The retained artifacts do not establish why the user's
earlier invocation did not finish; no post-download missing-source result was reproduced.

Changes: save current discovery with a running state and UTC timestamps, checkpoint
completed sources in the CLI, and save current failure evidence for unexpected local
exceptions. M5 now preserves string identifiers while allowing numeric sales parsing,
and validates/indexes the price dimension once rather than repeatedly rebuilding a
6.8-million-row join for every batch. Unique lookup and calendar cardinality checks
remain strict; missing prices remain null. Source files were not moved or rewritten.

### Actual files and schemas

All paths below are relative to data/raw/m5; all four are root-level CSVs, not nested
or archived. Other entries were acquisition.json (73,786 bytes) and .gitkeep (0 bytes).

| CSV | Bytes | Rows | Verified columns |
|---|---:|---:|---|
| calendar.csv | 103,469 | 1,969 | 14 columns; d/date/wm_yr_wk present |
| sell_prices.csv | 203,395,785 | 6,841,121 | store_id/item_id/wm_yr_wk/sell_price |
| sales_train_validation.csv | 120,007,726 | 30,490 | 6 identifiers plus d_1 through d_1913 |
| sales_train_evaluation.csv | 121,736,518 | 30,490 | 6 identifiers plus d_1 through d_1941 |

History identifiers: id, item_id, dept_id, cat_id, store_id, state_id. No required-schema
discrepancy was found. Calendar's 7,542 null cells occur in optional event name/type
fields; required day/date/week mappings contain no nulls. Price/history input fields
have no missing values. Actual parser schemas and full missingness are in m5.json.

### Full-run and independent persisted-output checks

| Check | Actual result |
|---|---|
| Profile status | passed_with_warnings; no critical errors |
| Selected history | sales_train_evaluation.csv only |
| Series / stores / products | 30,490 / 10 / 3,049 |
| Observed date range | 2011-01-29 through 2016-05-22, 1,941 days |
| Canonical rows / expected observations | 59,181,090 / 59,181,090 |
| Source sales sum / persisted sales sum | 66,927,173 / 66,927,173 units |
| Negative / missing-invalid / fractional sales | 0 / 0 / 0 |
| Zero-sales observations | 40,241,819 (approximately 68.00%) |
| History overlap | All 30,490 series matched over 1,913 shared days; not concatenated |
| Calendar duplicate day/date keys | 0 / 0 |
| Price duplicate store/item/week keys | 0 |
| Join cardinality | many-to-one; no observation expansion |
| Persisted duplicate dataset/store/item/date keys | 0, checked across every Parquet batch |
| Series/date key coverage | Complete; independently checked with a bounded boolean coverage array |
| Missing historical prices in canonical output | 12,299,413, retained as null |
| Raw checksums | All four unchanged; still match acquisition |
| Canonical output | data/processed/m5/daily_sales.parquet, 29,628,861 bytes |
| Canonical SHA-256 | 3907628a0231ebd9a3d7db0bfec994cdeb92066c4e66e26b7e46a84d586ba10d |
| Ruff / Pytest / pip check | Passed / 50 passed / no broken requirements |

The successful full profiler took 627.56 seconds. Measured peak worker working set was
1,131,978,752 bytes (about 1.05 GiB), including the actual Python worker behind the
virtualenv launcher. Sales were processed in 256-series batches; the indexed price
dimension remained in memory. The independent audit used 131,072-row Parquet batches,
one NumPy boolean per expected business key, and a separate 512-series source summation.
It took 35.96 seconds and peaked at 353,267,712 bytes (about 0.33 GiB).
These are Windows working-set measurements, not claims about total allocated memory.

Local inspectable evidence under reports/data_quality/: m5_debug_before.json,
m5.json/.md, profile-data.json, m5_verified_run.json, m5_verified.stderr.log and
m5_canonical_audit.json. The exact monitoring and audit calculations are retained in
m5_run_audit.py and m5_canonical_audit.py there. Early diagnostic runs were intentionally
stopped; their partial generated files were removed. They are not successful run evidence.

Remaining warnings concern null historical prices, future availability of observed price
covariates, and sales being potentially constrained demand. There is no remaining M5
Phase 1 execution blocker. Review these policies before Phase 2; no EDA, feature engineering,
model training, inventory simulation or Power BI build was started.

## Final Store Item independent audit and Phase 1 closure — 2026-11-06

**Phase 1 is formally closed with documented limitations.** Both datasets passed their
independent quality gates; current source and Parquet hashes match the exact audited
files. M5's full transformation and exhaustive audit were not rerun: their existing
findings were preserved and verified against current hashes. No Phase 2 work was started.

### Store Item source and persisted-file evidence

| Check | Actual result |
|---|---|
| Independent audit | passed; no critical errors |
| Source / canonical rows | 913,000 / 913,000 |
| Source / canonical sales total | 47,704,512 / 47,704,512 units, exact equality |
| Row-level sales comparison | Every canonical key/value matches CSV; 0 mismatches |
| Source / canonical duplicate business keys | 0 / 0 |
| Observed historical coverage | 2013-01-01–2017-12-31; 1,826 days for every series |
| Stores / products / series | 10 / 50 / 500 |
| Missing/extra canonical combinations | 0 / 0 |
| Missing historical dates | 0 across all 500 series, including interior and boundary checks |
| Missing core fields / negative sales | 0 / 0 |
| Zero-sales observations | 1, preserved in source and canonical output |
| Zero record | Store 6, item 4, 2014-01-15, sales=0 |
| Unlabelled competition test | 45,000 rows, 500 series×90 days, 2018-01-01–2018-03-31 |
| Test schema / duplicate keys and IDs | id/date/store/item, no sales field; 0 duplicates |
| Test records entering observed Parquet | 0; no test sales total or target values invented |
| Canonical optional fields | category_id and unit_price each have 913,000 structural nulls |
| Raw hash verification | train/test/sample_submission unchanged; all match acquisition |
| Canonical SHA-256 | eed83d489c4ee9033fec0aab6588e1f830b93de6540819873c428c2c1ce279ec |

Independent logical source types were validated by Arrow's typed CSV reader: date32
date and int64 store/item/sales (test id is int64). Canonical physical types are string
identifiers, date32[day], float64 sales/price and bool is_observed. All quantities are
finite, nonnegative and integral. Canonical series IDs are independently checked for
a bijection with store/item pairs, without calling the transformation's ID encoder.

The verification reuses configuration, checksum and report utilities, but does not call
the Store Item transformation or its feature/quantity logic. A NumPy store×item×day grid
checks every expected key and every persisted sales value in 65,536-row Parquet batches.
Source/test grids separately verify complete coverage. Raw and canonical hashes are
checked before and after; neither CSV nor Parquet is rewritten by the audit.

Raw acquisition hashes:

- train.csv: 038f25690a65149c94f86ddd3deceda20c037a5cfd754cafdfc539a72992f2ed
- test.csv: 16eb2eec677628c8ed62312a9d6749ebf46f59196dd2fece6fd1e5c147a918fb
- sample_submission.csv: b797330d1171538cf749abf6a76bef6743783d6eb74f81722465d86cf062ad3f

The prior warning, “Missing calendar dates are not filled,” described a policy and did
not assert a measured gap. The independent audit found zero gaps. The original report
now links the successful audit and states this explicitly. The single zero is a valid
recorded observation, not a missing value; its cause cannot be determined from these
files and it must not be replaced with an invented positive sale. Both datasets observe
sales rather than verified unconstrained demand. That limitation remains documented.

### Readiness and automated verification

Both sources support independent benchmarking, a common 28-day daily forecasting design,
and MAE/RMSE/WAPE/signed-bias methodology with chronological evaluation and explicit zero
handling. Methodological comparisons must use within-source baselines and consistent
windows/series, while reporting scale and period differences. Direct model transfer is
not justified: shared schema does not establish common identities, feature availability,
physical unit equivalence or target distributions. No empirical seasonal pattern or
model performance was estimated. Detailed comparison: EXPERIMENTAL_DESIGN.md.

Final automated results: Ruff passed, **60 Pytest tests passed**, pip check reported no
broken requirements. New tests detect value swaps with unchanged aggregate totals,
source/persisted duplicates, missing dates, extra products, future-test contamination,
raw checksum changes, wrong Parquet types and accidental acceptance of test sales labels.
Tiny fixtures are offline test data, not empirical project evidence.

Repeatable commands from project root:

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand audit-store-item
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp=.venv/pytest-phase1
.\.venv\Scripts\python.exe -m pip check
```

Evidence: reports/data_quality/store_item_canonical_audit.json/.md,
store_item.json/.md and phase1_readiness.json. The readiness script rebinds both audits
to current file hashes and preserves M5's 12,299,413 missing historical prices (20.782674%)
and sales/price-availability warnings. Store Item's zero-sales share is 0.000109529%; M5's
is 67.997766%. This is a zero-sales comparison, not a claim about latent demand.

No acquisition, data repair, M5 re-transformation, EDA, feature engineering, model training,
inventory simulation or Power BI work was performed in this final audit iteration.
