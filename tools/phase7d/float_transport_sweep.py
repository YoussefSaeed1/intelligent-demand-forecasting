"""Phase 7D-2 P-3 lossless float-transport sweep against the LOCAL reference database (no secrets, no network).

  .\\apps\\engine\\.venv\\Scripts\\python.exe tools\\phase7d\\float_transport_sweep.py

For every curated series-origin pair (base scenario, four policies) compares, bit for bit:
  reference : engine SQL in TEXT format on an exact session (extra_float_digits=1, Postgres default)
  defect    : engine SQL in TEXT format on a session forced to extra_float_digits=0 (Supabase's configured value)
  fixed     : the production `load_inputs` (binary results) on the same extra_float_digits=0 session
Requires fixed == reference for every input value and every planner output (no tolerance). Writes
reports/webapp/phase7d/float_transport_sweep.json including the pairs whose integer results the defect changes.
"""

import json
import math
import struct
import sys
import time
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/engine"))
from engine_service.data import load_inputs  # noqa: E402
from engine_service.schemas import SimulateRequest  # noqa: E402
from inventory_service.planner import run_planner, scenario_from  # noqa: E402

URL = "postgresql://postgres:local-owner-only@127.0.0.1:54329/webapp"  # local test server only
LOSSY = URL + "?options=-c%20extra_float_digits%3D0"
OUT = ROOT / "reports/webapp/phase7d/float_transport_sweep.json"
POLICIES = ("selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point")
SCENARIO = scenario_from(
    SimulateRequest.model_validate(
        {
            "seriesKey": "store_item|1:11",
            "originKey": "store_item|1",
            "policies": list(POLICIES),
            "scenario": {
                "leadDays": 7,
                "reviewDays": 1,
                "bufferDays": 3,
                "initialCoverDays": 7,
                "holdingCost": 1,
                "shortageCost": 10,
                "fixedOrderCost": 1,
                "variableOrderCost": 0,
                "terminalCost": 0,
                "variabilityMultiplier": 1,
            },
        }
    ).scenario.engine_parameters()
)


class TextOnly:
    """Proxy that runs the engine's own SQL in text format (drops binary=True) to reproduce the old transport."""

    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=None, **kwargs):
        kwargs.pop("binary", None)
        return self.conn.execute(query, params, **kwargs)


def bits(x):
    return struct.pack("<d", float(x)).hex()


def input_bits(inputs):
    values = [inputs.historical_mean56, *inputs.demand] + [
        v for role in sorted(inputs.forecasts) for v in inputs.forecasts[role]
    ]
    return [bits(v) for v in values]


def diff(a, b, path=""):
    if isinstance(a, dict):
        return [d for k in a for d in diff(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list):
        return [d for n, (x, y) in enumerate(zip(a, b, strict=True)) for d in diff(x, y, f"{path}[{n}]")]
    if isinstance(a, float) and isinstance(b, float):
        same = bits(a) == bits(b) or (math.isnan(a) and math.isnan(b))
        return [] if same else [path]
    return [] if a == b else [path]


def run(conn_like, series, origin):
    inputs = load_inputs(conn_like, series, origin)
    return inputs, {"historicalMean56": inputs.historical_mean56, **run_planner(inputs, SCENARIO, POLICIES)}


def main():
    exact = psycopg.connect(URL, autocommit=True, prepare_threshold=None)
    lossy = psycopg.connect(LOSSY, autocommit=True, prepare_threshold=None)
    settings = {
        "exact": exact.execute("show extra_float_digits").fetchone()[0],
        "lossy": lossy.execute("show extra_float_digits").fetchone()[0],
    }
    assert settings == {"exact": "1", "lossy": "0"}, settings
    pairs = exact.execute("select series_key, origin_key from app.series_origin_mean56 order by 1, 2").fetchall()
    started = time.time()
    defect_inputs = defect_any = 0
    affected, fixed_failures = [], []
    for series, origin in pairs:
        ref_in, ref_out = run(TextOnly(exact), series, origin)
        bad_in, bad_out = run(TextOnly(lossy), series, origin)
        fix_in, fix_out = run(lossy, series, origin)
        defect_inputs += input_bits(bad_in) != input_bits(ref_in)
        paths = diff(ref_out, bad_out)
        defect_any += bool(paths)
        material = [p for p in paths if p != ".historicalMean56"]
        if material:
            affected.append({"seriesKey": series, "originKey": origin, "paths": len(material), "example": material[0]})
        if input_bits(fix_in) != input_bits(ref_in) or diff(ref_out, fix_out):
            fixed_failures.append({"seriesKey": series, "originKey": origin})
    result = {
        "pairs": len(pairs),
        "sessions_extra_float_digits": settings,
        "seconds": round(time.time() - started),
        "defect_text_lossy": {
            "pairs_with_altered_inputs": defect_inputs,
            "pairs_with_any_output_difference": defect_any,
            "pairs_with_material_differences": len(affected),
        },
        "fixed_binary_lossy": {"pairs_with_any_difference": len(fixed_failures), "failures": fixed_failures[:20]},
        "affected_pairs": affected,
        "overall": "PASS" if not fixed_failures and affected else "FAIL",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "affected_pairs"}, indent=1))
    print("first affected pairs:", [(a["seriesKey"], a["originKey"], a["example"]) for a in affected[:6]])


if __name__ == "__main__":
    main()
