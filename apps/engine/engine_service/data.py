"""Read-only evidence access through the engine_api role (SELECT on four tables only)."""

import numpy as np
import psycopg
import psycopg.conninfo
from inventory_service.planner import FORECAST_ROLES, PlannerInputs

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
SECURE_SSLMODES = {"require", "verify-ca", "verify-full"}
ALLOWED_TLS_FLOORS = {None, "TLSv1.2", "TLSv1.3"}


class NotFound(Exception):
    pass


class InsecureDatabaseUrl(Exception):
    """The configured database URL would allow a plaintext or downgraded remote connection."""


def validate_database_url(url):
    """Require TLS for every non-loopback database: sslmode must refuse plaintext and the TLS floor must be >= 1.2.

    libpq's default sslmode ('prefer') silently falls back to plaintext, so it is rejected. Only loopback test servers
    may omit TLS. The URL is never echoed (it contains the password).
    """
    try:
        params = psycopg.conninfo.conninfo_to_dict(url)
    except psycopg.ProgrammingError as error:
        raise InsecureDatabaseUrl("unparseable database URL") from error
    hosts = {h for h in str(params.get("host") or "").split(",") if h}
    if hosts and hosts <= LOOPBACK_HOSTS:
        return
    if params.get("sslmode") not in SECURE_SSLMODES:
        raise InsecureDatabaseUrl("remote database URL must set sslmode=require, verify-ca or verify-full")
    if params.get("ssl_min_protocol_version") not in ALLOWED_TLS_FLOORS:
        raise InsecureDatabaseUrl("ssl_min_protocol_version below TLSv1.2")


def connect(url):
    validate_database_url(url)
    # prepare_threshold=None keeps the connection compatible with Supabase's transaction pooler.
    return psycopg.connect(url, connect_timeout=5, prepare_threshold=None, autocommit=True)


def load_inputs(conn, series_key, origin_key):
    dataset = series_key.split("|")[0]
    origin = conn.execute(
        "select origin_date, validation_start from app.validation_origins where origin_key = %s", (origin_key,)
    ).fetchone()
    if origin is None:
        raise NotFound("origin")
    demand = conn.execute(
        "select units from app.validation_actuals where series_key = %s and origin_key = %s order by date",
        (series_key, origin_key),
    ).fetchall()
    if len(demand) != 28:
        raise NotFound("series")
    mean = conn.execute(
        "select historical_mean56 from app.series_origin_mean56 where series_key = %s and origin_key = %s",
        (series_key, origin_key),
    ).fetchone()
    rows = conn.execute(
        "select model_key, forecast from app.forecasts where series_key = %s and origin_key = %s "
        "order by model_key, horizon_day",
        (series_key, origin_key),
    ).fetchall()
    forecasts = {}
    for role in FORECAST_ROLES:
        values = [f for m, f in rows if m == f"{dataset}|{role}"]
        if len(values) != 28:
            raise NotFound("forecast")
        forecasts[role] = np.asarray(values, dtype=float)
    if mean is None:
        raise NotFound("series")
    return PlannerInputs(
        origin_date=origin[0].isoformat(),
        validation_start=origin[1].isoformat(),
        demand=np.asarray([d[0] for d in demand], dtype=float),
        historical_mean56=float(mean[0]),
        forecasts=forecasts,
    )
