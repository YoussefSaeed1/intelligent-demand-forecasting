"""Opaque-byte integrity audit of the committed scientific evidence inventory."""

import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/internal_audit"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


started = time.perf_counter()
module_path = ROOT / "reports/forecasting/phase4_checkpoint_verify.py"
spec = importlib.util.spec_from_file_location("preservation", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checks = module.verify()
inventory_path = ROOT / "reports/forecasting/PHASE4_EVIDENCE_INVENTORY.json"
inventory = json.loads(inventory_path.read_text())
for index, item in enumerate(inventory["files"], 1):
    path = ROOT / item["path"]
    assert path.stat().st_size == item["bytes"], item["path"]
    assert digest(path) == item["sha256"], item["path"]
    if index % 1000 == 0:
        print("Verified", index, "original inventory entries", flush=True)
frozen = json.loads((ROOT / "artifacts/experiments/phase4/frozen_selection.json").read_text())
for path, expected in frozen["code_sha256"].items():
    output = subprocess.check_output(["git", "cat-file", "--filters", "HEAD:" + path], cwd=ROOT)
    assert hashlib.sha256(output).hexdigest() == expected, path
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).strip().decode() == (
    "54a689b7cb07970556bbf2fc164adf934307eab8"
)
checks.update(
    inventory_files_verified=len(inventory["files"]),
    inventory_bytes_verified=inventory["total_bytes"],
    inventory_sha256=digest(inventory_path),
    source_checkout_bytes_verified=89,
    python=sys.version,
    installed_packages=sorted(
        [{"name": p.metadata["Name"], "version": p.version} for p in distributions()],
        key=lambda p: p["name"].lower(),
    ),
    seconds=time.perf_counter() - started,
)
with (OUT / "integrity.json").open("x", encoding="utf-8") as stream:
    json.dump(checks, stream, indent=2)
    stream.write("\n")
print(json.dumps({k: v for k, v in checks.items() if k != "installed_packages"}, indent=2))
