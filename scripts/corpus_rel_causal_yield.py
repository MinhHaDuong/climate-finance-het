"""Yield, sentinel recall and delivery of the REL causal-map lane (ticket 1652).

Reads the OpenAlex run (``catalog_rel_causal_search.py``) and, when given, the
bibCNRS EDS run (``catalog_rel_causal_eds.py``); matches every retrieved record
to a work (DOI, then OpenAlex id, then normalised title and year) and to three
reference sets: the refined corpus, the raw merged pool (``unified_works``) and
the Sud search results (ticket 1530). Writes:

- ``yield_by_search.csv``, ``yield_by_formulation.csv``, ``yield_by_question.csv``:
  raw hits, unique works, absent from refined / unified / Sud, works no other
  formulation of the lane retrieved, and relevant counts once labels exist;
- ``sentinel_recall.csv``: per sentinel, the searches that retrieved it;
- ``judge_input.jsonl``: one (work, question) pair per line for the
  family-relevance judge (``corpus_rel_causal_judge.py``);
- ``delivery.csv``: one row per retrieval with provenance;
- with ``--intake-dir`` and ``--manifest-base``: the delivery to the pool (1655)
  in the intake-contract layout (records, registry, excluded, manifest).

A search run in several run directories keeps the union of its retrievals, and
a conservation check fails the run if any retrieved raw id is missing from the
delivery.

Every record is delivered: the relevance label is information, not a filter.

Usage:
    python scripts/corpus_rel_causal_yield.py --run-dir RUN --eds-dir EDS \
        --refined refined_works.csv --unified unified_works.csv \
        --sud-results a/results.jsonl.gz b/results.jsonl.gz \
        [--labels JUDGE/labels.jsonl] --archive-path PATH --output-dir OUT
"""

import argparse
import csv
import gzip
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

import yaml
from utils import get_logger, normalize_doi

log = get_logger("rel_causal_yield")

DELIVERY_FIELDS = [
    "lane", "search_id", "platform", "query_string", "filter", "run_datetime",
    "archive_path", "manifest_sha256", "work_key", "openalex_id", "eds_an", "doi",
    "title", "year", "language", "type", "has_abstract", "family", "formulation",
    "family_relevance", "in_refined", "in_unified", "in_sud",
]


_DOI = re.compile(r"^10\.\d{4,9}/\S+$")


def valid_doi(doi):
    """The normalised DOI, or "" for a truncated one (EDS returns bare
    prefixes such as `10.35219`, which would join unrelated works)."""
    d = normalize_doi(doi or "")
    return d if _DOI.match(d) else ""


def norm_title(title):
    t = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def title_key(title, year):
    t = norm_title(title)
    return f"{t}|{year}" if len(t) >= 20 and year else ""


class RefSet:
    """DOIs, OpenAlex ids and title+year keys of a reference collection."""

    def __init__(self):
        self.dois, self.ids, self.titles = set(), set(), set()

    def add(self, doi="", oa_id="", title="", year=None):
        if doi:
            self.dois.add(normalize_doi(doi))
        if oa_id:
            self.ids.add(oa_id)
        if k := title_key(title, year):
            self.titles.add(k)

    def __contains__(self, rec):
        return bool((rec.get("doi") and rec["doi"] in self.dois)
                    or (rec.get("openalex_id") and rec["openalex_id"] in self.ids)
                    or ((k := title_key(rec.get("title"), rec.get("year"))) and k in self.titles))


def load_catalog(path):
    ref = RefSet()
    if not path:
        return ref
    csv.field_size_limit(10**8)
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            year = row.get("year", "")
            year = int(float(year)) if year.replace(".", "", 1).isdigit() else None
            ref.add(row.get("doi", ""),
                    row["source_id"] if row.get("source") == "openalex" else "",
                    row.get("title", ""), year)
    return ref


# The corpus keyword probe: the protocol's indicative co-occurrence count
# ("finance-réseau" and so on) redone per family, in English, on title and
# abstract of the refined corpus: a short climate-finance term set AND the
# mediator group of the family's first English search string.
PROBE_FINANCE = ("climate finance", "climate aid", "climate fund", "climate funds",
                 "mitigation finance", "adaptation finance")


