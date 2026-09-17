"""Build the frozen, extraction sub-layer M1a JETP inventories.

M1a is a presentation export, not an identity reconciliation.  Every supplied
source row is written once, with its sub-layer and original payload intact.
"""

import argparse
import csv
import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from jetp.build_0818_zaf_q1_reconciliation import SOURCE_FIELDS as _RAW_FIELD_ORDER

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


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _require_input(
    root: Path,
    specification: Mapping[str, object],
    path_key: str = "input_path",
    sha_key: str = "input_sha256",
) -> Path:
    path = root / str(specification[path_key])
    if not path.is_file() or _sha256(path) != specification[sha_key]:
        raise ValueError(f"frozen M1a input hash mismatch: {path}")
    return path


def _plan_rows(rows: Sequence[Mapping[str, str]], specification: Mapping[str, object]) -> list[dict[str, object]]:
    selected = [
        row for row in rows
        if row["country"] == specification["country"]
        and row["source_id"] == specification["source_id"]
    ]
    return [
        {
            "source_row_id": row["plan_project_id"],
            "label": row["project_name"],
            "record_type": specification["record_type"],
            "reported_status": row["priority_tier"] or "unknown",
            "identity_status": "named" if row["project_name"] else "unknown",
            "evidence_locator": row["locator"],
            "source_fields": dict(row),
        }
        for row in selected
    ]


def _zaf_rows(
    rows: Sequence[Mapping[str, str]],
    specification: Mapping[str, object],
    field_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, object]]:
    # The 21 register labels live in the 0818 sidecar table, not in the
    # reconciled CSV, which is a content-hashed input of the 0822 freeze.  The
    # join is positional and checked: same builder, same row order, same
    # ``ordinal``.
    if len(field_rows) != len(rows):
        raise ValueError("South Africa register sidecar row count does not match")

    def _fields(row: Mapping[str, str], field_row: Mapping[str, str]) -> dict[str, object]:
        if field_row["ordinal"] != row["ordinal"]:
            raise ValueError("South Africa register sidecar is not aligned by ordinal")
        # The values are already the strings the sidecar holds; passing them
        # through ``_text`` again would be a second normalisation of the same
        # data.
        fields = dict(row)
        for source_key in _RAW_FIELD_ORDER:
            fields[_raw_slug(source_key)] = field_row[source_key]
        return fields

    return [
        {
            "source_row_id": row["ordinal"],
            "label": row["project_name"],
            "record_type": specification["record_type"],
            "reported_status": row["implementation_status"] or "unknown",
            "identity_status": "named" if row["project_name"] else "unknown",
            "evidence_locator": row["locator"],
            "source_fields": _fields(row, field_row),
        }
        for row, field_row in zip(rows, field_rows, strict=True)
    ]


def _vnm_rows(payload: Mapping[str, object], specification: Mapping[str, object]) -> list[dict[str, object]]:
    if specification["record_type"] != "from_source_classification":
        raise ValueError("Viet Nam M1a record type must preserve source classification")
    positions = payload.get("inventory_positions")
    if not isinstance(positions, list):
        raise ValueError("Viet Nam migration lacks inventory_positions")
    return [
        {
            "source_row_id": row["inventory_id"],
            "label": row["source_wording"],
            "record_type": row["classification"],
            "reported_status": (
                "unknown" if row.get("value") is None or row.get("value") == ""
                else str(row["value"])
            ),
            "identity_status": "unknown" if row["classification"] == "unknown" else "named",
            "evidence_locator": row["locator"],
            "source_fields": dict(row),
        }
        for row in positions
    ]


def build_existing_layers(root: Path, config_path: Path | None = None) -> list[FrozenLayer]:
    """Adapt only the pinned, already-extracted country inputs into M1a layers."""
    root = Path(root)
    config_path = config_path or root / "config" / "jetp-m1a-inventories.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    layers: list[FrozenLayer] = []
    csv_cache: dict[Path, list[dict[str, str]]] = {}
    json_cache: dict[Path, Mapping[str, object]] = {}
    for specification in config["layers"]:
        path = _require_input(root, specification)
        adapter = specification["adapter"]
        if adapter == "plan_projects":
            rows = _plan_rows(csv_cache.setdefault(path, _read_csv(path)), specification)
        elif adapter == "zaf_register":
            fields_path = _require_input(
                root, specification, "fields_input_path", "fields_input_sha256"
            )
            rows = _zaf_rows(
                csv_cache.setdefault(path, _read_csv(path)),
                specification,
                csv_cache.setdefault(fields_path, _read_csv(fields_path)),
            )
        elif adapter == "vnm_rmp":
            if path not in json_cache:
                json_cache[path] = json.loads(path.read_text(encoding="utf-8"))
            rows = _vnm_rows(json_cache[path], specification)
        else:
            raise ValueError(f"unknown M1a adapter: {adapter}")
        if len(rows) != specification["expected_rows"]:
            raise ValueError(f"frozen layer row count changed: {specification['layer_id']}")
        if any(
            row["source_fields"].get("document_sha256") != specification["source_sha256"]
            for row in rows
            if adapter != "vnm_rmp"
        ):
            raise ValueError(f"source document hash changed: {specification['layer_id']}")
        if adapter == "vnm_rmp" and any(
            row["source_fields"]["evidence"]["document_sha256"] != specification["source_sha256"]
            for row in rows
        ):
            raise ValueError("Viet Nam source document hash changed")
        layers.append(
            FrozenLayer(
                country=specification["country"],
                layer_id=specification["layer_id"],
                source_id=specification["source_id"],
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=root / "deliverables" / "jetp-observatory" / "data" / "m1a",
    )
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    write_inventories(build_existing_layers(root, args.config), args.output_dir)


if __name__ == "__main__":
    main()
