"""Incremental OpenAlex venue cache for the REL pool (ticket 1841).

The pool (``data/rel_pool/pool.csv``) carries a free-text ``journal`` only. A
work's venue identity (OpenAlex source id, ISSN-L, ISSNs, host organization,
source type, landing-page URL) comes from OpenAlex, keyed by the work's
OpenAlex id. This script fetches it for every OpenAlex id in the pool
(``all_openalex_ids``) that the cache does not hold yet, 100 ids per request
(``filter=ids.openalex:W1|W2|…`` with ``select=``), and appends to the cache.
A pool rebuild therefore costs only its new ids.

Cost: one request per 100 ids; OpenAlex bills a filtered list request one
credit (0.0001 USD, measured 2026-10-01 from the ``X-RateLimit-Cost-USD``
before a wave would take the day's budget below ``--budget-floor`` (0.2 USD);
rerun after the reset.
before a wave would take the day's budget below `--budget-floor` (0.2 USD); rerun after the reset.

Cache (``--output``, default ``data/rel_venues/openalex_work_venues.csv``): one
row per requested id, sorted by ``openalex_id`` on every write. An id
OpenAlex no longer returns (merged or deleted) gets ``status=not_found`` so it
is not requested again. The venue is the primary location's source; when the
primary location has none, the first other location whose source is a journal,
then any source (``location`` says which).

Usage:
    python scripts/enrich_rel_venues_openalex.py [--pool data/rel_pool/pool.csv]
        [--output data/rel_venues/openalex_work_venues.csv] [--dry-run] [--max-requests N]
"""

import argparse
import csv
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from _rel_pool_keys import norm_openalex
from pipeline_io import polite_get
from pipeline_keystore import read_credential
from utils import get_logger

log = get_logger("enrich_rel_venues_openalex")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OA_API = "https://api.openalex.org/works"
BATCH = 100
SELECT = "id,type,primary_location,locations"

CACHE_COLUMNS = ["openalex_id", "status", "work_type", "location", "source_id",
                 "source_name", "source_type", "issn_l", "issns", "host_org_id",
                 "host_org_name", "host_lineage_names", "is_in_doaj", "landing_url"]


def _short(url):
    return str(url or "").rsplit("/", 1)[-1]


def _pick_location(work):
    """``(label, location)`` carrying the work's venue, or ``("", None)``."""
    primary = work.get("primary_location") or {}
    if primary.get("source"):
        return "primary", primary
    others = [loc for loc in (work.get("locations") or []) if loc and loc.get("source")]
    for loc in others:
        if (loc["source"].get("type") or "") == "journal":
            return "other_journal", loc
    if others:
        return "other", others[0]
    return "", primary or None


def venue_row(work):
    """One cache row from an OpenAlex work object."""
    label, loc = _pick_location(work)
    src = (loc or {}).get("source") or {}
    return {
        "openalex_id": _short(work.get("id")).upper(),
        "status": "found",
        "work_type": work.get("type") or "",
        "location": label,
        "source_id": _short(src.get("id")),
        "source_name": src.get("display_name") or "",
        "source_type": src.get("type") or "",
        "issn_l": src.get("issn_l") or "",
        "issns": ";".join(sorted(set(src.get("issn") or []))),
        "host_org_id": _short(src.get("host_organization")),
        "host_org_name": src.get("host_organization_name") or "",
        "host_lineage_names": ";".join(src.get("host_organization_lineage_names") or []),
        "is_in_doaj": "" if src.get("is_in_doaj") is None else str(bool(src.get("is_in_doaj"))).lower(),
        "landing_url": (loc or {}).get("landing_page_url") or "",
    }


def pool_ids(pool_path):
    """Every OpenAlex id named by a pool work, sorted."""
    ids = set()
    with open(pool_path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            for x in (r.get("all_openalex_ids") or "").split(";"):
                oid = norm_openalex(x)
                if oid:
                    ids.add(oid)
    return sorted(ids)


def load_cache(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        return {r["openalex_id"]: r for r in csv.DictReader(fh)}


def write_cache(path, rows):
    """Write the cache sorted by id, atomically."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CACHE_COLUMNS, lineterminator="\n")
        w.writeheader()
        for oid in sorted(rows):
            w.writerow({c: rows[oid].get(c, "") for c in CACHE_COLUMNS})
    os.replace(tmp, path)


def fetch_batch(ids, api_key):
    """Cache rows for one batch of ids; ids absent from the reply are ``not_found``."""
    params = {"filter": "ids.openalex:" + "|".join(ids), "select": SELECT,
              "per_page": BATCH}
    if api_key:
        params["api_key"] = api_key
    resp = polite_get(OA_API, params=params, delay=0.1)
    resp.raise_for_status()
    found = {}
    for work in resp.json().get("results", []):
        row = venue_row(work)
        found[row["openalex_id"]] = row
    out = {}
    for oid in ids:
        out[oid] = found.get(oid) or {"openalex_id": oid, "status": "not_found"}
    # A merged id comes back under its new id: keep that row too, it is a venue.
    for oid, row in found.items():
        out.setdefault(oid, row)
    return out, resp.headers.get("X-RateLimit-Remaining-USD", "?")


def _below_floor(remaining, cost, floor):
    """True when spending ``cost`` would take the reported budget below ``floor``.

    An unreadable budget header counts as below: the run does not spend blind.
    """
    try:
        return float(remaining) - cost < floor
    except (TypeError, ValueError):
        return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--pool", default=os.path.join(ROOT, "data", "rel_pool", "pool.csv"))
    ap.add_argument("--output", default=os.path.join(ROOT, "data", "rel_venues",
                                                    "openalex_work_venues.csv"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-requests", type=int, default=0, help="0 = no cap")
    ap.add_argument("--checkpoint-every", type=int, default=50)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--budget-floor", type=float, default=0.2,
                    help="stop before a wave would take the daily budget below this (USD)")
    args = ap.parse_args(argv)

    cache = load_cache(args.output)
    todo = [i for i in pool_ids(args.pool) if i not in cache]
    n_req = -(-len(todo) // BATCH)
    log.info("cache holds %d ids; %d to fetch in %d requests (about %.4f USD at 0.0001 each)",
             len(cache), len(todo), n_req, n_req * 0.0001)
    if args.dry_run or not todo:
        return 0
    api_key = read_credential("openalex", "OPENALEX_API_KEY")
    batches = [todo[s:s + BATCH] for s in range(0, len(todo), BATCH)]
    if args.max_requests:
        batches = batches[:args.max_requests]
    done = 0
    _, remaining = fetch_batch(batches[0][:1], api_key)
    log.info("daily budget before the run: %s USD (floor %.2f)", remaining, args.budget_floor)
    # Requests run a few at a time; each wave is checkpointed, and the run
    # stops before a wave whose cost would take the daily budget below the floor.
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for w in range(0, len(batches), args.checkpoint_every):
            wave_cost = len(batches[w:w + args.checkpoint_every]) * 0.0001
            if _below_floor(remaining, wave_cost, args.budget_floor):
                log.warning("stopping after %d requests: daily budget %s USD, floor %.2f",
                            done, remaining, args.budget_floor)
                break
            results = list(pool.map(lambda b: fetch_batch(b, api_key),
                                    batches[w:w + args.checkpoint_every]))
            remaining = "?"
            for rows, remaining in results:
                cache.update(rows)
            done += len(results)
            write_cache(args.output, cache)
            log.info("%d/%d requests; remaining daily budget %s USD", done, n_req, remaining)
    write_cache(args.output, cache)
    log.info("cache now holds %d ids (%d requests this run)", len(cache), done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