def _phrase_re(phrases):
    return re.compile("|".join(r"(?<!\w)" + re.escape(p.lower()) + r"(?!\w)" for p in phrases))


def probe_patterns(search_cfg):
    """{question: compiled mediator pattern} from the first English string."""
    from _rel_causal_query import expand_blocks, split_and_groups
    out = {}
    for source in (search_cfg["queries"], search_cfg["themes"]):
        for q, by_lang in source.items():
            template = next(iter(by_lang.get("en", {}).values()), None)
            if template is None:
                continue
            groups = split_and_groups(expand_blocks(template, search_cfg["blocks"]["en"]))
            out[q] = _phrase_re(re.findall(r'"([^"]+)"', groups[-1]))
    return out


def keyword_probe(path, patterns):
    """({question: RefSet of refined works the probe recognises}, {question: count})."""
    fin = _phrase_re(PROBE_FINANCE)
    sets, counts = {q: RefSet() for q in patterns}, Counter()
    csv.field_size_limit(10**8)
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            text = f"{row.get('title', '')} {row.get('abstract', '')}".lower()
            if not fin.search(text):
                continue
            year = row.get("year", "")
            year = int(float(year)) if year.replace(".", "", 1).isdigit() else None
            for q, pat in patterns.items():
                if pat.search(text):
                    counts[q] += 1
                    sets[q].add(row.get("doi", ""),
                                row["source_id"] if row.get("source") == "openalex" else "",
                                row.get("title", ""), year)
    return sets, counts


def outcome_inputs(records, labels, probes, probe_counts, fam_cfg):
    """Per question: relevant works and how many the corpus keyword probe
    recognises; the evidence behind the three outcomes of the protocol."""
    meta = {**fam_cfg["families"], **fam_cfg["themes"]}
    by_q = defaultdict(dict)
    for r in records:
        if labels.get((r["work_key"], r["question"])) == "relevant":
            by_q[r["question"]].setdefault(r["work_key"], r)
    rows = []
    for q, m in meta.items():
        rel = list(by_q.get(q, {}).values())
        probe = probes.get(q, RefSet())
        rows.append({
            "question": q, "group": m.get("group", ""), "a_priori": m.get("a_priori", "theme"),
            "probe_hits_in_refined": probe_counts.get(q, 0),
            "relevant": len(rel),
            "relevant_in_refined": sum(r["in_refined"] for r in rel),
            "relevant_recognised_by_probe": sum(bool(r["in_refined"] and r in probe) for r in rel),
            "relevant_absent_refined": sum(not r["in_refined"] for r in rel),
            "relevant_absent_all_three": sum(not (r["in_refined"] or r["in_unified"] or r["in_sud"])
                                             for r in rel)})
    return rows


def read_jsonl_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def load_sud(paths):
    ref = RefSet()
    for p in paths or []:
        for r in read_jsonl_gz(p):
            ref.add(r.get("doi", ""), r.get("openalex_id", ""), r.get("title", ""), r.get("year"))
    return ref


def read_registry(path, with_econlit=False):
    with open(path, encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if with_econlit or r["platform"] != "econlit"]


def assign_work_keys(records):
    """Work key per record: its DOI; else the DOI another record gives its
    OpenAlex id or its title+year; else its OpenAlex id; else the key of an
    identified record with the same title+year; else a title+year key. The
    title join also covers an OpenAlex record without DOI and an EDS record
    carrying one, which an id-first rule would keep apart."""
    by_oa = {r["openalex_id"]: "doi:" + r["doi"] for r in records
             if r.get("doi") and r.get("openalex_id")}
    doi_by_title, oa_by_title = {}, {}
    for r in records:
        k = title_key(r.get("title"), r.get("year"))
        if k and r.get("doi"):
            doi_by_title.setdefault(k, "doi:" + r["doi"])
        elif k and r.get("openalex_id"):
            oa_by_title.setdefault(k, by_oa.get(r["openalex_id"], "oa:" + r["openalex_id"]))
    for r in records:
        k = title_key(r.get("title"), r.get("year"))
        if r.get("doi"):
            r["work_key"] = "doi:" + r["doi"]
        elif r.get("openalex_id"):
            r["work_key"] = (by_oa.get(r["openalex_id"]) or doi_by_title.get(k)
                             or "oa:" + r["openalex_id"])
        else:
            r["work_key"] = (doi_by_title.get(k) or oa_by_title.get(k)
                             or ("ty:" + k if k else "")
                             or ("edsdoi:" + r["doi_eds"] if r.get("doi_eds") else "")
                             or "an:" + r.get("eds_an", ""))
    return records


