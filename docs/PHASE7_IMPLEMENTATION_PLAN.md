# Phase 7 implementation plan

Milestones are sequential; each ends with the gates in [PHASE7_QUALITY_GATES.md](PHASE7_QUALITY_GATES.md).
Nothing in 7B to 7D may touch frozen evidence; all new code lives in new namespaces.

## Repository layout (to be created in 7B)

```
apps/
  web/                 Next.js (App Router, TypeScript, Tailwind), apps/web/supabase/migrations/
  engine/              FastAPI service; depends on packages/inventory_core
packages/
  inventory_core/      byte-identical engine.py + design.py (minus load_design) + service.py wrapper + parity tests
src/intelligent_demand/bi/webapp_export.py   read-only curated export + manifest (laptop only)
configs/webapp.yaml    curation rule, bounds, labels; configs/webapp_qa.yaml  gate definitions
reports/webapp/        export manifest, QA results (tracked); CSVs stay in artifacts/webapp/ (ignored)
docs/PHASE7_*.md       this design set, updated as built
```

## 7A: architecture and feasibility (this milestone)

Delivered: the eight design documents. Exit: owner review of architecture, data contract, schema, API, UI,
feasibility and gates. Owner decisions required before 7B:

1. Approve Option A (two Vercel projects) and the $0 Hobby/Free plan posture.
2. Confirm or create the Vercel account and Supabase project (owner action; nothing is created by the assistant without explicit authorisation).
3. Approve the curated M5 budget (300 series, rule in the data contract) or change the strata.
4. Confirm MVP without accounts; persistence and Supabase Auth deferred.

## 7B: backend and Supabase integration

| Step | Output | Gate |
|---|---|---|
| B1 Curation and export | `webapp_export.py`, `configs/webapp.yaml`, CSVs + `reports/webapp/export_manifest.json` | D-01 to D-06 |
| B2 Engine package | `packages/inventory_core` with hash-identity and parity tests on Python 3.12 | S-01 to S-06 |
| B3 Schema | SQL migrations for `app` and `planner`, RLS policies, seed script (`COPY` in one transaction) | D-07, A-05 |
| B4 Engine service | FastAPI `/health`, `/simulate`, Pydantic bounds, read-only DB role | A-01 to A-06, S-07 |
| B5 Web API | Next.js route handlers, zod schemas, caching, rate limiting, CSV export | A-01 to A-08 |
| B6 Local integration | `vercel dev`-style local run against a local Supabase stack; contract tests | all A and S gates green |

Estimated effort: 6 to 9 working days. Exit: backend gates pass locally; no deployment yet.

## 7C: Next.js frontend

| Step | Output | Gate |
|---|---|---|
| C1 Design system | tokens, typography, components (cards, metric tiles, caveat banner, NCU badge, charts) | U-06 |
| C2 Overview and Research pages | static-plus-API pages | U-01, U-05 |
| C3 Forecast Explorer | series search, origin tabs, chart, metrics | U-01 to U-03 |
| C4 Inventory Planner | parameter form with bounds, run, trajectory, comparison, study reference | U-01 to U-05 |
| C5 Scenario Comparison | matrix, differences, scatter | U-01, U-03 |
| C6 Exports, states, accessibility, responsiveness | PNG/CSV, loading/empty/error states, keyboard and screen-reader pass | U-04, U-06, U-07 |

Estimated effort: 7 to 10 working days. Exit: UI gates pass against the local backend; Lighthouse accessibility ≥ 90.

## 7D: deployment and integration QA

| Step | Output | Gate |
|---|---|---|
| D1 Provisioning (owner-authorised) | Supabase project, two Vercel projects, environment variables, preview + production | P-01, P-02 |
| D2 Seed | run the seed script against the live database; verify `provenance` | P-03 |
| D3 Deploy | production deployments of web and engine | P-04 |
| D4 Live QA | health, RLS negative test, planner parity from the browser, rate limit, mobile, bundle secret scan | P-05 to P-10 |
| D5 Documentation | `PHASE7_DEPLOYMENT_RECORD.md` with URLs, versions, costs observed, unverified items | P-11 |
| D6 Demo preparation | walkthrough script for examiners and portfolio, GitHub link once the public repo exists | |

Estimated effort: 2 to 4 working days plus owner time for accounts.

## Scientific integrity controls across all milestones

- New code never imports from `intelligent_demand.inventory.runner`, `plan`, `inputs` or `audit` at runtime; the engine package is a copy with a hash-identity test.
- Exports read evidence through hash checks and the Phase 5 adapter; they write only to `artifacts/webapp/` and `reports/webapp/`.
- The holdout window is excluded by construction and asserted by gate D-03.
- No step trains, tunes, reselects or re-evaluates anything.
- Git checkpoints at the end of 7B, 7C and 7D, each only with owner approval; no pushes until the owner decides to publish the repository.

## Out of scope for Phase 7

Kumo experiments, academic paper and presentation, Power BI changes, off-device evidence backup (still an
open audit item the owner must close before submission).
