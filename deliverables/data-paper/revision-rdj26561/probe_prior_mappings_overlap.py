"""Probe: prior bibliometric mappings vs refined corpus (ticket 0289).

Replicates the published search query of each prior climate/green finance
bibliometric mapping against OpenAlex, then reports what share of the
retrieved population is present in refined_works.csv (DOI match, normalized
title fallback). Supports the added-value claim of the RDJ-26561 revision:
"our corpus covers the source populations of the prior mappings" is checked
empirically, not asserted from corpus-size ratios.

Query definitions are transcribed from the papers themselves (docs/articles/
PDFs, read 2026-07-22):

- care_weber2023 (Scopus): TITLE-ABS-KEY("climate finance") AND DOCTYPE
  ar/re/sh AND LANGUAGE English AND SUBJAREA SOCI/ECON/BUSI, 2004-2021,
  final n=315. The subject-area limit has no OpenAlex equivalent; the
  replication is a superset on that axis.
- shang_jin2023 (WoS SCI+SSCI): topic "climate finance", 2001-2022, English,
  articles+reviews, manually pruned to n=2,311 (from 2,883).
- maria_etal2023 (Scopus): TITLE-ABS-KEY((finance OR financial) W/3 (green
  OR climate OR carbon OR sustainable)), journal sources, accessed Sept 2021,
  first sample 3,663, giant component n=3,275. The W/3 proximity operator has
  no OpenAlex equivalent; we replicate the four core phrases, a subset of
  their query surface.
- rusydiana2023 (Scopus): "Climate Finance", journal articles, n=1,051,
  accessed October 2023.

Not replicable from local sources: deb_chen2024 (PDF is an image-only scan,
no query text extractable) and singhania_etal2023 (no local fulltext).

Run from the repo root (network + real data — not wired into make):

    uv run python deliverables/data-paper/revision-rdj26561/\
probe_prior_mappings_overlap.py \
        --corpus data/catalogs/refined_works.csv \
        --output deliverables/data-paper/revision-rdj26561/\
prior-mappings-overlap.csv \
        --cache-dir data/raw/prior_mappings
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
import unicodedata

import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

OPENALEX_WORKS = "https://api.openalex.org/works"

STUDIES: list[dict] = [
    {
        "key": "care_weber2023",
        "label": "Carè & Weber 2023 (RIBAF)",
        "db": "Scopus",
        "reported_n": 315,
        "search": '"climate finance"',
        "from_date": "2004-01-01",
        "to_date": "2021-12-31",
        "types": "article|review",
        "language": "en",
        "notes": "SUBJAREA SOCI/ECON/BUSI limit not replicable in OpenAlex",
    },
    {
        "key": "shang_jin2023",
        "label": "Shang & Jin 2023 (ESPR)",
        "db": "Web of Science",
        "reported_n": 2311,
        "search": '"climate finance"',
        "from_date": "2001-01-01",
        "to_date": "2022-12-31",
        "types": "article|review",
        "language": "en",
        "notes": "WoS topic search; manual pruning of 572 off-topic works not replicated",
    },
    {
        "key": "maria_etal2023",
        "label": "Reis Maria et al. 2023 (Sustainability)",
        "db": "Scopus",
        "reported_n": 3275,
        "search": (
            '"green finance" OR "climate finance" OR "carbon finance" '
            'OR "sustainable finance"'
        ),
        "from_date": None,
        "to_date": "2021-09-30",
        "types": "article|review|book-chapter",
        "language": None,
        "notes": "W/3 proximity approximated by the four core phrases (subset)",
    },
    {
        "key": "rusydiana2023",
        "label": "Rusydiana 2023 (Text Analytics in Economics)",
        "db": "Scopus",
        "reported_n": 1051,
        "search": '"climate finance"',
        "from_date": None,
        "to_date": "2023-10-31",
        "types": "article",
        "language": None,
        "notes": "query reported only as the phrase; access date approximated",
    },
]


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def norm_doi(d: str) -> str:
    d = d.strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/",
              "http://dx.doi.org/", "doi:"):
        if d.startswith(p):
            d = d[len(p):]
    return d.strip("/ ")


def match_record(record: dict, corpus_dois: set[str],
                 corpus_titles: dict[str, set[int]]) -> str | None:
    """Return 'doi', 'title', or None for one retrieved work.

    A title match is year-constrained (±1 year against the corpus rows
    carrying that title) so cross-decade title collisions cannot inflate
    coverage; a record without publication year falls back to title-only.
    """
    doi = record.get("doi")
    if doi and norm_doi(doi) in corpus_dois:
        return "doi"
    title = record.get("title")
    if title:
        years = corpus_titles.get(norm_title(title))
        if years is not None:
            rec_year = record.get("publication_year")
            if rec_year is None or not years or any(abs(int(rec_year) - y) <= 1
                                                    for y in years):
                return "title"
    return None


def summarize(key: str, rows: list[dict], corpus_dois: set[str],
              corpus_titles: dict[str, set[int]]) -> dict:
    """Coverage summary for one study's retrieved population."""
    matched_doi = matched_title = 0
    with_doi = 0
    for r in rows:
        if r.get("doi"):
            with_doi += 1
        how = match_record(r, corpus_dois, corpus_titles)
        if how == "doi":
            matched_doi += 1
        elif how == "title":
            matched_title += 1
    matched = matched_doi + matched_title
    retrieved = len(rows)
    return {
        "study": key,
        "retrieved": retrieved,
        "with_doi": with_doi,
        "matched_doi": matched_doi,
        "matched_title": matched_title,
        "matched": matched,
        "coverage_pct": round(100.0 * matched / retrieved, 1) if retrieved else 0.0,
    }


