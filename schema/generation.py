"""Generate JSON Schema and Markdown reference artifacts from v1.4 models."""

from __future__ import annotations

import argparse
import json
from functools import cache
from pathlib import Path
from typing import Any

from data_snapshot.metadata_schema.models import DataSnapshotMetadata


_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_JSON_PATH = (
    _ROOT / "docs/schema_v1.4/data_snapshot_metadata_schema_v1.4.schema.json"
)
_DEFAULT_MARKDOWN_PATH = _ROOT / "docs/schema_v1.4/schema_reference_v1.4.md"

_SNAPSHOT_FIELD_MODULES = (
    (
        "Identity and discovery",
        (
            "title",
            "document_label",
            "subject_domains",
            "subject_summary",
            "panel_titles",
        ),
    ),
    ("Subject and semantics", ("variables", "dimensions", "population_group")),
    ("Temporal context", ("temporal_coverage",)),
    ("Spatial context", ("geographic_coverage",)),
    ("Measurement context", ("comparisons",)),
    ("Structural organization", ("visualization_types",)),
    (
        "Provenance and attribution",
        ("provenance", "languages", "interpretive_notes"),
    ),
    (
        "Project and operational context",
        ("project", "intervention_types", "financing"),
    ),
    (
        "Analytical and methodological context",
        ("analysis_methods", "data_collection_methods"),
    ),
)

_EXAMPLE_GUIDANCE = (
    "Each block is one possible field value. Examples for different fields are "
    "independent and should not be combined into a record automatically. They "
    "illustrate the schema and do not constrain accepted values. URIs under "
    "example.org are illustrative placeholders."
)

_STANDARDS_RELATIONSHIPS = (
    (
        "exact",
        "The standard term has the same essential meaning and intended use as "
        "the local field.",
    ),
    (
        "close",
        "The meanings substantially overlap, with a bounded difference in scope "
        "or application.",
    ),
    (
        "standard_broader",
        "The standard term covers the local field plus other meanings.",
    ),
    (
        "standard_narrower",
        "The standard term covers only part of the local field.",
    ),
    (
        "related_structural",
        "The standard offers a useful relationship or modeling pattern but is "
        "not a semantic equivalent.",
    ),
)


@cache
def _metadata_schema() -> dict[str, Any]:
    return DataSnapshotMetadata.model_json_schema(mode="validation")


@cache
def serialize_metadata_schema() -> str:
    """Serialize the canonical metadata schema once per process.

    Returns
    -------
    str
        Compact JSON suitable for repeated use as model input context.
    """
    return json.dumps(_metadata_schema(), ensure_ascii=False, separators=(",", ":"))


def render_json_schema() -> str:
    """Render the canonical model's JSON Schema deterministically.

    Returns
    -------
    str
        Pretty-printed JSON Schema with one trailing newline.
    """
    schema = _metadata_schema()
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def render_markdown_reference() -> str:
    """Render a human-readable schema reference from generated JSON Schema.

    Returns
    -------
    str
        Markdown reference with one trailing newline.
    """
    schema = _metadata_schema()
    lines = [
        "# Data Snapshot Metadata Schema v1.4 Reference",
        "",
        "<!-- Generated from DataSnapshotMetadata. Do not edit manually. -->",
        "",
        _summary(
            schema.get("description", "Canonical metadata for one data snapshot.")
        ),
        "",
        f"Schema version: `{schema['x-schema-version']}`",
        "",
        "## Validation and serialization",
        "",
        *[f"- {rule}" for rule in schema.get("x-validation-rules", [])],
        "",
        "## Standards relationship labels",
        "",
        (
            "The `Standards / code list` entries use the following labels to "
            "describe reviewed semantic alignments. These labels do not assert "
            "validation or automatic conversion behavior."
        ),
        "",
        "| Label | Meaning |",
        "|---|---|",
        *[f"| `{label}` | {meaning} |" for label, meaning in _STANDARDS_RELATIONSHIPS],
        "",
        "## Snapshot fields",
        "",
        "Fields are grouped by the v1.4 semantic modules.",
        "",
        _EXAMPLE_GUIDANCE,
    ]
    properties = schema.get("properties", {})
    grouped_fields = [
        field_name
        for _, field_names in _SNAPSHOT_FIELD_MODULES
        for field_name in field_names
    ]
    if len(grouped_fields) != len(set(grouped_fields)) or set(grouped_fields) != set(
        properties
    ):
        raise ValueError("Snapshot field modules must contain every root field once.")
    required = set(schema.get("required", []))
    for module_name, field_names in _SNAPSHOT_FIELD_MODULES:
        module_schema = {
            "properties": {name: properties[name] for name in field_names},
            "required": [name for name in field_names if name in required],
        }
        lines.extend(["", f"### {module_name}", ""])
        lines.extend(_object_table(module_schema, detail_heading_level=4))

    lines.extend(["", "## Referenced Types", "", _EXAMPLE_GUIDANCE])
    for name, definition in schema.get("$defs", {}).items():
        lines.extend(["", f"### {name}", ""])
        description = definition.get("description")
        if description:
            lines.extend([_summary(description), ""])
        for rule in definition.get("x-validation-rules", []):
            lines.extend([f"- {rule}", ""])
        if "enum" in definition:
            lines.append(", ".join(f"`{value}`" for value in definition["enum"]))
        elif definition.get("type") == "object":
            lines.extend(_object_table(definition, detail_heading_level=4))
        else:
            lines.append(f"Type: `{_type_label(definition)}`")
    return "\n".join(lines).rstrip() + "\n"


