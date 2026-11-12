# Phase 7D-0: pre-deployment readiness report

Date 2026-11-12. Read-only investigation: no cloud resource, database, secret, deployment, commit or push was created or
changed. Companion documents: [runbook](PHASE7D_DEPLOYMENT_RUNBOOK.md), [production QA plan](PHASE7D_PRODUCTION_QA_PLAN.md),
[rollback plan](PHASE7D_ROLLBACK_PLAN.md).

**Verdict: READY FOR CONTROLLED 7D-1 DEPLOYMENT (Supabase).** Two items must be resolved before 7D-2 (engine): the Starlette
advisories (R-1) and the deployment-source decision (D-2).

## 1. Local readiness (verified)

| Check | Result |
|---|---|
| Git | HEAD `7000c048900b315e131ba8ccce3350c7dd7e4140` on `main`; tracked tree clean; only `experiments/` (Kumo) untracked; no remote configured |
| Frozen evidence | plan `63efc59e`, execution `b55ba4a0`, selection `a71ab187`, ledger `fa2af529` recomputed directly; vendored engine `identical` |
| Backup | `C:/Project_Backups/Demand_Forecasting_Phase7C_WebApp_verified_20261112`: `sha256sum -c` 208/208 OK (read-only) |
| Build reproducibility | Verified at checkpoint from a fresh clone: `npm ci` (461 packages), `next typegen`, tsc, `next build`, 34/34 UI tests. Next.js generates `LayoutProps` types during `next build`, so Vercel needs no extra step |
| Secret scan (all 701 tracked files) | No tokens, keys, private keys, cloud connection strings or credential files. Only loopback-only placeholders for the embedded test DB |
| npm (production deps) | `npm audit --omit=dev`: 0 vulnerabilities |
| Python runtime deps (OSV) | 15 of 16 packages clean; **starlette 0.50.0 (via fastapi 0.121.3): 5 CVEs** (2 high, 2 moderate, 1 low); see R-1 |
| Python 3.14 | Supported by Vercel (3.12 default, 3.13, 3.14). manylinux x86_64 cp314 wheels exist for numpy 2.5.4, pandas 3.1.1, psycopg-binary 3.2.13, PyYAML 6.0.3 and pydantic-core |
| Engine bundle size | Installed runtime dependencies ≈ 185 MB (numpy 35, pandas 78; the venv's 287 MB includes test-only pyarrow 91 MB). Python limit is 500 MB uncompressed: comfortable margin. Final size is only known from the Vercel build log (`VERCEL_ANALYZE_BUILD_OUTPUT=1`) |
| Engine exposure | OpenAPI/docs disabled; constant-time `X-Engine-Key` check; 503 if the key is unset or shorter than 32 characters; 8 kB body cap; concurrency semaphore; no CORS (browsers cannot read cross-origin responses; the web server calls it server-to-server) |
| Migration | Creates roles `app_reader` (nologin), `webapp_api`, `engine_api` (login, no password); revokes `public`, `anon`, `authenticated`; RLS SELECT policies; one SECURITY DEFINER function with a pinned `search_path`. No extension, superuser or `ALTER SYSTEM` statement |

### Remediation and recommendations

- **R-1 (required before 7D-2): Starlette advisories.** CVE-2026-54283 (form-limit DoS, high), CVE-2026-48818 (Windows
  StaticFiles UNC, high), CVE-2026-48710 (Host header path poisoning, moderate), CVE-2026-48817 (HTTPEndpoint method dispatch,
  moderate) and CVE-2026-54282 (hostname poisoning, low); all fixed by starlette ≥ 1.3.1.
  - **Exposure is low.** The engine never calls `request.form()`, uses no StaticFiles or HTTPEndpoint, makes no path- or
    host-based security decision, and runs on Linux.
  - **Why it still blocks.** fastapi 0.121.3 pins `starlette<0.51`.
  - **Fix.** Upgrade fastapi to a current release (0.162.5 requires `starlette>=0.46`) and pin starlette ≥ 1.3.1. Rerun the
    engine's 37 service tests, the 3,264-episode parity suite and the 19 API tests. The engine mathematics are unaffected; this
    needs an owner-approved commit.
- **R-2 (recommended): Python lock.** No `uv.lock` exists (uv is not installed locally). Direct dependencies are pinned; transitive
  ones (starlette, anyio, python-dateutil, tzdata and others) resolve at build time. Pin the tested versions as constraints in
  `apps/engine/pyproject.toml` within the same R-1 commit. numpy and pandas, which determine the numeric results, are already pinned.
- **R-3 (recommended hardening):** add security response headers to `next.config.ts`
  (`X-Frame-Options`/`frame-ancestors`, `Referrer-Policy`, `Permissions-Policy`); HSTS is applied by Vercel. Include in the R-1 commit.

## 2. Vercel (read-only inspection)

- **Team:** `youssefsaeed206-3245's projects` (`team_CNXls9qDvhkHpuAhliQxEcPs`), the only accessible team. The connector does not
  expose the billing plan; it was previously observed as Hobby.
- **Projects:** `youssef-portfolio`, `court-iron`, `semester-planner`; there is no `idf-web` or `idf-engine` name conflict. Hobby allows
  200 projects, so two more fit. Domain availability for the `*.vercel.app` names is checked at creation.
- **Runtime facts** (docs, 2026-11-12):
  - Python: 3.14 supported; FastAPI found via `[tool.vercel] entrypoint = "main:app"`.
  - Limits: 500 MB uncompressed Python bundle; Hobby 2 GB / 1 vCPU and 300 s maximum duration; 4.5 MB request/response body.
  - Region: single region (default `iad1`; set `fra1`).
  - Hobby usage: 4 Active-CPU-hours and 1,000,000 invocations per month (shared across the whole team); 100 deployments per day;
    1-hour runtime logs; up to 3 WAF custom rules.
  - Exceeding a Hobby limit pauses the feature, with no charge.
- **Request headers:** Vercel overwrites `X-Forwarded-For` and does not forward external IPs (anti-spoofing), so the rate limiter's
  client bucket is trustworthy on Vercel.
- **Unverified until a real build:**
  - Engine install of the out-of-root path dependency `../../packages/inventory_core`. This needs "Include files outside the root
    directory". Fallback: set the engine project root to the repository root with an explicit entrypoint.
  - Final function size and cold-start latency.
  - Whether Deployment Protection defaults on new Hobby projects protect generated deployment URLs only, or also the production
    alias. `ENGINE_URL` must be the engine's production domain.

## 3. Supabase (read-only inspection)

- **Organisation and projects:** org `YoussefSaeed1's Org` (`uxqjykiobncetduzzqrg`), plan **free**. One project, `semester-planner`
  (eu-central-1, Postgres 17.11.0.003, active), which is unrelated and untouched. Free allows 2 active projects, so **one slot is
  available**. Postgres 17.11 matches the local test server.
- **Networking:**
  - The direct connection (`db.<ref>.supabase.co:5432`) is IPv6 on Free; the shared pooler (Supavisor) is IPv4.
  - Vercel functions must therefore use the pooler in transaction mode (port 6543).
  - The owner's laptop should seed through the pooler in session mode (port 5432), because COPY needs a session.
- **Custom roles:**
  - Supabase documents custom login roles through the pooler with username `[role].[PROJECT-REF]` (the Prisma guide creates a
    dedicated user exactly this way).
  - Transaction mode does not support prepared statements; both clients already disable them (postgres.js `prepare: false`,
    psycopg `prepare_threshold=None`).
  - Live authentication of `webapp_api` and `engine_api` through Supavisor remains **unverified** until 7D-1.
- **Quotas (pricing page):** 500 MB database per project, 5 GB egress plus 5 GB cached egress, 1 GB storage; free projects pause after
  1 week of inactivity. The page does not state behaviour on exceeding the database limit or commercial-use terms.
- **Footprint:** measured locally at 146 MB database (137 MB `app` schema), about 29% of 500 MB.
- **Risks:**
  - Supabase's own roles and grants differ from the local stubs. The migration revokes `anon` and `authenticated`, and A-05 must
    be rerun live.
  - Do not add `app` or `ops` to the Data API's exposed schemas.

## 4. Cost assessment

| Item | Status |
|---|---|
| Vercel Hobby, 2 projects | Confirmed free; personal, non-commercial use only (fair-use guidelines). An academic portfolio fits; any commercial use requires Pro |
| Supabase Free, 1 new project | Confirmed free; 2-active-project limit leaves exactly 1 slot. Pausing after 7 idle days makes the site return errors until the owner unpauses it |
| Usage estimate | Each planner run is about 0.4 s CPU, plus about 1–2 s on a pandas cold start. 4 CPU-hours a month (shared with the other team projects) is roughly thousands of runs; ample for a portfolio. Read responses are CDN-cacheable (s-maxage 1 day), which limits Supabase egress |
| Account-specific, not verified | Vercel plan (connector does not show it), current team usage against the shared Hobby quotas, Supabase org spend cap |
| Paid services required | **None** for the approved design. Not used: Supabase IPv4 add-on, dedicated pooler, Vercel Pro, password protection |

Zero cost is not guaranteed permanently: providers may change free tiers, and quota exhaustion pauses service rather than billing.

## 5. Owner decisions

- **D-1:** approve 7D-1, creating the Supabase project `idf-research-explorer` in eu-central-1 on the free org.
- **D-2:** choose the deployment source for 7D-2 and 7D-3. Recommended: a **private** GitHub repository with `main` pushed (reproducible
  builds from `7000c04` plus the R-1 commit). This needs explicit push approval. The alternative is the Vercel CLI from this laptop
  (requires a login token; not installed).
- **D-3:** approve R-1 (plus R-2 and R-3) as one local code commit before 7D-2.
- **D-4:** keep secrets in Production only (Preview deployments run without database or engine and return a 503). Recommended.
- **D-5:** pausing policy. Recommended: unpause before demonstrations, with no keep-alive automation.

## 6. References (official, fetched 2026-11-12)

- Vercel: https://vercel.com/docs/functions/runtimes/python/python-version · https://vercel.com/docs/functions/limitations ·
  https://vercel.com/docs/plans/hobby · https://vercel.com/docs/headers/request-headers ·
  https://vercel.com/docs/frameworks/backend/fastapi
- Supabase: https://supabase.com/pricing · https://supabase.com/docs/guides/database/connecting-to-postgres ·
  https://supabase.com/docs/guides/database/prisma
- Advisories: OSV (api.osv.dev) GHSA-82w8-qh3p-5jfq, GHSA-wqp7-x3pw-xc5r, GHSA-86qp-5c8j-p5mr, GHSA-x746-7m8f-x49c, GHSA-jp82-jpqv-5vv3
