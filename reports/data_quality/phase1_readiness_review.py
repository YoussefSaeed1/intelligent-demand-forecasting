"""Bind both independent data audits to current local files; no M5 transformation or EDA."""

import json
from datetime import UTC, datetime
from pathlib import Path

from intelligent_demand.config import load_config
from intelligent_demand.ingestion.datasets import sha256, write_json

root = Path(__file__).resolve().parents[2]
config = load_config(root / "configs/default.yaml")
directory = config.paths["reports"] / "data_quality"
store = json.loads((directory / "store_item_canonical_audit.json").read_text(encoding="utf-8"))
m5 = json.loads((directory / "m5_canonical_audit.json").read_text(encoding="utf-8"))
m5_profile = json.loads((directory / "m5.json").read_text(encoding="utf-8"))
assert store["status"] == m5["status"] == "passed"
assert m5["duplicate_business_keys"] == 0 and m5["business_key_coverage_complete"]
checks = {}
for name, audit in (("store_item", store), ("m5", m5)):
    raw_hashes = {
        filename: sha256(config.paths["raw"] / name / filename)
        for filename in audit["source_sha256"]
    }
    canonical_hash = sha256(config.paths["processed"] / name / "daily_sales.parquet")
    assert raw_hashes == audit["source_sha256"], f"{name}: source changed after audit"
    assert canonical_hash == audit["canonical_sha256"], f"{name}: Parquet changed after audit"
    checks[name] = {
        "independent_gate": "passed",
        "current_hash_binding": True,
        "audit_sha256": sha256(directory / f"{name}_canonical_audit.json"),
        "canonical_sha256": canonical_hash,
        "source_sha256": raw_hashes,
    }
comparison = {
    "store_item": {
        "date_min": store["train"]["date_min"],
        "date_max": store["train"]["date_max"],
        "days": store["train"]["days"],
        "observations": store["canonical_rows"],
        "series": store["canonical_series"],
        "stores": store["train"]["stores"],
        "products": store["train"]["products"],
        "sales_units_sum": store["source_sales_units_sum"],
        "zero_sales_observations": store["source_zero_sales_observations"],
        "zero_sales_percent": 100 * store["source_zero_sales_observations"] / store["source_rows"],
        "missing_historical_keys": store["canonical_missing_keys"],
        "missing_sales": 0,
        "unlabelled_test_rows": store["unlabelled_test_rows"],
        "unlabelled_test_rows_counted_as_observed": 0,
        "price_availability": "not supplied; all canonical unit_price values null",
    },
    "m5": {
        "date_min": m5["date_min"],
        "date_max": m5["date_max"],
        "days": m5["days"],
        "observations": m5["canonical_rows"],
        "series": m5["series"],
        "stores": m5["stores"],
        "products": m5["products"],
        "sales_units_sum": m5["source_sales_units_sum"],
        "zero_sales_observations": m5["zero_sales_observations"],
        "zero_sales_percent": 100 * m5["zero_sales_observations"] / m5["canonical_rows"],
        "missing_historical_keys": 0,
        "missing_sales": 0,
        "missing_historical_price_observations": m5["missing_price_observations"],
        "missing_historical_price_percent": 100
        * m5["missing_price_observations"]
        / m5["canonical_rows"],
        "warnings_preserved": m5_profile["warnings"],
    },
}
result = {
    "phase1_status": "closed_with_documented_limitations",
    "phase2_status": "not_started",
    "checked_at_utc": datetime.now(UTC).isoformat(),
    "quality_gates": checks,
    "both_independent_quality_gates_passed": True,
    "comparison": comparison,
    "granularity": "observed daily sales per source-specific store/product series",
    "readiness": {
        "independent_benchmarking": True,
        "common_28_day_horizon_feasible": True,
        "common_metrics_feasible": ["MAE", "RMSE", "WAPE", "signed forecast bias"],
        "cross_dataset_methodological_comparison": True,
        "direct_model_transfer_justified": False,
        "empirical_seasonality_established": False,
    },
    "m5_transformation_rerun": False,
}
write_json(directory / "phase1_readiness.json", result)
print(json.dumps(result, indent=2))
