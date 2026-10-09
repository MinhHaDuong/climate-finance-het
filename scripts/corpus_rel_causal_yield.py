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
from collections import Counter, defaultdict

import _rel_eds_ids as _eds_ids
import yaml
from _rel_causal_keys import (  # noqa: F401  (re-exported for callers and tests)
    DOI_CHECK_FIELDS,
    HANDLE_API,
    DoiChecks,
    _legacy_title_key,
    assign_work_keys,
    carry_labels,
    handle_lookup,
    norm_title,
    pair_id,
    title_key,
    valid_doi,
)
from catalog_rel_sud_search import fill_blank, intake_cells, read_backfill
from utils import get_logger, normalize_doi

log = get_logger("rel_causal_yield")

DELIVERY_FIELDS = [
    "lane", "search_id", "platform", "query_string", "filter", "run_datetime",
    "archive_path", "manifest_sha256", "work_key", "openalex_id", "eds_an", "doi",
    "title", "year", "language", "type", "has_abstract", "family", "formulation",
    "family_relevance", "in_refined", "in_unified", "in_sud",
]


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


def load_labels(path, pairs, records=None):
    """{(work_key, question): label} from the judge output; with ``records``,
    also the labels ``carry_labels`` can carry to pairs the judge never saw."""
    out, raw = {}, {}
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            raw[r["pair_id"]] = r["label"]
            if r["pair_id"] in pairs:
                out[pairs[r["pair_id"]]] = r["label"]
    if records is not None:
        log.info("labels carried to new work keys: %d", carry_labels(records, out, raw))
    return out


# --- delivery in the intake-contract format (docs/rel-intake-contract.md, 1730)

INTAKE_RECORD_FIELDS = [
    "record_id", "query_id", "platform", "retrieved_at", "title", "platform_record_id",
    "doi", "openalex_id", "title_original", "first_author", "all_authors", "year",
    "publication_date", "journal", "issn", "doc_type", "language", "abstract",
    "abstract_provenance", "url", "affiliation_countries", "version_hint",
    "lane_status", "lane_note", "doi_eds_hint", "repec_handle", "eds_identity_note", "families", "formulations", "all_query_ids",
    "family_relevance", "in_refined", "in_unified", "in_sud",
    "host_org_name", "host_org_id", "source_type", "issn_l", "landing_page",
]
INTAKE_REGISTRY_FIELDS = [
    "query_id", "platform", "query", "run_at", "n_received", "completed", "filter",
    "n_expected", "stop_reason", "question", "question_type", "group", "formulation",
    "language", "pages", "cost_usd", "runs", "cursor_state", "cursor_note",
]
INTAKE_FILES = ["records.csv", "registry.csv", "excluded.csv", "manifest.json"]
# The EconLit rows were written, not run: their registry date is the lane's date.
UNRUN_DATE = "2026-09-30"
_LANG = {"English": "en", "French": "fr", "Spanish": "es", "German": "de",
         "Portuguese": "pt", "Italian": "it", "Russian": "ru", "Chinese": "zh"}


def _platform_code(platform):
    m = re.match(r"bibCNRS EDS \((\w+)\)", platform)
    return f"bibcnrs_eds_{m.group(1).lower()}" if m else platform


def _flag(v):
    return "true" if str(v).lower() == "true" else "false"


def load_eds_handles(path):
    """``{eds_an: (status, handle)}`` from ``catalog_rel_eds_repec_handles``
    (ticket 2040), or {} without a table: every edsrep record is then
    delivered with its unverified candidate in the note."""
    if not path:
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        return {r["eds_an"]: (r["status"], r["handle"]) for r in csv.DictReader(fh)}


def _eds_identity(rs, handles):
    """``(repec_handle, note)`` of a work's EDS retrievals (ticket 2040).

    The handle is set only when the mirror check matched it; a candidate that
    did not match, or a ZBW catalogue number, is named in the note, never dropped."""
    notes, handle = [], ""
    for r in rs:
        an = r.get("eds_an") or ""
        if an.startswith("edsrep."):
            status, h = handles.get(an, ("unchecked", ""))
            cand = _eds_ids.decode_edsrep(an)
            if h and not handle:
                handle = h
            elif not h:
                notes.append(f"RePEc handle {status} in the mirror: "
                             f"candidate {cand['candidate'] if cand else an}")
        elif an.startswith("EDSZBW"):
            notes.append(f"{an[3:]} is a "
                         f"{'valid ' if _eds_ids.ppn_valid(an) else 'non-checking '}"
                         "K10plus catalogue number (ZBW), not a persistent key")
    return handle, "; ".join(dict.fromkeys(notes))


