# Phase 7D session handoff

Read this, then `docs/PHASE7D_PROGRESS.md`, then `docs/PHASE7D_PREDEPLOYMENT_REPORT.md`. Run `git status --short` and confirm HEAD.

## Architecture
Vercel project `idf-web` (Next.js, root `apps/web`) → Vercel project `idf-engine` (FastAPI, root `apps/engine`, Python 3.14,
include files outside root) → Supabase project `idf-research-explorer` (free, eu-central-1) via the Supavisor transaction pooler
using roles `webapp_api` / `engine_api`. Region `fra1`. Secrets in Production env only, entered by the owner.

## Identifiers (non-secret)
- Vercel team `team_CNXls9qDvhkHpuAhliQxEcPs`. Supabase org `uxqjykiobncetduzzqrg`. Supabase project `idf-research-explorer` ref `ecxswrwuylenwvsxghxg` (eu-central-1, free).
- Local checkpoint `7000c048900b315e131ba8ccce3350c7dd7e4140`; backup `C:/Project_Backups/Demand_Forecasting_Phase7C_WebApp_verified_20261112`.

## Status
7D-1 COMPLETE. P-1 `8c54c3c`; P-2 pushed to private `YoussefSaeed1/intelligent-demand-forecasting`. P-3: `idf-engine`
(`prj_ZkgvGobCJHntKWcrevCAgRlcsmX6`, https://idf-engine.vercel.app, protection All Deployments). Pre-fix run: E-06 FAIL from
Supabase `extra_float_digits=0` (15-digit text floats). Lossless binary-transport fix committed, pushed and auto-deployed;
sweep 3,200 pairs with 0 differences. **P-3 NOT closed** until the owner's production E-01..E-08 run passes.

## Next three actions (after approval only)
1. Owner: start the local reference engine on 8787 and run `tools/phase7d/live_engine_checks.py` (hidden prompts: engine
   key + bypass); Claude then checks runtime logs (E-08, within 1 h Hobby retention).
2. On PASS: close P-3 in the progress file. On FAIL: diagnose; never loosen the bit-exact comparison.
3. 7D-3 web project only after separate approval; first fix the postgres.js float-precision risk (runbook). Never re-apply
   or re-seed the database.

## Safe resume commands
`git status --short; git log --oneline -3` · evidence check snippet in the progress file history (plan/execution/selection/ledger)
· `cd packages/inventory_core && ../../apps/engine/.venv/Scripts/python.exe vendor_engine.py --check`.

## Approval boundaries
No cloud creation, remote SQL, data load, secret configuration, deployment, domain, paid plan, commit or push without explicit
approval for that step. Secrets never in chat, docs or Git. Never touch unrelated projects, frozen evidence, ledger or backups.
