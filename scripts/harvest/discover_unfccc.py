#!/usr/bin/env python3
"""Discovery crawl for the UNFCCC key-documents seed enumeration (ticket 0304).

Emits CANDIDATE entries as JSONL under data/ — teaching-style: scripted
discovery output is regenerable staging; the curation act is the reviewable
append to config/unfccc_sources.yaml.

Discovery index: the Wayback CDX API over the stable URL patterns of the two
origins. Rationale (recorded 2026-07-23): the unfccc.int/documents Drupal
facet search decided in ticket 0304 sits behind an Incapsula JavaScript
challenge, and enb.iisd.org serves 403 to non-browser clients — the polite
facet crawl is impossible from a headless pipeline. Static PDFs on both
origins are open, so the CDX index enumerates candidates and the harvest
fetch (catalog_keydocs --fetch) verifies each retained URL live.

Series covered:
  decisions  COP/CMP/CMA session-report addenda (Part two: action taken),
             old-style /resource/docs paths (<=2016) and new-style
             /sites/default/files/resource names (>=2017)
  inc        pre-1995 INC session documents under /resource/docs/a/
  enb        Earth Negotiations Bulletin vol. 12 English issues (per-COP
             summary selection happens at curation)

Usage:
    python scripts/harvest/discover_unfccc.py \
        --output data/raw/unfccc_candidates.jsonl [--series decisions inc enb]
"""

import argparse
import json
import os
import re
import time

from script_io_args import parse_io_args
from utils import get_logger, polite_get

log = get_logger("discover_unfccc")

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
CDX_DELAY_S = 4.0
# Per-query response cache: the CDX endpoint throttles hard (connection
# refused mid-crawl, 2026-07-23), so reruns must resume, not refetch.
CDX_CACHE_DIR = os.environ.get(
    "CDX_CACHE_DIR", os.path.join("data", "raw", "cdx_cache"))

# (series tag, session number, year) — session years per the UNFCCC calendar.
COP_SESSIONS = [
    ("cop", 1, 1995), ("cop", 2, 1996), ("cop", 3, 1997), ("cop", 4, 1998),
    ("cop", 5, 1999), ("cop", 6, 2000), ("cop", 7, 2001), ("cop", 8, 2002),
    ("cop", 9, 2003), ("cop", 10, 2004), ("cop", 11, 2005), ("cop", 12, 2006),
    ("cop", 13, 2007), ("cop", 14, 2008), ("cop", 15, 2009), ("cop", 16, 2010),
    ("cop", 17, 2011), ("cop", 18, 2012), ("cop", 19, 2013), ("cop", 20, 2014),
    ("cop", 21, 2015), ("cop", 22, 2016), ("cop", 23, 2017), ("cop", 24, 2018),
    ("cop", 25, 2019), ("cop", 26, 2021), ("cop", 27, 2022), ("cop", 28, 2023),
    ("cop", 29, 2024),
]
CMP_SESSIONS = [("cmp", n, y) for n, y in
                [(1, 2005), (2, 2006), (3, 2007), (4, 2008), (5, 2009),
                 (6, 2010), (7, 2011), (8, 2012), (9, 2013), (10, 2014),
                 (11, 2015), (12, 2016), (13, 2017), (14, 2018), (15, 2019),
                 (16, 2021), (17, 2022), (18, 2023), (19, 2024)]]
CMA_SESSIONS = [("cma", n, y) for n, y in
                [(1, 2018), (2, 2019), (3, 2021), (4, 2022), (5, 2023),
                 (6, 2024)]]

SERIES_PREFIX = {
    "cop": ("FCCC/CP", "UNFCCC Conference of the Parties",
            "Conference of the Parties"),
    "cmp": ("FCCC/KP/CMP", "UNFCCC CMP",
            "Conference of the Parties serving as the meeting of the Parties "
            "to the Kyoto Protocol"),
    "cma": ("FCCC/PA/CMA", "UNFCCC CMA",
            "Conference of the Parties serving as the meeting of the Parties "
            "to the Paris Agreement"),
}

