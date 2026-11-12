# Phase 7D-3B `idf-web` deployment checklist

Each step needs owner approval. Secrets never pass through Claude. Baseline: `main` at `36da979`; engine production
`9a13fab` (`dpl_7qGSEBPMyeqvJnifA5w6fuUtcorG`), protected for All Deployments.

## A. Before creating the project
- [x] A-1 `git status` clean except untracked `experiments/` and screenshots; HEAD = `origin/main`.
- [x] A-2 Engine still READY on `9a13fab`, alias `idf-engine.vercel.app`, anonymous requests 401.
- [x] A-3 Supabase project `idf-research-explorer` active (not paused); no schema/data/role change planned.
- [x] A-4 Owner has, in the password manager: `webapp_api` password, `ENGINE_SHARED_KEY`, the engine project's
      Protection Bypass for Automation secret, a NEW `RATE_LIMIT_SALT` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`).

## B. Create `idf-web` (Claude, after approval)
- [x] B-1 Import the same private repository; framework Next.js; Root Directory `apps/web`; install `npm ci`; build
      `next build`; Node 24.x; function region `fra1`; "include files outside the root directory" OFF.
- [x] B-2 Ignored Build Step: `git diff --quiet "$VERCEL_GIT_PREVIOUS_SHA" HEAD -- :/apps/web` (exit 0 skips; empty or
      unknown SHA builds). Verify it does not affect `idf-engine`.
- [x] B-3 Decide deployment protection for the public web app (recommended: Vercel Authentication for Preview only;
      production domain public). Do not change `idf-engine` protection.
- [x] B-4 Do NOT deploy until section C is complete (an env-less build succeeds but every API route returns 503).

## C. Production-only environment variables (owner, dashboard; never `NEXT_PUBLIC_`)
- [x] `WEBAPP_DATABASE_URL` =
      `postgresql://webapp_api.<ref>:<url-encoded password>@<transaction-pooler host>:6543/postgres?sslmode=require&ssl_min_protocol_version=TLSv1.2`
      (no other query parameters: they would be sent to the server as startup parameters).
- [x] `ENGINE_URL` = `https://idf-engine.vercel.app` (production domain, HTTPS, no path).
- [x] `ENGINE_SHARED_KEY` = same value as the engine.
- [x] `VERCEL_PROTECTION_BYPASS_SECRET` = the ENGINE project's bypass secret.
- [x] `RATE_LIMIT_SALT` = new secret. Optional: `RATE_LIMIT_SIMULATE_PER_MINUTE`, `_PER_DAY`, `RATE_LIMIT_READ_PER_MINUTE`.
- [x] Claude verifies names and Production-only targets via metadata (values never decrypted).

## D. Deploy and verify (QA plan W and S sections)
- [x] D-1 Production build READY in fra1 from `36da979` (or the approved commit); build log has no secret values.
- [x] D-2 `/api/v1/health`: `status ok`, `engine.reachable true`, `engineVersion cedc5a31533772fc` (proves bypass + key).
- [x] D-3 Numeric exactness through the Supavisor pooler: every `/api/v1` read endpoint byte-identical to the local
      reference (same request id), incl. aggregate/study/series-base/forecasts/research; no tolerance.
- [x] D-4 Planner simulate on the base case equals the Phase 5 totals (2555 / 2772 / 2900 / 1309 NCU); CSV export works.
- [x] D-5 Errors: invalid input 400, oversized 413, rate limit 429 with Retry-After; engine failure shows the
      precomputed-results fallback; no secrets, hosts or stack traces in any response.
- [x] D-6 Security headers (CSP frame-ancestors, X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy);
      client bundle contains no secret names or values.
- [x] D-7 Browser QA at 1280/1024/390 on the production URL: no overflow, 0 serious/critical axe, copy gate PASS.
- [x] D-8 Runtime logs (within 1 h Hobby retention): no secrets, URLs, headers or tracebacks; engine logs show the
      web's calls with 200.
- [x] D-9 Engine unchanged after the web deploy: still `9a13fab`, protected.
- [x] D-10 Measure cold/warm latency of reads and simulate; record quotas.

## E. Rollback
- Web: promote the previous `idf-web` deployment or pause the project; the engine and database are unaffected.
- Secrets: rotating `ENGINE_SHARED_KEY` or the bypass secret requires updating both projects together.

## Outcome (2026-11-12)
All items executed; see `docs/PHASE7D_DEPLOYMENT_RECORD.md`. Exceptions: B-3 preview protection configured but not
demonstrated on a built preview; D-5 engine-failure fallback verified locally and with an intercepted browser call, not
by inducing a production outage. The B-2 guard was corrected (explicit exit 1 for an empty/unknown previous SHA).
