# Data Snapshot Metadata Schema v1.4

Pydantic models for the semantic metadata of a data snapshot: a table, chart,
map, dashboard, or composite figure extracted from a document.

`DataSnapshotMetadata` is the canonical Python representation. It preserves
the approved 35 metadata concepts through 20 optional top-level fields and
nested value models. JSON Schema and the human-readable field reference are
generated from these models.

Field examples are stored in Pydantic `Field(examples=...)` metadata and included
in both generated representations. They illustrate individual values and nested
structures; they are neither defaults nor restrictions on accepted values.

## Package structure

```text
metadata_schema/
├── __init__.py       # Public models and enums
├── models.py         # Field definitions, validation, and standards metadata
├── generation.py     # Cached schema serialization and artifact generation
└── README.md         # Python usage
```

## Installation

Install the repository's core package. The project supports Python 3.10 and
declares Pydantic `>=2.13.5,<3` as a core dependency. Model construction and
validation run locally and require no API key.

From the repository root, in a **WSL terminal or PowerShell**:

```shell
uv sync --locked
```

## Creating metadata

Import models from `data_snapshot.metadata_schema`. Nested values can be
constructed as model instances or supplied as dictionaries.

```python
from data_snapshot.metadata_schema import (
    Currency,
    DataSnapshotMetadata,
    Unit,
    Variable,
)

metadata = DataSnapshotMetadata(
    title="Project financing",
    document_label="Table 3",
    variables=[
        Variable(
            name="Project cost",
            unit=Unit(source_text="US$ million", multiplier_exponent=6),
            currency=Currency(source_text="US$", code="USD"),
            statistical_forms=[{"normalized_value": "sum"}],
        )
    ],
    geographic_coverage={"scope": {"name": "Niger", "iso3_code": "NER"}},
    financing={"funders": [{"name": "International Development Association"}]},
)

print(metadata.variables[0].currency.code)  # USD
```

Variables own their units, currencies, analytical roles, axis roles, multi-axis
assignments, and statistical forms. Populate a variable name whenever the
measured concept is identifiable. An unnamed variable may retain a visible
unit, currency, or statistical form, but it cannot contain a role or multi-axis
assignment.
Never use `%`, `Value`, `Unknown`, or another placeholder as a variable name.
Repeat a qualifier that applies to multiple variables on each applicable
variable.

Use `analytical_roles` for supported roles in a statistical analysis:
`outcome`, `predictor`, `control`, and `instrumental`. Use `axis_roles` for an
ordinary x- or y-axis in a figure. Use `multi_axis_assignments` only when the
side or outward position must distinguish multiple axes of the same dimension.

Dimensions own categories and optional single-level category groups. Use a
dimension for characteristics that classify or organize observations, such as
year, country, or sector; use a variable for the quantity being measured. For
table presentation, `row` means categories vary downward and `column` means
they vary horizontally. An unnamed dimension is valid when it contains
categories or category groups; a presentation role alone is insufficient.
Provenance separates derivation sources from credited agents, and a credited
agent does not require an explicit role.

Within `geographic_coverage`, `locations[].type` describes what a named location
is, such as a school or district. `level` describes the administrative or
spatial level at which the snapshot's data are reported. Both may be present
when the snapshot supports both meanings. `iso3_code` stores an ISO 3166-1
alpha-3 country code such as `PHL`; World Bank aggregate and region codes do not
belong in that field.

Parent-document metadata is managed separately; `source_document_title` is not
a v1.4 field. The models represent metadata, not extracted numerical observations.

## Developer notes

- `visualization_types`: record `composite_figure` and the identifiable
  component types for a composite artifact. Schema v1.4 does not encode which
  component belongs to which panel or the panel count.

## Validating input

Use `model_validate()` for a Python dictionary and `model_validate_json()` for
a JSON string or bytes. Invalid input raises `pydantic.ValidationError`.

```python
from pydantic import ValidationError

from data_snapshot.metadata_schema import DataSnapshotMetadata

metadata = DataSnapshotMetadata.model_validate({"title": "Population by region"})
restored = DataSnapshotMetadata.model_validate_json('{"title":"Population by region"}')

try:
    DataSnapshotMetadata.model_validate({"panel_titles": []})
except ValidationError as error:
    print(error.errors())
```

- All root fields are optional. An empty root `{}` is valid.
- Missing values and explicit `null` both become `None`.
- Supplied collections must be nonempty; nested objects must satisfy their
  required fields or populated-content rules. A place may be identified by a
  name, source text, authoritative code, or identifier.
- Unknown properties and blank text are rejected.
- Source text receives Unicode NFC normalization and outer whitespace trimming.
  Exact collection duplicates are removed while preserving first-occurrence order.
- Codes, language tags, URIs, and temporal expressions have deterministic
  syntax or relationship checks. External registry membership and whether a
  value is supported by the source snapshot remain outside model validation.

Validation applies when constructing or parsing records. Revalidate modified
data before treating it as canonical; assignment and in-place collection edits
do not automatically rerun all validators.

## Semantic text, coded terms, and normalized terms

Fields without an approved normalization vocabulary store their semantic values
directly as strings. This includes subject domains, population groups,
intervention types, financing measures, analysis methods, and geographic roles.

