"""Private FastAPI simulation service. Reachable only with the shared engine key (server-to-server).

Security: constant-time key check; strict Pydantic bounds plus the engine's own Scenario validation;
realised demand and forecasts are loaded server-side (never accepted from the caller); body size and
concurrency caps; generic error bodies without traces, SQL or paths.
"""

import hashlib
import hmac
import logging
import os
import threading
import time
import uuid
from pathlib import Path

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from intelligent_demand.inventory import design, engine
from inventory_service.planner import run_planner, scenario_from

from engine_service.data import InsecureDatabaseUrl, NotFound, connect, load_inputs
from engine_service.schemas import SimulateRequest

LOG = logging.getLogger("engine")
logging.basicConfig(level=logging.INFO, format="%(message)s")
MAX_BODY = 8 * 1024
SLOTS = threading.BoundedSemaphore(int(os.environ.get("ENGINE_MAX_CONCURRENCY", "4")))
ENGINE_VERSION = hashlib.sha256(b"".join(Path(m.__file__).read_bytes() for m in (engine, design))).hexdigest()[:16]

app = FastAPI(title="IDF inventory engine", docs_url=None, redoc_url=None, openapi_url=None)


def error(status, code, message, request_id=None):
    return JSONResponse({"error": code, "message": message, "requestId": request_id}, status_code=status)


def configured_key():
    key = os.environ.get("ENGINE_SHARED_KEY", "")
    return key if len(key) >= 32 else None


@app.middleware("http")
async def guard(request: Request, call_next):
    request_id = request.headers.get("x-request-id", "")[:64] or uuid.uuid4().hex
    request.state.request_id = request_id
    length = request.headers.get("content-length")
    if length is not None and (not length.isdigit() or int(length) > MAX_BODY):
        return error(413, "payload_too_large", "Request body too large", request_id)
    if request.method == "POST" and request.url.path == "/simulate":
        # Authenticate from headers BEFORE the body is parsed or validated, so unauthenticated callers learn nothing
        # about the request schema. Constant-time comparison; the handler re-checks as defence in depth.
        key = configured_key()
        if key is None:
            return error(503, "not_configured", "Simulation service is not configured", request_id)
        if not hmac.compare_digest(request.headers.get("x-engine-key", "").encode(), key.encode()):
            return error(401, "unauthorized", "Missing or invalid service credentials", request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # never leak internals: class name only, no message or traceback (may carry host names)
        LOG.error("unhandled error request_id=%s type=%s", request_id, type(exc).__name__)
        response = error(500, "internal_error", "The simulation could not be completed", request_id)
    LOG.info(
        '{"request_id":"%s","path":"%s","status":%d,"ms":%.1f}',
        request_id,
        request.url.path,
        response.status_code,
        1000 * (time.perf_counter() - started),
    )
    response.headers["x-request-id"] = request_id
    response.headers["cache-control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_failed(request: Request, exc: RequestValidationError):
    fields = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        {
            "error": "invalid_request",
            "message": "Invalid simulation request",
            "fields": fields,
            "requestId": request.state.request_id,
        },
        status_code=400,
    )


@app.get("/health")
def health():
    return {"status": "ok", "engineVersion": ENGINE_VERSION, "keyConfigured": configured_key() is not None}


@app.post("/simulate")
def simulate(body: SimulateRequest, request: Request):
    request_id = request.state.request_id
    key = configured_key()
    supplied = request.headers.get("x-engine-key", "")
    if key is None:
        return error(503, "not_configured", "Simulation service is not configured", request_id)
    if not hmac.compare_digest(supplied.encode(), key.encode()):
        return error(401, "unauthorized", "Missing or invalid service credentials", request_id)
    if not SLOTS.acquire(blocking=False):
        return error(503, "busy", "Simulation capacity reached; retry shortly", request_id)
    try:
        url = os.environ.get("ENGINE_DATABASE_URL")
        if not url:
            return error(503, "not_configured", "Simulation service is not configured", request_id)
        try:
            with connect(url) as conn:
                inputs = load_inputs(conn, body.series_key, body.origin_key)
        except NotFound:
            return error(404, "not_found", "Unknown series or origin", request_id)
        except InsecureDatabaseUrl:
            # Misconfiguration (e.g. missing sslmode=require): refuse without connecting; never echo the URL.
            return error(503, "not_configured", "Simulation service is not configured", request_id)
        except psycopg.OperationalError as exc:
            # Login, network or pooler failure. One line, no message text (libpq messages include host names).
            LOG.warning("database_unavailable request_id=%s sqlstate=%s", request_id, getattr(exc, "sqlstate", None))
            return error(503, "database_unavailable", "Simulation data is temporarily unavailable", request_id)
        try:
            scenario = scenario_from(body.scenario.engine_parameters())
        except (ValueError, TypeError):
            return error(400, "invalid_request", "Scenario rejected by the engine", request_id)
        result = run_planner(inputs, scenario, tuple(body.policies))
        return {
            "engineVersion": ENGINE_VERSION,
            "seriesKey": body.series_key,
            "originKey": body.origin_key,
            "historicalMean56": inputs.historical_mean56,
            **result,
        }
    finally:
        SLOTS.release()
