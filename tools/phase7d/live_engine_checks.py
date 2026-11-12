"""Phase 7D-2 P-3 production checks for the deployed engine (owner-run; secrets via hidden prompts, never printed/stored).

  .\\apps\\engine\\.venv\\Scripts\\python.exe tools\\phase7d\\live_engine_checks.py

Checks: E-01 health and engine identity; E-02 Vercel protection (deployment URL; production domain if All Deployments);
E-03 key enforcement; E-04 invalid input handling; E-05 bounded simulation against live Supabase; E-06 parity (bit-exact
vs the verified local engine on the same commit, and exact saved Phase 5 totals); E-07 latency. Results (no secrets) go to
reports/webapp/phase7d/live_engine_checks.json.
"""

import getpass
import json
import statistics
import struct
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

PROD = "https://idf-engine.vercel.app"
DEPLOYMENT = "https://idf-engine-bpm9f8n8o-youssefsaeed206-3245s-projects.vercel.app"  # active deployment (e170d98)
LOCAL = "http://127.0.0.1:8787"
LOCAL_KEY = "local-test-engine-key-0123456789abcdef0123"  # local test server only
ENGINE_VERSION = "cedc5a31533772fc"
OUT = Path(__file__).resolve().parents[2] / "reports/webapp/phase7d/live_engine_checks.json"
SCENARIO = {
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
}
POLICIES = ["selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point"]
BASE = {
    "seriesKey": "store_item|1:11",
    "originKey": "store_item|1",
    "policies": POLICIES,
    "scenario": SCENARIO,
}
# Saved Phase 5 base results (app.inventory_series_base) for store_item|1:11, origin 1, read at full precision from the
# local reference DB (extra_float_digits=1, binary); Supabase-connector reads round to 15 digits and must not be used.
SAVED = {
    "selected_ml": {
        "totalCost": 2555,
        "holdingCost": 2505,
        "shortageCost": 30,
        "orderingCost": 20,
        "terminalCost": 0,
        "demandUnits": 710,
        "fulfilledUnits": 707,
        "unmetUnits": 3,
        "stockoutDays": 1,
        "orders": 20,
        "finalOnHand": 88,
        "finalPipeline": 0,
        "initialOnHand": 196,
        "averageOnHand": 89.46428571428571,
    },
    "moving_average_28": {
        "totalCost": 2772,
        "holdingCost": 2722,
        "shortageCost": 30,
        "orderingCost": 20,
        "terminalCost": 0,
        "demandUnits": 710,
        "fulfilledUnits": 707,
        "unmetUnits": 3,
        "stockoutDays": 1,
        "orders": 20,
        "finalOnHand": 102,
        "finalPipeline": 0,
        "initialOnHand": 196,
        "averageOnHand": 97.21428571428571,
    },
    "seasonal_naive": {
        "totalCost": 2900,
        "holdingCost": 2850,
        "shortageCost": 30,
        "orderingCost": 20,
        "terminalCost": 0,
        "demandUnits": 710,
        "fulfilledUnits": 707,
        "unmetUnits": 3,
        "stockoutDays": 1,
        "orders": 20,
        "finalOnHand": 112,
        "finalPipeline": 0,
        "initialOnHand": 196,
        "averageOnHand": 101.78571428571429,
    },
    "fixed_reorder_point": {
        "totalCost": 1309,
        "holdingCost": 1259,
        "shortageCost": 30,
        "orderingCost": 20,
        "terminalCost": 0,
        "demandUnits": 710,
        "fulfilledUnits": 707,
        "unmetUnits": 3,
        "stockoutDays": 1,
        "orders": 20,
        "finalOnHand": 49,
        "finalPipeline": 0,
        "initialOnHand": 196,
        "averageOnHand": 44.964285714285715,
    },
}


def call(base, path, *, body=None, key=None, bypass=None, raw=None):
    headers = {"content-type": "application/json"}
    if key is not None:
        headers["x-engine-key"] = key
    if bypass:
        headers["x-vercel-protection-bypass"] = bypass
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    request = urllib.request.Request(base + path, data=data, headers=headers, method="POST" if data else "GET")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status, text = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        status, text = error.code, error.read().decode(errors="replace")
    elapsed = round((time.perf_counter() - start) * 1000, 1)
    try:
        payload = json.loads(text)
    except ValueError:
        payload = None
    return status, payload, elapsed


