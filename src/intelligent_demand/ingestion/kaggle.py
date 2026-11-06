"""Credential-safe adapter around the official Kaggle CLI."""

import csv
import io
import json
import logging
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from tempfile import TemporaryDirectory

from intelligent_demand.ingestion.datasets import DatasetSpec, file_inventory, write_json

LOGGER = logging.getLogger(__name__)


def _reserved(part: str) -> bool:
    if hasattr(os.path, "isreserved"):
        return os.path.isreserved(part)
    return PureWindowsPath(part).is_reserved()


class AcquisitionError(RuntimeError):
    """Sanitised acquisition failure safe to show in logs."""


def safe_error(output: str) -> AcquisitionError:
    """Classify client failures without returning its potentially sensitive text."""
    text = output.lower()
    if any(
        word in text
        for word in (
            "401",
            "unauthenticated",
            "unauthorized",
            "credentials",
            "access_token",
            "kaggle_api_token",
            "authenticate",
        )
    ):
        return AcquisitionError(
            "Kaggle authentication unavailable or rejected. Configure official user-level "
            "authentication as described in docs/DATASETS.md; never paste secrets into chat."
        )
    if any(word in text for word in ("403", "forbidden", "permission", "must accept", "rules")):
        return AcquisitionError(
            "Kaggle competition access denied. Visit the competition rules page and manually "
            "join/accept if appropriate; account verification or other restrictions may also apply."
        )
    if any(
        word in text
        for word in (
            "connection",
            "getaddrinfo",
            "timeout",
            "timed out",
            "network",
            "resolve",
            "10013",
        )
    ):
        return AcquisitionError("Kaggle network request failed. Check connectivity and retry.")
    return AcquisitionError(
        "Kaggle operation failed. Check account access, client version and connectivity; "
        "raw client output was suppressed to protect credentials."
    )


class KaggleCLI:
    """Use official authentication, inherited environment and no shell interpolation."""

    def run(self, arguments: list[str], timeout: int = 120) -> str:
        """Capture all client output, exposing only whitelisted summaries on failure."""
        config_dir = os.environ.get("KAGGLE_CONFIG_DIR")
        if config_dir and Path(config_dir).resolve().is_relative_to(Path.cwd().resolve()):
            raise AcquisitionError("KAGGLE_CONFIG_DIR must be outside the project repository.")
        try:
            # Isolate client cwd so it cannot auto-load a project-local .env file.
            with TemporaryDirectory(prefix="demand-kaggle-client-") as temporary:
                result = subprocess.run(
                    [sys.executable, "-m", "kaggle", *arguments],
                    cwd=temporary,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                    check=False,
                )
        except subprocess.TimeoutExpired:
            raise AcquisitionError("Kaggle network operation timed out; retry safely.") from None
        except OSError:
            raise AcquisitionError(
                "Could not start Kaggle CLI in the current environment."
            ) from None
        if result.returncode:
            raise safe_error(result.stdout + result.stderr) from None
        return result.stdout

    def authenticate(self) -> None:
        """Use the user's entered-competitions listing as a read-only authenticated check."""
        self.run(["competitions", "list", "--group", "entered", "--csv"])

    def files(self, spec: DatasetSpec) -> list[str]:
        """Inspect a bounded listing for these small competition manifests."""
        output = self.run(
            [
                "competitions",
                "files",
                spec.competition,
                "--csv",
                "--page-size",
                "200",
                "--quiet",
            ]
        )
        rows = list(csv.DictReader(io.StringIO(output)))
        names = [row.get("name", "") for row in rows]
        if not names or not all(names):
            raise AcquisitionError("Kaggle file listing was empty or had an unsupported format.")
        return names

    def download(self, spec: DatasetSpec, destination: Path) -> None:
        """Download an archive only; use our checked extraction instead of --unzip."""
        self.run(
            [
                "competitions",
                "download",
                spec.competition,
                "--path",
                str(destination.resolve()),
                "--quiet",
            ],
            timeout=1800,
        )


