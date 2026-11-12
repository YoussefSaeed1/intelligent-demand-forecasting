# Phase 7D progress

Last updated: 2026-11-12. Current subphase: **7D-3A CLOSED (`36da979` on private `main`; engine untouched). 7D-3B (`idf-web`) awaiting approval.**

| Subphase | Status |
|---|---|
| 7D-0 pre-deployment readiness | DONE: [report](PHASE7D_PREDEPLOYMENT_REPORT.md), [runbook](PHASE7D_DEPLOYMENT_RUNBOOK.md), [QA plan](PHASE7D_PRODUCTION_QA_PLAN.md), [rollback](PHASE7D_ROLLBACK_PLAN.md) |
| 7D-1 Supabase | DONE: project, migration, SCRAM role passwords, seed, live gates and independent verification all PASS |
| 7D-2 engine | DONE: P-1, P-2, P-3 accepted; production E-01..E-08 PASS on `9a13fab` (`dpl_7qGSEBPMyeqvJnifA5w6fuUtcorG`) |
| 7D-3 web | 7D-3A CLOSED (`36da979`); 7D-3B deployment NOT STARTED ([checklist](PHASE7D_3B_CHECKLIST.md)) |
| 7D-4 production QA | NOT STARTED |

## Completed operations (7D-0, all read-only)
- Git: HEAD `7000c048900b315e131ba8ccce3350c7dd7e4140` (`main`); tracked tree clean; `experiments/` untracked; no remote.
- Evidence: plan `63efc59e`, execution `b55ba4a0`, selection `a71ab187`, ledger `fa2af529` recomputed; vendored engine identical;
  backup `sha256sum -c` 208/208.
- Scans: tracked-tree secret scan clean; `npm audit --omit=dev` 0; OSV found 5 Starlette CVEs (R-1). PyPI: cp314 Linux wheels exist.
- Measured engine runtime dependencies ≈ 185 MB installed.

## Cloud resources inspected (read-only)
- Vercel team `team_CNXls9qDvhkHpuAhliQxEcPs`: projects youssef-portfolio, court-iron, semester-planner (plan not exposed by connector).
- Supabase org `uxqjykiobncetduzzqrg` (free): project `semester-planner` (`xwaooaweoubxlshvmjtf`, eu-central-1, PG 17.11); one slot free.

## Cloud changes performed
- 2026-11-12: pushed `main` (`8c54c3c`) to private GitHub `YoussefSaeed1/intelligent-demand-forecasting` (P-2).
- 2026-11-12: created Vercel project `idf-engine` (`prj_ZkgvGobCJHntKWcrevCAgRlcsmX6`), Git-linked, root `apps/engine`, FastAPI, functions `fra1`, source files outside root enabled (P-3).
- 2026-11-12 (owner): Production-only sensitive env `ENGINE_DATABASE_URL`, `ENGINE_SHARED_KEY`; Protection Bypass for Automation generated.
- 2026-11-12: production deployment `dpl_5yubMyUoFsNF3RWwS8gMZY8niHzA` from `main` @ `8c54c3c` (P-3).
- 2026-11-12: created Supabase project `idf-research-explorer` (`ecxswrwuylenwvsxghxg`), approval A-1.
- 2026-11-12: applied migration `app_schema` (schemas app/ops, 21 tables, 3 roles without passwords), approval A-2.
- 2026-11-12 (owner): set `webapp_api`/`engine_api` passwords as client-side SCRAM verifiers; seeded the 20 curated tables (one transaction).

## Owner approvals recorded
- 7D-0 investigation only (2026-11-12).
- A-1: create `idf-research-explorer` only (2026-11-12).
- A-2: apply the committed migration only (2026-11-12).
- 7D-1 seeding/passwords run by owner (2026-11-12).
- P-1: local security fixes, tests and one local commit only (2026-11-12).
- P-2: add `origin` and push `main` to the private repo (2026-11-12).
- P-3: create and deploy `idf-engine` only (2026-11-12).

