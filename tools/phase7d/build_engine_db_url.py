"""Build and verify the Vercel ENGINE_DATABASE_URL locally (owner-run; nothing secret is printed or written to disk).

  .\\apps\\engine\\.venv\\Scripts\\python.exe tools\\phase7d\\build_engine_db_url.py

Prompts (password hidden) -> builds the transaction-pooler URL for engine_api with URL encoding and enforced TLS ->
validates it with the engine's own TLS guard -> performs ONE real login as engine_api and a read-only probe -> on
success copies the URL to the Windows clipboard so it can be pasted into Vercel, then clear the clipboard.
"""

import getpass
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps/engine"))
from engine_service.data import validate_database_url  # noqa: E402

PROJECT_REF = "ecxswrwuylenwvsxghxg"


def main():
    host = input("Pooler host (aws-N-eu-central-1.pooler.supabase.com): ").strip()
    if not re.fullmatch(r"aws-\d+-eu-central-1\.pooler\.supabase\.com", host):
        raise SystemExit("Unexpected pooler host")
    password = getpass.getpass("engine_api password (hidden): ")
    if password != password.strip():
        raise SystemExit(
            "The password has leading/trailing whitespace; check the password-manager entry"
        )
    url = (
        f"postgresql://engine_api.{PROJECT_REF}:{urllib.parse.quote(password, safe='')}@{host}:6543/postgres"
        "?sslmode=require&ssl_min_protocol_version=TLSv1.2"
    )
    validate_database_url(url)  # same guard as the deployed engine
    try:
        with psycopg.connect(
            url, connect_timeout=10, prepare_threshold=None, autocommit=True
        ) as conn:
            user, tls = (
                conn.execute("select current_user, true").fetchone()[0],
                conn.pgconn.ssl_in_use,
            )
            rows = conn.execute("select count(*) from app.validation_origins").fetchone()[0]
    except psycopg.OperationalError as error:
        reason = (
            "password authentication failed"
            if "password authentication failed" in str(error)
            else type(error).__name__
        )
        raise SystemExit(
            f"LOGIN FAILED ({reason}). Nothing copied. Re-check the engine_api password entry."
        ) from None
    print(
        f"LOGIN OK: current_user={user} client_tls={bool(tls)} validation_origins={rows} (expected 8)"
    )
    if user != "engine_api" or not tls or rows != 8:
        raise SystemExit("Unexpected result; nothing copied")
    subprocess.run(
        ["clip"], input=url.encode("utf-16-le"), check=True
    )  # Windows clipboard; never echoed
    print(
        "The verified ENGINE_DATABASE_URL is on the clipboard. Paste it into Vercel, then run: Set-Clipboard -Value ' '"
    )


if __name__ == "__main__":
    main()
