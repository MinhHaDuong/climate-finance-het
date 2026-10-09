"""REL causal-map lane over bibCNRS EDS: the EconLit strings against RePEc and ECONIS (ticket 1652).

EconLit is not licensed for the CNRS INSHS/INEE bibCNRS profiles (probe of
2026-09-30). The working-paper indexes that the same EBSCO Discovery Service
profile does carry, RePEc and ECONIS, are reached instead: each EconLit twin
of the query matrix (``catalog_rel_causal_search.py``) is sent as an EDS query
restricted to one content provider. The bibCNRS API ignores its date
limiter parameter (probe 2026-09-30: same totalHits with and without it), so the
date range stays in the query text as ``DT YYYY-YYYY``, which EDS applies.
This also exercises the adapted strings against a live EBSCO parser.

Login is Janus (Shibboleth SAML) with the credentials of
``~/.config/keys/janus.env``, read in-process only: nothing is printed,
logged or written, and the session cookies stay in memory. Metadata only; raw
results stay outside any public deposit (bibCNRS terms, docs/data-management-plan.md).
The raw API records are kept next to the slim ones (``raw.jsonl.gz``) since ticket 2040.
Returned fields and what is kept: see ``slim_eds``.

Registry and provenance follow the OpenAlex run: search id, platform, exact
string, provider filter, date, announced and received counts, completed flag,
stop reason. An output directory that already holds a registry is refused.

Usage:
    python scripts/catalog_rel_causal_eds.py --matrix RUN_DIR/matrix.csv \
        --output-dir EDS_DIR [--providers RePEc ECONIS] [--cap 500]
"""

import argparse
import csv
import gzip
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from utils import get_logger, normalize_doi

log = get_logger("rel_causal_eds")

API = "https://bib.cnrs.fr/api"
UA = "Mozilla/5.0 (X11; Linux x86_64) research-metadata-harvest (CNRS CIRED)"
PROVIDERS = ("RePEc", "ECONIS")
REGISTRY_FIELDS = [
    "search_id", "question", "question_type", "group", "formulation", "language",
    "platform", "query_string", "filter", "run_at", "n_expected", "n_received",
    "pages", "cost_usd", "completed", "stop_reason",
]
ISSN = re.compile(r"^\d{4}-?\d{3}[\dXx]$")
_DATE = re.compile(r"\s+AND\s+DT\s+(\d{4})\d{2}-(\d{4})\d{2}\s*$")


# --- pure request building (unit-tested offline) ----------------------------

def eds_term(econlit_string):
    """(query text, year_from, year_to): the EconLit string with its CCYYMM
    date limiter rewritten as the ``DT YYYY-YYYY`` form EDS applies."""
    m = _DATE.search(econlit_string)
    if not m:
        return econlit_string.strip(), None, None
    y0, y1 = int(m.group(1)), int(m.group(2))
    return f"{econlit_string[:m.start()].strip()} AND DT {y0}-{y1}", y0, y1


def build_params(term, provider, page, per_page):
    """Query parameters of GET /api/ebsco/{domain}/article/search.

    The field codes stay inside the term: the API returns HTTP 500 when a field
    code is put in its field slot."""
    return {
        "queries": json.dumps([{"boolean": "AND", "field": None, "term": term}]),
        "activeFacets": json.dumps({"ContentProvider": [provider]}),
        "resultsPerPage": per_page, "currentPage": page,
    }


def provider_filter(provider, year_from, year_to):
    return (f"ContentProvider={provider}"
            + (f"; DT {year_from}-{year_to} in the query text" if year_from else ""))


def _export_params(rec):
    """The bibliographic fields EDS puts in the query string of its BibTeX
    export link (ISBN, ISSN, volume, pages, document type), first value each."""
    links = rec.get("exportLinks")
    url = links.get("bibtex") if isinstance(links, dict) else None
    q = parse_qs(urlparse(url).query) if url else {}
    return {k: v[0] for k, v in q.items() if v and v[0]}


