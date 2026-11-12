# Phase 7A: Supabase schema design

> **Amended by Phase 7B (2026-11-12):** the implementation refines this design (no browser database access, dedicated least-privilege roles instead of the service-role key, Postgres-backed rate limiting, `/api/v1` routes, measured 137 MB footprint). See [PHASE7B_BACKEND_RESULTS.md](PHASE7B_BACKEND_RESULTS.md) section 3.

Design only. No project, table, policy or migration has been created. Implementation in 7B uses SQL
migrations under `apps/web/supabase/migrations/` applied with the Supabase CLI after owner approval.

## 1. Schemas

| Schema | Purpose | Access |
|---|---|---|
| `app` | Curated scientific evidence and application metadata (domains 2 and 3) | RLS enabled; `SELECT` for `anon` and `authenticated`; no insert/update/delete policies, so only the service role (seed script) can write |
| `planner` | User scenarios and saved runs (domains 4 and 5), post-MVP | RLS enabled; owner-only policies on `auth.uid() = owner_id` |
| `public` | Unused by the app (kept empty) | Default |

Expose `app` and `planner` through the API (`Exposed schemas` setting); keep `public` exposed but empty.

## 2. Tables (schema `app`)

Grain, keys and estimated rows. All text keys match the Phase 6 keys.

| Table | Grain | Primary key | Foreign keys | Rows |
|---|---|---|---|---|
| `datasets` | dataset | `dataset_key` | | 2 |
| `validation_origins` | dataset origin | `origin_key` | `dataset_key` | 8 |
| `forecast_models` | dataset x model role | `model_key` | `dataset_key` | 6 |
| `demand_patterns` | pattern | `pattern_key` | | 6 |
| `inventory_policies` | policy | `policy_key` | `forecast_role_key` nullable | 4 |
| `scenarios` | frozen scenario | `scenario_key` | | 17 |
| `series` | series | `series_key` | `dataset_key`, `pattern_key` | 800 curated (optionally all 30,990 metadata rows: 4 MB; MVP ships curated only) |
| `series_history` | series x origin x date (84 pre-origin days) | (`series_key`, `origin_key`, `date`) | `series_key`, `origin_key` | 268,800 |
| `validation_actuals` | series x origin x date (28 days) | (`series_key`, `origin_key`, `date`) | same | 89,600 |
| `forecasts` | series x origin x model x horizon day | (`series_key`, `origin_key`, `model_key`, `horizon_day`) | same + `model_key` | 268,800 |
| `series_origin_mean56` | series x origin | (`series_key`, `origin_key`) | same | 3,200 |
| `forecast_metrics_series` | series x origin x model | (`series_key`, `origin_key`, `model_key`) | same | 9,600 |
| `forecast_metrics_aggregate` | dataset x origin x model x pattern | (`origin_key`, `model_key`, `pattern_key`) with `pattern_key = 'all'` rows | `origin_key`, `model_key` | about 170 |
| `inventory_scenario_results` | origin x scenario x policy x pattern | (`origin_key`, `scenario_key`, `policy_key`, `pattern_key`) | all four | 1,904 |
| `inventory_series_base` | series x origin x policy | (`series_key`, `origin_key`, `policy_key`) | all three | 12,800 |
| `model_selection_trials` | trial | `trial_id` | `dataset_key` | 27 |
| `final_holdout_reported` | saved final assessment | `trial_id` | `dataset_key` | 8 |
| `limitations` | limitation | `limitation_id` | | 8 |
| `audit_findings` | finding | `finding_id` | | 12 |
| `provenance` | export version | `export_version` | | 1 per export |

Column rules: numeric evidence columns are `double precision`; counts `integer`; dates `date`; keys `text`.
Additive components are stored (sum of absolute error, squared error, error, actual, observations, scales),
never precomputed ratios, so the API divides consistently and undefined cases stay `NULL`.

### Indexes beyond primary keys

- `series (dataset_key, pattern_key, series_id)` for filtered listing and search; `series (dataset_key, is_curated)`.
- `forecasts (series_key, origin_key)` is covered by the PK prefix; same for history and actuals.
- `inventory_scenario_results (scenario_key, policy_key)` for scenario comparison.
- `forecast_metrics_series (origin_key, model_key)` for per-origin leaderboards within the curated set.

### Constraints

- `CHECK (horizon_day BETWEEN 1 AND 28)`, `CHECK (forecast >= 0)`, `CHECK (units >= 0)`.
- `validation_origins`: `CHECK (validation_start = origin_date + 1 AND validation_end = validation_start + 27)` and a trigger-free assertion at seed time that `validation_end < test_start` (stored on `datasets`).
- `forecast_models.role_key IN ('selected_ml','moving_average_28','seasonal_naive')`.

## 3. Tables (schema `planner`, post-MVP)

| Table | Grain | Primary key | Columns | Rows / retention |
|---|---|---|---|---|
| `scenarios` | user scenario | `id uuid` | `owner_id uuid`, `name`, `dataset_key`, `series_key`, `origin_key`, `parameters jsonb` (validated shape), `created_at` | per user, max 50 per owner (policy + check) |
| `runs` | executed run | `id uuid` | `owner_id`, `scenario_id`, `engine_version`, `result jsonb` (summary + 28-day events per policy), `created_at` | retention 30 days via scheduled cleanup; result size capped at 64 kB |

RLS: `USING (owner_id = auth.uid())` for select/update/delete and `WITH CHECK (owner_id = auth.uid())` for insert.
`owner_id` defaults to `auth.uid()`.

## 4. Volume and plan fit

Curated footprint about 650k rows and roughly 60 to 90 MB including indexes, against the Supabase Free limit of
500 MB (pricing page, read 2026-11-11). Monthly egress for a portfolio audience is far below the 5 GB
allowance when per-series payloads are cached by Next.js and the CDN.

## 5. Access model

| Actor | Key | Allowed |
|---|---|---|
| Browser | anon (publishable) key | `SELECT` on `app.*` through RLS; `planner.*` only when signed in |
| Next.js server | service-role key (environment variable, never `NEXT_PUBLIC_`) | Reads; writes only in the seed script and future admin tasks |
| FastAPI engine | service-role key or a dedicated read-only Postgres role (preferred) | `SELECT` on `validation_actuals`, `forecasts`, `series_origin_mean56`, `validation_origins` |
| Seed script (owner laptop) | service-role key, local `.env` outside Git | `TRUNCATE` + `COPY` into `app.*` inside one transaction, then writes `provenance` |

Authentication decision: the first public demo is read-only and needs no accounts. Supabase Auth (GitHub or
magic link) is introduced only with `planner.*` persistence after the MVP ships.

## 6. Operational notes

- Free projects pause after one week of inactivity. Before demos the owner unpauses the project, or a weekly
  Vercel cron pings `/api/health` (cron availability on Hobby: not verified in this phase).
- Re-exports replace `app.*` wholesale in a transaction and bump `provenance.export_version`; the app displays it.
- Branching is not on the Free plan; schema changes are tested against a local Supabase stack first.
