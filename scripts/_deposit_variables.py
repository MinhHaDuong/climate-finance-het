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
- tests/test_variables_table.py — pins contract/transform agreement;
- scripts/_deposit_schema.py — renders the machine-readable descriptor
  (`datapackage.json`) whose constraints ``frictionless validate`` enforces
  against the written CSV. It also carries the storage types, allowed values
  and measured missingness that the retired prose codebook used to print
  (ticket 0354).

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
    """One deposited column, described in machine-enforceable terms.

    Every constraint here is published in `datapackage.json` and checked by
    ``frictionless validate`` against the written CSV. Nothing is prose-only:
    the paper's table carries the name and the description, and a reuser who
    needs types, enumerations, ranges or missingness reads the descriptor.

    Three encodings are deliberate, each forced by how the deposit serialises:

    - ``enum`` never carries an empty sentinel. Frictionless treats an empty
      cell as a missing value and skips enum checks on it, so listing ``empty``
      would add a member no cell can match. ``nullable`` says that instead.
    - A boolean field gets no enum. The type already restricts it, and the
      deposit writes ``0``/``1`` for the provenance flags but ``True``/``False``
      for the curation ones; an enum is matched against the parsed value, not
      the token, so declaring either pair would reject the other.
    - ``empty_is_a_value`` marks a column where the empty string *means*
      something rather than being absent — ``flag_reason`` is empty for an
      unflagged work, which is data, not a gap. Such a field publishes
      ``missingValues: []`` so the emptiness is a value and ``required`` still
      holds.

    ``nullable`` is measured, not aspirational: it is true exactly where the
    shipped data has gaps, so ``required`` can be published as a guarantee a
    future build must keep.
    """

    name: str
    dtype: str
    description: str
    source: str
    required: bool = True
    group: str = ""
    nullable: bool = False
    enum: tuple[str, ...] = ()
    minimum: int | None = None
    maximum: int | None = None
    empty_is_a_value: bool = False


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

_MERGE = "source catalogs, merged by catalog_merge.py"
_ENRICH = "enrichment (enrich_* scripts)"
_FILTER = "quality filtering (corpus_filter.py)"
_KEYDOCS = "curated key-documents layer (catalog_keydocs.py, corpus v2)"

