"""Build the 1650 intake delivery from a TOC run directory (ticket 1650).

Contract: ``docs/rel-intake-contract.md``. Everything retrieved is delivered;
the pool match is carried as ``lane_status`` and never filters. Only non-items
(covers, boards, contents pages, issue records, erratum notices) and in-lane
duplicates go to ``excluded.csv``.
"""

import collections
import csv
import glob
import gzip
import json
import os
import subprocess
import time

from _rel_toc_core import (
    PoolIndex,
    build_register,
    crossref_filter,
    crossref_record,
    exclusion_reason,
    in_window,
    lane_status,
    merge_toc,
    openalex_record,
    record_id,
    unit_id,
)
from _rel_toc_plan import ROOT, _now, issns, openalex_filter, thematic_queries
from utils import get_logger

log = get_logger("rel_toc_deliver")

LANE = "t1650-sommaires"
RECORD_FIELDS = [
    "record_id", "query_id", "platform", "retrieved_at", "title", "platform_record_id",
    "doi", "openalex_id", "title_original", "first_author", "all_authors", "year",
    "publication_date", "journal", "issn", "doc_type", "language", "abstract",
    "abstract_provenance", "url", "affiliation_countries", "version_hint", "lane_status",
    "lane_note",
    # extra columns, carried by the merge
    "journal_key", "sweep_mode", "volume", "issue", "online_first", "item_class",
    "toc_source", "year_source", "pool_match",
]
REGISTRY_FIELDS = [
    "query_id", "platform", "query", "filter", "run_at", "n_expected", "n_received",
    "completed", "stop_reason", "stratum", "journal_key", "year", "volume", "issue",
    "expected", "scanned", "crossref_n", "openalex_only_n", "front_matter", "in_pool",
    "candidates", "unresolved",
]
EXCLUDED_FIELDS = ["record_id", "query_id", "reason", "title", "note"]
SUMMARY_FIELDS = [
    "journal_key", "sweep_mode", "units", "expected", "crossref_n", "openalex_only_n",
    "front_matter", "in_pool", "candidates", "unresolved", "out_of_window", "complete",
]


