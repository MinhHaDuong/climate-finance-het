"""Deliver the ticket-1653 southern-source runs to the REL pool (ticket 1655).

Reads the run directories written by ``catalog_rel_sud_sources.py`` (each
holds ``registry.csv``, ``candidates.csv`` and ``raw/``) and writes one
delivery in the intake-contract layout (``docs/rel-intake-contract.md``):
``records.csv``, ``registry.csv``, ``excluded.csv``, ``manifest.json``, plus
``sentinels.csv`` (class-b sentinels found or missed).

What is delivered, per route (decision of 2026-09-30, see
``docs/rel-sud-sources-2026-09-30.md``):

- search routes (``api``): every record the server returned, deduplicated in
  lane by record id (the other rows go to ``excluded.csv`` as
  ``duplicate_in_lane``);
- harvest and listing routes (``oai-pmh``, ``listing``) have no server-side
  search, so the local 1530 lexicon match *is* the query: the registry's
  ``query`` says so, ``n_received`` is the number of matches, ``n_expected``
  the number harvested or listed; the full harvest stays archived in the run
  directory's ``raw/``.

``matched_terms`` travels as an extra column and in ``lane_status`` /
``lane_note``, as information only: it never filters a search-route record.

A record with neither DOI nor year gets a DOI found in its URL, else a year
from ``year_enrichment.csv`` in its run directory (written by the
``enrich-years`` subcommand from the GARUDA detail page). A persistent URL (a
Handle, ``_rel_pool_keys.url_is_key``) is a key too. What still has no key
cannot enter ``records.csv`` (the checker refuses it): it is listed in
``excluded.csv`` as ``no_dedup_key`` with its URL, and counted in the
manifest, never dropped silently.

A source DOI carried by delivered records with different titles (Redalyc
puts issue-level DOIs on unrelated articles) is not a key for them: it is
blanked, and ``lane_note`` keeps it, so the pool does not fuse distinct works.
Deduplication in lane is by record id only; same-item records under two ids
(GARUDA indexes some articles twice) are left to the pool's DOI and title
joins.

The name follows the delivery precedent ``catalog_rel_1530_delivery.py``.

Usage:
    python scripts/catalog_rel_1653_delivery.py export \\
        --run DIR[:SOURCE,SOURCE] ... --output-dir data/rel_intake/<lane>/<delivery>
    python scripts/catalog_rel_1653_delivery.py enrich-years \\
        --run-dir DIR --source garuda
"""

import argparse
import csv
import json
import os
import re
import socket
import subprocess
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone

import yaml
from _rel_pool_keys import url_is_key
from pipeline_io import polite_get
from rel_sud_sources import (
    _garuda as garuda,
)
from rel_sud_sources._common import (
    HARVEST_ROUTES,
    _norm,
    discover,
    find_doi,
    sentinel_report,
)
from utils import get_logger

log = get_logger("catalog_rel_1653_delivery")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The listing adapters' route before it was named "listing" (runs of
# 2026-09-30 in series-b/ and ceew/): their registry already counts matches
# in n_received and the listing size in n_expected.
LEGACY_LISTING_ROUTES = {"export"}

LANE = "t1653-sud-hors-openalex"
# The intake contract's columns (docs/rel-intake-contract.md), in its order;
# the tests hold them to scripts/qa_rel_intake.py.
RECORD_COLUMNS = [
    "record_id", "query_id", "platform", "retrieved_at", "title",
    "platform_record_id", "doi", "openalex_id", "title_original",
    "first_author", "all_authors", "year", "publication_date", "journal",
    "issn", "doc_type", "language", "abstract", "abstract_provenance", "url",
    "affiliation_countries", "version_hint", "lane_status", "lane_note",
]
EXCLUDED_COLUMNS = ["record_id", "query_id", "reason", "title", "note"]
TICKET = "1653"
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
YEAR_RE = re.compile(r"^(19|20)\d{2}$")

EXTRA_RECORD_COLUMNS = ["source", "route", "endpoint", "run_dir", "export_file",
                        "matched_terms", "query_ids_all", "language_raw"]
REGISTRY_COLUMNS = ["query_id", "platform", "query", "run_at", "n_received",
                    "completed", "stop_reason", "filter", "n_expected",
                    "source", "route", "endpoint", "run_dir", "query_id_run",
                    "n_announced", "n_harvested", "n_delivered"]
