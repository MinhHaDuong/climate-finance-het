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
import html
import json
import os
import random
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone

import requests
from pipeline_keystore import read_credential
from utils import get_logger, normalize_doi, reconstruct_abstract

log = get_logger("rel_toc")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "config", "rel_toc_manifest.csv")
FROM_DATE = "1990-01-01"
UNTIL_DATE = "2026-09-28"  # config/rel_review.yaml search date
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
    "journal_key", "year", "volume", "issue", "expected", "scanned", "in_pool",
    "candidates", "candidate_articles", "status", "reason", "toc_source",
    "publisher_n", "publisher_only",
]
CANDIDATE_FIELDS = [
    "journal_key", "journal", "issn", "volume", "issue", "online_first", "item_class",
    "crossref_type", "doi", "title", "authors", "year", "pub_date", "abstract",
    "openalex_id", "toc_source", "endpoint", "retrieved_at", "in_openalex",
]


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

_TAG = re.compile(r"<[^>]+>")


def normalize_title(title):
    """Casefold, strip markup and accents, keep letters and digits."""
    if not isinstance(title, str) or not title:
        return ""
    t = html.unescape(_TAG.sub("", title))
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c)).casefold()
    t = re.sub(r"[^\w\s]|_", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def surname_key(name):
    """Last token of a surname, from 'Given Family', 'Family, Given' or 'Family'."""
    if not isinstance(name, str) or not name.strip():
        return ""
    if "," in name:
        name = name.split(",", 1)[0]
    tokens = normalize_title(name).split()
    return tokens[-1] if tokens else ""


_CLASSES = [
    ("front-back-matter", r"^(front|back) matter|^issue information|^editorial board"
                          r"|^masthead|^table of contents|^contents|^cover|^index\b"
                          r"|^subscription|^instructions? (to|for) authors|^announcement"),
    ("book-review", r"^books? (reviews?|received)|^review of\b|^book notes?"),
    ("erratum", r"^(erratum|errata|corrigend|correction|retraction|expression of concern)"),
    ("editorial", r"^editorial\b|^editors?'? (note|introduction)|^introduction to the (special )?issue"
                  r"|^foreword|^preface"),
    ("society-report", r"^report of the\b|^minutes of\b|^annual report|^program of\b"
                       r"|^papers and proceedings\b|^list of members|^in memoriam|^obituary"),
]


def classify_item(title):
    """Type a TOC item from its title; the type is recorded, never used to drop."""
    t = normalize_title(title)
    if not t:
        return "untitled"
    for label, pat in _CLASSES:
        if re.search(pat, t):
            return label
    return "article"


def _date_year(item, *keys):
    for k in keys:
        parts = (item.get(k) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0]), "-".join(str(p) for p in parts[0])
    return None, ""


def crossref_record(item, journal_key, issn):
    """Flatten one Crossref work into a TOC record."""
    authors = item.get("author") or []
    names = []
    for a in authors:
        fam, giv = a.get("family") or a.get("name") or "", a.get("given") or ""
        names.append(f"{fam}, {giv}".strip(", ") if giv else fam)
    volume = (item.get("volume") or "").strip()
    online_first = not volume
    if online_first:
        year, date = _date_year(item, "published-online", "issued")
    else:
        year, date = _date_year(item, "published-print", "issued", "published-online")
    title = " ".join(item.get("title") or [])
    return {
        "journal_key": journal_key, "issn": issn,
        "journal": " ".join(item.get("container-title") or []),
        "doi": normalize_doi(item.get("DOI") or ""),
        "title": title, "item_class": classify_item(title),
        "crossref_type": item.get("type") or "",
        "authors": "; ".join(names),
        "first_author_surname": surname_key(names[0]) if names else "",
        "year": year, "pub_date": date,
        "volume": volume, "issue": "" if online_first else (item.get("issue") or "").strip(),
        "online_first": online_first,
        "abstract": re.sub(r"\s+", " ", _TAG.sub(" ", item.get("abstract") or "")).strip()[:3000],
        "openalex_id": "",
    }


