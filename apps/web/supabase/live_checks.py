"""Phase 7D-1 live database checks against the Supabase project (no secrets printed or stored).

Connection strings come only from environment variables set by set_remote_env.ps1:
  WEBAPP_OWNER_DATABASE_URL  postgres via session pooler (5432)
  IDF_WEBAPP_URL             webapp_api via transaction pooler (6543)
  IDF_ENGINE_URL             engine_api via transaction pooler (6543)

  python live_checks.py ping            owner connectivity, before any import
  python live_checks.py set-passwords   hidden prompts; sends only SCRAM-SHA-256 verifiers for webapp_api/engine_api
  python live_checks.py checks   D-07 / provenance / holdout boundary / A-05 / A-09 / pooler logins

Same expectations as webapp_qa D-07, A-05 and A-09, but the application roles are tested by REAL logins through the
transaction pooler (on Supabase, postgres cannot SET ROLE to roles it created). anon/authenticated/service_role are probed
with SET LOCAL ROLE from the owner session. Results go to reports/webapp/phase7d/live_db_checks.json; errors are reduced to
SQLSTATE codes so no connection detail can leak.
"""

import base64
import getpass
import hashlib
import hmac
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import psycopg.conninfo
import psycopg.sql

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "reports/webapp/export_manifest.json"
OUT = ROOT / "reports/webapp/phase7d/live_db_checks.json"
FROZEN = {
    "PlanSha256": "63efc59ed0dc2b35b2ad3067fb790c0b42d0c1f279e3f8142519b78c07cce76e",
    "ExecutionSha256": "b55ba4a0c9c8fafb2ee3997f38d2f31efea99f4157033e70288814a2006c87c3",
    "SelectionFingerprint": "a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb",
    "LedgerSha256": "fa2af529b50299b50c8d77d67b0ce70f73fab35e4731a5b825dd27a20e4bc204",
}
PROBES = (
    ("select", "select count(*) from app.series"),
    ("actuals", "select count(*) from app.validation_actuals"),
    ("insert", "insert into app.limitations values ('X', 'x', 'x')"),
    ("update", "update app.series set series_id = series_id"),
    ("delete", "delete from app.limitations"),
    ("ddl", "create table app.intruder(x int)"),
)


class _Rollback(Exception):
    pass


SECURE_SSLMODES = {"require", "verify-ca", "verify-full"}
LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def tls_verdict(host, sslmode, ssl_in_use, protocol):
    """TLS judgement for the CLIENT connection, as reported by libpq.

    pg_stat_ssl is deliberately not used: behind a pooler it describes the pooler-to-Postgres backend link, not the
    client link (the Phase 7D-1 false negative). A remote connection passes only with TLS in use, TLS >= 1.2 and an sslmode
    that refuses plaintext. Loopback test servers are reported as 'local' and are never accepted by `ping`.
    """
    if host in LOOPBACK:
        return "local"
    if sslmode not in SECURE_SSLMODES:
        return f"insecure-sslmode:{sslmode or 'default(prefer)'}"
    if not ssl_in_use:
        return "no-tls"
    if protocol not in ("TLSv1.2", "TLSv1.3"):
        return f"weak-protocol:{protocol}"
    return "tls-verified" if sslmode == "verify-full" else "tls-encrypted"


def client_tls(conn):
    """Read TLS facts from the driver side of the connection (no secrets: sslmode, TLS floor, in-use flag only).

    psycopg 3.2's binary libpq wrapper exposes `ssl_in_use` but not the negotiated protocol, so the protocol floor is
    ENFORCED on the client with ssl_min_protocol_version (set by set_remote_env.ps1; libpq >= 16 defaults to TLSv1.2).
    """
    pg = conn.pgconn
    params = conn.info.get_parameters()
    dsn = psycopg.conninfo.conninfo_to_dict(conn.info.dsn)
    sslmode = params.get("sslmode") or dsn.get("sslmode")
    floor = params.get("ssl_min_protocol_version") or dsn.get("ssl_min_protocol_version") or "TLSv1.2"
    negotiated = None
    if hasattr(pg, "ssl_attribute"):
        raw = pg.ssl_attribute(b"protocol")
        negotiated = raw.decode() if raw else None
    facts = {"sslmode": sslmode, "ssl_in_use": bool(pg.ssl_in_use), "min_protocol": floor, "negotiated": negotiated}
    facts["verdict"] = tls_verdict(conn.info.host, sslmode, facts["ssl_in_use"], negotiated or floor)
    return facts


def require_tls(conn, allow_local=False):
    facts = client_tls(conn)
    accepted = facts["verdict"] in ("tls-encrypted", "tls-verified") or (allow_local and facts["verdict"] == "local")
    if not accepted:
        raise SystemExit(f"Refusing: client connection is not secure ({facts['verdict']})")
    return facts


def env(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"{name} is not set; dot-source apps/web/supabase/set_remote_env.ps1 first")
    return value


