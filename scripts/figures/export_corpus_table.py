"""Export corpus composition table by source.

Produces:
- content/tables/tab_corpus_sources.csv: detailed stats per source
- content/tables/tab_corpus_sources.md: Quarto-includable markdown table

Shows for each source: query description, records before/after refinement,
non-English share, journal-article share, DOI coverage, reference coverage,
and abstract availability.
"""

import os

import pandas as pd
import yaml
from _markdown_table import markdown_text_cell
from pipeline_loaders import load_refined_works
from script_io_args import parse_io_args, validate_io
from utils import BASE_DIR, CATALOGS_DIR, get_logger, save_csv

log = get_logger("export_corpus_table")

CORE_THRESHOLD = 50


def _openalex_language_count() -> int:
    """Target languages the Tier-1 taxonomy declares (ticket 0356).

    Same source of truth as the paper's language sentence
    (`tests/test_retrieval_protocol.py::target_languages`): distinct non-null
    `term_languages` tags. A hand-typed "9 languages" shipped in the deposit
    against a config declaring eight; deriving the count is what keeps table,
    paper, and config on one number. The ISTEX and bibCNRS descriptions below
    stay literal — they describe manual pulls with no config source to derive
    from.
    """
    path = os.path.join(BASE_DIR, "config", "openalex_queries.yaml")
    with open(path, encoding="utf-8") as fh:
        tags = yaml.safe_load(fh)["term_languages"]
    return len({lang for lang in tags.values() if lang})


# Source metadata: label and query description from catalog_*.py scripts
SOURCE_META = {
    "openalex": {
        "label": "OpenAlex",
        "query": f"4-tier keyword taxonomy, {_openalex_language_count()} languages"
                 " (default.search on title+abstract+fulltext)",
    },
    "istex": {
        "label": "ISTEX",
        "query": '"climate finance" OR "finance climat*" on French institutional archive',
    },
    "bibcnrs": {
        "label": "bibCNRS",
        "query": "FR, ZH, JA, DE queries via Gale/Wanfang/NewsBank (CNRS legacy portal)",
    },
    "scispace": {
        "label": "SciSpace",
        "query": "AI-curated systematic review (RIS + CSV exports)",
    },
    # Display label follows Table 1 of the data paper, which ticket 0334
    # renamed; the `grey` key, `from_grey` flag, and `grey_sources.yaml` are
    # code identifiers and keep the old name. Pinned by
    # tests/test_datapaper_claims.py (ticket 0565).
    "grey": {
        "label": "Institutional reports",
        "query": "World Bank Open Knowledge Repository API + curated YAML (OECD, UNFCCC, CPI)",
    },
    "teaching": {
        "label": "Teaching canon",
        "query": "Syllabi from 15 programmes (doctoral, MBA, professional, MOOC)",
    },
    # Curated key-documents layer (ticket 0288, corpus v2)
    "unfccc": {
        "label": "UNFCCC key documents",
        "query": "Curated COP/CMP/CMA decisions, SCF Biennial Assessments, fund"
                 " reports, INC records, submissions, ENB summaries"
                 " (config/unfccc_sources.yaml)",
    },
    "oecd": {
        "label": "OECD DAC key documents",
        "query": "Curated non-DOI founding documents: Rio-marker Statistical"
                 " Reporting Directives, pre-DOI Development Co-operation"
                 " Reports, early DAC/WP-STAT/ENVIRONET"
                 " (config/oecd_dac_sources.yaml)",
    },
}

PRIMARY_SOURCES = list(SOURCE_META.keys())


def sources_present(unified_cols, refined_cols) -> list[str]:
    """PRIMARY_SOURCES whose from_* column exists in either frame.

    A source absent from both (e.g. unfccc/oecd on pre-v2 data) is skipped so
    Phase-2 tables stay byte-stable until the corpus that carries the layer
    is actually built (ticket 0288).
    """
    cols = set(unified_cols) | set(refined_cols)
    return [s for s in PRIMARY_SOURCES if f"from_{s}" in cols]