def write_schema_artifacts(
    json_path: str | Path = _DEFAULT_JSON_PATH,
    markdown_path: str | Path = _DEFAULT_MARKDOWN_PATH,
) -> None:
    """Write both schema artifacts derived from the canonical model.

    Parameters
    ----------
    json_path : str | Path, optional
        Destination for the generated JSON Schema.
    markdown_path : str | Path, optional
        Destination for the generated Markdown reference.
    """
    json_output = Path(json_path)
    markdown_output = Path(markdown_path)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(render_json_schema(), encoding="utf-8")
    markdown_output.write_text(render_markdown_reference(), encoding="utf-8")


def _object_table(schema: dict[str, Any], detail_heading_level: int = 3) -> list[str]:
    required = set(schema.get("required", []))
    lines = [
        "| Field | Type | Required | Default | Constraints | Standards / code list |",
        "|---|---|---:|---|---|---|",
    ]
    for name, field_schema in schema.get("properties", {}).items():
        standards = [
            f"[{mapping['term']}]({mapping['term']}) ({mapping['relationship']})"
            for mapping in field_schema.get("x-standards", [])
        ]
        code_list = field_schema.get("x-code-list")
        if code_list:
            release = code_list.get("release", "not pinned; syntax only")
            standards.append(
                f"[{code_list['authority']} {code_list['identifier']}]"
                f"({code_list['uri']}); release: {release}"
            )
        constraints = []
        for option in [field_schema, *field_schema.get("anyOf", [])]:
            for key in (
                "minItems",
                "maxItems",
                "minLength",
                "maxLength",
                "pattern",
                "format",
            ):
                if key in option:
                    constraints.append(f"{key}: {option[key]}")
        default = (
            f"`{json.dumps(field_schema['default'], ensure_ascii=False)}`"
            if "default" in field_schema
            else "—"
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{name}`",
                    _cell(f"`{_type_label(field_schema)}`"),
                    "yes" if name in required else "no",
                    default,
                    _cell("; ".join(constraints)),
                    "<br>".join(standards),
                )
            )
            + " |"
        )
    fields = schema.get("properties", {})
    if fields:
        lines.extend(
            [
                "",
                f"{'#' * detail_heading_level} Field definitions and examples",
            ]
        )
        for name, field_schema in fields.items():
            lines.extend(["", f"{'#' * (detail_heading_level + 1)} `{name}`", ""])
            if field_schema.get("description"):
                lines.extend(["**Definition**", "", field_schema["description"], ""])
            if field_schema.get("examples"):
                lines.extend(["**Examples**", ""])
            for example in field_schema.get("examples", []):
                lines.extend(
                    [
                        "```json",
                        json.dumps(example, ensure_ascii=False, indent=2),
                        "```",
                        "",
                    ]
                )
    return lines


def _type_label(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    if "enum" in schema:
        return "enum"
    if "anyOf" in schema:
        labels = [
            _type_label(option)
            for option in schema["anyOf"]
            if option.get("type") != "null"
        ]
        return " | ".join(labels) + " | null"
    if schema.get("type") == "array":
        return f"array[{_type_label(schema.get('items', {}))}]"
    return schema.get("format", schema.get("type", "unknown"))


def _cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def _summary(value: str) -> str:
    return value.strip().split("\n\n", 1)[0]


def main() -> None:
    """Generate artifacts or verify that checked-in artifacts are current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when generated artifacts differ from checked-in files.",
    )
    args = parser.parse_args()
    if args.check:
        expected = {
            _DEFAULT_JSON_PATH: render_json_schema(),
            _DEFAULT_MARKDOWN_PATH: render_markdown_reference(),
        }
        stale = [
            str(path.relative_to(_ROOT))
            for path, content in expected.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.error(f"stale generated artifacts: {', '.join(stale)}")
        return
    write_schema_artifacts()


if __name__ == "__main__":
    main()
