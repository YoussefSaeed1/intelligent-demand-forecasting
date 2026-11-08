"""Synthetic source-edge probes; no original project data is read or modified."""

import argparse
import json
from pathlib import Path

import pandas as pd

from intelligent_demand.config import ProjectConfig
from intelligent_demand.ingestion.datasets import DATASETS
from intelligent_demand.validation.pipeline import profile_dataset

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--run-name", default="synthetic_ingestion_01")
parser.add_argument("--receipt", default="adversarial_ingestion_checks.json")
arguments = parser.parse_args()
root = Path(__file__).parent.resolve() / arguments.run_name
root.mkdir(exist_ok=False)
paths = {name: root / name for name in ("raw", "interim", "processed", "artifacts", "reports")}
raw = paths["raw"] / "store_item"
raw.mkdir(parents=True)
(raw / "train.csv").write_text(
    "date,store,item,sales\n2013-01-01,1,1,1\n2013-1-1,1,1,2\n2013-01-02,1,1,3\n",
    encoding="utf-8",
)
(raw / "test.csv").write_text("id,date,store,item\n0,2013-01-03,1,1\n", encoding="utf-8")
config = ProjectConfig("synthetic source duplicate date probe", 42, 28, paths)
report = profile_dataset(DATASETS["store_item"], config)
canonical = pd.read_parquet(paths["processed"] / "store_item/daily_sales.parquet")
duplicates = int(canonical.duplicated(["dataset_id", "date", "store_id", "item_id"]).sum())
outcome = {
    "status": "demonstrated_guard_defect",
    "fixture": (
        "Equivalent ISO dates with/without padding are distinct strings but same calendar day"
    ),
    "profile_status": report["status"],
    "reported_source_duplicate_business_keys": report["profiles"]["train.csv"][
        "duplicate_keys_after_first"
    ],
    "critical_errors": report["critical_errors"],
    "canonical_published": report["transformation"]["output_published"],
    "actual_published_duplicate_business_keys": duplicates,
    "scientific_impact": (
        "No demonstrated impact on preserved real data; independent source-to-Parquet/key audits "
        "and unchanged fingerprints protect the existing results. A malformed replacement source "
        "can nevertheless be mislabelled passed by profile-data alone."
    ),
}
assert outcome["canonical_published"] and duplicates == 1
assert not report["critical_errors"]
destination = Path(__file__).parent / arguments.receipt
with destination.open("x", encoding="utf-8") as out:
    json.dump(outcome, out, indent=2)
    out.write("\n")
print(json.dumps(outcome, indent=2))
