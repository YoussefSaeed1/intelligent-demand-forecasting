# Store Item independent source-to-Parquet audit

Status: passed

Typed Arrow CSV parsing and NumPy key grids are independent of the pandas transformation.
Competition test records are unlabelled and excluded from observed sales.

- Source / canonical rows: 913,000 / 913,000
- Source / canonical sales: 47,704,512 / 47,704,512
- Row-level sales mismatches: 0
- Duplicate canonical business keys: 0
- Missing source/canonical historical days: 0 / 0
- Historical dates: 2013-01-01 to 2017-12-31
- Historical series: 500
- Raw hashes unchanged and matching acquisition: True

The prior missing-date statement was informational; no calendar gaps were found.
The zero-sales record is preserved and matches Parquet. It is not treated as missing.
Sales are observations, not verified unconstrained demand.