def lane_of(platform):
    return "openalex" if platform == "openalex" else "eds"


def yields(records, registry, labels, group_key):
    """Rows of yield counts grouped by ``group_key(registry_row)``."""
    reg = {r["search_id"]: r for r in registry}
    works_by_group, pairs_by_group = defaultdict(set), defaultdict(set)
    hits = Counter()
    info = {}
    for r in records:
        g = group_key(reg[r["search_id"]])
        works_by_group[g].add(r["work_key"])
        pairs_by_group[g].add((r["work_key"], r["question"]))
        info.setdefault(r["work_key"], r)
    for s in registry:
        hits[group_key(s)] += int(s["n_received"] or 0)
    # marginal uniqueness: works no other group of the same lane retrieved
    lane_groups = defaultdict(list)
    for g in works_by_group:  # lane-level rows compare the lanes with each other
        lane_groups[g[0] if len(g) > 1 else "*"].append(g)
    rows = []
    for g in sorted(set(hits) | set(works_by_group)):
        ws = works_by_group.get(g, set())
        others = set().union(*(works_by_group[o] for o in lane_groups[g[0] if len(g) > 1 else "*"]
                               if o != g))
        rel = {w for w, q in pairs_by_group.get(g, ()) if labels.get((w, q)) == "relevant"}
        row = {"lane": g[0], "group": "|".join(str(x) for x in g[1:]), "raw_hits": hits[g],
               "unique_works": len(ws),
               "absent_refined": sum(not info[w]["in_refined"] for w in ws),
               "absent_unified": sum(not info[w]["in_unified"] for w in ws),
               "absent_sud": sum(not info[w]["in_sud"] for w in ws),
               "absent_all_three": sum(not (info[w]["in_refined"] or info[w]["in_unified"]
                                            or info[w]["in_sud"]) for w in ws),
               "only_this_group": len(ws - others)}
        if labels:
            row.update(relevant=len(rel),
                       relevant_absent_refined=sum(not info[w]["in_refined"] for w in rel),
                       relevant_absent_all_three=sum(not (info[w]["in_refined"] or info[w]["in_unified"]
                                                          or info[w]["in_sud"]) for w in rel),
                       relevant_only_this_group=len(rel - others))
        rows.append(row)
    return rows


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def load_labels(path, pairs):
    """{(work_key, question): label} from the judge output."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["pair_id"] in pairs:
                out[pairs[r["pair_id"]]] = r["label"]
    return out


# --- delivery in the intake-contract format (docs/rel-intake-contract.md, 1730)

INTAKE_RECORD_FIELDS = [
    "record_id", "query_id", "platform", "retrieved_at", "title", "platform_record_id",
    "doi", "openalex_id", "title_original", "first_author", "all_authors", "year",
    "publication_date", "journal", "issn", "doc_type", "language", "abstract",
    "abstract_provenance", "url", "affiliation_countries", "version_hint",
    "lane_status", "lane_note", "families", "formulations", "all_query_ids",
    "family_relevance", "in_refined", "in_unified", "in_sud",
]
INTAKE_REGISTRY_FIELDS = [
    "query_id", "platform", "query", "run_at", "n_received", "completed", "filter",
    "n_expected", "stop_reason", "question", "question_type", "group", "formulation",
    "language", "pages", "cost_usd", "runs",
]
# The EconLit rows were written, not run: their registry date is the lane's date.
UNRUN_DATE = "2026-09-30"
_LANG = {"English": "en", "French": "fr", "Spanish": "es", "German": "de",
         "Portuguese": "pt", "Italian": "it", "Russian": "ru", "Chinese": "zh"}


def _platform_code(platform):
    m = re.match(r"bibCNRS EDS \((\w+)\)", platform)
    return f"bibcnrs_eds_{m.group(1).lower()}" if m else platform


def _flag(v):
    return "true" if str(v).lower() == "true" else "false"


def intake_rows(records, registry_all, labels):
    """(records rows, registry rows, excluded rows, delivered raw ids) of the
    intake contract.

    One record per work: the first retrieval (OpenAlex before EDS, matrix
    order); every other retrieval of the same work is `duplicate_in_lane`.
    Families, formulations and relevance labels of all retrievals are carried
    in extra columns, as information."""
    reg = {r["search_id"]: r for r in registry_all}
    order = {sid: i for i, sid in enumerate(reg)}
    by_work = defaultdict(list)
    for r in records:
        by_work[r["work_key"]].append(r)
    out, excluded, delivered = [], [], set()
    for wk, rs in by_work.items():
        delivered |= {_raw_id(r) for r in rs}
        rs.sort(key=lambda r: (not (r.get("title") or "").strip(), r["platform"] != "openalex",
                               order[r["search_id"]]))
        first = rs[0]
        if not (first.get("title") or "").strip():
            # no retrieval of this work carries a title: the contract's not_retrievable
            excluded.append({"record_id": f"1652:{wk}", "query_id": first["search_id"],
                             "reason": "not_retrievable", "title": "",
                             "note": f"{first.get('openalex_id') or first.get('eds_an')}: "
                                     "no title in the platform record"})
            excluded += [{"record_id": f"1652:{wk}", "query_id": r["search_id"],
                          "reason": "duplicate_in_lane", "title": "", "note": "untitled work"}
                         for r in rs[1:]]
            continue
        rel = {q: labels.get((wk, q), "") for q in dict.fromkeys(r["question"] for r in rs)}
        year = first.get("year")
        out.append({
            "record_id": f"1652:{wk}", "query_id": first["search_id"],
            "platform": _platform_code(first["platform"]),
            "retrieved_at": reg[first["search_id"]]["run_at"], "title": first.get("title") or "",
            "platform_record_id": first.get("openalex_id") or first.get("eds_an") or "",
            "doi": first["doi"], "openalex_id": first.get("openalex_id") or "",
            "year": str(year) if year and len(str(year)) == 4 else "",
            "publication_date": first.get("date") or "", "journal": first.get("journal") or "",
            "doc_type": first.get("type") or "",
            "language": _LANG.get(first.get("language") or "", first.get("language") or "")
            if len(first.get("language") or "") != 2 else first["language"],
            "abstract": first.get("abstract") or "",
            "affiliation_countries": "; ".join(first.get("countries") or []),
            "lane_status": "already_in_pool" if any(r["in_unified"] for r in rs) else "candidate",
            "lane_note": "family relevance is a cheap-model mechanism judgment, not the ICF screen"
                         + (f"; EDS DOI as returned, often truncated: {first['doi_eds']}"
                            if first.get("doi_eds") else ""),
            "families": "|".join(rel), "formulations": "|".join(sorted({r["formulation"] for r in rs})),
            "all_query_ids": "|".join(r["search_id"] for r in rs),
            "family_relevance": "|".join(f"{q}={lab or 'unlabelled'}" for q, lab in rel.items()),
            **{k: _flag(any(r[k] for r in rs)) for k in ("in_refined", "in_unified", "in_sud")}})
        for r in rs[1:]:
            excluded.append({"record_id": f"1652:{wk}", "query_id": r["search_id"],
                             "reason": "duplicate_in_lane", "title": r.get("title") or "",
                             "note": f"{_raw_id(r)}: kept as retrieved by {first['search_id']}"})
    regs = []
    for s in registry_all:
        regs.append({
            **{k: s.get(k, "") for k in INTAKE_REGISTRY_FIELDS},
            "query_id": s["search_id"], "platform": _platform_code(s["platform"]),
            "query": s["query_string"], "run_at": s["run_at"] or UNRUN_DATE,
            "n_received": str(s["n_received"] or 0), "completed": _flag(s["completed"])})
    return out, regs, excluded, delivered


def write_intake(out_dir, records, registry_all, labels, manifest, force=False):
    """Write the four delivery files; a directory that already holds a
    delivery is refused unless ``force`` (a delivery is immutable once merged)."""
    if os.path.exists(os.path.join(out_dir, "records.csv")) and not force:
        raise SystemExit(f"{out_dir} already holds a delivery; pass --force-intake to replace it")
    rows, regs, excluded, _ = intake_rows(records, registry_all, labels)
    os.makedirs(out_dir, exist_ok=True)
    for name, fields, data in (("records.csv", INTAKE_RECORD_FIELDS, rows),
                               ("registry.csv", INTAKE_REGISTRY_FIELDS, regs),
                               ("excluded.csv", ["record_id", "query_id", "reason", "title", "note"],
                                excluded)):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(data)
    incomplete = [{"unit": s["search_id"], "reason": s["stop_reason"]}
                  for s in registry_all if _flag(s["completed"]) == "false"]
    manifest = {**manifest,
                "counts": {"records": len(rows),
                           "excluded": dict(Counter(e["reason"] for e in excluded))},
                "coverage": "incomplete" if incomplete else "complete",
                "incomplete": incomplete}
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
    return len(rows), len(excluded)


def pair_id(work_key, question):
    return f"{question}::{work_key}"


def _raw_id(rec):
    """The platform's own identity of a retrieved record."""
    return rec.get("openalex_id") or rec.get("eds_an") or f"{rec.get('doi')}|{rec.get('title')}"