## 7D-1 pre-provisioning checks (2026-11-12, read-only)
- HEAD `7000c04` confirmed; only the 7D docs and `experiments/` untracked.
- Target: org `uxqjykiobncetduzzqrg` (free), new project `idf-research-explorer`, `eu-central-1`; 1 of 2 free slots used.
- Seed inputs: 20/20 CSV hashes match `export_manifest.json`; 655,711 rows; export `2026-11-12.1`; provenance carries the four
  frozen hashes and `FinalHoldoutTargetsRead: false`.
- Migration: schemas/roles guarded (`if not exists`), 21 `create table` not idempotent → recovery = rollback-plan clean-up in the
  new project only, then one re-apply. No superuser-only statements; roles created without passwords.
- Seed: client-side `COPY FROM STDIN` in one transaction with count verification (allowed by the connector rules; run by owner).
- A-1 approved by owner (create project only).

## 7D-1 A-1 result (2026-11-12)
- Created Supabase project `idf-research-explorer`, ref **`ecxswrwuylenwvsxghxg`**, org `uxqjykiobncetduzzqrg` (plan free),
  region `eu-central-1`, status ACTIVE_HEALTHY, Postgres 17.11.0.019, created 2026-11-12T12:37:36Z. No cost-confirmation
  step was requested by the connector (which requires one for nonzero quotes): $0.
- Connection options: direct `db.ecxswrwuylenwvsxghxg.supabase.co:5432` (IPv6 on Free); Supavisor shared pooler (IPv4) with
  users `<role>.ecxswrwuylenwvsxghxg`, session port 5432 and transaction port 6543; exact pooler hostname is in the dashboard
  Connect panel (not exposed by the connector). No SQL executed against the new database.
- `semester-planner` (`xwaooaweoubxlshvmjtf`) unchanged (ACTIVE_HEALTHY, PG 17.11.0.003, created 2026-10-13).
- Free-plan active-project slots now 2 of 2 used.
- A-2 approved by owner (apply migration only).

## 7D-1 A-2 result (2026-11-12)
- Pre-checks: project ACTIVE_HEALTHY; no `app`/`ops` schemas or app roles existed; connector runs as `postgres`
  (CREATEROLE, not superuser); `pg_default_acl` has only schema-scoped entries (public, storage, graphql, …), none global.
  Migration SHA-256 `c7b2d172…` = committed file.
- Applied the committed migration verbatim inside `begin; … commit;` via `apply_migration` (name `app_schema`, recorded as
  version `20261112133809`). Success.
- Catalog fingerprint vs the local PG 17.11 reference built from the same file: columns, constraints, indexes, RLS flags,
  policies, table grants, schema ACLs, function (definition, SECURITY DEFINER, search_path, ACL) and role attributes all
  **identical**; 21 tables, 43 indexes. Memberships differ only by PG16+ implicit `postgres` ADMIN grants on the three roles
  it created (inherit/set false); `webapp_api ∈ app_reader` (inherit) identical.
- Empty: 0 rows across all 21 tables. RLS on 21/21; 24 policies, all SELECT.
- Effective privileges: anon/authenticated/service_role: no schema usage, 0 tables, no function execute. webapp_api: SELECT
  20 app tables + execute `ops.rate_limit_hit`, 0 writable. engine_api: SELECT 4 tables only, 0 writable. No role has CREATE on `app`.
- Advisors: security INFO `rls_enabled_no_policy` on `ops.rate_limits` (intentional deny-all; accessed only by the
  SECURITY DEFINER function). Performance: 22 INFO unused-index notices (empty database).
- One verification query reading `pg_authid` was declined at the consent prompt; not retried. Role passwords are unset by
  construction (migration sets none).
- `semester-planner` unchanged. No passwords, data, deployments, commits or pushes.
- Note: remote migration version `20261112133809` differs from the local file prefix `20261112000001`; align before any future
  `supabase db push` (do not re-push this migration).
- **Next (needs separate approval): owner sets role passwords and seeds; then live D-07/A-05/A-09 and pooler tests.**

