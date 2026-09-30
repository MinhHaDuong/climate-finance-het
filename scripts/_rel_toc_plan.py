"""Manifest and query plan of the REL TOC lane (ticket 1650).

Shared by the sweep (``catalog_rel_toc.py``) and the delivery
(``_rel_toc_deliver.py``): which titles, which ISSNs, which filters.
"""

import csv
import os
from datetime import datetime, timezone

import yaml
from _rel_toc_core import FROM_DATE, UNTIL_DATE
from catalog_rel_sud_search import build_filter, expand_query

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "config", "rel_toc_manifest.csv")
THEMATIC_CONFIG = os.path.join(ROOT, "config", "rel_sud_search.yaml")

def load_manifest(spec="all"):
    """Manifest rows: ``all``, ``full``, ``thematic`` or comma-separated keys."""
    with open(MANIFEST, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if spec in ("all", None):
        return rows
    if spec in ("full", "thematic"):
        return [r for r in rows if r["sweep_mode"] == spec]
    by = {r["journal_key"]: r for r in rows}
    keys = spec.split(",")
    missing = [k for k in keys if k not in by]
    if missing:
        raise SystemExit(f"unknown journal keys: {missing}")
    return [by[k] for k in keys]


def issns(journal):
    return list(dict.fromkeys(i for i in (journal["pissn"], journal["eissn"]) if i))


def openalex_filter(journal):
    return (f"primary_location.source.issn:{'|'.join(issns(journal))},"
            f"from_publication_date:{FROM_DATE},to_publication_date:{UNTIL_DATE}")


def thematic_queries(journals, config_path=THEMATIC_CONFIG):
    """The REL English thematic queries (T1-T4 and the gap-fill), one OR'd ISSN filter."""
    with open(config_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    all_issns = [i for j in journals for i in issns(j)]
    searches = [(f"MJ-en-{t}", s) for t, s in cfg["queries"]["en"].items()]
    searches.append(("MJ-en-gap-fill", cfg["gap_fill"]))
    return [{"query_id": qid, "search": expand_query(s),
             "filter": build_filter(expand_query(s), cfg["year_min"], cfg["year_max"],
                                    issns=all_issns)}
            for qid, s in searches]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
