"""Vendor the frozen Phase 5 engine into this package with byte-level identity verification.

Copies src/intelligent_demand/inventory/{__init__,engine,design}.py unchanged, checks every copy against
the original file AND the frozen Phase 5 execution contract (artifacts/inventory/phase5/execution.json
when present, otherwise the hashes recorded in VENDOR_MANIFEST.json), and refuses on any mismatch.
Usage (from the repository root):  python packages/inventory_core/vendor_engine.py [--check]
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FILES = ("__init__.py", "engine.py", "design.py")
SOURCE = REPO / "src/intelligent_demand/inventory"
TARGET = HERE / "src/intelligent_demand/inventory"
MANIFEST = HERE / "VENDOR_MANIFEST.json"
CONTRACT = REPO / "artifacts/inventory/phase5/execution.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_hashes():
    if CONTRACT.exists():
        code = json.loads(CONTRACT.read_text(encoding="utf-8"))["code"]
        return {Path(c["path"]).name: c["sha256"] for c in code if Path(c["path"]).name in FILES}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]


def verify():
    frozen = frozen_hashes()
    problems = []
    for name in FILES:
        copy = TARGET / name
        if not copy.is_file():
            problems.append(f"missing {name}")
            continue
        if sha256(copy) != frozen[name]:
            problems.append(f"{name} differs from the frozen execution contract")
        original = SOURCE / name
        if original.is_file() and original.read_bytes() != copy.read_bytes():
            problems.append(f"{name} differs byte-for-byte from the repository original")
    return problems


def vendor():
    frozen = frozen_hashes()
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        if sha256(SOURCE / name) != frozen[name]:
            raise SystemExit(f"Refusing: original {name} no longer matches the frozen execution contract")
        shutil.copyfile(SOURCE / name, TARGET / name)
    problems = verify()
    if problems:
        raise SystemExit(f"Refusing: {problems}")
    MANIFEST.write_text(
        json.dumps(
            {
                "source": "src/intelligent_demand/inventory",
                "contract": "artifacts/inventory/phase5/execution.json",
                "execution_sha256": json.loads(CONTRACT.read_text(encoding="utf-8"))["sha256"],
                "files": frozen,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"vendored {len(FILES)} files; byte-identical to originals and the frozen contract")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify only")
    if parser.parse_args().check:
        issues = verify()
        print("identical" if not issues else issues)
        sys.exit(1 if issues else 0)
    vendor()
