"""Build the frozen, extraction sub-layer M1a JETP inventories.

M1a is a presentation export, not an identity reconciliation.  Every supplied
source row is written once, with its sub-layer and original payload intact.

Since ticket 0873 the rows are read from the ledger: the lines of the six
extracts, their per-document fields and the routes of the identifiers the
export serves, which ``build_m1a_lines.py`` ingested once from the pinned
extracts.  The export is a view of those lines, byte for byte the export the
extracts gave.
"""

import argparse
import csv
import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from jetp._ledger_headers import load_schema, read_csv, read_table

COUNTRIES = ("ZAF", "IDN", "VNM", "SEN")
FIELDS = (
    "country",
    "source_layer",
    "source_id",
    "source_edition",
    "source_cutoff",
    "source_row_id",
    "label",
    "record_type",
    "reported_status",
    "identity_status",
    "evidence_locator",
)

# Viet Nam's source classification of a Resource Mobilisation Plan row and the
# line classification it is ingested as; the export shows the source word.
VNM_CLASSIFICATION = {
    "named": "named_item",
    "programme": "heading",
    "unknown": "unnamed_item",
}

# Appended by the ingestion to a locator whose printed row number the
# publisher repeated in the same table, so that no two lines claim one place;
# the export shows the locator as printed.
PHYSICAL_ROW = "; physical row {}"
_PHYSICAL_ROW_SUFFIX = re.compile(r"; physical row [0-9]+$")


@dataclass(frozen=True)
class FrozenLayer:
    """One bounded extraction sub-layer whose rows must not be reconciled or merged."""

    country: str
    layer_id: str
    source_id: str
    edition: str
    cutoff: str
    source_sha256: str
    rows: Sequence[Mapping[str, object]]
    unavailable_source_rows: int = 0
    input_path: str = "fixture"
    input_sha256: str = "fixture"
    excluded_source_rows: tuple = ()
    # Second pinned input, where the layer has one: the file the pass-through
    # ``raw_`` columns come from.  Empty for the layers that have none, so the
    # manifest key exists for every layer and the absence is readable.
    fields_input_path: str = ""
    fields_input_sha256: str = ""