def safe(error):
    return f"denied:{getattr(error, 'sqlstate', None) or type(error).__name__}"


def probe(conn, sql, role=None, params=None):
    """Run one statement in a transaction that is always rolled back; return the outcome only."""
    try:
        with conn.transaction():
            if role:
                conn.execute(f"set local role {role}")
            row = conn.execute(sql, params).fetchone() if sql.lstrip().startswith("select") else conn.execute(sql, params)
            raise _Rollback(row)
    except _Rollback as done:
        value = done.args[0]
        return ("allowed", value[0]) if isinstance(value, tuple) else ("allowed", None)
    except psycopg.Error as error:
        return (safe(error), None)


def scram_verifier(password, iterations=4096):
    """Client-side SCRAM-SHA-256 verifier, as psql's password command builds it: the plaintext never reaches the server."""
    if not password.isascii() or len(password) < 24:
        raise SystemExit("Use an ASCII password of at least 24 characters (e.g. secrets.token_urlsafe(32))")
    salt = os.urandom(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()

    def b64(raw):
        return base64.b64encode(raw).decode()

    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(hashlib.sha256(client_key).digest())}:{b64(server_key)}"


def set_passwords():
    with psycopg.connect(env("WEBAPP_OWNER_DATABASE_URL"), connect_timeout=10, autocommit=True) as conn:
        require_tls(conn)
        for role in ("webapp_api", "engine_api"):
            first = getpass.getpass(f"New password for {role} (hidden): ")
            if first != getpass.getpass(f"Repeat password for {role} (hidden): "):
                raise SystemExit(f"Passwords for {role} did not match; nothing changed for {role}")
            verifier = scram_verifier(first)
            conn.execute(
                psycopg.sql.SQL("alter role {} with password {}").format(
                    psycopg.sql.Identifier(role), psycopg.sql.Literal(verifier)
                )
            )
            print(f"{role}: SCRAM verifier set")
    return True


def ping():
    with psycopg.connect(env("WEBAPP_OWNER_DATABASE_URL"), connect_timeout=10) as conn:
        tls = client_tls(conn)
        user, version, backend_ssl = conn.execute(
            "select current_user, current_setting('server_version'), "
            "coalesce((select ssl::text from pg_stat_ssl where pid = pg_backend_pid()), 'unknown')"
        ).fetchone()
        tables = conn.execute("select count(*) from pg_tables where schemaname = 'app'").fetchone()[0]
    print(f"connected: user={user} server={version} app_tables={tables}")
    print(
        f"client TLS: verdict={tls['verdict']} sslmode={tls['sslmode']} in_use={tls['ssl_in_use']} "
        f"min_protocol={tls['min_protocol']} negotiated={tls['negotiated'] or 'not exposed by driver'}"
    )
    print(f"backend link ssl (pooler-to-Postgres, informational only)={backend_ssl}")
    ok = user == "postgres" and tables == 20 and tls["verdict"] in ("tls-encrypted", "tls-verified")
    print("PING PASS" if ok else "PING FAIL")
    return ok


