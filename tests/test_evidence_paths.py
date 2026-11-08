"""Explicit root relocation and path safety in disposable workspaces."""

import json
import shutil

import pytest

from intelligent_demand.preservation.backup import sha256
from intelligent_demand.preservation.paths import EvidenceResolver


def test_relative_and_historical_absolute_identifiers_after_relocation(tmp_path):
    original, relocated = tmp_path / "original", tmp_path / "relocated"
    (original / "cache").mkdir(parents=True)
    path = original / "cache/manifest.json"
    path.write_text(json.dumps({"old_location": "C:/historical/project/cache"}))
    expected = sha256(path)
    shutil.copytree(original, relocated)
    resolver = EvidenceResolver(relocated, "C:/historical/project")
    assert resolver.read_json("C:\\historical\\project\\cache\\manifest.json", expected) == {
        "old_location": "C:/historical/project/cache"
    }
    assert resolver.resolve("cache/manifest.json", expected) == relocated / "cache/manifest.json"
    assert path.read_bytes() == (relocated / "cache/manifest.json").read_bytes()
    assert resolver.reference(relocated / "cache/manifest.json") == {
        "path": "cache/manifest.json", "sha256": expected,
        "bytes": (relocated / "cache/manifest.json").stat().st_size,
    }


@pytest.mark.parametrize("identifier", ["../outside", "cache/../../outside", "C:/other/file",
                                        "C:/historical/project/../outside", "file:stream",
                                        "\\\\server\\share\\file", "/outside"])
def test_traversal_unmapped_absolute_and_network_paths_are_rejected(tmp_path, identifier):
    with pytest.raises(ValueError):
        EvidenceResolver(tmp_path, "C:/historical/project").resolve(identifier)


def test_hash_mismatch_and_unconfigured_absolute_path_fail(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="hash differs"):
        EvidenceResolver(tmp_path).resolve("manifest.json", "0" * 64)
    with pytest.raises(ValueError, match="explicit root mapping"):
        EvidenceResolver(tmp_path).resolve("C:/old/file")


def test_reparse_component_cannot_escape_root(tmp_path, monkeypatch):
    child = tmp_path / "redirect"
    child.mkdir()
    monkeypatch.setattr("intelligent_demand.preservation.paths.reparse", lambda p: p == child)
    with pytest.raises(ValueError, match="reparse"):
        EvidenceResolver(tmp_path).resolve("redirect/manifest.json")
