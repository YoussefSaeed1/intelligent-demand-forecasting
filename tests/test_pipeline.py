"""Deterministic miniature parser fixtures only; never reported as real-data results."""

import pandas as pd
import pytest

from intelligent_demand.config import ProjectConfig
from intelligent_demand.ingestion.datasets import DATASETS
from intelligent_demand.validation.pipeline import profile_dataset


@pytest.fixture
def config(tmp_path):
    return ProjectConfig(
        "test",
        42,
        28,
        {name: tmp_path / name for name in ("raw", "interim", "processed", "artifacts", "reports")},
    )


def test_missing_inputs_produce_blocked_report_without_output(config):
    report = profile_dataset(DATASETS["m5"], config)
    assert report["status"] == "blocked"
    assert not (config.paths["processed"] / "m5/daily_sales.parquet").exists()
    assert (config.paths["reports"] / "data_quality/m5.json").exists()


def _store(config, sales="3", duplicate=False):
    directory = config.paths["raw"] / "store_item"
    directory.mkdir(parents=True)
    row = f"2020-01-01,1,2,{sales}\n"
    (directory / "train.csv").write_text("date,store,item,sales\n" + row * (2 if duplicate else 1))
    (directory / "test.csv").write_text("id,date,store,item\n0,2020-01-02,1,2\n")


def test_store_canonical_reconciles_source_and_keeps_zero(config):
    _store(config, sales="0")
    report = profile_dataset(DATASETS["store_item"], config)
    assert report["status"] == "passed_with_warnings"
    result = pd.read_parquet(config.paths["processed"] / "store_item/daily_sales.parquet")
    assert len(result) == 1
    assert result.sales_units.tolist() == [0]
    assert report["quantities"]["train.sales"]["zero_share"] == 1
    assert report["transformation"]["row_and_quantity_reconciliation"]


@pytest.mark.parametrize(
    "sales,duplicate", [("-1", False), ("bad", False), ("inf", False), ("1", True)]
)
def test_invalid_store_data_never_published(config, sales, duplicate):
    _store(config, sales, duplicate)
    report = profile_dataset(DATASETS["store_item"], config)
    assert report["status"] == "invalid"
    assert not (config.paths["processed"] / "store_item/daily_sales.parquet").exists()


def _m5(config, conflicting=False, duplicate_price=False, duplicate_calendar=False):
    directory = config.paths["raw"] / "m5"
    directory.mkdir(parents=True)
    calendar = "d,date,wm_yr_wk\nd_1,2020-01-01,1\nd_2,2020-01-02,1\n"
    if duplicate_calendar:
        calendar += "d_1,2020-01-01,1\n"
    (directory / "calendar.csv").write_text(calendar)
    prices = "store_id,item_id,wm_yr_wk,sell_price\nS,A,1,2.5\n"
    if duplicate_price:
        prices += "S,A,1,2.5\n"
    (directory / "sell_prices.csv").write_text(prices)
    header = "id,item_id,dept_id,cat_id,store_id,state_id,d_1,d_2\n"
    (directory / "sales_train_evaluation.csv").write_text(header + "A_S_evaluation,A,D,C,S,X,0,3\n")
    value = "9" if conflicting else "3"
    (directory / "sales_train_validation.csv").write_text(
        header + f"A_S_validation,A,D,C,S,X,0,{value}\n"
    )
    return directory


def test_m5_overlap_not_duplicated_and_price_join_reconciles(config):
    _m5(config)
    report = profile_dataset(DATASETS["m5"], config)
    assert report["status"] == "passed_with_warnings", report
    result = pd.read_parquet(config.paths["processed"] / "m5/daily_sales.parquet")
    assert len(result) == 2
    assert result.sales_units.sum() == 3
    assert report["transformation"]["source_sales_units_sum"] == 3
    assert result.unit_price.tolist() == [2.5, 2.5]
    assert report["transformation"]["overlap_series_matched"] == 1
    assert not report["transformation"]["overlapping_history_concatenated"]


@pytest.mark.parametrize(
    "kwargs", [{"conflicting": True}, {"duplicate_price": True}, {"duplicate_calendar": True}]
)
def test_m5_rejects_conflicts_and_many_to_many_joins(config, kwargs):
    _m5(config, **kwargs)
    report = profile_dataset(DATASETS["m5"], config)
    assert report["status"] == "invalid"
    assert not (config.paths["processed"] / "m5/daily_sales.parquet").exists()


