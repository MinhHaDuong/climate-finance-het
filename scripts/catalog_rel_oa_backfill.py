"""Backfill authors and host organizations of already-harvested OpenAlex works (ticket 2041).

The older REL lanes (t1530, t1650, t1652, t1790) stored slim records that
dropped the authors, the host organization, the source type, the ISSNs and the
landing page. This script re-fetches those works by OpenAlex id, up to 200 per
call (``filter=ids.openalex:W1|W2|...``), and keeps the fields the shared
``slim()`` keeps now. Nothing is written into the lane deliveries: the
delivery scripts read the backfill and fill only blank cells.

Metered like the search collectors (``Meter`` of ``catalog_rel_causal_search``):
a lane cap in USD, a floor on the day's remaining budget, a stop on 429 and on
an "insufficient" answer. Resumable: ``done.csv`` records every id of a batch
once its records are on disk, so an interrupted run is never counted complete
and a rerun asks only for the ids still pending. Without ``OPENALEX_API_KEY``
the run refuses to start rather than fall back to the unauthenticated pool.

Usage:
    python scripts/catalog_rel_oa_backfill.py --ids RUN/results.jsonl.gz [--ids ...] \\
        --output-dir data/rel_backfill/2041 --dry-run [--cost-per-call USD]
    python scripts/catalog_rel_oa_backfill.py --ids ... --output-dir ... \\
        --lane-cap 5 --daily-floor 0.1 [--max-batches 1]
    python scripts/catalog_rel_oa_backfill.py --ids ... --output-dir ... --report
"""

import argparse
import csv
import gzip
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone

from _rel_meter import Meter
from catalog_rel_sud_search import (
    BACKFILL_FILE,
    OA_API,
    author_names,
    read_backfill,
    venue_fields,
)
from pipeline_keystore import read_credential
from utils import MAILTO, get_logger, polite_get

log = get_logger("rel_oa_backfill")

BATCH = 200
SELECT = "id,authorships,primary_location,locations"
DATA_FILE = BACKFILL_FILE
DONE_FILE = "done.csv"
SPEND_FILE = "spend.jsonl"
ACTS = ((1990, 2006, "1990-2006"), (2007, 2014, "2007-2014"), (2015, 2025, "2015-2025"))


def backfill_record(work):
    """The fields one re-fetched work contributes, named like the slim keys."""
    names = author_names(work)
    others = []
    for loc in work.get("locations") or []:
        src = loc.get("source") or {}
        org = src.get("host_organization_name")
        if org and org not in others:
            others.append(org)
    return {
        "openalex_id": (work.get("id") or "").rsplit("/", 1)[-1],
        "first_author": names[0] if names else "",
        "all_authors": names,
        **venue_fields(work),
        # host organizations of the non-primary locations, as information
        "location_hosts": others,
    }


# --- inputs, state ------------------------------------------------------------

def _lane_of(path):
    return os.path.basename(os.path.dirname(os.path.abspath(path)))