## 7D-1 seeding preparation (2026-11-12)
- Owner reports the database (postgres) password is set; app-role passwords not yet set.
- Finding: committed `webapp_qa` A-05/A-09 use `SET LOCAL ROLE webapp_api/engine_api`; on Supabase `postgres` holds only
  ADMIN (set_option false) on those roles, so the gates would report false failures; it can SET to anon/authenticated/service_role.
  `--db` also exposes the URL on the command line.
- Added (untracked, uncommitted): `apps/web/supabase/set_remote_env.ps1` (hidden prompts, URL-encoded pooler URLs in session env
  only) and `apps/web/supabase/live_checks.py` (`ping`, `set-passwords` sending client-computed SCRAM-SHA-256 verifiers so no
  plaintext reaches the SQL editor history or logs, `checks` = D-07 + provenance/frozen hashes + holdout boundary + A-05 + A-09 with
  REAL pooler logins for the app roles; results to `reports/webapp/phase7d/live_db_checks.json`, errors reduced to SQLSTATE).
- Validated locally: checks OVERALL PASS (655,711 rows, 0 boundary leaks, 30 probes, rate limiter as designed); SCRAM verifier
  login works and wrong password is rejected (throwaway local role, dropped). Tracked tree unchanged.
- Waiting for the owner to run the step-by-step sequence; Claude then verifies read-only via the connector.

## 7D-1 TLS investigation (2026-11-12) — before any mutation
- Owner ping: connected as postgres, `ssl=false`, PING FAIL. Nothing was mutated (no set-passwords, no seed).
- Root cause: **false negative**. The check read `pg_stat_ssl` for `pg_backend_pid()`, which behind Supavisor describes the
  pooler-to-Postgres backend link, not the client link. The URI already enforced `sslmode=require` (libpq refuses plaintext).
- Independent client-side evidence (OpenSSL STARTTLS, no credentials): both `aws-0`/`aws-1-eu-central-1.pooler.supabase.com`
  on 5432 and 6543 negotiate **TLSv1.3**; leaf `CN=*.pooler.supabase.com` ← Supabase Intermediate 2021 CA ← Supabase Root 2021 CA
  (private CA, not in public trust stores).
- Fix (no TLS weakening): verdict now from libpq's client connection (`ssl_in_use` + sslmode in {require, verify-ca,
  verify-full} + enforced `ssl_min_protocol_version=TLSv1.2`); `pg_stat_ssl` kept as informational "backend link".
  TLS is now enforced in `ping`, `set-passwords` and every `checks` connection (new `client_tls` gate). Optional stronger
  mode: `verify-full` with the Supabase CA certificate downloaded from the dashboard.
- Regression tests `apps/web/supabase/test_live_checks.py`: 14/14 PASS (verdict matrix, the pooled false-negative case,
  insecure modes refused, local server never counted as TLS, real-pooler verify-full handshake + host-name mismatch rejected
  using a non-existent tenant — no login to the project).
- Next: owner re-runs `set_remote_env.ps1` (new TLS query) and `ping`.

## Blockers
- None for P-2. Deployment risks: out-of-root package install on Vercel, cold start, bundle size (verified only at P-3).

## 7D-1 completion (2026-11-12)
- Owner run (`live_checks.py checks`, 14:17 UTC): OVERALL PASS — D-07 (655,711 rows, provenance = frozen hashes), holdout
  boundary 0, A-05 30 probes, A-09 (webapp_api allowed; engine_api/anon 42501; bad bucket P0001), pooler logins for both roles
  on 6543 (statement_timeout 5s), client TLS `tls-encrypted sslmode=require min=TLSv1.2` on all three connections.
  Evidence `reports/webapp/phase7d/live_db_checks.json` (no connection strings or passwords: scanned).