def test_m5_uses_available_history_only(config):
    directory = _m5(config)
    (directory / "sales_train_evaluation.csv").unlink()
    report = profile_dataset(DATASETS["m5"], config)
    assert report["status"] == "passed_with_warnings"
    assert report["transformation"]["selected_history"] == "sales_train_validation.csv"


def test_indexed_prices_preserve_multiple_series_and_row_order(config):
    directory = _m5(config)
    for filename, suffix in [
        ("sales_train_evaluation.csv", "evaluation"),
        ("sales_train_validation.csv", "validation"),
    ]:
        with (directory / filename).open("a") as stream:
            stream.write(f"B_S_{suffix},B,D,C,S,X,2,1\n")
    with (directory / "sell_prices.csv").open("a") as stream:
        stream.write("S,B,1,7\n")
    report = profile_dataset(DATASETS["m5"], config)
    assert report["status"] == "passed_with_warnings"
    result = pd.read_parquet(config.paths["processed"] / "m5/daily_sales.parquet")
    assert len(result) == 4
    assert result.sales_units.sum() == 6
    assert result.loc[result.item_id.eq("A"), "unit_price"].tolist() == [2.5, 2.5]
    assert result.loc[result.item_id.eq("B"), "unit_price"].tolist() == [7, 7]


def test_indexed_prices_retain_missing_values_without_losing_sales(config):
    directory = _m5(config)
    (directory / "sell_prices.csv").write_text("store_id,item_id,wm_yr_wk,sell_price\nS,B,1,7\n")
    report = profile_dataset(DATASETS["m5"], config)
    assert report["status"] == "passed_with_warnings"
    result = pd.read_parquet(config.paths["processed"] / "m5/daily_sales.parquet")
    assert len(result) == 2
    assert result.sales_units.sum() == 3
    assert result.unit_price.isna().all()
    assert report["transformation"]["missing_price_observations"] == 2


def test_current_discovery_is_reported_while_transformation_runs(config, monkeypatch):
    import json

    from intelligent_demand.validation import pipeline

    _m5(config)
    original = pipeline.transform_m5

    def inspect_running_report(raw, writer, report):
        path = config.paths["reports"] / "data_quality/m5.json"
        current = json.loads(path.read_text(encoding="utf-8"))
        assert current["status"] == "running"
        assert current["inventory"]["ready_for_profiling"]
        assert current["started_at_utc"]
        assert "finished_at_utc" not in current
        original(raw, writer, report)

    monkeypatch.setattr(pipeline, "transform_m5", inspect_running_report)
    report = profile_dataset(DATASETS["m5"], config)
    assert report["status"] == "passed_with_warnings"
    assert report["finished_at_utc"] >= report["started_at_utc"]


def test_unexpected_transform_failure_replaces_stale_missing_report(config, monkeypatch):
    import json

    from intelligent_demand.validation import pipeline

    _m5(config)
    directory = config.paths["reports"] / "data_quality"
    directory.mkdir(parents=True)
    (directory / "m5.json").write_text('{"status":"blocked"}', encoding="utf-8")

    def fail(raw, writer, report):
        raise TypeError("local parser regression")

    monkeypatch.setattr(pipeline, "transform_m5", fail)
    report = profile_dataset(DATASETS["m5"], config)
    saved = json.loads((directory / "m5.json").read_text(encoding="utf-8"))
    assert report["status"] == saved["status"] == "invalid"
    assert saved["failure_type"] == "TypeError"
    assert saved["inventory"]["ready_for_profiling"]
    assert saved["finished_at_utc"]
    assert not saved["transformation"]["output_published"]


def test_cli_checkpoints_completed_dataset_before_next_source_is_interrupted(config, monkeypatch):
    import json
    import sys

    from intelligent_demand import __main__ as cli
    from intelligent_demand.validation import pipeline

    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(sys, "argv", ["intelligent_demand", "profile-data", "--dataset", "all"])

    def profile(spec, settings):
        if spec.name == "store_item":
            return {"status": "passed"}
        raise KeyboardInterrupt

    monkeypatch.setattr(pipeline, "profile_dataset", profile)
    with pytest.raises(KeyboardInterrupt):
        cli.main()
    report = json.loads((config.paths["reports"] / "data_quality/profile-data.json").read_text())
    assert report["store_item"]["status"] == "passed"
    assert report["m5"]["status"] == "pending"