# A titled record whose source holds no DOI, OpenAlex id, year or persistent
# URL: contract reason no_dedup_key (ticket 1730); the pool takes it in as a
# title-only work.
NO_KEY_NOTE = ("no publication year, DOI, OpenAlex id or persistent URL in the source "
               "metadata (at most deposit dates)")
# OAI-PMH identifier prefix of a DSpace repository, by source, so an excluded
# record keeps every persistent identifier the pool may later accept as a key.
OAI_PREFIX = {"uwi": "oai:uwispace.sta.uwi.edu:"}


def no_key_note(rec):
    """``NO_KEY_NOTE`` plus the persistent identifiers the record does have."""
    ids = []
    pid = rec["platform_record_id"]
    if pid.startswith("hdl:"):
        handle = pid[4:]
        ids.append(f"Handle recorded: https://hdl.handle.net/{handle}")
        if rec["platform"] in OAI_PREFIX:
            ids.append(f"OAI identifier {OAI_PREFIX[rec['platform']]}{handle}")
    elif rec["url"]:
        ids.append(f"stable URL recorded: {rec['url']}")
    return "; ".join([NO_KEY_NOTE, *ids])


ENRICHMENT_FIELDS = ["record_id", "year", "source_url", "fetched_at", "status"]

# Language labels the sources use, to ISO 639-1. Anything else stays empty in
# ``language`` and is carried verbatim in ``language_raw``.
LANGUAGE_CODES = {
    "en": "en", "eng": "en", "en_us": "en", "inglés": "en", "english": "en",
    "es": "es", "spa": "es", "español": "es",
    "pt": "pt", "por": "pt", "portugués": "pt", "português": "pt",
    "fr": "fr", "fra": "fr", "fre": "fr", "francés": "fr",
    "de": "de", "alemán": "de", "it": "it", "italiano": "it",
    "pl": "pl", "polaco": "pl", "lt": "lt", "lituano": "lt",
    "gl": "gl", "gallego": "gl", "la": "la", "latín": "la",
    "hi": "hi", "bn": "bn", "ar": "ar", "id": "id", "ru": "ru", "zh": "zh",
}


def iso_language(raw):
    return LANGUAGE_CODES.get((raw or "").strip().casefold(), "")


def parse_run(arg):
    """``DIR[:a,b]`` -> ``(DIR, {a, b} or None)``."""
    path, _, srcs = arg.partition(":")
    return path, ({s for s in srcs.split(",") if s} or None)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read_enrichment(run_dir):
    path = os.path.join(run_dir, "year_enrichment.csv")
    if not os.path.exists(path):
        return {}
    return {r["record_id"]: r for r in read_csv(path) if YEAR_RE.match(r["year"] or "")}


def run_label(run_dir, root):
    return os.path.relpath(os.path.abspath(run_dir), os.path.abspath(root)) if root else run_dir


def delivered_record_id(source, rid):
    return rid if rid.startswith(f"{source}:") else f"{source}:{rid}"