- Claude independent read-only verification (connector):
  - 21 tables: all 20 counts equal the manifest exactly (total 655,711); `ops.rate_limits` 0.
  - Provenance: export 2026-11-12.1, git 987e27f…, plan 63efc59e…, execution b55ba4a0…, selection a71ab187…, ledger fa2af529…,
    Phase 6 manifest 047d9983…, curated M5 b8499988…, `final_holdout_targets_read=false`.
  - Boundary: M5 test_start 2016-04-25, max history 2016-03-27, max actual/forecast/validation_end 2016-04-24; Store Item
    2017-12-04 vs 2017-11-05 / 2017-12-03. 0 rows on/after test_start; 0 history after origin; 0 actuals outside window.
  - Coverage: 500 Store Item + 300 curated M5 series.
  - Size: database 148.6 MB (142 MiB), app schema 130 MiB (≈137 MB) — 30% of the 500 MB Free limit.
  - Security advisors: only INFO `rls_enabled_no_policy` on `ops.rate_limits` (intentional).
  - `semester-planner` unchanged. Tracked `qa_data_results.json` byte-identical to its pre-seed backup.
- Remaining security note: production TLS mode is `require` (encrypted, server not authenticated); `verify-full` available.

## 7D-2 P-1 local security checkpoint (2026-11-12)
- Engine dependencies: fastapi 0.162.0, starlette 1.10.0 (fixes the 5 Starlette CVEs); full runtime closure pinned in
  `apps/engine/pyproject.toml` (18 packages incl. new transitive opentelemetry-api 1.45.2), resolved in a clean Python 3.14
  venv, `pip check` clean; installed == pinned for all 18; OSV: 0 known vulnerabilities.
- Engine TLS guard (`engine_service/data.py`): remote database URLs must use sslmode require/verify-ca/verify-full and a TLS
  floor >= 1.2; otherwise generic 503 `not_configured` without connecting or echoing the URL.
- Web security headers in `apps/web/next.config.ts` (minimal non-breaking CSP, X-Frame-Options, nosniff, Referrer-Policy,
  Permissions-Policy, COOP; X-Powered-By removed); verified on pages and API routes of the production build.
- Tests (all executed, none skipped): engine 51/51 (original 37 + 1 insecure-URL end-to-end + 13 TLS-guard unit);
  engine package 23/23 incl. S-02 parity 3,264/3,264 bit-exact (max rel. diff 0.0); web 53/53 (19 real local API via the
  upgraded engine + 34 UI); tsc 0; ESLint 0; next build PASS; browser QA 15/15 page×viewport with headers active (0 overflow,
  0 serious/critical axe, U-05 PASS, live engine parity 2,555/2,772/2,900/1,309 NCU, CSV/PNG, console clean) — evidence
  `reports/webapp/phase7d/browser_p1/browser-qa.json`; TLS regression 14/14; npm audit (prod) 0; Ruff clean.
- Integrity: plan 63efc59e, execution b55ba4a0, selection a71ab187, ledger fa2af529 unchanged; vendored engine identical;
  engineVersion still cedc5a31533772fc; `qa_parity_results.json` regenerated byte-identical.
- Commit hash recorded in the ignored receipt `artifacts/experiments/phase7d_p1_20261112/postcommit.json` (no self-reference).

## 7D-2 P-2 private push (2026-11-12)
- Target `YoussefSaeed1/intelligent-demand-forecasting` (GitHub user = Vercel-connected account; GCM signed in as
  YoussefSaeed1). Anonymous API 404 and anonymous git access refused before and after push; Vercel `search_repo` reports
  `private: true`. Repo empty before push (0 refs).
- Outgoing history scan (13 commits, 745 blobs): no tokens/keys/private keys, no real connection strings (templates and
  placeholders only), author emails are users.noreply.github.com, largest 1.5 MB, no CSV/Parquet/raw data/.env/Kumo.
- Pushed `main` only (`--no-tags`); remote has exactly `refs/heads/main` = `8c54c3cdeec021c513419d4f59020fb2198a54b1`;
  local tracks origin/main, 0 ahead/behind.

## 7D-2 P-3 engine project (2026-11-12, in progress)
- Created `idf-engine` with `create_project` (link only; `create_git_project` would deploy before secrets exist).
- Team default Deployment Protection applied: Vercel Authentication on **all deployments except custom domains**, so the
  production `*.vercel.app` URL is behind a Vercel login and the web server cannot reach it without a bypass.