COMPARABLE = ("policies", "historicalMean56", "dates", "demand", "engineVersion", "seriesKey", "originKey")
# Pairs whose integer planner results changed under 15-digit text transport (tools/phase7d/float_transport_sweep.py).
AFFECTED_PAIRS = [
    ("store_item|1:11", "store_item|2"),
    ("store_item|1:113", "store_item|2"),
    ("m5|4:CA_1FOODS_3_764", "m5|3"),
    ("m5|4:CA_1HOBBIES_1_371", "m5|2"),
]  # reports/webapp/phase7d/float_transport_sweep.json (182 affected of 3,200)


def exact_equal(a, b):
    """Bit-exact for floats (struct-packed IEEE-754), plain equality otherwise; ints and integral floats compare by value."""
    if isinstance(a, float) or isinstance(b, float):
        try:
            return struct.pack("<d", float(a)) == struct.pack("<d", float(b))
        except (TypeError, ValueError):
            return False
    return a == b


def json_diff(a, b, path=""):
    """Every JSON path where a and b differ (floats compared bit-exactly; no tolerance)."""
    if isinstance(a, dict) and isinstance(b, dict):
        keys = sorted(set(a) | set(b))
        return [d for k in keys for d in json_diff(a.get(k), b.get(k), f"{path}.{k}")]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path} (length {len(a)} vs {len(b)})"]
        return [d for n, (x, y) in enumerate(zip(a, b, strict=True)) for d in json_diff(x, y, f"{path}[{n}]")]
    if a is None or b is None or isinstance(a, (str, bool)) or isinstance(b, (str, bool)):
        return [] if a == b else [path]
    return [] if exact_equal(a, b) else [f"{path} (local={a!r} prod={b!r})"]


def summary_key(policy):
    # Engine returns snake_case summary fields; compare against the saved camelCase reference.
    return {"".join(w if i == 0 else w.title() for i, w in enumerate(k.split("_"))): v for k, v in policy["summary"].items()}