def openalex_record(work, journal_key):
    biblio = work.get("biblio") or {}
    names = [(a.get("author") or {}).get("display_name") or ""
             for a in work.get("authorships") or []]
    title = work.get("display_name") or ""
    return {
        "journal_key": journal_key,
        "openalex_id": (work.get("id") or "").rsplit("/", 1)[-1],
        "doi": normalize_doi(work.get("doi") or ""),
        "title": title, "item_class": classify_item(title),
        "openalex_type": work.get("type") or "",
        "authors": "; ".join(names),
        "first_author_surname": surname_key(names[0]) if names else "",
        "year": work.get("publication_year"), "pub_date": work.get("publication_date") or "",
        "volume": biblio.get("volume") or "", "issue": biblio.get("issue") or "",
        "abstract": (reconstruct_abstract(work.get("abstract_inverted_index")) or "")[:3000],
    }


def issue_key(rec):
    """(journal, year, volume, issue); online-first items group by year."""
    if rec["online_first"]:
        return (rec["journal_key"], rec["year"], "", "online-first")
    return (rec["journal_key"], rec["year"], rec["volume"], rec["issue"])


def _year(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class PoolIndex:
    """Match keys of the pool: DOI, OpenAlex id, title+surname, title (no author)."""

    def __init__(self, rows):
        self.dois, self.ids = set(), set()
        self.title_author = collections.defaultdict(set)
        self.title_noauthor = collections.defaultdict(set)
        for r in rows:
            if r.get("doi"):
                self.dois.add(normalize_doi(r["doi"]))
            if r.get("openalex_id"):
                self.ids.add(r["openalex_id"])
            t, y = normalize_title(r.get("title")), _year(r.get("year"))
            if not t:
                continue
            s = surname_key(r.get("first_author"))
            if s:
                self.title_author[(t, s)].add(y)
            else:
                self.title_noauthor[t].add(y)
        self.size = len(rows)

    @staticmethod
    def _near(years, y):
        return y is not None and any(v is not None and abs(v - y) <= 1 for v in years)

    def match(self, rec):
        """How the record is found in the pool: a method name, or '' if absent."""
        if rec.get("doi") and normalize_doi(rec["doi"]) in self.dois:
            return "doi"
        if rec.get("openalex_id") and rec["openalex_id"] in self.ids:
            return "openalex_id"
        t, y = normalize_title(rec.get("title")), _year(rec.get("year"))
        if not t:
            return ""
        s = rec.get("first_author_surname") or ""
        if s and self._near(self.title_author.get((t, s), ()), y):
            return "title_author_year"
        if self._near(self.title_noauthor.get(t, ()), y):
            return "title_year_noauthor"
        return ""


def build_register(records, checks):
    """One row per journal/year/volume/issue.

    ``checks`` maps (journal, year, volume, issue) to the publisher check. Only a
    ``verified`` issue counts its items as scanned.
    """
    groups = collections.OrderedDict()
    for rec in sorted(records, key=lambda r: (r["journal_key"], r["year"] or 0,
                                              str(r["volume"]), str(r["issue"]))):
        groups.setdefault(issue_key(rec), []).append(rec)
    rows = []
    for key, recs in groups.items():
        chk = checks.get(key) or {"status": "not-checked", "reason": "",
                                  "toc_source": "crossref", "publisher_n": "",
                                  "publisher_only": ""}
        n_pool = sum(1 for r in recs if r["in_pool"])
        rows.append({
            "journal_key": key[0], "year": key[1], "volume": key[2], "issue": key[3],
            "expected": len(recs),
            "scanned": len(recs) if chk["status"] == "verified" else 0,
            "in_pool": n_pool, "candidates": len(recs) - n_pool,
            "candidate_articles": sum(1 for r in recs if not r["in_pool"]
                                      and r.get("item_class", "article") == "article"),
            "status": chk["status"], "reason": chk["reason"],
            "toc_source": chk["toc_source"], "publisher_n": chk["publisher_n"],
            "publisher_only": chk["publisher_only"],
        })
    return rows


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
    url = f"{CR_API}/journals/{issn}/works"
    params = {"filter": f"from-pub-date:{FROM_DATE},until-pub-date:{UNTIL_DATE}",
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
        resp = _get(session, f"https://www.aeaweb.org/issues/{iid}",
                    headers={"User-Agent": BROWSER_UA})
        calls += 1
        time.sleep(delay)
        if resp is None or resp.status_code != 200:
            listed[(vol, no)] = (None, f"http {getattr(resp, 'status_code', 'none')}")
            continue
        with gzip.open(os.path.join(raw_dir, f"{iid}.html.gz"), "wt", encoding="utf-8") as fh:
            fh.write(resp.text)
        dois = {normalize_doi(d) for d in re.findall(r"/articles\?id=(10\.[^\"'&]+)", resp.text)}
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


def match_journal(journal, run_dir, pool, retrieved_at):
    key = journal["journal_key"]
    issn = journal["pissn"] or journal["eissn"]
    cr = [crossref_record(it, key, issn) for it in
          _read_jsonl(os.path.join(run_dir, f"crossref_{key}.jsonl.gz"))]
    oa = [openalex_record(w, key) for w in
          _read_jsonl(os.path.join(run_dir, f"openalex_{key}.jsonl.gz"))]
    oa_by_doi = {r["doi"]: r for r in oa if r["doi"]}
    for r in cr:
        o = oa_by_doi.get(r["doi"])
        r["openalex_id"] = o["openalex_id"] if o else ""
        r["in_openalex"] = bool(o)
        if o and not r["abstract"]:
            r["abstract"] = o["abstract"]
        r["in_pool"] = pool.match(r)
    cr_dois = {r["doi"] for r in cr}
    oa_only = [o for o in oa if not o["doi"] or o["doi"] not in cr_dois]
    for o in oa_only:
        o["in_pool"] = pool.match(o)
    checks_path = os.path.join(run_dir, f"checks_{key}.json")
    checks = {}
    if os.path.exists(checks_path):
        with open(checks_path, encoding="utf-8") as fh:
            checks = {tuple(json.loads(k)): v for k, v in json.load(fh).items()}
    register = build_register(cr, checks)
    endpoint = f"{CR_API}/journals/{issn}/works?filter=from-pub-date:{FROM_DATE},until-pub-date:{UNTIL_DATE}"
    candidates = [{**{f: r.get(f, "") for f in CANDIDATE_FIELDS},
                   "toc_source": "crossref", "endpoint": endpoint,
                   "retrieved_at": retrieved_at} for r in cr if not r["in_pool"]]
    for o in oa_only:
        if o["in_pool"]:
            continue
        candidates.append({**{f: o.get(f, "") for f in CANDIDATE_FIELDS}, "issn": issn,
                           "journal": journal["title"], "crossref_type": "",
                           "online_first": not o["volume"], "toc_source": "openalex-only",
                           "endpoint": f"{OA_API}/works primary_location.source.id",
                           "retrieved_at": retrieved_at, "in_openalex": True})
    summary = {
        "journal": key,
        "crossref_items": len(cr),
        "crossref_by_class": dict(collections.Counter(r["item_class"] for r in cr)),
        "crossref_by_type": dict(collections.Counter(r["crossref_type"] for r in cr)),
        "crossref_online_first": sum(r["online_first"] for r in cr),
        "crossref_issues": sum(1 for g in register if g["issue"] != "online-first"),
        "openalex_items": len(oa),
        "openalex_by_type": dict(collections.Counter(o["openalex_type"] for o in oa)),
        "openalex_no_doi": sum(1 for o in oa if not o["doi"]),
        "crossref_not_in_openalex": sum(1 for r in cr if not r["in_openalex"]),
        "openalex_not_in_crossref": len(oa_only),
        "openalex_not_in_crossref_with_doi": sum(1 for o in oa_only if o["doi"]),
        "in_pool": sum(1 for r in cr if r["in_pool"]),
        "in_pool_by_method": dict(collections.Counter(r["in_pool"] for r in cr if r["in_pool"])),
        "absent": sum(1 for r in cr if not r["in_pool"]),
        "absent_articles": sum(1 for r in cr if not r["in_pool"] and r["item_class"] == "article"),
        "openalex_only_absent": sum(1 for o in oa_only if not o["in_pool"]),
        "issues_by_status": dict(collections.Counter(g["status"] for g in register)),
        "needs_human_reasons": dict(collections.Counter(
            g["reason"].split(":")[0] for g in register if g["status"] == "needs-human")),
        "by_year": {y: sum(1 for r in cr if r["year"] == y)
                    for y in sorted({r["year"] for r in cr if r["year"]})},
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
            recs = [crossref_record(it, j["journal_key"], j["pissn"] or j["eissn"]) for it in
                    _read_jsonl(os.path.join(args.run_dir, f"crossref_{j['journal_key']}.jsonl.gz"))]
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
