# Dataset acquisition, authentication and verification

## Current execution status — 2026-11-06

**Phase 1 data-quality gates formally closed.** Store Item and M5 both passed independent
source-to-Parquet audits, and current raw/Parquet hashes match the audited artifacts.
The Store Item review did not rerun the full M5 transformation. Reproducible Store Item
audit command (project root):

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand audit-store-item
```

This command audits existing files and writes evidence only; it does not download,
retransform, impute or replace datasets. The independent audit uses a typed Arrow CSV
reader and NumPy historical key grids, comparing every persisted sales value by business
key. Per-series missing-date counts are retained in store_item_canonical_audit.json.

Store Item train.csv has 913,000 labelled daily rows (2013-01-01–2017-12-31), 10 stores,
50 products and complete 500-series×1,826-day coverage. test.csv has 45,000 unlabelled
rows for the same series over 2018-01-01–2018-03-31; its rows are excluded from observed
sales and its sales total is undefined, not zero. sample_submission.csv is a submission
template, not an observed target source. All three CSV hashes still match acquisition.

The single zero is store 6 / item 4 / 2014-01-15 and matches Parquet unchanged. No
historical dates are missing. The old missing-date warning was a no-imputation policy
statement; the readable report now separates that information from actual quality risks.
Store Item price/category nulls reflect absent source fields. M5 retains 12,299,413 null
historical prices and optional calendar event nulls; no M5 warning has been removed.
See VALIDATION.md, DATA_DICTIONARY.md and EXPERIMENTAL_DESIGN.md for closure and readiness.

Both datasets have now been acquired locally. Store Item and M5 profiling passed with
warnings and canonical Parquet outputs were published. The earlier M5 missing-file
report predated acquisition; it was stale, not evidence that the downloaded files were
missing. All four M5 CSVs were found directly in data/raw/m5, their headers validated,
and their hashes matched the acquisition manifest. No redownload or raw-file replacement
was performed during debugging. See docs/VALIDATION.md and reports/data_quality/m5.json.

Official Kaggle 2.2.5 remains installed. The original authentication-blocked attempt is
historical; current credential validity was not retested during this local-only debug.
Detailed data-use terms still require the user's recorded review of competition rules.

## Secure official authentication

The [official authentication documentation](https://github.com/Kaggle/kaggle-cli/blob/main/docs/README.md#authentication)
documents browser login, environment tokens, a local access_token file and legacy credentials.
The project delegates credential loading to that client, captures stdout/stderr and emits
only fixed failure summaries. It never runs print-access-token or accepts competition rules.

Choose one method outside Codex chat. Never store credentials in this repository, including
ignored .env files. Do not paste credentials into chat, logs or screenshots.

1. Recommended browser flow: run this yourself from PowerShell and complete the official
   authorization. The client uses its supported user-level credential storage:

   ```powershell
   .\.venv\Scripts\python.exe -m kaggle auth login
   ```

2. Local API token: sign in at [Kaggle API settings](https://www.kaggle.com/settings/api),
   generate a token, and use a local editor to save only that token to
   `%USERPROFILE%\.kaggle\access_token` (no extension). Create .kaggle if necessary,
   keep it outside the workspace and restrict access to your account.

3. Environment token: use a masked prompt in your own PowerShell session. Run project
   commands in the same session; do not persist this in a project file:

   ```powershell
   $kaggleSecret = Read-Host 'Kaggle API token' -AsSecureString
   $env:KAGGLE_API_TOKEN = [System.Net.NetworkCredential]::new('', $kaggleSecret).Password
   Remove-Variable kaggleSecret
   ```

   Clear it later with `Remove-Item Env:KAGGLE_API_TOKEN`.

4. Legacy credentials: in API settings, choose Legacy API Credentials / Create Legacy
   API Key, then move downloaded kaggle.json to `%USERPROFILE%\.kaggle\kaggle.json`,
   outside the repository. The official client also supports KAGGLE_USERNAME/KAGGLE_KEY
   environment authentication.

KAGGLE_CONFIG_DIR, if set, must point outside the repository. The wrapper uses a temporary
working directory so startup cannot discover a project-local .env. Avoid credential-bearing
debug logging. The official client resolves user-level paths; project code never opens or
parses credential files. Do not create another virtual environment.

## Competition access and manual rules acceptance

| Dataset | Competition / source | Raw directory | Expected files |
|---|---|---|---|
| Store Item | [demand-forecasting-kernels-only](https://www.kaggle.com/competitions/demand-forecasting-kernels-only/data) | data/raw/store_item/ | train.csv, test.csv; sample_submission.csv optional |
| M5 | [m5-forecasting-accuracy](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data) | data/raw/m5/ | calendar.csv, sell_prices.csv, sales_train_validation.csv, sales_train_evaluation.csv |

Visit each competition while signed in. Read the
[Store Item rules](https://www.kaggle.com/competitions/demand-forecasting-kernels-only/rules)
and [M5 rules](https://www.kaggle.com/competitions/m5-forecasting-accuracy/rules), then manually
join/accept if appropriate. Account verification or other restrictions may also apply.
The downloader does not bypass restrictions. Public availability does not imply an open
licence; record attribution, allowed academic use and redistribution limits after reviewing
the current rules. Detailed data-use terms remain unverified here.

## Commands (PowerShell, project root)

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand check-access --dataset all
.\.venv\Scripts\python.exe -m intelligent_demand download-data --dataset store_item
.\.venv\Scripts\python.exe -m intelligent_demand download-data --dataset m5
# Or both:
.\.venv\Scripts\python.exe -m intelligent_demand download-data --dataset all
.\.venv\Scripts\python.exe -m intelligent_demand discover-data --dataset all
.\.venv\Scripts\python.exe -m intelligent_demand profile-data --dataset all
```

