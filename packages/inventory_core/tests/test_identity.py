"""S-01: the vendored engine is byte-identical to the frozen Phase 5 execution contract and is what Python imports."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def load_vendor_tool():
    spec = importlib.util.spec_from_file_location("vendor_engine", HERE / "vendor_engine.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vendored_files_match_contract_and_originals():
    assert load_vendor_tool().verify() == []


def test_imported_engine_is_the_vendored_copy():
    from intelligent_demand.inventory import design, engine

    vendored = (HERE / "src/intelligent_demand/inventory").resolve()
    assert Path(engine.__file__).resolve().parent == vendored
    assert Path(design.__file__).resolve().parent == vendored