def read_ids(paths):
    """(ordered unique ids, {id: {lane, year, language}}) of the id sources.

    A source is a ``results.jsonl.gz`` (key ``openalex_id``), a CSV with an
    ``openalex_id`` column, or a text file of one id per line; the lane is the
    name of the source's directory."""
    meta = {}
    for path in paths:
        lane = _lane_of(path)
        if path.endswith(".gz") or path.endswith(".jsonl"):
            opener = gzip.open if path.endswith(".gz") else open
            with opener(path, "rt", encoding="utf-8") as fh:
                rows = (json.loads(line) for line in fh if line.strip())
                for r in rows:
                    _note(meta, r.get("openalex_id"), lane, r.get("year"), r.get("language"))
        elif path.endswith(".csv"):
            csv.field_size_limit(10**8)
            with open(path, encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    _note(meta, r.get("openalex_id"), lane, r.get("year"), r.get("language"))
        else:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    _note(meta, line.strip(), lane, None, None)
    return list(meta), meta


def _note(meta, wid, lane, year, language):
    wid = (wid or "").rsplit("/", 1)[-1]
    if wid and wid not in meta:
        meta[wid] = {"lane": lane, "year": year, "language": language}


def read_done(out_dir):
    path = os.path.join(out_dir, DONE_FILE)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        return {r["openalex_id"]: r["status"] for r in csv.DictReader(fh)}


def batches(ids, size=BATCH):
    return [ids[i:i + size] for i in range(0, len(ids), size)]


def _write_batch(out_dir, batch, works):
    """One complete gzip member of records, then the done rows: a crash between
    the two leaves records without done rows (refetched, deduplicated on read),
    never done rows without records."""
    with gzip.open(os.path.join(out_dir, DATA_FILE), "at", encoding="utf-8") as fh:
        for w in works:
            fh.write(json.dumps(backfill_record(w), ensure_ascii=False) + "\n")
    got = {(w.get("id") or "").rsplit("/", 1)[-1] for w in works}
    path = os.path.join(out_dir, DONE_FILE)
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new:
            w.writerow(["openalex_id", "status"])
        w.writerows([(i, "found" if i in got else "absent") for i in batch])


# --- the metered fetch --------------------------------------------------------

def fetch_batch(batch, api_key, delay, meter):
    """(works, stop_reason, cost): stop_reason '' when the batch is complete."""
    if reason := meter.stop_reason():
        return [], reason, 0.0
    params = {"filter": "ids.openalex:" + "|".join(batch), "select": SELECT,
              "per_page": len(batch), "mailto": MAILTO, "api_key": api_key}
    before = meter.spent
    try:
        resp = polite_get(OA_API, params=params, delay=delay)
    except Exception as exc:  # network failure after retries
        return [], f"error: {type(exc).__name__}", 0.0
    meter.observe(resp.headers)
    cost = meter.spent - before
    if resp.status_code == 429:
        return [], "rate limited or budget exhausted", cost
    if resp.status_code != 200:
        return [], f"http {resp.status_code}", cost
    try:
        body = resp.json()
        works, count = body["results"], body["meta"]["count"]
    except (ValueError, KeyError, TypeError):
        return [], "error: bad body", cost
    if "insufficient" in json.dumps(body.get("meta", {})).lower():
        return [], "insufficient budget", cost
    if count > len(works):  # more matches than one page: the batch is not whole
        return [], f"short page: {len(works)} of {count}", cost
    return works, "", cost


def plan(ids, done, size=BATCH):
    pending = [i for i in ids if i not in done]
    return pending, batches(pending, size)


def run(args, api_key, fetch=fetch_batch):
    ids, _ = read_ids(args.ids)
    done = read_done(args.output_dir) if os.path.isdir(args.output_dir) else {}
    pending, todo = plan(ids, done, args.batch)
    if args.dry_run:
        log.info("%d ids, %d done, %d pending, %d batches of up to %d",
                 len(ids), len(ids) - len(pending), len(pending), len(todo), args.batch)
        if args.cost_per_call is not None:
            total = args.cost_per_call * len(todo)
            log.info("derived: %.4f USD per call x %d batches = %.2f USD; %d days at %.2f USD/day",
                     args.cost_per_call, len(todo), total,
                     math.ceil(total / args.daily_budget), args.daily_budget)
        return 0
    if not api_key:
        log.error("OPENALEX_API_KEY is unavailable: refusing the unauthenticated pool")
        return 2
    os.makedirs(args.output_dir, exist_ok=True)
    meter = Meter(args.lane_cap, args.daily_floor)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    costs, stop, n_found = [], "", 0
    for k, batch in enumerate(todo):
        if args.max_batches and k >= args.max_batches:
            stop = f"max batches {args.max_batches}"
            break
        works, stop, cost = fetch(batch, api_key, args.delay, meter)
        if cost:
            costs.append(round(cost, 6))
        if stop:
            break
        _write_batch(args.output_dir, batch, works)
        n_found += len(works)
        log.info("batch %d/%d: %d of %d found, cost %.6f USD, daily remaining %s",
                 k + 1, len(todo), len(works), len(batch), cost, meter.remaining)
    done_after = read_done(args.output_dir)
    with open(os.path.join(args.output_dir, SPEND_FILE), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "started": started, "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "requests": meter.requests, "run_spent_usd": round(meter.spent, 6),
            "cost_per_call_usd": costs, "daily_remaining_usd_at_end": meter.remaining,
            "prepaid_remaining_usd_at_end": meter.prepaid, "lane_cap_usd": meter.lane_cap,
            "daily_floor_usd": meter.daily_floor, "stopped": stop,
            "done_total": len(done_after), "ids_total": len(ids)}) + "\n")
    complete = all(i in done_after for i in ids)
    log.info("spent %.6f USD in %d requests; %d/%d ids done%s; %s", meter.spent, meter.requests,
             len(done_after), len(ids), "" if complete else " (INCOMPLETE)", stop or "ran to the end")
    return 0


# --- coverage report ----------------------------------------------------------

def _act(year):
    try:
        y = int(year)
    except (TypeError, ValueError):
        return "unknown"
    return next((name for lo, hi, name in ACTS if lo <= y <= hi), "other")


def coverage(ids, meta, done, records):
    """Per (lane, period, language): works, done, with authors, with a host
    organization, with neither. Works not yet backfilled count in ``n`` only."""
    rows = {}
    for i in ids:
        m = meta[i]
        key = (m["lane"], _act(m["year"]), m["language"] or "")
        r = rows.setdefault(key, Counter())
        r["n"] += 1
        if i not in done:
            continue
        r["done"] += 1
        rec = records.get(i) or {}
        a, h = bool(rec.get("all_authors")), bool(rec.get("host_org_name"))
        r["authors"] += a
        r["host_org"] += h
        r["neither"] += (not a and not h)
    return rows


def write_coverage(path, rows):
    cols = ["lane", "period", "language", "n", "done", "authors", "host_org", "neither"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for key in sorted(rows):
            r = rows[key]
            w.writerow([*key, *(r[c] for c in cols[3:])])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids", action="append", required=True,
                    help="results.jsonl.gz, CSV with openalex_id, or text file; repeat")
    # Multi-output: backfill records, done ledger, spend ledger, coverage report.
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--lane-cap", type=float, default=0.5,
                    help="spend cap of this run in USD")
    ap.add_argument("--daily-floor", type=float, default=0.1,
                    help="stop when x-ratelimit-remaining-usd falls below this")
    ap.add_argument("--max-batches", type=int, default=0, help="0 = no limit (1 = a probe)")
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument("--dry-run", action="store_true", help="plan and price; no key, no call")
    ap.add_argument("--cost-per-call", type=float, default=None,
                    help="measured USD per call, to price a dry run")
    ap.add_argument("--daily-budget", type=float, default=1.0)
    ap.add_argument("--report", action="store_true",
                    help="write coverage.csv per lane, period and language; no call")
    args = ap.parse_args(argv)
    if args.report:
        ids, meta = read_ids(args.ids)
        rows = coverage(ids, meta, read_done(args.output_dir), read_backfill(args.output_dir))
        write_coverage(os.path.join(args.output_dir, "coverage.csv"), rows)
        log.info("coverage.csv: %d strata", len(rows))
        return 0
    api_key = None if args.dry_run else read_credential("openalex", "OPENALEX_API_KEY")
    return run(args, api_key)


if __name__ == "__main__":
    sys.exit(main())