def merge_registry_rows(rows):
    """One registry row for a search run in several run directories.

    Counts describe the union of the retrievals; the row is complete only when
    some run reached the end of the cursor AND received what it announced, so a
    run that stopped short can never pass for a finished one."""
    base = max(rows, key=lambda r: int(r["n_received"] or 0))
    expected = max((int(r["n_expected"]) for r in rows if str(r["n_expected"]).isdigit()),
                   default=None)
    done = [r for r in rows if r["completed"] == "True"
            and (expected is None or int(r["n_received"] or 0) >= expected)]
    reasons = []
    for r in rows:
        why = r["stop_reason"] or ("short cursor" if r["completed"] == "True" else "")
        reasons.append(f"{r['_run']}: {why or 'complete'} ({r['n_received']} of {r['n_expected']})")
    return {**base, "n_expected": "" if expected is None else expected,
            "completed": "True" if done else "False",
            "stop_reason": "" if done else "; ".join(reasons),
            "runs": "|".join(r["_run"] for r in rows)}


def load_runs(dirs):
    """(registry, registry with the EconLit rows, records) of the run directories.

    A search run in several directories (reruns of errored or capped rows)
    keeps the union of its retrievals, one record per raw platform id: a rerun
    never loses what an earlier run retrieved."""
    by_id, econlit_rows = defaultdict(list), []
    for d in dirs:
        for r in read_registry(os.path.join(d, "registry.csv"), with_econlit=True):
            if r["platform"] == "econlit":
                econlit_rows.append(r)
            else:
                by_id[r["search_id"]].append({**r, "_run": os.path.basename(os.path.normpath(d))})
    meta = {sid: rows[0] for sid, rows in by_id.items()}
    records, seen = [], set()
    for d in dirs:
        for rec in read_jsonl_gz(os.path.join(d, "results.jsonl.gz")):
            key = (rec["search_id"], _raw_id(rec))
            if key in seen:
                continue
            seen.add(key)
            s = meta[rec["search_id"]]
            rec.setdefault("openalex_id", "")
            rec.setdefault("eds_an", "")
            rec["doi"] = valid_doi(rec.get("doi") or "")
            if s["platform"] != "openalex":
                # EDS (RePEc, ECONIS) cuts DOIs short: 528 of the 552 title+year
                # twins of an OpenAlex work carry a strict prefix of its DOI. Kept
                # as a hint, never used as an identifier.
                rec["doi_eds"], rec["doi"] = rec["doi"], ""
            rec.update(question=s["question"], formulation=s["formulation"],
                       platform=s["platform"], language_q=s["language"])
            records.append(rec)
    received = Counter(r["search_id"] for r in records)
    registry = []
    for sid, rows in by_id.items():
        row = merge_registry_rows(rows)
        row["n_received"] = received.get(sid, 0)
        row.pop("_run", None)
        registry.append(row)
    return registry, registry + econlit_rows, records


