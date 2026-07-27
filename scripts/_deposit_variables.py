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
    group: str = ""
    allowed_values: str = ""


# The four logical groups of the deposit layout (ticket 0287, remark R1-19).
# Contract order follows the groups: identity, then bibliographic metadata,
# then provenance, then curation — no interleaving.
GROUPS = [
    "Record identity",
    "Bibliographic metadata",
    "Provenance flags",
    "Curation metadata",
]
_IDENTITY, _BIBLIO, _PROV, _CURATION = GROUPS

_BOOL01 = "0, 1"
_BOOLTF = "true, false"

_MERGE = "source catalogs, merged by catalog_merge.py"
_ENRICH = "enrichment (enrich_* scripts)"
_FILTER = "quality filtering (corpus_filter.py)"
_KEYDOCS = "curated key-documents layer (catalog_keydocs.py, corpus v2)"

DEPOSIT_VARIABLES: list[Variable] = [
    Variable("source", "string",
             "Primary source catalog for the record's metadata (highest-priority "
             "contributing source)", _MERGE, group=_IDENTITY,
             allowed_values="openalex, istex, bibcnrs, scispace, grey, teaching, unfccc, oecd"),
    Variable("source_id", "string",
             "Identifier in the primary source (e.g. OpenAlex work ID)", _MERGE,
             group=_IDENTITY),
    Variable("doi", "string, nullable",
             "Digital Object Identifier, when available", _MERGE,
             group=_IDENTITY),
    Variable("title", "string", "Title of the work", _MERGE, group=_BIBLIO),
    Variable("first_author", "string, nullable", "First author name", _MERGE,
             group=_BIBLIO),
    Variable("all_authors", "string, nullable",
             "Full author list, separator-joined", _MERGE, group=_BIBLIO),
    Variable("year", "integer", "Publication year", _MERGE, group=_BIBLIO),
    Variable("journal", "string, nullable",
             "Publication venue (journal, publisher, or repository)", _MERGE,
             group=_BIBLIO),
    Variable("language", "string, nullable",
             "Language code (ISO 639-1), detected and normalised", _ENRICH,
             group=_BIBLIO),
    Variable("keywords", "string, nullable",
             "Keywords, semicolon-separated", _MERGE, group=_BIBLIO),
    Variable("categories", "string, nullable",
             "Subject categories / concepts from the source catalog", _MERGE,
             group=_BIBLIO),
    Variable("cited_by_count", "integer",
             "Citation count (OpenAlex, as of the collection date)", _MERGE,
             group=_BIBLIO),
    Variable("affiliations", "string, nullable",
             "Author affiliations, when available", _MERGE, group=_BIBLIO),
    Variable("from_openalex", "boolean", "Provenance flag: found in OpenAlex",
             _MERGE, group=_PROV, allowed_values=_BOOL01),
    Variable("from_istex", "boolean", "Provenance flag: found in ISTEX",
             _MERGE, group=_PROV, allowed_values=_BOOL01),
    Variable("from_bibcnrs", "boolean", "Provenance flag: found in bibCNRS",
             _MERGE, group=_PROV, allowed_values=_BOOL01),
    Variable("from_scispace", "boolean", "Provenance flag: found via SciSpace",
             _MERGE, group=_PROV, allowed_values=_BOOL01),
    Variable("from_grey", "boolean",
             "Provenance flag: grey-literature source", _MERGE, group=_PROV,
             allowed_values=_BOOL01),
    Variable("from_teaching", "boolean",
             "Provenance flag: teaching canon (syllabi)", _MERGE, group=_PROV,
             allowed_values=_BOOL01),
    Variable("from_unfccc", "boolean",
             "Provenance flag: curated UNFCCC key document", _KEYDOCS,
             required=False, group=_PROV, allowed_values=_BOOL01),
    Variable("from_oecd", "boolean",
             "Provenance flag: curated OECD key document", _KEYDOCS,
             required=False, group=_PROV, allowed_values=_BOOL01),
    Variable("abstract_provenance", "string, nullable",
             "Provenance of the abstract text for curated key documents: "
             "`curated`, `reconstructed:lead`, or `reconstructed:exec_summary`; "
             "empty elsewhere", _KEYDOCS, required=False, group=_PROV,
             allowed_values="curated, reconstructed:lead, "
             "reconstructed:exec_summary, empty"),
    Variable("keywords_provenance", "string, nullable",
             "Provenance of the keywords for curated key documents: `extracted` "
             "or `generated:lexicon`; empty elsewhere", _KEYDOCS,
             required=False, group=_PROV,
             allowed_values="extracted, generated:lexicon, empty"),
    Variable("language_provenance", "string, nullable",
             "How the language code was obtained: `source` (carried by the "
             "source catalog), `openalex` (backfilled from the OpenAlex API), "
             "or `detected:langdetect` (inferred from title and abstract); "
             "empty where no language could be established", _ENRICH,
             required=False, group=_PROV,
             allowed_values="source, openalex, detected:langdetect, empty"),
    Variable("source_count", "integer",
             "Number of sources that contributed the record (sum of the "
             "provenance flags)", _MERGE, group=_PROV,
             allowed_values="1–8"),
    Variable("abstract_status", "string",
             "Status of the (undistributed) abstract: `original`, "
             "`reconstructed` (from OpenAlex inverted index or ISTEX fulltext), "
             "`generated` (LLM summary of an oversized abstract), `too_long`, "
             "or `missing`", _ENRICH, group=_CURATION,
             allowed_values="original, reconstructed, generated, too_long, "
             "missing"),
    Variable("near_duplicate_group", "integer, nullable",
             "Group identifier for near-identical content published under "
             "several DOIs; null for ungrouped works", _FILTER,
             group=_CURATION),
    Variable("semantic_outlier_dist", "float, nullable",
             "Distance to the corpus embedding centroid, computed for the "
             "semantic-outlier flag", _FILTER, required=False,
             group=_CURATION),
    Variable("in_v1", "boolean",
             "Version tracking: work present in the v1.0 submission corpus",
             _FILTER, required=False, group=_CURATION, allowed_values=_BOOLTF),
    Variable("is_flagged", "boolean",
             "Any quality flag raised; the refined subset is "
             "`df[~df['is_flagged'] | df['is_protected']]`", _FILTER,
             group=_CURATION, allowed_values=_BOOLTF),
    Variable("flag_reason", "string",
             "Comma-separated list of raised quality flags "
             f"({', '.join(FLAG_COLUMNS)}); empty when unflagged", _FILTER,
             group=_CURATION,
             allowed_values="comma-joined subset of the six flag names, or "
             "empty"),
    Variable("is_protected", "boolean",
             "Protection from removal (key papers kept despite flags)", _FILTER,
             group=_CURATION, allowed_values=_BOOLTF),
    Variable("protection_reason", "string, nullable",
             "Why the work is protected (citation count, seed list, ...)",
             _FILTER, required=False, group=_CURATION),
]