def build(runs, root=None, languages=None):
    """``(records, registry, excluded, stats)`` from ``[(run_dir, sources|None)]``.

    ``languages`` maps a source to its lexicon languages (for the query text of
    harvest routes); by default read from the adapters.
    """
    if languages is None:
        languages = {n: m.SOURCE["languages"] for n, m in discover().items()}
    registry, records, excluded = OrderedDict(), OrderedDict(), []
    stats = Counter()
    for run_dir, sources in runs:
        label = run_label(run_dir, root)
        qmap = {}
        for r in read_csv(os.path.join(run_dir, "registry.csv")):
            if sources and r["source"] not in sources:
                continue
            qid = r["query_id"]
            if qid in registry:
                qid = f"{qid}@{label}"
            qmap[r["query_id"]] = qid
            harvest = r["route"] in HARVEST_ROUTES
            legacy = r["route"] in LEGACY_LISTING_ROUTES
            query = r["query_string"]
            if harvest or legacy:
                langs = "/".join(languages.get(r["source"], []))
                query += (f" || candidates selected by local 1530 lexicon match on "
                          f"title+abstract (titles only where the source gives no "
                          f"abstract), languages {langs}")
            registry[qid] = {
                "query_id": qid, "platform": r["source"], "query": query,
                "run_at": r["run_at"],
                "n_received": r["n_matched"] if harvest or legacy else r["n_received"],
                "completed": "true" if r["completed"] == "True" else "false",
                "stop_reason": r["stop_reason"],
                "filter": "local lexicon match" if harvest or legacy else "",
                "n_expected": r["n_received"] if harvest else r["n_expected"],
                "source": r["source"], "route": r["route"], "endpoint": r["endpoint"],
                "run_dir": label, "query_id_run": r["query_id"],
                "n_announced": r["n_expected"], "n_harvested": r["n_received"] if harvest else "",
                "n_delivered": 0,
            }
        enrich = read_enrichment(run_dir)
        for c in read_csv(os.path.join(run_dir, "candidates.csv")):
            if sources and c["source"] not in sources:
                continue
            qid = qmap[c["query_id"]]
            rid = delivered_record_id(c["source"], c["record_id"])
            if rid in records:
                kept = records[rid]
                kept["query_ids_all"] += f"; {qid}"
                excluded.append({"record_id": rid, "query_id": qid,
                                 "reason": "duplicate_in_lane", "title": c["title"],
                                 "note": f"also retrieved by {kept['query_id']}"})
                continue
            records[rid] = to_record(c, rid, qid, registry[qid], label, enrich, stats)
            registry[qid]["n_delivered"] += 1
    unshare_dois(records.values(), stats)
    delivered = []
    for rec in records.values():
        if rec["doi"] or rec["year"] or url_is_key(rec["url"]):
            if not (rec["doi"] or rec["year"]):
                stats["url_key_only"] += 1
            delivered.append(rec)
            continue
        stats["no_dedup_key"] += 1
        # No dedup key: records.csv refuses the row; the contract lists it here
        # and the pool merge still takes it in, as a title-only work.
        excluded.append({"record_id": rec["record_id"], "query_id": rec["query_id"],
                         "reason": "no_dedup_key", "title": rec["title"],
                         "note": no_key_note(rec), "url": rec["url"],
                         "platform_record_id": rec["platform_record_id"]})
        registry[rec["query_id"]]["n_delivered"] -= 1
    return delivered, list(registry.values()), excluded, stats


def same_title(a, b):
    """Two normalized titles of one work: one extends the other (a subtitle),
    or they share at least half their words (punctuation, encoding noise)."""
    if a.startswith(b) or b.startswith(a):
        return True
    wa, wb = set(a.split()), set(b.split())
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.5


def title_clusters(titles):
    """Number of distinct works among normalized titles (greedy clustering)."""
    heads = []
    for t in titles:
        if not any(same_title(t, h) for h in heads):
            heads.append(t)
    return len(heads)


def unshare_dois(records, stats):
    """Blank a DOI carried by records whose titles name different works.

    Such a DOI names an issue or a container, not the work (Redalyc: one DOI
    on 17 unrelated articles; a GARUDA template DOI ending in ``p%p``). Titles
    that differ only by a subtitle or by noise count as one work. A title and
    its translation count as two, so the DOI is blanked there too: the
    conservative side, since a missed join costs a duplicate to screen and a
    false one loses a work. The original stays in ``lane_note``."""
    titles = {}
    for rec in records:
        if rec["doi"]:
            titles.setdefault(rec["doi"], []).append(_norm(rec["title"]))
    works = {doi: title_clusters(ts) for doi, ts in titles.items()}
    for rec in records:
        doi = rec["doi"]
        if doi and works[doi] > 1:
            rec["doi"] = ""
            rec["lane_note"] = (f"source DOI {doi} is carried by {works[doi]} "
                                f"different works in this delivery, so it is not used "
                                f"as this record's key; " + rec["lane_note"])
            stats["doi_shared_blanked"] += 1


def to_record(c, rid, qid, reg, label, enrich, stats):
    notes = []
    doi = c["doi"] if DOI_RE.match(c["doi"] or "") else ""
    if not doi and c["doi"]:
        notes.append(f"source DOI {c['doi']!r} is malformed")
    year = c["year"] if YEAR_RE.match(c["year"] or "") else ""
    if not doi and not year:
        doi = find_doi([c["url"]])
        if doi and DOI_RE.match(doi):
            notes.append("DOI read from the record URL")
            stats["doi_from_url"] += 1
        else:
            doi = ""
    if not doi and not year and c["record_id"] in enrich:
        e = enrich[c["record_id"]]
        year = e["year"]
        notes.append(f"year from {e['source_url']} ({e['fetched_at'][:10]})")
        stats["year_enriched"] += 1
    authors = [a.strip() for a in (c["authors"] or "").split(";") if a.strip()]
    matched = c["matched_terms"]
    notes.append(f"lexicon match on title/abstract: {matched}" if matched
                 else "no lexicon phrase in title/abstract (full-text or all-words hit)")
    return {
        "record_id": rid, "query_id": qid, "platform": c["source"],
        "retrieved_at": reg["run_at"], "title": c["title"],
        "platform_record_id": c["record_id"], "doi": doi, "openalex_id": "",
        "title_original": "", "first_author": authors[0] if authors else "",
        "all_authors": "; ".join(authors), "year": year, "publication_date": "",
        "journal": c["venue"], "issn": "", "doc_type": c["doc_type"],
        "language": iso_language(c["language"]), "abstract": c["abstract"],
        "abstract_provenance": "", "url": c["url"], "affiliation_countries": "",
        "version_hint": "",
        "lane_status": "lexicon_match" if matched else "no_lexicon_match",
        "lane_note": "; ".join(notes),
        "source": c["source"], "route": c["route"], "endpoint": c["endpoint"],
        "run_dir": label, "export_file": os.path.join(label, c["export_file"]),
        "matched_terms": matched, "query_ids_all": qid, "language_raw": c["language"],
    }