def raw_ids(dirs):
    """Distinct raw platform ids retrieved in the run directories."""
    return {_raw_id(rec) for d in dirs for rec in read_jsonl_gz(os.path.join(d, "results.jsonl.gz"))}


def check_conservation(dirs, records, delivered_ids):
    """Every raw id retrieved lands in the delivery (records or excluded)."""
    loaded = {_raw_id(r) for r in records}
    missing = (raw_ids(dirs) - loaded) | (loaded - delivered_ids)
    if missing:
        raise SystemExit(f"conservation: {len(missing)} retrieved ids missing from the delivery, "
                         f"e.g. {sorted(missing)[:5]}")
    return len(loaded)


def sentinel_recall(sentinels, records, refined, unified):
    rows = []
    for s in sentinels:
        doi, oid = normalize_doi(s["doi"]), s["openalex_id"]
        tk = title_key(s["title"], s["year"])
        keys = {k for k in (doi and "doi:" + doi, oid and "oa:" + oid, tk and "ty:" + tk) if k}
        # a record joined to the sentinel's work by title carries the work's key
        hits = [r for r in records if r["work_key"] in keys
                or (oid and r.get("openalex_id") == oid) or (doi and r["doi"] == doi)
                or (tk and title_key(r.get("title"), r.get("year")) == tk)]
        own = [r for r in hits if r["question"] == s["family"]]
        probe = {"doi": doi, "openalex_id": oid, "title": s["title"],
                 "year": int(s["year"]) if s["year"].isdigit() else None}
        rows.append({**{k: s[k] for k in ("sentinel", "family", "set", "source")},
                     "in_refined": probe in refined, "in_unified": probe in unified,
                     "found_any_search": bool(hits), "found_own_family": bool(own),
                     "found_openalex": any(r["platform"] == "openalex" for r in hits),
                     "found_eds": any(r["platform"] != "openalex" for r in hits),
                     "searches": "|".join(sorted({r["search_id"] for r in hits}))})
    return rows