def intake_rows(records, registry_all, labels, handles=None, note_column=False):
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
        # every EDS DOI of every retrieval of the work, not only the kept one's
        hints = list(dict.fromkeys(r["doi_eds"] for r in rs if r.get("doi_eds")))
        year = first.get("year")
        handle, id_note = _eds_identity(rs, handles or {})
        eds = next((r for r in rs if r.get("eds_an") and r.get("authors")), {})
        out.append(fill_blank({
            "record_id": f"1652:{wk}", "query_id": first["search_id"],
            "platform": _platform_code(first["platform"]),
            "retrieved_at": reg[first["search_id"]]["run_at"], "title": first.get("title") or "",
            "platform_record_id": first.get("openalex_id") or first.get("eds_an") or "",
            "doi": first["doi"] or next((r["doi"] for r in rs if r.get("doi_promoted")), ""),
            "openalex_id": first.get("openalex_id") or "",
            "year": str(year) if year and len(str(year)) == 4 else "",
            "publication_date": first.get("date") or "", "journal": first.get("journal") or "",
            "doc_type": first.get("type") or "",
            "first_author": (eds.get("authors") or [""])[0],
            "all_authors": "; ".join(eds.get("authors") or []),
            "issn": next((r["issn"] for r in rs if r.get("eds_an") and r.get("issn")), ""),
            "url": next((r["urls"][0] for r in rs if r.get("eds_an") and r.get("urls")), ""),
            "repec_handle": handle,
            "eds_identity_note": id_note if note_column else "",
            "language": _LANG.get(first.get("language") or "", first.get("language") or "")
            if len(first.get("language") or "") != 2 else first["language"],
            "abstract": first.get("abstract") or "",
            "affiliation_countries": "; ".join(first.get("countries") or []),
            "lane_status": "already_in_pool" if any(r["in_unified"] for r in rs) else "candidate",
            "lane_note": "family relevance is a cheap-model mechanism judgment, not the ICF screen"
                         + ("; doi is the EDS DOI: it disagrees with the DOI of a record with the "
                            "same title and year, so the two are different works"
                            if any(r.get("doi_promoted") for r in rs) else "")
                         + (f"; EDS DOI as returned, often truncated: {'; '.join(hints)}"
                            if hints else "")
                         + (f"; {id_note}" if id_note and not note_column else ""),
            "doi_eds_hint": "; ".join(hints),
            "families": "|".join(rel), "formulations": "|".join(sorted({r["formulation"] for r in rs})),
            "all_query_ids": "|".join(r["search_id"] for r in rs),
            "family_relevance": "|".join(f"{q}={lab or 'unlabelled'}" for q, lab in rel.items()),
            **{k: _flag(any(r[k] for r in rs)) for k in ("in_refined", "in_unified", "in_sud")}},
            intake_cells(first)))
        for r in rs[1:]:
            excluded.append({"record_id": f"1652:{wk}", "query_id": r["search_id"],
                             "reason": "duplicate_in_lane", "title": r.get("title") or "",
                             "note": f"{_raw_id(r)}: kept as retrieved by {first['search_id']}"
                                     + (f"; EDS DOI as returned: {r['doi_eds']}"
                                        if r.get("doi_eds") else "")})
    regs = []
    for s in registry_all:
        regs.append({
            **{k: s.get(k, "") for k in INTAKE_REGISTRY_FIELDS},
            "query_id": s["search_id"], "platform": _platform_code(s["platform"]),
            "query": s["query_string"], "run_at": s["run_at"] or UNRUN_DATE,
            "n_received": str(s["n_received"] or 0), "completed": _flag(s["completed"]),
            "cursor_state": s.get("cursor_state") or run_state(s, None)})
    return out, regs, excluded, delivered


