"""Build and verify the Vercel WEBAPP_DATABASE_URL locally (owner-run; nothing secret is printed or written to disk).

  .\\apps\\engine\\.venv\\Scripts\\python.exe tools\\phase7d\\build_web_db_url.py

Prompts (password hidden) -> builds the transaction-pooler URL for webapp_api (port 6543, TLS) -> ONE real login through
Supavisor -> read-only probes, including the web app's lossless-float contract: inside a READ ONLY transaction,
set_config('extra_float_digits', '3', true) must make TEXT float8 output bit-identical to float8send, and the setting
must not survive the transaction (pooled sessions) -> on success copies the URL to the Windows clipboard for Vercel.
Prints only pass/fail facts (no host, user, password or URL).
"""

import getpass
import re
import struct
import subprocess
import urllib.parse

import psycopg

PROJECT_REF = "ecxswrwuylenwvsxghxg"
SAMPLE = """select historical_mean56 as v, float8send(historical_mean56) as b
            from app.series_origin_mean56 order by series_key, origin_key"""


def exact_rows(conn):
    """Text-format values (as postgres.js receives them) vs the stored binary bits."""
    rows = conn.execute(SAMPLE).fetchall()
    return [(struct.pack(">d", float(v)), bytes(b)) for v, b in rows]


def main():
    host = input("Pooler host (aws-N-eu-central-1.pooler.supabase.com): ").strip()
    if not re.fullmatch(r"aws-\d+-eu-central-1\.pooler\.supabase\.com", host):
        raise SystemExit("Unexpected pooler host")
    password = getpass.getpass("webapp_api password (hidden): ")
    if password != password.strip():
        raise SystemExit("The password has leading/trailing whitespace; check the password-manager entry")
    url = (
        f"postgresql://webapp_api.{PROJECT_REF}:{urllib.parse.quote(password, safe='')}@{host}:6543/postgres"
        "?sslmode=require&ssl_min_protocol_version=TLSv1.2"
    )
    checks = {}
    try:
        with psycopg.connect(url, connect_timeout=10, prepare_threshold=None, autocommit=True) as conn:
            checks["current_user=webapp_api"] = conn.execute("select current_user").fetchone()[0] == "webapp_api"
            checks["client_tls"] = bool(conn.pgconn.ssl_in_use)
            checks["validation_origins=8"] = conn.execute("select count(*) from app.validation_origins").fetchone()[0] == 8
            checks["no_write_privilege"] = not conn.execute(
                "select has_table_privilege('app.forecasts', 'insert') or has_table_privilege('app.series', 'update')"
            ).fetchone()[0]
            checks["rate_limit_function_executable"] = conn.execute(
                "select has_function_privilege('ops.rate_limit_hit(text, integer, integer)', 'execute')"
            ).fetchone()[0]
            checks["server_extra_float_digits=0 (defect present)"] = (
                conn.execute("show extra_float_digits").fetchone()[0] == "0"
            )
            lossy = exact_rows(conn)
            checks["lossy text alters values (defect reproduced)"] = any(t != b for t, b in lossy)
            with conn.transaction():
                conn.execute("set transaction read only")
                conn.execute("select set_config('extra_float_digits', '3', true)")
                inside = conn.execute("show extra_float_digits").fetchone()[0]
                fixed = exact_rows(conn)
            checks["set_config inside transaction = 3"] = inside == "3"
            checks[f"exact text == float8send for all {len(fixed)} values"] = len(fixed) > 3000 and all(
                t == b for t, b in fixed
            )
            checks["setting reset after commit (no pooled leak)"] = (
                conn.execute("show extra_float_digits").fetchone()[0] == "0"
            )
    except psycopg.OperationalError as error:
        reason = "password authentication failed" if "password authentication failed" in str(error) else type(error).__name__
        raise SystemExit(f"LOGIN FAILED ({reason}). Nothing copied. Re-check the webapp_api password entry.") from None
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if not all(checks.values()):
        raise SystemExit("A check failed; nothing copied")
    subprocess.run(["clip"], input=url.encode("utf-16-le"), check=True)  # Windows clipboard; never echoed
    print("ALL PASS. The verified WEBAPP_DATABASE_URL is on the clipboard. Paste it into Vercel (idf-web > Settings >")
    print("Environment Variables, Production only, Sensitive), then clear the clipboard: Set-Clipboard -Value ' '")


if __name__ == "__main__":
    main()
