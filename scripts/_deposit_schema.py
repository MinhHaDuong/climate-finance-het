"""Machine-readable rendering of the deposit column contract (ticket 0354).

A **Frictionless Data Package** (`datapackage.json`) over the facts
`_deposit_variables.py` already carries. It is the descriptor `frictionless
validate` reads, so every value-level claim the deposit publishes (types,
enumerations, ranges) is checked against the *written* CSV rather than an
in-memory frame. Validating the artifact is the whole point: an integer
serialised as ``1.0``, a quoting slip, or an encoding fault is invisible to a
frame-level assertion (0288/0347, 0325).

A second serialisation in MLCommons Croissant was built and dropped: nothing
in reach validates it against the spec (`mlcroissant` pulls `pandas-stubs`,
which changes mypy's verdict repo-wide), and an unvalidated descriptor is the
drift this ticket exists to remove.

The emitter stamps no timestamp. The descriptor is a build output, and a
changing ``created`` field would dirty git on every rebuild for no information.

The envelope below mirrors the Zenodo record by hand, because the deposit is
uploaded through the web form: no repo-side metadata file is ingested. Keep it
in step with `deliverables/data-paper/revision-rdj26561/ed04-zenodo-restructure-upload.md`,
which is the author's upload checklist and the reason these literals exist here
rather than being read from the record.
"""

import csv

from _deposit_variables import DEPOSIT_VARIABLES, Variable


def read_header(path: str) -> list[str]:
    """Column names of a CSV, without loading its rows."""
    with open(path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), [])
    if not header:
        raise ValueError(f"no header row in {path}")
    return header


# The deposited CSV, named the same in the archive and in the descriptor.
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
          # Crossref Funder Registry ID: the Zenodo upload form asks for it,
          # the Data Package contributor object has no slot for it.
          "funder_id": "https://doi.org/10.13039/501100004794"}


def _constraints(v: Variable) -> dict[str, object]:
    """Frictionless field constraints for one variable, omitting empty ones.

    ``required`` is the negation of ``nullable``, which the contract states
    from measured evidence rather than intent — so a column declared required
    is one the shipped data has no gap in, and a future build that introduces
    one fails the gate. That is the guarantee worth publishing.
    """
    out: dict[str, object] = {}
    if not v.nullable:
        out["required"] = True
    if v.enum:
        out["enum"] = list(v.enum)
    if v.minimum is not None:
        out["minimum"] = v.minimum
    if v.maximum is not None:
        out["maximum"] = v.maximum
    return out


def frictionless_field(v: Variable,
                       missing: float | None = None) -> dict[str, object]:
    """One Frictionless Table Schema field.

    ``missingRate`` is a custom property carrying what the retired prose
    codebook printed: the share of empty cells measured on the shipped data.
    Frictionless preserves unknown field properties, so it travels with the
    schema instead of in a separate document that can drift from it.
    """
    field: dict[str, object] = {
        "name": v.name,
        "type": v.dtype,
        "description": v.description,
    }
    if v.empty_is_a_value:
        # An empty cell here is data ("no flags raised"), not an absent value,
        # so it must not be read as missing — otherwise `required` would fail
        # on every unflagged work.
        field["missingValues"] = []
    constraints = _constraints(v)
    if constraints:
        field["constraints"] = constraints
    if missing is not None:
        field["missingRate"] = round(missing, 4)
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


def render_datapackage(columns: list[str], version: str,
                       missingness: dict[str, float] | None = None,
                       ) -> dict[str, object]:
    """Frictionless Data Package descriptor for the deposited CSV.

    ``missingness`` maps column → share of empty cells, measured on the file
    being described. Omitted, the fields carry no ``missingRate``.
    """
    miss = missingness or {}
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
                "fields": [frictionless_field(v, miss.get(v.name))
                           for v in contract_for(columns)],
                "missingValues": [""],
            },
        }],
    }
