# store_item — Phase 1 data quality

Status: passed_with_warnings

Started (UTC): not recorded
Finished (UTC): not recorded (historical run)

## Critical errors

None recorded.

## Warnings and interpretation

- Sales are observations, not verified unconstrained demand.

## Policy and audit notes

- Independent audit found zero missing historical dates in every store/item series. The earlier missing-date warning described a no-imputation policy, not a data gap.

## Input profiles

| File | Rows | Date range | Stores | Products |
|---|---:|---|---:|---:|
| train.csv | 913000 | 2013-01-01 to 2017-12-31 | 10 | 50 |
| test.csv | 45000 | 2018-01-01 to 2018-03-31 | 10 | 50 |

## Quantity checks

| Measure | Observations | Zeros | Negative | Invalid/missing |
|---|---:|---:|---:|---:|
| train.sales | 913000 | 1 | 0 | 0 |

## Canonical transformation

Output: `data\processed\store_item\daily_sales.parquet`

- Canonical rows: 913,000
- Expected source observations: 913,000
- Source sales units: 47,704,512
- Persisted sales units: 47,704,512
- Source/Parquet reconciliation: True

## Independent persisted-file audit

Status: passed; checked 2026-11-06T13:50:52.891970+00:00
- Missing historical dates: 0
- Duplicate business keys: 0
- Row-level source/Parquet sales mismatches: 0
- Evidence: `reports/data_quality/store_item_canonical_audit.json`

See the adjacent JSON for inventory hashes, parser schemas, counts,
missingness, duplicate checks, quantities and transformation reconciliation.
Checks are implemented in src/intelligent_demand/ingestion and validation.
