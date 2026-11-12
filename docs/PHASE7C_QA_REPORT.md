# Phase 7C: frontend QA report and Phase 7D handoff

Status 2026-11-12: **Phase 7C passed its local quality gate.** Nothing was deployed, pushed or committed and no cloud
resource was touched. Git HEAD `987e27f` (Phase 6 checkpoint); the tracked diff is empty and all Phase 7 work is untracked.
Built by Claude (7C-1, 7C-2), continued by Codex (7C-3 first version, browser QA script), then independently reviewed and
completed by Claude (this report).

## 1. What was built

| Page | Route | Data (all via `/api/v1`) | Highlights |
|---|---|---|---|
| Executive Overview | `/` | datasets, metrics/aggregate, inventory/study, research | headline KPIs per dataset with both baselines; MAE by origin; ML cost relative to each baseline by origin; policy cost/service table; data-driven findings; limitations |
| Forecast Explorer | `/forecasts` | datasets, series, series/[key], forecasts, metrics/aggregate (pattern) | curated-series search and paging, origin and model toggles, 28/84-day history, origin marker and validation window, per-model metrics, full-population pattern context, daily table, CSV; M5 "300 curated of 30,490" caveat |
| Inventory Planner | `/planner` | planner/simulate, planner/export, inventory/series-base | policy toggles, ten bounded inputs with field messages, base-match indicator, real engine run, KPI cards, server MA28 deltas, saved Phase 5 reference, cost breakdown, trajectories (stock, position, demand, orders), daily engine events, CSV; labelled precomputed fallback when the engine is unavailable |
| Scenario Comparison | `/scenarios` | inventory/study (dataset, optional pattern) | dataset/pattern/origin/scenario as URL state; trade-off scatter, cost components, pooled table, sensitivity across 17 scenarios, scenario × origin grid (shows the Store Item origin-4 reversal), 17-scenario matrix with CSV, per-origin detail, policy definitions |
| Research & Methodology | `/research` | datasets, research, inventory/study | problem, evidence types, datasets, forecasting approach and leaderboard, validation protocol, reported final holdout, simulation assumptions, findings, audit (12), limitations (8), threats, provenance hashes, future work |

Shared components: AppShell (sidebar, mobile drawer, status footer), PageHeader, Panel, Badge, SeriesKey, MetricCard,
ScientificNotice, DataTable, Segmented, Loading/Empty/Error states, Dataset/Origin/Pattern/Model/Series selectors, SVG
charts (TimeChart, GroupedColumns, DivergingBars, StackedBars, ScatterChart) with crosshair/keyboard reading and PNG
export. Typed client `src/lib/api/{types,client,useApi}.ts`; URL state `src/lib/{selection,useQueryState}.ts`.

## 2. Independent review of the Codex 7C-3 work (findings and resolution)

| # | Finding | Severity | Resolution |
|---|---|---|---|
| R-1 | Planner showed only an error when the engine was unavailable; the required labelled precomputed fallback was missing | High (requirement) | Added `PrecomputedFallback` (saved base-scenario Phase 5 rows via `/inventory/series-base`) labelled "Not your scenario"; shown for `engine_unavailable` and timeout |
| R-2 | No policy selection; always four policies | Medium | Policy toggles (at least one), sent as the `policies` array the API already validates |
| R-3 | Scenario inputs reset whenever the series or origin changed (state lived in a keyed child) | Medium (usability) | Inputs lifted to the page; results are bound to the exact request signature, so stale results can never be shown and inputs persist |
| R-4 | One generic validation message; `<legend>` misuse | Low | Per-field bound messages; proper fieldset/legend |
| R-5 | Scenario page lacked sensitivity, cost breakdown, origin filter, scenario × origin view, reversal callout, export; scenario not in URL | Medium (requirement) | All added; reversal notice computed from the data |
| R-6 | Daily planner table would have summed cost components in the browser (my draft) | Low (scientific rule) | Removed; only engine-returned values are shown |
| R-7 | Scenario grid cells lacked `min-w-0`, causing 5 px overflow at 1024 px after the rework | Low | Fixed (also hardened the Overview grid) |
| R-8 | `zod` 4.1.12 high advisory GHSA-mrhx-c7xc-m3w5 (memory exhaustion on oversized collections). Exposure was low (8 kB body cap before parsing, policies max 4) | High (dependency) | Pinned `zod` 4.6.7; `npm audit --omit=dev`: 0 vulnerabilities; all suites re-run |
| R-9 | `.env*` ignore rule would have hidden the env template | Low | `!.env.example` added |

Confirmed sound: the Codex `pattern` filter on `/inventory/study` (six-value enum, parameterised SQL applied before the
existing additive sums; defaults unchanged; 400 for unknown values; reconciliation test), the PNG export (rasterises the
displayed SVG only), the darker UI teal token (contrast) and the niceTicks upper-bound fix.

## 3. Test results (all executed 2026-11-12 on the final code)

