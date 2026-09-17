"""Build the frozen, source-layer M1a JETP inventories.

M1a is a presentation export, not an identity reconciliation.  Every supplied
source row is written once, with its layer and original payload intact.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

COUNTRIES = ("ZAF", "IDN", "VNM", "SEN")
FIELDS = (
    "inventory_row_id",
    "country",
    "source_layer",
    "source_id",
    "source_edition",
    "source_cutoff",
    "source_document_sha256",
    "source_row_id",
    "label",
    "record_type",
    "reported_status",
    "identity_status",
    "evidence_locator",
    "unknown_fields",
    "source_fields_json",
)


@dataclass(frozen=True)
class FrozenLayer:
    """One bounded source layer whose rows must not be reconciled or merged."""

    country: str
    layer_id: str
    source_id: str
    edition: str
    cutoff: str
    source_sha256: str
    rows: Sequence[Mapping[str, object]]
    unavailable_source_rows: int = 0


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _unknown_source_fields(fields: Mapping[str, object]) -> list[str]:
    return sorted(key for key, value in fields.items() if value is None or value == "")


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
        output.append(
            {
                "inventory_row_id": f"{layer.country}:{layer.layer_id}:{row_id}",
                "country": layer.country,
                "source_layer": layer.layer_id,
                "source_id": layer.source_id,
                "source_edition": layer.edition,
                "source_cutoff": layer.cutoff,
                "source_document_sha256": layer.source_sha256,
                "source_row_id": row_id,
                "label": str(source_row.get("label", "")),
                "record_type": str(source_row.get("record_type", "unknown")) or "unknown",
                "reported_status": str(source_row.get("reported_status", "")),
                "identity_status": identity_status,
                "evidence_locator": str(source_row.get("evidence_locator", "")),
                "unknown_fields": "|".join(unknown_fields),
                "source_fields_json": _json(dict(source_fields)),
            }
        )
    return output, {
        "layer_id": layer.layer_id,
        "source_id": layer.source_id,
        "edition": layer.edition,
        "cutoff": layer.cutoff,
        "source_sha256": layer.source_sha256,
        "row_count": len(output),
        "unknowns": {
            "field_values": field_unknowns,
            "identity_rows": identity_unknowns,
            "unavailable_source_rows": layer.unavailable_source_rows,
        },
    }


def write_inventories(layers: Iterable[FrozenLayer], output_dir: Path) -> dict[str, object]:
    """Write one deterministic CSV per country plus a source/unknown manifest."""
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
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        countries[country] = {
            "file": destination.name,
            "sha256": _sha256(destination),
            "row_count": len(rows),
            "layers": summaries,
            "unknowns": {
                key: sum(int(layer["unknowns"][key]) for layer in summaries)
                for key in ("field_values", "identity_rows", "unavailable_source_rows")
            },
        }

    manifest: dict[str, object] = {
        "schema_version": "jetp-m1a-frozen-inventories/1",
        "scope": "frozen source-layer inventories; no identity reconciliation or live refresh",
        "countries": countries,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
