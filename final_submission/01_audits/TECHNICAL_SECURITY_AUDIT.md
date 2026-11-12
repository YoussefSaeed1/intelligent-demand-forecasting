# Technical and security audit (Phase 8)

Audit date: 2026-11-12. Self-review by the assistant that implemented Phase 7; not an external penetration test.
Only non-disruptive checks were run: no secret rotation, no cloud configuration change, no load or outage test.

## 1. Production inventory (verified 2026-11-12)

| Component | Identifier | State |
|---|---|---|
| Public web application | https://idf-web.vercel.app | `idf-web` production deployment `dpl_362iX8C1ZZjJgYAEXPLS4TknU6zL`, commit `36da979`, READY, fra1; `/api/v1/health` returns `status ok`, engine reachable, engine version `cedc5a31533772fc`, build `36da9797baa3` |
| Simulation engine | https://idf-engine.vercel.app | `idf-engine` production `dpl_7qGSEBPMyeqvJnifA5w6fuUtcorG`, commit `9a13fab`, READY, fra1; anonymous request 401 (Vercel Authentication, all deployments) |
| Database | Supabase `idf-research-explorer` (eu-central-1, Free), PostgreSQL 17.11 | 655,711 seeded rows; 142 MB of 500 MB; accessed only through the transaction pooler by two least-privilege roles |
| Source control | Private GitHub repository `YoussefSaeed1/intelligent-demand-forecasting`, `main` at `9453f28` before Phase 8 | Private (anonymous API request returns 404); no tags |

Later commits after `36da979` touched only documentation and tools; both projects' build guards cancelled those
builds, so production still serves `36da979` (web) and `9a13fab` (engine).

## 2. Architecture and data flow

Browser → `idf-web` (Next.js 16 route handlers under `/api/v1`) → Supabase (role `webapp_api`, read-only plus a
rate-limit function) and → `idf-engine` (FastAPI, frozen Phase 5 engine) → Supabase (role `engine_api`, read-only).
The browser never holds a credential and never talks to the database or engine directly. Realised demand and
forecasts used by a simulation are loaded server-side by the engine; clients can only choose a curated series,
origin, policies and bounded scenario parameters.

## 3. Security controls and evidence

| Control | Evidence | Status |
|---|---|---|
| Secrets server-only | Production variables Sensitive, Production scope only; no `NEXT_PUBLIC_` names; client bundle scan (9 assets) finds no secret names, header names, database URLs or role names | Verified |
| Engine access | Shared key (constant-time check, before body parsing) + Vercel protection bypass header; engine protected for all deployments | Verified (E-01..E-08 production gates, PASS) |
| Redirect safety | Engine client uses `redirect: "manual"`; a cross-origin login redirect receives no headers (local test with a real second server) | Verified locally |
| Database least privilege | `webapp_api` has no insert/update on `app` tables; `engine_api` read-only; RLS enabled on `ops.rate_limits` with access only through a security-definer function | Verified; Supabase advisor reports only this intended INFO lint |
| Transport security | TLS to the pooler with a 1.2 minimum (Node `minVersion`); HTTPS with HSTS (preload) on both Vercel domains | Verified; the database certificate is not pinned (`require` semantics) |
| Input validation | Zod schemas with strict bounds; unknown fields, client-supplied demand, cross-dataset keys, oversized bodies (413) and injection-like keys rejected | Verified in production (9 of 9 cases) |
| Rate limiting | Postgres-backed per-client (salted IP hash) limits: 30 simulations per minute, 300 per day, 120 reads per minute | Verified in production (429 with Retry-After 60) |
| Error handling | Generic bodies, request ids, no stack traces, hosts or SQL; engine failures map to labelled precomputed-results fallback | Verified locally; production outage not induced |
| Security headers | CSP (frame-ancestors, base-uri, object-src, form-action), X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy, HSTS (`live_web_checks.json` S-1); Cross-Origin-Opener-Policy `same-origin` (live header check 2026-11-13); no X-Powered-By | Verified in production |
| Logging | Structured lines with request id, path, status and duration only | Verified in production logs (web and engine) |
| Numerical exactness | Read transactions set `extra_float_digits=3` (Supabase default 0 rounds floats to 15 digits); engine reads binary floats | Verified: 21/21 production API responses byte-identical to the local reference |

## 4. Dependency vulnerabilities (2026-11-12)

| Scope | Tool | Result |
|---|---|---|
| Web production dependencies (20) | `npm audit --omit=dev` | 0 vulnerabilities |
| Web development dependencies | `npm audit` | 9 (8 moderate, 1 critical) in vitest 4.0.8 and typescript-eslint/minimatch; not deployed; the critical vitest advisory concerns its UI server, which the project does not run |
| Engine runtime closure (21 pinned packages) | OSV batch query | No known vulnerabilities |

## 5. Deployment reproducibility

- Web: `npm ci` from a committed lockfile, `next build`, Node 24.x. Builds without any secret (verified locally and on Vercel).
- Engine: pinned closure in `apps/engine/pyproject.toml`, uv path source for the vendored engine package; engine version is
  the SHA-256 of the vendored `engine.py` and `design.py` (`cedc5a31533772fc`), byte-identical to the frozen Phase 5 engine.
- Build guards: an Ignored Build Step per project builds only when that project's inputs changed; an empty or unknown
  previous SHA explicitly builds (the first web deployment showed that Vercel treats exit 128 as an error).
- Runbooks and rollback: `docs/PHASE7D_DEPLOYMENT_RUNBOOK.md`, `docs/PHASE7D_ROLLBACK_PLAN.md`, deployment record
  `docs/PHASE7D_DEPLOYMENT_RECORD.md`.

## 6. Not tested in production (not claimed as passed)

1. **Real engine outage.** Not induced. Covered by 11 local engine-client tests (401, 403, 503, timeout, redirect,
   network) and a browser check of the labelled fallback with the simulate call intercepted.
2. **Real database outage or Supabase pause.** Not induced. Covered by local tests that map driver failures to 503.
3. **Built-preview protection.** Configured (`ssoProtection=preview`) but not demonstrated: the only preview attempt was
   correctly cancelled by the build guard and its URL serves Vercel's cancellation placeholder.

## 7. Operational limitations and risks

| Risk | Impact | Mitigation |
|---|---|---|
| Supabase Free pauses inactive projects | API 503 during a demonstration | Open the app shortly before the viva; know how to resume the project |
| Hobby log retention of 1 hour | Little post-incident evidence | Capture evidence immediately after tests |
| Shared IP rate-limit buckets | Users behind one network share the simulation budget | Acceptable for a research demonstration |
| Database TLS without certificate pinning | Theoretical interception risk on the pooler path | Same posture as the engine; upgrade to verify-full with Supabase CA later |
| Paired secret rotation | Rotating the engine key or bypass secret must update both projects | Documented in the runbook |
| Dev-only vulnerable tooling | Local developer risk only | Upgrade vitest separately |
| More than 10 commits between deployments | Build guard falls back to building (safe direction) | Documented |

## 8. Verdict

The deployed system meets its documented security design for a public, read-mostly research demonstrator. No
credential, internal URL or sensitive header was found in any client-visible output. Three production scenarios
remain untested by design and are listed above.
