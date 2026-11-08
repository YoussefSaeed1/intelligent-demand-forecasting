"""Report-only label reflow after visual QA; no training or target-reading operations.

The immutable scientific package/code snapshot remains unchanged. Run after the
frozen report generator when reproducing the final presentation.
"""

import json
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from intelligent_demand.experiments.registry import atomic_json, file_digest, utc_now
from intelligent_demand.reporting.phase4_report import FIGURES, MODEL_COLORS, verify_report
from intelligent_demand.tuning.authority import verify_frozen
from intelligent_demand.tuning.plan import OUTPUT, REPORTS


def main():
    frozen = verify_frozen()
    evaluation = json.loads((OUTPUT / "final_evaluation.json").read_text())
    rows = []
    sources = {}
    for record in evaluation["results"]:
        path = OUTPUT / record["metrics"]["path"]
        if file_digest(path) != record["metrics"]["sha256"]:
            raise ValueError("Saved final metrics changed")
        sources[path.relative_to(OUTPUT).as_posix()] = file_digest(path)
        groups = json.loads(path.read_text())["by_demand_class"]
        rows.append((record, groups))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    figure, axes = plt.subplots(1, 2, figsize=(14, 5.5), layout="constrained")
    for axis, dataset in zip(axes, ("store_item", "m5"), strict=True):
        selected = [(r, g) for r, g in rows if r["dataset"] == dataset]
        patterns = sorted(selected[0][1])
        width = 0.8 / len(selected)
        for number, (record, groups) in enumerate(selected):
            axis.bar(
                [i + (number - (len(selected) - 1) / 2) * width for i in range(len(patterns))],
                [groups[p]["macro"]["mae"] for p in patterns],
                width,
                label=record["model"],
                color=MODEL_COLORS[record["model"]],
            )
        labels = [
            textwrap.fill(p.replace("_", " "), width=14)
            + f"\n(n={selected[0][1][p]['coverage']['series']:,})"
            for p in patterns
        ]
        axis.set(
            title=dataset,
            ylabel="Final macro MAE (units)",
            xticks=range(len(patterns)),
            xticklabels=labels,
        )
        axis.tick_params(axis="x", labelsize=9)
        axis.spines[["top", "right"]].set_visible(False)
        axis.legend(fontsize=8)
    validation_path = REPORTS / "phase4_report_validation.json"
    validation = json.loads(validation_path.read_text())
    changes = []
    for extension in ("png", "svg"):
        path = FIGURES / f"final_demand_patterns.{extension}"
        previous = file_digest(path)
        figure.savefig(path, dpi=165, bbox_inches="tight", facecolor="white")
        relative = path.relative_to(REPORTS.parent).as_posix()
        item = next(r for r in validation["figures"] if r["path"] == relative)
        item["sha256"] = file_digest(path)
        changes.append(
            {"path": relative, "previous_sha256": previous, "corrected_sha256": item["sha256"]}
        )
    plt.close(figure)
    receipt_path = REPORTS / "phase4_visual_adjustments.json"
    history = json.loads(receipt_path.read_text()) if receipt_path.exists() else {"events": []}
    history["events"].append(
        {
            "timestamp_utc": utc_now(),
            "scope": (
                "Wrap long demand-class tick labels; "
                "unchanged values, bars, groups and metrics"
            ),
            "selection_sha256": frozen["manifest_sha256"],
            "input_metric_sha256": sources,
            "helper_sha256": file_digest(__file__),
            "files": changes,
        }
    )
    atomic_json(receipt_path, history)
    verification = verify_report(REPORTS / "PHASE4_FORECASTING_REPORT.html", validation["figures"])
    validation.update(verification)
    validation["presentation_correction_receipt"] = receipt_path.name
    atomic_json(validation_path, validation)
    print(json.dumps({"status": "passed", "changed_figures": 1, **verification}, indent=2))


if __name__ == "__main__":
    main()
