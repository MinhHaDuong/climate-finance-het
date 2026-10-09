"""REL tables of contents of the manifest journals (ticket 1650).

Scope (author decision, 2026-09-30, after the timed pilot): a title's table of
contents is what Crossref and OpenAlex hold under its ISSNs, **not verified
against publisher pages**. The six megajournals of the manifest
(``sweep_mode = thematic``) are not swept in full: they are searched with the
REL English thematic queries of ``config/rel_sud_search.yaml``.

Steps, each writing into one run directory (never into the pool); every step
resumes safely (a finished file is skipped, a partial one is rewritten):

``crossref``  every work under each ISSN of the title in the REL window,
              cursor-paged, polite pool (mailto = project agent address);
``openalex``  the same by ISSN of the primary source; the ``Remaining-USD``
              header is read before each journal and the batch stops at a floor;
``thematic``  the thematic queries restricted to the megajournals (one OR'd
              ISSN filter per query);
``deliver``   the intake delivery (``docs/rel-intake-contract.md``) under
              ``data/rel_intake/t1650-sommaires/<date>/``: every retrieved item,
              matched against the pool (DOI, OpenAlex id, then normalised title +
              first-author surname + year within one) as ``lane_status``, never
              filtered on it. 1650 does not judge ICF relevance.

Usage:
    python scripts/catalog_rel_toc.py crossref --journals full --run-dir RUN
    python scripts/catalog_rel_toc.py openalex --journals full --run-dir RUN
    python scripts/catalog_rel_toc.py thematic --run-dir RUN
    python scripts/catalog_rel_toc.py deliver --run-dir RUN --pool unified_works.csv \
        --rel-results 'rel_sud_runs/*/results.jsonl.gz' --delivery-dir OUT
"""

import argparse
import gzip
import json
import os
import random
import sys
import time

import requests
from _rel_toc_core import crossref_filter
from _rel_toc_plan import (
    ROOT,
    _now,
    load_manifest,
    openalex_filter,
    thematic_queries,
)
from pipeline_keystore import read_credential
from utils import get_logger

log = get_logger("rel_toc")

CR_API = "https://api.crossref.org"
OA_API = "https://api.openalex.org"
CR_SELECT = ",".join(["DOI", "title", "author", "issued", "published-print",
                      "published-online", "volume", "issue", "type", "page",
                      "container-title", "abstract"])
OA_SELECT = ",".join(["id", "doi", "display_name", "publication_year", "publication_date",
                      "type", "biblio", "authorships", "abstract_inverted_index",
                      "primary_location"])


def agent_mailto():
    """Project agent address for the polite pools (never the author's)."""
    if os.environ.get("AGENT_GIT_EMAIL"):
        return os.environ["AGENT_GIT_EMAIL"]
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("AGENT_GIT_EMAIL="):
                    return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("AGENT_GIT_EMAIL not set (.env)")


def _get(session, url, params=None, tries=5):
    resp = None
    for attempt in range(tries):
        try:
            resp = session.get(url, params=params, timeout=60)
        except requests.RequestException:
            resp = None
        if resp is not None and resp.status_code not in (429, 500, 502, 503, 504):
            return resp
        time.sleep(2 ** attempt + random.random())
    return resp


class StepLog:
    """Append-only JSONL log of each step: wall clock, calls, cost headers."""

    def __init__(self, run_dir):
        self.path = os.path.join(run_dir, "steps.jsonl")

    def write(self, **kw):
        kw["at"] = _now()
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(kw) + "\n")
        log.info("%s", {k: v for k, v in kw.items() if k != "filter"})


def _paged(session, url, params, out, kind):
    """Cursor-page one query into ``out`` via a ``.part`` file.

    Returns (calls, expected, received, stop_reason, last_response); the final
    file exists only when the last page was reached.
    """
    part = out + ".part"
    calls, n, total, reason, resp = 0, 0, None, "", None
    with gzip.open(part, "wt", encoding="utf-8") as fh:
        while True:
            resp = _get(session, url, params)
            calls += 1
            if resp is None or resp.status_code != 200:
                reason = f"http {getattr(resp, 'status_code', 'none')}"
                break
            body = resp.json()
            if kind == "crossref":
                msg = body["message"]
                total = msg.get("total-results") if total is None else total
                items, cursor = msg.get("items") or [], msg.get("next-cursor")
            else:
                total = body["meta"]["count"] if total is None else total
                items, cursor = body["results"], body["meta"].get("next_cursor")
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")
            n += len(items)
            if not items or not cursor or (kind == "crossref" and n >= total):
                break
            params["cursor"] = cursor
    if not reason and kind == "crossref" and n != total:
        reason = f"received {n} of {total}"  # keep the .part: a resume retries it
    if not reason:
        os.replace(part, out)
    return calls, total, n, reason, resp


