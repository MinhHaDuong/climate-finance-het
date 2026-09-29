"""REL "Sud et langues" search pass over OpenAlex (ticket 1530).

Runs the query matrix of ``config/rel_sud_search.yaml`` (region x language x
theme), a full sweep of the E journals and a topic query in the Q journals.
Output goes to its own directory, never to the OpenAlex pool: candidates absent
from the corpus enter phase 1 only after a decision.

Per query the registry records the exact search string and filter, the count
OpenAlex announced, the count received and whether the last page was reached.
A query stopped by the record cap, a rate limit or an error is ``incomplete``,
and the run report says so.

Usage:
    python scripts/rel_sud_search.py --output-dir data/rel_sud/run1 \
        --corpus data/catalogs/refined_works.csv [--only q|e|qj] [--dry-run]
"""

import argparse
import csv
import gzip
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

import yaml
from pipeline_keystore import read_credential
from utils import MAILTO, get_logger, normalize_doi, polite_get, reconstruct_abstract

log = get_logger("rel_sud_search")

OA_API = "https://api.openalex.org/works"
OA_SELECT = ",".join([
    "id", "doi", "display_name", "publication_year", "publication_date",
    "language", "type", "cited_by_count", "primary_location", "authorships",
    "abstract_inverted_index",
])
REGISTRY_FIELDS = [
    "query_id", "kind", "stratum", "language", "theme", "platform", "run_at",
    "filter", "n_expected", "n_received", "completed", "stop_reason",
]


def split_terms(query):
    """Phrases of an ``"a" OR "b"`` query string, unquoted."""
    return [t.strip().strip('"') for t in query.split(" OR ") if t.strip()]


# OpenAlex folds neither Unicode spellings of the same letter nor ё/е (control
# counts 2026-09-29: Bengali "climate change" 5 vs 4, Russian 0 vs 1), so each
# phrase is sent in every spelling. Bengali and Hindi nukta letters exist both
# as base+nukta and as one composition-excluded code point.
_PRECOMPOSED = {unicodedata.normalize("NFD", c): c
                for c in map(chr, [*range(0x958, 0x960), 0x9DC, 0x9DD, 0x9DF])}


def spelling_variants(phrase):
    out = [phrase]
    for dec, pre in _PRECOMPOSED.items():
        for p in list(out):
            for a, b in ((dec, pre), (pre, dec)):
                q = p.replace(a, b)
                if a in p and q not in out:
                    out.append(q)
    for p in list(out):
        q = p.replace("ё", "е").replace("Ё", "Е")
        if q not in out:
            out.append(q)
    return out


def expand_query(query):
    """The query with every spelling variant of each phrase, in stable order."""
    phrases = []
    for term in split_terms(query):
        for v in spelling_variants(term):
            if v not in phrases:
                phrases.append(v)
    return " OR ".join(f'"{p}"' for p in phrases)


def build_filter(search, year_min, year_max, language=None, countries=None,
                 issns=None):
    parts = [f"title_and_abstract.search:{search}"] if search else []
    parts.append(f"publication_year:{year_min}-{year_max}")
    if language:
        parts.append(f"language:{language}")
    if countries:
        parts.append("authorships.institutions.country_code:" + "|".join(countries))
    if issns:
        parts.append("primary_location.source.issn:" + "|".join(issns))
    return ",".join(parts)


def plan_queries(cfg):
    """Ordered list of query specs; the 76 stratum runs come first."""
    y0, y1 = cfg["year_min"], cfg["year_max"]
    specs = []
    for stratum, s in cfg["strata"].items():
        for lang in s["languages"]:
            for theme, search in cfg["queries"][lang].items():
                specs.append({
                    "query_id": f"Q-{stratum}-{lang}-{theme}", "kind": "q",
                    "stratum": stratum, "language": lang, "theme": theme,
                    # Affiliation countries are missing on most non-English
                    # works (Chinese T2: 260 hits by language, 4 with the
                    # country filter), so only English queries are filtered
                    # by country. For the others the stratum names the query
                    # set; geography comes from the recorded `countries`.
                    "filter": build_filter(
                        expand_query(search), y0, y1, language=lang,
                        countries=s["countries"] if lang == "en" else None)})
    for j in cfg["journals_e"]:
        slug = re.sub(r"\W+", "-", j["name"]).strip("-").lower()
        specs.append({
            "query_id": f"E-{slug}", "kind": "e", "stratum": j["name"],
            "language": "", "theme": "",
            "filter": build_filter(None, y0, y1, issns=j["issn"])})
    for j in cfg["journals_q"]:
        slug = re.sub(r"\W+", "-", j["name"]).strip("-").lower()
        search = " OR ".join(cfg["queries"][lang][t] for lang in j["languages"]
                             for t in cfg["themes"])
        specs.append({
            "query_id": f"J-{slug}", "kind": "qj", "stratum": j["name"],
            "language": "+".join(j["languages"]), "theme": "all",
            "filter": build_filter(expand_query(search), y0, y1, issns=j["issn"])})
    return specs