- Waiting for owner: protection decision (A: keep protection + Protection Bypass for Automation header from the web server;
  B: Standard protection, public production alias guarded by X-Engine-Key), and Production-only env vars
  `ENGINE_DATABASE_URL` (engine_api, port 6543, `sslmode=require&ssl_min_protocol_version=TLSv1.2`) and `ENGINE_SHARED_KEY`.

## 7D-2 P-3 deployment (2026-11-12)
- Pre-checks: env `ENGINE_DATABASE_URL`, `ENGINE_SHARED_KEY` type sensitive, target production only (values not read);
  Vercel Authentication enabled (scope `all_except_custom_domains`).
- Deployment `dpl_5yubMyUoFsNF3RWwS8gMZY8niHzA`: READY; commit `8c54c3c`; region fra1; runtime python3.14 (log: "Using Python
  3.14 from apps/engine/pyproject.toml", uv 0.13.5); out-of-root `packages/inventory_core` installed; build 16 s. Aliases:
  `idf-engine.vercel.app` (production domain), `idf-engine-youssefsaeed206-3245s-projects.vercel.app`, git-main alias.
- Versions: installed from exact `==` pins (uv fails on any mismatch) → fastapi 0.162.0 / starlette 1.10.0 by construction;
  the build log does not list versions. Bundle size NOT MEASURED (VERCEL_ANALYZE_BUILD_OUTPUT not set).
- Vendored engine in production: `/health` engineVersion `cedc5a31533772fc` = SHA-256 of the deployed engine.py + design.py,
  identical to local.
- Anonymous checks (Claude, no secrets): deployment URL → 401 on /health and /simulate (Vercel Authentication);
  **production domain `idf-engine.vercel.app` → /health 200 publicly** (Standard-protection semantics exempt production
  domains). Well-formed /simulate without key or with a wrong key → 401 in ~0.3 s; 9 kB body → 413; /docs, /openapi.json,
  /redoc → 404. Malformed bodies → 400 before the key check (pre-auth validation; minor information exposure).
- Runtime logs: request_id/path/status/ms only; no secrets, URLs or bodies. A few Vercel-internal GET / probes on the
  deployment URL logged region sfo1; all production-domain requests ran in fra1.
- Findings: F-P3-1 production domain not covered by Vercel Authentication (fix: scope "All Deployments", free on all plans;
  needs owner approval; web must then send the bypass header). F-P3-2 pre-auth body validation (optional code fix).
- Owner-run checker `tools/phase7d/live_engine_checks.py` (hidden prompts; dry-run vs local: all gates PASS except E-02,
  which needs real Vercel protection).

## 7D-2 P-3 production failure — root cause (2026-11-12)
- Owner run: E-01, E-02, E-03 PASS; E-04 FAIL (unknown_series 500); E-05 FAIL (500); E-06 FAIL (no result); E-07 measured
  failing requests.
- Vercel runtime logs (Hobby retains 1 h): 7 × `/simulate` errors 15:12:42–15:12:57Z, all `unhandled error` tracebacks from
  the route; full-text search: all 7 contain `OperationalError` and `password authentication failed for user "engine_api"`
  and the pooler host; 0 contain "Tenant or user not found", timeout, network-unreachable or DNS errors; 0 contain
  `postgresql://` or `sslmode` (no URL leak). 7 = first simulate + unknown_series + 5 warm (all DB-reaching calls).
- Supabase logs (read-only): 14:14Z `alter role engine_api with password '{REDACTED}'` (7D-1 SCRAM); 14:17Z successful
  engine_api pooler logins (7D-1 live checks PASS); 15:12Z 17 × Supavisor `Exchange error: password authentication failed
  for user "engine_api"`. No role/password change after 14:14.
- Conclusion: network, DNS, TLS, pooler routing and tenant resolution all work; the password inside the Vercel
  `ENGINE_DATABASE_URL` differs from the engine_api password. Category: deployment configuration (secret value), not the
  API logic, database permissions, TLS or runtime.
- Shared root cause: `/simulate` connects before any series lookup, so a failed login yields 500 for every DB-reaching
  request (unknown_series included). Reproduced locally with a wrong local password: valid and unknown series → 500.
- Code hygiene gap: `psycopg.OperationalError` is unhandled → generic 500 plus a full traceback (incl. pooler host) in logs.
- Added owner tool `tools/phase7d/build_engine_db_url.py` (hidden prompt, URL-encodes, TLS guard, one real login, copies to
  clipboard). Proposed patch (not applied): OperationalError → 503 `database_unavailable` with one-line log; key check
  before body validation (F-P3-2); 2 tests.
- Security: a secret appeared in the conversation → owner rotates `ENGINE_SHARED_KEY` (and the bypass secret if unsure).

## 7D-2 P-3 remediation (2026-11-12)
- Owner: rebuilt `ENGINE_DATABASE_URL` with `tools/phase7d/build_engine_db_url.py` (LOGIN OK, engine_api, client TLS,
  validation_origins=8) and replaced it in Vercel Production (env updatedAt 15:24:50Z); `ENGINE_SHARED_KEY` edited 15:15:39Z
  (metadata only; rotation of the exposed value confirmed by the owner before push); protection scope All Deployments
  (anonymous production /health and /simulate → 401).
- Patch (owner-approved): engine key checked in the middleware before body validation (constant time; handler re-checks);
  `psycopg.OperationalError` → 503 `database_unavailable` with a one-line log (request_id, SQLSTATE); unexpected errors log
  the exception class only (no message/traceback that could carry host names). Frozen engine, planner and data access unchanged.
- Tests: engine 56/56 (51 + 5 new regression cases: key-before-validation ×3, DB login failure → 503 for valid and unknown
  series, class-only error logging); engine package 23/23 with S-02 3,264/3,264 bit-exact (max rel. diff 0.0); web API 19/19
  via the patched local engine; Ruff clean; vendored engine identical; frozen evidence unchanged.

## 7D-2 P-3 E-06 diagnosis (2026-11-12)
- Deployment `dpl_BzZ4a8sXWD9ARo6QXdvhrw2PwxnU` (commit `e170d98`, fra1) live run 15:36:49Z: E-01..E-05 PASS (simulate 200,
  unknown series 404), E-07 first 745.7 ms / warm median 417.2 ms (client-side; function time 117-257 ms), E-06 FAIL
  (`bit_exact_vs_local_engine=false`, `saved_phase5_mismatches={}`).
- Root cause: Supabase's postgresql.conf sets `extra_float_digits = 0` (pg_settings source "configuration file",
  boot_val 1, reset_val 0); no role/database override. psycopg receives `double precision` as TEXT, so the engine parses
  15-significant-digit strings (e.g. historical_mean56 27.9285714285714 instead of 27.928571428571427). Local Postgres uses
  the default 1 (exact shortest round-trip).