def write_delivery(path, records, registry, labels, archive_path, manifest_sha256):
    """Every retrieval, one row each, with its provenance."""
    reg = {r["search_id"]: r for r in registry}
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, DELIVERY_FIELDS)
        w.writeheader()
        for r in records:
            s = reg[r["search_id"]]
            w.writerow({
                "lane": "1652", "search_id": r["search_id"], "platform": s["platform"],
                "query_string": s["query_string"], "filter": s["filter"], "run_datetime": s["run_at"],
                "archive_path": archive_path, "manifest_sha256": manifest_sha256,
                "work_key": r["work_key"], "openalex_id": r.get("openalex_id", ""),
                "eds_an": r.get("eds_an", ""), "doi": r["doi"], "title": r.get("title", ""),
                "year": r.get("year") or "", "language": r.get("language") or "",
                "type": r.get("type") or "", "has_abstract": bool(r.get("abstract")),
                "family": r["question"], "formulation": r["formulation"],
                "family_relevance": labels.get((r["work_key"], r["question"]), ""),
                "in_refined": r["in_refined"], "in_unified": r["in_unified"], "in_sud": r["in_sud"]})


def run(args):
    with open(args.families, encoding="utf-8") as fh:
        fam_cfg = yaml.safe_load(fh)
    mech = {q: m["mechanism"].strip() for q, m in {**fam_cfg["families"], **fam_cfg["themes"]}.items()}
    run_dirs = args.run_dir if isinstance(args.run_dir, list) else [args.run_dir]
    dirs = [d for d in run_dirs + [args.eds_dir] if d]
    registry, registry_all, records = load_runs(dirs)
    assign_work_keys(records)
    refined, unified, sud = load_catalog(args.refined), load_catalog(args.unified), load_sud(args.sud_results)
    for r in records:
        r.update(in_refined=r in refined, in_unified=r in unified, in_sud=r in sud)
    log.info("%d records, %d works", len(records), len({r["work_key"] for r in records}))

    os.makedirs(args.output_dir, exist_ok=True)
    # judge input: one pair per (work, question)
    pairs, seen = {}, set()
    with open(os.path.join(args.output_dir, "judge_input.jsonl"), "w", encoding="utf-8") as fh:
        for r in records:
            key = (r["work_key"], r["question"])
            pid = pair_id(*key)
            pairs[pid] = key
            if pid in seen:
                continue
            seen.add(pid)
            fh.write(json.dumps({"pair_id": pid, "question": r["question"],
                                 "mechanism": mech[r["question"]], "title": r.get("title"),
                                 "abstract": r.get("abstract"), "year": r.get("year"),
                                 "language": r.get("language"), "journal": r.get("journal"),
                                 "countries": r.get("countries") or []},
                                ensure_ascii=False) + "\n")
    labels = load_labels(args.labels, pairs)

    groupings = {
        "yield_by_search.csv": lambda s: (lane_of(s["platform"]), s["search_id"]),
        "yield_by_formulation.csv": lambda s: (lane_of(s["platform"]), s["formulation"], s["language"]),
        "yield_by_question.csv": lambda s: (lane_of(s["platform"]), s["question"]),
        "yield_by_lane.csv": lambda s: (lane_of(s["platform"]),),
    }
    for name, key in groupings.items():
        write_csv(os.path.join(args.output_dir, name), yields(records, registry, labels, key))

    if args.search_config and args.refined:
        with open(args.search_config, encoding="utf-8") as fh:
            probes, counts = keyword_probe(args.refined, probe_patterns(yaml.safe_load(fh)))
        write_csv(os.path.join(args.output_dir, "family_outcome_inputs.csv"),
                  outcome_inputs(records, labels, probes, counts, fam_cfg))

    with open(args.sentinels, encoding="utf-8", newline="") as fh:
        sentinels = list(csv.DictReader(fh))
    write_csv(os.path.join(args.output_dir, "sentinel_recall.csv"),
              sentinel_recall(sentinels, records, refined, unified))
    write_delivery(os.path.join(args.output_dir, "delivery.csv"), records, registry, labels,
                   args.archive_path, args.manifest_sha256)
    log.info("wrote yields, sentinel recall, %d judge pairs and %d delivery rows",
             len(seen), len(records))
    # conservation: every raw id retrieved in any run lands in the delivery
    n_ids = check_conservation(dirs, records, intake_rows(records, registry_all, labels)[3])
    log.info("conservation: %d distinct raw ids, all delivered", n_ids)
    if getattr(args, "intake_dir", None):
        if not args.manifest_base:
            raise SystemExit("--intake-dir needs --manifest-base")
        with open(args.manifest_base, encoding="utf-8") as fh:
            base = json.load(fh)
        n, x = write_intake(args.intake_dir, records, registry_all, labels, base,
                            force=getattr(args, "force_intake", False))
        log.info("intake delivery: %d records, %d excluded rows", n, x)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", required=True, nargs="+",
                    help="OpenAlex run directories; a later one supersedes the ids it reran")
    ap.add_argument("--eds-dir")
    ap.add_argument("--refined")
    ap.add_argument("--unified")
    ap.add_argument("--sud-results", nargs="*")
    ap.add_argument("--labels")
    ap.add_argument("--families", default="config/rel_causal_families.yaml")
    ap.add_argument("--sentinels", default="config/rel_causal_sentinels.csv")
    ap.add_argument("--search-config", default="config/rel_causal_search.yaml",
                    help="for the corpus keyword probe (needs --refined)")
    ap.add_argument("--archive-path", default="")
    ap.add_argument("--manifest-sha256", default="",
                    help="SHA-256 of the archive's MANIFEST.sha256 file")
    ap.add_argument("--intake-dir", help="also write the delivery in the 1730 intake format")
    ap.add_argument("--force-intake", action="store_true",
                    help="replace an existing, not yet merged delivery")
    ap.add_argument("--manifest-base", help="JSON with lane, ticket, delivery, delivered_at, "
                    "producer, needs_human, supersedes, notes (counts and coverage are added)")
    # Multi-output script (yields, recall, judge input, delivery): --output-dir.
    ap.add_argument("--output-dir", required=True)
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