OLD_DECISION_FILE = re.compile(r"/(\d{2}a\d{2})\.pdf$")
NEW_DECISION_FILE = re.compile(r"/((?:cp|cmp|cma)\d{4}_\d{1,2}a\d{1,2}E)\.pdf$",
                               re.IGNORECASE)
INC_FILE = re.compile(r"/(\d{1,3}(?:p\d)?(?:a\d{2})?)\.pdf$")
ENB_FILE = re.compile(r"/(enb12\d{2,3}e(?:Rev\d+)?)\.pdf$")

ORDINALS = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
    6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
    15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
    19: "nineteenth", 20: "twentieth", 30: "thirtieth",
}
UNITS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
         6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth"}


def ordinal(n: int) -> str:
    if n in ORDINALS:
        return ORDINALS[n]
    tens, unit = divmod(n, 10)
    assert tens == 2 and unit in UNITS, f"ordinal out of range: {n}"
    return f"twenty-{UNITS[unit]}"


def cdx_urls(url_pattern: str) -> list[str]:
    """Query the CDX index for original URLs matching a pattern.

    Responses are cached on disk (resumable crawl — the endpoint throttles).
    """
    os.makedirs(CDX_CACHE_DIR, exist_ok=True)
    cache = os.path.join(
        CDX_CACHE_DIR, re.sub(r"[^A-Za-z0-9._-]+", "_", url_pattern) + ".txt")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    time.sleep(CDX_DELAY_S)
    resp = polite_get(CDX_ENDPOINT, params={
        "url": url_pattern, "fl": "original", "collapse": "urlkey",
        "filter": "statuscode:200", "matchType": "prefix", "limit": "5000",
    }, delay=0.5, max_retries=6)
    with open(cache, "w", encoding="utf-8") as f:
        f.write(resp.text)
    return [line.strip() for line in resp.text.splitlines() if line.strip()]


def extract_files(rows: list[str], pattern: re.Pattern) -> list[str]:
    """Dedupe CDX rows down to clean matching PDF basenames, sorted."""
    files = set()
    for row in rows:
        m = pattern.search(row.split("?")[0])
        if m:
            files.add(m.group(1) + ".pdf")
    return sorted(files)


def decision_symbol(series: str, year: int, filename: str) -> str:
    prefix = SERIES_PREFIX[series][0]
    base = os.path.basename(filename)
    m = re.match(r"(?:cp|cmp|cma)\d{4}_(\d{1,2})a(\d{1,2})E?\.pdf",
                 base, re.IGNORECASE) or \
        re.match(r"(\d{2})a(\d{2})\.pdf", base)
    assert m, f"unrecognized decision filename: {filename}"
    doc, add = int(m.group(1)), int(m.group(2))
    return f"{prefix}/{year}/{doc}/Add.{add}"


def inc_symbol(filename: str) -> str:
    m = re.match(r"(\d{1,3})(p(\d))?(a(\d{2}))?\.pdf", filename)
    assert m, f"unrecognized INC filename: {filename}"
    sym = f"A/AC.237/{int(m.group(1))}"
    if m.group(3):
        part = {"1": "I", "2": "II", "3": "III"}[m.group(3)]
        sym += f" (Part {part})"
    if m.group(5):
        sym += f"/Add.{int(m.group(5))}"
    return sym