- Stored data are bit-identical to the local reference (md5 of raw float8send bits over all rows): forecasts
  8ac4ba74…, validation_actuals f4f8b4ef…, series_origin_mean56 74053a84…, inventory_series_base d41169dc… (equal on both).
- E-06 case store_item|1:11 origin 1: 1 differing JSON path (`historicalMean56`, rel 1.0e-15); 55/84 forecast inputs
  altered in the last digits; all integer results equal, hence `saved_phase5_mismatches={}`.
- Materiality (local reproduction with `-c extra_float_digits=0`, all 3,200 curated series-origin pairs, base scenario,
  4 policies, 535 s): 2,701 pairs differ somewhere; **182 pairs (5.7%) differ beyond the echoed mean** — integer results
  change via ceil boundaries (summary.total_cost 680 policy results, initial_on_hand 664, window_turnover 664, daily stock and
  holding cost). Scientifically material; the strict bit-exact check is justified.
- E-08 PASS: 14 info lines on the active deployment, 0 errors/warnings, no credentials/URLs/headers/tracebacks; 401/413
  early returns are not logged (observability gap, not a leak).
- Proposed fix (applied, see below): read engine inputs in psycopg binary result format (exact IEEE-754, independent of server
  float settings) + regression tests + log early rejections; web postgres.js text floats to be addressed in 7D-3.