def main():
    key = getpass.getpass("idf-engine ENGINE_SHARED_KEY (hidden): ").strip()
    bypass = getpass.getpass("Protection Bypass for Automation secret (hidden; Enter to skip): ").strip() or None
    if len(key) < 32:
        raise SystemExit("The engine key must be at least 32 characters")
    results, gates = (
        {
            "checked_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "base": PROD,
            "bypass_supplied": bypass is not None,
        },
        {},
    )

    # E-07 (part): the first simulate call is the cold-start candidate; measure it before anything warms the function.
    s, first, cold_ms = call(PROD, "/simulate", body=BASE, key=key, bypass=bypass)
    results["first_simulate_ms"], results["first_simulate_status"] = cold_ms, s

    s, health, health_ms = call(PROD, "/health", bypass=bypass)
    gates["E-01 health"] = {
        "pass": s == 200
        and health
        and health.get("engineVersion") == ENGINE_VERSION
        and health.get("keyConfigured") is True,
        "status": s,
        "health": health,
        "ms": health_ms,
    }

    s_no, _, _ = call(DEPLOYMENT, "/health")
    e02 = {"deployment_url_without_bypass": s_no}
    if bypass:
        e02["deployment_url_with_bypass"] = call(DEPLOYMENT, "/health", bypass=bypass)[0]
        e02["production_domain_without_bypass"] = call(PROD, "/health")[0]
    e02["pass"] = s_no in (401, 403) and (not bypass or e02["deployment_url_with_bypass"] == 200)
    gates["E-02 protection"] = e02

    wrong = call(PROD, "/simulate", body=BASE, key="x" * 48, bypass=bypass)[0]
    missing = call(PROD, "/simulate", body=BASE, bypass=bypass)[0]
    gates["E-03 key"] = {
        "pass": wrong == 401 and missing == 401,
        "wrong_key": wrong,
        "missing_key": missing,
    }

    cases = {
        "lead_days_out_of_bounds": ({**BASE, "scenario": {**SCENARIO, "leadDays": 99}}, 400),
        "client_supplied_demand": ({**BASE, "demand": [1] * 28}, 400),
        "unknown_series": ({**BASE, "seriesKey": "store_item|9:999"}, 404),
        "dataset_mismatch": ({**BASE, "originKey": "m5|1"}, 400),
    }
    e04 = {name: call(PROD, "/simulate", body=body, key=key, bypass=bypass)[0] for name, (body, _) in cases.items()}
    e04["oversized_body"] = call(PROD, "/simulate", raw=b'{"x":"' + b"a" * 9000 + b'"}', key=key, bypass=bypass)[0]
    expected = {**{n: c for n, (_, c) in cases.items()}, "oversized_body": 413}
    gates["E-04 invalid input"] = {"pass": e04 == expected, "observed": e04, "expected": expected}

    gates["E-05 simulation"] = {
        "pass": results["first_simulate_status"] == 200 and first is not None and len(first.get("policies", [])) == 4,
        "status": results["first_simulate_status"],
        "engineVersion": (first or {}).get("engineVersion"),
    }

    # E-06: strict bit-exact parity (no tolerance) vs the verified local engine on the same commit, for the base case and
    # the pairs whose integer results changed under the old 15-digit text transport; exact saved Phase 5 values.
    e06 = {"pairs": {}, "saved_phase5_mismatches": {}}
    for series_key, origin_key in [(BASE["seriesKey"], BASE["originKey"]), *AFFECTED_PAIRS]:
        body = {**BASE, "seriesKey": series_key, "originKey": origin_key}
        prod = first if (series_key, origin_key) == (BASE["seriesKey"], BASE["originKey"]) else None
        if prod is None:
            status_prod, prod, _ = call(PROD, "/simulate", body=body, key=key, bypass=bypass)
        else:
            status_prod = results["first_simulate_status"]
        status_local, local, _ = call(LOCAL, "/simulate", body=body, key=LOCAL_KEY)
        paths = (
            json_diff({k: local.get(k) for k in COMPARABLE}, {k: prod.get(k) for k in COMPARABLE})
            if prod and local
            else ["(no response)"]
        )
        e06["pairs"][f"{series_key} @ {origin_key}"] = {
            "prod_status": status_prod,
            "local_status": status_local,
            "bit_exact": status_prod == status_local == 200 and not paths,
            "differing_paths": paths[:20],
            "differing_path_count": len(paths),
        }
    for policy in (first or {}).get("policies", []):
        got = summary_key(policy)
        for field, value in SAVED[policy["policy"]].items():
            if not exact_equal(got.get(field), value):
                e06["saved_phase5_mismatches"][f"{policy['policy']}.{field}"] = [got.get(field), value]
    e06["bit_exact_vs_local_engine"] = all(p["bit_exact"] for p in e06["pairs"].values())
    e06["totals"] = {p["policy"]: summary_key(p)["totalCost"] for p in (first or {}).get("policies", [])}
    e06["pass"] = e06["bit_exact_vs_local_engine"] and not e06["saved_phase5_mismatches"] and len(e06["pairs"]) >= 4
    gates["E-06 parity"] = e06

    warm = [call(PROD, "/simulate", body=BASE, key=key, bypass=bypass)[2] for _ in range(5)]
    gates["E-07 latency"] = {
        "pass": max(warm) < 20000,
        "first_simulate_ms": cold_ms,
        "warm_simulate_ms": warm,
        "warm_median_ms": statistics.median(warm),
        "health_ms": health_ms,
    }

    results["gates"] = gates
    results["overall"] = "PASS" if all(g["pass"] for g in gates.values()) else "FAIL"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    for name, gate in gates.items():
        print(
            f"{name:20s} {'PASS' if gate['pass'] else 'FAIL'}  "
            + json.dumps({k: v for k, v in gate.items() if k != "pass"})[:200]
        )
    print(f"OVERALL {results['overall']} -> {OUT}")


if __name__ == "__main__":
    main()
