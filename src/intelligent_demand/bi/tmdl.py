"""Generate the TMDL semantic model from configs/powerbi_model.yaml and the reporting-data manifest.

Deterministic: lineage tags are UUID5 values of object names, so rebuilding yields identical files.
Usage:  .venv\\Scripts\\python.exe -m intelligent_demand.bi.tmdl [--data-root PATH]
"""

import argparse
import json
import uuid
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "configs/powerbi_model.yaml"
MANIFEST = ROOT / "reports/powerbi/data_manifest.json"
PROJECT = ROOT / "powerbi"
NAMESPACE = uuid.UUID("6f1c2d3e-4b5a-4c6d-8e7f-901a2b3c4d5e")
TYPES = {
    "string": ("string", "type text"),
    "int64": ("int64", "Int64.Type"),
    "double": ("double", "type number"),
    "dateTime": ("dateTime", "type date"),
}


def tag(*parts):
    return str(uuid.uuid5(NAMESPACE, "/".join(parts)))


def quote(name):
    return "'" + name.replace("'", "''") + "'"


def column_types(spec, path):
    frame = pd.read_csv(path, nrows=2000, low_memory=False)
    result = {}
    for name, dtype in frame.dtypes.items():
        if name in spec["date_columns"]:
            result[name] = "dateTime"
        elif pd.api.types.is_integer_dtype(dtype):
            result[name] = "int64"
        elif pd.api.types.is_float_dtype(dtype):
            result[name] = "double"
        else:
            result[name] = "string"
    return result