def load_pool(pool_csv, rel_globs):
    """Raw merged catalogue plus REL search results, as match rows."""
    rows, sources = [], collections.Counter()
    csv.field_size_limit(10**9)
    with open(pool_csv, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append({"doi": r.get("doi"), "title": r.get("title"),
                         "first_author": r.get("first_author"), "year": r.get("year"),
                         "openalex_id": r["source_id"] if r.get("source") == "openalex" else ""})
            sources["catalogue"] += 1
    for pattern in rel_globs or []:
        for path in sorted(glob.glob(pattern)):
            n = 0
            try:
                with gzip.open(path, "rt", encoding="utf-8") as fh:
                    for line in fh:
                        w = json.loads(line)
                        rows.append({"doi": w.get("doi"), "title": w.get("title"),
                                     "first_author": "", "year": w.get("year"),
                                     "openalex_id": w.get("openalex_id")})
                        n += 1
            except (OSError, EOFError, json.JSONDecodeError) as exc:
                log.warning("unreadable %s after %d rows: %s", path, n, exc)
            sources[path] = n
    return rows, sources


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def _step_status(run_dir):
    """Last log entry per (step, journal or query)."""
    status = {}
    path = os.path.join(run_dir, "steps.jsonl")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                e = json.loads(line)
                if e.get("skipped"):
                    continue
                status[(e["step"], e.get("journal") or e.get("query_id"))] = e
    return status


def journal_toc(journal, run_dir):
    key = journal["journal_key"]
    cr = [crossref_record(it, key, "; ".join(issns(journal))) for it in
          _read_jsonl(os.path.join(run_dir, f"crossref_{key}.jsonl.gz"))]
    oa = [openalex_record(w, key) for w in
          _read_jsonl(os.path.join(run_dir, f"openalex_{key}.jsonl.gz"))]
    recs = merge_toc(cr, oa)
    for r in recs:
        r["issn"], r["journal"] = "; ".join(issns(journal)), r["journal"] or journal["title"]
    return recs


def _iso_date(value):
    parts = str(value or "").split("-")
    if not parts[0]:
        return ""
    return "-".join([parts[0]] + [p.zfill(2) for p in parts[1:3]])


def record_row(rec, qid, retrieved_at, sweep_mode):
    notes = []
    if rec.get("in_pool"):
        notes.append(f"in pool by {rec['in_pool']}")
    if not in_window(rec):
        notes.append("dated outside 1990-2026 (OpenAlex misdating redated by volume)")
    if rec.get("alias_dois"):
        notes.append(f"alias DOI {rec['alias_dois']}")
    platform = "crossref" if rec.get("toc_source") == "crossref" else "openalex"
    return {
        "record_id": record_id(rec), "query_id": qid, "platform": platform,
        "retrieved_at": retrieved_at, "title": rec["title"],
        "platform_record_id": rec["doi"] if platform == "crossref" else rec["openalex_id"],
        "doi": rec["doi"], "openalex_id": rec.get("openalex_id", ""), "title_original": "",
        "first_author": rec.get("first_author", ""), "all_authors": rec.get("authors", ""),
        "year": str(rec["year"]) if rec.get("year") else "",
        "publication_date": _iso_date(rec.get("pub_date")), "journal": rec.get("journal", ""),
        "issn": rec.get("issn", ""),
        "doc_type": rec.get("crossref_type") or rec.get("openalex_type") or "",
        "language": "", "abstract": rec.get("abstract", ""),
        "abstract_provenance": rec.get("abstract_provenance", ""),
        "url": f"https://doi.org/{rec['doi']}" if rec["doi"] else "",
        "affiliation_countries": "", "version_hint": rec.get("alias_dois", ""),
        "lane_status": lane_status(rec), "lane_note": "; ".join(notes),
        "journal_key": rec["journal_key"], "sweep_mode": sweep_mode,
        "volume": rec.get("volume", ""), "issue": rec.get("issue", ""),
        "online_first": str(bool(rec.get("online_first"))).lower(),
        "item_class": rec.get("item_class", ""), "toc_source": rec.get("toc_source", ""),
        "year_source": rec.get("year_source", ""), "pool_match": rec.get("in_pool", ""),
    }


def _write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _git_head():
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def deliver(args, manifest, steps):
    t0 = time.time()
    run_dir, out = args.run_dir, args.delivery_dir
    os.makedirs(out, exist_ok=True)
    pool_rows, sources = load_pool(args.pool, args.rel_results)
    pool = PoolIndex(pool_rows)
    steps.write(step="pool", sources=dict(sources), rows=pool.size)
    status = _step_status(run_dir)
    records, excluded, registry, summary = [], [], [], []
    seen = {}

    def add(rec, qid, retrieved_at, sweep_mode):
        rid = record_id(rec)
        reason = exclusion_reason(rec)
        if not reason and rid in seen:
            reason = "duplicate_in_lane"
        if reason:
            excluded.append({"record_id": rid if reason == "front_matter" else f"{rid}#{qid}",
                             "query_id": qid, "reason": reason, "title": rec.get("title", ""),
                             "note": rec.get("item_class", "") if reason == "front_matter"
                             else f"kept under {seen[rid]}"})
            return
        seen[rid] = qid
        records.append(record_row(rec, qid, retrieved_at, sweep_mode))

    for j in [m for m in manifest if m["sweep_mode"] == "full"]:
        key = j["journal_key"]
        cr_s, oa_s = status.get(("crossref", key), {}), status.get(("openalex", key), {})
        complete = bool(cr_s.get("complete")) and bool(oa_s.get("complete"))
        why = "; ".join(f"{name}: {s.get('stop_reason') or 'not run'}"
                        for name, s in (("crossref", cr_s), ("openalex", oa_s))
                        if not s.get("complete"))
        recs = journal_toc(j, run_dir)
        for r in recs:
            r["in_pool"] = pool.match(r)
        retrieved = {"crossref": cr_s.get("at", ""), "openalex-only": oa_s.get("at", "")}
        for r in recs:
            add(r, unit_id(r), retrieved[r["toc_source"]] or _now(), "full")
        units = build_register(recs)
        for u in units:
            registry.append({
                **u, "platform": "crossref;openalex",
                "query": (f"{j['title']} (ISSN {'; '.join(issns(j))}) "
                          + (f"online-first {u['year']}" if u["issue"] == "online-first"
                             else f"vol {u['volume'] or 'na'} issue {u['issue'] or 'na'} ({u['year']})")),
                "filter": f"crossref /works {crossref_filter(j)} | openalex /works {openalex_filter(j)}",
                "run_at": cr_s.get("at") or oa_s.get("at") or "", "n_expected": u["expected"],
                "n_received": u["expected"], "completed": str(complete).lower(),
                "stop_reason": why, "stratum": "toc-full"})
        summary.append({"journal_key": key, "sweep_mode": "full", "units": len(units),
                        **{k: sum(u[k] for u in units) for k in
                           ("expected", "crossref_n", "openalex_only_n", "front_matter",
                            "in_pool", "candidates", "unresolved")},
                        "out_of_window": sum(1 for r in recs if not in_window(r)),
                        "complete": str(complete).lower()})

    mega = [m for m in manifest if m["sweep_mode"] == "thematic"]
    by_issn = {i: m["journal_key"] for m in mega for i in issns(m)}
    for q in thematic_queries(mega):
        s = status.get(("thematic", q["query_id"]), {})
        works = _read_jsonl(os.path.join(run_dir, f"thematic_{q['query_id']}.jsonl.gz"))
        n_pool = n_cand = n_front = 0
        for w in works:
            src = ((w.get("primary_location") or {}).get("source") or {})
            key = next((by_issn[i] for i in src.get("issn") or [] if i in by_issn), "")
            rec = openalex_record(w, key)
            rec.update(toc_source="openalex-thematic", online_first=not rec["volume"],
                       journal=src.get("display_name") or "", issn="; ".join(src.get("issn") or []),
                       year_source="openalex", alias_dois="", abstract_provenance="")
            rec["in_pool"] = pool.match(rec)
            n_pool += bool(rec["in_pool"])
            n_front += bool(exclusion_reason(rec))
            n_cand += not rec["in_pool"] and not exclusion_reason(rec)
            add(rec, q["query_id"], s.get("at") or _now(), "thematic")
        registry.append({
            "query_id": q["query_id"], "platform": "openalex", "query": q["search"],
            "filter": q["filter"], "run_at": s.get("at", ""),
            "n_expected": s.get("expected", ""), "n_received": len(works),
            "completed": str(bool(s.get("complete"))).lower(),
            "stop_reason": "" if s.get("complete") else (s.get("stop_reason") or "not run"),
            "stratum": "megajournal-thematic", "expected": len(works), "scanned": len(works),
            "front_matter": n_front, "in_pool": n_pool, "candidates": n_cand,
            "openalex_only_n": len(works), "crossref_n": 0, "unresolved": 0})
        summary.append({"journal_key": q["query_id"], "sweep_mode": "thematic", "units": 1,
                        "expected": len(works), "crossref_n": 0, "openalex_only_n": len(works),
                        "front_matter": n_front, "in_pool": n_pool, "candidates": n_cand,
                        "unresolved": 0, "out_of_window": 0,
                        "complete": str(bool(s.get("complete"))).lower()})

    _write_csv(os.path.join(out, "records.csv"), records, RECORD_FIELDS)
    _write_csv(os.path.join(out, "registry.csv"), registry, REGISTRY_FIELDS)
    _write_csv(os.path.join(out, "excluded.csv"), excluded, EXCLUDED_FIELDS)
    if args.summary:
        _write_csv(args.summary, summary, SUMMARY_FIELDS)
    incomplete = [{"unit": r["query_id"], "reason": r["stop_reason"]} for r in registry
                  if r["completed"] != "true"]
    incomplete = list({u["unit"]: u for u in incomplete}.values())
    incomplete += SCOPE_LIMITS
    man = {
        "lane": LANE, "ticket": "1650", "delivery": os.path.basename(out.rstrip("/")),
        "delivered_at": _now(),
        "producer": {"script": "scripts/catalog_rel_toc.py deliver", "commit": _git_head(),
                     "machine": args.machine},
        "counts": {"records": len(records),
                   "excluded": dict(collections.Counter(e["reason"] for e in excluded))},
        "coverage": "incomplete", "incomplete": incomplete, "needs_human": NEEDS_HUMAN,
        "supersedes": None,
        "pool_matched": {"catalogue": args.pool, "rel_results": dict(sources),
                         "rows": pool.size},
        "notes": NOTES,
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    steps.write(step="deliver", records=len(records), excluded=man["counts"]["excluded"],
                registry=len(registry), seconds=round(time.time() - t0, 1))
    return 0


SCOPE_LIMITS = [
    {"unit": "all 57 fully swept titles",
     "reason": "scope (author, 2026-09-30): tables of contents are what Crossref and OpenAlex "
               "hold under the title's ISSNs, not verified against publisher pages; the pilot "
               "found 95% of issues behind publisher bot blocks"},
    {"unit": "six megajournals (Sustainability, Energies, Environmental Science and Pollution "
             "Research, Journal of Cleaner Production, Journal of Environmental Management, "
             "Applied Energy)",
     "reason": "scope (author, 2026-09-30): searched with the REL English thematic queries "
               "(config/rel_sud_search.yaml en T1-T4 and gap-fill), not swept in full "
               "(328,861 Crossref items)"},
    {"unit": "Economic and Political Weekly, 1990-2023",
     "reason": "no DOIs before 2024; covered only as far as OpenAlex holds it; no crawl "
               "(author decision)"},
]
NEEDS_HUMAN = [
    {"item": "Economic and Political Weekly, issues 1990-2023",
     "reason": "no DOIs; a TOC check needs epw.in by hand or a crawl the author declined"},
]
NOTES = (
    "Pool matched = raw merged catalogue (unified_works.csv, 43,179 works, 29 July 2026) plus "
    "the 1530 REL South search results (~/rel_sud_runs, archive 2026-09-29). Run 20260929e "
    "holds no record: it stopped at its first request on an OpenAlex 429 (empty registry, "
    "run.log) and was replaced by run f; nothing to recover. lane_status is information "
    "only. Items OpenAlex misdates (AER, 2016-01-01 for JSTOR-era works) are redated from "
    "the volume; those falling before 1990 are delivered with a lane_note, not dropped. "
    "Manifest: config/rel_toc_manifest.csv (frozen 2026-09-30, 63 titles)."
)
