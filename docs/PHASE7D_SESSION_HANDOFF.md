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
7D-1 COMPLETE. 7D-2 COMPLETE (P-3 accepted on `9a13fab`, `dpl_7qGSEBPMyeqvJnifA5w6fuUtcorG`, https://idf-engine.vercel.app,
protection All Deployments). 7D-3A local preparation COMPLETE and verified (engine bypass header, lossless float reads,
DB URL TLS fix) CLOSED at `36da979`; the push's engine build was canceled by the Ignored Build Step and production
stays on `9a13fab`. 7D-3B NOT STARTED: follow `docs/PHASE7D_3B_CHECKLIST.md`.

## Next three actions (after approval only)
1. Confirm `idf-engine` production still points at `9a13fab` after any push (Ignored Build Step; see runbook).
2. Create `idf-web` per runbook; owner enters Production-only secrets incl. `VERCEL_PROTECTION_BYPASS_SECRET`.
3. Deploy and run QA W/S gates incl. byte-identical numeric responses through the Supavisor pooler.

## Safe resume commands
`git status --short; git log --oneline -3` · evidence check snippet in the progress file history (plan/execution/selection/ledger)
· `cd packages/inventory_core && ../../apps/engine/.venv/Scripts/python.exe vendor_engine.py --check`.

## Approval boundaries
No cloud creation, remote SQL, data load, secret configuration, deployment, domain, paid plan, commit or push without explicit
approval for that step. Secrets never in chat, docs or Git. Never touch unrelated projects, frozen evidence, ledger or backups.
