#!/usr/bin/env python3
"""Merge citation caches into a single citations.csv.

Reads source-specific cache files from enrich_cache/:
  - crossref_refs.csv   (source_doi, ref_doi, ref_title, ..., ref_raw)
  - openalex_refs.csv   (source_doi, ref_oa_id, ref_doi, ref_title, ...)
  - ref_parsed.csv      (GROBID-parsed unstructured refs, REFS_COLUMNS schema)
  - ref_matches.csv     (fuzzy-matched refs with discovered DOIs, #539)

Plus the catalog-stage OpenAlex harvest (ticket 0300):
  - data/catalogs/openalex_citations.csv  (source_doi, source_id, ref_oa_id)
    DOIs covered at catalog stage are treated as done by the enrich
    harvester and never re-queried, so their edges exist only here.

Produces citations.csv with REFS_COLUMNS schema, deduplicated on
(source_doi, ref_doi). Sentinel rows are excluded.

This script is the final step of the ref_match DVC stage.
It runs after corpus_ref_match.py (which fuzzy-matches parsed refs to corpus).
DVC may wipe citations.csv before a re-run — this merge regenerates it
from the persistent caches in seconds, with no API calls.

Usage:
    uv run python scripts/corpus_merge_citations.py
"""

import argparse
import os

import pandas as pd
from utils import CATALOGS_DIR, REFS_COLUMNS, get_logger, normalize_doi, save_csv

log = get_logger("corpus_merge_citations")

CACHE_DIR = os.path.join(CATALOGS_DIR, "enrich_cache")
CROSSREF_CACHE = os.path.join(CACHE_DIR, "crossref_refs.csv")
OPENALEX_CACHE = os.path.join(CACHE_DIR, "openalex_refs.csv")
OUTPUT_PATH = os.path.join(CATALOGS_DIR, "citations.csv")
CATALOG_CITATIONS_PATH = os.path.join(CATALOGS_DIR, "openalex_citations.csv")
SENTINEL_REF_DOI = "__NO_REFS__"


