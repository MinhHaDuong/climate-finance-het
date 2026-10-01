"""REL lane over the local RePEc ReDIF mirror: search, delivery, recall (ticket 1810).

``search`` replays on the ReDIF table (``catalog_rel_repec_redif.py``) the
query units declared in ``config/rel_repec_search.yaml``: the 1652 causal-map
strings and JEL rows, the 1530 ICF terms (T1-T4, every language, gap-fill),
and the declared JEL filter. It writes a delivery in the layout of
``docs/rel-intake-contract.md``:

- every record any unit retrieved, once, keyed by its RePEc handle
  (``record_id``); ``query_id`` is the first unit in registry order that
  retrieved it, and the extra column ``query_ids_all`` lists them all
  (``;``-joined, the 1530 and 1653 spelling);
- a record with neither DOI nor year has no deduplication key under the
  contract (a RePEc handle is not a CNRI Handle, and an EconPapers or IDEAS
  page is a landing page): it goes to ``excluded.csv`` as ``no_dedup_key``,
  which the pool still takes in as a title-only work; a template without a
  title (retrieved by its abstract, keywords or JEL codes) is
  ``not_retrievable``: the contract requires title-level metadata;
- the registry has one row per unit with its exact string (the expanded
  OpenAlex string, or the JEL groups) and its hit count. Nothing is capped, so
  every unit is complete.

``recall`` measures, for the sentinels of 1530 (``config/rel_sud_sentinels.csv``)
and 1652 (``config/rel_causal_sentinels.csv``), whether each one is in the
mirror table at all (positive control: the parser sees it) and whether the lane
retrieved it, reporting hold-out (reserve) sentinels apart; and, for the
American Economic Review 1990-1998 items that 1650 delivered without a DOI
(OpenAlex-only, "unresolved"), how many the mirror holds and with what extra
metadata.

Usage (padme):
    uv run python scripts/catalog_rel_repec_search.py search --table T.parquet \\
        --output-dir data/rel_intake/t1810-repec-local/<date> --retrieved-at <mirror date> \\
        --counts T.counts.json [--jobs 16]
    uv run python scripts/catalog_rel_repec_search.py recall --table T.parquet \\
        --delivery data/rel_intake/t1810-repec-local/<date> \\
        --toc-1650 data/rel_intake/t1650-sommaires/2026-09-30 --output recall.json
"""

import argparse
import csv
import json
import os
import re
import socket
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

import _rel_local_query as lq
import yaml
from _rel_causal_query import expand_blocks, split_and_groups
from utils import get_logger, normalize_doi, normalize_title

log = get_logger('rel_repec_search')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANE = "t1810-repec-local"
PLATFORM = "repec"
RECORD_FIELDS = [
    "record_id", "query_id", "platform", "retrieved_at", "title", "platform_record_id",
    "doi", "openalex_id", "title_original", "first_author", "all_authors", "year",
    "publication_date", "journal", "issn", "doc_type", "language", "abstract",
    "abstract_provenance", "url", "affiliation_countries", "version_hint",
    "lane_status", "lane_note",
    # extra columns, carried by the pool
    "query_ids_all", "jel", "keywords", "series_handle", "template_type",
]
REGISTRY_FIELDS = ["query_id", "platform", "query", "run_at", "n_received", "completed",
                   "filter", "n_expected", "stop_reason", "source", "question",
                   "formulation", "language", "kind"]
EXCLUDED_FIELDS = ["record_id", "query_id", "reason", "title", "note"]
DOC_TYPES = {"redif-article": "article", "redif-paper": "working-paper",
             "redif-book": "book", "redif-chapter": "book-chapter"}
DOI_SHAPE = re.compile(r"^10\.\d{4,9}/\S+$")  # the contract's check (qa_rel_intake.DOI)
TEXT_FILTER = ("title + abstract + keywords, case/accent-folded, phrase on word "
               "boundaries, last word also plural-s; no year or language filter")


