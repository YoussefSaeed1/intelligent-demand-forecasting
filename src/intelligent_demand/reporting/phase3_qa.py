"""Final local report, figure, metric-table and Git-scope quality checks."""

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from intelligent_demand.experiments.benchmark import OUTPUT, ROOT, verify_sources
from intelligent_demand.experiments.config import load_experiment_config
from intelligent_demand.experiments.gates import require_gate
from intelligent_demand.experiments.registry import ExperimentRegistry, atomic_json, file_digest


class LocalReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets, self.ids, self.headings = [], set(), 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "h2":
            self.headings += 1
        if "id" in values:
            if values["id"] in self.ids:
                raise ValueError("Duplicated HTML navigation anchor")
            self.ids.add(values["id"])
        for key in ("src", "href"):
            if key in values:
                self.targets.append(values[key])
        if tag in ("script", "iframe"):
            raise ValueError("Offline report must not require executable/external resources")


def final_qa(output=None):
    gate = require_gate("3e")
    manifest = json.loads((OUTPUT / "3e_report_manifest.json").read_text())
    if manifest["gate_sha256"] != file_digest(ROOT / "reports/forecasting/phase3e_gate.json"):
        raise ValueError("Report was not generated from the current final gate")
    table = pd.read_parquet(OUTPUT / "3e_model_summary.parquet")
    for (dataset, scope, model), group in table.groupby(["dataset", "scope", "model"]):
        if len(group) != 1:
            raise ValueError("Duplicate model-summary key")
        rows = [
            r
            for r in gate["runs"]
            if (r["dataset"], r["scope"], r["model"]) == (dataset, scope, model)
        ]
        if len(rows) != 4 or {r["fold"] for r in rows} != {1, 2, 3, 4}:
            raise ValueError("Report comparison has incomplete origins")
        n = sum(r["coverage"]["observations"] for r in rows)
        actual = sum(r["totals"]["actual"] for r in rows)
        absolute = sum(r["totals"]["absolute_error"] for r in rows)
        expected = {
            "macro_mae": np.mean([r["macro"]["mae"] for r in rows]),
            "pooled_rmse": np.sqrt(sum(r["totals"]["squared_error"] for r in rows) / n),
            "pooled_wape_percent": 100 * absolute / actual if actual else np.nan,
            "bias_units": sum(r["totals"]["error"] for r in rows) / n,
            "observations": n,
        }
        for metric, value in expected.items():
            if not np.isclose(group.iloc[0][metric], value, rtol=1e-10, atol=1e-10, equal_nan=True):
                raise ValueError(f"Final summary table fails independent aggregation: {metric}")
    figure_dir = ROOT / "reports/figures/phase3"
    images, figure_checks = [], []
    for path in sorted(figure_dir.glob("*.png")):
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if min(image.size) < 500:
                raise ValueError("Insufficient scientific figure resolution")
            thumb = image.convert("RGB")
            thumb.thumbnail((700, 520))
            images.append((path.name, thumb.copy()))
        svg = path.with_suffix(".svg")
        parsed = ET.parse(svg)
        if not parsed.getroot().tag.endswith("svg"):
            raise ValueError("Invalid SVG figure")
        figure_checks.append(
            {
                "png": path.relative_to(ROOT).as_posix(),
                "png_sha256": file_digest(path),
                "svg_sha256": file_digest(svg),
                "decode_and_parse": "passed",
            }
        )
    sheet = Image.new("RGB", (1440, 560 * ((len(images) + 1) // 2)), "#e7edf3")
    draw = ImageDraw.Draw(sheet)
    for number, (name, image) in enumerate(images):
        x, y = (number % 2) * 720, (number // 2) * 560
        draw.text((x + 10, y + 8), name, fill="black")
        sheet.paste(image, (x + 10, y + 32))
    sheet.save(OUTPUT / "3e_visual_contact_sheet.png")
    report = ROOT / "reports/forecasting/PHASE3_BENCHMARK_REPORT.html"
    parser = LocalReportParser()
    parser.feed(report.read_text(encoding="utf-8"))
    for target in parser.targets:
        url = urlsplit(target)
        if url.scheme or url.netloc:
            raise ValueError("Offline report contains an external URL/resource")
        if url.path:
            resolved = (report.parent / unquote(url.path)).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.is_file():
                raise ValueError(f"Broken local report link: {target}")
        elif url.fragment and url.fragment not in parser.ids:
            raise ValueError("Broken HTML navigation anchor")
    if parser.headings < 10:
        raise ValueError("Report sections are incomplete")
    git = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT)]
    head = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
    staged = subprocess.check_output(git + ["diff", "--cached", "--name-only"], text=True).strip()
    subprocess.run(git + ["diff", "--check"], capture_output=True, check=True)
    # Later authorised checkpoints must remain valid regeneration environments.
    base = "23c1ddeaca0cf6cced2bdf161904f8fb114d4646"
    subprocess.run(git + ["merge-base", "--is-ancestor", base, head], check=True)
    subprocess.run(
        git
        + [
            "diff",
            "--exit-code",
            base,
            "--",
            "docs/FORECASTING_EXPERIMENTAL_PROTOCOL.md",
            "reports/eda/proposed_splits.json",
        ],
        capture_output=True,
        check=True,
    )
    if staged:
        raise ValueError("Report QA requires a clean index; review staged changes separately")
    sources = verify_sources()
    registry = ExperimentRegistry(
        load_experiment_config(ROOT / "configs/forecasting.yaml").registry_directory
    )
    inventory = {}
    for path in registry.root.glob("*/status.json"):
        saved = json.loads(path.read_text())
        inventory[saved["status"]] = inventory.get(saved["status"], 0) + 1
        if saved["status"] == "completed":
            registry.completed(saved["run_id"])
    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "intelligent_demand",
            "experiment-status",
            "--run-id",
            gate["runs"][0]["run_id"],
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    if json.loads(cli.stdout)["status"] != "completed":
        raise ValueError("Completed-run CLI smoke failed")
    result = {
        "status": "passed",
        "summary_rows_reconciled": len(table),
        "html_relative_links_checked": len(parser.targets),
        "html_sections": parser.headings,
        "figures": figure_checks,
        "source_files_unchanged": len(sources),
        "git_head": head,
        "phase3a_ancestor_verified": base,
        "staged_files": 0,
        "final_holdout_targets_accessed": False,
        "visual_human_review": "pending agent inspection of generated images",
        "registry_status_inventory": inventory,
        "completed_run_status_cli": "passed",
    }
    destination = (
        ROOT / "reports/forecasting/phase3_final_qa.json" if output is None else Path(output)
    )
    destination = destination.resolve()
    if not destination.is_relative_to(ROOT):
        raise ValueError("QA output must stay inside this project")
    destination.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(destination, result)
    print(json.dumps({key: value for key, value in result.items() if key != "figures"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional project-local QA evidence path")
    final_qa(parser.parse_args().output)
