"""Machine-readable renderings of the deposit column contract (ticket 0354).

Two serialisations of the same facts `_deposit_variables.py` already carries:

- **Frictionless Data Package** (`datapackage.json`) — the descriptor
  `frictionless validate` reads, so every value-level claim the codebook
  publishes (types, enumerations, ranges) is checked against the *written* CSV
  rather than an in-memory frame. Validating the artifact is the whole point:
  an integer serialised as ``1.0``, a quoting slip, or an encoding fault is
  invisible to a frame-level assertion (0288/0347, 0325).
- **Croissant** (`croissant.json`) — MLCommons JSON-LD over schema.org, for ML
  consumers that index datasets by field. Optional deliverable; it reuses the
  same contract, so the two descriptions cannot disagree.

Neither emitter stamps a timestamp. The descriptors are build outputs, and a
changing ``created`` field would dirty git on every rebuild for no information.

The envelope below mirrors the Zenodo record by hand, because the deposit is
uploaded through the web form: no repo-side metadata file is ingested. Keep it
in step with `deliverables/data-paper/revision-rdj26561/ed04-zenodo-restructure-upload.md`,
which is the author's upload checklist and the reason these literals exist here
rather than being read from the record.
"""

import csv
import hashlib
import os

from _deposit_variables import DEPOSIT_VARIABLES, Variable


def read_header(path: str) -> list[str]:
    """Column names of a CSV, without loading its rows."""
    with open(path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), [])
    if not header:
        raise ValueError(f"no header row in {path}")
    return header


def count_rows(path: str) -> int:
    """Data rows in a CSV.

    Counted through the csv reader, not by newlines: bibliographic titles and
    author lists carry embedded newlines inside quoted fields, so a line count
    overstates the number of records.
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        return sum(1 for _ in reader)

# The deposited CSV, named the same in the archive and in the descriptors.
RESOURCE_FILENAME = "climate_finance_corpus.csv"
RESOURCE_NAME = "climate-finance-corpus"

CONCEPT_DOI = "https://doi.org/10.5281/zenodo.19236130"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"

# Bumped with the Zenodo record's version field; the ed04 checklist is where
# the author sets it on upload. Overridable per invocation with --version.
DEPOSIT_VERSION = "1.1.1"

DATASET_TITLE = ("A Curated Corpus of Climate Finance Literature, 1990–2024: "
                 "Six Sources, Multilingual Retrieval, and Grey Literature")
DATASET_DESCRIPTION = (
    "Deduplicated bibliographic corpus of the climate finance literature, "
    "merged from six catalogs with multilingual retrieval and grey literature, "
    "carrying per-source provenance flags and a quality-flag audit trail. The "
    "refined subset is df[~df['is_flagged'] | df['is_protected']]. Abstracts "
    "are not redistributed; retrieve them via the DOI or OpenAlex identifier.")
CITE_AS = (
    "Ha-Duong, M. (2026). A Curated Corpus of Climate Finance Literature, "
    "1990–2024: Six Sources, Multilingual Retrieval, and Grey Literature "
    "[Data set]. Zenodo. https://doi.org/10.5281/zenodo.19236130")

KEYWORDS = ["climate finance", "bibliometrics", "history of economic thought",
            "grey literature", "OpenAlex", "text corpus"]

# ORCID is also carried by the paper front matter (data-paper.qmd); the funder
# identifiers were verified against ROR and the Crossref Funder Registry, which
# cross-confirm (the ROR record holds the same fundref ID).
AUTHOR = {"name": "Minh Ha-Duong",
          "orcid": "https://orcid.org/0000-0001-9988-2100",
          "organization": "CIRED"}
FUNDER = {"name": "Centre National de la Recherche Scientifique",
          "ror": "https://ror.org/02feahw73",
          "funder_id": "https://doi.org/10.13039/501100004794"}

# Frictionless type → Croissant (schema.org) dataType.
_CROISSANT_TYPE = {
    "string": "sc:Text",
    "integer": "sc:Integer",
    "number": "sc:Float",
    "boolean": "sc:Boolean",
}


def _constraints(v: Variable) -> dict[str, object]:
    """Frictionless field constraints for one variable, omitting empty ones.

    ``nullable`` deliberately does not become ``required``. Four columns the
    contract types non-nullable carry real gaps in the shipped data (source_id
    1.3%, title 0.6%, year 1.1%, cited_by_count 4.7%), so publishing a
    non-null guarantee would either fail the gate on a correct build or bake
    this build's missingness into the schema. The prose keeps saying what the
    column is *for*; the schema only claims what it can enforce.
    """
    out: dict[str, object] = {}
    if v.enum:
        out["enum"] = list(v.enum)
    if v.minimum is not None:
        out["minimum"] = v.minimum
    if v.maximum is not None:
        out["maximum"] = v.maximum
    return out


def frictionless_field(v: Variable) -> dict[str, object]:
    """One Frictionless Table Schema field."""
    field: dict[str, object] = {
        "name": v.name,
        "type": v.dtype,
        "description": v.description,
    }
    constraints = _constraints(v)
    if constraints:
        field["constraints"] = constraints
    return field


def contract_for(columns: list[str]) -> list[Variable]:
    """Contract variables for ``columns``, **in the order the file has them**.

    Two reasons the order is the file's and not the contract's. Frictionless
    matches schema fields to CSV columns by *position*, so a descriptor in
    contract order silently validates each column against its neighbour's
    rules — which is how this emitter first reported `source_count` holding
    the value `source` (the deposit writes the curation columns in a different
    order than the contract declares them, at six positions).

    And the descriptor describes the file *as shipped*: an optional column
    absent from a build gets no field, or validation would report a missing
    label for a column the build legitimately never produced.
    """
    by_name = {v.name: v for v in DEPOSIT_VARIABLES}
    return [by_name[c] for c in columns if c in by_name]


def render_datapackage(columns: list[str], version: str) -> dict[str, object]:
    """Frictionless Data Package descriptor for the deposited CSV."""
    return {
        "$schema": "https://datapackage.org/profiles/2.0/datapackage.json",
        "name": RESOURCE_NAME,
        "id": CONCEPT_DOI,
        "title": DATASET_TITLE,
        "description": DATASET_DESCRIPTION,
        "version": version,
        "homepage": CONCEPT_DOI,
        "keywords": KEYWORDS,
        "licenses": [{
            "name": "CC-BY-4.0",
            "path": LICENSE_URL,
            "title": "Creative Commons Attribution 4.0 International",
        }],
        "contributors": [
            {"title": AUTHOR["name"], "path": AUTHOR["orcid"],
             "roles": ["author"], "organization": AUTHOR["organization"]},
            {"title": FUNDER["name"], "path": FUNDER["ror"],
             "roles": ["funder"]},
        ],
        "resources": [{
            "name": RESOURCE_NAME,
            "type": "table",
            "path": RESOURCE_FILENAME,
            "format": "csv",
            "mediatype": "text/csv",
            "encoding": "utf-8",
            "dialect": {"delimiter": ",", "header": True},
            "schema": {
                "fields": [frictionless_field(v) for v in contract_for(columns)],
                "missingValues": [""],
            },
        }],
    }


def sha256_of(path: str) -> str:
    """Streaming SHA-256 of a file, for the Croissant FileObject."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_CROISSANT_CONTEXT: dict[str, object] = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "cr": "http://mlcommons.org/croissant/",
    "sc": "https://schema.org/",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "dct": "http://purl.org/dc/terms/",
    "extract": "cr:extract",
    "field": "cr:field",
    "fileObject": "cr:fileObject",
    "recordSet": "cr:recordSet",
    "source": "cr:source",
}


