"""TLS guard for the engine's database URL (Phase 7D-2 P-1). No database needed; nothing here connects."""

import pytest

from engine_service.data import InsecureDatabaseUrl, validate_database_url

POOLER = "aws-1-eu-central-1.pooler.supabase.com"
CRED = "engine_api.ref:pw"  # placeholder; validation never connects


@pytest.mark.parametrize("query", [
    "sslmode=require",
    "sslmode=require&ssl_min_protocol_version=TLSv1.2",
    "sslmode=verify-full&sslrootcert=/tmp/ca.crt",
    "sslmode=verify-ca&ssl_min_protocol_version=TLSv1.3",
])
def test_remote_urls_with_tls_are_accepted(query):
    validate_database_url(f"postgresql://{CRED}@{POOLER}:6543/postgres?{query}")


@pytest.mark.parametrize("query", [
    "",                      # libpq default 'prefer' can fall back to plaintext
    "sslmode=prefer",
    "sslmode=allow",
    "sslmode=disable",
    "sslmode=require&ssl_min_protocol_version=TLSv1",
    "sslmode=require&ssl_min_protocol_version=TLSv1.1",
])
def test_remote_urls_without_enforced_tls_are_rejected(query):
    with pytest.raises(InsecureDatabaseUrl):
        validate_database_url(f"postgresql://{CRED}@{POOLER}:6543/postgres" + (f"?{query}" if query else ""))


def test_loopback_test_server_may_omit_tls():
    validate_database_url("postgresql://engine_api:local@127.0.0.1:54329/webapp")
    validate_database_url("postgresql://engine_api:local@localhost:54329/webapp")


def test_mixed_host_list_requires_tls():
    with pytest.raises(InsecureDatabaseUrl):
        validate_database_url(f"host=127.0.0.1,{POOLER} user=engine_api dbname=postgres")


def test_error_message_never_contains_the_url():
    secret = "s3cr3t-password-value"
    with pytest.raises(InsecureDatabaseUrl) as caught:
        validate_database_url(f"postgresql://engine_api:{secret}@{POOLER}:6543/postgres")
    assert secret not in str(caught.value) and POOLER not in str(caught.value)
