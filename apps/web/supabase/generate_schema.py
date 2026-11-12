"""Generate the reviewed SQL migration for the curated `app` schema from the export manifest.

Column names and order come from reports/webapp/export_manifest.json so DDL cannot drift from the CSVs.
Keys, foreign keys, checks and indexes are declared below. Output: supabase/migrations/<name>.sql.
Run from the repository root:  .venv\\Scripts\\python.exe apps/web/supabase/generate_schema.py
"""

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "reports/webapp/export_manifest.json"
OUTPUT = Path(__file__).parent / "migrations/20261112000001_app_schema.sql"

PRIMARY = {
    "datasets": ["dataset_key"],
    "validation_origins": ["origin_key"],
    "forecast_models": ["model_key"],
    "demand_patterns": ["pattern_key"],
    "inventory_policies": ["policy_key"],
    "scenarios": ["scenario_key"],
    "model_selection_trials": ["trial_id"],
    "final_holdout_reported": ["trial_id"],
    "limitations": ["limitation_id"],
    "audit_findings": ["finding_id"],
    "series": ["series_key"],
    "series_history": ["series_key", "origin_key", "date"],
    "validation_actuals": ["series_key", "origin_key", "date"],
    "forecasts": ["series_key", "origin_key", "model_key", "horizon_day"],
    "series_origin_mean56": ["series_key", "origin_key"],
    "forecast_metrics_series": ["series_key", "origin_key", "model_key"],
    "forecast_metrics_aggregate": ["origin_key", "model_key", "pattern_key"],
    "inventory_scenario_results": ["origin_key", "scenario_key", "policy_key", "pattern_key"],
    "inventory_series_base": ["series_key", "origin_key", "policy_key"],
    "provenance": ["export_version"],
}
FOREIGN = {
    "validation_origins": [("dataset_key", "datasets")],
    "forecast_models": [("dataset_key", "datasets")],
    "series": [("dataset_key", "datasets"), ("pattern_key", "demand_patterns")],
    "series_history": [("series_key", "series"), ("origin_key", "validation_origins")],
    "validation_actuals": [("series_key", "series"), ("origin_key", "validation_origins")],
    "series_origin_mean56": [("series_key", "series"), ("origin_key", "validation_origins")],
    "forecasts": [("series_key", "series"), ("origin_key", "validation_origins"), ("model_key", "forecast_models")],
    "forecast_metrics_series": [
        ("series_key", "series"),
        ("origin_key", "validation_origins"),
        ("model_key", "forecast_models"),
    ],
    "forecast_metrics_aggregate": [("origin_key", "validation_origins"), ("model_key", "forecast_models")],
    "inventory_scenario_results": [
        ("origin_key", "validation_origins"),
        ("scenario_key", "scenarios"),
        ("policy_key", "inventory_policies"),
        ("pattern_key", "demand_patterns"),
    ],
    "inventory_series_base": [
        ("series_key", "series"),
        ("origin_key", "validation_origins"),
        ("policy_key", "inventory_policies"),
    ],
    "model_selection_trials": [("dataset_key", "datasets")],
    "final_holdout_reported": [("dataset_key", "datasets")],
}
CHECKS = {
    "forecasts": ["horizon_day between 1 and 28", "forecast >= 0"],
    "validation_actuals": ["units >= 0"],
    "series_history": ["units >= 0"],
    "series_origin_mean56": ["historical_mean56 >= 0"],
    "validation_origins": ["validation_start = origin_date + 1", "validation_end = validation_start + 27"],
}
INDEXES = {
    "series": [["dataset_key", "pattern_key", "series_id"]],
    "inventory_scenario_results": [["scenario_key", "policy_key"]],
    "forecast_metrics_series": [["origin_key", "model_key"]],
}
# Tables the engine service may read (everything else is web API only).
ENGINE_TABLES = ("validation_origins", "validation_actuals", "forecasts", "series_origin_mean56")
DATE_COLUMNS = {"date", "origin_date", "validation_start", "validation_end", "train_start", "training_start", "test_start"}
ORDER = [
    "datasets",
    "demand_patterns",
    "inventory_policies",
    "scenarios",
    "validation_origins",
    "forecast_models",
    "series",
    "series_history",
    "validation_actuals",
    "forecasts",
    "series_origin_mean56",
    "forecast_metrics_series",
    "forecast_metrics_aggregate",
    "inventory_scenario_results",
    "inventory_series_base",
    "model_selection_trials",
    "final_holdout_reported",
    "limitations",
    "audit_findings",
    "provenance",
]


def snake(name):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


def sql_type(column, series):
    if column in DATE_COLUMNS:
        return "date"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "bigint" if series.abs().max() > 2_000_000_000 else "integer"
    if pd.api.types.is_float_dtype(series):
        return "double precision"
    return "text"