def classify_miss(record: dict, ext_dois: set[str],
                  ext_titles: dict[str, set[int]],
                  audit: dict[str, dict]) -> dict:
    """Classify one missed work: dropped by our filter, or never captured.

    'filtered_out' means the work is present in extended_works (captured by
    a source, then removed by the corpus-filter policy); 'not_captured'
    means no source ever retrieved it. Audit fields are joined by DOI when
    available.
    """
    status = ("filtered_out"
              if match_record(record, ext_dois, ext_titles) else "not_captured")
    a = audit.get(norm_doi(record.get("doi") or "")) if record.get("doi") else None
    return {
        "status": status,
        "audit_action": (a or {}).get("action", ""),
        "audit_flags": (a or {}).get("flags", ""),
        "cited_by_count": (a or {}).get("cited_by_count", ""),
    }


def load_audit(path: str) -> dict[str, dict]:
    csv.field_size_limit(sys.maxsize)
    audit: dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("doi"):
                audit[norm_doi(row["doi"])] = row
    return audit


def build_filter(study: dict) -> str:
    parts = [f"title_and_abstract.search:{study['search']}"]
    if study.get("from_date"):
        parts.append(f"from_publication_date:{study['from_date']}")
    if study.get("to_date"):
        parts.append(f"to_publication_date:{study['to_date']}")
    if study.get("types"):
        parts.append(f"type:{study['types']}")
    if study.get("language"):
        parts.append(f"language:{study['language']}")
    return ",".join(parts)


