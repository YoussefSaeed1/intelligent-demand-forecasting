"""Cross-process exclusive case ownership; abandoned locks require explicit recovery."""

import json
import os
import re
import uuid
from pathlib import Path

import psutil


class CaseOwnedError(RuntimeError):
    """Another or uncertain owner already holds the case."""


def _read(path):
    if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 1024:
        raise ValueError("Lock cannot be a link or reparse point")
    return json.loads(path.read_text(encoding="utf-8"))


def owner_state(record):
    try:
        process = psutil.Process(record["pid"])
        if abs(process.create_time() - record["process_created"]) > 0.001:
            return "original_owner_stopped_pid_reused"
        return "alive" if process.is_running() else "stopped"
    except psutil.NoSuchProcess:
        return "stopped"
    except (psutil.AccessDenied, KeyError, TypeError, ValueError):
        return "uncertain"


class CaseLock:
    def __init__(self, path):
        self.path = Path(path)
        self.token = uuid.uuid4().hex
        self.record = {"token": self.token, "pid": os.getpid(),
                       "process_created": psutil.Process().create_time()}

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        recovery = self.path.with_name(self.path.name + ".recovery")
        if recovery.exists():
            raise CaseOwnedError("Explicit lock recovery is in progress; no automatic takeover")
        try:
            with self.path.open("x", encoding="utf-8") as stream:
                json.dump(self.record, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise CaseOwnedError(
                "Case already owned or abandoned; explicitly recover a confirmed stopped owner"
            ) from exc
        return self

    def __exit__(self, exc_type, exc, tb):
        record = _read(self.path)
        if record != self.record or os.getpid() != self.record["pid"]:
            raise CaseOwnedError("Ownership changed; refusing to remove another owner's lock")
        self.path.unlink()


def recover_abandoned(path, *, expected_token):
    """Explicit recovery only after matching token and proving the original process exited."""
    path = Path(path)
    if not isinstance(expected_token, str) or not re.fullmatch(r"[0-9a-f]{32}", expected_token):
        raise ValueError("Expected ownership token must be 32 hexadecimal characters")
    recovery = path.with_name(path.name + ".recovery")
    with CaseLock(recovery):
        record = _read(path)
        if record.get("token") != expected_token:
            raise CaseOwnedError("Recovery token changed; inspect again")
        if owner_state(record) not in ("stopped", "original_owner_stopped_pid_reused"):
            raise CaseOwnedError("Owner is alive or uncertain; recovery refused")
        archive = path.with_name(path.name + f".abandoned-{expected_token}.json")
        with archive.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        if _read(path) != record:
            raise CaseOwnedError("Ownership changed during recovery; original lock retained")
        path.unlink()
    return archive
