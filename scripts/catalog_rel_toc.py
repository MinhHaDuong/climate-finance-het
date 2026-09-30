"""REL full tables of contents of the manifest journals (ticket 1650).

Four steps, each writing into one run directory (never into the pool):

``crossref``  every work Crossref holds under the journal ISSN in the REL window,
              cursor-paged, polite pool (mailto = project agent address);
``openalex``  the same by OpenAlex source id, with the USD budget headers logged;
``publisher`` the publisher's own issue pages where they can be fetched and parsed;
              an issue that cannot be checked is ``needs-human`` with its reason and
              is never counted as scanned;
``match``     every TOC item against the pool (DOI, OpenAlex id, then normalised
              title + first-author surname + year within one), then the register per
              journal/year/volume/issue and the candidate file (absent from the pool,
              raw, with provenance). 1650 does not judge ICF relevance: ticket 1655
              screens the whole pool once.

Items are typed (article, front/back matter, book review, erratum, editorial,
society report), never dropped. Items with no volume are online-first and are
registered under ``issue = online-first`` by year.

Usage:
    python scripts/catalog_rel_toc.py crossref  --journals aer,jeem --run-dir RUN
    python scripts/catalog_rel_toc.py openalex  --journals aer --run-dir RUN
    python scripts/catalog_rel_toc.py publisher --journals aer,jeem --run-dir RUN
    python scripts/catalog_rel_toc.py match --journals aer --run-dir RUN \
        --pool unified_works.csv --rel-results 'rel_sud_runs/*/results.jsonl.gz'
"""

import argparse
import collections
import csv
import glob
import gzip
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone

import requests
from _rel_toc_core import (
    FROM_DATE,
    UNTIL_DATE,
    PoolIndex,
    build_register,
    crossref_filter,
    crossref_record,
    in_window,
    issue_key,
    merge_toc,
    openalex_record,
)
from pipeline_keystore import read_credential
from utils import get_logger, normalize_doi

log = get_logger("rel_toc")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "config", "rel_toc_manifest.csv")
CR_API = "https://api.crossref.org"
OA_API = "https://api.openalex.org"
CR_SELECT = ",".join(["DOI", "title", "author", "issued", "published-print",
                      "published-online", "volume", "issue", "type", "page",
                      "container-title", "abstract"])
OA_SELECT = ",".join(["id", "doi", "display_name", "publication_year", "publication_date",
                      "type", "biblio", "authorships", "abstract_inverted_index"])
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126 Safari/537.36")

