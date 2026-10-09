"""Recover the missing resource type of pool works (ticket 2050).

Reads the blank-``doc_type`` works of a rebuilt REL pool (``pool.csv``) and asks
for their resource type on two routes:

* ``openalex``: ``filter=ids.openalex:W1|W2`` (works with an OpenAlex id) or
  ``filter=doi:...`` (works with a DOI only), 100 per call, ``select=id,doi,type``;
  metered with the ``Meter`` of ``_rel_meter`` (lane cap, daily floor);
* ``crossref``: ``/works/<doi>`` one request at a time, 1 per second, for the
  works with a DOI that OpenAlex did not answer with a type (or for every DOI
  with ``--crossref-scope all``, to measure agreement).

Raw answers go to append-only JSONL archives next to a ``done`` ledger per
route; the ledger row is written after the records, so a crash leaves a batch
pending, never lost. A rerun asks only for what is pending. A 429, a network
error or an exhausted budget stops the run at once: there is no retry loop. No
archive is ever overwritten.

``--merge`` makes no call: it maps the raw types into the pool vocabulary and
writes ``doc_types.csv`` (one row per recovered work, only for works whose pool
``doc_type`` is blank) and ``coverage.csv`` (per catalogue source, period and
language). It refuses to overwrite an existing ``doc_types.csv``.

Usage:
    python scripts/catalog_rel_doc_type_recover.py --pool POOL.csv --output-dir DIR --dry-run
    python scripts/catalog_rel_doc_type_recover.py --pool POOL.csv --output-dir DIR \\
        --route openalex [--max-batches 1] [--lane-cap 0.5 --daily-floor 0.1]
    python scripts/catalog_rel_doc_type_recover.py --pool POOL.csv --output-dir DIR --route crossref
    python scripts/catalog_rel_doc_type_recover.py --pool POOL.csv --output-dir DIR --merge
"""

import argparse
import csv
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import requests
from _rel_meter import Meter
from pipeline_keystore import read_credential
from utils import MAILTO, get_logger, normalize_doi

log = get_logger("rel_doc_type_recover")

OA_API = "https://api.openalex.org/works"
CR_API = "https://api.crossref.org/works/"
BATCH = 100  # verified OpenAlex limit for an id filter (ticket 2041 log)
SELECT = "id,doi,type"
ACTS = ((1990, 2006, "1990-2006"), (2007, 2014, "2007-2014"), (2015, 2025, "2015-2025"))
DONE_STATUSES = ("found", "absent")
OUT_FILE = "doc_types.csv"

# Raw type -> the pool's doc_type vocabulary. A value in neither table is kept
# as delivered and counted under ``unmapped``: it is never replaced by a guess.
# OpenAlex already speaks the lanes' vocabulary (the pool holds ``article`` 108,705,
# ``review``, ``dataset``, ``conference-abstract``... from OpenAlex-fed lanes), so
# its types pass through unchanged; the table only names the ones seen in the pool.
OPENALEX_MAP = {t: t for t in (
    "article", "book-chapter", "book", "dissertation", "preprint", "report", "review",
    "letter", "editorial", "erratum", "other", "dataset", "conference-paper",
    "conference-abstract", "paratext", "peer-review", "reference-entry", "standard",
    "software", "retraction", "supplementary-materials", "data-paper")}
# Crossref keeps its own spelling where the pool has it (``journal-article`` 204,458)
# and is folded onto the pool's word where Crossref uses another.
CROSSREF_MAP = {
    "journal-article": "journal-article", "book-chapter": "book-chapter",
    "book-section": "book-chapter", "book-part": "book-chapter",
    "book": "book", "monograph": "book", "edited-book": "book", "reference-book": "book",
    "dissertation": "dissertation", "posted-content": "preprint",
    "proceedings-article": "conference-paper", "report": "report",
    "report-component": "report", "dataset": "dataset", "reference-entry": "reference-entry",
    "peer-review": "peer-review", "standard": "standard", "journal-issue": "journal-issue",
    "other": "other",
}
# Pairs (OpenAlex, Crossref) that name the same thing: not a disagreement.
EQUIVALENT = {("article", "journal-article"), ("preprint", "posted-content"),
              ("book", "monograph"), ("book", "edited-book"), ("book", "reference-book"),
              ("conference-paper", "proceedings-article"), ("report", "report-component"),
              ("book-chapter", "book-section"), ("book-chapter", "book-part")}


# --- pool targets --------------------------------------------------------------

def _act(year):
    try:
        y = int(year)
    except (TypeError, ValueError):
        return "unknown"
    return next((name for lo, hi, name in ACTS if lo <= y <= hi), "other")