def merge_citations(cache_dir=None, output_path=None, catalog_path=None):
    """Merge crossref + openalex caches into a single citations.csv.

    Args:
        cache_dir: Path to enrich_cache/ directory (default: CACHE_DIR)
        output_path: Path for output citations.csv (default: OUTPUT_PATH)
        catalog_path: Path to the catalog-stage openalex_citations.csv
            (default: CATALOG_CITATIONS_PATH). Ticket 0300: DOIs harvested
            at catalog stage are skipped by the enrich harvester, so their
            edges must be merged from this layer or they are lost.

    Returns:
        Number of rows written.

    """
    cache_dir = cache_dir or CACHE_DIR
    output_path = output_path or OUTPUT_PATH
    catalog_path = catalog_path or CATALOG_CITATIONS_PATH

    crossref_path = os.path.join(cache_dir, "crossref_refs.csv")
    openalex_path = os.path.join(cache_dir, "openalex_refs.csv")

    frames = []

    # Read Crossref cache — already has REFS_COLUMNS schema.
    # on_bad_lines="warn" tolerates partial trailing lines from crash-during-append.
    if os.path.exists(crossref_path):
        cr = pd.read_csv(crossref_path, dtype=str, keep_default_na=False,
                         on_bad_lines="warn")
        log.info("Crossref cache: %d rows", len(cr))
        frames.append(cr)
    else:
        log.info("No Crossref cache at %s", crossref_path)

    # Read OpenAlex cache — has ref_oa_id, needs mapping to REFS_COLUMNS
    if os.path.exists(openalex_path):
        oa = pd.read_csv(openalex_path, dtype=str, keep_default_na=False,
                         on_bad_lines="warn")
        log.info("OpenAlex cache: %d rows", len(oa))
        # Map to REFS_COLUMNS: ref_oa_id → source_id, fill missing columns
        oa_mapped = pd.DataFrame({
            "source_doi": oa["source_doi"],
            "source_id": oa.get("ref_oa_id", pd.Series(dtype=str)).apply(
                lambda x: f"openalex:{x}" if x else ""),
            "ref_doi": oa.get("ref_doi", pd.Series(dtype=str)),
            "ref_title": oa.get("ref_title", pd.Series(dtype=str)),
            "ref_first_author": oa.get("ref_first_author", pd.Series(dtype=str)),
            "ref_year": oa.get("ref_year", pd.Series(dtype=str)),
            "ref_journal": oa.get("ref_journal", pd.Series(dtype=str)),
            "ref_raw": "",
        })
        frames.append(oa_mapped)
    else:
        log.info("No OpenAlex cache at %s", openalex_path)

    # Read GROBID-parsed cache — already has REFS_COLUMNS schema
    grobid_path = os.path.join(cache_dir, "ref_parsed.csv")
    if os.path.exists(grobid_path):
        gp = pd.read_csv(grobid_path, dtype=str, keep_default_na=False)
        log.info("GROBID parsed cache: %d rows", len(gp))
        frames.append(gp)
    else:
        log.info("No GROBID parsed cache at %s", grobid_path)

    # Read fuzzy-matched refs (#539) — REFS_COLUMNS schema with discovered DOIs
    ref_matches_path = os.path.join(cache_dir, "ref_matches.csv")
    if os.path.exists(ref_matches_path):
        rm = pd.read_csv(ref_matches_path, dtype=str, keep_default_na=False)
        log.info("Ref matches cache: %d rows", len(rm))
        frames.append(rm)
    else:
        log.info("No ref matches cache at %s", ref_matches_path)

    # Read catalog-stage OpenAlex harvest (0300) — edge list with ref_oa_id
    # only (no ref metadata). FALLBACK layer: applied only to sources with
    # no resolved (non-sentinel) reference row in the caches above. Catalog
    # rows carry no ref_doi/title, so nothing could dedup them against a
    # Crossref-resolved twin — a plain union would double-count every
    # reference of a Crossref-covered source. Appended LAST so the
    # (source_doi, source_id) dedup below keeps a resolved twin.
    if os.path.exists(catalog_path):
        cat = pd.read_csv(catalog_path, dtype=str, keep_default_na=False,
                          on_bad_lines="warn")
        log.info("Catalog-stage OpenAlex layer: %d rows", len(cat))
        if frames:
            cached = pd.concat(frames, ignore_index=True)
            covered = set(
                cached.loc[cached["ref_doi"] != SENTINEL_REF_DOI, "source_doi"]
                .apply(lambda x: normalize_doi(x) if x else ""))
            covered.discard("")
        else:
            covered = set()
        cat = cat[~cat["source_doi"].apply(
            lambda x: normalize_doi(x) if x else "").isin(covered)]
        log.info("Catalog-stage rows kept (uncovered sources): %d", len(cat))
        cat_mapped = pd.DataFrame({
            "source_doi": cat["source_doi"],
            "source_id": cat["ref_oa_id"].apply(
                lambda x: f"openalex:{x}" if x else ""),
            "ref_doi": "",
            "ref_title": "",
            "ref_first_author": "",
            "ref_year": "",
            "ref_journal": "",
            "ref_raw": "",
        })
        frames.append(cat_mapped)
    else:
        log.info("No catalog-stage OpenAlex layer at %s", catalog_path)

    if not frames:
        log.info("No cache files found — writing empty citations.csv")
        empty = pd.DataFrame({c: pd.Series(dtype=str) for c in REFS_COLUMNS})
        save_csv(empty, output_path)
        return 0

    combined = pd.concat(frames, ignore_index=True)

    # Remove sentinel rows
    is_sentinel = combined["ref_doi"] == SENTINEL_REF_DOI
    n_sentinel = int(is_sentinel.sum())
    combined = combined[~is_sentinel]

    # Normalize DOIs for dedup
    combined["_src_norm"] = combined["source_doi"].apply(
        lambda x: normalize_doi(x) if x else "")
    combined["_ref_norm"] = combined["ref_doi"].apply(
        lambda x: normalize_doi(x) if x else "")

    # Cross-layer dedup on (source_doi, source_id): the same OpenAlex edge
    # may appear both in the enrich cache (resolved, with ref_doi/metadata)
    # and in the catalog-stage layer (bare ref_oa_id). keep="first" keeps
    # the resolved row because the catalog layer is concatenated last (0300).
    has_source_id = combined["source_id"] != ""
    combined = pd.concat([
        combined[has_source_id].drop_duplicates(
            subset=["_src_norm", "source_id"], keep="first"),
        combined[~has_source_id],
    ], ignore_index=True)

    # Dedup: for rows with ref_doi, dedup on (source_doi, ref_doi).
    # For rows without ref_doi (books/reports), dedup on
    # (source_doi, ref_title, ref_first_author, ref_year) to catch
    # the same book reference from both Crossref and OpenAlex.
    # Normalize title/author to lowercase for case-insensitive matching.
    # Metadata-less rows (catalog-stage edges: empty title AND author) are
    # exempt from the title key — it would collapse every catalog edge of a
    # source into one row; they are already deduplicated on source_id above.
    has_ref_doi = combined["_ref_norm"] != ""
    with_doi = combined[has_ref_doi].drop_duplicates(
        subset=["_src_norm", "_ref_norm"], keep="first")
    without_doi = combined[~has_ref_doi].copy()
    without_doi["_title_norm"] = without_doi["ref_title"].str.lower().str.strip()
    without_doi["_author_norm"] = without_doi["ref_first_author"].str.lower().str.strip()
    has_meta = (without_doi["_title_norm"] != "") | (without_doi["_author_norm"] != "")
    no_meta = without_doi[~has_meta]
    without_doi = without_doi[has_meta].drop_duplicates(
        subset=["_src_norm", "_title_norm", "_author_norm", "ref_year"],
        keep="first")
    without_doi = pd.concat([without_doi, no_meta], ignore_index=True)
    without_doi = without_doi.drop(columns=["_title_norm", "_author_norm"])

    result = pd.concat([with_doi, without_doi], ignore_index=True)
    n_deduped = len(combined) - len(result)

    # Drop internal columns, ensure REFS_COLUMNS order
    result = result[REFS_COLUMNS]
    save_csv(result, output_path)

    log.info("Merged: %d rows (-%d sentinels, -%d dupes) → %s",
             len(result), n_sentinel, n_deduped, output_path)
    return len(result)


def main():
    parser = argparse.ArgumentParser(
        description="Merge citation caches into citations.csv")
    parser.add_argument("--cache-dir", default=CACHE_DIR,
                        help="Path to enrich_cache/ directory")
    parser.add_argument("--output", default=OUTPUT_PATH,
                        help="Output path for merged citations.csv")
    parser.add_argument("--catalog-path", default=CATALOG_CITATIONS_PATH,
                        help="Path to catalog-stage openalex_citations.csv")
    args = parser.parse_args()

    merge_citations(cache_dir=args.cache_dir, output_path=args.output,
                    catalog_path=args.catalog_path)


if __name__ == "__main__":
    main()
