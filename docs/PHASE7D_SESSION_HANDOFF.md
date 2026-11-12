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
7D-1 COMPLETE. 7D-2 P-1 DONE: one local security commit after `7000c04` (hash in ignored receipt `artifacts/experiments/phase7d_p1_20261112/postcommit.json`). Next: P-2 private GitHub push (needs approval).

## Next three actions (after approval only)
1. P-2 (approval): owner creates empty private GitHub repo; Claude adds remote and pushes `main`.
2. P-3 (approval): create Vercel `idf-engine`, owner sets Production env vars (TLS query required), deploy, E-01..E-08.
3. 7D-3 web project after the engine passes. Never re-apply or re-seed the database.

## Safe resume commands
`git status --short; git log --oneline -3` · evidence check snippet in the progress file history (plan/execution/selection/ledger)
· `cd packages/inventory_core && ../../apps/engine/.venv/Scripts/python.exe vendor_engine.py --check`.

## Approval boundaries
No cloud creation, remote SQL, data load, secret configuration, deployment, domain, paid plan, commit or push without explicit
approval for that step. Secrets never in chat, docs or Git. Never touch unrelated projects, frozen evidence, ledger or backups.