def read_targets(pool_path):
    """Blank-``doc_type`` pool works that carry an identifier, in pool order."""
    csv.field_size_limit(10**9)
    targets = []
    with open(pool_path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get("doc_type") or "").strip():
                continue
            oa = (r.get("openalex_id") or "").rsplit("/", 1)[-1]
            doi = normalize_doi(r.get("doi"))
            if not (oa or doi):
                continue
            targets.append({
                "openalex_id": oa, "doi": doi,
                "source": (r.get("catalogue_sources") or "").split(";")[0] or "lane-only",
                "period": _act(r.get("year")), "language": r.get("language") or ""})
    return targets


def lookup_key(t):
    return t["openalex_id"] or t["doi"]


# --- ledgers and archives (append only) -----------------------------------------

def _path(out_dir, name):
    return os.path.join(out_dir, name)


def read_done(out_dir, route):
    path = _path(out_dir, f"{route}_done.csv")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        # a row cut short by a crash has no status: that key is still pending
        return {r["key"]: r["status"] for r in csv.DictReader(fh)
                if r.get("status") in DONE_STATUSES}


def read_records(out_dir, route):
    """Archived answers of a route; a line cut by a crash is skipped."""
    path = _path(out_dir, f"{route}.jsonl")
    recs = {}
    if not os.path.exists(path):
        return recs
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            recs[r["key"]] = r
    return recs


def _append_lines(path, lines):
    """Append, first closing a line a crash left open."""
    if os.path.exists(path) and os.path.getsize(path):
        with open(path, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                lines = ["", *lines]
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def write_batch(out_dir, route, records, statuses):
    """Records first, then the done rows."""
    if records:
        _append_lines(_path(out_dir, f"{route}.jsonl"),
                      [json.dumps(r, ensure_ascii=False) for r in records])
    path = _path(out_dir, f"{route}_done.csv")
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new:
            w.writerow(["key", "status"])
        w.writerows(statuses)


# --- OpenAlex route -----------------------------------------------------------------

def oa_batches(targets, done, size=BATCH):
    """Batches of one kind each: ``("ids.openalex", [W...])`` or ``("doi", [10...])``."""
    by_id = [t["openalex_id"] for t in targets if t["openalex_id"] and t["openalex_id"] not in done]
    by_doi = [t["doi"] for t in targets if not t["openalex_id"] and t["doi"] not in done]
    out = [("ids.openalex", by_id[i:i + size]) for i in range(0, len(by_id), size)]
    return out + [("doi", by_doi[i:i + size]) for i in range(0, len(by_doi), size)]


def oa_get(params):
    """One request, no retry; the error is the caller's stop reason."""
    return requests.get(OA_API, params=params, timeout=30,
                        headers={"User-Agent": f"ClimateFinancePipeline/1.0 (mailto:{MAILTO})"})


def fetch_openalex(kind, keys, api_key, meter, get=oa_get):
    """(works, stop_reason, cost); stop_reason '' when the batch is whole."""
    if reason := meter.stop_reason():
        return [], reason, 0.0
    values = keys if kind == "ids.openalex" else [f"https://doi.org/{k}" for k in keys]
    params = {"filter": f"{kind}:" + "|".join(values), "select": SELECT,
              # room for two works per key: one DOI can match two OpenAlex works (batch 313 of
              # the bulk run returned 101 for 100 DOIs and stopped on the short-page guard)
              "per_page": min(200, 2 * len(keys)), "mailto": MAILTO, "api_key": api_key}
    before = meter.spent
    try:
        resp = get(params)
    except requests.RequestException as exc:
        return [], f"error: {type(exc).__name__}", 0.0
    meter.observe(resp.headers)
    cost = meter.spent - before
    if resp.status_code == 429:
        return [], "rate limited or budget exhausted (429)", cost
    if resp.status_code != 200:
        return [], f"http {resp.status_code}", cost
    try:
        body = resp.json()
        works, count = body["results"], body["meta"]["count"]
    except (ValueError, KeyError, TypeError):
        return [], "error: bad body", cost
    if "insufficient" in json.dumps(body.get("meta", {})).lower():
        return [], "insufficient budget", cost
    if count > len(works):
        return [], f"short page: {len(works)} of {count}", cost
    return works, "", cost


def oa_records(kind, keys, works, by_key):
    """(records, statuses): one record per requested key, found or absent."""
    ids = {(w.get("id") or "").rsplit("/", 1)[-1]: w for w in works}
    dois = {}
    for w in works:  # a DOI shared by two works keeps the first listed, with its match count
        if w.get("doi"):
            dois.setdefault(normalize_doi(w["doi"]), []).append(w)
    records, statuses = [], []
    for k in keys:
        t = by_key[k]
        w = ids.get(t["openalex_id"])
        matches = 1
        if w is None and t["doi"] and dois.get(t["doi"]):
            w, matches = dois[t["doi"]][0], len(dois[t["doi"]])
        if w is None:
            statuses.append((k, "absent"))
            continue
        records.append({"key": k, "openalex_id": (w.get("id") or "").rsplit("/", 1)[-1],
                        "doi": normalize_doi(w.get("doi")), "type": w.get("type") or "",
                        "matches": matches})
        statuses.append((k, "found"))
    return records, statuses


def run_openalex(args, targets, api_key, fetch=fetch_openalex):
    by_key = {lookup_key(t): t for t in targets}
    done = read_done(args.output_dir, "openalex")
    todo = oa_batches(targets, done, args.batch)
    if args.dry_run:
        price(len(todo), args)
        return ""
    os.makedirs(args.output_dir, exist_ok=True)
    meter = Meter(args.lane_cap, args.daily_floor)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    costs, stop = [], ""
    for k, (kind, keys) in enumerate(todo):
        if args.max_batches and k >= args.max_batches:
            stop = f"max batches {args.max_batches}"
            break
        works, stop, cost = fetch(kind, keys, api_key, meter)
        if cost:
            costs.append(round(cost, 6))
        if stop:
            break
        recs, statuses = oa_records(kind, keys, works, by_key)
        write_batch(args.output_dir, "openalex", recs, statuses)
        log.info("batch %d/%d (%s): %d of %d found, cost %.6f USD, daily remaining %s",
                 k + 1, len(todo), kind, len(recs), len(keys), cost, meter.remaining)
    with open(_path(args.output_dir, "spend.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "route": "openalex", "started": started,
            "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "requests": meter.requests, "run_spent_usd": round(meter.spent, 6),
            "cost_per_call_usd": costs, "daily_remaining_usd_at_end": meter.remaining,
            "lane_cap_usd": meter.lane_cap, "daily_floor_usd": meter.daily_floor,
            "stopped": stop}) + "\n")
    log.info("openalex: spent %.6f USD in %d requests; %s", meter.spent, meter.requests,
             stop or "ran to the end")
    return stop


