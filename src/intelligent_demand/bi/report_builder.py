"""Build the PBIR report pages from configs/powerbi_report.yaml.

Visuals, bindings, container titles and filters are written by pbi-cli so the PBIR structures are the
tool's own. JSON patches add only what the CLI cannot express: textbox text, slicer behaviour (dropdown,
single-select, default selection, cross-page sync), card display units and matrix subtotals.
Deterministic: each page's visuals and filters are cleared and rebuilt.
Usage:  .venv\\Scripts\\python.exe -m intelligent_demand.bi.report_builder
"""

import json
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "powerbi"
REPORT = PROJECT / "IntelligentDemand.Report" / "definition"
LAYOUT = ROOT / "configs/powerbi_report.yaml"
ROLE_OPTIONS = {
    "field": "--field",
    "category": "--category",
    "value": "--value",
    "legend": "--legend",
    "row": "--row",
    "column": "--column",
    "x": "--x",
    "y": "--y",
    "detail": "--detail",
}


def pbi(*args):
    result = subprocess.run(
        ["pbi", *args], cwd=PROJECT, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pbi {' '.join(args)} failed: {(result.stderr or result.stdout)[-400:]}"
        )
    return result.stdout


def field(reference, measures):
    """'Table.Column' is a column; a bare name is a measure in the measure table."""
    if "." in reference and "[" not in reference:
        table, column = reference.split(".", 1)
        return f"{table}[{column}]"
    return f"{measures}[{reference}]"


def literal(value):
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (int, float)):
        text = f"{value}D"
    else:
        text = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": text}}}


def visual_path(page, name):
    return REPORT / "pages" / page / "visuals" / name / "visual.json"


def patch(page, name, function):
    path = visual_path(page, name)
    data = json.loads(path.read_text(encoding="utf-8"))
    function(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def textbox(page, name, paragraphs):
    def apply(data):
        rendered = []
        for paragraph in paragraphs:
            runs = []
            for text, style in paragraph["runs"]:
                text_style = {
                    "fontSize": f"{style.get('size', 10)}pt",
                    "color": style.get("color", "#14213D"),
                }
                if style.get("bold"):
                    text_style["fontWeight"] = "bold"
                runs.append({"value": text, "textStyle": text_style})
            rendered.append({"textRuns": runs})
        data["visual"].setdefault("objects", {})["general"] = [
            {"properties": {"paragraphs": rendered}}
        ]

    patch(page, name, apply)


def slicer(page, spec):
    table, column = spec["field"].split(".", 1)

    def apply(data):
        objects = data["visual"].setdefault("objects", {})
        objects["data"] = [{"properties": {"mode": literal("Dropdown")}}]
        if spec.get("single"):
            objects["selection"] = [
                {"properties": {"singleSelect": literal(True), "strictSingleSelect": literal(True)}}
            ]
        if spec.get("default"):
            objects["general"] = [
                {
                    "properties": {
                        "filter": {
                            "filter": {
                                "Version": 2,
                                "From": [{"Name": "s", "Entity": table, "Type": 0}],
                                "Where": [
                                    {
                                        "Condition": {
                                            "In": {
                                                "Expressions": [
                                                    {
                                                        "Column": {
                                                            "Expression": {
                                                                "SourceRef": {"Source": "s"}
                                                            },
                                                            "Property": column,
                                                        }
                                                    }
                                                ],
                                                "Values": [
                                                    [
                                                        {
                                                            "Literal": {
                                                                "Value": "'" + spec["default"] + "'"
                                                            }
                                                        }
                                                    ]
                                                ],
                                            }
                                        }
                                    }
                                ],
                            }
                        }
                    }
                }
            ]
        if spec.get("sync"):
            data["visual"]["syncGroup"] = {
                "groupName": spec["sync"],
                "fieldChanges": True,
                "filterChanges": True,
            }

    patch(page, spec["name"], apply)


def card_units(page, name, text_card=False):
    def apply(data):
        properties = {"labelDisplayUnits": literal(1)}
        if text_card:
            properties["fontSize"] = literal(13)
        data["visual"].setdefault("objects", {})["labels"] = [{"properties": properties}]

    patch(page, name, apply)


def display_names(page, name, names):
    """Friendly projection labels; the underlying field reference is unchanged."""

    def apply(data):
        for role in data["visual"].get("query", {}).get("queryState", {}).values():
            for projection in role.get("projections", []):
                if projection["queryRef"] in names:
                    projection["displayName"] = names[projection["queryRef"]]

    patch(page, name, apply)


def matrix_subtotals(page, name):
    def apply(data):
        data["visual"].setdefault("objects", {})["subTotals"] = [
            {"properties": {"rowSubtotals": literal(False), "columnSubtotals": literal(False)}}
        ]

    patch(page, name, apply)


def legend_role(page, name):
    """pbi-cli 3.12 writes the legend projection under a 'Legend' role; Power BI cartesian and scatter
    charts call that role 'Series' and silently ignore unknown roles, leaving the chart empty."""

    def apply(data):
        state = data["visual"]["query"]["queryState"]
        if "Legend" in state:
            state["Series"] = state.pop("Legend")

    patch(page, name, apply)


def reset_page(page, height, width):
    folder = REPORT / "pages" / page
    shutil.rmtree(folder / "visuals", ignore_errors=True)
    meta_path = folder / "page.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.pop("filterConfig", None)
    meta.update(
        height=height, width=width, displayOption="FitToPage" if height == 720 else "FitToWidth"
    )
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def add(page, visual, measures):
    alias = visual["type"]
    pbi(
        "visual",
        "--no-sync",
        "add",
        "--page",
        page,
        "--type",
        alias,
        "--name",
        visual["name"],
        "--x",
        str(visual["x"]),
        "--y",
        str(visual["y"]),
        "--width",
        str(visual["w"]),
        "--height",
        str(visual["h"]),
    )
    if visual.get("bind"):
        args = []
        for role, references in visual["bind"].items():
            for reference in references:
                args += [ROLE_OPTIONS[role], field(reference, measures)]
        pbi("visual", "--no-sync", "bind", visual["name"], "--page", page, *args)
    if visual.get("bind"):
        legend_role(page, visual["name"])
    if visual.get("title"):
        pbi(
            "visual",
            "--no-sync",
            "set-container",
            visual["name"],
            "--page",
            page,
            "--title",
            visual["title"],
        )
    for flt in visual.get("visual_filters", []):
        values = [arg for value in flt["values"] for arg in ("--value", value)]
        pbi(
            "filters",
            "--no-sync",
            "add-categorical",
            "--page",
            page,
            "--table",
            flt["table"],
            "--column",
            flt["column"],
            *values,
            "--visual",
            visual["name"],
        )
    if visual.get("text"):
        textbox(page, visual["name"], visual["text"])
    if visual.get("bind"):
        display_names(page, visual["name"], LABELS)
    if alias == "card":
        card_units(page, visual["name"], any(ref in TEXT_CARDS for ref in visual["bind"]["field"]))
    if alias == "matrix":
        matrix_subtotals(page, visual["name"])


def register_theme(theme):
    """Apply the theme with pbi-cli, then correct its registration to the layout Desktop itself writes.

    pbi-cli 3.12 stores the file in StaticResources/RegisteredResources but records the item path as
    BaseThemes/<file> and the custom theme name as the theme's display name; Desktop resolves
    RegisteredResources items by file name relative to that folder, and fails to load the report otherwise.
    """
    pbi("report", "--no-sync", "set-theme", "--file", theme)
    file_name = Path(theme).name
    if not (REPORT.parent / "StaticResources" / "RegisteredResources" / file_name).is_file():
        raise FileNotFoundError("Theme was not registered as a report resource")
    path = REPORT / "report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["themeCollection"]["customTheme"] = {
        "name": file_name,
        "reportVersionAtImport": "5.55",
        "type": "RegisteredResources",
    }
    for package in report.get("resourcePackages", []):
        if package["type"] == "RegisteredResources":
            # PBIR requires the string resource type; pbi-cli's legacy numeric 202 makes
            # Desktop fail with "Failed to load the report" (found by bisection, 2026-11-10).
            package["items"] = [{"name": file_name, "path": file_name, "type": "CustomTheme"}]
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


