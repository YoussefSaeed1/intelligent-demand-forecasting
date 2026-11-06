"""Atomic local run manifests, exclusive ownership and restart-safe attempt directories."""

import hashlib
import json
import os
import re
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from intelligent_demand.experiments.config import canonical_json, identity


def utc_now():
    return datetime.now(UTC).isoformat()


def file_digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path, value):
    payload = canonical_json(value)
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(payload + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class ExperimentRegistry:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def directory(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise ValueError("Run IDs are 32 lowercase hexadecimal UUID characters")
        result = (self.root / run_id).resolve()
        if not result.is_relative_to(self.root):
            raise ValueError("Run directory escapes registry")
        return result

    def create(self, specification):
        canonical_json(specification)
        self.root.mkdir(parents=True, exist_ok=True)
        run_id = uuid.uuid4().hex
        directory = self.directory(run_id)
        directory.mkdir()
        atomic_json(directory / "specification.json", specification)
        atomic_json(
            directory / "status.json",
            {
                "run_id": run_id,
                "status": "pending",
                "specification_sha256": identity(specification),
                "created_at": utc_now(),
                "attempts": [],
            },
        )
        return run_id

    def read(self, run_id):
        directory = self.directory(run_id)
        status = json.loads((directory / "status.json").read_text())
        specification = json.loads((directory / "specification.json").read_text())
        if identity(specification) != status["specification_sha256"]:
            raise ValueError("Experiment specification was modified")
        return {**status, "specification": specification}

    @contextmanager
    def attempt(self, run_id, specification, *, resume=False):
        directory = self.directory(run_id)
        lock = directory / "execution.lock"
        token = uuid.uuid4().hex
        try:
            with lock.open("x", encoding="utf-8") as stream:
                stream.write(canonical_json({"token": token, "pid": os.getpid()}))
        except FileExistsError as exc:
            raise RuntimeError(
                "Run already owned; live/abandoned locks are never silently stolen"
            ) from exc
        state = None
        started = False
        try:
            state = self.read(run_id)
            if state["specification_sha256"] != identity(specification):
                raise ValueError("Resume configuration/data/code/population does not match")
            permitted = ("pending", "failed", "interrupted") if resume else ("pending",)
            if state["status"] not in permitted:
                raise ValueError("Run cannot start from its current status")
            attempt_id = uuid.uuid4().hex
            attempt_dir = directory / "attempts" / attempt_id
            attempt_dir.mkdir(parents=True)
            state.pop("specification")
            state.update(
                status="running",
                attempt_id=attempt_id,
                owner_token=token,
                owner_pid=os.getpid(),
                started_at=utc_now(),
            )
            state["attempts"].append(attempt_id)
            atomic_json(directory / "status.json", state)
            started = True
            yield attempt_dir
            if self.read(run_id)["status"] != "completed":
                raise RuntimeError("Attempt ended without validated output publication")
        except BaseException as exc:
            if started and self.read(run_id)["status"] != "completed":
                state.update(
                    status="interrupted"
                    if isinstance(exc, (KeyboardInterrupt, SystemExit))
                    else "failed",
                    ended_at=utc_now(),
                    error_type=type(exc).__name__,
                )
                atomic_json(directory / "status.json", state)
            raise
        finally:
            if lock.exists() and json.loads(lock.read_text())["token"] == token:
                lock.unlink()

    def complete(self, run_id, attempt_dir, outputs):
        directory = self.directory(run_id)
        state = self.read(run_id)
        if state["status"] != "running":
            raise ValueError("Only a running attempt can complete")
        lock = directory / "execution.lock"
        if (
            not lock.exists()
            or json.loads(lock.read_text())["token"] != state["owner_token"]
            or state["owner_pid"] != os.getpid()
        ):
            raise ValueError("Completion requires the current attempt's exclusive ownership")
        expected = (directory / "attempts" / state["attempt_id"]).resolve()
        if Path(attempt_dir).resolve() != expected:
            raise ValueError("Attempt does not own this run")
        paths = {}
        for key, value in outputs.items():
            path = Path(value).resolve()
            if (
                not path.is_relative_to(expected)
                or not path.is_file()
                or path.name.endswith(".part")
            ):
                raise ValueError("Only complete attempt-local files may be published")
            paths[key] = {"path": str(path.relative_to(directory)), "sha256": file_digest(path)}
        if not {"predictions", "metrics", "model_metadata"}.issubset(paths):
            raise ValueError("Predictions, metrics and model metadata are required")
        state.pop("specification")
        state.update(status="completed", ended_at=utc_now(), outputs=paths)
        atomic_json(directory / "status.json", state)

    def completed(self, run_id):
        state = self.read(run_id)
        if state["status"] != "completed":
            raise ValueError("Partial/failed/interrupted runs have no completed result")
        directory = self.directory(run_id)
        attempt_id = state.get("attempt_id")
        outputs = state.get("outputs")
        if (
            not isinstance(attempt_id, str)
            or not re.fullmatch(r"[0-9a-f]{32}", attempt_id)
            or attempt_id not in state.get("attempts", [])
            or not isinstance(outputs, dict)
            or not {"predictions", "metrics", "model_metadata"}.issubset(outputs)
        ):
            raise ValueError("Completed result requires its owned attempt and mandatory outputs")
        attempt = (directory / "attempts" / attempt_id).resolve()
        if not attempt.is_relative_to(directory):
            raise ValueError("Completed attempt escapes its run")
        try:
            for output in outputs.values():
                path = (directory / output["path"]).resolve()
                if (
                    not path.is_relative_to(attempt)
                    or path.name.endswith(".part")
                    or file_digest(path) != output["sha256"]
                ):
                    raise ValueError("Completed output is changed, partial or outside its attempt")
        except (OSError, KeyError, TypeError) as exc:
            raise ValueError("Completed experiment output is missing or malformed") from exc
        return state

    def comparison_candidates(self, run_ids):
        """Verify eligibility for a later same-fold comparison; never rank model scores."""
        run_ids = tuple(run_ids)
        if not run_ids or len(set(run_ids)) != len(run_ids):
            raise ValueError("Nonempty unique comparison run IDs required")
        states = [self.completed(run_id) for run_id in run_ids]
        fields = (
            "schema_version", "dataset_id", "fold", "settings", "random_seed",
            "source_fingerprint", "protocol_sha256", "series_count", "series_sha256",
            "classes_sha256", "class_as_of", "code",
        )
        cohorts = []
        for state in states:
            specification = state["specification"]
            if not set(fields).issubset(specification):
                raise ValueError("Comparison requires a complete forecasting specification")
            cohorts.append(identity({key: specification[key] for key in fields}))
        if len(set(cohorts)) != 1:
            raise ValueError(
                "Comparison requires matching protocol, source, population and settings"
            )
        return states

    def recover_interrupted(self, run_id, *, expected_owner_token, owner_confirmed_stopped=False):
        """Explicit operator recovery after a hard kill; never infer a stale lease by age."""
        directory = self.directory(run_id)
        state = self.read(run_id)
        if (
            not owner_confirmed_stopped
            or state["status"] != "running"
            or state["owner_token"] != expected_owner_token
        ):
            raise ValueError("Recovery requires the matching owner and explicit stop confirmation")
        lock = directory / "execution.lock"
        if lock.exists() and json.loads(lock.read_text())["token"] != expected_owner_token:
            raise ValueError("Lock ownership changed")
        state.pop("specification")
        state.update(status="interrupted", ended_at=utc_now(), error_type="ExternalInterruption")
        atomic_json(directory / "status.json", state)
        if lock.exists():
            lock.unlink()