def price(n_calls, args):
    log.info("%d calls of up to %d keys", n_calls, args.batch)
    if args.cost_per_call is not None:
        total = args.cost_per_call * n_calls
        log.info("derived: %.4f USD per call x %d calls = %.4f USD; %d day(s) at %.2f USD/day",
                 args.cost_per_call, n_calls, total,
                 max(1, math.ceil(total / args.daily_budget)), args.daily_budget)


# --- Crossref route ---------------------------------------------------------------------

def cr_get(doi):
    return requests.get(CR_API + requests.utils.quote(doi, safe="/"),
                        params={"mailto": MAILTO}, timeout=30,
                        headers={"User-Agent": f"ClimateFinancePipeline/1.0 (mailto:{MAILTO})"})


def crossref_pending(targets, oa_recs, done, scope):
    """DOIs still to ask: those OpenAlex left without a type (``unanswered``) or all."""
    out = []
    for t in targets:
        if not t["doi"] or t["doi"] in done:
            continue
        if scope == "unanswered":
            rec = oa_recs.get(lookup_key(t))
            if rec and rec["type"]:
                continue
        out.append(t["doi"])
    return list(dict.fromkeys(out))


def run_crossref(args, targets, get=cr_get, sleep=time.sleep):
    oa_recs = read_records(args.output_dir, "openalex")
    done = read_done(args.output_dir, "crossref")
    pending = crossref_pending(targets, oa_recs, done, args.crossref_scope)
    if args.dry_run:
        log.info("crossref: %d DOIs pending, about %d s at 1 request per second",
                 len(pending), len(pending))
        return ""
    os.makedirs(args.output_dir, exist_ok=True)
    stop = ""
    for k, doi in enumerate(pending):
        if args.max_batches and k >= args.max_batches:
            stop = f"max requests {args.max_batches}"
            break
        try:
            resp = get(doi)
        except requests.RequestException as exc:
            stop = f"error: {type(exc).__name__}"
            break
        if resp.status_code == 429:
            stop = "rate limited (429)"
            break
        if resp.status_code == 404:
            write_batch(args.output_dir, "crossref", [], [(doi, "absent")])
        elif resp.status_code == 200:
            try:
                msg = resp.json()["message"]
            except (ValueError, KeyError, TypeError):
                stop = "error: bad body"
                break
            write_batch(args.output_dir, "crossref",
                        [{"key": doi, "doi": doi, "type": msg.get("type") or ""}],
                        [(doi, "found")])
        else:
            stop = f"http {resp.status_code}"
            break
        sleep(args.crossref_delay)
    log.info("crossref: %d requests planned; %s", len(pending), stop or "ran to the end")
    return stop


