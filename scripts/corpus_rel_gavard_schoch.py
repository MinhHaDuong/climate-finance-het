"""REL Gavard-Schoch lane: match the audit references against the pool (ticket 1651).

The reference register ``data/rel/gavard_schoch/references.csv`` is written by
hand from the Zotero records and the PDFs of the Gavard & Schoch audit: one row
per reference, with its scope (pertinent, hors thème, hors période, non résolu)
and the evidence read on the record. This script adds what a hand cannot keep
honest: whether each reference is already in the pool, and how that was found.

Matching, per pool file, in order:

1. normalised DOI, exact;
2. normalised title (accents folded, punctuation dropped), fuzzy ratio at least
   ``TITLE_THRESHOLD`` against the title or the alternative title, publication
   year within one year (working paper against article), and the first-author
   surname found in the pool record's first author. A pool record without an
   author (the 1530 candidate files) needs ``TITLE_THRESHOLD_NO_AUTHOR``.

A missing DOI match is never taken as absence: the title rule runs for every
reference without a DOI hit.

Decision per reference: a pertinent reference found in the pool is ``doublon``,
a pertinent one absent from every pool file is ``inclus``; the other scopes are
the decision. ``non résolu`` is flagged needs-human and never counted as
treated. The delivery to 1655 holds every reference absent from the pool,
whatever its scope (no relevance set-aside), with its provenance.

Usage:
    python scripts/corpus_rel_gavard_schoch.py \
        --references data/rel/gavard_schoch/references.csv \
        --pool unified=data/catalogs/unified_works.csv \
        --pool refined=data/catalogs/refined_works.csv \
        --pool rel_sud_1530=.../screen_input_union.jsonl \
        --retrieved 2026-09-30 --output-dir data/rel/gavard_schoch
"""

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher

log = logging.getLogger("rel_gavard_schoch")

csv.field_size_limit(sys.maxsize)

TITLE_THRESHOLD = 0.90
TITLE_THRESHOLD_NO_AUTHOR = 0.95
YEAR_TOLERANCE = 1

SCOPES = ("pertinent", "hors thème", "hors période", "non résolu")
DECISIONS = ("inclus", "doublon", "hors thème", "hors période", "non résolu")
TREATED = ("inclus", "doublon", "hors thème", "hors période")

DECISION_FIELDS = [
    "ref_id", "zotero_key", "first_author", "year", "title", "doi", "scope",
    "decision", "treated", "needs_human", "pool_match_method", "pool_matches",
    "version_link", "scope_reason", "evidence",
]
DELIVERY_FIELDS = [
    "lane", "ref_id", "zotero_key", "zotero_collection", "item_type", "doi",
    "title", "alt_title", "first_author", "authors", "year", "venue",
    "source_file", "decision", "treated", "needs_human", "version_link",
    "match_method", "best_title_candidate", "retrieval_date", "pool_revision",
    "scope_reason", "evidence",
]


