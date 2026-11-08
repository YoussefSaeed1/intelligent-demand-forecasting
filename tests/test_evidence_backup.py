"""Synthetic inventory backup checks; no real evidence or external destinations."""

import json
from types import SimpleNamespace

import pytest

from intelligent_demand.preservation.backup import backup, evidence_path, sha256


def fixture_inventory(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / ".gitignore").write_bytes(b"original-ignore\n")
    (source / "nested").mkdir()
    (source / "nested/evidence.bin").write_bytes(b"immutable\0evidence")
    entries = [{"path": p.relative_to(source).as_posix(), "bytes": p.stat().st_size,
                "sha256": sha256(p)} for p in source.rglob("*") if p.is_file()]
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"files": entries, "file_count": len(entries),
                                    "total_bytes": sum(e["bytes"] for e in entries)}))
    return source, inventory


def test_backup_preserves_structure_source_gitignore_and_every_hash(tmp_path):
    source, inventory = fixture_inventory(tmp_path)
    target, receipt = tmp_path / "backup", tmp_path / "receipt.json"
    result = backup(source, inventory, target, sha256(inventory), receipt)
    assert result["status"] == "passed" and result["verified_files"] == 2
    assert not result["missing"] and not result["mismatched"]
    assert "SAME DEVICE" in result["backup_kind"]
    for item in result["files"]:
        assert sha256(source / item["path"]) == sha256(target / item["path"]) == item["sha256"]
    assert (target / ".gitignore").read_bytes() == b"original-ignore\n"
    saved = json.loads((target / "BACKUP_VERIFICATION.json").read_text())
    assert json.loads(receipt.read_text()) == saved


def test_existing_backup_is_never_overwritten(tmp_path):
    source, inventory = fixture_inventory(tmp_path)
    target = tmp_path / "backup"
    target.mkdir()
    (target / "owner.txt").write_text("keep")
    with pytest.raises(FileExistsError):
        backup(source, inventory, target, sha256(inventory))
    assert (target / "owner.txt").read_text() == "keep"


@pytest.mark.parametrize("relative", ["../secret", "C:/outside", "/outside", "a\\b",
                                      ".env", "sub/kaggle.json", ".aws/config", "key.pem"])
def test_unsafe_and_credential_paths_rejected(tmp_path, relative):
    with pytest.raises(ValueError):
        evidence_path(tmp_path, relative)


def test_bad_source_hash_does_not_create_backup(tmp_path):
    source, inventory = fixture_inventory(tmp_path)
    (source / "nested/evidence.bin").write_bytes(b"changed")
    with pytest.raises(ValueError, match="wrong-sized original|hash differs"):
        backup(source, inventory, tmp_path / "backup", sha256(inventory))
    assert not (tmp_path / "backup").exists()


def test_overlapping_destination_rejected(tmp_path):
    source, inventory = fixture_inventory(tmp_path)
    with pytest.raises(ValueError, match="overlap"):
        backup(source, inventory, source / "backup", sha256(inventory))


def test_insufficient_space_is_checked_before_copy(tmp_path, monkeypatch):
    source, inventory = fixture_inventory(tmp_path)
    monkeypatch.setattr("intelligent_demand.preservation.backup.shutil.disk_usage",
                        lambda _: SimpleNamespace(free=0))
    with pytest.raises(ValueError, match="Insufficient"):
        backup(source, inventory, tmp_path / "backup", sha256(inventory))
    assert not (tmp_path / "backup").exists()


def test_interrupted_copy_keeps_failure_receipt_and_original(tmp_path, monkeypatch):
    source, inventory = fixture_inventory(tmp_path)
    expected = (source / ".gitignore").read_bytes()

    def interrupted(*args, **kwargs):
        raise OSError("synthetic interrupted copy")

    monkeypatch.setattr("intelligent_demand.preservation.backup.shutil.copyfileobj", interrupted)
    with pytest.raises(OSError, match="synthetic"):
        backup(source, inventory, tmp_path / "backup", sha256(inventory))
    result = json.loads((tmp_path / "backup/BACKUP_VERIFICATION.json").read_text())
    assert result["status"] == "failed" and result["verified_files"] == 0
    assert (source / ".gitignore").read_bytes() == expected