def icf_flag_pattern(cfg):
    terms = {v for q in cfg["queries"].values() for s in q.values()
             for t in split_terms(s) for v in spelling_variants(t)}
    return re.compile("|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)),
                      re.IGNORECASE)


def slim(work):
    loc = work.get("primary_location") or {}
    src = loc.get("source") or {}
    countries = sorted({c for a in work.get("authorships") or []
                        for i in a.get("institutions") or []
                        if (c := i.get("country_code"))})
    return {
        "openalex_id": (work.get("id") or "").rsplit("/", 1)[-1],
        "doi": normalize_doi(work.get("doi") or ""),
        "title": work.get("display_name") or "",
        "year": work.get("publication_year"),
        "date": work.get("publication_date"),
        "language": work.get("language"),
        "type": work.get("type"),
        "cited_by_count": work.get("cited_by_count"),
        "journal": src.get("display_name"),
        "countries": countries,
        "abstract": (reconstruct_abstract(work.get("abstract_inverted_index")) or "")[:1500],
    }


def load_corpus_keys(path):
    """(normalized DOIs, OpenAlex ids) of the refined corpus."""
    dois, ids = set(), set()
    if not path:
        return dois, ids
    csv.field_size_limit(10**8)
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("doi"):
                dois.add(normalize_doi(row["doi"]))
            if row.get("source") == "openalex" and row.get("source_id"):
                ids.add(row["source_id"])
    return dois, ids


def fetch(spec, api_key, cap, delay):
    """Yield ('meta', count) then ('work', dict); the last item is ('end', reason)."""
    cursor = "*"
    received = 0
    while cursor:
        params = {"filter": spec["filter"], "select": OA_SELECT, "per_page": 200,
                  "cursor": cursor, "mailto": MAILTO}
        if api_key:
            params["api_key"] = api_key
        try:
            resp = polite_get(OA_API, params=params, delay=delay)
        except Exception as exc:  # network failure after retries
            yield ("end", f"error: {type(exc).__name__}")
            return
        if resp.status_code == 429:
            yield ("end", "rate limited or budget exhausted")
            return
        if resp.status_code != 200:
            yield ("end", f"http {resp.status_code}")
            return
        body = resp.json()
        if cursor == "*":
            yield ("meta", body["meta"]["count"])
        for w in body["results"]:
            yield ("work", w)
            received += 1
            if cap and received >= cap:
                yield ("end", "record cap")
                return
        cursor = body["meta"].get("next_cursor")
    yield ("end", "")


def run(cfg, args, api_key):
    pattern = icf_flag_pattern(cfg)
    corpus_dois, corpus_ids = load_corpus_keys(args.corpus)
    specs = [s for s in plan_queries(cfg)
             if args.only is None or s["kind"] == args.only]
    if args.dry_run:
        for s in specs:
            log.info("%s %s", s["query_id"], s["filter"][:160])
        log.info("%d queries", len(specs))
        return 0
    os.makedirs(args.output_dir, exist_ok=True)
    reg_path = os.path.join(args.output_dir, "registry.csv")
    with open(reg_path, "w", encoding="utf-8", newline="") as reg_fh, \
            gzip.open(os.path.join(args.output_dir, "results.jsonl.gz"), "wt",
                      encoding="utf-8") as res_fh:
        reg = csv.DictWriter(reg_fh, REGISTRY_FIELDS)
        reg.writeheader()
        stop_all = False
        for spec in specs:
            row = {k: spec.get(k, "") for k in REGISTRY_FIELDS}
            row.update(platform="openalex", run_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       n_expected="", n_received=0, completed=False, stop_reason="not run")
            if not stop_all:
                n, reason = 0, "no response"
                for kind, val in fetch(spec, api_key, args.cap, args.delay):
                    if kind == "meta":
                        row["n_expected"] = val
                    elif kind == "work":
                        rec = slim(val)
                        rec.update(
                            query_id=spec["query_id"],
                            in_corpus=bool(rec["openalex_id"] in corpus_ids
                                           or (rec["doi"] and rec["doi"] in corpus_dois)),
                            icf_term=bool(pattern.search(rec["title"] + " " + rec["abstract"])))
                        res_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        n += 1
                    else:
                        reason = val
                row["n_received"] = n
                row["completed"] = reason == ""
                row["stop_reason"] = reason
                stop_all = reason.startswith("rate limited")
            reg.writerow(row)
            reg_fh.flush()
            log.info("%s expected=%s received=%s %s", spec["query_id"],
                     row["n_expected"], row["n_received"], row["stop_reason"] or "complete")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="config/rel_sud_search.yaml")
    # Multi-output script (registry, results, report): --output-dir, not --output.
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--corpus", default=None,
                    help="refined_works.csv, to flag works already in the corpus")
    ap.add_argument("--only", choices=["q", "e", "qj"])
    ap.add_argument("--cap", type=int, default=5000,
                    help="max records per query (0 = unlimited)")
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    api_key = None if args.dry_run else read_credential("openalex", "OPENALEX_API_KEY")
    return run(cfg, args, api_key)


if __name__ == "__main__":
    sys.exit(main())
