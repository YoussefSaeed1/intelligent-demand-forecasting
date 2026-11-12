"""Engine service API and security tests against the local Postgres (engine_api role, read-only)."""

import json
from pathlib import Path

import numpy as np
import psycopg
import pyarrow.parquet as pq
import pytest
import yaml
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[3]
LOCAL_ENGINE_URL = "postgresql://engine_api:local-engine-only@127.0.0.1:54329/webapp"
KEY = "k" * 48
BASE_BODY = {
    "seriesKey": "store_item|1:11",
    "originKey": "store_item|1",
    "policies": ["selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point"],
}


def database_available():
    try:
        with psycopg.connect(LOCAL_ENGINE_URL, connect_timeout=2):
            return True
    except psycopg.Error:
        return False


pytestmark = pytest.mark.skipif(not database_available(), reason="local test database not running")


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ENGINE_SHARED_KEY", KEY)
    monkeypatch.setenv("ENGINE_DATABASE_URL", LOCAL_ENGINE_URL)
    from engine_service.app import app

    return TestClient(app, raise_server_exceptions=False)


def post(client, body, key=KEY, **headers):
    return client.post("/simulate", json=body, headers={"x-engine-key": key, **headers})


def assert_no_internals(response):
    text = response.text.lower()
    for marker in ("traceback", 'file "', ".py", "select ", "psycopg", "c:\\", "/users/"):
        assert marker not in text, (marker, response.text)


def test_bounds_mirror_the_declared_configuration():
    from engine_service.schemas import BOUNDS

    declared = yaml.safe_load((REPO / "configs/webapp.yaml").read_text(encoding="utf-8"))["planner_bounds"]
    assert {k: tuple(v) for k, v in declared.items()} == BOUNDS