# Authored Markdown, deliberately unescaped: the caption is a paragraph below
# the table, not a row, so its backticks and emphasis are intentional markup and
# a `|` here would end no cell. Its interpolated values are all `int`-formatted
# counts, so none can carry one either (ticket 0370).
def build_caption(
    raw_multi: int,
    raw_extra: int,
    raw_triple: int,
    refined_multi: int,
    refined_extra: int,
    refined_triple: int,
) -> str:
    """Caption reporting the union/sum discrepancy in both count columns.

    The source rows count provenance *memberships*, the TOTAL row counts
    distinct works, so the columns sum above their total. Ticket 0327: the
    submitted table left that unstated, and the refined column's 763 extra
    memberships did not match the 738 multi-source works quoted in section 2.2.
    The works carrying three provenances close that gap, and each column gets
    its own count rather than one figure standing for both populations. Every
    number is measured, so the caption cannot drift from the table.
    """
    return (
        ": Corpus sources. *Raw*: records with `from_*` provenance flag before"
        " filtering (a record in multiple sources is counted once per source)."
        " *Refined*: after six-flag quality filtering."
        " *Unique*: found only in that source (`source_count = 1`)."
        " The **TOTAL** row is the deduplicated union of works, not the column"
        f" sum: {raw_multi:,} raw records and {refined_multi:,} refined works"
        " carry more than one provenance flag, which puts the source rows"
        f" {raw_extra:,} and {refined_extra:,} memberships above their totals"
        f" ({raw_triple:,} and {refined_triple:,} of them carry three)."
        " *%non-EN*: share of non-English works."
        " *%DOI*, *%Abstract*, *%Refs*: metadata completeness among refined"
        " records. {#tbl-quality}"
    )


def membership_overlap(frame: pd.DataFrame, from_cols: list[str]) -> tuple[int, int, int]:
    """(works with 2+ provenances, extra memberships, works with 3+)."""
    per_work = frame[from_cols].fillna(0).astype(int).sum(axis=1)
    return (
        int((per_work >= 2).sum()),
        int((per_work - 1).clip(lower=0).sum()),
        int((per_work >= 3).sum()),
    )


def _from_cols(frame: pd.DataFrame, sources: list[str]) -> list[str]:
    """`from_*` columns actually present in `frame`, for the given sources."""
    return [f"from_{s}" for s in sources if f"from_{s}" in frame.columns]


def _write_md_table(summary: pd.DataFrame, path: str, caption: str) -> None:
    """Write a Quarto-includable markdown table with selected columns."""
    cols = ["Source", "Raw", "Refined", "Unique", "%non-EN", "%DOI", "%Abstract", "%Refs"]
    lines = [
        "| Source | Raw | Refined | Unique | %non-EN | %DOI | %Abstract | %Refs |",
        "|:-------|----:|--------:|-------:|--------:|-----:|----------:|------:|",
    ]
    # Every cell is escaped, not just `Source`: the point of the helper is that
    # no emitter has to know which column happens to carry a `|` today (tickets
    # 0325, 0339, 0370). Escaping runs *before* the TOTAL row's emphasis markers
    # are added, so the `**` stay markup and only the value is treated as text.
    # A missing value is blanked once, for every column, before anything is
    # formatted. `row.get(c, "")` does not cover it: a source that refines to
    # zero works reaches here with the four percentage keys *present* and
    # holding NaN, so the default never fires and the cell renders the string
    # `nan` (ticket 0375). The int branch keeps no `pd.notna` guard of its own —
    # one blanking rule for all eight columns is what stops the next column
    # added here from inheriting the same hole.
    for _, row in summary.iterrows():
        is_total = "TOTAL" in str(row["Source"])
        vals = []
        for c in cols:
            v = row.get(c, "")
            if pd.isna(v):
                v = ""
            elif c in ("Raw", "Refined", "Unique"):
                v = f"{int(v):,}"
            cell = markdown_text_cell(v)
            # An empty TOTAL cell must not become a bare `****`, which pandoc
            # reads as two literal asterisks rather than emphasis.
            vals.append(f"**{cell}**" if is_total and cell else cell)
        lines.append("| " + " | ".join(vals) + " |")
    lines.append("")
    lines.append(caption)
    lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))


