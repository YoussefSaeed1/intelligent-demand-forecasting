"""Future ingestion guard regressions; all sources and outputs are disposable."""

import pandas as pd
import pytest

from intelligent_demand.config import ProjectConfig
from intelligent_demand.ingestion.datasets import DATASETS
from intelligent_demand.validation.pipeline import profile_dataset
from intelligent_demand.validation.quality import CanonicalWriter


def profile(tmp_path, dates):
    config = ProjectConfig("synthetic", 42, 28, {
        name: tmp_path / name for name in ("raw", "interim", "processed", "artifacts", "reports")
    })
    raw = config.paths["raw"] / "store_item"
    raw.mkdir(parents=True)
    (raw / "train.csv").write_text("date,store,item,sales\n" + "".join(
        f"{day},1,2,3\n" for day in dates))
    (raw / "test.csv").write_text("id,date,store,item\n0,2020-01-03,1,2\n")
    return profile_dataset(DATASETS["store_item"], config), config


@pytest.mark.parametrize("dates", [
    ["2020-01-01", "2020-1-1"], ["2020-01-01", "2020-01-01"],
    ["2020-01-01", "2020-01-01T00:00:00"], ["not-a-date"],
    ["2020-01-01T00:00:00Z"], ["2020-01-01+02:00"],
])
def test_ambiguous_invalid_or_duplicate_source_dates_cannot_publish(tmp_path, dates):
    report, config = profile(tmp_path, dates)
    assert report["status"] == "invalid"
    assert report["critical_errors"] and not report["transformation"]["output_published"]
    assert not (config.paths["processed"] / "store_item/daily_sales.parquet").exists()


def frame(day, series="1:12"):
    return pd.DataFrame({"dataset_id": ["store_item"], "series_id": [series],
                         "date": [pd.Timestamp(day)], "sales_units": [3.0],
                         "store_id": ["1"], "item_id": ["2"], "category_id": [None],
                         "unit_price": [None], "is_observed": [True]})


def test_writer_rejects_duplicate_after_timestamp_to_day_normalisation(tmp_path):
    writer = CanonicalWriter(tmp_path / "synthetic.parquet")
    writer.append(frame("2020-01-01"))
    with pytest.raises(ValueError, match="Duplicate canonical"):
        writer.append(frame("2020-01-01 23:59:00"))
    with pytest.raises(ValueError, match="do not publish"):
        writer.close()
    assert not list(tmp_path.glob("*.sqlite"))


def test_join_expansion_and_alias_series_cannot_bypass_business_keys(tmp_path):
    writer = CanonicalWriter(tmp_path / "synthetic.parquet")
    joined = pd.concat([frame("2020-01-01"), frame("2020-01-01", "alias")])
    with pytest.raises(ValueError, match="Duplicate canonical"):
        writer.append(joined)
    with pytest.raises(ValueError, match="do not publish"):
        writer.close()


def test_writer_rejects_timezone_ambiguity(tmp_path):
    writer = CanonicalWriter(tmp_path / "synthetic.parquet")
    with pytest.raises(ValueError, match="timezone-naive"):
        writer.append(frame("2020-01-01T00:00:00+02:00"))
    with pytest.raises(ValueError, match="do not publish"):
        writer.close()


def test_valid_source_values_and_canonical_keys_are_preserved(tmp_path):
    report, config = profile(tmp_path, ["2020-01-01", "2020-01-02"])
    assert report["status"] == "passed_with_warnings"
    assert report["transformation"]["canonical_business_keys_unique"]
    result = pd.read_parquet(config.paths["processed"] / "store_item/daily_sales.parquet")
    assert result.sales_units.tolist() == [3.0, 3.0]
    assert not result.duplicated(["dataset_id", "date", "store_id", "item_id"]).any()


def test_duplicate_report_names_normalised_key_failure(tmp_path):
    report, _ = profile(tmp_path, ["2020-01-01", "2020-1-1"])
    assert report["profiles"]["train.csv"]["duplicate_keys_after_first"] == 1
    assert any("duplicate canonical" in message for message in report["critical_errors"])