def unreviewed_languages(status):
    """Languages with a query string no reviewer has read.

    Per-string review (``translation_review: {lang: {theme: {status: ...}}}``)
    supersedes the older bare ``unreviewed_languages`` list, still accepted.
    """
    review = status.get("translation_review")
    if review is None:
        return list(status.get("unreviewed_languages", []))
    return [lang for lang, themes in review.items()
            if any(t["status"] == "unreviewed" for t in themes.values())]


def disputed_strings(status):
    """``lang T#`` of every string one reviewer objected to and nobody changed."""
    return [f"{lang} {theme}"
            for lang, themes in (status.get("translation_review") or {}).items()
            for theme, t in themes.items() if t["status"] == "reviewed-disputed"]


def manifest(records, registry, excluded, stats, status, producer, delivery, notes=""):
    incomplete, needs_human = [], []
    by_source = {}
    for r in registry:
        by_source.setdefault(r["source"], []).append(r)
    for name, s in status["sources"].items():
        if s["status"] in {"partial", "impossible"}:
            incomplete.append({"unit": f"{name}: {s.get('stratum', '')}",
                               "reason": f"{s['status']}: {' '.join(s['reason'].split())}"})
        elif s["status"] == "run":
            short = [r for r in by_source.get(name, []) if r["completed"] != "true"]
            if short:
                why = Counter(r["stop_reason"] for r in short).most_common(3)
                incomplete.append({
                    "unit": f"{name}: {len(short)} of {len(by_source[name])} queries",
                    "reason": "; ".join(f"{w} ({n})" for w, n in why)})
        if s.get("needs_human"):
            needs_human.append({"item": s["needs_human"], "reason": f"{name}: {s['status']}"})
    langs = ", ".join(unreviewed_languages(status))
    disputed = disputed_strings(status)
    if disputed:
        incomplete.append({"unit": f"query strings {', '.join(disputed)}",
                           "reason": "reviewed-disputed: one of two reviewers objected, "
                                     "string kept as run"})
    if langs:
        incomplete.append({"unit": f"query strings in {langs}",
                           "reason": "machine-drafted, no competent reader reviewed them "
                                     "(non résolu)"})
        needs_human.append({"item": f"Competent readers for the {langs} query strings",
                            "reason": "exit criterion 3 of ticket 1653"})
    return {
        "lane": LANE, "ticket": TICKET, "delivery": delivery,
        "delivered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "producer": producer,
        "counts": {"records": len(records),
                   "excluded": dict(Counter(e["reason"] for e in excluded)),
                   "by_platform": dict(Counter(r["platform"] for r in records)),
                   "no_dedup_key": stats["no_dedup_key"],
                   "url_key_only": stats["url_key_only"],
                   "doi_from_url": stats["doi_from_url"],
                   "year_enriched": stats["year_enriched"],
                   "doi_shared_blanked": stats["doi_shared_blanked"]},
        "coverage": "incomplete",
        "incomplete": incomplete,
        "needs_human": needs_human,
        "supersedes": None,
        "notes": notes,
    }


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields)
        w.writeheader()
        w.writerows(rows)


