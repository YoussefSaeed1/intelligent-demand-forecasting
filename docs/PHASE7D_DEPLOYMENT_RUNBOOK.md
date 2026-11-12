# Phase 7D deployment runbook

Each stage needs explicit owner approval and stops at its gate. **Secrets never pass through Claude:** the owner generates
passwords and keys locally, enters them in the Supabase SQL editor or the Vercel dashboard, and keeps them in a password manager.
Claude may perform approved non-secret operations through the connectors and read-only verification queries.

Generate each secret locally: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## 7D-1 Supabase provisioning

1. **Claude, after approval D-1:** create the project `idf-research-explorer` in the free org, region `eu-central-1`. Confirm the
   connector cost prompt shows $0. Record the project ref (non-secret).
2. **Owner:** Dashboard → Database → set a strong database password. Keep it to yourself.
3. **Claude:** apply `apps/web/supabase/migrations/20261112000001_app_schema.sql` once via `apply_migration`. Do not retry blindly;
   see the rollback plan. Then confirm through `list_tables`, read-only, that schemas `app` and `ops` exist, with 20 app tables plus
   `ops.rate_limits`.
4. **Owner, SQL editor:**
   `alter role webapp_api with password '<A>'; alter role engine_api with password '<B>';`
   Leave Data API exposed schemas unchanged; do not add `app` or `ops`.
5. **Owner, laptop, seeding through the session pooler on IPv4.** Get the session-pooler URI for `postgres.<ref>` from Connect.
   ```powershell
   $env:WEBAPP_OWNER_DATABASE_URL = '<session pooler URI, port 5432>'
   .\apps\engine\.venv\Scripts\python.exe apps\web\supabase\seed_database.py
   .\apps\engine\.venv\Scripts\python.exe src\intelligent_demand\bi\webapp_qa.py --db $env:WEBAPP_OWNER_DATABASE_URL --only D-07,A-05,A-09
   Remove-Item Env:WEBAPP_OWNER_DATABASE_URL
   ```
   The seed verifies the 20 CSV hashes against `reports/webapp/export_manifest.json`, then truncates, COPYs and checks counts in one
   transaction.

   `--only` merges its results into the tracked `reports/webapp/qa_data_results.json`. Either copy that file aside first, or record
   the live results in a new `reports/webapp/phase7d/` file and restore the tracked file with `git checkout -- reports/webapp/qa_data_results.json`.
6. **Claude, read-only:**
   - `execute_sql` for row counts against the manifest (655,711 rows), the `app.provenance` export version `2026-11-12.1`, and
     `pg_database_size`.
   - `get_advisors` for security and performance.
7. **Owner:** in Connect, note the **transaction-pooler** host for `webapp_api.<ref>` and `engine_api.<ref>` (port 6543). Verify both
   logins with a single `select 1` (owner terminal).

**Gate 7D-1:** counts and provenance match; D-07, A-05 and A-09 pass live; both custom roles authenticate through Supavisor;
database under 200 MB.

## 7D-2 Engine on Vercel (requires D-2, D-3 and R-1 merged)

1. **Claude:** create project `idf-engine`.
   - Framework: FastAPI (Python); root directory `apps/engine`; include files outside the root directory **on**.
   - Function region `fra1`; Python from `requires-python` (3.14).
2. **Owner, dashboard → Environment Variables, Production only:**
   - `ENGINE_DATABASE_URL`: transaction-pooler URI for `engine_api.<ref>`, port 6543, ending
     `?sslmode=require&ssl_min_protocol_version=TLSv1.2`. Since P-1 the engine refuses any remote URL without `sslmode`
     of `require`, `verify-ca` or `verify-full` (generic 503 `not_configured`).
   - `ENGINE_SHARED_KEY`: new 48-byte secret.
   - Optional: `ENGINE_MAX_CONCURRENCY=4`, `VERCEL_ANALYZE_BUILD_OUTPUT=1` for the first build.
3. Deploy the production build from the approved commit. Read the build log for the function size and the bundled
   `intelligent_demand/inventory/engine.py`.
4. **Verify (QA plan E-01..E-08):**
   - `/health` returns 200 with `engineVersion` `cedc5a31533772fc` and `keyConfigured: true`.
   - Requests without the key, or with a wrong key, return 401/403.
   - The parity case equals the saved Phase 5 values exactly.
   - Measure cold and warm latency.

## 7D-3 Web on Vercel

1. **Claude:** create project `idf-web`: framework Next.js; root `apps/web`; install `npm ci`; build `next build`; Node 24.x;
   region `fra1`.
