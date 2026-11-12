# Codex to Claude: Phase 7C return handoff

2026-11-12, local only. Resume here; do not rebuild completed work.

## Milestone
7C-3 requested core functionality implemented. 7C-4 reached a verified safe local
checkpoint; strict U-05 remains unresolved. No unconditional gate signoff.
7C-1/2 preserved. No Phase 7D, deployment, commit or push.

## Changes made by Codex
Paths below are under apps/web unless prefixed docs/.
- New src/features/planner/InventoryPlanner.tsx: real existing Python-backed POST,
  all four policies, ten approved input bounds/defaults, series/origin carry,
  reset, loading/validation/error/retry, hypothetical NCU costs, saved Phase 5
  reference costs, fill rates, stockout days, mean stock/orders, closing inventory
  chart, daily event/cost tables and server CSV export. Input/selection changes
  clear stale results. No simulation mathematics in JavaScript.
- New src/features/scenarios/ScenarioComparison.tsx: dataset/pattern/scenario
  controls, saved full-population 17-scenario cost matrix, four-policy cost/service
  scatter/table, per-origin costs/fill/stockouts, dependence and provenance caveats.
- src/app/{planner,scenarios}/page.tsx: replaced placeholders with client views.
- src/lib/schemas.ts, src/lib/server/repository.ts and
  src/app/api/v1/inventory/study/route.ts: additive optional pattern enum filter.
  Checked saved CSV grain (PatternKey plus additive totals); SQL filters before
  existing sums and pooled ratios. Six known keys only, invalid keys 400; absent
  populations return empty arrays. No new endpoint/grants/data/math changes.
  Contract amendment in docs/PHASE7_API_SPECIFICATION.md.
- New src/components/charts/exportPng.ts; modified charts/core.tsx: client PNG of
  displayed SVG, CSS colours resolved, validation/hypothetical-NCU caption. Fixed
  rounded-down upper axis tick that clipped peaks; regression test added.
- Responsive repairs: features/overview/OverviewView.tsx grid minimums,
  features/research/ResearchData.tsx grid, ui/DataTable.tsx containment,
  ui/Panel.tsx wrapping badges; globals.css darkens UI teal text for contrast.
  Chart identity palette unchanged.
- New tests/ui/planner-scenarios.test.tsx (5 tests), extended tests/api.test.ts,
  new tests/browser/phase7c.mjs. Evidence: reports/webapp/phase7c_codex/.
- Both checkpoint files updated and this return handoff created. Repaired Windows
  PowerShell legacy encoding in Codex checkpoint appendices; final docs are UTF-8.

## Tests actually executed
- Incoming baseline reproduced: 24/24 UI tests.
- Final UI: 29/29 (mocked fixtures); API: 19/19 (real local Postgres/Python engine).
  API checks cover saved evidence, simulation parity, bounds, rate limits, errors,
  CSV and pattern cost/episode reconciliation. No frozen parity/data rerun.
- TypeScript --noEmit, ESLint, next production build PASS.
- Health: export 2026-11-12.1, engine reachable, hash cedc5a31533772fc.
- Final browser script against local production 127.0.0.1:3001: 15 page/viewport
  combinations (5 pages x 1280/1024/390), all HTTP 200, zero document overflow,
  zero serious/critical axe findings, no console errors. Real Explorer-to-Planner
  origin carry, simulation, CSV/PNG downloads, input bounds and M5 all_zero filter.
- Browser loading/empty/error checks explicitly intercepted mocks; UI engine-
  unavailable test mocked. The real local engine was healthy.
- PNG and mobile Planner/desktop Scenario screenshots visually inspected.
- axe-core 4.14.0 uses existing transitive installation; no new browser downloads.
- Existing jsdom navigation-not-implemented warning in old CSV test remains;
  all tests pass and real browser CSV works. One local Next shutdown emitted a
  TimeoutNegativeWarning; browser consoles clean.
- .next/static JS scan found no local DB URLs, shared keys or salts.
- Tracked diff empty (git diff --exit-code PASS); no scientific evidence touched.

## Outstanding / not verified
1. U-05 strict literal gate NOT PASS: existing Overview/Research negative caveats
   say 'not realised savings', including immutable-source limitation L1. These
   are not positive financial claims. browser-qa.json records exact main-content
   lines. Footer/CSV also contain negative caveats. Do not modify frozen sources
   to satisfy a regex. Choose presentation/gate wording explicitly.