DEPOSIT_VARIABLES: list[Variable] = [
    Variable("source", "string",
             "Primary source catalog for the record's metadata", _MERGE,
             group=_IDENTITY,
             enum=("openalex", "istex", "bibcnrs", "scispace", "grey",
                   "teaching", "unfccc", "oecd")),
    Variable("source_id", "string",
             "Identifier in the primary source (e.g. OpenAlex work ID)", _MERGE,
             group=_IDENTITY, nullable=True),
    Variable("doi", "string",
             "Digital Object Identifier, when available", _MERGE,
             group=_IDENTITY, nullable=True),
    Variable("title", "string", "Title of the work", _MERGE, group=_BIBLIO,
             nullable=True),
    Variable("first_author", "string", "First author name", _MERGE,
             group=_BIBLIO, nullable=True),
    Variable("all_authors", "string",
             "Full author list, separator-joined", _MERGE, group=_BIBLIO,
             nullable=True),
    Variable("year", "integer", "Publication year", _MERGE, group=_BIBLIO,
             nullable=True),
    Variable("journal", "string",
             "Publication venue (journal, publisher, or repository)", _MERGE,
             group=_BIBLIO, nullable=True),
    Variable("language", "string",
             "Language code (ISO 639-1), detected and normalised", _ENRICH,
             group=_BIBLIO, nullable=True),
    Variable("keywords", "string",
             "Keywords, semicolon-separated", _MERGE, group=_BIBLIO,
             nullable=True),
    Variable("categories", "string",
             "Subject categories / concepts from the source catalog", _MERGE,
             group=_BIBLIO, nullable=True),
    Variable("cited_by_count", "integer",
             "Citation count (OpenAlex, as of the collection date)", _MERGE,
             group=_BIBLIO, nullable=True),
    Variable("affiliations", "string",
             "Author affiliations, when available", _MERGE, group=_BIBLIO,
             nullable=True),
    Variable("from_openalex", "boolean", "Provenance flag: found in OpenAlex",
             _MERGE, group=_PROV),
    Variable("from_istex", "boolean", "Provenance flag: found in ISTEX",
             _MERGE, group=_PROV),
    Variable("from_bibcnrs", "boolean", "Provenance flag: found in bibCNRS",
             _MERGE, group=_PROV),
    Variable("from_scispace", "boolean", "Provenance flag: found via SciSpace",
             _MERGE, group=_PROV),
    Variable("from_grey", "boolean",
             "Provenance flag: institutional reports (curated seed + World Bank)",
             _MERGE, group=_PROV),
    Variable("from_teaching", "boolean",
             "Provenance flag: teaching canon (syllabi)", _MERGE, group=_PROV),
    Variable("from_unfccc", "boolean",
             "Provenance flag: curated UNFCCC key document", _KEYDOCS,
             required=False, group=_PROV),
    Variable("from_oecd", "boolean",
             "Provenance flag: curated OECD key document", _KEYDOCS,
             required=False, group=_PROV),
    Variable("abstract_provenance", "string",
             "Provenance of the abstract text, for curated key documents only",
             _KEYDOCS, required=False, group=_PROV, nullable=True,
             enum=("curated", "reconstructed:lead",
                   "reconstructed:exec_summary")),
    Variable("keywords_provenance", "string",
             "Provenance of the keywords, for curated key documents only",
             _KEYDOCS, required=False, group=_PROV, nullable=True,
             enum=("extracted", "generated:lexicon")),
    Variable("language_provenance", "string",
             "How the language code was obtained: carried by the source "
             "catalog, backfilled from OpenAlex, or inferred from title and "
             "abstract", _ENRICH,
             required=False, group=_PROV, nullable=True,
             enum=("source", "openalex", "detected:langdetect")),
    Variable("source_count", "integer",
             "Number of sources that contributed the record", _MERGE,
             group=_PROV,
             minimum=1, maximum=8),
    Variable("abstract_status", "string",
             "Whether the undistributed abstract was original, reconstructed "
             "from an inverted index or fulltext, LLM-summarised, oversized, "
             "or missing", _ENRICH, group=_CURATION,
             enum=("original", "reconstructed", "generated", "too_long",
                   "missing")),
    Variable("near_duplicate_group", "integer",
             "Group identifier for near-identical content published under "
             "several DOIs", _FILTER,
             group=_CURATION, nullable=True),
    Variable("semantic_outlier_dist", "number",
             "Distance to the corpus embedding centroid", _FILTER,
             required=False,
             group=_CURATION, nullable=True),
    Variable("in_v1", "boolean",
             "Version tracking: work present in the v1.0 submission corpus",
             _FILTER, required=False, group=_CURATION),
    Variable("is_flagged", "boolean",
             "Any quality flag raised; the refined subset is "
             "`df[~df['is_flagged'] | df['is_protected']]`", _FILTER,
             group=_CURATION),
    Variable("flag_reason", "string",
             "Comma-separated list of raised quality flags "
             f"({', '.join(FLAG_COLUMNS)}); empty when unflagged", _FILTER,
             group=_CURATION,
             empty_is_a_value=True),
    Variable("is_protected", "boolean",
             "Protection from removal (key papers kept despite flags)", _FILTER,
             group=_CURATION),
    Variable("protection_reason", "string",
             "Why the work is protected (citation count, seed list, ...)",
             _FILTER, required=False, group=_CURATION, nullable=True),
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

# The Markdown side of the same split moved to `_markdown_table` when the venue
# emitters turned out to need it too (ticket 0339); it is imported above.


OPTIONAL_MARK = "†"


def describe(v: Variable) -> str:
    """The variable's description as published, in Markdown.

    Optionality is marked on the variable name, not spelled out per row. Eight
    of the 33 variables are optional, so the old per-row sentence spent 64
    words — a quarter of all description text in the table — repeating one
    fact eight times. The caption states it once and the name carries a dagger
    (ticket 0332, word budget).
    """
    return v.description


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
        r"\begin{longtable}{@{}l p{10.4cm}@{}}",
        r"\toprule",
        r"Variable & Description \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"Variable & Description \\",
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
        mark = "" if v.required else OPTIONAL_MARK
        lines.append(
            rf"\texttt{{{v.name.translate(_LATEX_CODE)}}}{mark}"
            rf" & {latex_inline(describe(v))} \\")
    lines += [
        r"\bottomrule",
        r"\end{longtable}",
        "```",
        "",
        "Variables of `climate_finance_corpus.csv`. Horizontal rules separate "
        "the four logical groups: " + ", ".join(groups) + ". " + OPTIONAL_MARK +
        " marks a variable absent from corpus builds predating its pipeline "
        "stage. Generated from the deposit column contract "
        "(`scripts/_deposit_variables.py`); storage types, allowed values, "
        "ranges and measured missingness are in the deposited "
        "`datapackage.json`.",
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