def table_sql(name, entry):
    frame = pd.read_csv(ROOT / entry["file"], nrows=50_000, low_memory=False)
    columns = [snake(c) for c in entry["columns"]]
    lines = []
    for raw, column in zip(entry["columns"], columns, strict=True):
        nullable = frame[raw].isna().any() or raw in (
            "DepartmentId",
            "CategoryId",
            "StateId",
            "ForecastRoleKey",
            "ScaleAbs",
            "ScaleSquared",
            "ForecastMAE",
            "MacroMASE",
            "MacroRMSSE",
            "PooledRMSE",
            "PooledWAPEPercent",
        )
        lines.append(f"  {column} {sql_type(column, frame[raw])}{'' if nullable else ' not null'}")
    lines.append(f"  , primary key ({', '.join(PRIMARY[name])})".replace("  , ", "  "))
    for column, target in FOREIGN.get(name, []):
        lines.append(f"  foreign key ({column}) references app.{target} ({PRIMARY[target][0]})")
    for condition in CHECKS.get(name, []):
        lines.append(f"  check ({condition})")
    body = ",\n".join(lines)
    statements = [
        f"create table app.{name} (\n{body}\n);",
        f"alter table app.{name} enable row level security;",
        f"create policy {name}_read on app.{name} for select to app_reader using (true);",
    ]
    if name in ENGINE_TABLES:
        statements.append(f"create policy {name}_engine_read on app.{name} for select to engine_api using (true);")
        statements.append(f"grant select on app.{name} to engine_api;")
    statements.append(f"grant select on app.{name} to app_reader;")
    for index in INDEXES.get(name, []):
        statements.append(f"create index {name}_{'_'.join(index)}_idx on app.{name} ({', '.join(index)});")
    for column, _target in FOREIGN.get(name, []):
        if column not in PRIMARY[name][:1]:
            statements.append(f"create index {name}_{column}_fk_idx on app.{name} ({column});")
    return "\n".join(statements)


HEADER = """-- Phase 7B: curated, read-only scientific evidence for the web application.
-- Generated by apps/web/supabase/generate_schema.py from reports/webapp/export_manifest.json; reviewed.
-- Security model:
--   * schema app holds curated evidence; RLS is enabled on every table with SELECT-only policies;
--   * app_reader (NOLOGIN group) may SELECT every app table; webapp_api (login) inherits app_reader;
--   * engine_api (login) may SELECT only the four tables the simulation needs;
--   * anon, authenticated and PUBLIC receive no privileges on app or ops, so the browser cannot query them;
--   * no INSERT/UPDATE/DELETE policy exists: only the owner (seed script) can write.
-- Passwords are NEVER set here. The owner sets them once in the Supabase SQL editor:
--   alter role webapp_api with password '<generated secret>';  alter role engine_api with password '<...>';

create schema if not exists app;
create schema if not exists ops;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'app_reader') then
    create role app_reader nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'webapp_api') then
    create role webapp_api login noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'engine_api') then
    create role engine_api login noinherit;
  end if;
end
$$;

alter role webapp_api inherit;
grant app_reader to webapp_api;
alter role webapp_api set statement_timeout = '5s';
alter role engine_api set statement_timeout = '5s';
alter role webapp_api set idle_in_transaction_session_timeout = '10s';
alter role engine_api set idle_in_transaction_session_timeout = '10s';

revoke all on schema app from public;
revoke all on schema ops from public;
do $$
declare r text;
begin
  foreach r in array array['anon', 'authenticated'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format('revoke all on schema app from %I', r);
      execute format('revoke all on schema ops from %I', r);
    end if;
  end loop;
end
$$;
grant usage on schema app to app_reader, engine_api;
"""

FOOTER = """
-- Rate limiting shared across serverless instances. Buckets are SHA-256 hex digests of a salted client key,
-- never raw IP addresses. Only webapp_api may call the function; it cannot read or write the table directly.
create table ops.rate_limits (
  bucket text not null check (bucket ~ '^[0-9a-f]{64}$'),
  window_start timestamptz not null,
  hits integer not null default 0,
  primary key (bucket, window_start)
);
alter table ops.rate_limits enable row level security;

create function ops.rate_limit_hit(p_bucket text, p_max_hits integer, p_window_seconds integer)
returns boolean
language plpgsql
security definer
set search_path = pg_catalog, ops
as $$
declare
  v_window timestamptz;
  v_hits integer;
begin
  if p_bucket !~ '^[0-9a-f]{64}$' or p_max_hits < 1 or p_window_seconds not between 1 and 86400 then
    raise exception 'invalid rate limit request';
  end if;
  v_window := to_timestamp(floor(extract(epoch from now()) / p_window_seconds) * p_window_seconds);
  insert into ops.rate_limits as r (bucket, window_start, hits) values (p_bucket, v_window, 1)
  on conflict (bucket, window_start) do update set hits = r.hits + 1
  returning hits into v_hits;
  if random() < 0.01 then
    delete from ops.rate_limits where window_start < now() - interval '2 days';
  end if;
  return v_hits <= p_max_hits;
end
$$;

revoke all on function ops.rate_limit_hit(text, integer, integer) from public;
grant usage on schema ops to webapp_api;
grant execute on function ops.rate_limit_hit(text, integer, integer) to webapp_api;
"""


def build():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if set(ORDER) != set(manifest["tables"]):
        raise ValueError("Table order list differs from the export manifest")
    body = "\n\n".join(table_sql(name, manifest["tables"][name]) for name in ORDER)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(HEADER + "\n" + body + "\n" + FOOTER, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(ORDER)} tables)")


if __name__ == "__main__":
    build()
