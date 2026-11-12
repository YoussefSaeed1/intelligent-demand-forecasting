# Phase 7D deployment record

Recorded 2026-11-12. All checks below were executed against production unless marked otherwise.

## Public application
- URL: **https://idf-web.vercel.app** (production domain, public).
- Vercel project `idf-web` (`prj_r38MRs59MUsJMhpd7DRV42ABdM8t`): Next.js 16.4.6, root `apps/web`, `npm ci`, `next build`,
  Node 24.x, function region fra1, files outside root OFF, production branch `main`.
- Production deployment `dpl_362iX8C1ZZjJgYAEXPLS4TknU6zL`, commit `36da979`, READY (build ~100 s).
- Protection: Vercel Authentication for **Preview** deployments only; production domain and production deployment URLs
  public (verified 200 anonymously). Preview protection is configured (`ssoProtection.deploymentType=preview`) but NOT
  demonstrated on a built preview: the only preview attempt (`dpl_2dYw3MZ734EwhSKrz9cRFy9BtZsH`) was correctly canceled
  by the web build guard and its URL serves Vercel's "Deployment was cancelled" placeholder (no application, no data).
  The `idf-web-git-main-…` branch alias now points at that placeholder; the production domain is unaffected.
- Production-only environment: `WEBAPP_DATABASE_URL`, `ENGINE_SHARED_KEY`, `VERCEL_PROTECTION_BYPASS_SECRET`,
  `RATE_LIMIT_SALT` (owner-entered, Sensitive), `ENGINE_URL=https://idf-engine.vercel.app` (plain). None `NEXT_PUBLIC_`.
- Ignored Build Step (both projects): exit 1 (build) when the previous SHA is empty or unknown, else `git diff --quiet`
  over the project's inputs (`apps/web` for the web; `apps/engine`, `packages`, root config for the engine). The first
  web deployment exposed that Vercel treats exit 128 as an ERROR, not as "build"; both guards were corrected.

## Engine (unchanged)
- `idf-engine` production `dpl_7qGSEBPMyeqvJnifA5w6fuUtcorG`, commit `9a13fab`, alias `idf-engine.vercel.app`,
  Vercel Authentication for All Deployments (anonymous 401). Pushes since `9a13fab` were canceled by its build guard.

## Database
- Supabase `idf-research-explorer` (`ecxswrwuylenwvsxghxg`, eu-central-1, Free), PostgreSQL 17.11, `webapp_api` through
  the Supavisor transaction pooler (port 6543, TLS). No schema, role, permission or data change in 7D-3/7D-4.
- Owner-run `tools/phase7d/build_web_db_url.py` through the pooler: login, TLS, read-only privileges, rate-limit function,
  server `extra_float_digits=0` with the defect reproduced, transaction-scoped `set_config` exact for all 3,200 means and
  reset after commit (all PASS before the URL was entered).
- Utilisation after QA: database 142 MB (Free limit 500 MB); 5 application backends of 60 connections; 4 rate-limit rows.

## Production QA (`tools/phase7d/live_web_checks.mjs` → `reports/webapp/phase7d/live_web_checks.json`, overall PASS)
| Gate | Result |
|---|---|
| W-1 parity | 21/21 responses byte-identical to the local reference (same commit, exact local DB, verified local engine, same request id): datasets, series lists, series detail, forecasts ×2, aggregate ×4, study ×4, series-base ×2, research, simulate ×3, CSV export |
| W-2 health + Phase 5 | health ok, engine reachable (bypass + key) `cedc5a31533772fc`; base totals 2555 / 2772 / 2900 / 1309 NCU, studyReference matched |
| W-3 validation | 400 ×7 (bounds, client demand, cross-dataset, non-JSON, bad/extra query, injection-like key), 413 oversized, 404 unknown |
| W-4 data scope | curated M5 300 of 30,490; non-curated series 404; `finalHoldoutTargetsRead=false` |
| S-1 headers | CSP (frame-ancestors/base-uri/object-src/form-action), X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy, HSTS (preload, Vercel), no X-Powered-By |
| S-2 methods | DELETE/POST on read-only routes 405 |
| S-3 secrets | 107 response bodies/header sets + 9 client assets: no secret names, header names, DB URLs, pooler host, role names, engine URL, traces |
| S-4 rate limit | 429 `rate_limited` with Retry-After 60 at the 30/min simulate limit (shared window) |
| Browser | 5 pages × 1280/1024/390: 15/15 HTTP 200, no horizontal overflow, 0 serious/critical axe, copy gate PASS, 0 console errors; real engine run equals Phase 5 totals; explorer → planner, CSV and PNG exports, invalid bounds, pattern and origin filters (`reports/webapp/phase7d/browser_prod/browser-qa.json`) |
| Logs | web: 0 runtime errors, no log lines (it logs only failures); engine: every web call 200, lines contain id/path/status/ms only |

## Performance (client-side from Egypt; server in fra1)
- Health: first 824 ms, then 443 ms. First API call after deploy 515 ms.
- Warm reads (m5 study): 232 / 85 / 91 / 82 / 84 ms (median 85 ms); other reads 135–290 ms.
- Simulate through web + engine: 264–449 ms; engine function time 53–134 ms warm, 214 ms first.

## Not executed in production (and why)
- Real engine outage fallback: not induced (it would require breaking the accepted engine). Covered by the 11 local
  engine-client tests (401/403/503/timeout/redirect/network) and the browser check of the labelled fallback with the
  simulate call intercepted.
- Database outage handling: not induced in production; covered by local tests.

## Known limitations and operational risks
- Supabase Free pauses inactive projects: open the app (or resume the project) before demos.
- Hobby runtime logs are kept 1 hour; Hobby/Free quotas apply (no paid resources).
- Rate limiting keys on the client IP (salted hash); users behind one NAT share the 30/min, 300/day simulate budget.
- Database TLS is encrypted without certificate pinning (`require` semantics, as for the engine).
- Rotating `ENGINE_SHARED_KEY` or the engine bypass secret requires updating both projects together.
- Dev-only `npm audit` findings (vitest, typescript-eslint) are not deployed; upgrade separately.
- If more than 10 commits accumulate between deployments, a build guard falls back to building (by design).
