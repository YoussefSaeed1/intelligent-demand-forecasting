"""Load the curated export into schema `app` in ONE transaction (truncate + COPY + verify), then commit.

Every CSV is verified against reports/webapp/export_manifest.json before loading, and row counts are
checked inside the transaction, so a partial or mismatched load is rolled back. The connection string is
read from the environment and never stored:
    WEBAPP_OWNER_DATABASE_URL  owner (postgres) connection string; for Supabase use the session pooler or
                               direct connection, never a client-side key.
Run with the engine environment (psycopg):  apps/engine/.venv/Scripts/python.exe apps/web/supabase/seed_database.py
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "reports/webapp/export_manifest.json"
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


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seed(url):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name in ORDER:
        entry = manifest["tables"][name]
        if sha256(ROOT / entry["file"]) != entry["sha256"]:
            raise SystemExit(f"Refusing: {name}.csv does not match the export manifest")
    with psycopg.connect(url) as conn:
        with conn.transaction():
            conn.execute("truncate " + ", ".join(f"app.{n}" for n in ORDER))
            for name in ORDER:
                entry = manifest["tables"][name]
                columns = ", ".join(snake(c) for c in entry["columns"])
                with (
                    open(ROOT / entry["file"], "rb") as source,
                    conn.cursor().copy(f"copy app.{name} ({columns}) from stdin with (format csv, header true)") as copy,
                ):
                    while chunk := source.read(1 << 20):
                        copy.write(chunk)
                rows = conn.execute(f"select count(*) from app.{name}").fetchone()[0]
                if rows != entry["rows"]:
                    raise RuntimeError(f"{name}: loaded {rows} rows, manifest {entry['rows']}; rolling back")
                print(f"{name:28s} {rows:>9,} rows")
            version = conn.execute("select export_version from app.provenance").fetchone()[0]
            if version != manifest["export_version"]:
                raise RuntimeError("Provenance version mismatch; rolling back")
        conn.execute("analyze")
    print(f"seeded export {manifest['export_version']} in one transaction")


if __name__ == "__main__":
    url = os.environ.get("WEBAPP_OWNER_DATABASE_URL")
    if not url:
        sys.exit("Set WEBAPP_OWNER_DATABASE_URL (owner connection string) in the environment")
    seed(url)
