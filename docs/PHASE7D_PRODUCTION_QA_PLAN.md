# Phase 7D production QA plan

Extends gates P-01..P-11 in [PHASE7_QUALITY_GATES.md](PHASE7_QUALITY_GATES.md). Every result is recorded with date, URL and
evidence path under `reports/webapp/phase7d/`; mocked checks are labelled as such.

**Severities:** C = critical (stop the rollout), H = high, M = medium.

## D: database (after 7D-1)

| ID | Sev | Check |
|---|---|---|
| D-L1 | C | Row counts for all 20 tables equal `export_manifest.json` (655,711 total); `app.provenance.export_version = 2026-11-12.1` with the four frozen hashes |
| D-L2 | C | No `series_history` or `validation_actuals` date on or after each dataset's `test_start` (final holdout excluded) |
| D-L3 | C | A-05 live: `anon` and `authenticated` cannot select, insert, update or delete in `app` or `ops`; `webapp_api` and `engine_api` are SELECT-only; no role can run DDL |
| D-L4 | C | A-09 live: `ops.rate_limit_hit` is executable only by `webapp_api` and rejects non-hash buckets |
| D-L5 | H | `webapp_api.<ref>` and `engine_api.<ref>` authenticate through the transaction pooler (6543) |
| D-L6 | H | `pg_database_size` recorded (expect about 150 MB, under 500 MB); `get_advisors` has no security errors |
| D-L7 | H | The Data API cannot reach `app` or `ops` (REST request with the publishable key returns 404 or permission denied) |

## E: engine (after 7D-2)

| ID | Sev | Check |
|---|---|---|
| E-01 | C | Missing key → 401; wrong key → 401/403; no stack traces, paths or configuration in any response |
| E-02 | C | Parity: Store Item `1:11`, origin 1, base scenario, four policies. Exact totals equal the saved Phase 5 per-series values (`app.inventory_series_base`; 2,555 / 2,772 / 2,900 / 1,309 NCU), plus all 23 summary fields against the local parity fixture |
| E-03 | C | Client-supplied demand rejected; unknown series or origin → 404; out-of-bounds parameters → 400; body over 8 kB → 413 |
| E-04 | H | `/health` reports `engineVersion cedc5a31533772fc` (hash of engine.py plus design.py) |
| E-05 | H | Function size from the build log (under 500 MB); bundled engine file hashes equal the vendored ones (deployment file listing) |
| E-06 | M | Cold-start and warm latency (median of 5); concurrency of 5 parallel calls handled without errors |
| E-07 | H | Starlette ≥ 1.3.1 installed (build log), confirming R-1 |
| E-08 | M | Runtime logs show no secret, connection string or request body |

## W: web (after 7D-3)

| ID | Sev | Check |
|---|---|---|
| W-01 | C | `/api/v1/health` returns `status ok` with the engine reachable and `exportVersion` matching provenance (P-04) |
| W-02 | C | `tests/api.test.ts` equivalents against the live URL: registry metric reproduction, study reconciliation, the pattern filter, invalid input → 400 |
| W-03 | C | Client bundle and HTML contain none of the four secret values or a pooler hostname (scan downloaded `/_next/static`) |
| W-04 | H | Rate limit: simulate returns 429 with `Retry-After` at the configured threshold; a spoofed `X-Forwarded-For` does not change the bucket |
| W-05 | H | Engine-unavailable path (owner temporarily sets a wrong `ENGINE_URL` on a preview, or the result is checked in the logs) shows the labelled precomputed fallback |
| W-06 | H | Preview deployments have no Production secrets (they return a 503 `not_configured`) |

## S: scientific and frontend (after 7D-3)

| ID | Sev | Check |
|---|---|---|
| S-01 | C | Browser QA script against the live URL: `APP_URL=<url> QA_OUT=../../reports/webapp/phase7d node tests/browser/phase7c.mjs`. Five pages × 1280/1024/390: HTTP 200, 0 overflow, 0 serious/critical axe, U-05 copy gate, Explorer→Planner carry, real run equal to the saved Phase 5 totals, CSV/PNG downloads. Space the run or raise the read limit temporarily if 429s appear |
| S-02 | C | Overview KPIs equal the local values: Store Item MAE 6.3080 and M5 1.0201; base mean cost 6,038.44 and 223.82 NCU; "300 curated of 30,490" shown |
| S-03 | H | Research page shows the 8 limitations, 12 audit findings, the reported final-holdout rows labelled as reported, and the provenance hashes |

## O: operations

| ID | Sev | Check |
|---|---|---|
| O-01 | H | Usage dashboards after QA: Vercel Active CPU and invocations; Supabase database size and egress. Record the figures |
| O-02 | M | Deployment record written (P-11), including every NOT VERIFIED item |