## 7D-2 P-3 lossless float-transport remediation (2026-11-12, approved)
- `engine_service/data.py`: all four input queries use psycopg binary result format (`binary=True`), so `double precision`
  arrives as exact IEEE-754 bits regardless of server `extra_float_digits`. No engine, inventory-maths or data change.
- `engine_service/app.py`: early 401/413/503 rejections now emit the same one-line structured log (id, path, status, ms only).
- Sweep `tools/phase7d/float_transport_sweep.py` (local reference DB, 3,200 pairs, base scenario, 4 policies, 712 s):
  defect path (text, `extra_float_digits=0`) alters inputs on 3,200 pairs, any output on 2,701, material outputs on 182
  (107 store_item, 75 m5); fixed path (binary, same lossy session) **0 differences** in inputs and outputs, bit for bit.
  Evidence: `reports/webapp/phase7d/float_transport_sweep.json` (overall PASS).
- Regression tests `apps/engine/tests/test_float_transport.py` 10/10, none skipped: text+`extra_float_digits=0` reproduces
  the defect (27.9285714285714 vs 27.928571428571427); binary reads preserve every stored bit of means, forecasts, actuals;
  production loader lossless on a lossy session; 4 known affected pairs (store_item|1:11@2, store_item|1:113@2,
  m5|4:CA_1FOODS_3_764@3, m5|4:CA_1HOBBIES_1_371@2) confirmed defective on text and bit-exact on binary.
- Live checker strict: E-06 compares production vs local engine bit-exactly (struct-packed float equality, differing JSON
  paths listed, no tolerance) on the base pair plus the 4 affected pairs, and saved Phase 5 fields at full precision.
  Local dry run: 5/5 pairs bit-exact, 0 saved mismatches.
- Verification: engine 69/69 (none skipped); engine package 23/23 with S-02 3,264/3,264 bit-exact (max rel. diff 0.0);
  vendored engine identical; frozen evidence (plan/execution/selection/ledger) unchanged; Ruff clean; web API 19/19 via
  the patched local engine. The pre-fix 15:36Z run (E-06 FAIL) is preserved in commit `9a13fab`; the file now holds the accepted 16:14Z run.
- Web (postgres.js) float precision is a known 7D-3 risk, documented in the runbook; frontend unchanged.

## 7D-2 P-3 final production verification and acceptance (2026-11-12)
- Deployment `dpl_7qGSEBPMyeqvJnifA5w6fuUtcorG`: commit `9a13fab`, READY, function region fra1, Python 3.14, aliases
  `idf-engine.vercel.app` + team/git-main aliases. Project protection unchanged: Vercel Authentication `all`, password
  protection and trusted IPs off. Env: `ENGINE_DATABASE_URL`, `ENGINE_SHARED_KEY` sensitive, Production only.
- Owner run 16:14:23Z (`reports/webapp/phase7d/live_engine_checks.json`, overall **PASS**):
  - E-01 health 200, engineVersion `cedc5a31533772fc`, keyConfigured true.
  - E-02 deployment URL and production domain without bypass 401; with bypass 200.
  - E-03 wrong and missing key 401. E-04 400/400/404/400/413 as expected. E-05 200.
  - E-06 5/5 pairs bit-exact vs the local reference engine (base store_item|1:11@1 + 4 known affected pairs), 0 differing
    paths, `saved_phase5_mismatches={}`; totals selected_ml 2555, moving_average_28 2772, seasonal_naive 2900,
    fixed_reorder_point 1309.
  - E-07 first simulate 761.1 ms, warm 380.7/367.8/378.7/357.2/355.9 ms (median 367.8), health 264.9 ms (client-side
    from Egypt; function time 114-142 ms warm, 269.6 ms first).
- E-08 PASS: 19 info lines for the run (16:14:23-16:14:30Z), 0 warnings/errors, `get_runtime_errors` empty. Every line is
  `{request_id,path,status,ms}` only: no keys, URLs, hosts, headers, query strings, bodies or tracebacks. Early 401 ×2 and
  413 now logged (observability gap closed). Two unrelated `GET /` 404 lines at 16:11:53Z are Vercel's post-deploy probe.
