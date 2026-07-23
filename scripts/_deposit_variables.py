"""Column contract for the Zenodo deposit file climate_finance_corpus.csv.

Single source of truth for the deposit's variables (ticket 0279, remark
ED-03): each entry documents one column — name, type, description, source
step. Three consumers keep it honest:

- ``transform()`` — the extended_works → deposit column transform used by
  scripts/figures/export_deposit.py, which calls ``check_columns()`` on its
  output at write time, so an undocumented or missing column stops the build;
- scripts/figures/export_variables_table.py — renders the data paper's
  variables table (``render_markdown_table()``), so the published table
  cannot drift from the shipped CSV;
- tests/test_variables_table.py — pins contract/transform agreement.

Columns marked ``required=False`` depend on optional pipeline stages
(embeddings for the outlier distance, the v1 identifier file, the corpus-v2
curated key-documents layer) and may be absent from older corpus builds.
"""

from dataclasses import dataclass

# Individual flag columns collapsed into is_flagged + flag_reason
FLAG_COLUMNS = [
    "missing_metadata",
    "no_abstract_irrelevant",
    "title_blacklist",
    "citation_isolated_old",
    "semantic_outlier",
    "llm_irrelevant",
]

# Columns dropped from the deposit (intermediate or restricted)
COLUMNS_TO_DROP = [
    "abstract",       # publisher redistribution restrictions
    "doi_norm",       # intermediate
    "action",         # redundant with is_flagged/is_protected
]

DEPOSIT_RENAMES = {"from_scispsace": "from_scispace"}


@dataclass(frozen=True)
class Variable:
    name: str
    type: str
    description: str
    source: str
    required: bool = True


_MERGE = "source catalogs, merged by catalog_merge.py"
_ENRICH = "enrichment (enrich_* scripts)"
_FILTER = "quality filtering (corpus_filter.py)"
_KEYDOCS = "curated key-documents layer (catalog_keydocs.py, corpus v2)"

DEPOSIT_VARIABLES: list[Variable] = [
    Variable("source", "string",
             "Primary source catalog for the record's metadata (highest-priority "
             "contributing source)", _MERGE),
    Variable("source_id", "string",
             "Identifier in the primary source (e.g. OpenAlex work ID)", _MERGE),
    Variable("doi", "string, nullable",
             "Digital Object Identifier, when available", _MERGE),
    Variable("title", "string", "Title of the work", _MERGE),
    Variable("first_author", "string, nullable", "First author name", _MERGE),
    Variable("all_authors", "string, nullable",
             "Full author list, separator-joined", _MERGE),
    Variable("year", "integer", "Publication year", _MERGE),
    Variable("journal", "string, nullable",
             "Publication venue (journal, publisher, or repository)", _MERGE),
    Variable("language", "string, nullable",
             "Language code (ISO 639-1), detected and normalised", _ENRICH),
    Variable("keywords", "string, nullable",
             "Keywords, semicolon-separated", _MERGE),
    Variable("categories", "string, nullable",
             "Subject categories / concepts from the source catalog", _MERGE),
    Variable("cited_by_count", "integer",
             "Citation count (OpenAlex, as of the collection date)", _MERGE),
    Variable("affiliations", "string, nullable",
             "Author affiliations, when available", _MERGE),
    Variable("from_openalex", "boolean", "Provenance flag: found in OpenAlex", _MERGE),
    Variable("from_istex", "boolean", "Provenance flag: found in ISTEX", _MERGE),
    Variable("from_bibcnrs", "boolean", "Provenance flag: found in bibCNRS", _MERGE),
    Variable("from_scispace", "boolean", "Provenance flag: found via SciSpace", _MERGE),
    Variable("from_grey", "boolean",
             "Provenance flag: grey-literature source", _MERGE),
    Variable("from_teaching", "boolean",
             "Provenance flag: teaching canon (syllabi)", _MERGE),
    Variable("from_unfccc", "boolean",
             "Provenance flag: curated UNFCCC key document", _KEYDOCS,
             required=False),
    Variable("from_oecd", "boolean",
             "Provenance flag: curated OECD key document", _KEYDOCS,
             required=False),
    Variable("abstract_provenance", "string, nullable",
             "Provenance of the abstract text for curated key documents: "
             "`curated`, `reconstructed:lead`, or `reconstructed:exec_summary`; "
             "empty elsewhere", _KEYDOCS, required=False),
    Variable("keywords_provenance", "string, nullable",
             "Provenance of the keywords for curated key documents: `extracted` "
             "or `generated:lexicon`; empty elsewhere", _KEYDOCS, required=False),
    Variable("source_count", "integer",
             "Number of sources that contributed the record (sum of the "
             "provenance flags)", _MERGE),
    Variable("abstract_status", "string",
             "Status of the (undistributed) abstract: `original`, "
             "`reconstructed` (from OpenAlex inverted index or ISTEX fulltext), "
             "`generated` (LLM summary of an oversized abstract), `too_long`, "
             "or `missing`", _ENRICH),
    Variable("near_duplicate_group", "integer, nullable",
             "Group identifier for near-identical content published under "
             "several DOIs; null for ungrouped works", _FILTER),
    Variable("semantic_outlier_dist", "float, nullable",
             "Distance to the corpus embedding centroid, computed for the "
             "semantic-outlier flag", _FILTER, required=False),
    Variable("in_v1", "boolean",
             "Version tracking: work present in the v1.0 submission corpus",
             _FILTER, required=False),
    Variable("is_flagged", "boolean",
             "Any quality flag raised; the refined subset is "
             "`df[~df['is_flagged'] | df['is_protected']]`", _FILTER),
    Variable("flag_reason", "string",
             "Comma-separated list of raised quality flags "
             f"({', '.join(FLAG_COLUMNS)}); empty when unflagged", _FILTER),
    Variable("is_protected", "boolean",
             "Protection from removal (key papers kept despite flags)", _FILTER),
    Variable("protection_reason", "string, nullable",
             "Why the work is protected (citation count, seed list, ...)",
             _FILTER, required=False),
]