def fold(text):
    """Lower case, accents folded, punctuation to spaces, spaces collapsed."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", text)).strip()


def norm_doi(doi):
    """Bare lower-case DOI, without resolver prefix; empty when none."""
    m = re.search(r"10\.\d{4,}/\S+", (doi or "").strip().lower())
    return m.group(0).rstrip(".") if m else ""


def to_year(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def load_pool(name, path):
    """Pool records as dicts: pool, id, doi, title, tnorm, author, year."""
    records = []
    if path.endswith(".jsonl"):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                records.append({"id": r.get("openalex_id", ""), "doi": r.get("doi", ""),
                                "title": r.get("title", ""), "author": "",
                                "year": r.get("year")})
    else:
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                records.append({"id": f"{r.get('source', '')}:{r.get('source_id', '')}",
                                "doi": r.get("doi", ""), "title": r.get("title", ""),
                                "author": r.get("first_author", ""), "year": r.get("year")})
    for r in records:
        r["pool"] = name
        r["doi"] = norm_doi(r["doi"])
        r["tnorm"] = fold(r["title"])
        r["author"] = fold(r["author"])
        r["year"] = to_year(r["year"])
    return records


def match_one(ref, pool):
    """Best match of one reference in one pool: (method, record, score) or None.

    Also returns the best title candidate below threshold, for the evidence.
    """
    doi = norm_doi(ref["doi"])
    if doi:
        for r in pool:
            if r["doi"] == doi:
                return ("doi", r, 1.0), None
    titles = [fold(t) for t in (ref["title"], ref.get("alt_title", "")) if t]
    year = to_year(ref["year"])
    surname = fold(ref["first_author"])
    best = None
    for r in pool:
        if not r["tnorm"] or year is None or r["year"] is None:
            continue
        if abs(r["year"] - year) > YEAR_TOLERANCE:
            continue
        for t in titles:
            sm = SequenceMatcher(None, t, r["tnorm"])
            if sm.real_quick_ratio() < 0.75 or sm.quick_ratio() < 0.75:
                continue
            score = sm.ratio()
            if best is None or score > best[1]:
                best = (r, score)
    if best is None:
        return None, None
    r, score = best
    if r["author"]:
        ok = score >= TITLE_THRESHOLD and bool(surname) and surname in r["author"]
    else:
        ok = score >= TITLE_THRESHOLD_NO_AUTHOR
    if ok:
        return ("title_author_year" if r["author"] else "title_year", r, score), None
    return None, (r, score)


def decide(scope, matched):
    """Decision class from the hand scope and the pool presence."""
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}")
    if scope == "pertinent":
        return "doublon" if matched else "inclus"
    return scope


def md5sum(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(references, pools, retrieved, lane="1651"):
    """Decision rows and delivery rows for a register against named pools.

    ``pools`` maps a pool name to its list of records (see ``load_pool``).
    """
    decisions, delivery = [], []
    for ref in references:
        hits, near = [], None
        for pool in pools.values():
            hit, cand = match_one(ref, pool)
            if hit:
                hits.append(hit)
            elif cand and (near is None or cand[1] > near[1]):
                near = cand
        method = ""
        if hits:
            method = "doi" if any(h[0] == "doi" for h in hits) else hits[0][0]
        decision = decide(ref["scope"], bool(hits))
        treated = decision in TREATED
        row = {k: ref.get(k, "") for k in DECISION_FIELDS}
        row.update({
            "decision": decision,
            "treated": "yes" if treated else "no",
            "needs_human": "yes" if decision == "non résolu" else "no",
            "pool_match_method": method or "absent",
            "pool_matches": "; ".join(f"{h[1]['pool']}={h[1]['id']} ({h[0]}, {h[2]:.2f})"
                                      for h in hits),
        })
        decisions.append(row)
        if not hits:
            out = {k: ref.get(k, "") for k in DELIVERY_FIELDS}
            out.update({
                "lane": lane, "source_file": ref.get("pdf_files", ""),
                "decision": decision, "treated": row["treated"],
                "needs_human": row["needs_human"], "match_method": "absent",
                "best_title_candidate": (f"{near[0]['pool']}={near[0]['id']} "
                                         f"'{near[0]['title'][:80]}' ({near[1]:.2f})"
                                         if near else ""),
                "retrieval_date": retrieved,
            })
            delivery.append(out)
    return decisions, delivery


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--references", required=True)
    ap.add_argument("--pool", action="append", required=True, metavar="NAME=PATH")
    ap.add_argument("--retrieved", required=True, help="retrieval date, YYYY-MM-DD")
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    with open(args.references, newline="", encoding="utf-8") as fh:
        references = list(csv.DictReader(fh))
    pools, manifest = {}, {}
    for spec in args.pool:
        name, path = spec.split("=", 1)
        pools[name] = load_pool(name, path)
        manifest[name] = {"file": os.path.basename(path), "md5": md5sum(path),
                          "records": len(pools[name])}
    revision = "; ".join(f"{n}:{m['file']}@md5:{m['md5']}" for n, m in manifest.items())

    decisions, delivery = run(references, pools, args.retrieved)
    for row in delivery:
        row["pool_revision"] = revision
    os.makedirs(args.output_dir, exist_ok=True)
    write_csv(os.path.join(args.output_dir, "decisions.csv"), DECISION_FIELDS, decisions)
    write_csv(os.path.join(args.output_dir, "delivery_1655.csv"), DELIVERY_FIELDS, delivery)
    with open(os.path.join(args.output_dir, "pool_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"retrieved": args.retrieved, "title_threshold": TITLE_THRESHOLD,
                   "title_threshold_no_author": TITLE_THRESHOLD_NO_AUTHOR,
                   "year_tolerance": YEAR_TOLERANCE, "pools": manifest},
                  fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    counts = {d: sum(r["decision"] == d for r in decisions) for d in DECISIONS}
    log.info("%s", json.dumps({"references": len(decisions), "decisions": counts,
                      "delivered": len(delivery)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
