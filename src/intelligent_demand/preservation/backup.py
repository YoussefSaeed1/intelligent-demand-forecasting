"""Inventory-driven exclusive local backup; never reads targets as analytical data."""

import argparse
import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def reparse(path):
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0) & 1024)
    except FileNotFoundError:
        return False


def evidence_path(root, relative):
    if not isinstance(relative, str) or "\\" in relative:
        raise ValueError("Evidence identifiers must use relative forward-slash paths")
    logical = PurePosixPath(relative)
    if (not relative or ":" in relative or logical.is_absolute() or PureWindowsPath(relative).drive
            or any(p in {"", "..", "."} for p in relative.split("/"))):
        raise ValueError("Unsafe evidence path")
    credential_names = {".env", "kaggle.json", "access_token", ".aws", ".ssh", ".kaggle"}
    if any(p.lower() in credential_names or p.lower().startswith(".env.")
           or p.lower().endswith((".pem", ".key")) for p in logical.parts):
        raise ValueError("Credential paths are never backed up by this utility")
    current = Path(root)
    for part in logical.parts:
        current = current / part
        if reparse(current):
            raise ValueError("Evidence paths cannot traverse links or junctions")
    result = current.resolve()
    if not result.is_relative_to(Path(root).resolve()):
        raise ValueError("Evidence path escapes root")
    return result


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def backup(source, inventory, destination, inventory_sha256, receipt=None):
    source, inventory = Path(source).resolve(), Path(inventory).resolve()
    destination = Path(destination).absolute()
    # Check every existing ancestor before resolution can hide a junction.
    for parent in (destination, *destination.parents):
        if reparse(parent):
            raise ValueError("Backup destination cannot traverse links/junctions")
    destination = destination.resolve()
    if (source.is_relative_to(destination) or destination.is_relative_to(source)):
        raise ValueError("Source and backup destination must not overlap")
    if destination.exists():
        raise FileExistsError("Backup exists; choose a new destination. Nothing overwritten.")
    if receipt and Path(receipt).exists():
        raise FileExistsError("Verification receipt already exists")
    if sha256(inventory) != inventory_sha256:
        raise ValueError("Authoritative evidence inventory hash differs")
    value = json.loads(inventory.read_text(encoding="utf-8"))
    entries = value["files"]
    if len({e["path"] for e in entries}) != len(entries):
        raise ValueError("Duplicate inventory paths")
    total = sum(e["bytes"] for e in entries)
    if total != value["total_bytes"] or len(entries) != value["file_count"]:
        raise ValueError("Inventory totals do not reconcile")
    sources = []
    for entry in entries:
        if (type(entry["bytes"]) is not int or entry["bytes"] < 0
                or len(entry["sha256"]) != 64):
            raise ValueError("Invalid evidence size or hash")
        path = evidence_path(source, entry["path"])
        if not path.is_file() or path.stat().st_size != entry["bytes"]:
            raise ValueError(f"Missing or wrong-sized original: {entry['path']}")
        if sha256(path) != entry["sha256"]:
            raise ValueError(f"Original evidence hash differs: {entry['path']}")
        sources.append((entry, path))
    ancestor = destination.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    free = shutil.disk_usage(ancestor).free
    reserve = max(1024 ** 3, total // 20)
    if free < total + inventory.stat().st_size + reserve:
        raise ValueError("Insufficient free space including safety reserve")
    destination.mkdir(parents=True, exist_ok=False)
    result = {
        "schema_version": 1, "status": "in_progress",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "backup_kind": (
            "LOCAL BACKUP ON THE SAME DEVICE; not independent off-device backup"
            if source.stat().st_dev == ancestor.stat().st_dev
            else "LOCAL BACKUP ON A DIFFERENT VOLUME; physical device independence unverified"
        ),
        "destination": destination.as_posix(), "inventory_sha256": inventory_sha256,
        "inventory_files": len(entries), "inventory_bytes": total,
        "free_bytes_before": free, "reserve_bytes": reserve, "files": [],
        "missing": [], "mismatched": [], "originals_deleted_moved_or_rewritten": False,
    }
    try:
        for number, (entry, path) in enumerate(sources, 1):
            target = evidence_path(destination, entry["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            before = path.stat()
            with path.open("rb") as incoming, target.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing, length=4 * 1024 ** 2)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            after = path.stat()
            copied = sha256(target)
            if (target.stat().st_size != entry["bytes"] or copied != entry["sha256"]
                    or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
                    or sha256(path) != entry["sha256"]):
                result["mismatched"].append(entry["path"])
                raise ValueError(f"Copy/original verification failed: {entry['path']}")
            result["files"].append({"path": entry["path"], "bytes": entry["bytes"],
                                    "sha256": copied, "status": "verified"})
            if number % 1000 == 0:
                print(f"Copied and verified {number}/{len(entries)} files", flush=True)
        saved_inventory = destination / "EVIDENCE_INVENTORY.json"
        with inventory.open("rb") as src, saved_inventory.open("xb") as dst:
            shutil.copyfileobj(src, dst, length=4 * 1024 ** 2)
        if sha256(destination / "EVIDENCE_INVENTORY.json") != inventory_sha256:
            raise ValueError("Backup inventory copy changed")
        result["status"] = "passed"
    except BaseException as exc:
        result["status"] = "failed"
        result["error_type"] = type(exc).__name__
        raise
    finally:
        result["verified_files"] = len(result["files"])
        result["completed_at_utc"] = datetime.now(UTC).isoformat()
        write_new(destination / "BACKUP_VERIFICATION.json", result)
        if receipt:
            Path(receipt).parent.mkdir(parents=True, exist_ok=True)
            write_new(receipt, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--inventory-sha256", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    report = backup(args.source, args.inventory, args.destination,
                    args.inventory_sha256, args.receipt)
    print(json.dumps({k: v for k, v in report.items() if k != "files"}, indent=2))