def render_croissant(columns: list[str], version: str, csv_path: str,
                     n_rows: int) -> dict[str, object]:
    """Croissant (MLCommons JSON-LD) description of the deposited CSV."""
    file_id = RESOURCE_FILENAME
    record_id = RESOURCE_NAME
    fields = [{
        "@type": "cr:Field",
        "@id": f"{record_id}/{v.name}",
        "name": v.name,
        "description": v.description,
        "dataType": _CROISSANT_TYPE[v.dtype],
        "source": {
            "fileObject": {"@id": file_id},
            "extract": {"column": v.name},
        },
    } for v in contract_for(columns)]
    return {
        "@context": _CROISSANT_CONTEXT,
        "@type": "sc:Dataset",
        "conformsTo": "http://mlcommons.org/croissant/1.0",
        "name": RESOURCE_NAME,
        "title": DATASET_TITLE,
        "description": DATASET_DESCRIPTION,
        "version": version,
        "license": LICENSE_URL,
        "url": CONCEPT_DOI,
        "citeAs": CITE_AS,
        "keywords": KEYWORDS,
        "creator": {
            "@type": "sc:Person",
            "name": AUTHOR["name"],
            "sameAs": AUTHOR["orcid"],
            "affiliation": {"@type": "sc:Organization",
                            "name": AUTHOR["organization"]},
        },
        "funder": {
            "@type": "sc:Organization",
            "name": FUNDER["name"],
            "sameAs": FUNDER["ror"],
            "identifier": FUNDER["funder_id"],
        },
        "distribution": [{
            "@type": "cr:FileObject",
            "@id": file_id,
            "name": os.path.basename(csv_path),
            "description": f"Deposited corpus table, {n_rows} rows.",
            "contentUrl": RESOURCE_FILENAME,
            "encodingFormat": "text/csv",
            "sha256": sha256_of(csv_path),
        }],
        "recordSet": [{
            "@type": "cr:RecordSet",
            "@id": record_id,
            "name": record_id,
            "description": "One deduplicated bibliographic work per row.",
            "field": fields,
        }],
    }
