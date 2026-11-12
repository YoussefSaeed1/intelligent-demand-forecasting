"""Lossless float transport for engine inputs (Phase 7D-2 P-3).

Supabase's server configuration sets extra_float_digits=0, so TEXT results round double precision to 15 significant
digits. The engine must read its inputs in binary format. These tests reproduce the defect on the local reference
database by forcing extra_float_digits=0 on the session, and require bit-exact equality (no tolerance).
"""

import math
import struct

import psycopg
import pytest
from inventory_service.planner import run_planner, scenario_from

from engine_service.data import load_inputs
from engine_service.schemas import SimulateRequest

URL = "postgresql://postgres:local-owner-only@127.0.0.1:54329/webapp"  # local test server only
LOSSY = URL + "?options=-c%20extra_float_digits%3D0"
POLICIES = ("selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point")
# Pairs whose INTEGER planner results change under 15-digit text transport (from tools/phase7d/float_transport_sweep.py).
AFFECTED = [
    ("store_item|1:11", "store_item|2"),
    ("store_item|1:113", "store_item|2"),
    ("m5|4:CA_1FOODS_3_764", "m5|3"),
    ("m5|4:CA_1HOBBIES_1_371", "m5|2"),
]  # reports/webapp/phase7d/float_transport_sweep.json (182 affected of 3,200)


def _available():
    try:
        psycopg.connect(URL, connect_timeout=2).close()
        return True
    except psycopg.Error:
        return False


pytestmark = pytest.mark.skipif(not _available(), reason="local test database not running")


class TextOnly:
    """The engine's own SQL in text format (the pre-fix transport)."""

    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=None, **kwargs):
        kwargs.pop("binary", None)
        return self.conn.execute(query, params, **kwargs)


@pytest.fixture(scope="module")
def sessions():
    exact = psycopg.connect(URL, autocommit=True, prepare_threshold=None)
    lossy = psycopg.connect(LOSSY, autocommit=True, prepare_threshold=None)
    assert exact.execute("show extra_float_digits").fetchone()[0] == "1"
    assert lossy.execute("show extra_float_digits").fetchone()[0] == "0"
    yield exact, lossy
    exact.close()
    lossy.close()


def bits(x):
    return struct.pack("<d", float(x)).hex()


def scenario():
    body = SimulateRequest.model_validate(
        {"seriesKey": "store_item|1:11", "originKey": "store_item|1", "policies": list(POLICIES),
         "scenario": {"leadDays": 7, "reviewDays": 1, "bufferDays": 3, "initialCoverDays": 7, "holdingCost": 1,
                      "shortageCost": 10, "fixedOrderCost": 1, "variableOrderCost": 0, "terminalCost": 0,
                      "variabilityMultiplier": 1}}
    )
    return scenario_from(body.scenario.engine_parameters())


def same(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, float) and isinstance(b, float):
        return bits(a) == bits(b) or (math.isnan(a) and math.isnan(b))
    return a == b


def test_text_transport_under_extra_float_digits_0_reproduces_the_defect(sessions):
    exact, lossy = sessions
    good = load_inputs(TextOnly(exact), "store_item|1:11", "store_item|1")
    bad = load_inputs(TextOnly(lossy), "store_item|1:11", "store_item|1")
    assert repr(good.historical_mean56) == "27.928571428571427"
    assert repr(bad.historical_mean56) == "27.9285714285714"  # 15 significant digits
    assert bits(good.historical_mean56) != bits(bad.historical_mean56)


@pytest.mark.parametrize(
    ("label", "sql"),
    [
        ("historical_mean56", "select historical_mean56 from app.series_origin_mean56 order by series_key, origin_key"),
        ("forecasts", "select forecast from app.forecasts order by series_key, origin_key, model_key, horizon_day"),
        ("validation_actuals", "select units from app.validation_actuals order by series_key, origin_key, date"),
    ],
)
def test_binary_reads_preserve_every_stored_input_bit(sessions, label, sql):
    exact, lossy = sessions
    reference = [bits(r[0]) for r in exact.execute(sql).fetchall()]  # exact shortest round-trip text
    binary = [bits(r[0]) for r in lossy.execute(sql, binary=True).fetchall()]  # Supabase-like session, binary
    text = [bits(r[0]) for r in lossy.execute(sql).fetchall()]  # Supabase-like session, text (old transport)
    assert len(reference) == len(binary) > 0
    assert binary == reference, label
    if label != "validation_actuals":  # integer-valued sales survive 15 digits; real-valued inputs do not
        assert text != reference, f"{label}: expected the 15-digit text transport to alter some values"


def test_production_loader_is_lossless_on_a_lossy_session(sessions):
    exact, lossy = sessions
    reference = load_inputs(TextOnly(exact), "store_item|1:11", "store_item|1")
    fixed = load_inputs(lossy, "store_item|1:11", "store_item|1")
    assert bits(fixed.historical_mean56) == bits(reference.historical_mean56)
    assert [bits(v) for v in fixed.demand] == [bits(v) for v in reference.demand]
    for role in reference.forecasts:
        assert [bits(v) for v in fixed.forecasts[role]] == [bits(v) for v in reference.forecasts[role]]


@pytest.mark.parametrize(("series_key", "origin_key"), AFFECTED)
def test_known_affected_pairs_give_bit_exact_planner_output(sessions, series_key, origin_key):
    exact, lossy = sessions
    plan = scenario()
    reference = run_planner(load_inputs(TextOnly(exact), series_key, origin_key), plan, POLICIES)
    defect = run_planner(load_inputs(TextOnly(lossy), series_key, origin_key), plan, POLICIES)
    fixed = run_planner(load_inputs(lossy, series_key, origin_key), plan, POLICIES)
    assert not same(reference, defect), "pair is expected to be affected by 15-digit text transport"
    assert same(reference, fixed)


def test_affected_pair_list_is_populated():
    assert len(AFFECTED) >= 3
