# Phase 7D-2 prerequisites (engine deployment)

Status 2026-11-12: Phase 7D-1 complete. **P-1 done** (owner-approved local commit; see PHASE7D_PROGRESS.md). P-2 and P-3
not started; each needs explicit owner approval. Order: P-2 private GitHub push, then P-3 Vercel engine project.

## P-1 Local remediation commit (approval D-3) — DONE 2026-11-12

| Change | Detail | Scientific effect |
|---|---|---|
| R-1 Starlette CVEs | `apps/engine/pyproject.toml`: `fastapi==0.162.0` (released 2026-10-23; requires `starlette>=0.46`) and an explicit `starlette==1.10.0` pin (2026-10-24; fixes CVE-2026-54283/-48818/-48710/-48817/-54282). OSV 2026-11-12: no known vulnerabilities for either | None: web wrapper only |
| R-2 transitive pins | Implemented as explicit `==` pins of the complete runtime closure in `[project].dependencies` (works for uv and pip): annotated-doc, annotated-types, anyio, idna, opentelemetry-api (new FastAPI dependency), psycopg-binary, pydantic-core, python-dateutil, typing-extensions, typing-inspection, tzdata | None; numpy 2.5.4 and pandas 3.1.1 stay pinned |
| Engine TLS guard | `engine_service/data.py`: refuse non-loopback database URLs without `sslmode=require` or stronger (7D-1 lesson) | None |
| R-3 headers | `apps/web/next.config.ts`: minimal CSP (`frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`; `X-Powered-By` removed. No script/style CSP (would need nonces) | None |
| Tooling and evidence | `apps/web/supabase/{live_checks.py,set_remote_env.ps1,test_live_checks.py}`, `reports/webapp/phase7d/`, `docs/PHASE7D_*.md` | None |

Re-verification before the commit:
- Reinstall the engine virtual environment from the new pins.
- Engine service tests: 37.
- Engine package tests, including the 3,264-episode parity suite (S-02, bit-exact), plus the identity check.
- Web: 19 real-API tests, 34 UI tests, tsc, ESLint and `next build`.
- `npm audit --omit=dev` and OSV must both report 0.
- Ruff; frozen-evidence hashes; vendor `--check`; a secret scan of the staged files.
- One commit on `main`, no amend.

## P-2 Private GitHub repository (approval D-2 plus explicit push approval)

- The `gh` CLI is not installed, and no Git remote exists.
- **Owner:** on github.com, create an **empty private** repository (no README, licence or .gitignore), for example `idf-demand-inventory`.
- **Claude, after approval:**
  - `git remote add origin https://github.com/<owner>/<repo>.git`
  - `git push -u origin main`
  - Sign-in goes through Git Credential Manager in your browser. Claude never handles a token.
- **Pre-push gates (already true at `7000c04`; re-run after P-1):**
  - The secret scan of all tracked files is clean.
  - The largest file is 1.5 MB (GitHub's limit is 100 MB); the pack is 14.6 MiB.
  - `experiments/` (Kumo), raw Kaggle data, curated CSVs, `.env*` files, the virtual environments and `node_modules` are not tracked.
- **Keep the repository private.** Kaggle competition rules restrict redistributing data; only derived reports are tracked.

## P-3 Vercel engine project (approval of 7D-2)

1. **Owner:** in Vercel, add the GitHub integration limited to this one repository.
2. **Claude:** create `idf-engine` in team `team_CNXls9qDvhkHpuAhliQxEcPs`:
   - root `apps/engine`; framework FastAPI (`[tool.vercel] entrypoint = "main:app"`); Python 3.14 from `requires-python`;
   - **Include files outside the root directory: on** (needed for `packages/inventory_core`);
   - function region `fra1`.
3. **Owner, dashboard, Production environment only:**
   - `ENGINE_DATABASE_URL`: `postgresql://engine_api.ecxswrwuylenwvsxghxg:<url-encoded password>@<pooler host>:6543/postgres?sslmode=require&ssl_min_protocol_version=TLSv1.2`
   - `ENGINE_SHARED_KEY`: a new `secrets.token_urlsafe(48)`, also kept for `idf-web`.
   - First build only: `VERCEL_ANALYZE_BUILD_OUTPUT=1`.
4. **Deploy from `main` and verify E-01..E-08** (QA plan):
   - The key is enforced.
   - Parity on Store Item `1:11` / origin 1 / base equals the saved values exactly.
   - `engineVersion` is `cedc5a31533772fc`.
   - Starlette 1.10.0 appears in the build log.
   - Bundle size and cold-start time are recorded.
   - Logs contain no secrets.

**Fallback if the out-of-root package fails to install:** set the project root to the repository root, with `[tool.vercel]` pointing at
`apps/engine/main.py`. Decide only after reading the build log.

**Optional later hardening:** `verify-full` for both apps with the Supabase CA certificate, held as a non-secret environment
variable. 7D-1 verified TLS 1.3 with `sslmode=require`.