REGISTER_FIELDS = [
    "journal_key", "year", "volume", "issue", "expected", "crossref_n", "openalex_only_n",
    "scanned", "in_pool",
    "candidates", "candidate_articles", "status", "reason", "toc_source",
    "publisher_n", "publisher_only",
]
CANDIDATE_FIELDS = [
    "journal_key", "journal", "issn", "volume", "issue", "online_first", "item_class",
    "crossref_type", "openalex_type", "doi", "alias_dois", "title", "authors", "year",
    "pub_date", "abstract", "openalex_id", "toc_source", "endpoint", "retrieved_at",
    "in_openalex",
]


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def load_manifest(keys=None):
    with open(MANIFEST, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if keys:
        by = {r["journal_key"]: r for r in rows}
        missing = [k for k in keys if k not in by]
        if missing:
            raise SystemExit(f"unknown journal keys: {missing}")
        rows = [by[k] for k in keys]
    return rows


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


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get(session, url, params=None, headers=None, tries=5):
    for attempt in range(tries):
        try:
            resp = session.get(url, params=params, headers=headers, timeout=60)
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
        log.info("%s", kw)


def crossref_sweep(journal, run_dir, mailto):
    issn = journal["pissn"] or journal["eissn"]
    session = requests.Session()
    session.headers["User-Agent"] = f"ClimateFinanceHET-RELtoc/0.1 (mailto:{mailto})"
    url = f"{CR_API}/works"
    params = {"filter": crossref_filter(journal),
              "rows": 1000, "cursor": "*", "select": CR_SELECT, "mailto": mailto}
    out = os.path.join(run_dir, f"crossref_{journal['journal_key']}.jsonl.gz")
    t0, calls, n, total, reason = time.time(), 0, 0, None, ""
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        while True:
            resp = _get(session, url, params)
            calls += 1
            if resp is None or resp.status_code != 200:
                reason = f"http {getattr(resp, 'status_code', 'none')}"
                break
            msg = resp.json()["message"]
            total = msg.get("total-results") if total is None else total
            items = msg.get("items") or []
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")
            n += len(items)
            if not items or n >= total:
                break
            params["cursor"] = msg.get("next-cursor")
    return {"step": "crossref", "journal": journal["journal_key"], "issn": issn,
            "endpoint": url, "filter": params["filter"], "calls": calls,
            "total_results": total, "received": n, "complete": n == total and not reason,
            "stop_reason": reason, "seconds": round(time.time() - t0, 1), "cost_usd": 0}


def _oa_budget(resp):
    h = resp.headers if resp is not None else {}
    return {k: h.get(f"X-RateLimit-{k}") for k in
            ("Remaining-USD", "Prepaid-Remaining-USD", "Limit-USD")}


def openalex_sweep(journal, run_dir, api_key, mailto, max_usd):
    session = requests.Session()
    base = {"mailto": mailto, "api_key": api_key}
    t0 = time.time()
    issn = journal["pissn"] or journal["eissn"]
    resp = _get(session, f"{OA_API}/sources", {**base, "filter": f"issn:{issn}",
                                               "select": "id,display_name,works_count"})
    before = _oa_budget(resp)
    sources = resp.json().get("results") or [] if resp is not None and resp.ok else []
    if not sources:
        return {"step": "openalex", "journal": journal["journal_key"],
                "stop_reason": "no source for ISSN", "budget_before": before}
    source_id = sources[0]["id"].rsplit("/", 1)[-1]
    flt = (f"primary_location.source.id:{source_id},"
           f"from_publication_date:{FROM_DATE},to_publication_date:{UNTIL_DATE}")
    params = {**base, "filter": flt, "select": OA_SELECT, "per_page": 200, "cursor": "*"}
    out = os.path.join(run_dir, f"openalex_{journal['journal_key']}.jsonl.gz")
    calls, n, count, reason, after = 1, 0, None, "", before
    start_usd = float(before["Remaining-USD"] or 0)
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        while params["cursor"]:
            resp = _get(session, f"{OA_API}/works", params)
            calls += 1
            if resp is None or resp.status_code != 200:
                reason = f"http {getattr(resp, 'status_code', 'none')}"
                break
            after = _oa_budget(resp)
            body = resp.json()
            count = body["meta"]["count"] if count is None else count
            for w in body["results"]:
                fh.write(json.dumps(w, ensure_ascii=False) + "\n")
            n += len(body["results"])
            params["cursor"] = body["meta"].get("next_cursor")
            if start_usd - float(after["Remaining-USD"] or 0) > max_usd:
                reason = f"budget cap {max_usd} USD"
                break
    spent = None
    if before["Remaining-USD"] and after["Remaining-USD"]:
        spent = round(float(before["Remaining-USD"]) - float(after["Remaining-USD"]), 5)
    return {"step": "openalex", "journal": journal["journal_key"], "source_id": source_id,
            "source_name": sources[0].get("display_name"), "filter": flt, "calls": calls,
            "count": count, "received": n, "complete": n == count and not reason,
            "stop_reason": reason, "seconds": round(time.time() - t0, 1),
            "budget_before": before, "budget_after": after, "cost_usd": spent}


# Publisher checks -----------------------------------------------------------

def _aea_issue_list(session, slug):
    resp = _get(session, f"https://www.aeaweb.org/journals/{slug}/issues",
                headers={"User-Agent": BROWSER_UA})
    if resp is None or resp.status_code != 200:
        return None, f"http {getattr(resp, 'status_code', 'none')} on issue list"
    found = re.findall(r"href='/issues/(\d+)'>([^<]*?)\(Vol\. (\d+), No\. ([^)]+)\)",
                       resp.text)
    return [(iid, label.strip(), vol, no.strip()) for iid, label, vol, no in found], ""


def aea_check(journal, records, run_dir, delay=1.0):
    """AEA site issue pages (1999 on): DOIs listed per issue vs Crossref."""
    session = requests.Session()
    slug = journal["publisher_slug"]
    issues, why = _aea_issue_list(session, slug)
    checks, calls, t0 = {}, 1, time.time()
    by_issue = collections.defaultdict(set)
    for r in records:
        if not r["online_first"]:
            by_issue[(r["volume"], r["issue"])].add(r["doi"])
    listed = {}
    if issues is None:
        issues = []
    raw_dir = os.path.join(run_dir, f"publisher_{journal['journal_key']}")
    os.makedirs(raw_dir, exist_ok=True)
    for iid, _label, vol, no in issues:
        cached = os.path.join(raw_dir, f"{iid}.html.gz")
        if os.path.exists(cached):  # a rerun re-reads the saved page
            with gzip.open(cached, "rt", encoding="utf-8") as fh:
                text = fh.read()
        else:
            resp = _get(session, f"https://www.aeaweb.org/issues/{iid}",
                        headers={"User-Agent": BROWSER_UA})
            calls += 1
            time.sleep(delay)
            if resp is None or resp.status_code != 200:
                listed[(vol, no)] = (None, f"http {getattr(resp, 'status_code', 'none')}")
                continue
            text = resp.text
            with gzip.open(cached, "wt", encoding="utf-8") as fh:
                fh.write(text)
        dois = {normalize_doi(d) for d in re.findall(r"/articles\?id=(10\.[^\"'&]+)", text)}
        listed[(vol, no)] = (dois, "" if dois else "issue page lists no DOI")
    for r in records:
        key = issue_key(r)
        if key in checks:
            continue
        if r["online_first"]:
            checks[key] = {"status": "needs-human", "toc_source": "aea",
                           "reason": "online-first items: forthcoming page not compared",
                           "publisher_n": "", "publisher_only": ""}
            continue
        got = listed.get((r["volume"], r["issue"]))
        if got is None:
            reason = why or ("not on AEA site (pre-1999: JSTOR)" if (r["year"] or 0) < 1999
                             else "issue absent from AEA issue list")
            checks[key] = {"status": "needs-human", "toc_source": "aea", "reason": reason,
                           "publisher_n": "", "publisher_only": ""}
            continue
        dois, reason = got
        if dois is None or not dois:
            checks[key] = {"status": "needs-human", "toc_source": "aea", "reason": reason,
                           "publisher_n": "", "publisher_only": ""}
            continue
        only = dois - by_issue[(r["volume"], r["issue"])]
        checks[key] = {"status": "verified" if not only else "needs-human",
                       "toc_source": "aea",
                       "reason": "" if not only else f"{len(only)} DOI on AEA page not in Crossref: "
                                                     + " ".join(sorted(only)[:5]),
                       "publisher_n": len(dois), "publisher_only": len(only)}
    return checks, {"step": "publisher", "journal": journal["journal_key"], "method": "aea",
                    "calls": calls, "issues_listed": len(issues),
                    "seconds": round(time.time() - t0, 1), "cost_usd": 0}


def probe_check(journal, records, run_dir, sample=6, delay=2.0):
    """Publisher without a parser: probe a sample of issue URLs, label all needs-human."""
    session = requests.Session()
    tmpl = journal["toc_url_template"]
    keys = sorted({issue_key(r) for r in records if not r["online_first"]},
                  key=lambda k: (k[1] or 0, k[2], k[3]))
    step = max(1, len(keys) // sample)
    probes, t0 = [], time.time()
    for key in keys[::step][:sample]:
        url = tmpl.format(volume=key[2], issue=key[3],
                          issue_path=f"issue/{key[3]}" if key[3] else "suppl/C")
        resp = _get(session, url, headers={"User-Agent": BROWSER_UA}, tries=1)
        code = getattr(resp, "status_code", "none")
        text = resp.text if resp is not None else ""
        blocked = code != 200 or re.search(r"cloudflare|captcha|are you a robot|"
                                           r"problem providing the content", text, re.I)
        probes.append({"url": url, "http": code, "bytes": len(text),
                       "blocked": bool(blocked)})
        time.sleep(delay)
    n_blocked = sum(p["blocked"] for p in probes)
    reason = (f"publisher site blocks automated access ({n_blocked}/{len(probes)} sampled "
              f"issue pages: http {sorted({p['http'] for p in probes})})")
    checks = {}
    for r in records:
        key = issue_key(r)
        checks.setdefault(key, {"status": "needs-human", "toc_source": journal["publisher"],
                                "reason": reason if not r["online_first"]
                                else "online-first items: publisher list not compared",
                                "publisher_n": "", "publisher_only": ""})
    return checks, {"step": "publisher", "journal": journal["journal_key"], "method": "probe",
                    "probes": probes, "seconds": round(time.time() - t0, 1), "cost_usd": 0}


# Match ----------------------------------------------------------------------

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
            try:
                with gzip.open(path, "rt", encoding="utf-8") as fh:
                    for line in fh:
                        w = json.loads(line)
                        rows.append({"doi": w.get("doi"), "title": w.get("title"),
                                     "first_author": "", "year": w.get("year"),
                                     "openalex_id": w.get("openalex_id")})
                        sources[path] += 1
            except (OSError, EOFError, json.JSONDecodeError) as exc:
                log.warning("skipping unreadable %s: %s", path, exc)
    return rows, sources


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def journal_toc(journal, run_dir):
    """Merged Crossref + OpenAlex TOC records of one journal from its run files."""
    key = journal["journal_key"]
    issn = journal["pissn"] or journal["eissn"]
    cr = [crossref_record(it, key, issn) for it in
          _read_jsonl(os.path.join(run_dir, f"crossref_{key}.jsonl.gz"))]
    oa = [openalex_record(w, key) for w in
          _read_jsonl(os.path.join(run_dir, f"openalex_{key}.jsonl.gz"))]
    merged = merge_toc(cr, oa)
    recs = [r for r in merged if in_window(r)]
    for r in recs:
        r["issn"], r["journal"] = issn, r["journal"] or journal["title"]
    out_of_window = [r for r in merged if not in_window(r)]
    return recs, oa, out_of_window


def match_journal(journal, run_dir, pool, retrieved_at):
    key = journal["journal_key"]
    issn = journal["pissn"] or journal["eissn"]
    recs, oa, out_of_window = journal_toc(journal, run_dir)
    for r in recs:
        r["in_pool"] = pool.match(r)
    checks_path = os.path.join(run_dir, f"checks_{key}.json")
    checks = {}
    if os.path.exists(checks_path):
        with open(checks_path, encoding="utf-8") as fh:
            checks = {tuple(json.loads(k)): v for k, v in json.load(fh).items()}
    register = build_register(recs, checks)
    endpoints = {
        "crossref": f"{CR_API}/works?filter={crossref_filter(journal)}",
        "openalex-only": f"{OA_API}/works?filter=primary_location.source.id (ISSN {issn}),"
                         f"from_publication_date:{FROM_DATE},to_publication_date:{UNTIL_DATE}",
    }
    candidates = [{**{f: r.get(f, "") for f in CANDIDATE_FIELDS},
                   "endpoint": endpoints[r["toc_source"]], "retrieved_at": retrieved_at}
                  for r in recs if not r["in_pool"]]
    cr = [r for r in recs if r["toc_source"] == "crossref"]
    only = [r for r in recs if r["toc_source"] == "openalex-only"]
    absent = [r for r in recs if not r["in_pool"]]
    summary = {
        "journal": key,
        "toc_items": len(recs),
        "crossref_items": len(cr),
        "crossref_by_class": dict(collections.Counter(r["item_class"] for r in cr)),
        "crossref_by_type": dict(collections.Counter(r["crossref_type"] for r in cr)),
        "crossref_online_first": sum(r["online_first"] for r in cr),
        "crossref_first_year": min((r["year"] for r in cr if r["year"]), default=None),
        "openalex_items": len(oa),
        "openalex_by_type": dict(collections.Counter(o["openalex_type"] for o in oa)),
        "openalex_no_doi": sum(1 for o in oa if not o["doi"]),
        "crossref_not_in_openalex": sum(1 for r in cr if not r["in_openalex"]),
        "crossref_with_openalex_alias_doi": sum(1 for r in cr if r["alias_dois"]),
        "openalex_only": len(only),
        "openalex_only_with_doi": sum(1 for r in only if r["doi"]),
        "openalex_only_by_type": dict(collections.Counter(r["openalex_type"] for r in only)),
        "openalex_only_year_source": dict(collections.Counter(r["year_source"] for r in only)),
        "openalex_redated_out_of_window": len(out_of_window),
        "openalex_only_years": dict(sorted(collections.Counter(r["year"] for r in only).items(),
                                           key=lambda kv: kv[0] or 0)),
        "issues": sum(1 for g in register if g["issue"] != "online-first"),
        "online_first_items": sum(1 for r in recs if r["online_first"]),
        "in_pool": len(recs) - len(absent),
        "in_pool_by_method": dict(collections.Counter(r["in_pool"] for r in recs if r["in_pool"])),
        "absent": len(absent),
        "absent_by_class": dict(collections.Counter(r["item_class"] for r in absent)),
        "absent_by_source": dict(collections.Counter(r["toc_source"] for r in absent)),
        "issues_by_status": dict(collections.Counter(g["status"] for g in register)),
        "items_scanned": sum(g["scanned"] for g in register),
        "needs_human_reasons": dict(collections.Counter(
            g["reason"].split(":")[0].split("(")[0].strip()
            for g in register if g["status"] == "needs-human")),
    }
    return register, candidates, summary


def _write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=["crossref", "openalex", "publisher", "match"])
    ap.add_argument("--journals", required=True, help="comma-separated journal_key list")
    # Multi-output steps (raw pages, registers, logs): --run-dir, not --output.
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--pool", help="raw merged catalogue (unified_works.csv)")
    ap.add_argument("--rel-results", action="append", default=[],
                    help="glob of REL search results.jsonl.gz (repeatable)")
    ap.add_argument("--max-usd", type=float, default=0.05,
                    help="OpenAlex spending cap per journal")
    args = ap.parse_args(argv)
    os.makedirs(args.run_dir, exist_ok=True)
    journals = load_manifest(args.journals.split(","))
    steps = StepLog(args.run_dir)
    if args.step == "crossref":
        mailto = agent_mailto()
        for j in journals:
            steps.write(**crossref_sweep(j, args.run_dir, mailto))
    elif args.step == "openalex":
        mailto, key = agent_mailto(), read_credential("openalex", "OPENALEX_API_KEY")
        for j in journals:
            steps.write(**openalex_sweep(j, args.run_dir, key, mailto, args.max_usd))
    elif args.step == "publisher":
        for j in journals:
            recs, _, _ = journal_toc(j, args.run_dir)
            if j["publisher_method"] == "aea":
                checks, info = aea_check(j, recs, args.run_dir)
            else:
                checks, info = probe_check(j, recs, args.run_dir)
            with open(os.path.join(args.run_dir, f"checks_{j['journal_key']}.json"), "w",
                      encoding="utf-8") as fh:
                json.dump({json.dumps(list(k)): v for k, v in checks.items()}, fh)
            steps.write(**info)
    else:
        t0 = time.time()
        rows, sources = load_pool(args.pool, args.rel_results)
        pool = PoolIndex(rows)
        steps.write(step="pool", sources=dict(sources), rows=pool.size,
                    seconds=round(time.time() - t0, 1))
        retrieved = _now()
        all_reg, all_cand, summaries = [], [], []
        for j in journals:
            reg, cand, summ = match_journal(j, args.run_dir, pool, retrieved)
            all_reg += reg
            all_cand += cand
            summaries.append(summ)
        _write_csv(os.path.join(args.run_dir, "register.csv"), all_reg, REGISTER_FIELDS)
        _write_csv(os.path.join(args.run_dir, "candidates.csv"), all_cand, CANDIDATE_FIELDS)
        with open(os.path.join(args.run_dir, "summary.json"), "w", encoding="utf-8") as fh:
            json.dump(summaries, fh, indent=1)
        steps.write(step="match", journals=[s["journal"] for s in summaries],
                    seconds=round(time.time() - t0, 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