2. **Owner, Production only:**
   - `WEBAPP_DATABASE_URL`: `webapp_api.<ref>` transaction pooler, port 6543, with
     `?sslmode=require&ssl_min_protocol_version=TLSv1.2` (postgres.js also enforces `ssl: "require"` for non-local hosts).
   - `ENGINE_URL`: the engine **production domain** `https://idf-engine.vercel.app`, not a per-deployment URL.
   - `ENGINE_SHARED_KEY`: the same value as the engine.
   - `VERCEL_PROTECTION_BYPASS_SECRET`: the engine project's Protection Bypass for Automation secret (the engine stays
     protected for All Deployments). Required for any non-loopback `ENGINE_URL`; missing → generic 503 `not_configured`.
   - `RATE_LIMIT_SALT`: new secret.
   - Optional: `RATE_LIMIT_SIMULATE_PER_MINUTE`, `RATE_LIMIT_SIMULATE_PER_DAY`, `RATE_LIMIT_READ_PER_MINUTE`.
3. Deploy, then run the QA plan sections W and S.

**Float precision in the web API (found in 7D-2 P-3; fixed locally in 7D-3A, pending Supabase verification).**
Supabase's server configuration sets `extra_float_digits = 0`; postgres.js 3.4.7 always requests TEXT results (its Bind
message sends zero result-format codes, so binary float transport is not available). Every read in
`apps/web/src/lib/server/repository.ts` now runs through `readExact` (`db.ts`): a `READ ONLY` transaction whose first
statement is `select set_config('extra_float_digits', '3', true)`. PostgreSQL 17.11 (same version locally and on
Supabase; the setting has context `user`) then emits shortest exact round-trip text, which JavaScript parses to the
identical double. The setting is transaction-scoped (compatible with the transaction pooler; verified not to leak).
Regression tests: `apps/web/tests/precision.test.ts` (whole-database float8send bit comparison on a forced
`extra_float_digits=0` session; byte-identical API responses exact vs lossy; API values vs the hash-verified export).

**Database URL (fixed in 7D-3A).** postgres.js forwards unknown URL parameters to the server as startup parameters, so
`ssl_min_protocol_version=TLSv1.2` made PostgreSQL reject the connection (55P02, reproduced locally). `db.ts` now
consumes `sslmode` / `ssl_min_protocol_version` as Node TLS options (remote: TLS always, minimum TLS 1.2, `require`
semantics as for the engine) and rejects `sslmode=disable|allow|prefer` for remote hosts.

**`WEBAPP_DATABASE_URL` contract (web, postgres.js):**
`postgresql://webapp_api.<ref>:<url-encoded password>@<transaction-pooler host>:6543/postgres?sslmode=require&ssl_min_protocol_version=TLSv1.2`
- User `webapp_api.<ref>` (Supavisor tenant form), port 6543 (transaction mode; the client uses `prepare: false`).
- `sslmode` and `ssl_min_protocol_version` are consumed by `connectionOptions` and never sent as startup parameters (the
  client's startup parameters are only `application_name`, asserted in `precision.test.ts`). TLS 1.2 minimum is enforced
  by Node's `tls.connect({ minVersion: "TLSv1.2" })`; remote hosts always use TLS even without `sslmode`.
- Any other query parameter WOULD be forwarded as a server startup parameter: add none.

**Engine build guard (7D-3A push).** Vercel's native "skip unaffected projects" needs npm/yarn/pnpm/Bun workspaces; this
repository has none (Python engine), so every push counted as a global change and would rebuild `idf-engine`. The engine
project's Ignored Build Step is therefore:
`git diff --quiet "$VERCEL_GIT_PREVIOUS_SHA" HEAD -- :/apps/engine :/packages :/pyproject.toml :/vercel.json :/.vercelignore`
It skips (exit 0) only when none of the engine's build inputs (`apps/engine/**`, `packages/**` incl. the uv path source
`packages/inventory_core`, root config) changed since the last successful deployment. Empty or unknown previous SHA
(first deploy, or more than 10 commits since, beyond Vercel's depth-10 clone) exits 128 and BUILDS (fail-safe).
Redeploy/promote from the dashboard can bypass it ("Use project's Ignore Build Step" checkbox).

**7D-3B gate (before go-live):** after deployment, verify through the Supavisor transaction pooler that `/api/v1`
numeric responses equal the local reference byte for byte (W gates), and that a production simulate passes the engine's
Vercel protection with the bypass secret.

## 7D-4 Production verification

Run the full [production QA plan](PHASE7D_PRODUCTION_QA_PLAN.md). Write `docs/PHASE7D_DEPLOYMENT_RECORD.md` with URLs, versions,
measured latencies, quota usage and anything NOT VERIFIED. A live URL with every critical flow passing is the acceptance criterion;
a successful build alone is not.

## Environment variable names (no values)

- Web: `WEBAPP_DATABASE_URL`, `ENGINE_URL`, `ENGINE_SHARED_KEY`, `VERCEL_PROTECTION_BYPASS_SECRET`, `RATE_LIMIT_SALT`,
  optional `RATE_LIMIT_*`.
- Engine: `ENGINE_DATABASE_URL`, `ENGINE_SHARED_KEY`, optional `ENGINE_MAX_CONCURRENCY`.
- Laptop only (transient): `WEBAPP_OWNER_DATABASE_URL`; `ENGINE_DEPLOYMENT_URL` (non-secret, for
  `tools/phase7d/live_engine_checks.py`).

Never prefix any of these with `NEXT_PUBLIC_`.
