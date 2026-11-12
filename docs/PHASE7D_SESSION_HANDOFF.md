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
Phase 7D COMPLETE. Public app https://idf-web.vercel.app (`idf-web` `prj_r38MRs59MUsJMhpd7DRV42ABdM8t`, production
`dpl_362iX8C1ZZjJgYAEXPLS4TknU6zL`, commit `36da979`). Engine `9a13fab` (`dpl_7qGSEBPMyeqvJnifA5w6fuUtcorG`) protected for
All Deployments and unchanged. Evidence: `docs/PHASE7D_DEPLOYMENT_RECORD.md`, `reports/webapp/phase7d/live_web_checks.json`,
`reports/webapp/phase7d/browser_prod/browser-qa.json`.

## Next actions (optional)
1. Before demos: open the app (Supabase Free pauses inactive projects); re-run `tools/phase7d/live_web_checks.mjs`.
2. Demonstrate preview protection with the next real `apps/web` change on a non-production branch.
3. Upgrade dev-only tooling (vitest) in a separate change.

## Safe resume commands
`git status --short; git log --oneline -3` · evidence check snippet in the progress file history (plan/execution/selection/ledger)
· `cd packages/inventory_core && ../../apps/engine/.venv/Scripts/python.exe vendor_engine.py --check`.

## Approval boundaries
No cloud creation, remote SQL, data load, secret configuration, deployment, domain, paid plan, commit or push without explicit
approval for that step. Secrets never in chat, docs or Git. Never touch unrelated projects, frozen evidence, ledger or backups.