def safe_extract(archive: Path, destination: Path) -> list[Path]:
    """Extract bounded regular files; reject traversal, links and Windows aliases."""
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as zipped:
        members = zipped.infolist()
        if len(members) > 1000 or sum(m.file_size for m in members) > 5 * 1024**3:
            raise AcquisitionError("ZIP exceeds extraction size/member limits.")
        targets = []
        seen = set()
        for member in members:
            # ZipInfo normalises separators on Windows; validate the original ZIP name.
            name = member.orig_filename
            posix = PurePosixPath(name)
            windows = PureWindowsPath(name)
            mode = member.external_attr >> 16
            target = destination.joinpath(*posix.parts).resolve()
            if (
                "\\" in name
                or ":" in name
                or posix.is_absolute()
                or windows.drive
                or ".." in posix.parts
                or not target.is_relative_to(destination)
                or stat.S_ISLNK(mode)
                or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))
                or any(p.endswith((".", " ")) or _reserved(p) for p in posix.parts)
                or any(ord(c) < 32 or c in '<>"|?*' for c in name)
                or str(target).casefold() in seen
            ):
                raise AcquisitionError("Unsafe or duplicate ZIP member rejected.")
            seen.add(str(target).casefold())
            if target.exists():
                raise AcquisitionError("ZIP extraction refuses to overwrite existing files.")
            targets.append((member, target))
        extracted = []
        for member, target in targets:
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            extracted.append(target)
    return extracted


def download_dataset(
    spec: DatasetSpec,
    raw_root: Path,
    client: KaggleCLI,
    force: bool = False,
) -> dict:
    """Stage, validate and publish source files without implicit raw-data replacement."""
    directory = raw_root / spec.name
    directory.mkdir(parents=True, exist_ok=True)
    inventory = file_inventory(directory, spec)
    manifest_path = directory / "acquisition.json"
    previous = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    )
    previous_hashes = {r["filename"]: r.get("sha256") for r in previous.get("files", [])}
    existing = [r for r in inventory["files"] if r["status"] != "missing"]
    for record in existing:
        changed = record["filename"] in previous_hashes and previous_hashes[
            record["filename"]
        ] != record.get("sha256")
        if not force and (record["status"] != "header_valid" or changed):
            raise AcquisitionError(
                "Existing raw file is invalid or changed; inspect it or use --force."
            )
    remote = client.files(spec)
    LOGGER.info("%s: competition listing accessible (%s files)", spec.name, len(remote))
    # A listing alone does not prove download entitlement; the download endpoint enforces rules.
    if (
        not force
        and inventory["ready_for_profiling"]
        and all((directory / name).is_file() for name in spec.expected if name in remote)
    ):
        inventory.update(
            action="skipped_existing",
            provenance="local files; no new download",
            remote_files=remote,
        )
        LOGGER.info(
            "%s: skipping existing files with valid headers and checked local hashes", spec.name
        )
        return inventory
    try:
        with TemporaryDirectory(prefix=".acquire-", dir=directory) as staging:
            staging_path = Path(staging)
            LOGGER.info("%s: downloading to temporary staging directory", spec.name)
            client.download(spec, staging_path)
            archive = staging_path / f"{spec.competition}.zip"
            if not archive.is_file():
                raise AcquisitionError("Kaggle did not produce the expected competition ZIP.")
            extracted = staging_path / "extracted"
            safe_extract(archive, extracted)
            incoming = file_inventory(extracted, spec)
            if not incoming["ready_for_profiling"] or any(
                r["status"] not in ("missing", "header_valid") for r in incoming["files"]
            ):
                raise AcquisitionError(
                    "Downloaded archive lacks required files or valid CSV headers."
                )
            published = set()
            for record in incoming["files"]:
                source = extracted / record["filename"]
                target = directory / record["filename"]
                if not source.is_file():
                    continue
                if target.exists() and not force:
                    continue
                if force:
                    source.replace(target)
                else:
                    os.link(source, target)  # Atomic create; never replace an existing raw path.
                published.add(record["filename"])
            inventory = file_inventory(directory, spec)
            old_records = {r["filename"]: r for r in previous.get("files", [])}
            for record in inventory["files"]:
                if record["status"] == "missing":
                    continue
                fresh = record["filename"] in published
                record["acquisition_method"] = "kaggle_download" if fresh else "preserved_existing"
                record["downloaded_at_utc"] = (
                    incoming["checked_at_utc"]
                    if fresh
                    else old_records.get(record["filename"], {}).get("downloaded_at_utc")
                )
            inventory.update(
                action="downloaded",
                downloaded_at_utc=incoming["checked_at_utc"],
                source_url=f"https://www.kaggle.com/competitions/{spec.competition}/data",
                remote_files=remote,
                validation_status="headers_and_local_hashes_verified",
                notes="SHA-256 is a local provenance checksum, not a publisher authenticity proof.",
            )
            write_json(manifest_path, inventory)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        if isinstance(exc, AcquisitionError):
            raise
        raise AcquisitionError(
            "Archive validation or local publication failed; inspect local storage."
        ) from None
    LOGGER.info("%s: verified files available at %s", spec.name, directory)
    return inventory