Use `CodedTerm` when a value can carry an exact external code or authoritative
URI. Its `source_text` is the exact text or symbol visible in the snapshot that
explicitly expresses the represented value. Omit `source_text` when the value is
inferred from visual form, structure, or context rather than transcribed. A
`code` and `scheme` must be supplied together.

The four specialized normalized-term models constrain `normalized_value` to an
approved enum: `StatisticalFormTerm`, `VisualizationTypeTerm`,
`ReportingIntervalTerm`, and `GeographicLevelTerm`. They accept either an
explicit source label, a normalized value inferred from the snapshot, or both.
For visualization types, preserve an explicitly written unfamiliar label as a
source-only term. Return `visualization_types=null` when neither a listed type
nor an explicit unfamiliar label is supported; never force the closest enum
value.

```python
from data_snapshot.metadata_schema import (
    CodedTerm,
    StatisticalFormTerm,
    StatisticalFormValue,
)

coded_instrument = CodedTerm(
    source_text="Grant",
    code="110",
    scheme="IATI Finance Type",
)
known_form = StatisticalFormTerm(
    source_text="Mean",
    normalized_value=StatisticalFormValue.ARITHMETIC_MEAN,
)
unfamiliar_form = StatisticalFormTerm(source_text="Winsorized mean")
```

Preserve displayed wording when adding normalized values. Pydantic validates the
structure and membership in local enum vocabularies; it does not infer mappings.

## External registry validation

Schema v1.4 validates the syntax and relationships of external codes and tags,
but it does not perform registry membership checks or offline normalization. A
well-formed but unassigned value can therefore pass Pydantic validation. The
planned deterministic normalization stage remains downstream work; it is not
part of the v1.4 schema contract. The affected fields and candidate
machine-readable sources are recorded in the
[v1.3 change report](../../../docs/schema_v1.3/schema_v1.3_change_report.md#13-align-standards-claims-with-actual-validation-strength).

Identifier `value` data may come from the snapshot or trusted metadata.
`scheme`, `issuer`, and `uri` may additionally come from configured and verified
enrichment. The extractor must not infer or manufacture any of these values
from an identifier's apparent pattern or from model knowledge. Add an
authoritative URI only when the source or enrichment process supplies and
verifies it.

## Serializing records

Use `exclude_none=True` to omit unavailable values. Use `mode="json"` when a
dictionary must contain JSON-compatible values, including URL and enum values.

Continuing with a `metadata` instance:

```python
record = metadata.model_dump(mode="json", exclude_none=True)
record_json = metadata.model_dump_json(exclude_none=True, indent=2)
```

These methods serialize one metadata record. They do not generate the schema.

## Generating the schema

Call `model_json_schema()` for a fresh schema dictionary. For repeated use in a
process, use the cached compact serialization helper from `generation`.

```python
from data_snapshot.metadata_schema import DataSnapshotMetadata
from data_snapshot.metadata_schema.generation import serialize_metadata_schema

schema = DataSnapshotMetadata.model_json_schema(mode="validation")
schema_json = serialize_metadata_schema()
```

The helper caches schema generation and serialization in memory; it does not
read the checked-in JSON artifact. Restart a long-running process after model
changes to use a fresh cache.

The exported schema uses JSON Schema Draft 2020-12. Its `x-standards`,
`x-code-list`, and `x-validation-rules` annotations describe mappings,
normalization authorities, and validation rules. Python remains the canonical
validator: the export does not execute normalization, deduplication, or every
Python-only check, such as calendar validity and chronological ordering.

## Generating reference files

Regenerate both versioned artifacts from the models, from the repository root
in a **WSL terminal or PowerShell**:

```shell
uv run --locked python -m data_snapshot.metadata_schema.generation
```

This overwrites the generated files:

- [JSON Schema](../../../docs/schema_v1.4/data_snapshot_metadata_schema_v1.4.schema.json)
- [Field reference](../../../docs/schema_v1.4/schema_reference_v1.4.md)

Check whether they match the models without writing files, in a **WSL terminal
or PowerShell**:

```shell
uv run --locked python -m data_snapshot.metadata_schema.generation --check
```

For in-memory output, `render_json_schema()` and `render_markdown_reference()`
return strings. `write_schema_artifacts(json_path, markdown_path)` accepts custom
output paths. Import these helpers from `data_snapshot.metadata_schema.generation`.

## Further reading

- [Field reference](../../../docs/schema_v1.4/schema_reference_v1.4.md): generated types, constraints, enums, and mappings.
- [Schema v1.4 change report](../../../docs/schema_v1.4/schema_v1.4_change_report.md): changes derived from Batch 1 annotation.
- [Schema v1.3 change report](../../../docs/schema_v1.3/schema_v1.3_change_report.md): earlier decisions and expected extraction effects.

The following v1.2 documents are frozen historical design inputs. They explain
the baseline evaluated by Schema Validation 3 but do not override the current
models and generated artifacts.

- [Schema v1.2 concept design](../../../docs/schema_v1.2/2.0-concept_design.md): baseline concepts and relationships.
- [Schema v1.2 normalization profile](../../../docs/schema_v1.2/3.0-normalization.md): baseline normalization policy.
- [Schema v1.2 standards crosswalk](../../../docs/schema_v1.2/1.0-standards_crosswalk.md): baseline semantic alignment with external standards.
