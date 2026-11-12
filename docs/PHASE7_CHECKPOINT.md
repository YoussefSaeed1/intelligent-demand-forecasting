# Phase 7 local checkpoint (7A architecture, 7B backend, 7C frontend)

Owner-authorised local checkpoint of the web application before deployment. No push, deployment, cloud resource,
retraining, regeneration, final-holdout access or ledger write. Phase 7D has not started.

## Verified scope

- Phase 7A design documents (`docs/PHASE7_*.md`), Phase 7B backend (curated export and QA modules, migration, seed
  script, FastAPI engine service, byte-identical vendored Phase 5 engine package), Phase 7C frontend (five pages,
  components, typed client, tests, browser QA script, env template) and QA evidence (`reports/webapp/`).
- Final gates (2026-11-12, `docs/PHASE7C_QA_REPORT.md`): tsc, ESLint and production build PASS; 34/34 UI component tests;
  19/19 real-backend API tests; browser QA 15/15 page × viewport checks (0 overflow, 0 serious/critical axe, U-05 PASS)
  with a live engine run equal to the saved Phase 5 totals; `npm audit --omit=dev` 0 vulnerabilities.
- Scientific integrity: plan `63efc59e…`, execution `b55ba4a0…`, selection `a71ab187aaad10eb…`, ledger `fa2af529…`
  verified directly and by D-01; vendored `engine.py`, `design.py`, `__init__.py` byte-identical to the originals.
- Reproducibility from tracked files: the staged index was exported to a clean folder; the vendored engine check
  passes there and the migration bytes equal the generated file (`c7b2d172…`). Regenerating the migration in the
  working tree is byte-identical. `apps/web/supabase/.gitattributes` pins the generated SQL to LF so a Windows
  (`core.autocrlf=true`) checkout does not alter it. The generator and seed script read the git-ignored curated CSVs
  (`artifacts/webapp/data/`, 20 files, hashes in `reports/webapp/export_manifest.json`), which the deterministic
  `python -m intelligent_demand.bi.webapp_export` rebuilds from local evidence.

## Excluded from Git

Secrets and real `.env` files (only the empty `apps/web/.env.example` is tracked), `node_modules`, `.next`, Python
virtual environments and caches, the embedded Postgres data directory (`apps/web/.local-postgres`), build info, the
generated curated CSVs (`artifacts/webapp/`), two QA planner CSV downloads (ignored by the existing CSV rule) and the
unrelated `experiments/kumo_forecast/KUMO_FEASIBILITY_REPORT.md`. Tests and docs contain only loopback-only placeholder
values for the embedded test database (`db-reset.mjs` refuses non-local hosts); no real credential exists in the tree.

## Preservation

Same-device verified snapshot: `C:/Project_Backups/Demand_Forecasting_Phase7C_WebApp_verified_20261112`, holding the
committed files, the git-ignored curated CSVs and QA CSVs, a SHA-256 manifest, and a Git bundle of `main`. This is a
**LOCAL BACKUP ON THE SAME DEVICE**, not protection against device loss; the off-device copy (audit finding F-02) is
still outstanding. Existing Phase 4, 5 and 6 backups were not modified.

## Git

Commit message: `feat: complete phase 7a-7c web application checkpoint`. The commit hash is reported to the owner, in
the ignored receipt `artifacts/experiments/phase7_checkpoint_20261112/postcommit.json` and in the backup, avoiding a
self-reference. No push, amend or history rewrite.