# A description is Markdown: prose with backtick code spans. It is rendered
# into two markup languages, and each has characters it reads as markup rather
# than as text (ticket 0325 — an unescaped `~` in the LaTeX table silently
# turned the published reconstruction recipe into its own complement).
#
# The LaTeX mapping mirrors pandoc's, so a description sets the same whether it
# reaches the PDF through this emitter's raw-LaTeX block or through Quarto's
# own Markdown pipeline; `tests/test_rendered_table_fidelity.py` pins that.
_LATEX_TEXT_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "$": r"\$",
    "{": r"\{", "}": r"\}",
    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    "|": r"\textbar{}", "<": r"\textless{}", ">": r"\textgreater{}",
}
# In a code span an apostrophe must stay upright, not curl into a quote.
_LATEX_CODE_SPECIALS = _LATEX_TEXT_SPECIALS | {"'": r"\textquotesingle{}"}

# Translation is single-pass: a sequential replace loop would re-escape the
# braces and backslashes its own earlier substitutions introduced.
_LATEX_TEXT = str.maketrans(_LATEX_TEXT_SPECIALS)
_LATEX_CODE = str.maketrans(_LATEX_CODE_SPECIALS)


def describe(v: Variable) -> str:
    """The variable's description as published, in Markdown."""
    if v.required:
        return v.description
    return v.description + \
        " (absent from corpus builds predating this pipeline stage)"


def latex_inline(text: str) -> str:
    """Markdown description → LaTeX cell content.

    Backtick spans set as ``\\texttt``; prose and code are escaped with their
    respective specials.

    Raw LaTeX also bypasses pandoc's smart punctuation, so prose is given the
    one substitution the contract exercises — the rendered-fidelity test fails
    on any further one rather than letting the table drift typographically
    from the prose around it.
    """
    parts = text.split("`")
    if len(parts) % 2 == 0:
        raise ValueError(f"unbalanced backtick in description: {text!r}")
    return "".join(
        rf"\texttt{{{part.translate(_LATEX_CODE)}}}" if i % 2
        else part.translate(_LATEX_TEXT).replace("...", r"\ldots{}")
        for i, part in enumerate(parts)
    )