Place global --config before the subcommand when needed. The original no-subcommand
configuration check still works without datasets or authentication. Only download-data
accepts --force; use it deliberately to replace raw files. It was not used in this run.
A successful profile atomically replaces its derived Parquet file. Failed profiles publish
no new canonical file; an earlier successful file may remain, so use its matching report
and input hashes. Raw source files are never modified by profiling.

## Verification and reproducibility

- Command results: reports/data_quality/<command>.json. Each attempted dataset has a status.
- Discovery: actual expected-file presence, headers, byte sizes and SHA-256. Header checks
  require a correctly shaped first data row; this is not full CSV validation. Actual parser
  columns/types are retained in profile evidence, including additional source columns.
- Acquisition: official authenticated file listing, then staged competition ZIP download.
  File-list access alone is not proof of download entitlement; the download endpoint
  separately enforces competition permissions and rules.
- Extraction rejects traversal, absolute/drive paths, backslashes, Windows reserved aliases,
  links, duplicate/case-colliding names and excessive member counts/sizes. Streaming
  extraction checks ZIP CRC. Only expected source files are published.
- Existing files are skipped by default when headers/first rows are valid and all remotely
  listed expected files exist. Previously recorded hashes must match. Without an earlier
  manifest, hashes establish a local baseline only; publisher provenance is unverified.
  A changed/invalid raw file requires inspection or explicit --force.
- After download, data/raw/<dataset>/acquisition.json records competition, source URL,
  timestamp, actual byte size, SHA-256, validation status and per-file acquisition method.
  Preserved existing files are not assigned fabricated download timestamps. Local hashes
  establish reproducibility, not authenticity against a publisher-provided checksum.
- Record permitted terms evidence, source version, acquisition date, code revision,
  environment snapshot and exact command. Raw data, manifests, credentials and generated
  quality exports are excluded from Git. Credential contents are never recorded.

## Profiling and canonical transformation

Store Item checks required columns, dates, identifiers, missingness, duplicate
store/item/date keys, numeric/finite/nonnegative/integral sales and zero sales. Train and
test are profiled separately; only observed train sales enter the canonical output.

M5 validates unique day/date mappings and contiguous day columns, unique price keys,
numeric quantities and many-to-one calendar/price joins. Evaluation history is preferred;
validation history is the fallback. When both exist, common-day values and series coverage
are compared using row fingerprints. Histories are never concatenated. Sales melt in
256-series batches and write incrementally; the categorical price dimension remains in
memory. Full-scale runtime and memory are unmeasured. Missing prices remain null and are
reported. Dates and sales are not imputed. Historical prices are not guaranteed future
predictors; sales may be constrained by availability.

Outputs: data/processed/<dataset>/daily_sales.parquet and
reports/data_quality/<dataset>.json plus a readable Markdown summary. JSON includes
inventory, parser schemas, null counts/shares, row counts, date/series coverage, duplicate
evidence, zero/invalid quantities, selected history, canonical row count, sales-total
reconciliation, output hash, critical errors and warnings. Raw hashes are rechecked before
publication. Critical errors prevent canonical publication. See DATA_DICTIONARY.md for
the implemented contract. These field contracts passed on the current local source files;
future source versions must be verified again rather than assumed compatible.

## Troubleshooting

- Authentication unavailable/rejected: configure one official method above. Restart the
  VS Code terminal if its environment changed; retry check-access. Never send secrets.
- Access denied/403: open the affected competition rules page and join manually if
  appropriate. Rule acceptance is not the only possible account restriction.
- Network/timeout: check connectivity/proxy/firewall and retry. Interrupted downloads
  remain staged and do not replace existing raw files.
- Missing file: inspect the official listing. A missing optional Store Item submission or
  one M5 history variant is reported. M5 needs at least one history plus calendar and prices.
- Unsupported/empty listing: inspect client version and the official page. These small
  manifests are bounded to 200 entries; larger/paginated listings require explicit handling.
- Windows test temp/cache permissions: the verified offline command was
  `python -m pytest -p no:cacheprovider --basetemp=.venv/pytest-phase1` from project root,
  with normal user filesystem permissions. Pytest owns and clears that dedicated temporary
  directory. Never point --basetemp at raw data or a source directory.

Phase 1 stops at acquisition, quality gates and canonical representation. It performs no
forecasting, model selection, cleaning/EDA study, inventory simulation or BI build.