def table_tmdl(spec, name, entry):
    meta = spec["tables"][name]
    types = column_types(spec, ROOT / entry["file"])
    if list(types) != entry["columns"]:
        raise ValueError(f"Column order differs from manifest: {name}")
    rename = meta.get("rename", {})
    hidden = set(meta.get("hidden", []))
    lines = [f"/// {meta['description']}", f"table {name}", f"\tlineageTag: {tag('table', name)}"]
    if name == spec["date_table"]:
        lines.append("\tdataCategory: Time")
    lines.append("")
    for source, kind in types.items():
        column = rename.get(source, source)
        lines += [f"\tcolumn {quote(column)}", f"\t\tdataType: {TYPES[kind][0]}"]
        if meta.get("hide_all") or source in hidden:
            lines.append("\t\tisHidden")
        if name == spec["date_table"] and source == "Date":
            lines.append("\t\tisKey")
        if kind == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd")
        elif source in meta.get("formats", {}):
            lines.append(f"\t\tformatString: {meta['formats'][source]}")
        elif kind == "int64":
            lines.append("\t\tformatString: 0")
        lines += [
            f"\t\tlineageTag: {tag('column', name, column)}",
            "\t\tsummarizeBy: none",
            f"\t\tsourceColumn: {source}",
        ]
        if source in meta.get("sort_by", {}):
            lines.append(f"\t\tsortByColumn: {quote(meta['sort_by'][source])}")
        lines += ["", "\t\tannotation SummarizationSetBy = User", ""]
    schema = ", ".join(f'{{"{c}", {TYPES[k][1]}}}' for c, k in types.items())
    lines += [
        f"\tpartition {name} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        f'\t\t\t\t    Source = LoadReportingTable("{name}", {{{schema}}})',
        "\t\t\t\tin",
        "\t\t\t\t    Source",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(lines)


def measures_tmdl(spec):
    lines = [
        "/// Reusable DAX measures. Hypothetical inventory values are normalised cost units (NCU).",
        "table _Measures",
        f"\tlineageTag: {tag('table', '_Measures')}",
        "",
    ]
    for measure in spec["measures"]:
        expression = measure["expression"].strip()
        lines.append(f"\t/// {measure['description']}")
        if "\n" in expression:
            lines.append(f"\tmeasure {quote(measure['name'])} =")
            lines += [f"\t\t\t{line}" for line in expression.splitlines()]
        else:
            lines.append(f"\tmeasure {quote(measure['name'])} = {expression}")
        if measure.get("format"):
            lines.append(f"\t\tformatString: {measure['format']}")
        if measure.get("hidden"):
            lines.append("\t\tisHidden")
        lines += [
            f"\t\tdisplayFolder: {measure['folder']}",
            f"\t\tlineageTag: {tag('measure', measure['name'])}",
            "",
        ]
    lines += [
        "\tcolumn Placeholder",
        "\t\tdataType: string",
        "\t\tisHidden",
        f"\t\tlineageTag: {tag('column', '_Measures', 'Placeholder')}",
        "\t\tsummarizeBy: none",
        "\t\tsourceColumn: Placeholder",
        "",
        "\t\tannotation SummarizationSetBy = Automatic",
        "",
        "\tpartition _Measures = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        "\t\t\t\t    Source = #table(type table [Placeholder = text], {})",
        "\t\t\t\tin",
        "\t\t\t\t    Source",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(lines)


def expressions_tmdl(data_root):
    root = data_root.rstrip("\\/") + "\\"
    return "\n".join(
        [
            "/// Folder holding the Phase 6 reporting CSVs. Change this one value after moving the project.",
            f'expression DataRoot = "{root}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
            f"\tlineageTag: {tag('expression', 'DataRoot')}",
            "",
            "\tannotation PBI_ResultType = Text",
            "",
            "/// Loads one reporting CSV with an explicit schema: early projection, empty text to null, typed with en-US.",
            "expression LoadReportingTable =",
            "\t\t(tableName as text, schema as list) as table =>",
            "\t\tlet",
            '\t\t    Source = Csv.Document(File.Contents(DataRoot & tableName & ".csv"), '
            '[Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
            "\t\t    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
            "\t\t    Projected = Table.SelectColumns(Promoted, List.Transform(schema, each _{0}), MissingField.Error),",
            '\t\t    Nulls = Table.TransformColumns(Projected, {}, each if _ = "" then null else _),',
            '\t\t    Typed = Table.TransformColumnTypes(Nulls, schema, "en-US")',
            "\t\tin",
            "\t\t    Typed",
            f"\tlineageTag: {tag('expression', 'LoadReportingTable')}",
            "",
            "\tannotation PBI_ResultType = Function",
            "",
        ]
    )


def relationships_tmdl(spec):
    lines = []
    for fact, fact_column, dim, dim_column in spec["relationships"]:
        lines += [
            f"relationship {tag('relationship', fact, fact_column, dim)}",
            f"\tfromColumn: {fact}.{fact_column}",
            f"\ttoColumn: {dim}.{dim_column}",
            "",
        ]
    return "\n".join(lines)


def build(data_root):
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    model = PROJECT / f"{spec['model_name']}.SemanticModel"
    definition = model / "definition"
    (definition / "tables").mkdir(parents=True, exist_ok=True)
    for stale in (definition / "tables").glob("*.tmdl"):
        stale.unlink()
    write = lambda path, text: path.write_text(text, encoding="utf-8", newline="\n")  # noqa: E731
    write(
        model / ".platform",
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                "metadata": {"type": "SemanticModel", "displayName": spec["model_name"]},
                "config": {"version": "2.0", "logicalId": tag("logical", "semanticmodel")},
            },
            indent=2,
        )
        + "\n",
    )
    write(
        model / "definition.pbism", json.dumps({"version": "4.2", "settings": {}}, indent=2) + "\n"
    )
    write(
        definition / "database.tmdl",
        f"database\n\tcompatibilityLevel: {spec['compatibility_level']}\n",
    )
    names = list(spec["tables"]) + ["_Measures"]
    write(
        definition / "model.tmdl",
        "\n".join(
            [
                "model Model",
                f"\tculture: {spec['culture']}",
                "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
                f"\tsourceQueryCulture: {spec['culture']}",
                "\tdataAccessOptions",
                "\t\tlegacyRedirects",
                "\t\treturnErrorValuesAsNull",
                "",
                "annotation __PBI_TimeIntelligenceEnabled = 0",
                "",
            ]
            + [f"ref table {n}" for n in names]
            + [""]
        ),
    )
    write(definition / "expressions.tmdl", expressions_tmdl(data_root))
    for name in spec["tables"]:
        write(
            definition / "tables" / f"{name}.tmdl", table_tmdl(spec, name, manifest["tables"][name])
        )
    write(definition / "tables" / "_Measures.tmdl", measures_tmdl(spec))
    write(definition / "relationships.tmdl", relationships_tmdl(spec))
    print(
        f"TMDL written: {len(names)} tables, {len(spec['measures'])} measures, "
        f"{len(spec['relationships'])} relationships -> {model.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=str(ROOT / "artifacts" / "powerbi" / "data"))
    build(parser.parse_args().data_root)
