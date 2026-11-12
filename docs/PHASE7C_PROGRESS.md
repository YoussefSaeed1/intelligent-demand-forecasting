# Phase 7C progress (frontend)

Last updated: 2026-11-12 (Phase 7 checkpoint). Phase 7A-7C committed locally on top of `987e27f` (Phase 6);
only `experiments/` (Kumo) remains untracked. Full results: `docs/PHASE7C_QA_REPORT.md`.

| Milestone | Status | Evidence |
|---|---|---|
| Preflight | DONE | 7B contracts checked against live local responses |
| 7C-1 Foundation | DONE | shell, tokens, typed client, URL state |
| 7C-2 Overview, Forecast Explorer, Research | DONE | |
| 7C-3 Planner, Scenario Comparison | DONE | Codex first version; Claude review fixes R-1..R-7 (QA report section 2) |
| 7C-4 QA and handoff | DONE, gate PASS | tsc, ESLint, build PASS; 34/34 UI + 19/19 real API; browser 15/15 (1280/1024/390), 0 overflow, 0 serious/critical axe, U-05 PASS; D-01 PASS; engine identical |

## Decisions (cumulative)
- Browser data only via existing `/api/v1/*`; one additive contract change: optional `pattern` enum on
  `/inventory/study` (Codex; reviewed; documented in PHASE7_API_SPECIFICATION.md).
- Hand-written SVG charts; dataviz-validated series palette (ML `#1c5cab`, MA28 `#1baf7a`, SN `#eb6834`, ROP `#9085e9`).
- No inventory arithmetic in the browser; only relative differences of displayed values and the equal-origin mean MAE
  (reproduces saved leaderboard values in tests).
- U-05 clarified: only negated "not (realised) (financial) savings" caveats approved (`tests/copy-gate.mjs`).
- `zod` pinned 4.6.7 (security advisory GHSA-mrhx-c7xc-m3w5); dev test deps exact-pinned.

## Checkpoint
- Owner-authorised local commit of Phase 7A-7C on `main` (see `docs/PHASE7_CHECKPOINT.md`); hash in the ignored receipt
  `artifacts/experiments/phase7_checkpoint_20261112/postcommit.json`. Same-device backup:
  `C:/Project_Backups/Demand_Forecasting_Phase7C_WebApp_verified_20261112`. Not pushed, not deployed.

## Owner decisions still needed
- Authorisation to start Phase 7D (deployment); off-device evidence backup (F-02) remains open.

## Next actions (only after authorisation)
1. Phase 7D per `docs/PHASE7C_QA_REPORT.md` section 6 and `docs/PHASE7B_BACKEND_RESULTS.md` section 4.