def decision_candidate(series: str, session: int, year: int,
                       filename: str, url: str | None = None) -> dict:
    prefix, body, long_body = SERIES_PREFIX[series]
    if url is None:
        url = (f"https://unfccc.int/resource/docs/{year}/{series}{session}"
               f"/eng/{filename}" if year >= 2005 else
               f"https://unfccc.int/resource/docs/{series}{session}/{filename}")
    sym = decision_symbol(series, year, filename)
    add = sym.rsplit("Add.", 1)[1]
    title = (f"Report of the {long_body} on its {ordinal(session)} session "
             f"({year}). Addendum {add}: action taken")
    return {
        "series": "decisions", "symbol": sym, "title": title, "year": year,
        "session": f"{series.upper()}{session}", "body": body,
        "doc_class": "decision", "language": "en", "url": url,
        "provenance": ("CDX discovery (ticket 0304); constructed title — "
                       "official form fixed at curation; URL verified at "
                       "harvest fetch."),
    }


def discover_decisions() -> list[dict]:
    out = []
    for series, session, year in COP_SESSIONS + CMP_SESSIONS + CMA_SESSIONS:
        if year <= 2016:
            paths = ([f"unfccc.int/resource/docs/{year}/{series}{session}/eng/"]
                     if year >= 2005 else
                     [f"unfccc.int/resource/docs/{series}{session}/"])
            pattern = OLD_DECISION_FILE
        else:
            paths = [f"unfccc.int/sites/default/files/resource/"
                     f"{series}{year}_"]
            pattern = NEW_DECISION_FILE
        for path in paths:
            rows = cdx_urls(path)
            files = extract_files(rows, pattern)
            log.info("%s%d (%d): %d addendum files", series, session, year,
                     len(files))
            for f in files:
                url = None
                if year > 2016:
                    url = ("https://unfccc.int/sites/default/files/resource/"
                           + f)
                out.append(decision_candidate(series, session, year, f, url))
    return out


def discover_inc() -> list[dict]:
    rows = cdx_urls("unfccc.int/resource/docs/a/")
    out = []
    for f in extract_files(rows, INC_FILE):
        out.append({
            "series": "inc", "symbol": inc_symbol(f),
            "title": ("Intergovernmental Negotiating Committee document "
                      f"{inc_symbol(f)} (title fixed at curation)"),
            "year": 0, "session": "INC",
            "body": "Intergovernmental Negotiating Committee",
            "doc_class": "inc", "language": "en",
            "url": f"https://unfccc.int/resource/docs/a/{f}",
            "provenance": ("CDX discovery (ticket 0304); year and official "
                           "title fixed at curation; URL verified at harvest."),
        })
    log.info("INC: %d files", len(out))
    return out


def discover_enb() -> list[dict]:
    rows = cdx_urls("enb.iisd.org/download/pdf/enb12")
    out = []
    for f in extract_files(rows, ENB_FILE):
        issue = re.match(r"enb12(\d+)e", f).group(1)
        out.append({
            "series": "enb", "symbol": f"ENB/12/{issue}",
            "title": (f"Earth Negotiations Bulletin vol. 12 no. {issue} "
                      "(per-COP summary selection at curation)"),
            "year": 0, "session": "",
            "body": "IISD Earth Negotiations Bulletin",
            "doc_class": "negotiation_record", "language": "en",
            "url": f"https://enb.iisd.org/download/pdf/{f}",
            "provenance": ("CDX discovery (ticket 0304); COP-summary issues "
                           "selected at curation; URL verified at harvest."),
        })
    log.info("ENB: %d English vol-12 issues", len(out))
    return out


DISCOVERERS = {
    "decisions": discover_decisions,
    "inc": discover_inc,
    "enb": discover_enb,
}


def main(argv=None):
    io_args, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series", nargs="+", default=list(DISCOVERERS),
                        choices=list(DISCOVERERS))
    args = parser.parse_args(extra)
    if not io_args.output:
        raise SystemExit("--output is required")

    candidates = []
    for name in args.series:
        candidates.extend(DISCOVERERS[name]())

    os.makedirs(os.path.dirname(io_args.output) or ".", exist_ok=True)
    with open(io_args.output, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    log.info("Wrote %d candidates to %s", len(candidates), io_args.output)


if __name__ == "__main__":
    main()
