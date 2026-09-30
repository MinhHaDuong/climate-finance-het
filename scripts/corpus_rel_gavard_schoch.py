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
treated. The decision list stays in ``data/rel/gavard_schoch/``.

The delivery to the pool (ticket 1655) follows the intake contract of ticket
1730 (``docs/rel-intake-contract.md``): every reference retrieved, whatever its
scope or pool presence, with the decision and the pool match carried in
``lane_status`` and ``lane_note`` as information only. The only item left out is
the collection's status web notice, which is not a reference (``front_matter``).

Usage:
    python scripts/corpus_rel_gavard_schoch.py \
        --references data/rel/gavard_schoch/references.csv \
        --pool unified=data/catalogs/unified_works.csv \
        --pool refined=data/catalogs/refined_works.csv \
        --pool rel_sud_1530=.../screen_input_union.jsonl \
        --retrieved 2026-09-30 --output-dir data/rel/gavard_schoch \
        --delivery-dir data/rel_intake/t1651-gavard-schoch/2026-09-30 \
        --commit "$(git rev-parse HEAD)" --machine "$(hostname)"
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
# Intake contract of ticket 1730 (docs/rel-intake-contract.md).
RECORD_COLUMNS = [
    "record_id", "query_id", "platform", "retrieved_at", "title",
    "platform_record_id", "doi", "openalex_id", "title_original",
    "first_author", "all_authors", "year", "publication_date", "journal",
    "issn", "doc_type", "language", "abstract", "abstract_provenance", "url",
    "affiliation_countries", "version_hint", "lane_status", "lane_note",
]
REGISTRY_COLUMNS = ["query_id", "platform", "query", "run_at", "n_received",
                    "completed", "n_expected", "stop_reason"]
EXCLUDED_COLUMNS = ["record_id", "query_id", "reason", "title", "note"]
LANE_STATUS = {"inclus": "candidate", "doublon": "already_in_pool",
               "hors thème": "off_topic_in_lane_view",
               "hors période": "out_of_window_in_lane_view",
               "non résolu": "unresolved"}