def write_intake(out_dir, records, registry_all, labels, manifest, force=False, handles=None,
                 note_column=False):
    """Write the four delivery files; a directory that already holds any of
    them is refused unless ``force`` (a delivery is immutable once merged)."""
    taken = [n for n in INTAKE_FILES if os.path.exists(os.path.join(out_dir, n))]
    if taken and not force:
        raise SystemExit(f"{out_dir} already holds a delivery ({', '.join(taken)}); "
                         "pass --force-intake to replace it")
    rows, regs, excluded, _ = intake_rows(records, registry_all, labels, handles, note_column)
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


def _raw_id(rec):
    """The platform's own identity of a retrieved record."""
    return rec.get("openalex_id") or rec.get("eds_an") or f"{rec.get('doi')}|{rec.get('title')}"


def run_state(r, expected):
    """State of one run of a search, judged on its distinct ids (ticket 1755).

    ``complete``: the cursor ended with every announced id. ``cursor_exhausted``:
    the cursor ended after serving at least the announced number of rows, but
    OpenAlex repeated some across pages, so fewer distinct ids arrived; the
    search cannot return more, and the row counts as complete (arbitration at
    the merge of PR #1609). ``short_cursor``: the cursor ended with fewer rows
    than announced. ``record_cap``, ``error``, ``budget``, ``not_run``: the
    run stopped before the end of its cursor."""
    rows = int(r["n_received"] or 0)
    distinct = int(r.get("_distinct", rows))
    reason = r.get("stop_reason") or ""
    if str(r.get("completed")) == "True" or reason.startswith("short cursor"):
        if expected is None or distinct >= expected:
            return "complete"
        return "cursor_exhausted" if rows >= expected else "short_cursor"
    for state in ("record cap", "error", "budget", "not run"):
        if reason.startswith(state):
            return state.replace(" ", "_")
    return "stopped"