2. Remaining UI-spec polish: planner always runs all four policies (no toggles or
   sliders); only closing inventory is charted, with pipeline/demand/orders in
   daily tables; no MA28 delta strip. Scenario per-origin rows exist, but no origin
   filter, delta chart or scenario-origin heatmap. Core user request implemented;
   do not claim every UI-spec detail is complete.
3. PNG includes SVG/description/caveat, not surrounding HTML legends/export version.
   One inventory PNG download tested, not every chart. CSV downloaded and endpoint
   content/bounds checked. No full manual accessibility audit; axe scoped to main.
4. Browser tests cover navigation carry, not all nav controls at every width.
5. No cloud/deployment gates, no Phase 7D. Never deploy/commit/push in this task.

## Exact targeted commands (PowerShell)
From repo root enter apps/web. Bare node resolves to a System32 shadow file.

```powershell
Set-Location apps/web
& 'C:/Program Files/nodejs/node.exe' node_modules/typescript/bin/tsc --noEmit -p .
& 'C:/Program Files/nodejs/node.exe' node_modules/eslint/bin/eslint.js .
& 'C:/Program Files/nodejs/node.exe' node_modules/vitest/vitest.mjs run --project ui
& 'C:/Program Files/nodejs/node.exe' node_modules/vitest/vitest.mjs run --project api
& 'C:/Program Files/nodejs/node.exe' node_modules/next/dist/bin/next build
```
API tests set local-only configuration in tests/setup.ts. Check existing services
before starting anything; no reseeding or lock deletion. If absent:

```powershell
# apps/web, DB terminal:
& 'C:/Program Files/nodejs/node.exe' scripts/local-db.mjs
# apps/engine, engine terminal:
$env:ENGINE_SHARED_KEY='local-test-engine-key-0123456789abcdef0123'
$env:ENGINE_DATABASE_URL='postgresql://engine_api:local-engine-only@127.0.0.1:54329/webapp'
& ./.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8787
# apps/web, production verification server terminal:
$env:WEBAPP_DATABASE_URL='postgresql://webapp_api:local-webapp-only@127.0.0.1:54329/webapp'
$env:ENGINE_URL='http://127.0.0.1:8787'
$env:ENGINE_SHARED_KEY='local-test-engine-key-0123456789abcdef0123'
$env:RATE_LIMIT_SALT='local-test-salt-0123456789abcdef0123456789'
& 'C:/Program Files/nodejs/node.exe' node_modules/next/dist/bin/next start -p 3001 -H 127.0.0.1
# Separate apps/web terminal:
$env:APP_URL='http://127.0.0.1:3001'
& 'C:/Program Files/nodejs/node.exe' tests/browser/phase7c.mjs
```
Existing DB/engine/dev 3000 predated Codex; preserve them. Codex stops only its
own temporary 3001 server before return.

## Next three actions
1. Review U-05 literal-copy conflict without changing frozen scientific evidence.
2. Decide required UI-spec polish before closing 7C-4.
3. Re-run targeted checks after changes, update verdict, and stop before 7D.

## Precise Git state
HEAD 987e27f8a56cde6617e44ad8795feec9b97218ef (Phase 6), tracked diff empty.
All incoming uncommitted work preserved. Normal untracked status below includes
incoming Phase 7A/7B work; it is not solely Codex-created content.
?? apps/
?? configs/webapp.yaml
?? docs/PHASE7B_BACKEND_RESULTS.md
?? docs/PHASE7C_CODEX_TO_CLAUDE_HANDOFF.md
?? docs/PHASE7C_PROGRESS.md
?? docs/PHASE7C_SESSION_HANDOFF.md
?? docs/PHASE7_API_SPECIFICATION.md
?? docs/PHASE7_APPLICATION_ARCHITECTURE.md
?? docs/PHASE7_DATA_CONTRACT.md
?? docs/PHASE7_DEPLOYMENT_FEASIBILITY.md
?? docs/PHASE7_IMPLEMENTATION_PLAN.md
?? docs/PHASE7_QUALITY_GATES.md
?? docs/PHASE7_SUPABASE_SCHEMA_DESIGN.md
?? docs/PHASE7_UI_UX_SPECIFICATION.md
?? experiments/
?? packages/
?? reports/webapp/
?? src/intelligent_demand/bi/webapp_export.py
?? src/intelligent_demand/bi/webapp_qa.py