def slim_eds(rec):
    """The fields of one EDS result the REL pool needs, none truncated.

    Fields returned by the API (probe 2026-10-09, one RePEc and one ECONIS
    record): id, an, dbId, articleLinks {fullTextLinks, pdfLinks, html, urls},
    exportLinks {bibtex, ris}, doi, title, source, authors (list or null),
    publicationDate, languages, database, subjects, publicationType, abstract,
    bibcheck. There is no publisher, no ISSN and no identifier field. The
    BibTeX export link carries isbn, issn, volume, pages and doctype in its
    query string; the RePEc ``issn`` there is the placeholder ``edsr-ep``, kept
    out. ``authors`` is null on a RePEc chapter, a list on an ECONIS article.
    ``urls`` holds the RePEc page (``ideas.repec.org/<kind>/<archive>/<series>/
    <item>.html``) of an ``edsrep`` record."""
    date = rec.get("publicationDate") or ""
    langs = rec.get("languages") or []
    exp = _export_params(rec)
    links = rec.get("articleLinks") if isinstance(rec.get("articleLinks"), dict) else {}
    return {
        "eds_an": rec.get("an") or "",
        "db": rec.get("dbId") or "",
        "doi": normalize_doi(rec.get("doi") or ""),
        "title": rec.get("title") or "",
        "year": int(date[:4]) if date[:4].isdigit() else None,
        "language": langs[0] if langs else None,
        "type": rec.get("publicationType"),
        "journal": rec.get("source"),
        "abstract": rec.get("abstract") or "",
        "authors": [a for a in (rec.get("authors") or []) if a],
        "issn": exp["issn"] if ISSN.match(exp.get("issn", "")) else "",
        "isbn": exp.get("isbn", ""),
        "volume": exp.get("volume", ""),
        "pages": exp.get("pages", ""),
        "doctype": exp.get("doctype", ""),
        "subjects": rec.get("subjects"),
        "urls": [u["url"] for u in (links.get("urls") or []) if isinstance(u, dict) and u.get("url")],
    }


def eds_rows(matrix_rows):
    """The EconLit strings the EDS lane replays: every OpenAlex twin and the
    JEL rows; the working-paper rows are redundant with a RePEc restriction."""
    return [r for r in matrix_rows if r["econlit_string"] and r["formulation"] != "WP"]


# --- login and run (live; not part of the tests) ------------------------------

def _creds():
    vals = {}
    with open(os.path.expanduser("~/.config/keys/janus.env"), encoding="utf-8") as fh:
        for line in fh:
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.rstrip("\n").split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals["JANUS_USERNAME"], vals["JANUS_PASSWORD"]


class _FirstForm(HTMLParser):
    """Action and named inputs of the first <form> of a page (stdlib only)."""

    def __init__(self):
        super().__init__()
        self.action, self.inputs, self._state = None, {}, "before"

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and self._state == "before":
            self.action, self._state = a.get("action") or "", "in"
        elif tag == "input" and self._state == "in" and a.get("name"):
            self.inputs[a["name"]] = a.get("value") or ""

    def handle_endtag(self, tag):
        if tag == "form" and self._state == "in":
            self._state = "after"


def parse_first_form(html, base_url):
    """(absolute action URL, {input name: value}) of the first form, or None."""
    p = _FirstForm()
    p.feed(html)
    if p.action is None:
        return None
    return urljoin(base_url, p.action or base_url), p.inputs


def _form(resp):
    return parse_first_form(resp.text, resp.url)


def login():
    """A requests session holding the bibCNRS API token, in memory only."""
    s = requests.Session()
    s.headers["User-Agent"] = UA
    r = s.get(f"{API}/ebsco/login_renater/", params={"origin": "https://bib.cnrs.fr/"})
    form = _form(r)
    if not form or "j_username" not in form[1]:
        raise RuntimeError("Janus login page not recognised")
    action, data = form
    user, pw = _creds()
    data.update(j_username=user, j_password=pw, _eventId_proceed="")
    r = s.post(action, data=data)
    del user, pw, data
    for _ in range(5):
        if any(c.name == "bibapi_token" for c in s.cookies):
            break
        form = _form(r)
        if not form or "SAMLResponse" not in form[1]:
            raise RuntimeError("SAML exchange did not complete")
        r = s.post(*form)
    if not any(c.name == "bibapi_token" for c in s.cookies):
        raise RuntimeError("login did not yield a bibCNRS token")
    s.post(f"{API}/ebsco/getLogin", headers={"Accept": "application/json"})
    return s