# --- merge: map, decide, report ------------------------------------------------------------

def map_type(raw, table):
    """(pool doc_type, mapped): an unknown raw value is kept as delivered."""
    if not raw:
        return "", False
    if raw in table:
        return table[raw], True
    return raw, False


def decide(oa_type, cr_type):
    """(doc_type, rule). OpenAlex wins where both answer: it keys the same record
    the catalogue came from and speaks the lanes' vocabulary; Crossref fills where
    OpenAlex has no type. Disagreements are counted by the caller."""
    oa, oa_known = map_type(oa_type, OPENALEX_MAP)
    cr, cr_known = map_type(cr_type, CROSSREF_MAP)
    if oa:
        rule = "openalex" + ("" if oa_known else "-unmapped")
        if cr_type and oa_type != cr_type and (oa_type, cr_type) not in EQUIVALENT:
            rule += "+crossref-differs"
        return oa, rule
    if cr:
        return cr, "crossref" + ("" if cr_known else "-unmapped")
    return "", "none"


def merge(args, targets):
    out_path = _path(args.output_dir, OUT_FILE)
    if os.path.exists(out_path):
        raise SystemExit(f"{out_path} exists: refusing to overwrite an archive")
    oa_recs = read_records(args.output_dir, "openalex")
    cr_recs = read_records(args.output_dir, "crossref")
    rows, rules, cover, unmapped = [], Counter(), {}, Counter()
    for t in targets:
        rec = oa_recs.get(lookup_key(t)) or {}
        cr = cr_recs.get(t["doi"]) or {} if t["doi"] else {}
        doc_type, rule = decide(rec.get("type", ""), cr.get("type", ""))
        c = cover.setdefault((t["source"], t["period"], t["language"]), Counter())
        c["n"] += 1
        c["openalex"] += bool(rec.get("type"))
        c["crossref"] += bool(cr.get("type"))
        c["recovered"] += bool(doc_type)
        rules[rule] += 1
        for route, raw, table in (("openalex", rec.get("type"), OPENALEX_MAP),
                                  ("crossref", cr.get("type"), CROSSREF_MAP)):
            if raw and raw not in table:
                unmapped[(route, raw)] += 1
        if doc_type:
            rows.append((t["openalex_id"], t["doi"], doc_type, rec.get("type", ""),
                         cr.get("type", ""), rule))
    with open(out_path, "x", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["openalex_id", "doi", "doc_type", "openalex_type", "crossref_type", "rule"])
        w.writerows(rows)
    with open(_path(args.output_dir, "coverage.csv"), "w", encoding="utf-8", newline="") as fh:
        cols = ["n", "openalex", "crossref", "recovered"]
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["source", "period", "language", *cols])
        for key in sorted(cover):
            w.writerow([*key, *(cover[key][c] for c in cols)])
    log.info("%d of %d works recovered; rules %s; unmapped %s", len(rows), len(targets),
             dict(rules), dict(unmapped))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pool", required=True, help="pool.csv of a rebuilt REL pool")
    # Multi-output: raw archives, done ledgers, spend ledger, doc_types.csv, coverage.csv.
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--route", choices=("openalex", "crossref"), default="openalex")
    ap.add_argument("--crossref-scope", choices=("unanswered", "all"), default="unanswered")
    ap.add_argument("--crossref-delay", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--lane-cap", type=float, default=0.5, help="spend cap of this run in USD")
    ap.add_argument("--daily-floor", type=float, default=0.1,
                    help="stop when x-ratelimit-remaining-usd falls below this")
    ap.add_argument("--max-batches", type=int, default=0, help="0 = no limit")
    ap.add_argument("--dry-run", action="store_true", help="plan and price; no key, no call")
    ap.add_argument("--cost-per-call", type=float, default=None,
                    help="measured USD per call, to price a dry run")
    ap.add_argument("--daily-budget", type=float, default=1.0)
    ap.add_argument("--merge", action="store_true", help="map and report; no call")
    args = ap.parse_args(argv)
    targets = read_targets(args.pool)
    log.info("%d blank-doc_type works with an identifier", len(targets))
    if args.merge:
        merge(args, targets)
        return 0
    if args.dry_run:
        if args.route == "openalex":
            run_openalex(args, targets, None)
        else:
            run_crossref(args, targets)
        return 0
    if args.route == "crossref":
        return 1 if run_crossref(args, targets) else 0
    api_key = read_credential("openalex", "OPENALEX_API_KEY")
    if not api_key:
        log.error("OPENALEX_API_KEY is unavailable: refusing the unauthenticated pool")
        return 2
    return 1 if run_openalex(args, targets, api_key) not in ("", f"max batches {args.max_batches}") else 0


if __name__ == "__main__":
    sys.exit(main())
