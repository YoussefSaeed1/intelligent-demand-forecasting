"""Offline acquisition tests; tiny fixtures are not project datasets or research evidence."""

import json
import stat
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from intelligent_demand.ingestion.datasets import DATASETS, file_inventory, select_datasets
from intelligent_demand.ingestion.kaggle import (
    AcquisitionError,
    KaggleCLI,
    download_dataset,
    safe_error,
    safe_extract,
)

TRAIN = "date,store,item,sales\n2020-01-01,1,2,3\n"
TEST = "id,date,store,item\n0,2020-01-02,1,2\n"


def source_files(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "train.csv").write_text(TRAIN, encoding="utf-8")
    (directory / "test.csv").write_text(TEST, encoding="utf-8")


@pytest.mark.parametrize("selection,count", [("all", 2), ("store_item", 1), ("m5", 1)])
def test_selection(selection, count):
    assert len(select_datasets(selection)) == count


def test_invalid_selection():
    with pytest.raises(ValueError):
        select_datasets("unknown")


def test_file_inventory_checks_headers_and_hashes(tmp_path):
    source_files(tmp_path)
    result = file_inventory(tmp_path, DATASETS["store_item"])
    assert result["ready_for_profiling"]
    assert len(result["files"][0]["sha256"]) == 64
    (tmp_path / "train.csv").write_text("wrong\n1\n", encoding="utf-8")
    assert not file_inventory(tmp_path, DATASETS["store_item"])["ready_for_profiling"]


def test_skips_existing_files_without_download(tmp_path):
    source_files(tmp_path / "store_item")
    client = Mock()
    client.files.return_value = ["train.csv", "test.csv"]
    result = download_dataset(DATASETS["store_item"], tmp_path, client)
    assert result["action"] == "skipped_existing"
    client.download.assert_not_called()