def _cfg_path(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


# --- the query units ----------------------------------------------------------

def load_sentinels(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _order(spec: dict) -> tuple[int, int]:
    """The 1652 run order (``catalog_rel_causal_search._order``): priority
    families in English, citation rows, themes, French and Spanish, others."""
    g, lang, f = spec["group"], spec["language"], spec["formulation"]
    if f == "SI":
        return (1, 0)
    if spec["question_type"] == "theme":
        return (2, 0)
    if g and lang == "en":
        return (0, g)
    return (3, g) if g else (4, 0)


def plan_queries(causal: dict, fams: dict, sentinels: list[dict]) -> list[dict]:
    """The 1652 query rows with their expanded strings, in the 1652 order.

    Rebuilt here from the same configs and ``expand_blocks`` rather than
    imported from the 1652 entry point (layering rule, tests/test_script_classification.py);
    tests/test_catalog_rel_repec_search.py asserts the two plans are identical."""
    families, themes = fams["families"], fams["themes"]
    specs = []
    for qtype, source in (("family", causal["queries"]), ("theme", causal["themes"])):
        for question, by_lang in source.items():
            meta = families.get(question) or themes[question]
            for lang, forms in by_lang.items():
                for form, template in forms.items():
                    specs.append({"search_id": f"RC-{question}-{form}-{lang}", "question": question,
                                  "question_type": qtype, "group": meta.get("group", 0),
                                  "formulation": form, "language": lang,
                                  "query_string": expand_blocks(template, causal["blocks"][lang])})
    for question in list(families) + list(themes):
        ids = [s["openalex_id"] for s in sentinels
               if s["family"] == question and s["set"] == "tuning" and s["openalex_id"]]
        if not ids:
            continue
        meta = families.get(question) or themes[question]
        specs.append({"search_id": f"RC-{question}-SI-any", "question": question,
                      "question_type": "family" if question in families else "theme",
                      "group": meta.get("group", 0), "formulation": "SI", "language": "any",
                      "query_string": "cites:" + "|".join(ids)})
    specs.sort(key=_order)
    return specs


def plan_units(cfg: dict) -> list[dict]:
    """Every search unit, in registry order: causal text, causal SI (titles),
    causal JEL rows, sud T1-T4 and gap-fill, declared JEL filter."""
    src = cfg["sources"]
    with open(_cfg_path(src["causal"]), encoding="utf-8") as fh:
        causal = yaml.safe_load(fh)
    with open(_cfg_path(src["causal_families"]), encoding="utf-8") as fh:
        fams = yaml.safe_load(fh)
    sentinels = load_sentinels(_cfg_path(src["causal_sentinels"]))
    with open(_cfg_path(src["sud"]), encoding="utf-8") as fh:
        sud = yaml.safe_load(fh)
    units: list[dict] = []
    specs = plan_queries(causal, fams, sentinels)
    by_id = {s["search_id"]: s for s in specs}
    for s in specs:
        base = {"source": src["causal"], "question": s["question"],
                "formulation": s["formulation"], "language": s["language"]}
        if s["formulation"] == "SI":
            titles = [t["title"] for t in sentinels
                      if t["family"] == s["question"] and t["set"] == "tuning" and t["title"]]
            q = " OR ".join('"' + t.replace('"', " ") + '"' for t in titles)
            units.append({**base, "query_id": "RP-" + s["search_id"].replace("-any", "-titles"),
                          "kind": "text", "query": q,
                          "note": "SI replayed as a title search of the tuning sentinels (EconLit twin)"})
        else:
            units.append({**base, "query_id": "RP-" + s["search_id"], "kind": "text",
                          "query": s["query_string"]})
    econ = causal["econlit"]
    for fam in fams["families"]:
        b = by_id.get(f"RC-{fam}-IM-en") or by_id[f"RC-{fam}-IO-en"]
        mediator = split_and_groups(b["query_string"])[-1]
        codes = [c.replace("CC", "").replace("*", "").strip() for c in econ["jel"][fam]]
        units.append({"source": src["causal"], "question": fam, "formulation": "JEL",
                      "language": "en", "query_id": f"RP-RE-{fam}-JEL-en", "kind": "jel_text",
                      "jel": [codes], "query": mediator})
    for lang, themes in sud["queries"].items():
        for theme, q in (themes or {}).items():
            units.append({"source": src["sud"], "question": theme, "formulation": "TH",
                          "language": lang, "query_id": f"RP-SUD-{theme}-{lang}",
                          "kind": "text", "query": q})
    units.append({"source": src["sud"], "question": "gap_fill", "formulation": "TH",
                  "language": "en", "query_id": "RP-SUD-gapfill-en", "kind": "text",
                  "query": sud["gap_fill"]})
    for name, groups in cfg["jel"].items():
        units.append({"source": "config/rel_repec_search.yaml", "question": name,
                      "formulation": "JEL", "language": "any", "query_id": f"RP-{name}",
                      "kind": "jel", "jel": [[str(c) for c in g] for g in groups], "query": ""})
    ids = [u["query_id"] for u in units]
    dup = [k for k, n in Counter(ids).items() if n > 1]
    if dup:
        raise ValueError(f"duplicate query ids: {dup}")
    for u in units:
        if u["kind"] != "jel":
            u["ast"] = lq.parse(u["query"])
    return units


def unit_query_string(u: dict) -> str:
    if u["kind"] == "jel":
        return "JEL " + " AND ".join("(" + " OR ".join(g) + ")" for g in u["jel"])
    if u["kind"] == "jel_text":
        return ("JEL " + " AND ".join("(" + " OR ".join(g) + ")" for g in u["jel"])
                + " AND (" + u["query"] + ")")
    return u["query"]


# --- running them ---------------------------------------------------------------

def folded_texts(rows: list[dict]) -> list[str]:
    """Each field folded on its own and joined by ``|``, which ``fold`` never
    emits and no phrase contains: a phrase cannot match across the end of the
    title and the start of the abstract."""
    return ["|".join(lq.fold(r.get(k) or "") for k in ("title", "abstract", "keywords")) for r in rows]


def _chunk_hits(args: tuple[list[str], list[str], int]) -> dict[str, list[int]]:
    texts, plist, offset = args
    return lq.phrase_hits(texts, plist, offset)


def all_phrase_hits(texts: list[str], plist: list[str], jobs: int) -> dict[str, set[int]]:
    if jobs <= 1 or len(texts) < 10000:
        return {p: set(v) for p, v in lq.phrase_hits(texts, plist).items()}
    step = -(-len(texts) // (jobs * 4))
    work = [(texts[i:i + step], plist, i) for i in range(0, len(texts), step)]
    out: dict[str, set[int]] = defaultdict(set)
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for part in ex.map(_chunk_hits, work):
            for p, idx in part.items():
                out[p].update(idx)
    return {p: out.get(p, set()) for p in plist}


SCRIPTS = {"arabic": r"[\u0600-\u06ff]", "devanagari": r"[\u0900-\u097f]",
           "bengali": r"[\u0980-\u09ff]", "cyrillic": r"[\u0400-\u04ff]",
           "cjk": r"[\u3400-\u9fff]"}


def zero_hit_controls(units: list[dict], hits: dict[str, set[int]], ph: dict[str, set[int]],
                      rows: list[dict]) -> list[dict]:
    """Positive controls for every unit that retrieved nothing: the hit count of
    each of its top-level AND groups alone (the matcher sees the vocabulary; the
    conjunction is what is empty), and how many table titles are written in the
    unit's script at all."""
    script_n = {k: sum(1 for r in rows if re.search(v, r.get("title") or "")) for k, v in SCRIPTS.items()}
    lang_script = {"ar": "arabic", "hi": "devanagari", "bn": "bengali", "ru": "cyrillic", "zh": "cjk"}
    out = []
    for u in units:
        if hits[u["query_id"]] or "ast" not in u:
            continue
        groups = split_and_groups(u["query"])
        sizes = [len(lq.evaluate(lq.parse(g), ph.__getitem__, lambda: set())) for g in groups]
        out.append({"query_id": u["query_id"], "and_group_hits": "|".join(map(str, sizes)),
                    "titles_in_script": script_n.get(lang_script.get(u["language"], ""), "")})
    return out


def run_units(units: list[dict], rows: list[dict], jobs: int = 1,
              keep: dict | None = None) -> dict[str, set[int]]:
    """{query_id: indices of ``rows`` it retrieves}; ``keep`` receives the phrase hits."""
    texts = folded_texts(rows)
    plist = sorted({p for u in units if "ast" in u for p in lq.phrases(u["ast"])})
    ph = all_phrase_hits(texts, plist, jobs)
    if keep is not None:
        keep["phrase_hits"] = ph
    jel = [[c for c in (r.get("jel") or "").split(";")] for r in rows]
    universe = set(range(len(rows)))
    out: dict[str, set[int]] = {}
    for u in units:
        if u["kind"] == "text":
            out[u["query_id"]] = lq.evaluate(u["ast"], ph.__getitem__, lambda: universe)
        elif u["kind"] == "jel":
            out[u["query_id"]] = {i for i, cs in enumerate(jel) if cs[0] and lq.jel_match(cs, u["jel"])}
        else:
            text_hits = lq.evaluate(u["ast"], ph.__getitem__, lambda: universe)
            out[u["query_id"]] = {i for i in text_hits if lq.jel_match(jel[i], u["jel"])}
    return out


# --- the delivery --------------------------------------------------------------

def econpapers_url(handle: str) -> str:
    return "https://econpapers.repec.org/" + handle


def to_record(r: dict, qids: list[str], retrieved_at: str) -> dict:
    authors = [a.strip() for a in (r.get("authors") or "").split(";") if a.strip()]
    doi = normalize_doi(r.get("doi") or "") or ""
    cd = r.get("creation_date") or ""
    lang = (r.get("language") or "").strip().lower()
    note = []
    if r.get("handle_valid") == "0":
        note.append("RePEc handle malformed at source")
    if doi and not DOI_SHAPE.match(doi):
        note.append("malformed DOI in ReDIF: " + doi)
        doi = ""
    if r.get("publication_status"):
        note.append("publication status: " + r["publication_status"])
    return {
        "record_id": r["handle"], "query_id": qids[0], "platform": PLATFORM,
        "retrieved_at": retrieved_at, "title": r.get("title") or "",
        "platform_record_id": r["handle"], "doi": doi, "openalex_id": "",
        "title_original": "", "first_author": authors[0] if authors else "",
        "all_authors": "; ".join(authors), "year": r.get("year") or "",
        "publication_date": cd if len(cd) == 10 and cd[4] == "-" and cd[7] == "-" else "",
        "journal": r.get("journal") or "", "issn": "",
        "doc_type": DOC_TYPES.get(r.get("template_type") or "", r.get("template_type") or ""),
        "language": lang if len(lang) == 2 and lang.isalpha() else "",
        "abstract": r.get("abstract") or "", "abstract_provenance": "",
        "url": ("https://doi.org/" + doi) if doi else econpapers_url(r["handle"]),
        "affiliation_countries": "", "version_hint": "",
        "lane_status": "candidate", "lane_note": "; ".join(note),
        "query_ids_all": ";".join(qids), "jel": r.get("jel") or "",
        "keywords": r.get("keywords") or "", "series_handle": r.get("series_handle") or "",
        "template_type": r.get("template_type") or "",
    }


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _write_csv(path: str, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def deliver(units: list[dict], hits: dict[str, set[int]], rows: list[dict], out_dir: str,
            retrieved_at: str, run_at: str, table_counts: dict | None = None) -> dict:
    if os.path.exists(os.path.join(out_dir, "records.csv")):
        raise SystemExit(f"refusing to overwrite the delivery in {out_dir}")
    os.makedirs(out_dir, exist_ok=True)
    by_rec: dict[int, list[str]] = defaultdict(list)
    for u in units:
        for i in sorted(hits[u["query_id"]]):
            by_rec[i].append(u["query_id"])
    records, excluded = [], []
    for i in sorted(by_rec, key=lambda i: rows[i]["handle"].lower()):
        rec = to_record(rows[i], by_rec[i], retrieved_at)
        if not rec["title"].strip():
            excluded.append({"record_id": rec["record_id"], "query_id": rec["query_id"],
                             "reason": "not_retrievable", "title": "",
                             "note": f"ReDIF template without a title; {rec['url']}"})
        elif not rec["doi"] and not rec["year"]:
            excluded.append({"record_id": rec["record_id"], "query_id": rec["query_id"],
                             "reason": "no_dedup_key", "title": rec["title"],
                             "note": f"no DOI and no year in ReDIF; {rec['url']}"})
        else:
            records.append(rec)
    registry = [{"query_id": u["query_id"], "platform": PLATFORM, "query": unit_query_string(u),
                 "run_at": run_at, "n_received": len(hits[u["query_id"]]), "completed": "true",
                 "filter": ("Classification-JEL code prefixes" if u["kind"] == "jel" else
                            TEXT_FILTER + ("; AND JEL code prefixes" if u["kind"] == "jel_text" else "")),
                 "n_expected": len(hits[u["query_id"]]), "stop_reason": "",
                 "source": u["source"], "question": u["question"], "formulation": u["formulation"],
                 "language": u["language"], "kind": u["kind"]} for u in units]
    _write_csv(os.path.join(out_dir, "records.csv"), RECORD_FIELDS, records)
    _write_csv(os.path.join(out_dir, "registry.csv"), REGISTRY_FIELDS, registry)
    _write_csv(os.path.join(out_dir, "excluded.csv"), EXCLUDED_FIELDS, excluded)
    manifest = {
        "lane": LANE, "ticket": "1810", "delivery": os.path.basename(os.path.normpath(out_dir)),
        "delivered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "producer": {"script": "scripts/catalog_rel_repec_search.py", "commit": _git_commit(),
                     "machine": socket.gethostname()},
        "counts": {"records": len(records),
                   "excluded": dict(Counter(e["reason"] for e in excluded))},
        "coverage": "complete",
        "incomplete": [],
        "needs_human": [],
        "supersedes": None,
        "notes": ("Local RePEc ReDIF mirror; record_id = RePEc handle. url = DOI resolver when a "
                  "DOI is known, else the EconPapers handle page (a landing page, not a key). "
                  "1652 SI rows replayed as tuning-sentinel title searches; no citation search "
                  "(CitEc is ticket 1654). No year or language filter."),
        "mirror": table_counts or {},
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
    return manifest


def load_rows(table: str) -> list[dict]:
    import pandas as pd
    return pd.read_parquet(table).fillna("").to_dict("records")


def cmd_search(a: argparse.Namespace) -> int:
    with open(a.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    units = plan_units(cfg)
    run_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = load_rows(a.table)
    keep: dict = {}
    hits = run_units(units, rows, a.jobs, keep)
    if a.controls:
        ctl = zero_hit_controls(units, hits, keep["phrase_hits"], rows)
        _write_csv(a.controls, ["query_id", "and_group_hits", "titles_in_script"], ctl)
    counts = None
    if a.counts:
        with open(a.counts, encoding="utf-8") as fh:
            counts = json.load(fh)
    m = deliver(units, hits, rows, a.output_dir, a.retrieved_at, run_at, counts)
    log.info(json.dumps(m["counts"]))
    return 0


# --- recall --------------------------------------------------------------------

def _index(rows: list[dict]) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    by_doi: dict[str, list[int]] = defaultdict(list)
    by_title: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        d = normalize_doi(r.get("doi") or "")
        if d:
            by_doi[d].append(i)
        t = normalize_title(r.get("title") or "")
        if t:
            by_title[t].append(i)
    return by_doi, by_title


def find(rows: list[dict], idx: tuple[dict, dict], doi: str, title: str, year: str = "") -> list[int]:
    """Table rows for an item: by DOI, else by normalized title (year within 1 when both known)."""
    by_doi, by_title = idx
    d = normalize_doi(doi or "")
    if d and by_doi.get(d):
        return list(by_doi[d])
    cand = by_title.get(normalize_title(title or ""), [])
    y = (year or "")[:4]
    if y.isdigit():
        near = [i for i in cand if not str(rows[i].get("year") or "").isdigit()
                or abs(int(rows[i]["year"]) - int(y)) <= 1]
        return near
    return list(cand)


def sentinel_recall(rows: list[dict], delivered: dict[str, str], paths: list[str]) -> list[dict]:
    idx = _index(rows)
    out = []
    for path in paths:
        for s in load_sentinels(path):
            hit = find(rows, idx, s.get("doi", ""), s.get("title", ""), s.get("year", ""))
            handles = [rows[i]["handle"] for i in hit]
            got = [h for h in handles if h in delivered]
            out.append({"file": os.path.basename(path), "sentinel": s["sentinel"],
                        "set": s.get("set", ""), "class": s.get("class", ""),
                        "family": s.get("family", ""), "title": s.get("title", ""),
                        "in_mirror": bool(handles), "retrieved": bool(got),
                        "handles": "|".join(handles), "query_ids": ";".join(delivered[h] for h in got)})
    return out


def summarize_sentinels(res: list[dict]) -> dict:
    out: dict = {}
    for part, keep in (("reserve", lambda r: r["set"] == "holdout"),
                       ("non_reserve", lambda r: r["set"] != "holdout")):
        sub = [r for r in res if keep(r)]
        for f in sorted({r["file"] for r in sub}):
            s = [r for r in sub if r["file"] == f]
            out.setdefault(part, {})[f] = {
                "n": len(s), "in_mirror": sum(r["in_mirror"] for r in s),
                "retrieved": sum(r["retrieved"] for r in s),
                "recall_given_in_mirror": (round(sum(r["retrieved"] for r in s)
                                                 / max(1, sum(r["in_mirror"] for r in s)), 3)),
                "missed_in_mirror": [r["sentinel"] for r in s if r["in_mirror"] and not r["retrieved"]],
            }
    return out


def aer_recall(rows: list[dict], toc_dir: str, y0: int = 1990, y1: int = 1998) -> dict:
    """1650's American Economic Review items of ``y0``-``y1`` without a DOI
    (OpenAlex-only), matched to the AEA series of the mirror."""
    import pandas as pd
    r = pd.read_csv(os.path.join(toc_dir, "records.csv"), dtype=str, low_memory=False).fillna("")
    a = r[(r.journal_key == "aer") & (r.doi == "") & (r.toc_source == "openalex-only")]
    a = a[a.year.str[:4].str.isdigit()]
    a = a[a.year.str[:4].astype(int).between(y0, y1)]
    aer = [i for i, x in enumerate(rows) if (x.get("series_handle") or "") == "repec:aea:aecrev"]
    sub = [rows[i] for i in aer]
    idx = _index(sub)
    found = with_abs = gains_abs = 0
    miss = []
    for _, x in a.iterrows():
        hit = find(sub, idx, "", x.title, x.year)
        if hit:
            found += 1
            if any(sub[i].get("abstract") for i in hit):
                with_abs += 1
                if not x.abstract:
                    gains_abs += 1
        else:
            miss.append(x.title)
    years = Counter(str(x.get("year")) for x in sub)
    return {"toc_items": int(len(a)), "found_in_mirror": found, "found_with_abstract": with_abs,
            "abstract_added_where_1650_had_none": gains_abs,
            "mirror_aer_records_by_year": {str(y): years.get(str(y), 0) for y in range(y0, y1 + 1)},
            "missed_titles_sample": miss[:25]}


def cmd_recall(a: argparse.Namespace) -> int:
    import pandas as pd
    rows = load_rows(a.table)
    rec = pd.read_csv(os.path.join(a.delivery, "records.csv"), dtype=str).fillna("")
    exc = pd.read_csv(os.path.join(a.delivery, "excluded.csv"), dtype=str).fillna("")
    delivered = dict(zip(rec.record_id, rec.query_ids_all))
    delivered.update(dict(zip(exc.record_id, exc.query_id)))
    res = sentinel_recall(rows, delivered, [_cfg_path(p) for p in a.sentinels])
    out = {"sentinels": summarize_sentinels(res), "aer_1990_1998": aer_recall(rows, a.toc_1650)}
    stem = os.path.splitext(a.output)[0]
    _write_csv(stem + ".sentinels.csv", list(res[0].keys()), res)
    with open(a.output, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    log.info(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--table", required=True)
    s.add_argument("--config", default=os.path.join(ROOT, "config", "rel_repec_search.yaml"))
    s.add_argument("--output-dir", required=True)
    s.add_argument("--retrieved-at", required=True, help="mirror refresh date (ISO)")
    s.add_argument("--counts", help="the table's counts.json, copied into the manifest")
    s.add_argument("--jobs", type=int, default=1)
    s.add_argument("--controls", help="CSV of positive controls for zero-hit units (outside the delivery)")
    r = sub.add_parser("recall")
    r.add_argument("--table", required=True)
    r.add_argument("--delivery", required=True)
    r.add_argument("--toc-1650", required=True)
    r.add_argument("--sentinels", nargs="+",
                   default=["config/rel_sud_sentinels.csv", "config/rel_causal_sentinels.csv"])
    r.add_argument("--output", required=True)
    a = ap.parse_args(argv)
    return cmd_search(a) if a.cmd == "search" else cmd_recall(a)


if __name__ == "__main__":
    sys.exit(main())
