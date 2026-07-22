#!/usr/bin/env python3
"""Merge all source catalogs into a unified, deduplicated catalog.

Reads the 6 declared per-source catalogs from data/catalogs/ and produces:
  data/catalogs/unified_works.csv

Only these files are loaded (matching dvc.yaml catalog_merge deps):
  bibcnrs, istex, openalex, grey, teaching, scispace

Deduplication: DOI-based (primary), then normalized title+year match (fallback).
Priority for field values follows SOURCE_PRIORITY list.

Usage:
    python scripts/catalog_merge.py
"""

import argparse
import os

import pandas as pd
import yaml
from pipeline_text import normalize_text
from utils import (
    BASE_DIR,
    CATALOGS_DIR,
    FROM_COLS,
    WORKS_COLUMNS,
    get_logger,
    make_run_id,
    normalize_doi,
    normalize_title,
    save_csv,
    save_run_report,
)

log = get_logger("catalog_merge")

SOURCE_PRIORITY = ["openalex", "scopus", "istex", "bibcnrs", "scispace", "grey", "teaching"]


SOURCE_RANK = {s: i for i, s in enumerate(SOURCE_PRIORITY)}


def _load_and_tag(path):
    """Load a per-source catalog CSV and normalise the source column.

    The canonical source name is derived from the filename (e.g.
    ``scispace_works.csv`` → ``"scispace"``), overriding whatever the CSV
    contains.  This prevents silent mismatches when the CSV's source column
    has a legacy typo (e.g. ``"scispsace"``).
    """
    name = os.path.basename(path).replace("_works.csv", "")
    df = pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)
    df["source"] = name
    log.info("  %s: %d rows", name, len(df))
    return df


def _dedup_vectorized(df, group_col):
    """Vectorized dedup: sort by priority, pick first non-empty per group.

    1. Add a priority rank column and sort so highest-priority rows come first.
    2. Replace empty strings with NaN so groupby().first() skips them.
    3. Use first() for text columns, max() for cited_by_count, any() for from_*.
    """
    df = df.copy()
    df["_rank"] = df["source"].map(SOURCE_RANK).fillna(99)
    df = df.sort_values(["_rank", group_col])

    # cited_by_count as numeric for max aggregation
    df["_cbc_num"] = pd.to_numeric(df["cited_by_count"], errors="coerce")

    # Replace empty strings with NaN so first() skips them
    text_cols = [c for c in WORKS_COLUMNS if c != "cited_by_count"]
    df[text_cols] = df[text_cols].replace("", pd.NA)

    # Build aggregation: first() for text, max() for citations, max() for from_*
    agg = {c: "first" for c in text_cols}
    agg["_cbc_num"] = "max"
    for col in FROM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            agg[col] = "max"

    result = df.groupby(group_col, sort=False).agg(agg)

    # Restore cited_by_count from numeric max
    result["cited_by_count"] = result["_cbc_num"].apply(
        lambda x: str(int(x)) if pd.notna(x) else "")
    result = result.drop(columns=["_cbc_num"])

    # Fill NaN back to empty string
    result[text_cols] = result[text_cols].fillna("")

    # Ensure from_* columns exist and are int
    for col in FROM_COLS:
        if col not in result.columns:
            result[col] = 0
        else:
            result[col] = result[col].astype(int)

    return result.reset_index(drop=True)


def catalog_files_from_dvc():
    """Read catalog_merge deps from dvc.yaml — single source of truth."""
    dvc_path = os.path.join(BASE_DIR, "dvc.yaml")
    with open(dvc_path) as f:
        dvc = yaml.safe_load(f)
    deps = dvc["stages"]["catalog_merge"]["deps"]
    return [d for d in deps if d.endswith("_works.csv")]


def _dedup_no_doi_records(no_doi: pd.DataFrame) -> tuple[pd.DataFrame | None, int]:
    """Deduplicate records without a DOI using normalized title + year.

    Returns ``(deduplicated DataFrame or None if nothing survives filtering,
    n_titled)`` where ``n_titled`` is the number of records that carried a
    non-empty normalized title and therefore entered the title+year pass
    (records with an empty title are dropped before it). The caller uses
    ``n_titled`` to split the no-DOI removals into ``dropped_empty_title`` and
    ``title_year_duplicates_removed``.
    """
    no_doi = no_doi.copy()
    no_doi["_title_norm"] = no_doi["title"].apply(normalize_title)
    no_doi["_year"] = no_doi["year"].astype(str).str[:4]
    # Drop empty titles
    no_doi = no_doi[no_doi["_title_norm"] != ""]
    n_titled = len(no_doi)
    if n_titled == 0:
        return None, 0
    # Composite key for groupby
    no_doi["_title_year"] = no_doi["_title_norm"] + "|" + no_doi["_year"]
    result = _dedup_vectorized(no_doi, "_title_year")
    log.info("  After title dedup: %d", len(result))
    return result, n_titled


