"""Small offline audit fixtures, explicitly separate from real-dataset evidence."""

import json

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from intelligent_demand.config import ProjectConfig
from intelligent_demand.ingestion.datasets import DATASETS, file_inventory
from intelligent_demand.validation.pipeline import profile_dataset
from intelligent_demand.validation.store_item_audit import audit_store_item


def _manifest(config):
    directory = config.paths["raw"] / "store_item"
    (directory / "acquisition.json").write_text(
        json.dumps(file_inventory(directory, DATASETS["store_item"])),
        encoding="utf-8",
    )


@pytest.fixture
def config(tmp_path):
    settings = ProjectConfig(
        "test",
        42,
        28,
        {name: tmp_path / name for name in ("raw", "interim", "processed", "artifacts", "reports")},
    )
    directory = settings.paths["raw"] / "store_item"
    directory.mkdir(parents=True)
    training = ["date,store,item,sales"]
    testing = ["id,date,store,item"]
    value = 0
    for store in (1, 2):
        for item in (3, 4):
            for day in range(1, 4):
                training.append(f"2020-01-0{day},{store},{item},{value}")
                value += 1
            for day in range(4, 6):
                testing.append(f"{len(testing) - 1},2020-01-0{day},{store},{item}")
    (directory / "train.csv").write_text("\n".join(training) + "\n")
    (directory / "test.csv").write_text("\n".join(testing) + "\n")
    _manifest(settings)
    result = profile_dataset(DATASETS["store_item"], settings)
    assert result["status"] == "passed_with_warnings"
    return settings


def _change_parquet(config, change):
    path = config.paths["processed"] / "store_item/daily_sales.parquet"
    table = pq.read_table(path)
    frame = table.to_pandas(date_as_object=False)
    change(frame)
    pq.write_table(pa.Table.from_pandas(frame, schema=table.schema, preserve_index=False), path)


def test_complete_audit_preserves_zero_and_excludes_unlabelled_test(config):
    profile_path = config.paths["reports"] / "data_quality/store_item.json"
    historical = json.loads(profile_path.read_text())
    historical.pop("started_at_utc")
    historical.pop("finished_at_utc")
    profile_path.write_text(json.dumps(historical))
    report = audit_store_item(config)
    assert report["status"] == "passed", report
    assert report["source_rows"] == report["canonical_rows"] == 12
    assert report["source_sales_units_sum"] == report["canonical_sales_units_sum"] == 66
    assert report["row_level_sales_mismatches"] == report["duplicate_business_keys"] == 0
    assert report["train"]["missing_dates_global_window"] == report["canonical_missing_keys"] == 0
    assert len(report["train"]["missing_dates_per_series"]) == 4
    assert (
        report["source_zero_sales_observations"] == report["canonical_zero_sales_observations"] == 1
    )
    assert report["zero_sales_records"][0]["source_and_canonical_match"]
    assert report["unlabelled_test_rows"] == 8
    assert report["test_sales_total"] is None
    assert report["unlabelled_test_rows_in_canonical"] == 0
    assert report["raw_hashes_match_acquisition"] and report["raw_hashes_unchanged"]
    profile = json.loads((config.paths["reports"] / "data_quality/store_item.json").read_text())
    assert profile["independent_audit"]["status"] == "passed"
    assert profile["independent_audit"]["missing_dates_global_window"] == 0
    assert any("zero missing historical dates" in note for note in profile["notes"])
    readable = (config.paths["reports"] / "data_quality/store_item.md").read_text(encoding="utf-8")
    assert "Finished (UTC): not recorded (historical run)" in readable
    assert profile["profiles"]["test.csv"]["series"] == 4


def test_row_level_comparison_catches_swapped_values_with_identical_total(config):
    def swap(frame):
        frame.loc[[0, 1], "sales_units"] = frame.loc[[1, 0], "sales_units"].to_numpy()

    _change_parquet(config, swap)
    result = audit_store_item(config)
    assert result["status"] == "invalid"
    assert "row-level sales" in result["critical_errors"][0]


def test_duplicate_persisted_business_keys_are_rejected(config):
    def duplicate(frame):
        frame.loc[1] = frame.loc[0]

    _change_parquet(config, duplicate)
    result = audit_store_item(config)
    assert result["status"] == "invalid"
    assert "Duplicate canonical business keys" in result["critical_errors"][0]


def test_future_competition_dates_cannot_enter_observed_parquet(config):
    def contaminate(frame):
        frame.loc[0, "date"] = pd.Timestamp("2020-01-04")

    _change_parquet(config, contaminate)
    result = audit_store_item(config)
    assert result["status"] == "invalid"
    assert "possible test contamination" in result["critical_errors"][0]


def test_unexpected_canonical_product_is_rejected(config):
    _change_parquet(config, lambda frame: frame.__setitem__("item_id", "99"))
    result = audit_store_item(config)
    assert result["status"] == "invalid"
    assert "extra/invalid item" in result["critical_errors"][0]


def test_missing_source_date_is_a_real_gate_failure(config):
    path = config.paths["raw"] / "store_item/train.csv"
    rows = path.read_text().splitlines()
    path.write_text("\n".join(rows[:2] + rows[3:]) + "\n")
    _manifest(config)
    result = audit_store_item(config)
    assert result["status"] == "invalid"
    assert result["train"]["missing_dates_global_window"] == 1
    assert "date gaps" in result["critical_errors"][0]


def test_duplicate_source_key_is_rejected(config):
    path = config.paths["raw"] / "store_item/train.csv"
    with path.open("a") as stream:
        stream.write("2020-01-01,1,3,0\n")
    _manifest(config)
    result = audit_store_item(config)
    assert result["status"] == "invalid"
    assert result["train"]["duplicate_business_keys_after_first"] == 1


def test_changed_raw_file_fails_acquisition_hash_check(config):
    path = config.paths["raw"] / "store_item/train.csv"
    path.write_text(path.read_text().replace(",0\n", ",1\n"))
    result = audit_store_item(config)
    assert result["status"] == "invalid"
    assert "acquisition baseline" in result["critical_errors"][0]


def test_wrong_physical_parquet_schema_is_rejected(config):
    path = config.paths["processed"] / "store_item/daily_sales.parquet"
    table = pq.read_table(path)
    index = table.schema.get_field_index("sales_units")
    table = table.set_column(index, "sales_units", table["sales_units"].cast(pa.float32()))
    pq.write_table(table, path)
    result = audit_store_item(config)
    assert result["status"] == "invalid"
    assert "physical schema" in result["critical_errors"][0]


def test_test_file_with_sales_labels_is_not_silently_accepted(config):
    path = config.paths["raw"] / "store_item/test.csv"
    frame = pd.read_csv(path)
    frame["sales"] = 0
    frame.to_csv(path, index=False)
    _manifest(config)
    result = audit_store_item(config)
    assert result["status"] == "invalid"
    assert "unexpected source schema" in result["critical_errors"][0]