def fetch_study(study: dict, mailto: str | None, api_key: str | None,
                delay: float = 0.15) -> list[dict]:
    """Cursor-paginate the replicated query; return [{id, doi, title}, ...]."""
    session = requests.Session()
    params: dict = {
        "filter": build_filter(study),
        "select": "id,doi,title,publication_year",
        "per-page": 200,
        "cursor": "*",
    }
    if mailto:
        params["mailto"] = mailto
    if api_key:
        params["api_key"] = api_key
    rows: list[dict] = []
    while True:
        resp = session.get(OPENALEX_WORKS, params=params, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        rows.extend(payload.get("results", []))
        cursor = payload.get("meta", {}).get("next_cursor")
        if not cursor or not payload.get("results"):
            break
        params["cursor"] = cursor
        time.sleep(delay)
    log.info("  %s: retrieved %d works from OpenAlex", study["key"], len(rows))
    return rows


def load_corpus(path: str) -> tuple[set[str], dict[str, set[int]]]:
    csv.field_size_limit(sys.maxsize)
    dois: set[str] = set()
    titles: dict[str, set[int]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("doi"):
                dois.add(norm_doi(row["doi"]))
            if row.get("title"):
                years = titles.setdefault(norm_title(row["title"]), set())
                try:
                    years.add(int(float(row.get("year") or "")))
                except ValueError:
                    pass
    log.info("corpus: %d dois, %d titles", len(dois), len(titles))
    return dois, titles


def get_rows(study: dict, cache_dir: str | None, mailto: str | None,
             api_key: str | None) -> list[dict]:
    """Fetch one study's population, using the JSONL cache when present."""
    cache = (os.path.join(cache_dir, f"{study['key']}.jsonl")
             if cache_dir else None)
    if cache and os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f]
        log.info("  %s: %d works from cache", study["key"], len(rows))
        return rows
    rows = fetch_study(study, mailto, api_key)
    if cache:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", required=True,
                    help="path to refined_works.csv")
    ap.add_argument("--output", required=True,
                    help="summary CSV to write")
    ap.add_argument("--cache-dir", default=None,
                    help="directory for per-study JSONL pulls (reused on rerun)")
    ap.add_argument("--study", default=None,
                    help="restrict to one study key")
    ap.add_argument("--extended", default=None,
                    help="extended_works.csv (pre-filter corpus) — enables "
                         "miss decomposition: filtered_out vs not_captured")
    ap.add_argument("--audit", default=None,
                    help="corpus_audit.csv — joins removal action/flags "
                         "onto filtered misses")
    ap.add_argument("--misses-output", default=None,
                    help="CSV of missed works with decomposition status "
                         "(requires --extended)")
    args = ap.parse_args()

    mailto = os.environ.get("MAILTO") or os.environ.get("OPENALEX_MAILTO")
    api_key = os.environ.get("OPENALEX_API_KEY")

    corpus_dois, corpus_titles = load_corpus(args.corpus)
    ext_dois: set[str] = set()
    ext_titles: dict[str, set[int]] = {}
    if args.extended:
        ext_dois, ext_titles = load_corpus(args.extended)
    audit = load_audit(args.audit) if args.audit else {}

    summaries = []
    miss_rows: list[dict] = []
    for study in STUDIES:
        if args.study and study["key"] != args.study:
            continue
        log.info("== %s — %s, reported n=%d", study["label"], study["db"],
                 study["reported_n"])
        rows = get_rows(study, args.cache_dir, mailto, api_key)
        s = summarize(study["key"], rows, corpus_dois, corpus_titles)
        s["db"] = study["db"]
        s["reported_n"] = study["reported_n"]
        s["notes"] = study["notes"]
        s["missed_filtered"] = s["missed_not_captured"] = ""
        if args.extended:
            n_filtered = n_uncaptured = 0
            for r in rows:
                if match_record(r, corpus_dois, corpus_titles):
                    continue
                c = classify_miss(r, ext_dois, ext_titles, audit)
                if c["status"] == "filtered_out":
                    n_filtered += 1
                else:
                    n_uncaptured += 1
                miss_rows.append({
                    "study": study["key"], "openalex_id": r.get("id", ""),
                    "doi": r.get("doi") or "", "title": r.get("title") or "",
                    "year": r.get("publication_year") or "", **c,
                })
            s["missed_filtered"] = n_filtered
            s["missed_not_captured"] = n_uncaptured
            log.info("  misses: %d filtered_out, %d not_captured",
                     n_filtered, n_uncaptured)
        summaries.append(s)
        log.info("  matched %d/%d (%.1f%%; doi %d, title %d)",
                 s["matched"], s["retrieved"], s["coverage_pct"],
                 s["matched_doi"], s["matched_title"])

    if args.misses_output and miss_rows:
        mf = ["study", "openalex_id", "doi", "title", "year", "status",
              "audit_action", "audit_flags", "cited_by_count"]
        with open(args.misses_output, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=mf)
            w.writeheader()
            w.writerows(miss_rows)
        log.info("wrote %s (%d missed works)", args.misses_output,
                 len(miss_rows))

    fieldnames = ["study", "db", "reported_n", "retrieved", "with_doi",
                  "matched_doi", "matched_title", "matched", "coverage_pct",
                  "missed_filtered", "missed_not_captured", "notes"]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(summaries)
    log.info("wrote %s (%d studies)", args.output, len(summaries))


if __name__ == "__main__":
    main()