def contract_names() -> list[str]:
    """Ordered column names declared by the contract."""
    return [v.name for v in DEPOSIT_VARIABLES]


def check_columns(columns: list[str]) -> list[str]:
    """Compare a deposit column set against the contract.

    Returns a list of error strings: one per undocumented column, one per
    missing required column. Empty list = no drift.
    """
    declared = set(contract_names())
    errors = [f"undocumented column in deposit: {c}"
              for c in columns if c not in declared]
    present = set(columns)
    errors += [f"required column missing from deposit: {v.name}"
               for v in DEPOSIT_VARIABLES if v.required and v.name not in present]
    return errors


def transform(df):
    """Extended_works → deposit transform (pure; no I/O).

    Collapses individual flag columns into is_flagged/flag_reason, renames
    protection columns, drops restricted/intermediate columns, and fixes the
    legacy scispace typo. Mirrored from the historical export_deposit.py body.
    """
    df = df.copy()
    flag_cols_present = [c for c in FLAG_COLUMNS if c in df.columns]
    if flag_cols_present:
        flags = df[flag_cols_present].fillna(False).astype(bool)
        df["is_flagged"] = flags.any(axis=1)
        df["flag_reason"] = flags.apply(
            lambda row: ",".join(c for c in flag_cols_present if row[c]), axis=1)
        df.loc[~df["is_flagged"], "flag_reason"] = ""

    if "protected" in df.columns:
        df = df.rename(columns={"protected": "is_protected"})
    if "protect_reason" in df.columns:
        df = df.rename(columns={"protect_reason": "protection_reason"})

    to_drop = [c for c in COLUMNS_TO_DROP + flag_cols_present if c in df.columns]
    if to_drop:
        df = df.drop(columns=to_drop)

    renames = {k: v for k, v in DEPOSIT_RENAMES.items() if k in df.columns}
    if renames:
        df = df.rename(columns=renames)
    return df


def render_markdown_table() -> str:
    """Render the contract as a Quarto pipe table with caption and label."""
    lines = [
        "| Variable | Type | Description | Source |",
        "|:------|:----|:-------------------------|:---------|",
    ]
    for v in DEPOSIT_VARIABLES:
        desc = v.description if v.required else v.description + \
            " (absent from corpus builds predating this pipeline stage)"
        lines.append(f"| `{v.name}` | {v.type} | {desc} | {v.source} |")
    lines += [
        "",
        ": Variables of `climate_finance_corpus.csv`. The table is generated "
        "from the deposit column contract (`scripts/_deposit_variables.py`), "
        "which the export script enforces at write time. {#tbl-variables}",
    ]
    return "\n".join(lines) + "\n"
