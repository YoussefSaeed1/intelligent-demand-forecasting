"""Future validation orchestration; no built-in models or real-data execution at import."""

import logging
import platform
import subprocess
import time
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import pandas as pd

from intelligent_demand.evaluation.predictions import PredictionWriter, validate_prediction_frame
from intelligent_demand.evaluation.scoring import score_predictions, training_scales
from intelligent_demand.evaluation.splits import validate_fold
from intelligent_demand.experiments.config import identity
from intelligent_demand.experiments.registry import atomic_json, file_digest

LOGGER = logging.getLogger(__name__)


def provenance(root):
    root = Path(root).resolve()
    git = ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root)]
    revision, dirty = None, None
    try:
        revision = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(git + ["status", "--porcelain"], text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        pass
    package = Path(__file__).resolve().parents[1]
    return {
        "git_revision": revision,
        "git_dirty": dirty,
        "python": platform.python_version(),
        "package_versions": {name: version(name) for name in ("numpy", "pandas", "pyarrow")},
        "code_sha256": {
            p.relative_to(package).as_posix(): file_digest(p) for p in sorted(package.rglob("*.py"))
        },
    }


def experiment_specification(
    config,
    fold,
    model_info,
    model_config,
    series,
    source_fingerprint,
    code_metadata,
    classes=None,
    class_as_of=None,
):
    validate_fold(fold)
    if not series or len(series) != len(set(series)):
        raise ValueError("Unique comparison population required")
    if len(source_fingerprint) != 64 or any(
        c not in "0123456789abcdef" for c in source_fingerprint
    ):
        raise ValueError("Source fingerprint must be SHA-256")
    if not isinstance(code_metadata, dict) or not (
        code_metadata.get("git_revision") or code_metadata.get("code_sha256")
    ):
        raise ValueError("Code provenance requires a Git revision or explicit source hashes")
    if classes is not None and (
        set(classes) != set(series) or class_as_of is None or class_as_of > fold.origin
    ):
        raise ValueError("Class labels must cover the population and be known by origin")
    return {
        "schema_version": 1,
        "dataset_id": fold.dataset_id,
        "fold": {
            k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in asdict(fold).items()
        },
        "model": asdict(model_info),
        "model_configuration": model_config,
        "settings": config.metadata(),
        "random_seed": config.random_seed,
        "source_fingerprint": source_fingerprint,
        "protocol_sha256": file_digest(config.split_manifest),
        "series_count": len(series),
        "series_sha256": identity(sorted(series)),
        "classes_sha256": identity(classes) if classes is not None else None,
        "class_as_of": str(class_as_of) if class_as_of is not None else None,
        "code": code_metadata,
    }


def execute_validation(
    *,
    config,
    fold,
    source,
    series,
    models,
    model_info,
    model_config,
    registry,
    source_fingerprint,
    code_metadata,
    run_id=None,
    resume=False,
    classes=None,
    class_as_of=None,
):
    """Future execution API, exercised only with small fixture doubles during Phase 3A."""
    for key, expected in (("random_seed", config.random_seed), ("max_threads", config.max_threads)):
        if key in model_config and model_config[key] != expected:
            raise ValueError("Model parameters cannot override experiment seed/resource policy")
    series = tuple(sorted(series))
    if len(series) * fold.horizon > config.max_evaluation_rows:
        raise ValueError("Evaluation population exceeds the declared memory row budget")
    specification = experiment_specification(
        config,
        fold,
        model_info,
        model_config,
        series,
        source_fingerprint,
        code_metadata,
        classes,
        class_as_of,
    )
    if run_id is None:
        run_id = registry.create(specification)
    LOGGER.info("Run %s: checking specification and source identity", run_id)
    current = registry.read(run_id)
    if current["specification_sha256"] != identity(specification):
        raise ValueError("Run specification mismatch")
    if current["status"] == "completed":
        if file_digest(source.path) != source_fingerprint:
            raise ValueError("Source fingerprint changed; completed output cannot be reused")
        return registry.completed(run_id)
    with registry.attempt(run_id, specification, resume=resume) as attempt:
        started = time.perf_counter()
        if file_digest(source.path) != source_fingerprint:
            raise ValueError("Source data fingerprint changed")
        view = source.at_origin(fold, series)
        LOGGER.info("%s: computing training-only weekly scales", run_id)
        scales = (
            source.scales(fold, series)
            if hasattr(source, "scales")
            else training_scales(view.history(), fold, series, config.season_days)
        )
        stages = {
            "training_preparation_seconds": time.perf_counter() - started,
            "model_fit_seconds": 0.0,
            "prediction_publication_seconds": 0.0,
            "model_artifacts_seconds": 0.0,
        }
        writer = PredictionWriter(
            attempt / "predictions.parquet", fold, series, model_info, run_id, config.batch_rows
        )
        metadata = []
        artifacts = {}
        try:
            populations = [(key,) for key in series] if model_info.scope == "local" else [series]
            for number, population in enumerate(populations):
                model = models.create(model_info.identifier, model_info.version)
                training = source.at_origin(fold, population)
                stage_started = time.perf_counter()
                model.fit(
                    training,
                    {
                        **model_config,
                        "random_seed": config.random_seed,
                        "max_threads": config.max_threads,
                    },
                )
                stages["model_fit_seconds"] += time.perf_counter() - stage_started
                stage_started = time.perf_counter()
                predicted = model.predict(fold.origin, fold.horizon, training.calendar_features())
                if isinstance(predicted, pd.DataFrame):
                    predicted = [predicted]
                for batch in predicted:
                    validate_prediction_frame(batch, fold, population)
                    writer.write(batch)
                stages["prediction_publication_seconds"] += time.perf_counter() - stage_started
                stage_started = time.perf_counter()
                model_dir = attempt / "models" / str(number)
                model_dir.mkdir(parents=True)
                for key, value in model.save_artifacts(model_dir).items():
                    artifact = Path(value)
                    artifact = (
                        (model_dir / artifact).resolve()
                        if not artifact.is_absolute()
                        else artifact.resolve()
                    )
                    if not artifact.is_relative_to(model_dir.resolve()):
                        raise ValueError(
                            "Model artefact escaped its supplied persistence directory"
                        )
                    artifacts[f"model_{number}_{key}"] = artifact
                metadata.append(model.metadata())
                stages["model_artifacts_seconds"] += time.perf_counter() - stage_started
                if number % 100 == 0:
                    LOGGER.info(
                        "%s: model units processed %s/%s", run_id, number + 1, len(populations)
                    )
            stage_started = time.perf_counter()
            writer.finish()
            stages["prediction_publication_seconds"] += time.perf_counter() - stage_started
            LOGGER.info("%s: complete predictions sealed; validation scoring starts", run_id)
        finally:
            writer.close()
        # Validation targets become visible to the evaluator only after predictions are sealed.
        stage_started = time.perf_counter()
        chunks, count = [], 0
        for batch in source.validation_targets(fold, series):
            count += len(batch)
            if count > config.max_evaluation_rows:
                raise ValueError("Actual-target read exceeded evaluation row budget")
            chunks.append(batch)
        if not chunks:
            raise ValueError("Validation target window is empty")
        actuals = pd.concat(chunks, ignore_index=True)
        actuals = actuals.rename(columns={"date": "target_date", "sales_units": "actual"})
        predictions = pd.read_parquet(attempt / "predictions.parquet")
        scores = score_predictions(actuals, predictions, scales, fold, series, classes, class_as_of)
        stages["validation_read_and_scoring_seconds"] = time.perf_counter() - stage_started
        scores["runtime_stages"] = stages
        scores["elapsed_seconds"] = time.perf_counter() - started
        atomic_json(attempt / "metrics.json", scores)
        atomic_json(attempt / "model_metadata.json", metadata)
        if file_digest(source.path) != source_fingerprint:
            raise ValueError("Source changed during execution")
        registry.complete(
            run_id,
            attempt,
            {
                "predictions": attempt / "predictions.parquet",
                "metrics": attempt / "metrics.json",
                "model_metadata": attempt / "model_metadata.json",
                **artifacts,
            },
        )
    return registry.completed(run_id)
