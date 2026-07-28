"""Export the deposited removal-ablation table (ticket 0337).

All four external reviewers asked what the six-flag filter removes, stratum
by stratum: does it erase the grey, non-English, and poorly-indexed records
the corpus claims to add? This table answers with numbers. It is computed
from ``extended_works.csv`` — the pre-removal catalog that carries every
flag on every work — never from ``refined_works.csv``, which would be
circular and report zeros (ticket 0337 invariant).

One row per stratum: works in the stratum, works flagged by any of the five
deployed flags, works rescued by a protection criterion, works removed, and
the removal share. The ``source`` axis is non-exclusive (a work found by two
sources appears in both rows); the ``language``, ``period``, ``doi``, and
``citation_decile`` axes are complete partitions of the corpus, so their
``removed`` columns each sum to the corpus total — the invariant
``tests/test_filter_ablation.py`` pins.

Usage:
    uv run python scripts/figures/export_filter_ablation.py \
        --output deliverables/_shared/tables/tab_filter_ablation.csv
"""

import os

import pandas as pd
from script_io_args import parse_io_args, validate_io
from utils import CATALOGS_DIR, get_logger, save_csv

log = get_logger("export_filter_ablation")

# The five flags deployed in corpus v2. Flag 5 (semantic_outlier) contributed
# no column to this corpus build and is deliberately absent.
FLAG_COLUMNS = [
    "missing_metadata", "no_abstract_irrelevant", "title_blacklist",
    "citation_isolated_old", "llm_irrelevant",
]

SOURCES = [
    ("openalex", "from_openalex"), ("istex", "from_istex"),
    ("bibcnrs", "from_bibcnrs"), ("scispace", "from_scispace"),
    ("grey", "from_grey"), ("teaching", "from_teaching"),
    ("unfccc", "from_unfccc"), ("oecd", "from_oecd"),
]

PERIODS = [
    ("pre-1990", lambda y: y < 1990),
    ("1990-2006", lambda y: (y >= 1990) & (y <= 2006)),
    ("2007-2014", lambda y: (y >= 2007) & (y <= 2014)),
    ("2015 on", lambda y: y >= 2015),
    ("no year", lambda y: y.isna()),
]


def _strata(df: pd.DataFrame):
    """Yield (axis, stratum, boolean mask) over every reported stratum."""
    yield "corpus", "all", pd.Series(True, index=df.index)

    for name, col in SOURCES:
        yield "source", name, df[col].fillna(0).astype(bool)

    lang = df["language"].fillna("unknown")
    yield "language", "English", lang.eq("en")
    yield "language", "non-English", ~lang.eq("en") & ~lang.eq("unknown")
    yield "language", "unknown", lang.eq("unknown")

    year = pd.to_numeric(df["year"], errors="coerce")
    for name, rule in PERIODS:
        yield "period", name, rule(year)

    has_doi = df["doi_norm"].fillna("").ne("")
    yield "doi", "has DOI", has_doi
    yield "doi", "no DOI", ~has_doi

    # Deciles of citation count, ties broken by rank so the bins stay equal
    # despite the mass of zero-citation works.
    cites = pd.to_numeric(df["cited_by_count"], errors="coerce").fillna(0)
    decile = pd.qcut(cites.rank(method="first"), 10, labels=range(1, 11))
    for d in range(1, 11):
        yield "citation_decile", str(d), decile.eq(d)


def build_table(df: pd.DataFrame) -> pd.DataFrame:
    flagged = df[FLAG_COLUMNS].fillna(False).any(axis=1)
    removed = df["action"].eq("would_remove")
    rescued = flagged & ~removed

    rows = []
    for axis, stratum, mask in _strata(df):
        n = int(mask.sum())
        rows.append({
            "axis": axis,
            "stratum": stratum,
            "n": n,
            "flagged": int((mask & flagged).sum()),
            "rescued": int((mask & rescued).sum()),
            "removed": int((mask & removed).sum()),
            "removed_pct": round(100 * (mask & removed).sum() / n, 1) if n else 0.0,
        })
    return pd.DataFrame(rows)


def main():
    io_args, _ = parse_io_args()
    source = os.path.join(CATALOGS_DIR, "extended_works.csv")
    validate_io(io_args.output, inputs=[source])
    df = pd.read_csv(source, low_memory=False)
    table = build_table(df)
    total = int(table.loc[table["axis"].eq("corpus"), "removed"].iloc[0])
    log.info("corpus removals: %d over %d works", total, len(df))
    save_csv(table, io_args.output)
    log.info("wrote %s (%d strata)", io_args.output, len(table))


if __name__ == "__main__":
    main()