def git_commit():
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def cmd_export(args):
    runs = [parse_run(a) for a in args.run]
    records, registry, excluded, stats = build(runs, root=args.root)
    with open(args.status, encoding="utf-8") as fh:
        status = yaml.safe_load(fh)
    os.makedirs(args.output_dir, exist_ok=True)
    write_csv(os.path.join(args.output_dir, "records.csv"),
              RECORD_COLUMNS + EXTRA_RECORD_COLUMNS, records)
    write_csv(os.path.join(args.output_dir, "registry.csv"), REGISTRY_COLUMNS, registry)
    write_csv(os.path.join(args.output_dir, "excluded.csv"),
              EXCLUDED_COLUMNS + ["url", "platform_record_id"], excluded)
    with open(args.sentinels, encoding="utf-8", newline="") as fh:
        sentinels = list(csv.DictReader(fh))
    report = sentinel_report(sentinels, [{**r, "query_id": r["query_ids_all"]} for r in records])
    write_csv(os.path.join(args.output_dir, "sentinels.csv"),
              ["sentinel", "found", "sources", "query_ids", "title"], report)
    producer = {"script": "scripts/catalog_rel_1653_delivery.py",
                "commit": args.commit or git_commit(),
                "machine": args.machine or socket.gethostname(),
                "runs": [a for a in args.run], "runs_root": args.root or ""}
    delivery = os.path.basename(os.path.abspath(args.output_dir))
    notes = args.notes or ""
    if stats["url_key_only"]:
        notes += (f" {stats['url_key_only']} record(s) have no DOI or year: their "
                  "persistent URL (a Handle) is their key.")
    if stats["no_dedup_key"]:
        notes += (f" {stats['no_dedup_key']} record(s) carry no DOI, OpenAlex id, year "
                  "or persistent URL anywhere in their source: listed in excluded.csv "
                  "as no_dedup_key, with their URL, for the pool to take in as "
                  "title-only works.")
    if stats["doi_shared_blanked"]:
        notes += (f" {stats['doi_shared_blanked']} record(s) had a source DOI shared with "
                  "differently titled records (issue-level DOIs); it is kept in lane_note, "
                  "not used as a key.")
    man = manifest(records, registry, excluded, stats, status, producer, delivery,
                   notes.strip())
    with open(os.path.join(args.output_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    log.info("counts %s", json.dumps(man["counts"], ensure_ascii=False))
    for s in report:
        log.info("%s %s %s %s", s["sentinel"], "found" if s["found"] else "missed",
                 s["sources"], s["query_ids"])
    return 0


def cmd_enrich_years(args, get=polite_get):
    """Detail-page years for the records with neither year nor DOI."""
    if args.source != "garuda":
        log.error("only garuda has a detail page with a publication date")
        return 2
    rows = read_csv(os.path.join(args.run_dir, "candidates.csv"))
    todo = list(dict.fromkeys(r["record_id"] for r in rows if r["source"] == args.source
                              and not YEAR_RE.match(r["year"] or "")
                              and not DOI_RE.match(r["doi"] or "")
                              and not find_doi([r["url"]])))
    out = []
    for rid in todo:
        url = garuda.detail_url(rid)
        fetched = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            resp = get(url, delay=args.delay)
            year = garuda.publish_year(resp.text) if resp.status_code == 200 else None
            state = "ok" if year else f"no date (http {resp.status_code})"
        except Exception as exc:  # one page lost: recorded, not fatal
            year, state = None, f"error: {type(exc).__name__}"
        out.append({"record_id": rid, "year": year or "", "source_url": url,
                    "fetched_at": fetched, "status": state})
    write_csv(os.path.join(args.run_dir, "year_enrichment.csv"), ENRICHMENT_FIELDS, out)
    log.info("%d of %d years found", sum(1 for o in out if o["year"]), len(out))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("--run", action="append", required=True,
                    help="run directory, optionally :source,source (repeatable)")
    ex.add_argument("--root", help="base the run_dir labels are relative to")
    # Multi-output (the four contract files + sentinels.csv): --output-dir.
    ex.add_argument("--output-dir", required=True)
    ex.add_argument("--status", default="config/rel_sud_sources_status.yaml")
    ex.add_argument("--sentinels", default="config/rel_sud_sentinels.csv")
    ex.add_argument("--commit")
    ex.add_argument("--machine")
    ex.add_argument("--notes")
    en = sub.add_parser("enrich-years")
    en.add_argument("--run-dir", required=True)
    en.add_argument("--source", required=True)
    en.add_argument("--delay", type=float, default=1.0,
                    help="seconds between requests (the runner's default; "
                         "GARUDA publishes no crawl-delay)")
    args = ap.parse_args(argv)
    return cmd_export(args) if args.cmd == "export" else cmd_enrich_years(args)


if __name__ == "__main__":
    sys.exit(main())