def checks():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = {
        "project": "ecxswrwuylenwvsxghxg",
        "checked_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "export_version": manifest["export_version"],
        "gates": {},
    }
    gates = result["gates"]

    tls = {}
    with psycopg.connect(env("WEBAPP_OWNER_DATABASE_URL"), connect_timeout=10, autocommit=True) as owner:
        tls["postgres"] = require_tls(owner, allow_local=True)
        # D-07: row counts, provenance, sizes
        counts = {name: owner.execute(f'select count(*) from app."{name}"').fetchone()[0] for name in manifest["tables"]}
        mismatches = {n: [c, manifest["tables"][n]["rows"]] for n, c in counts.items() if c != manifest["tables"][n]["rows"]}
        prov = owner.execute(
            "select export_version, plan_sha256, execution_sha256, selection_fingerprint, ledger_sha256, "
            "final_holdout_targets_read from app.provenance"
        ).fetchall()
        app_mb, db_mb = owner.execute(
            "select (select sum(pg_total_relation_size(c.oid)) from pg_class c "
            "join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'app' and c.relkind = 'r') / 1e6, "
            "pg_database_size(current_database()) / 1e6"
        ).fetchone()
        prov_ok = (
            len(prov) == 1
            and prov[0][0] == manifest["export_version"]
            and prov[0][1] == FROZEN["PlanSha256"]
            and prov[0][2] == FROZEN["ExecutionSha256"]
            and prov[0][3] == FROZEN["SelectionFingerprint"]
            and prov[0][4] == FROZEN["LedgerSha256"]
            and prov[0][5] is False
        )
        gates["D-07"] = {
            "pass": not mismatches and prov_ok,
            "total_rows": sum(counts.values()),
            "mismatches": mismatches,
            "provenance_matches_frozen_hashes": prov_ok,
            "app_schema_mb": round(float(app_mb), 1),
            "database_mb": round(float(db_mb), 1),
        }
        # Validation-only boundary: no history or actuals on/after each dataset's final-holdout start.
        leaks = owner.execute(
            "select (select count(*) from app.series_history h join app.validation_origins o using (origin_key) "
            "join app.datasets d using (dataset_key) where h.date >= d.test_start) + "
            "(select count(*) from app.validation_actuals a join app.validation_origins o using (origin_key) "
            "join app.datasets d using (dataset_key) where a.date >= d.test_start) + "
            "(select count(*) from app.forecasts f join app.validation_origins o using (origin_key) "
            "join app.datasets d using (dataset_key) where f.date >= d.test_start)"
        ).fetchone()[0]
        gates["holdout_boundary"] = {"pass": leaks == 0, "rows_on_or_after_test_start": leaks}
        # A-05 / A-09 for Supabase's own roles via SET LOCAL ROLE
        supa = {}
        for role in ("anon", "authenticated", "service_role"):
            for label, sql in PROBES:
                supa[f"{role}.{label}"] = probe(owner, sql, role)[0]
            supa[f"{role}.rate_limit"] = probe(owner, "select ops.rate_limit_hit(%s, 2, 60)", role, ("a" * 64,))[0]

    # A-05 / A-09 for the application roles via REAL transaction-pooler logins
    apps, logins = {}, {}
    for role, var in (("webapp_api", "IDF_WEBAPP_URL"), ("engine_api", "IDF_ENGINE_URL")):
        with psycopg.connect(env(var), connect_timeout=10, prepare_threshold=None) as conn:
            tls[role] = require_tls(conn, allow_local=True)
            who = conn.execute("select current_user, current_setting('statement_timeout')").fetchone()
            conn.rollback()
            logins[role] = {"current_user": who[0], "statement_timeout": who[1], "port": 6543}
            for label, sql in PROBES:
                apps[f"{role}.{label}"] = probe(conn, sql)[0]
            apps[f"{role}.rate_limit"] = probe(conn, "select ops.rate_limit_hit(%s, 2, 60)", params=("a" * 64,))
            apps[f"{role}.rate_limit"] = apps[f"{role}.rate_limit"][0] + (
                f":{apps[f'{role}.rate_limit'][1]}" if apps[f"{role}.rate_limit"][1] is not None else ""
            )
            if role == "webapp_api":
                apps["webapp_api.rate_limit_bad_bucket"] = probe(
                    conn, "select ops.rate_limit_hit(%s, 2, 60)", params=("not-a-hash",)
                )[0]
    outcomes = {**supa, **apps}
    expected_allowed = {"webapp_api.select", "webapp_api.actuals", "engine_api.actuals", "webapp_api.rate_limit"}
    wrong = {}
    for key, value in outcomes.items():
        allowed = value.startswith("allowed")
        if key == "webapp_api.rate_limit_bad_bucket":
            if allowed:
                wrong[key] = value
        elif key == "webapp_api.rate_limit":
            if value != "allowed:True":
                wrong[key] = value
        elif allowed != (key in expected_allowed):
            wrong[key] = value
    gates["A-05"] = {"pass": not {k: v for k, v in wrong.items() if "rate_limit" not in k}, "probes": len(PROBES) * 5}
    gates["A-09"] = {
        "pass": not {k: v for k, v in wrong.items() if "rate_limit" in k},
        "webapp_api": outcomes["webapp_api.rate_limit"],
        "engine_api": outcomes["engine_api.rate_limit"],
        "anon": outcomes["anon.rate_limit"],
        "bad_bucket": outcomes["webapp_api.rate_limit_bad_bucket"],
    }
    gates["pooler_logins"] = {
        "pass": logins["webapp_api"]["current_user"] == "webapp_api"
        and logins["engine_api"]["current_user"] == "engine_api",
        **logins,
    }
    gates["client_tls"] = {
        "pass": all(t["verdict"] in ("tls-encrypted", "tls-verified") for t in tls.values()),
        **{r: f"{t['verdict']} sslmode={t['sslmode']} min={t['min_protocol']}" for r, t in tls.items()},
    }
    result["unexpected"] = wrong
    result["outcomes"] = outcomes
    result["overall"] = "PASS" if all(g["pass"] for g in gates.values()) else "FAIL"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for name, gate in gates.items():
        print(
            f"{name:17s} {'PASS' if gate['pass'] else 'FAIL'}  "
            + json.dumps({k: v for k, v in gate.items() if k != "pass"})[:180]
        )
    if wrong:
        print("unexpected outcomes:", json.dumps(wrong))
    print(f"OVERALL {result['overall']} -> {OUT.relative_to(ROOT)}")
    return result["overall"] == "PASS"


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    modes = {"ping": ping, "checks": checks, "set-passwords": set_passwords}
    if mode not in modes:
        sys.exit("usage: live_checks.py ping|set-passwords|checks")
    sys.exit(0 if modes[mode]() else 1)