def deduplicate(combined: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Run both dedup passes and return the unified frame plus removal counts.

    Expects ``combined`` to already carry ``_doi_norm`` and the ``from_*``
    provenance columns (set by ``main`` before this call). Pass 1 deduplicates
    records with a DOI on the normalized DOI; pass 2 deduplicates records
    without a DOI on normalized title+year, after dropping empty titles.

    The returned counters give the per-procedure breakdown the data-paper
    referee asked for (ticket 0284, R1-12) and reconcile exactly::

        records_total
            - doi_duplicates_removed
            - title_year_duplicates_removed
            - dropped_empty_title
            == records_unified
    """
    has_doi = combined[combined["_doi_norm"] != ""]
    no_doi = combined[combined["_doi_norm"] == ""]
    log.info("  With DOI: %d, without DOI: %d", len(has_doi), len(no_doi))

    parts = []
    doi_unified = 0
    if len(has_doi) > 0:
        deduped_doi = _dedup_vectorized(has_doi, "_doi_norm")
        doi_unified = len(deduped_doi)
        parts.append(deduped_doi)
        log.info("  After DOI dedup: %d", doi_unified)

    title_unified = 0
    n_titled = 0
    if len(no_doi) > 0:
        deduped_no_doi, n_titled = _dedup_no_doi_records(no_doi)
        if deduped_no_doi is not None:
            title_unified = len(deduped_no_doi)
            parts.append(deduped_no_doi)

    result = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    counters = {
        "records_total": len(combined),
        "records_with_doi": len(has_doi),
        "records_without_doi": len(no_doi),
        "doi_duplicates_removed": len(has_doi) - doi_unified,
        "records_without_doi_titled": n_titled,
        "dropped_empty_title": len(no_doi) - n_titled,
        "title_year_duplicates_removed": n_titled - title_unified,
        "records_unified": len(result),
    }
    return result, counters


def _load_combined(files: list[str]) -> pd.DataFrame | None:
    """Load and concatenate all catalog files.

    Warns about missing files, skips them, and returns None if nothing loaded.
    """
    existing = []
    for f in files:
        if not os.path.exists(f):
            log.warning("missing catalog: %s", f)
        else:
            existing.append(f)

    if not existing:
        log.error("No catalog files found in data/catalogs/")
        return None

    log.info("Loading catalogs:")
    frames = []
    for f in existing:
        try:
            frames.append(_load_and_tag(f))
        except Exception as e:
            log.error("  %s: ERROR - %s", os.path.basename(f), e)

    if not frames:
        log.error("No data loaded.")
        return None

    combined = pd.concat(frames, ignore_index=True)
    log.info("Total records before dedup: %d", len(combined))
    return combined


def main(run_id: str | None = None):
    run_id = run_id or make_run_id()

    # Load only the catalogs declared as deps in dvc.yaml
    catalog_deps = catalog_files_from_dvc()
    files = [os.path.join(BASE_DIR, d) for d in catalog_deps]
    combined = _load_combined(files)
    if combined is None:
        return

    # Normalize text fields — fix encoding artifacts from upstream aggregators
    text_fields = ["title", "abstract", "first_author", "all_authors",
                   "journal", "keywords"]
    for col in text_fields:
        if col in combined.columns:
            combined[col] = combined[col].apply(
                lambda x: normalize_text(x) if x else x)

    # Normalize DOIs
    combined["_doi_norm"] = combined["doi"].apply(normalize_doi)

    # Set from_* provenance columns based on source field
    for col in FROM_COLS:
        src_name = col.replace("from_", "")
        combined[col] = (combined["source"] == src_name).astype(int)

    # Deduplicate (DOI pass, then title+year pass) and capture per-procedure
    # removal counts for the run report.
    result, dedup_counters = deduplicate(combined)

    # Ensure all expected columns
    for col in WORKS_COLUMNS:
        if col not in result.columns:
            result[col] = ""
    for col in FROM_COLS:
        if col not in result.columns:
            result[col] = 0
    result = result[WORKS_COLUMNS + FROM_COLS]

    # Add source_count
    result["source_count"] = result[FROM_COLS].sum(axis=1).astype(int)

    # Sort by year desc, then cited_by_count desc
    result["_year_sort"] = pd.to_numeric(result["year"], errors="coerce")
    result["_cite_sort"] = pd.to_numeric(result["cited_by_count"], errors="coerce")
    result = result.sort_values(["_year_sort", "_cite_sort"],
                                ascending=[False, False])
    result = result.drop(columns=["_year_sort", "_cite_sort"])

    save_csv(result, os.path.join(CATALOGS_DIR, "unified_works.csv"))

    # Persist the per-procedure dedup counts as a pipeline-traceable artifact
    # (ticket 0284): the data-paper referee asks how many duplicates each
    # procedure removes. multi_source_works is added here (post-column build)
    # rather than in deduplicate(), which sees no source_count column.
    report = {**dedup_counters,
              "multi_source_works": int((result["source_count"] > 1).sum())}
    report_path = save_run_report(report, run_id, "catalog_merge")

    log.info("Summary:")
    log.info("  Unified works: %d", len(result))
    log.info("  Multi-source works: %d", (result['source_count'] > 1).sum())
    log.info("  DOI duplicates removed: %d", dedup_counters["doi_duplicates_removed"])
    log.info("  Title+year duplicates removed: %d",
             dedup_counters["title_year_duplicates_removed"])
    log.info("  Dropped empty title: %d", dedup_counters["dropped_empty_title"])
    log.info("  Run report: %s", report_path)
    log.info("  Source distribution:")
    for col in FROM_COLS:
        src_name = col.replace("from_", "")
        count = (result[col] == 1).sum()
        if count:
            log.info("    %s: %d", src_name, count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None,
                        help="Run identifier for the run report filename "
                             "(default: UTC timestamp).")
    args = parser.parse_args()
    main(run_id=args.run_id)