# The lane's search units: the two Zotero collections of the audit, read from
# the local Zotero database (immutable copy) on 2026-09-30. n_items counts
# every top-level item of the collection.
ZOTERO_COLLECTIONS = {
    "Climate finance audit (2026)": {"query_id": "zotero-9UYPWCER", "key": "9UYPWCER",
                                     "n_items": 17},
    "Comment on Gavard & Schoch (2026)": {"query_id": "zotero-JTA96SGZ",
                                          "key": "JTA96SGZ", "n_items": 13},
}
# Items of those collections that are not references at all.
EXCLUDED = [
    {"record_id": "1651-zotero-DG7WX77H", "query_id": "zotero-9UYPWCER",
     "reason": "front_matter",
     "title": "Climate-finance audit — PDFs still needed",
     "note": "Zotero web notice pointing to the local status page docs/missing-papers.html; "
             "the one reference it lists (Wang & Tang 2026) is delivered as 1651-GS16"},
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


def run(references, pools):
    """Decision rows for a register against named pools, with the pool hits.

    ``pools`` maps a pool name to its list of records (see ``load_pool``).
    Each decision row carries a private ``_hits`` list for the intake records.
    """
    decisions = []
    for ref in references:
        hits = []
        for pool in pools.values():
            hit, _near = match_one(ref, pool)
            if hit:
                hits.append(hit)
        method = ""
        if hits:
            method = "doi" if any(h[0] == "doi" for h in hits) else hits[0][0]
        decision = decide(ref["scope"], bool(hits))
        row = {k: ref.get(k, "") for k in DECISION_FIELDS}
        row.update({
            "decision": decision,
            "treated": "yes" if decision in TREATED else "no",
            "needs_human": "yes" if decision == "non résolu" else "no",
            "pool_match_method": method or "absent",
            "pool_matches": "; ".join(f"{h[1]['pool']}={h[1]['id']} ({h[0]}, {h[2]:.2f})"
                                      for h in hits),
            "_hits": hits,
        })
        decisions.append(row)
    return decisions


def _openalex_id(hits):
    for _method, rec, _score in hits:
        m = re.search(r"\bW\d+$", rec["id"])
        if m:
            return m.group(0)
    return ""


def intake_records(references, decisions, retrieved):
    """records.csv rows of the intake contract: every reference, unscreened."""
    by_ref = {r["ref_id"]: r for r in references}
    rows = []
    for d in decisions:
        ref = by_ref[d["ref_id"]]
        link = ref.get("version_link", "")
        rows.append({
            "record_id": f"1651-{ref['ref_id']}",
            "query_id": ZOTERO_COLLECTIONS[ref["zotero_collection"]]["query_id"],
            "platform": "zotero",
            "retrieved_at": retrieved,
            "title": ref["title"],
            "platform_record_id": ref["zotero_key"],
            "doi": norm_doi(ref["doi"]),
            "openalex_id": _openalex_id(d["_hits"]),
            "first_author": ref["first_author"],
            "all_authors": ref["authors"],
            "year": ref["year"],
            "journal": ref["venue"],
            "doc_type": ref["item_type"],
            "url": f"https://doi.org/{norm_doi(ref['doi'])}" if ref["doi"] else "",
            "version_hint": f"1651-{link}" if link else "",
            "lane_status": LANE_STATUS[d["decision"]],
            "lane_note": "; ".join(x for x in (
                f"decision {d['decision']}: {ref['scope_reason']}",
                f"pool {d['pool_match_method']}" + (f" [{d['pool_matches']}]"
                                                    if d["pool_matches"] else ""),
                f"alt title: {ref['alt_title']}" if ref.get("alt_title") else "",
                f"files: {ref['pdf_files']}" if ref.get("pdf_files") else "",
            ) if x),
        })
    return rows


def intake_registry(records, run_at):
    """registry.csv: one search unit per Zotero collection."""
    rows = []
    for name, c in ZOTERO_COLLECTIONS.items():
        n_delivered = sum(r["query_id"] == c["query_id"] for r in records)
        n_excluded = sum(e["query_id"] == c["query_id"] for e in EXCLUDED)
        rows.append({
            "query_id": c["query_id"], "platform": "zotero",
            "query": f"Zotero collection '{name}' (key {c['key']}), every top-level item",
            "run_at": run_at, "n_received": str(n_delivered + n_excluded),
            "completed": "true", "n_expected": str(c["n_items"]), "stop_reason": "",
        })
    return rows


def write_intake(delivery_dir, references, decisions, retrieved, producer, notes=""):
    """Write the four files of an intake delivery (docs/rel-intake-contract.md)."""
    records = intake_records(references, decisions, retrieved)
    registry = intake_registry(records, retrieved)
    os.makedirs(delivery_dir, exist_ok=True)
    write_csv(os.path.join(delivery_dir, "records.csv"), RECORD_COLUMNS, records)
    write_csv(os.path.join(delivery_dir, "registry.csv"), REGISTRY_COLUMNS, registry)
    write_csv(os.path.join(delivery_dir, "excluded.csv"), EXCLUDED_COLUMNS, EXCLUDED)
    excluded_counts = {}
    for e in EXCLUDED:
        excluded_counts[e["reason"]] = excluded_counts.get(e["reason"], 0) + 1
    manifest = {
        "lane": os.path.basename(os.path.dirname(os.path.abspath(delivery_dir))),
        "ticket": "1651",
        "delivery": os.path.basename(os.path.abspath(delivery_dir)),
        "delivered_at": retrieved,
        "producer": producer,
        "counts": {"records": len(records), "excluded": excluded_counts},
        "coverage": "complete",
        "incomplete": [],
        "needs_human": [
            {"item": f"1651-{d['ref_id']} doi:{norm_doi(d['doi'])}",
             "reason": d["scope_reason"]}
            for d in decisions if d["needs_human"] == "yes"],
        "supersedes": None,
        "notes": notes,
    }
    with open(os.path.join(delivery_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return records, manifest


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--references", required=True)
    ap.add_argument("--pool", action="append", required=True, metavar="NAME=PATH")
    ap.add_argument("--retrieved", required=True, help="retrieval date, YYYY-MM-DD")
    ap.add_argument("--output-dir", required=True, help="decision list directory")
    ap.add_argument("--delivery-dir", required=True,
                    help="data/rel_intake/t1651-gavard-schoch/<YYYY-MM-DD>")
    ap.add_argument("--commit", required=True, help="git sha of the producing script")
    ap.add_argument("--machine", required=True)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    with open(args.references, newline="", encoding="utf-8") as fh:
        references = list(csv.DictReader(fh))
    pools, pool_manifest = {}, {}
    for spec in args.pool:
        name, path = spec.split("=", 1)
        pools[name] = load_pool(name, path)
        pool_manifest[name] = {"file": os.path.basename(path), "md5": md5sum(path),
                               "records": len(pools[name])}

    decisions = run(references, pools)
    os.makedirs(args.output_dir, exist_ok=True)
    write_csv(os.path.join(args.output_dir, "decisions.csv"), DECISION_FIELDS, decisions)
    with open(os.path.join(args.output_dir, "pool_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"retrieved": args.retrieved, "title_threshold": TITLE_THRESHOLD,
                   "title_threshold_no_author": TITLE_THRESHOLD_NO_AUTHOR,
                   "year_tolerance": YEAR_TOLERANCE, "pools": pool_manifest},
                  fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    revision = "; ".join(f"{n}={m['file']} md5 {m['md5']}" for n, m in pool_manifest.items())
    producer = {"script": "scripts/corpus_rel_gavard_schoch.py", "commit": args.commit,
                "machine": args.machine}
    records, _ = write_intake(
        args.delivery_dir, references, decisions, args.retrieved, producer,
        notes=("Every reference of the two Zotero collections is delivered, pool "
               "presence and scope included, as lane_status/lane_note information. "
               f"Pool matched: {revision}. Decision list: data/rel/gavard_schoch/."))
    counts = {d: sum(r["decision"] == d for r in decisions) for d in DECISIONS}
    log.info("%s", json.dumps({"references": len(decisions), "decisions": counts,
                               "delivered": len(records), "excluded": len(EXCLUDED)},
                              ensure_ascii=False))


if __name__ == "__main__":
    main()