def _raw_slug(name: str) -> str:
    """Prefix one source label into a pass-through column name.

    Uniform by construction: ``Total US$`` becomes ``raw_total_us``, the ``$``
    dropping out like any other non-alphanumeric character.  The rule is applied
    to every label or to none — a hand-corrected ``raw_total_usd`` would make the
    column set unreproducible from the source header.
    """
    return "raw_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _unknown_source_fields(fields: Mapping[str, object]) -> list[str]:
    # Pass-through ``raw_`` columns restate values the adapter already exposes
    # under its own labels, so counting their blanks would report one absence
    # twice and move a published statistic for a change that adds no unknown.
    return sorted(
        key
        for key, value in fields.items()
        if not key.startswith("raw_") and (value is None or value == "")
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_layer(layer: FrozenLayer) -> tuple[list[dict[str, str]], dict[str, object]]:
    if layer.country not in COUNTRIES:
        raise ValueError(f"unsupported M1a country: {layer.country}")
    if not all((layer.layer_id, layer.source_id, layer.edition, layer.cutoff)):
        raise ValueError(f"incomplete frozen layer metadata: {layer.country}/{layer.layer_id}")
    if layer.unavailable_source_rows < 0:
        raise ValueError("unavailable source-row count cannot be negative")

    output: list[dict[str, str]] = []
    seen: set[str] = set()
    field_unknowns = 0
    identity_unknowns = 0
    for source_row in layer.rows:
        row_id = str(source_row.get("source_row_id", ""))
        if not row_id or row_id in seen:
            raise ValueError(f"missing or duplicate source row in {layer.layer_id}: {row_id}")
        seen.add(row_id)
        source_fields = source_row.get("source_fields")
        if not isinstance(source_fields, Mapping):
            raise ValueError(f"source_fields must preserve the original row: {row_id}")
        unknown_fields = _unknown_source_fields(source_fields)
        field_unknowns += len(unknown_fields)
        identity_status = str(source_row.get("identity_status", "unknown")) or "unknown"
        identity_unknowns += identity_status == "unknown"
        # Pass-through columns, if the adapter produced any: every key the
        # adapter prefixed ``raw_``, in its own order, copied without reading or
        # converting the value.  Countries whose adapter produces none keep the
        # eleven presentation columns, which is what makes the export width
        # per-country rather than global.
        passthrough = {
            key: value for key, value in source_fields.items() if key.startswith("raw_")
        }
        output.append(
            {
                "country": layer.country,
                "source_layer": layer.layer_id,
                "source_id": layer.source_id,
                "source_edition": layer.edition,
                "source_cutoff": layer.cutoff,
                "source_row_id": row_id,
                "label": str(source_row.get("label", "")),
                "record_type": str(source_row.get("record_type", "unknown")) or "unknown",
                "reported_status": str(source_row.get("reported_status", "")),
                "identity_status": identity_status,
                "evidence_locator": str(source_row.get("evidence_locator", "")),
                **passthrough,
            }
        )
    return output, {
        "excluded_source_rows": list(layer.excluded_source_rows),
        "sublayer_id": layer.layer_id,
        "source_id": layer.source_id,
        "edition": layer.edition,
        "cutoff": layer.cutoff,
        "source_sha256": layer.source_sha256,
        "input_path": layer.input_path,
        "input_sha256": layer.input_sha256,
        "fields_input_path": layer.fields_input_path,
        "fields_input_sha256": layer.fields_input_sha256,
        "row_count": len(output),
        "unknowns": {
            "field_values": field_unknowns,
            "identity_rows": identity_unknowns,
            "unavailable_source_rows": layer.unavailable_source_rows,
        },
    }


def _write_json_companion(
    destination: Path,
    country: str,
    header: Sequence[str],
    rows: Sequence[Mapping[str, str]],
) -> None:
    """Write the renderer's copy of one country's rows: header once, then values.

    Built from the in-memory rows, never by re-reading the CSV back: the Viet
    Nam locators carry commas and newlines inside quoted fields, which a
    browser-side splitter breaks on the real file while passing on a fixture.

    Header-plus-values rather than one object per row.  The keys are identical
    for every row of a country by construction — ``csv.DictWriter`` would raise
    otherwise — so repeating them 1 579 times only costs bytes: Indonesia came
    to 761 720 bytes under ``json.dumps(rows, ensure_ascii=False, indent=2)`` —
    the figure moves with the indentation, so the spelling is named — over the
    repository's 512 000 byte ceiling for a committed file, against 414 564
    here for the same rows in the same order.  One row per line keeps a
    regeneration readable as a diff.
    """
    values = ",\n    ".join(
        json.dumps([row[key] for key in header], ensure_ascii=False) for row in rows
    )
    destination.write_text(
        "{\n"
        f'  "country": {json.dumps(country)},\n'
        f'  "fields": {json.dumps(list(header), ensure_ascii=False)},\n'
        '  "rows": [\n'
        f"    {values}\n"
        "  ]\n"
        "}\n",
        encoding="utf-8",
    )


def write_inventories(layers: Iterable[FrozenLayer], output_dir: Path) -> dict[str, object]:
    """Write a deterministic CSV and JSON per country plus a source/unknown manifest.

    The CSV is the download artefact; the JSON companion carries the same rows,
    in the same order and under the same column names, for the Inventories page
    to read without parsing CSV text in the browser.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    by_country: dict[str, list[FrozenLayer]] = {country: [] for country in COUNTRIES}
    for layer in layers:
        if layer.country not in by_country:
            raise ValueError(f"unsupported M1a country: {layer.country}")
        by_country[layer.country].append(layer)
    missing = [country for country, country_layers in by_country.items() if not country_layers]
    if missing:
        raise ValueError(f"M1a requires a frozen layer for: {', '.join(missing)}")

    countries: dict[str, object] = {}
    for country in COUNTRIES:
        rows: list[dict[str, str]] = []
        summaries: list[dict[str, object]] = []
        for layer in sorted(by_country[country], key=lambda item: item.layer_id):
            layer_rows, summary = _render_layer(layer)
            rows.extend(layer_rows)
            summaries.append(summary)
        destination = output_dir / f"{country}.csv"
        # Width is per country: _render_layer emits the eleven presentation keys
        # first and then the pass-through keys, in the same order for every row
        # of a country, so the first row's key order is the header.
        extra = list(rows[0].keys())[len(FIELDS):] if rows else []
        header = FIELDS + tuple(extra)
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=header, lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        _write_json_companion(output_dir / f"{country}.json", country, header, rows)
        countries[country] = {
            "file": destination.name,
            "sha256": _sha256(destination),
            "row_count": len(rows),
            "sublayers": summaries,
            "unknowns": {
                key: sum(int(layer["unknowns"][key]) for layer in summaries)
                for key in ("field_values", "identity_rows", "unavailable_source_rows")
            },
        }

    manifest: dict[str, object] = {
        "schema_version": "jetp-m1a-frozen-inventories/1",
        "scope": "frozen extraction sub-layer inventories; no identity reconciliation or live refresh",
        "countries": countries,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _layer_rows(
    specification: Mapping[str, object],
    lines: Sequence[Mapping[str, str | None]],
    fields: Mapping[str, Mapping[str, str]],
    columns: Sequence[str],
    routes: Mapping[str, str],
) -> list[dict[str, object]]:
    """One layer's export rows, read from its document's lines and fields.

    ``lines`` are the layer's lines in extraction order, the order the export
    keeps. The unknown field values of a row are the blank cells among the
    columns its own table prints, a table printing a column when one of its
    lines fills it: a Viet Nam annex does not print the columns of the others.
    """
    document_id = str(specification["source_id"])
    adapter = specification["adapter"]
    table_of = {
        line["line_id"]: str(line["line_id"])[len(document_id) + 1:].rsplit("-", 1)[0]
        for line in lines
    }
    printed: dict[str, set[str]] = {}
    for line in lines:
        filled = {c for c in columns if fields[line["line_id"]][c]}
        printed.setdefault(table_of[line["line_id"]], set()).update(filled)
    inverse = {term: source for source, term in VNM_CLASSIFICATION.items()}
    rows = []
    for line in lines:
        line_id = str(line["line_id"])
        own = fields[line_id]
        table = printed[table_of[line_id]]
        source_fields: dict[str, object] = {c: own[c] for c in columns if c in table}
        if adapter == "zaf_register":
            source_fields.update({_raw_slug(c): own[c] for c in columns})
            reported = line["own_status"] or "unknown"
        elif adapter == "plan_projects":
            reported = own["priority_tier"] or "unknown"
        else:
            reported = str(specification["reported_status"])
        record_type = specification["record_type"]
        if record_type == "from_source_classification":
            record_type = inverse[str(line["classification"])]
        label = line["label"] or ""
        rows.append(
            {
                "source_row_id": routes.get(line_id, str(line["ordinal"])),
                "label": label,
                "record_type": record_type,
                "reported_status": reported,
                "identity_status": (
                    "named" if label and line["classification"] != "unnamed_item"
                    else "unknown"
                ),
                "evidence_locator": _PHYSICAL_ROW_SUFFIX.sub("", str(line["locator"])),
                "source_fields": source_fields,
            }
        )
    return rows


def _ledger(ledger_dir: Path) -> tuple[list[dict], dict, dict, dict]:
    schema = load_schema()

    def table(name: str) -> list[dict]:
        rows, errors = read_table(ledger_dir, name, schema)
        if errors:
            raise ValueError(f"ledger table {name}: {errors[0]}")
        return [dict(zip(schema.header(name), row)) for row in rows]

    # read_table reunites chunks in file order and keeps each file's row
    # order, which is extraction order: lines are appended, never reordered.
    lines = table("lines")
    specs = {row["document_id"]: json.loads(row["columns"]) for row in table("line_field_specs")}
    routes = {row["new_id"]: row["old_id"] for row in table("routes") if row["kind"] == "line"}
    fields: dict[str, dict[str, str]] = {}
    for document_id, columns in specs.items():
        header, body = read_csv(Path(ledger_dir) / "line-fields" / f"{document_id}.csv")
        if header != ["line_id", *columns]:
            raise ValueError(f"line-fields/{document_id}.csv does not carry its spec's header")
        fields.update({row[0]: dict(zip(columns, row[1:])) for row in body})
    return lines, specs, fields, routes


def build_existing_layers(
    root: Path, config_path: Path | None = None, ledger_dir: Path | None = None
) -> list[FrozenLayer]:
    """Read the six extracts' lines back into M1a layers (ticket 0873).

    The layer metadata, edition, cutoff and the pinned inputs the lines were
    ingested from (``build_m1a_lines.py``), stays in the layer manifest; every
    row comes from the ledger's ``lines``, ``line-fields``,
    ``line-field-specs`` and ``routes``.
    """
    root = Path(root)
    config_path = config_path or root / "config" / "jetp-m1a-inventories.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    lines, specs, fields, routes = _ledger(ledger_dir or root / "data" / "jetp")
    layers: list[FrozenLayer] = []
    for specification in config["layers"]:
        document_id = specification["source_id"]
        layer_lines = [
            line for line in lines
            if line["sha256"] == specification["source_sha256"]
            and str(line["line_id"]).startswith(f"{document_id}-")
            and line["line_id"] in fields
        ]
        if len(layer_lines) != specification["expected_rows"]:
            raise ValueError(f"frozen layer row count changed: {specification['layer_id']}")
        rows = _layer_rows(specification, layer_lines, fields, specs[document_id], routes)
        layers.append(
            FrozenLayer(
                country=specification["country"],
                layer_id=specification["layer_id"],
                source_id=document_id,
                edition=specification["edition"],
                cutoff=specification["cutoff"],
                source_sha256=specification["source_sha256"],
                rows=tuple(rows),
                unavailable_source_rows=specification["unavailable_source_rows"],
                input_path=specification["input_path"],
                input_sha256=specification["input_sha256"],
                excluded_source_rows=tuple(
                    specification.get("excluded_source_rows", ())
                ),
                fields_input_path=str(specification.get("fields_input_path", "")),
                fields_input_sha256=str(specification.get("fields_input_sha256", "")),
            )
        )
    return layers


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    # Deliberate script-io exception: nine files (a CSV and a JSON per country
    # and the manifest) go into one directory, so the single --output contract
    # of script_io_args does not fit; the Makefile names them as a group target.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=root / "deliverables" / "jetp-observatory" / "data" / "m1a",
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--ledger-dir", type=Path)
    args = parser.parse_args()
    write_inventories(
        build_existing_layers(root, args.config, args.ledger_dir), args.output_dir
    )


if __name__ == "__main__":
    main()
