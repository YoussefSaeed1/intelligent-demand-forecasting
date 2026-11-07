"""Configuration, dataset acquisition and Phase 1 quality gates."""

import argparse
import logging
from pathlib import Path

import yaml

from intelligent_demand.config import load_config
from intelligent_demand.ingestion.datasets import file_inventory, select_datasets, write_json
from intelligent_demand.ingestion.kaggle import AcquisitionError, KaggleCLI, download_dataset


def main() -> None:
    """Run explicit subcommands; retain the original dataset-free default."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    commands = parser.add_subparsers(dest="command")
    for name in ("forecast-plan", "forecast-models", "experiment-status"):
        command = commands.add_parser(name)
        command.add_argument("--settings", type=Path, default=Path("configs/forecasting.yaml"))
        if name == "experiment-status":
            command.add_argument("--run-id", required=True)
    for name in (
        "download-data",
        "discover-data",
        "check-access",
        "profile-data",
        "audit-store-item",
        "eda",
    ):
        command = commands.add_parser(name)
        if name == "audit-store-item":
            command.set_defaults(dataset="store_item")
        else:
            command.add_argument("--dataset", choices=["all", "store_item", "m5"], default="all")
        if name == "download-data":
            command.add_argument("--force", action="store_true")
        if name == "eda":
            command.add_argument("--settings", type=Path, default=Path("configs/eda.yaml"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        config = load_config(args.config)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.exit(2, f"Configuration error: {exc}\n")
    logging.info("Configuration valid: %s", config.project_name)
    if args.command is None:
        logging.info("Planned horizon: %s days; no data required", config.forecast_horizon_days)
        return
    if args.command in ("forecast-plan", "forecast-models", "experiment-status"):
        import json
        from dataclasses import asdict

        from intelligent_demand.evaluation.splits import load_splits
        from intelligent_demand.experiments.config import load_experiment_config
        from intelligent_demand.experiments.registry import ExperimentRegistry
        from intelligent_demand.models.catalog import registered_models

        try:
            settings = load_experiment_config(args.settings)
            if args.command == "forecast-plan":
                folds = load_splits(settings.split_manifest)
                output = {
                    "status": "validated_plan_only",
                    "models_executed": 0,
                    "settings": settings.metadata(),
                    "validation_folds": {
                        name: [asdict(fold) for fold in rows] for name, rows in folds.items()
                    },
                }
            elif args.command == "forecast-models":
                output = {
                    "registered_models": registered_models(),
                    "models_executed": 0,
                }
            else:
                registry = ExperimentRegistry(settings.registry_directory)
                output = registry.read(args.run_id)
                if output["status"] == "completed":
                    output = registry.completed(args.run_id)
            print(json.dumps(output, default=str, indent=2, allow_nan=False))
        except (OSError, ValueError, yaml.YAMLError) as exc:
            parser.exit(2, f"Forecast infrastructure validation failed: {exc}\n")
        return
    if args.command == "eda":
        from intelligent_demand.exploration.pipeline import run_eda

        result = run_eda(config, args.dataset, args.settings)
        logging.info("Phase 2 EDA status: %s; no forecasting models trained", result["status"])
        return
    results = {}
    report = config.paths["reports"] / "data_quality" / f"{args.command}.json"
    if args.command == "profile-data":
        for spec in select_datasets(args.dataset):
            results[spec.name] = {"status": "pending"}
        write_json(report, results)
    client = KaggleCLI()
    authentication_error = None
    if args.command in ("download-data", "check-access"):
        try:
            client.authenticate()
            logging.info("Authenticated read-only Kaggle operation passed")
        except AcquisitionError as exc:
            authentication_error = str(exc)
    for spec in select_datasets(args.dataset):
        try:
            if authentication_error:
                raise AcquisitionError(authentication_error)
            if args.command == "check-access":
                results[spec.name] = {
                    "status": "listing_accessible",
                    "files": client.files(spec),
                    "note": "Download entitlement is enforced separately by Kaggle.",
                }
            elif args.command == "download-data":
                results[spec.name] = download_dataset(
                    spec,
                    config.paths["raw"],
                    client,
                    args.force,
                )
            elif args.command == "audit-store-item":
                from intelligent_demand.validation.store_item_audit import audit_store_item

                results[spec.name] = audit_store_item(config)
                logging.info("Store Item independent audit: %s", results[spec.name]["status"])
            elif args.command == "profile-data":
                from intelligent_demand.validation.pipeline import profile_dataset

                results[spec.name] = profile_dataset(spec, config)
            else:
                results[spec.name] = file_inventory(config.paths["raw"] / spec.name, spec)
                logging.info(
                    "%s: ready_for_profiling=%s",
                    spec.name,
                    results[spec.name]["ready_for_profiling"],
                )
        except (AcquisitionError, OSError, ValueError) as exc:
            # Only AcquisitionError contains whitelisted, credential-safe client text.
            reason = (
                str(exc) if isinstance(exc, AcquisitionError) else "Local data operation failed."
            )
            logging.error("%s: %s", spec.name, reason)
            results[spec.name] = {"status": "blocked", "reason": reason}
        # Persist completed sources if another source is slow or interrupted later.
        write_json(report, results)
    write_json(report, results)
    logging.info("Status report: %s", report)
    if any(r.get("status") in ("blocked", "invalid") for r in results.values()):
        parser.exit(1)


if __name__ == "__main__":
    main()