def markdown_cell(text: str) -> str:
    """Text → a Markdown pipe-table cell.

    A raw ``|`` ends the cell, so the codebook's recipe used to be published
    cut in half. Escaping it is valid inside a code span too (GFM tables).
    """
    return text.replace("|", r"\|")


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
    r"""Render the contract as a cross-referenceable LaTeX table.

    Emitted as a Quarto div (#tbl-variables) wrapping raw LaTeX: pipe tables
    cannot draw the horizontal rules that separate the four logical groups,
    so the paper's PDF build gets a longtable with \midrule at each group
    boundary. Group names appear in the caption only (author decision,
    2026-07-24).

    Raw LaTeX means pandoc never sees these cells, so this function owns their
    escaping — see ``latex_inline``.
    """
    lines = [
        "::: {#tbl-variables}",
        "```{=latex}",
        r"\begin{longtable}{@{}l l p{8.2cm}@{}}",
        r"\toprule",
        r"Variable & Type & Description \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"Variable & Type & Description \\",
        r"\midrule",
        r"\endhead",
    ]
    prev_group = None
    groups: list[str] = []
    for v in DEPOSIT_VARIABLES:
        if prev_group is not None and v.group != prev_group:
            lines.append(r"\midrule")
        if v.group != prev_group:
            groups.append(v.group.lower())
        prev_group = v.group
        lines.append(
            rf"\texttt{{{v.name.translate(_LATEX_CODE)}}}"
            rf" & {latex_inline(v.type)}"
            rf" & {latex_inline(describe(v))} \\")
    lines += [
        r"\bottomrule",
        r"\end{longtable}",
        "```",
        "",
        "Variables of `climate_finance_corpus.csv`. Horizontal rules separate "
        "the four logical groups: " + ", ".join(groups) + ". Generated from "
        "the deposit column contract (`scripts/_deposit_variables.py`); "
        "per-source provenance, allowed values, and missingness are in the "
        "deposited codebook.",
        ":::",
    ]
    return "\n".join(lines) + "\n"


def compute_missingness(df) -> dict[str, float]:
    """Fraction of missing values (NaN or empty string) per contract column.

    Only columns present in ``df`` and declared in the contract are reported —
    measured from the real data, never hand-curated.
    """
    declared = set(contract_names())
    out: dict[str, float] = {}
    for col in df.columns:
        if col not in declared:
            continue
        s = df[col]
        missing = s.isna() | (s.astype(str).str.strip() == "")
        out[col] = float(missing.mean())
    return out


def render_codebook(missingness: dict[str, float], n_rows: int) -> str:
    """Render the formal data dictionary (codebook) as standalone Markdown.

    One section per logical group; per column: type, allowed values,
    measured missingness, description. Ships in the Zenodo package
    (coordinated with ticket 0280) and answers remark R1-19.
    """
    lines = [
        "# Codebook — climate_finance_corpus.csv",
        "",
        "Formal data dictionary for the deposited corpus file. Columns are "
        "organised in four logical groups. Missingness (share of empty or "
        f"null cells) is measured on the shipped data ({n_rows} rows) by "
        "`scripts/figures/export_codebook.py`; `n/a` marks optional columns "
        "absent from this build. Generated from the deposit column contract "
        "(`scripts/_deposit_variables.py`).",
    ]
    for group in GROUPS:
        members = [v for v in DEPOSIT_VARIABLES if v.group == group]
        if not members:
            continue
        lines += [
            "",
            f"## {group}",
            "",
            "| Variable | Type | Allowed values | Missing | Description |",
            "|:------|:----|:------------|------:|:-------------------------|",
        ]
        for v in members:
            if v.name in missingness:
                miss = f"{100 * missingness[v.name]:.1f}%"
            else:
                miss = "n/a"
            allowed = v.allowed_values or "free"
            cells = [f"`{v.name}`", v.type, allowed, miss, v.description]
            lines.append("| " + " | ".join(markdown_cell(c) for c in cells) + " |")
    return "\n".join(lines) + "\n"
