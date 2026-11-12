"""Regression tests for the Phase 7D-1 client-side TLS verdict (run: python -m pytest apps/web/supabase/test_live_checks.py).

Context: `ping` once judged TLS from pg_stat_ssl, which behind Supavisor reports the pooler-to-Postgres backend link and
showed ssl=false although the client link used TLSv1.3. The verdict must come from libpq's client connection.
"""

import os
import socket
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from live_checks import client_tls, require_tls, tls_verdict  # noqa: E402

POOLER = "aws-1-eu-central-1.pooler.supabase.com"


class FakePgConn:
    def __init__(self, in_use, protocol):
        self.ssl_in_use = in_use
        self._attrs = {b"protocol": protocol.encode() if protocol else None, b"cipher": b"TLS_AES_256_GCM_SHA384"}

    def ssl_attribute(self, name):
        return self._attrs.get(name)


class FakeInfo:
    def __init__(self, host, sslmode):
        self.host, self._sslmode = host, sslmode
        self.dsn = f"host={host} sslmode={sslmode}" if sslmode else f"host={host}"

    def get_parameters(self):
        return {"sslmode": self._sslmode} if self._sslmode else {}


class FakeConn:
    def __init__(self, host, sslmode, in_use, protocol):
        self.pgconn, self.info = FakePgConn(in_use, protocol), FakeInfo(host, sslmode)


@pytest.mark.parametrize(
    ("host", "sslmode", "in_use", "protocol", "expected"),
    [
        (POOLER, "require", True, "TLSv1.3", "tls-encrypted"),
        (POOLER, "verify-full", True, "TLSv1.3", "tls-verified"),
        (POOLER, "verify-ca", True, "TLSv1.2", "tls-encrypted"),
        (POOLER, "prefer", True, "TLSv1.3", "insecure-sslmode:prefer"),
        (POOLER, "disable", False, None, "insecure-sslmode:disable"),
        (POOLER, None, True, "TLSv1.3", "insecure-sslmode:default(prefer)"),
        (POOLER, "require", False, None, "no-tls"),
        (POOLER, "require", True, "TLSv1.1", "weak-protocol:TLSv1.1"),
        ("127.0.0.1", None, False, None, "local"),
    ],
)
def test_tls_verdict(host, sslmode, in_use, protocol, expected):
    assert tls_verdict(host, sslmode, in_use, protocol) == expected


def test_regression_pooled_client_tls_passes_even_if_backend_link_is_plain():
    # The 7D-1 observation: pg_stat_ssl said false, but libpq's client link was TLSv1.3 with sslmode=require.
    facts = client_tls(FakeConn(POOLER, "require", True, "TLSv1.3"))
    assert facts["verdict"] == "tls-encrypted"
    assert require_tls(FakeConn(POOLER, "require", True, "TLSv1.3"))["negotiated"] == "TLSv1.3"


def test_driver_without_protocol_attribute_uses_enforced_floor():
    conn = FakeConn(POOLER, "require", True, None)
    del FakePgConn.ssl_attribute  # psycopg 3.2 binary has no ssl_attribute
    try:
        facts = client_tls(conn)
    finally:
        FakePgConn.ssl_attribute = lambda self, name: self._attrs.get(name)
    assert facts["negotiated"] is None and facts["min_protocol"] == "TLSv1.2" and facts["verdict"] == "tls-encrypted"


def test_insecure_remote_connections_are_refused():
    for conn in (FakeConn(POOLER, "prefer", True, "TLSv1.3"), FakeConn(POOLER, "require", False, None)):
        with pytest.raises(SystemExit):
            require_tls(conn)


def test_local_server_is_reported_local_and_never_counts_as_tls():
    url = os.environ.get("IDF_LOCAL_OWNER_URL", "postgresql://postgres:local-owner-only@127.0.0.1:54329/webapp")
    try:
        conn = psycopg.connect(url, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local test database not running")
    with conn:
        facts = client_tls(conn)
        with pytest.raises(SystemExit):
            require_tls(conn)
    assert facts["verdict"] == "local" and facts["ssl_in_use"] is False


def _pooler_reachable():
    try:
        socket.create_connection((POOLER, 5432), timeout=5).close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _pooler_reachable(), reason="pooler not reachable")
def test_verify_full_handshake_and_hostname_against_real_pooler(tmp_path):
    """Credential-free: a non-existent tenant is rejected only AFTER the TLS handshake, proving verify-full works.

    The root used here is taken from the server's own chain, so this proves the verify-full MECHANISM (chain + host
    name), not trust; production trust must come from the CA certificate downloaded from the Supabase dashboard.
    """
    chain = subprocess.run(
        ["openssl", "s_client", "-starttls", "postgres", "-connect", f"{POOLER}:5432", "-servername", POOLER, "-showcerts"],
        input="",
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    certs = [c + "-----END CERTIFICATE-----\n" for c in chain.split("-----END CERTIFICATE-----") if "BEGIN CERTIFICATE" in c]
    root = tmp_path / "root.crt"
    root.write_text(certs[-1][certs[-1].index("-----BEGIN") :], encoding="ascii")
    base = f"host={POOLER} port=5432 dbname=postgres user=tls_probe.nonexistenttenant0000 password=x connect_timeout=10"
    with pytest.raises(psycopg.OperationalError) as ok:
        psycopg.connect(f"{base} sslmode=verify-full sslrootcert={root.as_posix()}")
    assert "certificate" not in str(ok.value).lower() and "ssl" not in str(ok.value).lower()  # got past TLS
    with pytest.raises(psycopg.OperationalError) as wrong_host:
        psycopg.connect(
            f"{base} sslmode=verify-full sslrootcert={root.as_posix()} hostaddr={socket.gethostbyname(POOLER)} "
            f"host=not-the-pooler.example.com"
        )
    assert "certificate" in str(wrong_host.value).lower() or "does not match" in str(wrong_host.value).lower()