- **Verdict: P-3 ACCEPTED; 7D-2 COMPLETE.**

## 7D-3A Next.js production readiness (2026-11-12, local only)
- Engine client (`apps/web/src/lib/server/engine.ts`, `env.ts`): server-only `VERCEL_PROTECTION_BYPASS_SECRET` sent as
  `x-vercel-protection-bypass` on /simulate and /health; `x-engine-key` on /simulate only. Remote `ENGINE_URL` must be
  HTTPS without credentials/query, and the bypass secret is mandatory for any non-loopback engine. `redirect: "manual"`
  (Vercel login redirects would otherwise forward custom secret headers cross-origin). Engine 401/403 → 502, 503 → 503,
  timeout → 504, network/other → 502, all `engine_unavailable` with the precomputed-results message (UI fallback
  unchanged); one structured warning line per failure (request id, reason, engine status only).
- Logging: `handle()` no longer logs `error.message` (driver errors can carry hosts/users): class, SQLSTATE/errno code
  and, for configuration errors, the variable name only.
- Float precision: postgres.js 3.4.7 has no binary result format (Bind sends zero result-format codes). Fix: every
  repository read runs in `readExact` = `BEGIN READ ONLY` + `set_config('extra_float_digits','3', true)`. Verified on
  PostgreSQL 17.11 (Supabase is 17.11, setting context `user`): lossy session 27.9285714285714 → 27.928571428571427;
  setting resets at commit (no pooled-session leak). No role/database setting changed.
- DB URL: `ssl_min_protocol_version=TLSv1.2` in the URL was forwarded as a startup parameter → FATAL 55P02 (reproduced
  locally); now applied as Node TLS `minVersion`; remote `sslmode=disable|allow|prefer` rejected.
- Tests: web 88/88, 0 skipped (UI 34; API 19; precision 24 incl. all 68 float8 columns of schema `app` bit-identical to
  float8send on a forced `extra_float_digits=0` session, 13 endpoints byte-identical exact vs lossy, API values vs the
  SHA-256-verified export bit for bit; engine-client 11 with a real local engine and cross-origin redirect target).
  Mutation checks: removing set_config fails 18 precision tests; following redirects fails 2; dropping the bypass
  header fails 2. TypeScript, ESLint clean; `next build` PASS without secrets; client bundle contains no secret names,
  header names or DB code. Browser QA on `next start` with a lossy DB session: 15/15 page×width PASS (no overflow, 0
  serious/critical axe, copy gate PASS, 0 console errors), real engine run equals Phase 5 totals.
- Unchanged: engine 69/69; vendored engine identical; frozen evidence UNCHANGED; no Supabase or Vercel change.
- `npm audit --omit=dev` 0. Full audit: 9 dev-only (vitest 4.0.8 critical advisories for the Vitest UI/browser server,
  not used; typescript-eslint/minimatch moderate); not deployed.
- `tools/phase7d/live_engine_checks.py` deployment URL is now supplied per run via `ENGINE_DEPLOYMENT_URL` (validated).
- Pre-push (approved): `idf-engine` Ignored Build Step set to skip only when no engine build input changed (runbook
  "Engine build guard"); verified locally against this commit (skip), `e170d98` (build), empty/unknown SHA (build).
  Database URL contract asserted: postgres.js startup parameters for the production URL format are `application_name`
  only.

## 7D-3A closure verification (2026-11-12)
- `origin/main` = local HEAD `36da979` (fetched; zero diff); repository private (anonymous GitHub API 404); no tags pushed.
- `idf-engine`: push created `dpl_7AsK3nrJdTUdFf3MVagG21RAAfjP` for `36da979`, CANCELED by the Ignored Build Step
  ("returned exit code 0", no aliases). Alias `idf-engine.vercel.app` → `dpl_7qGSEBPMyeqvJnifA5w6fuUtcorG` (`9a13fab`),
  READY. Anonymous `/health` on the production domain and deployment URL 401; anonymous POST 302 to Vercel login.
  Note: the connector's project `domains` field mirrors the latest deployment record (the canceled one), not the alias.
- **Verdict: 7D-3A CLOSED.**