def test_health_reports_engine_version_without_secrets(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["keyConfigured"] is True and len(body["engineVersion"]) == 16
    assert KEY not in json.dumps(body)


@pytest.mark.parametrize("key", ["", "wrong", KEY[:-1] + "x"])
def test_missing_or_wrong_key_is_rejected(client, key):
    response = post(client, BASE_BODY, key=key)
    assert response.status_code == 401
    assert_no_internals(response)


def test_unconfigured_key_refuses_to_run(client, monkeypatch):
    monkeypatch.setenv("ENGINE_SHARED_KEY", "short")
    assert post(client, BASE_BODY, key="short").status_code == 503


@pytest.mark.parametrize(
    "change",
    [
        {"scenario": {"leadDays": 15}},
        {"scenario": {"leadDays": -1}},
        {"scenario": {"leadDays": 2.5}},
        {"scenario": {"reviewDays": 0}},
        {"scenario": {"reviewDays": 8}},
        {"scenario": {"bufferDays": 7.5}},
        {"scenario": {"holdingCost": 0}},
        {"scenario": {"shortageCost": 51}},
        {"scenario": {"terminalCost": 2}},
        {"scenario": {"variabilityMultiplier": 1.6}},
        {"scenario": {"unknown": 1}},
        {"policies": []},
        {"policies": ["selected_ml", "selected_ml"]},
        {"policies": ["oracle"]},
        {"seriesKey": "store_item|1:11;drop"},
        {"originKey": "store_item|5"},
        {"originKey": "m5|1"},
        {"demand": [1] * 28},
        {"forecasts": {"x": 1}},
    ],
)
def test_invalid_requests_return_400_without_internals(client, change):
    body = BASE_BODY | change
    if "scenario" in change:
        body = BASE_BODY | {"scenario": change["scenario"]}
    response = post(client, body)
    assert response.status_code == 400, response.text
    assert response.json()["error"] == "invalid_request"
    assert_no_internals(response)


def test_client_cannot_supply_demand_or_forecasts(client):
    """Realised demand is loaded server-side; any attempt to pass it is rejected, not silently used."""
    assert post(client, BASE_BODY | {"demand": [0] * 28}).status_code == 400


def test_unknown_series_returns_404(client):
    response = post(client, BASE_BODY | {"seriesKey": "store_item|9:999"})
    assert response.status_code == 404
    assert_no_internals(response)


def test_oversized_body_is_rejected(client):
    response = client.post(
        "/simulate", content=b"{" + b" " * 9000 + b"}", headers={"x-engine-key": KEY, "content-type": "application/json"}
    )
    assert response.status_code == 413


def test_response_shape_and_no_store(client):
    response = post(client, BASE_BODY)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    body = response.json()
    assert [p["policy"] for p in body["policies"]] == BASE_BODY["policies"]
    assert len(body["dates"]) == 28 and len(body["demand"]) == 28
    assert all(len(p["daily"]) == 28 for p in body["policies"])


@pytest.mark.parametrize("scenario_id", ["base", "lead_long", "variability_high", "weekly_review"])
@pytest.mark.parametrize("dataset,series", [("store_item", "1:11"), ("m5", "4:CA_1FOODS_1_001")])
def test_service_reproduces_saved_phase5_results(client, dataset, series, scenario_id):
    """A-08: the full HTTP path through Postgres reproduces the saved Phase 5 per-series outputs."""
    plan = json.loads((REPO / "artifacts/inventory/phase5/plan.json").read_text(encoding="utf-8"))
    scenario = next(s for s in plan["scenarios"] if s["identifier"] == scenario_id)
    camel = {
        "lead_days": "leadDays",
        "review_days": "reviewDays",
        "buffer_days": "bufferDays",
        "initial_cover_days": "initialCoverDays",
        "holding_cost": "holdingCost",
        "shortage_cost": "shortageCost",
        "fixed_order_cost": "fixedOrderCost",
        "variable_order_cost": "variableOrderCost",
        "terminal_cost": "terminalCost",
        "variability_multiplier": "variabilityMultiplier",
    }
    body = {
        "seriesKey": f"{dataset}|{series}",
        "originKey": f"{dataset}|2",
        "policies": ["selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point"],
        "scenario": {camel[k]: scenario[k] for k in camel},
    }
    response = post(client, body)
    assert response.status_code == 200, response.text
    results = {p["policy"]: p["summary"] for p in response.json()["policies"]}
    for status_path in (REPO / "artifacts/inventory/phase5/runs").glob("*/status.json"):
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if (status["dataset"], status["fold"]["number"], status["scenario"]["identifier"]) != (dataset, 2, scenario_id):
            continue
        saved = pq.read_table(REPO / status["files"]["series"]["path"]).to_pandas()
        row = saved[saved.series_id == series].iloc[0]
        for field, value in results[status["policy"]].items():
            if value is None:
                assert row[field] != row[field]
            else:
                assert np.isclose(value, row[field], rtol=1e-9, atol=1e-9), (status["policy"], field)


def test_insecure_remote_database_url_is_refused_without_connecting(client, monkeypatch):
    # Phase 7D-2 P-1: a remote URL without sslmode=require must never be used (libpq 'prefer' can downgrade to plaintext).
    monkeypatch.setenv("ENGINE_DATABASE_URL", "postgresql://engine_api.ref:placeholder@db.invalid.example:6543/postgres")
    response = post(client, BASE_BODY)
    assert response.status_code == 503
    assert response.json()["error"] == "not_configured"
    assert "invalid.example" not in response.text and "placeholder" not in response.text
    assert_no_internals(response)


# ---- Phase 7D-2 P-3 regressions (production root cause: wrong database password -> unhandled 500) ----


@pytest.mark.parametrize("body", [{}, {"seriesKey": 1}, {"unexpected": "field"}])
def test_key_is_checked_before_body_validation(client, body):
    for key in ("", "x" * 48):
        response = post(client, body, key=key)
        assert response.status_code == 401, (key, response.text)
        assert "fields" not in response.json()  # no schema detail for unauthenticated callers
    assert post(client, body).status_code == 400  # with the right key, validation still applies


def test_database_login_failure_is_a_generic_503_for_valid_and_unknown_series(client, monkeypatch):
    monkeypatch.setenv("ENGINE_DATABASE_URL", "postgresql://engine_api:definitely-wrong@127.0.0.1:54329/webapp")
    for series in ("store_item|1:11", "store_item|9:999"):
        response = post(client, {**BASE_BODY, "seriesKey": series})
        assert response.status_code == 503, response.text
        assert response.json()["error"] == "database_unavailable"
        assert "definitely-wrong" not in response.text and "127.0.0.1" not in response.text
        assert_no_internals(response)


def test_unexpected_errors_log_the_class_only(client, monkeypatch, caplog):
    import engine_service.app as service

    def boom(*args, **kwargs):
        raise RuntimeError("host aws-1-example.pooler password=leaky")

    monkeypatch.setattr(service, "run_planner", boom)
    with caplog.at_level("INFO", logger="engine"):
        response = post(client, BASE_BODY)
    assert response.status_code == 500 and response.json()["error"] == "internal_error"
    assert_no_internals(response)
    logged = "\n".join(r.getMessage() + (r.exc_text or "") for r in caplog.records)
    assert "RuntimeError" in logged and "leaky" not in logged and "aws-1-example" not in logged


@pytest.mark.parametrize(
    ("label", "kwargs", "status"),
    [
        ("missing key", {"key": ""}, 401),
        ("wrong key", {"key": "w" * 40 + "SENSITIVE-KEY-VALUE"}, 401),
    ],
)
def test_early_rejections_are_logged_without_sensitive_values(client, caplog, label, kwargs, status):
    with caplog.at_level("INFO", logger="engine"):
        response = post(client, {**BASE_BODY, "note": "BODY-MARKER"}, **kwargs)
    assert response.status_code == status, label
    lines = [r.getMessage() for r in caplog.records]
    assert any(f'"status":{status}' in line and '"path":"/simulate"' in line for line in lines), lines
    joined = "\n".join(lines)
    for secret in ("SENSITIVE-KEY-VALUE", KEY, "BODY-MARKER", "x-engine-key"):
        assert secret not in joined


def test_oversized_rejection_is_logged_without_the_body(client, caplog):
    with caplog.at_level("INFO", logger="engine"):
        response = client.post("/simulate", content=b'{"x":"' + b"Z" * 9000 + b'"}',
                               headers={"x-engine-key": KEY, "content-type": "application/json"})
    assert response.status_code == 413
    lines = [r.getMessage() for r in caplog.records]
    assert any('"status":413' in line for line in lines), lines
    assert "ZZZZ" not in "\n".join(lines) and KEY not in "\n".join(lines)
    assert response.headers["x-request-id"] and response.headers["cache-control"] == "no-store"
