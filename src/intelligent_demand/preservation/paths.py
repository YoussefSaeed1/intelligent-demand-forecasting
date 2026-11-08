"""Explicit read-only relocation without rewriting historical absolute path records."""

import json
from pathlib import Path, PurePosixPath, PureWindowsPath

from intelligent_demand.preservation.backup import sha256


def reparse(path):
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0) & 1024)
    except FileNotFoundError:
        return False


class EvidenceResolver:
    def __init__(self, workspace_root, historical_root=None):
        physical = Path(workspace_root).absolute()
        if any(reparse(p) for p in (physical, *physical.parents)):
            raise ValueError("Workspace root traverses a link or reparse point")
        self.root = physical.resolve()
        self.historical_root = None if historical_root is None else str(historical_root)

    def logical_id(self, value):
        text = str(value)
        windows = PureWindowsPath(text)
        if ".." in windows.parts or ".." in PurePosixPath(text).parts:
            raise ValueError("Parent traversal is forbidden")
        if windows.drive or windows.is_absolute() or PurePosixPath(text).is_absolute():
            if self.historical_root is None:
                raise ValueError("Historical absolute paths require an explicit root mapping")
            if windows.drive:
                if windows.drive.startswith("\\\\"):
                    raise ValueError("UNC/network paths are not supported")
                try:
                    logical = windows.relative_to(PureWindowsPath(self.historical_root)).as_posix()
                except ValueError as exc:
                    raise ValueError("Path is outside the configured historical root") from exc
            else:
                logical = PurePosixPath(text).relative_to(self.historical_root).as_posix()
        else:
            logical = text.replace("\\", "/")
        if not logical or ":" in logical or any(p in {"", ".", ".."} for p in logical.split("/")):
            raise ValueError("Invalid logical evidence identifier")
        return logical

    def resolve(self, value, expected_sha256=None):
        logical = self.logical_id(value)
        current = self.root
        for component in logical.split("/"):
            current = current / component
            if reparse(current):
                raise ValueError("Evidence path traverses a link or reparse point")
        path = current.resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Evidence path escapes configured root")
        if expected_sha256 is not None and sha256(path) != expected_sha256:
            raise ValueError("Resolved artifact hash differs from preserved evidence")
        return path

    def read_json(self, value, expected_sha256):
        return json.loads(self.resolve(value, expected_sha256).read_text(encoding="utf-8"))

    def reference(self, path):
        """Create a portable future-manifest reference without modifying legacy records."""
        physical = Path(path).absolute()
        if not physical.is_relative_to(self.root):
            raise ValueError("Future artifact reference must be inside configured workspace")
        logical = physical.relative_to(self.root).as_posix()
        physical = self.resolve(logical)
        return {"path": logical, "sha256": sha256(physical), "bytes": physical.stat().st_size}
