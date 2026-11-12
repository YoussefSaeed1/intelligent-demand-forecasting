# Phase 7A: deployment feasibility

Assessed 2026-11-11 from official provider documentation and local measurements. No account, project or
resource was created. The Vercel and Supabase connectors were not available in this session (the MCP servers
were disconnected), so nothing about the owner's accounts was inspected; everything below is public
documentation plus local measurement.

## 1. Python engine profile (measured locally, Python 3.14, this laptop)

| Item | Measurement |
|---|---|
| Engine imports | numpy, pandas, PyYAML (design.py only, for `load_design`, not needed by the service) |
| Package footprint | numpy 33 MB + numpy.libs 21 MB, pandas 74 MB; pyarrow (93 MB) and psutil are not needed by the engine |
| Estimated service bundle | about 130 MB engine dependencies + FastAPI, Pydantic, uvicorn and a Postgres client (not measured; typically under 30 MB) |
| Cold import | numpy + pandas 1.1 s; engine + design 0.05 s |
| One request (1 series, 4 policies, 28 days) | about 0.40 s, peak traced memory 0.5 MB |
| 500 series x 4 policies | 0.35 s, 4.5 MB (cost is per-day Python loop, not per series) |
| Native libraries | numpy and pandas wheels only; no compilers, no model artefacts, no GPU |
| Determinism | pure arithmetic on saved inputs; identical output per input |

Conclusion: the engine is tiny, stateless and serverless-friendly. The heaviest element is importing pandas.

## 2. Provider constraints (official documentation, read 2026-11-11)

Vercel Python runtime and function limits (docs last updated 2026-08):

| Constraint | Value |
|---|---|
| Python versions | 3.12 default, 3.13, 3.14 |
| FastAPI | zero-configuration preset; entrypoint `app` in `app.py`/`main.py` or `tool.vercel.entrypoint` |
| Bundle size | 500 MB uncompressed for Python (250 MB for other runtimes); 5 GB large functions in beta |
| Memory / CPU | Hobby 2 GB / 1 vCPU (fixed); Pro up to 4 GB / 2 vCPU |
| Max duration | Hobby 300 s; Pro 800 s |
| Request and response body | 4.5 MB (not applicable to streamed responses) |
| Hobby included usage | 4 active-CPU hours, 360 GB-hours provisioned memory, 1,000,000 invocations per month, 100 GB fast data transfer |
| Hobby terms | free; non-commercial, personal use only (fair-use guidelines) |
| Services (one project, several runtimes) | Beta on all plans |

Supabase Free plan (pricing page):

| Constraint | Value |
|---|---|
| Price | $0 |
| Database | 500 MB, shared CPU, 500 MB RAM |
| Storage | 1 GB; egress 5 GB plus 5 GB cached |
| Auth | 50,000 monthly active users |
| Projects | 2 active; projects pause after one week of inactivity (unpause manually) |
| Branching | not on Free (Pro from $25/month) |

## 3. Budget check against the design

| Need | Budget | Headroom |
|---|---|---|
| Engine bundle about 160 MB | 500 MB | ample |
| 0.4 s CPU per planner run | 4 CPU-hours/month on Hobby | about 36,000 runs/month before throttling |
| Memory 2 GB fixed | engine needs well under 200 MB with pandas loaded | ample |
| Curated database about 60 to 90 MB | 500 MB | ample; full `series` metadata for all 30,990 series would add about 4 MB |
| Response size: one run with 4 policies x 28 daily rows | about 30 kB | far below 4.5 MB |
| Audience egress | tens of MB per visit at most | below 5 GB/month for a portfolio audience |

Expected recurring cost: **$0** on Vercel Hobby + Supabase Free, provided the project remains personal and
non-commercial and the owner accepts the Free-plan pause behaviour.

## 4. Options compared

| Option | Scientific fidelity | Complexity | Cost | Performance | Reliability | Deployment effort | Maintenance |
|---|---|---|---|---|---|---|---|
| A. Next.js on Vercel + FastAPI engine on Vercel (two projects, one repo) | Full: unchanged engine | Low | $0 | 0.4 s warm; cold start about 1.5 to 3 s (import + boot, not measured on Vercel) | High, GA features only | Low | Low: one repo, one CI |
| A'. Same, using Vercel Services in one project | Full | Low | $0 | same | Beta feature | Low | Low once GA |
| B. Next.js on Vercel + FastAPI on a separate host (Fly.io, Render, Railway free tiers) | Full | Medium (two platforms, two deploy pipelines, CORS) | $0 to small; free-tier limits and sleep behaviour not verified | No cold start if always-on, but free tiers sleep | Medium | Medium | Medium |
| C. Next.js only, precomputed results, no live engine | Partial: planner limited to the 17 frozen scenarios for curated series (data exists for base per series; other scenarios exist only at pattern grain) | Lowest | $0 | Fastest | Highest | Lowest | Lowest |

Recommendation: **A primary**, with **A'** as an optimisation when Services leaves beta, **C** as the degraded
mode built into the app (if the engine is unreachable the planner still shows Phase 5 base results and the
scenario study), and **B** only if Vercel's Python bundle or cold-start behaviour proves unacceptable in 7D
smoke tests. No always-on service is justified by the workload.

## 5. Risks and unverified items

| Item | Status | Mitigation |
|---|---|---|
| Vercel cold start for a pandas-importing function | not measured on Vercel | Measure in 7D; keep the function warm with an hourly cron if needed (cron availability on Hobby not verified) |
| Vercel WAF rate-limit rules on Hobby | not verified | In-handler token bucket is the primary limit |
| Vercel cron jobs on Hobby | not verified | Fallback: manual unpause before demos |
| Supabase pause after 7 days | documented | Weekly health ping or manual unpause |
| Hobby non-commercial clause | documented | Academic portfolio use; no monetisation |
| Owner accounts and quotas | not inspected (connectors unavailable) | Owner confirms in 7B kickoff |
| Python 3.14 locally vs 3.12 default on Vercel | engine has no version-specific code | Pin 3.12 in the engine `pyproject.toml`; parity test runs on 3.12 in CI |
| Fly.io/Render/Railway free tiers | not verified | Only relevant for Option B |

## 6. Verification plan for 7D (deployment QA)

Successful build is not success. Required: live production URL, `/api/health` on both projects reporting
matching export and engine versions, RLS proven by an anon-key write attempt failing, planner run from the
browser returning results identical to the local parity fixture for a known series, mobile viewport check,
rate limit triggering at the configured threshold, and no secrets in the client bundle (grep of built assets).