def search_all(session, domain, term, provider, cap, per_page, delay):
    """Yield ('meta', count), ('work', rec); last ('end', reason)."""
    page, received = 1, 0
    while True:
        params = build_params(term, provider, page, per_page)
        try:
            r = session.get(f"{API}/ebsco/{domain}/article/search", params=params,
                            headers={"Accept": "application/json"}, timeout=90)
        except requests.RequestException as exc:
            yield ("end", f"error: {type(exc).__name__}")
            return
        time.sleep(delay)
        if r.status_code != 200:
            yield ("end", f"http {r.status_code}")
            return
        try:
            body = r.json()
            total, results = int(body.get("totalHits") or 0), body.get("results") or []
            max_page = int(body.get("maxPage") or 0)
        except (ValueError, TypeError):
            yield ("end", "error: bad body")
            return
        if page == 1:
            yield ("meta", total)
        for rec in results:
            yield ("work", rec)
            received += 1
            if cap and received >= cap and received < total:
                yield ("end", "record cap")
                return
        if not results or page >= max_page or received >= total:
            yield ("end", f"short cursor: {received} of {total}" if received < total else "")
            return
        page += 1


def run(args, session=None):
    with open(args.matrix, encoding="utf-8", newline="") as fh:
        rows = eds_rows(list(csv.DictReader(fh)))
    os.makedirs(args.output_dir, exist_ok=True)
    reg_path = os.path.join(args.output_dir, "registry.csv")
    if os.path.exists(reg_path):
        log.error("%s already holds a registry; use a new --output-dir", args.output_dir)
        return 2
    session = session or login()
    with open(reg_path, "w", encoding="utf-8", newline="") as reg_fh, \
            gzip.open(os.path.join(args.output_dir, "results.jsonl.gz"), "wt",
                      encoding="utf-8") as res_fh, \
            gzip.open(os.path.join(args.output_dir, "raw.jsonl.gz"), "wt",
                      encoding="utf-8") as raw_fh:
        reg = csv.DictWriter(reg_fh, REGISTRY_FIELDS, extrasaction="ignore")
        reg.writeheader()
        for provider in args.providers:
            for row in rows:
                term, y0, y1 = eds_term(row["econlit_string"])
                sid = re.sub(r"^R[CE]-", f"EDS-{provider}-", row["search_id"])
                out = {**row, "search_id": sid, "platform": f"bibCNRS EDS ({provider})",
                       "query_string": term, "filter": provider_filter(provider, y0, y1),
                       "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "n_expected": "", "n_received": 0, "pages": 0, "cost_usd": 0}
                n, reason = 0, "no response"
                for kind, val in search_all(session, args.domain, term, provider,
                                            args.cap, args.per_page, args.delay):
                    if kind == "meta":
                        out["n_expected"] = val
                    elif kind == "work":
                        rec = slim_eds(val)
                        rec.update(search_id=sid)
                        # the API response as received, so a field added to slim_eds
                        # later is re-read from the archive, not re-queried
                        raw_fh.write(json.dumps({"search_id": sid, "record": val},
                                                ensure_ascii=False) + "\n")
                        res_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        n += 1
                    else:
                        reason = val
                out["pages"] = -(-n // args.per_page) if n else 1
                out.update(n_received=n, completed=reason == "", stop_reason=reason)
                reg.writerow(out)
                reg_fh.flush()
                log.info("%s expected=%s received=%s %s", sid, out["n_expected"], n,
                         reason or "complete")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--matrix", required=True, help="matrix.csv of the OpenAlex run")
    # Multi-output script (registry and results): --output-dir.
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--providers", nargs="+", default=list(PROVIDERS))
    ap.add_argument("--domain", default="INSHS")
    ap.add_argument("--cap", type=int, default=500)
    ap.add_argument("--per-page", type=int, default=50)
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