LABELS, TEXT_CARDS = {}, set()


def build():
    layout = yaml.safe_load(LAYOUT.read_text(encoding="utf-8"))
    measures = layout["measures"]
    LABELS.update(layout.get("display_names", {}))
    TEXT_CARDS.update(layout.get("text_cards", []))
    register_theme(layout["theme"])
    width = layout["canvas"]["width"]
    total = 0
    for page in layout["pages"]:
        name, height = page["name"], page.get("height", layout["canvas"]["height"])
        reset_page(name, height, width)
        header = [
            {
                "name": "hdr_title",
                "type": "textbox",
                "x": 24,
                "y": 6,
                "w": 740,
                "h": 42,
                "text": [
                    {"runs": [[page["title"], {"bold": True, "size": 18, "color": "#14213D"}]]}
                ],
            },
            {
                "name": "hdr_subtitle",
                "type": "textbox",
                "x": 24,
                "y": 42,
                "w": 740,
                "h": 32,
                "text": [{"runs": [[page["subtitle"], {"size": 9, "color": "#3D4B5C"}]]}],
            },
            {"name": "hdr_nav", "type": "page_navigator", "x": 780, "y": 14, "w": 476, "h": 40},
            # Height matches the owner's Desktop adjustment (about 47 px) while staying inside the canvas.
            {
                "name": "ftr_caveat",
                "type": "textbox",
                "x": 24,
                "y": height - 48,
                "w": 1232,
                "h": 47,
                "text": [
                    {
                        "runs": [
                            ["Scientific caveat: ", {"bold": True, "size": 8, "color": "#C0504D"}],
                            [layout["footer"], {"size": 8, "color": "#3D4B5C"}],
                        ]
                    }
                ],
            },
        ]
        slicers = [
            {**s, "type": "slicer", "bind": {"field": [s["field"]]}}
            for s in page.get("slicers", [])
        ]
        for visual in header + slicers + page["visuals"]:
            add(name, visual, measures)
            total += 1
        for spec in page.get("slicers", []):
            slicer(name, spec)
        for flt in page.get("filters", []):
            values = [arg for value in flt["values"] for arg in ("--value", value)]
            pbi(
                "filters",
                "--no-sync",
                "add-categorical",
                "--page",
                name,
                "--table",
                flt["table"],
                "--column",
                flt["column"],
                *values,
            )
        print(
            f"page {name}: {len(header) + len(slicers) + len(page['visuals'])} visuals", flush=True
        )
    print(f"{total} visuals built")


if __name__ == "__main__":
    build()