def merge_registry_rows(rows, n_union=None):
    """One registry row for a search run in several run directories.

    Counts describe the union of the retrievals; the row is complete only when
    some run reached the end of the cursor with every announced id, or
    exhausted it (``run_state``), so a run that stopped short can never pass
    for a finished one. ``cursor_state`` names the state of the deciding run,
    ``cursor_note`` details an exhausted cursor. ``n_union``, the distinct
    ids of all runs together, completes a row whose runs jointly received
    every announced id."""
    base = max(rows, key=lambda r: int(r.get("_distinct", r["n_received"] or 0)))
    expected = max((int(r["n_expected"]) for r in rows if str(r["n_expected"]).isdigit()),
                   default=None)
    states = [(r, run_state(r, expected)) for r in rows]
    complete = [r for r, s in states if s == "complete"]
    exhausted = [r for r, s in states if s == "cursor_exhausted"]
    reasons = []
    for r, s in states:
        why = r["stop_reason"].split(":")[0] if s == "short_cursor" else r["stop_reason"]
        why = why or s.replace("_", " ")
        reasons.append(f"{r['_run']}: {why} ({r.get('_distinct', r['n_received'])} of {r['n_expected']})")
    note = ""
    if complete or (n_union is not None and expected is not None and n_union >= expected):
        state = "complete"
    elif exhausted:
        state, r = "cursor_exhausted", exhausted[0]
        note = (f"{r['_run']}: cursor exhausted ({r['n_received']} rows, "
                f"{r.get('_distinct', r['n_received'])} distinct ids of {expected} announced)")
    else:
        state = dict((id(r), s) for r, s in states)[id(base)]
    done = state in ("complete", "cursor_exhausted")
    return {**base, "n_expected": "" if expected is None else expected,
            "completed": "True" if done else "False",
            "stop_reason": "" if done else "; ".join(reasons),
            "cursor_state": state, "cursor_note": note,
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
    records, seen, distinct = [], set(), defaultdict(set)
    for d in dirs:
        run_name = os.path.basename(os.path.normpath(d))
        for rec in read_jsonl_gz(os.path.join(d, "results.jsonl.gz")):
            key = (rec["search_id"], _raw_id(rec))
            distinct[(run_name, rec["search_id"])].add(key[1])
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
        for r in rows:  # the cursor's page repeats count once
            r["_distinct"] = len(distinct[(r["_run"], sid)])
        row = merge_registry_rows(rows, received.get(sid, 0))
        row["n_received"] = received.get(sid, 0)
        row.pop("_run", None)
        row.pop("_distinct", None)
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


def apply_backfill(records, backfill):
    """Fill the author, ISSN and host-organization cells of OpenAlex records from
    a ticket 2041 backfill; a value the record already has is never overwritten."""
    for r in records:
        extra = backfill.get(r.get("openalex_id") or "")
        if extra:
            r.update(fill_blank(intake_cells(r), intake_cells(extra)))
    return records


def apply_eds_requery(records, path):
    """Fill the authors, ISSN and URLs the first EDS run did not keep from the
    2026-10-09 re-query of the same strings (ticket 2040), matched on search id and
    EDS accession number. The registry, the DOIs, the titles and every other
    field stay those of the first run, so no record or work key moves; a value the
    record already has is never overwritten. Returns the number of records filled."""
    again = {(r["search_id"], r.get("eds_an") or ""): r
             for r in read_jsonl_gz(os.path.join(path, "results.jsonl.gz"))}
    n = 0
    for r in records:
        new = again.get((r["search_id"], r.get("eds_an") or "")) if r.get("eds_an") else None
        if not new:
            continue
        got = {k: new[k] for k in ("authors", "issn", "urls") if not r.get(k) and new.get(k)}
        r.update(got)
        n += bool(got)
    return n


def run(args):
    with open(args.families, encoding="utf-8") as fh:
        fam_cfg = yaml.safe_load(fh)
    mech = {q: m["mechanism"].strip() for q, m in {**fam_cfg["families"], **fam_cfg["themes"]}.items()}
    run_dirs = args.run_dir if isinstance(args.run_dir, list) else [args.run_dir]
    dirs = [d for d in run_dirs + [args.eds_dir] if d]
    registry, registry_all, records = load_runs(dirs)
    assign_work_keys(records, DoiChecks(args.doi_checks) if args.doi_checks else None)
    if getattr(args, "eds_requery", None):
        log.info("EDS re-query: %d records filled", apply_eds_requery(records, args.eds_requery))
    if getattr(args, "backfill", None):
        apply_backfill(records, read_backfill(args.backfill))
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
    labels = load_labels(args.labels, pairs, records)

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
    if args.intake_dir:
        if not args.manifest_base:
            raise SystemExit("--intake-dir needs --manifest-base")
        with open(args.manifest_base, encoding="utf-8") as fh:
            base = json.load(fh)
        handles = load_eds_handles(getattr(args, "eds_handles", None))
        n, x = write_intake(args.intake_dir, records, registry_all, labels, base,
                            force=args.force_intake, handles=handles,
                            note_column=getattr(args, "identity_note_column", False))
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
    ap.add_argument("--doi-checks", help="CSV cache of doi.org lookups of the EDS DOIs that "
                    "would split a title group; without it no EDS DOI is promoted to doi")
    ap.add_argument("--eds-handles", help="eds_repec_handles.csv of catalog_rel_eds_repec_handles: "
                    "the RePEc handles of edsrep records, checked against the mirror")
    ap.add_argument("--identity-note-column", action="store_true",
                    help="write the EDS identity note (unverified RePEc candidate, ZBW number) to "
                    "its own column eds_identity_note and leave lane_note as delivered")
    ap.add_argument("--eds-requery", help="directory with the results.jsonl.gz of the EDS re-query "
                    "(ticket 2040): fills the authors, ISSN and URLs of EDS records, nothing else")
    ap.add_argument("--backfill", help="catalog_rel_oa_backfill.py directory: fills the authors, "
                    "ISSN and host organization the OpenAlex records lack (ticket 2041)")
    ap.add_argument("--manifest-base", help="JSON with lane, ticket, delivery, delivered_at, "
                    "producer, needs_human, supersedes, notes (counts and coverage are added)")
    # Multi-output script (yields, recall, judge input, delivery): --output-dir.
    ap.add_argument("--output-dir", required=True)
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