| Suite | Command (from `apps/web`) | Result |
|---|---|---|
| TypeScript | `node node_modules/typescript/bin/tsc --noEmit -p .` | PASS |
| ESLint | `node node_modules/eslint/bin/eslint.js .` | PASS (0 problems) |
| UI component tests (jsdom; fetch and Next navigation doubled; fixtures captured from the live API) | `node node_modules/vitest/vitest.mjs run --project ui` | 34/34 PASS |
| Real-backend API integration (local Postgres 17.11 + Python engine) | `... run --project api` | 19/19 PASS |
| Production build | `node node_modules/next/dist/bin/next build` | PASS (5 static pages, 11 dynamic API routes) |
| Browser QA, real local production server (Edge, playwright-core, axe-core 4.14) | `APP_URL=http://127.0.0.1:3001 node tests/browser/phase7c.mjs` | PASS: 15/15 page × viewport checks (1280/1024/390): HTTP 200, 0 px overflow, 0 serious/critical axe, U-05 pass; 0 console errors |
| Client bundle secret scan | grep of `.next/static` for local keys, salt, DB URL | 0 matches |
| Dependency audit | `npm audit --omit=dev` | 0 vulnerabilities (dev-only tooling still reports advisories; not shipped) |
| Scientific evidence | `python -m intelligent_demand.bi.webapp_qa --only D-01`; `vendor_engine.py --check` | D-01 PASS (plan, execution, selection, ledger hashes unchanged); engine `identical` |

Real integration evidence (browser, not mocked): Explorer → Planner carries series and origin; a live four-policy run for
Store Item 1:11, origin 1, base scenario returned Selected ML 2,555, MA28 2,772, Seasonal Naive 2,900, Fixed ROP 1,309 NCU,
each equal to the saved Phase 5 total displayed beside it; server CSV and PNG downloads; out-of-bounds input blocks the run
with a field message; M5 `all_zero` pattern filter; Scenario origin filter as URL state and the Store Item final-origin
reversal rendered from real data. Intercepted (mocked, labelled as such): loading, empty and error states; engine outage
with the precomputed fallback (fallback GET real). Evidence: `reports/webapp/phase7c_final/` (JSON, screenshots, CSV, PNG).
Codex's earlier evidence is kept in `reports/webapp/phase7c_codex/`.

Local QA configuration note: the browser sweep ran the production server with `RATE_LIMIT_READ_PER_MINUTE=1000`, because
15 full page loads from one address exceed the default 120 reads/minute; the default limit itself is covered by A-07.

## 4. Copy gate U-05

The literal rule ("no savings ... in rendered text") conflicts with the mandatory caveat the same copy rules require
("simulated differences are not realised savings", API `ncuNotice`, frozen limitation L1). Weakening or deleting the caveat
would reduce scientific safety, so the gate was clarified rather than the caveat removed: `tests/copy-gate.mjs` approves only
the negated forms `not (realised|realized) (financial) savings`; any other "savings", "profit(ability)", "ROI" or
"optimal" fails; pages showing NCU must say "hypothetical"; any Fixed ROP mention requires "low-stock comparator". Applied
to every page and viewport in the browser and to rendered Overview, Planner and Scenario text in jsdom; 21 approved caveats,
0 violations. The clarification is recorded in `docs/PHASE7_QUALITY_GATES.md` (U-05).

## 5. Remaining limitations (not defects)

- PNG export captures the chart SVG plus a scientific caption, not surrounding HTML legends; one PNG was tested in the browser.
- Planner presets exist only for the base scenario (no endpoint exposes the other 16 scenarios' parameters); runs that
  match another frozen scenario are still recognised by the server's `studyReference`.
- No manual screen-reader audit; axe covers `main` only. Keyboard: all controls and charts (arrow keys) are operable.
- Mobile tables scroll inside labelled regions rather than reflowing to key-value lists.
- The jsdom CSV test logs "navigation not implemented" (anchor click); harmless, real browser download verified.
- Dev-only packages (eslint chain, embedded-postgres, vitest) carry npm advisories; they are not part of the deployed bundle.

## 6. Phase 7D handoff (nothing below has been done)

Prerequisites are unchanged from `docs/PHASE7B_BACKEND_RESULTS.md` section 4 (Supabase project, migration, role passwords,
seed, Vercel projects `idf-web` root `apps/web` and `idf-engine` root `apps/engine`, region `fra1`). Frontend additions:
- `apps/web/.env.example` lists the four required server-only variables and optional limits; no `NEXT_PUBLIC_*` values exist.
- The web build needs no database at build time (pages are static shells; data is fetched at runtime from `/api/v1`).
- Gates to run live: P-01..P-11 in `docs/PHASE7_QUALITY_GATES.md`; reuse `tests/browser/phase7c.mjs` with `APP_URL` set to the
  deployment (P-07/P-08) and `QA_OUT` pointing to a new folder; expect default rate limits to require spacing the sweep.
- Still unverified until 7D: Vercel engine build with the out-of-root package, cold start, pooler with custom roles, live RLS.

## 7. Local run instructions

From the repository root, three terminals (local-only values; the `&` in the path breaks npm shims, so call tools via node):
1. `cd apps/web && node scripts/local-db.mjs`
2. `cd apps/engine && ENGINE_SHARED_KEY=local-test-engine-key-0123456789abcdef0123 ENGINE_DATABASE_URL=postgresql://engine_api:local-engine-only@127.0.0.1:54329/webapp .venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8787`
3. `cd apps/web && WEBAPP_DATABASE_URL=postgresql://webapp_api:local-webapp-only@127.0.0.1:54329/webapp ENGINE_URL=http://127.0.0.1:8787 ENGINE_SHARED_KEY=local-test-engine-key-0123456789abcdef0123 RATE_LIMIT_SALT=local-test-salt-0123456789abcdef0123456789 node node_modules/next/dist/bin/next dev -p 3000 -H 127.0.0.1`
Open http://127.0.0.1:3000. First-time setup (schema and seed) is in `docs/PHASE7B_BACKEND_RESULTS.md` section 5.
In PowerShell, use `& 'C:/Program Files/nodejs/node.exe'` instead of `node` if a System32 shadow resolves first.
