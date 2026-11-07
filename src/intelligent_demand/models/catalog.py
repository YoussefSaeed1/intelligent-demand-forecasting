"""Read-only catalogue; importing and listing models never fits an estimator."""

from intelligent_demand.models.baselines import baseline_registry
from intelligent_demand.models.global_ml import ml_registry
from intelligent_demand.models.statistical import statistical_registry


def registered_models():
    entries = [
        entry
        for registry in (baseline_registry(), statistical_registry(), ml_registry())
        for entry in registry.registered()
    ]
    return sorted(entries, key=lambda entry: (entry["identifier"], entry["version"]))