def crossref_sweep(journal, run_dir, mailto):
    out = os.path.join(run_dir, f"crossref_{journal['journal_key']}.jsonl.gz")
    flt = crossref_filter(journal)
    if os.path.exists(out):
        return {"step": "crossref", "journal": journal["journal_key"], "skipped": "done"}
    session = requests.Session()
    session.headers["User-Agent"] = f"ClimateFinanceHET-RELtoc/0.1 (mailto:{mailto})"
    t0 = time.time()
    params = {"filter": flt, "rows": 1000, "cursor": "*", "select": CR_SELECT, "mailto": mailto}
    calls, total, n, reason, _ = _paged(session, f"{CR_API}/works", params, out, "crossref")
    return {"step": "crossref", "journal": journal["journal_key"], "filter": flt,
            "calls": calls, "expected": total, "received": n,
            "complete": not reason and n == total, "stop_reason": reason,
            "seconds": round(time.time() - t0, 1), "cost_usd": 0}


def _remaining_usd(resp):
    try:
        return float(resp.headers.get("X-RateLimit-Remaining-USD"))
    except (AttributeError, TypeError, ValueError):
        return None


def openalex_query(qid, flt, out, session, api_key, mailto, floor_usd):
    """One OpenAlex query, guarded by the budget floor read just before it."""
    base = {"mailto": mailto, "api_key": api_key}
    probe = _get(session, f"{OA_API}/works", {**base, "filter": flt, "per_page": 1,
                                              "select": "id"})
    before = _remaining_usd(probe)
    if probe is None or probe.status_code != 200:
        return {"query_id": qid, "stop_reason": f"http {getattr(probe, 'status_code', 'none')}",
                "complete": False, "budget_before": before}
    if before is not None and before < floor_usd:
        return {"query_id": qid, "stop_reason": f"budget floor: {before} < {floor_usd} USD",
                "complete": False, "budget_before": before, "stop_batch": True}
    t0 = time.time()
    params = {**base, "filter": flt, "select": OA_SELECT, "per_page": 200, "cursor": "*"}
    calls, total, n, reason, resp = _paged(session, f"{OA_API}/works", params, out, "openalex")
    after = _remaining_usd(resp)
    return {"query_id": qid, "filter": flt, "calls": calls + 1, "expected": total,
            "received": n, "complete": not reason, "stop_reason": reason,
            "seconds": round(time.time() - t0, 1), "budget_before": before,
            "budget_after": after,
            # Upper bound: the key is shared, other sessions spend in the same window.
            "spent_usd_upper_bound": (round(before - after, 5)
                                      if before is not None and after is not None else None),
            "stop_batch": reason.startswith("http 429")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=["crossref", "openalex", "thematic", "deliver"])
    ap.add_argument("--journals", default="full",
                    help="all | full | thematic | comma-separated journal_key list")
    # Multi-output steps (raw pages, logs, a delivery): directories, not --output.
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--floor-usd", type=float, default=0.30,
                    help="stop the OpenAlex batch when Remaining-USD falls below this")
    ap.add_argument("--pool", help="raw merged catalogue (unified_works.csv)")
    ap.add_argument("--rel-results", action="append", default=[],
                    help="glob of REL search results.jsonl.gz (repeatable)")
    ap.add_argument("--delivery-dir", help="data/rel_intake/t1650-sommaires/<date>")
    ap.add_argument("--summary", help="per-journal summary CSV (e.g. docs/rel-toc-1650-summary.csv)")
    ap.add_argument("--backfill", help="catalog_rel_oa_backfill.py directory: fills the blank "
                    "authors, host organization, source type and landing page of deliver (ticket 2049)")
    ap.add_argument("--supersedes", help="deliver: the delivery of the lane this one replaces")
    ap.add_argument("--legacy-alias-separator", action="store_true",
                    help="deliver: join alias DOIs with a space as delivery 2026-09-30 did (commit "
                    "aedec84f changed it to ';'), so a regeneration changes no delivered cell")
    ap.add_argument("--note", default="", help="deliver: text appended to the manifest notes")
    ap.add_argument("--delivered-at", help="deliver: ISO datetime of the manifest (default: now)")
    ap.add_argument("--machine", default=os.uname().nodename)
    args = ap.parse_args(argv)
    os.makedirs(args.run_dir, exist_ok=True)
    steps = StepLog(args.run_dir)
    if args.step == "crossref":
        mailto = agent_mailto()
        for j in load_manifest(args.journals):
            steps.write(**crossref_sweep(j, args.run_dir, mailto))
        return 0
    if args.step in ("openalex", "thematic"):
        mailto, key = agent_mailto(), read_credential("openalex", "OPENALEX_API_KEY")
        session = requests.Session()
        if args.step == "openalex":
            jobs = [(j["journal_key"], openalex_filter(j),
                     os.path.join(args.run_dir, f"openalex_{j['journal_key']}.jsonl.gz"))
                    for j in load_manifest(args.journals)]
        else:
            jobs = [(q["query_id"], q["filter"],
                     os.path.join(args.run_dir, f"thematic_{q['query_id']}.jsonl.gz"))
                    for q in thematic_queries(load_manifest("thematic"))]
        for qid, flt, out in jobs:
            if os.path.exists(out):
                continue
            info = openalex_query(qid, flt, out, session, key, mailto, args.floor_usd)
            steps.write(step=args.step, **info)
            if info.get("stop_batch"):
                log.warning("OpenAlex batch stopped (%s); rerun later to resume",
                            info["stop_reason"])
                return 3
        return 0
    from _rel_toc_deliver import deliver
    return deliver(args, load_manifest("all"), steps)


if __name__ == "__main__":
    sys.exit(main())