def test_rejects_changed_previously_hashed_file(tmp_path):
    directory = tmp_path / "store_item"
    source_files(directory)
    manifest = file_inventory(directory, DATASETS["store_item"])
    (directory / "acquisition.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "train.csv").write_text(TRAIN + "2020-01-02,1,2,4\n", encoding="utf-8")
    with pytest.raises(AcquisitionError, match="changed"):
        download_dataset(DATASETS["store_item"], tmp_path, Mock())


def test_download_failure_preserves_raw_files(tmp_path):
    source_files(tmp_path / "store_item")
    client = Mock()
    client.files.return_value = ["train.csv", "test.csv"]
    client.download.side_effect = AcquisitionError("Kaggle network request failed")
    with pytest.raises(AcquisitionError, match="network"):
        download_dataset(DATASETS["store_item"], tmp_path, client, force=True)
    assert (tmp_path / "store_item/train.csv").read_text() == TRAIN


def test_staged_download_records_actual_provenance(tmp_path):
    client = Mock()
    client.files.return_value = ["train.csv", "test.csv"]

    def download(spec, destination):
        with zipfile.ZipFile(destination / f"{spec.competition}.zip", "w") as archive:
            archive.writestr("train.csv", TRAIN)
            archive.writestr("test.csv", TEST)

    client.download.side_effect = download
    result = download_dataset(DATASETS["store_item"], tmp_path, client)
    assert result["action"] == "downloaded"
    assert result["downloaded_at_utc"]
    assert (tmp_path / "store_item/acquisition.json").is_file()


@pytest.mark.parametrize(
    "name",
    [
        "../escape.csv",
        "/absolute.csv",
        "C:/bad.csv",
        "dir\\escape.csv",
        "CON.csv",
        "bad.csv:stream",
    ],
)
def test_zip_rejects_unsafe_names(tmp_path, name):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        member = zipfile.ZipInfo("placeholder")
        member.filename = name  # Bypass ZipInfo's Windows separator normalisation.
        zipped.writestr(member, "untrusted")
    with pytest.raises(AcquisitionError, match="Unsafe"):
        safe_extract(archive, tmp_path / "out")


def test_zip_rejects_symlinks_and_case_collisions(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        link = zipfile.ZipInfo("link.csv")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        zipped.writestr(link, "../target")
    with pytest.raises(AcquisitionError):
        safe_extract(archive, tmp_path / "out")
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("a.csv", "one")
        zipped.writestr("A.csv", "two")
    with pytest.raises(AcquisitionError):
        safe_extract(archive, tmp_path / "out")


def test_zip_does_not_overwrite(tmp_path):
    archive = tmp_path / "files.zip"
    destination = tmp_path / "out"
    destination.mkdir()
    (destination / "train.csv").write_text("original")
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("train.csv", TRAIN)
    with pytest.raises(AcquisitionError, match="overwrite"):
        safe_extract(archive, destination)
    assert (destination / "train.csv").read_text() == "original"


@pytest.mark.parametrize(
    "error,expected",
    [
        ("401 Unauthorized SECRET", "authentication"),
        ("403 Forbidden SECRET", "manually"),
        ("must accept competition rules SECRET", "manually"),
        ("getaddrinfo connection failed SECRET", "network"),
        ("unexpected SECRET", "suppressed"),
    ],
)
def test_error_messages_never_echo_client_output(error, expected):
    result = str(safe_error(error))
    assert expected in result
    assert "SECRET" not in result


def test_authentication_uses_official_read_only_command(monkeypatch):
    client = KaggleCLI()
    client.run = Mock(return_value="")
    client.authenticate()
    client.run.assert_called_once_with(["competitions", "list", "--group", "entered", "--csv"])


def test_cli_failure_output_is_captured(monkeypatch):
    monkeypatch.delenv("KAGGLE_CONFIG_DIR", raising=False)
    runner = Mock(return_value=subprocess.CompletedProcess([], 1, "401 SECRET", "SECRET"))
    monkeypatch.setattr(subprocess, "run", runner)
    with pytest.raises(AcquisitionError, match="authentication") as failure:
        KaggleCLI().authenticate()
    assert "SECRET" not in str(failure.value)
    assert runner.call_args.kwargs["capture_output"]
    assert runner.call_args.kwargs["stdin"] == subprocess.DEVNULL


def test_repository_credential_directory_rejected(monkeypatch):
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(Path.cwd() / ".kaggle"))
    with pytest.raises(AcquisitionError, match="outside"):
        KaggleCLI().authenticate()


def test_force_replaces_only_after_a_valid_download(tmp_path):
    directory = tmp_path / "store_item"
    source_files(directory)
    client = Mock()
    client.files.return_value = ["train.csv", "test.csv"]

    def download(spec, destination):
        with zipfile.ZipFile(destination / f"{spec.competition}.zip", "w") as archive:
            archive.writestr("train.csv", TRAIN.replace(",3\n", ",7\n"))
            archive.writestr("test.csv", TEST)

    client.download.side_effect = download
    result = download_dataset(DATASETS["store_item"], tmp_path, client, force=True)
    assert ",7\n" in (directory / "train.csv").read_text()
    assert result["files"][0]["acquisition_method"] == "kaggle_download"


def test_partial_acquisition_preserves_existing_raw_data_and_unknown_timestamp(tmp_path):
    directory = tmp_path / "store_item"
    directory.mkdir()
    (directory / "train.csv").write_text(TRAIN)
    client = Mock()
    client.files.return_value = ["train.csv", "test.csv"]

    def download(spec, destination):
        with zipfile.ZipFile(destination / f"{spec.competition}.zip", "w") as archive:
            archive.writestr("train.csv", TRAIN.replace(",3\n", ",7\n"))
            archive.writestr("test.csv", TEST)

    client.download.side_effect = download
    result = download_dataset(DATASETS["store_item"], tmp_path, client)
    assert (directory / "train.csv").read_text() == TRAIN
    assert result["files"][0]["acquisition_method"] == "preserved_existing"
    assert result["files"][0]["downloaded_at_utc"] is None


def test_header_only_files_are_not_ready(tmp_path):
    source_files(tmp_path)
    (tmp_path / "train.csv").write_text("date,store,item,sales\n")
    assert not file_inventory(tmp_path, DATASETS["store_item"])["ready_for_profiling"]


def test_file_listing_uses_official_csv_and_sanitises_permission_failure():
    client = KaggleCLI()
    client.run = Mock(return_value="name,size,creationDate\ntrain.csv,1KB,2020-01-01\n")
    assert client.files(DATASETS["store_item"]) == ["train.csv"]
    client.run.side_effect = safe_error("403 Forbidden sensitive response")
    with pytest.raises(AcquisitionError, match="manually") as failure:
        client.files(DATASETS["store_item"])
    assert "sensitive" not in str(failure.value)
