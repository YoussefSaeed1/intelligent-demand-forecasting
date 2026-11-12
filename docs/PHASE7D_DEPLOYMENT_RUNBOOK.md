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
   - `ENGINE_URL`: the engine **production domain**, not a per-deployment URL.
   - `ENGINE_SHARED_KEY`: the same value as the engine.
   - `RATE_LIMIT_SALT`: new secret.
   - Optional: `RATE_LIMIT_SIMULATE_PER_MINUTE`, `RATE_LIMIT_SIMULATE_PER_DAY`, `RATE_LIMIT_READ_PER_MINUTE`.
3. Deploy, then run the QA plan sections W and S.

**Known risk to resolve before 7D-3 deployment: float precision in the web API (found in 7D-2 P-3).** Supabase's server
configuration sets `extra_float_digits = 0`, so every `double precision` value read in text format is rounded to 15
significant digits. The engine was fixed by reading its inputs in binary format. The web app (postgres.js) still reads text:
- Displayed values (2-4 decimals) are unaffected, but metric ratios and NCU means computed in `/api/v1` from rounded
  additive components can differ from the local reference in the last digits.
- The web API tests that reproduce the registry metrics and the post-audit reconciliation could therefore fail or drift
  against Supabase, and any exact comparison with saved values is unsafe.
- Planner results are not affected: simulations run in the engine.
- Proposed fix (7D-3, separate approval): make postgres.js return exact floats, either by setting
  `extra_float_digits = 3` per transaction (`SET LOCAL` inside the query transaction, compatible with the transaction
  pooler) or by binary result transfer. Add a regression test that forces `extra_float_digits = 0` locally and requires
  bit-identical `/api/v1` numeric output. Verify against Supabase before go-live.

## 7D-4 Production verification

Run the full [production QA plan](PHASE7D_PRODUCTION_QA_PLAN.md). Write `docs/PHASE7D_DEPLOYMENT_RECORD.md` with URLs, versions,
measured latencies, quota usage and anything NOT VERIFIED. A live URL with every critical flow passing is the acceptance criterion;
a successful build alone is not.

## Environment variable names (no values)

- Web: `WEBAPP_DATABASE_URL`, `ENGINE_URL`, `ENGINE_SHARED_KEY`, `RATE_LIMIT_SALT`, optional `RATE_LIMIT_*`.
- Engine: `ENGINE_DATABASE_URL`, `ENGINE_SHARED_KEY`, optional `ENGINE_MAX_CONCURRENCY`.
- Laptop only (transient): `WEBAPP_OWNER_DATABASE_URL`.

Never prefix any of these with `NEXT_PUBLIC_`.
