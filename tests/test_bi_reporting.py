"""Spec-level guards for the Phase 6 Power BI layer (no data, Desktop or network needed)."""

from pathlib import Path

import yaml

from intelligent_demand.bi import qa, report_builder, tmdl

ROOT = Path(__file__).resolve().parents[1]
MODEL = yaml.safe_load((ROOT / "configs/powerbi_model.yaml").read_text(encoding="utf-8"))
LAYOUT = yaml.safe_load((ROOT / "configs/powerbi_report.yaml").read_text(encoding="utf-8"))
RULES = yaml.safe_load((ROOT / "configs/powerbi_qa.yaml").read_text(encoding="utf-8"))
MEASURES = {m["name"] for m in MODEL["measures"]}


def test_measure_names_unique_and_no_reserved_table_name():
    assert len(MEASURES) == len(MODEL["measures"])
    assert "Measures" not in MODEL["tables"]  # reserved by Power BI Desktop
    assert LAYOUT["measures"] == "_Measures"


def test_every_report_measure_binding_exists_in_the_model():
    references = []
    for page in LAYOUT["pages"]:
        for visual in page["visuals"]:
            for values in visual.get("bind", {}).values():
                references += [v for v in values if "." not in v]
    missing = sorted(set(references) - MEASURES)
    assert not missing, missing


def test_model_relationships_match_the_independent_qa_list():
    declared = {(f, c, d) for f, c, d, _ in MODEL["relationships"]}
    assert declared == set(qa.RELATIONSHIPS)


def test_every_qa_rule_maps_to_a_registered_check():
    ids = [rule["id"] for rule in RULES["rules"]]
    assert len(ids) == len(set(ids))
    assert {rule["check"] for rule in RULES["rules"]} <= set(qa.CHECKS)
    assert all(rule["severity"] in RULES["severities"] for rule in RULES["rules"])


def test_inventory_measures_are_guarded_and_never_labelled_savings():
    for measure in MODEL["measures"]:
        assert "saving" not in measure["name"].lower()
        if (
            measure["folder"] in ("Inventory\\Cost", "Inventory\\Service", "Inventory\\Stock")
            and measure["name"] != "Order Frequency"
        ):
            assert "[Inventory Scope Valid]" in measure["expression"], measure["name"]


def test_builder_field_and_literal_helpers():
    assert report_builder.field("DimDataset.Dataset", "_Measures") == "DimDataset[Dataset]"
    assert report_builder.field("Fill Rate", "_Measures") == "_Measures[Fill Rate]"
    assert report_builder.literal(True) == {"expr": {"Literal": {"Value": "true"}}}
    assert report_builder.literal(13) == {"expr": {"Literal": {"Value": "13D"}}}
    assert report_builder.literal("O'Brien") == {"expr": {"Literal": {"Value": "'O''Brien'"}}}
    assert tmdl.quote("Bias %") == "'Bias %'"


def test_lineage_tags_are_deterministic():
    assert tmdl.tag("measure", "MAE") == tmdl.tag("measure", "MAE")
    assert tmdl.tag("measure", "MAE") != tmdl.tag("measure", "RMSE")