def main():
    # The .md path is derived from --output, so being handed the .md (a bare
    # $@ under the grouped Make target) would write the CSV to the .md path and
    # leave the tracked CSV stale. Refuse instead of half-building.
    if not _output_csv.endswith(".csv"):
        raise ValueError(
            f"--output must name the .csv member, got {_output_csv!r}; "
            "the .md is derived from it"
        )

    # Load refined corpus (after filtering). load_refined_works() coerces
    # year to numeric and cited_by_count to numeric-filled-0 — the same
    # coercion this script did inline before the loader migration.
    df = load_refined_works()
    df["doi_lower"] = df["doi"].str.lower().str.strip()
    df["has_doi"] = df["doi_lower"].apply(
        lambda x: bool(x) and str(x) not in ("", "nan", "none")
    )
    df["is_english"] = df["language"].str.lower().str.startswith("en", na=True)
    df["has_journal"] = df["journal"].notna() & (df["journal"].str.strip() != "")

    # Abstract availability
    abs_s = df["abstract"].fillna("").astype(str).str.strip()
    df["has_abstract"] = (abs_s.str.len() > 10) & (abs_s != "nan")

    log.info("Loaded %d refined works", len(df))

    # Load unified corpus (before filtering) for raw counts
    # Must include from_* columns — usecols=["source"] dropped them (#251 bug)
    unified_path = os.path.join(CATALOGS_DIR, "unified_works.csv")
    unified_cols = pd.read_csv(unified_path, nrows=0).columns.tolist()
    use = [c for c in unified_cols if c.startswith("from_") or c in ("source", "source_count")]
    unified = pd.read_csv(unified_path, usecols=use)
    log.info("Loaded %d unified works from %s", len(unified), unified_path)

    # Load citations for reference coverage
    cit_path = os.path.join(CATALOGS_DIR, "citations.csv")
    cit = pd.read_csv(cit_path, usecols=["source_doi"], low_memory=False)
    source_dois = set(cit["source_doi"].str.lower().str.strip().dropna()) - {
        "", "nan", "none",
    }
    df["has_refs"] = df["doi_lower"].isin(source_dois)
    log.info("Loaded %d citation rows", len(cit))

    # Compute per-source statistics
    present = sources_present(unified.columns, df.columns)
    rows = []
    for src in present:
        from_col = f"from_{src}"
        mask_u = unified[from_col] == 1 if from_col in unified.columns else unified["source"].str.contains(src, na=False)
        mask_r = df[from_col] == 1 if from_col in df.columns else df["source"].str.contains(src, na=False)
        sub = df[mask_r]
        meta = SOURCE_META[src]
        n_raw = int(mask_u.sum())
        n_refined = len(sub)
        n_unique = int(((df["source_count"] == 1) & (df[from_col] == 1)).sum()) if from_col in df.columns else 0
        if n_refined == 0:
            rows.append({
                "Source": meta["label"], "Query": meta["query"],
                "Raw": n_raw, "Refined": n_refined, "Unique": n_unique,
            })
            continue
        rows.append({
            "Source": meta["label"],
            "Query": meta["query"],
            "Raw": n_raw,
            "Refined": n_refined,
            "Unique": n_unique,
            "%non-EN": f"{(~sub['is_english']).mean() * 100:.0f}%",
            "%Journal": f"{sub['has_journal'].mean() * 100:.0f}%",
            "%DOI": f"{sub['has_doi'].mean() * 100:.0f}%",
            "%Refs": f"{sub['has_refs'].mean() * 100:.0f}%",
            "%Abstract": f"{sub['has_abstract'].mean() * 100:.0f}%",
        })

    # Totals row (deduplicated)
    n_unique_total = int((df["source_count"] == 1).sum()) if "source_count" in df.columns else 0
    rows.append({
        "Source": "TOTAL",
        "Query": "",
        "Raw": len(unified),
        "Refined": len(df),
        "Unique": n_unique_total,
        "%non-EN": f"{(~df['is_english']).mean() * 100:.0f}%",
        "%Journal": f"{df['has_journal'].mean() * 100:.0f}%",
        "%DOI": f"{df['has_doi'].mean() * 100:.0f}%",
        "%Refs": f"{df['has_refs'].mean() * 100:.0f}%",
        "%Abstract": f"{df['has_abstract'].mean() * 100:.0f}%",
    })

    summary = pd.DataFrame(rows)

    # Save CSV (full detail)
    csv_path = _output_csv
    save_csv(summary, csv_path)

    # Provenance overlap: what separates each column's sum from its TOTAL.
    raw_multi, raw_extra, raw_triple = membership_overlap(
        unified, _from_cols(unified, present)
    )
    ref_multi, ref_extra, ref_triple = membership_overlap(df, _from_cols(df, present))
    caption = build_caption(
        raw_multi=raw_multi,
        raw_extra=raw_extra,
        raw_triple=raw_triple,
        refined_multi=ref_multi,
        refined_extra=ref_extra,
        refined_triple=ref_triple,
    )

    # Save markdown table (included by data-paper.qmd and _includes/tab_corpus_sources.md)
    md_path = os.path.splitext(csv_path)[0] + ".md"
    _write_md_table(summary, md_path, caption)
    log.info("Wrote %s", md_path)


# Default output path (overridden by --output)
_output_csv = os.path.join(BASE_DIR, "deliverables", "_shared", "tables", "tab_corpus_sources.csv")

if __name__ == "__main__":
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    _output_csv = io_args.output
    main()
