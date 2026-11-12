"""S-02: every Phase 5 representative episode replayed through the planner from curated export inputs.

6 representatives x 2 datasets x 17 scenarios x 4 policies = 816 episodes per origin; all four origins are
replayed (3,264 episodes). Every summary field must equal the saved, hash-verified Phase 5 per-series output.
"""

import hashlib
import json

import numpy as np
import pyarrow.parquet as pq
from conftest import REPO, planner_inputs

from inventory_service.planner import SUMMARY_FIELDS, run_planner, scenario_from

RESULTS = REPO / "reports/webapp/qa_parity_results.json"


def test_planner_reproduces_every_phase5_representative_episode(curated, phase5_cases):
    plan = json.loads((REPO / "artifacts/inventory/phase5/plan.json").read_text(encoding="utf-8"))
    representatives = {c["dataset"]: set(c["representatives"]) for c in plan["cohorts"]}
    episodes = exact = 0
    worst = 0.0
    per_origin = {}
    for case in phase5_cases:
        item = case["files"]["series"]
        path = REPO / item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        saved = pq.read_table(path).to_pandas()
        saved = saved[saved.series_id.isin(representatives[case["dataset"]])]
        assert len(saved) == 6
        parameters = {k: v for k, v in case["scenario"].items() if k not in ("identifier", "horizon", "fulfilment")}
        scenario = scenario_from(parameters, case["scenario"]["identifier"])
        origin_key = f"{case['dataset']}|{case['fold']['number']}"
        for row in saved.itertuples(index=False):
            inputs = planner_inputs(curated, f"{case['dataset']}|{row.series_id}", origin_key)
            result = run_planner(inputs, scenario, (case["policy"],))["policies"][0]["summary"]
            for field in SUMMARY_FIELDS:
                expected, actual = getattr(row, field), result[field]
                if expected != expected:  # NaN: undefined ratio must stay undefined
                    assert actual is None, (case["case_id"], row.series_id, field)
                    continue
                assert np.isclose(actual, expected, rtol=1e-9, atol=1e-9), (case["case_id"], row.series_id, field)
                worst = max(worst, abs(actual - expected) / max(abs(expected), 1e-12))
            exact += all(
                (result[f] is None and getattr(row, f) != getattr(row, f)) or result[f] == getattr(row, f)
                for f in SUMMARY_FIELDS
            )
            episodes += 1
            per_origin[origin_key] = per_origin.get(origin_key, 0) + 1
    assert episodes == 3264 and all(v == 408 for v in per_origin.values())
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(
            {
                "gate": "S-02",
                "status": "PASS",
                "episodes": episodes,
                "episodes_per_origin_and_dataset": 408,
                "episodes_816_definition": "6 representatives x 2 datasets x 17 scenarios x 4 policies, per origin",
                "summary_fields": len(SUMMARY_FIELDS),
                "bit_exact_episodes": exact,
                "max_relative_difference": worst,
                "tolerance": "rtol 1e-9, atol 1e-9",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
