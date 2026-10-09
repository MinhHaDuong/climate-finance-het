"""REL view logic shared by the view script and the stage-2 tooling (ticket 1732).

Joins pool works (``data/rel_pool/pool.csv``) with ``icf_screen`` labels and
gives each work its status; ``corpus_rel_view.py`` documents the rules and
writes the outputs.
"""

import csv
import hashlib
import re
from collections import Counter, defaultdict

import _icf_screen as ics
import pandas as pd
from pipeline_loaders import classify_rel_review_works

POOL_FIELDS = ["work_key", "openalex_id", "doi", "title", "year", "journal", "language",
               "abstract", "affiliation_countries", "doc_type", "version_hint",
               "all_dois", "all_openalex_ids", "in_catalogue", "sources", "member_record_ids",
               # ticket 2043, the minimum metadata profile; the last three are intake columns
               # (tickets 2040, 2041) the pool merge does not carry yet: blank when absent
               "first_author", "all_authors", "repec_handle", "host_org_name", "landing_page"]

# Document types that mark the published version of a work (family representative).
ARTICLE_TYPES = {"article", "journal-article", "journalarticle", "academic journal"}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_pool(path: str) -> list[dict]:
    csv.field_size_limit(1 << 30)
    with open(path, encoding="utf-8", newline="") as fh:
        return [{k: r.get(k) or "" for k in POOL_FIELDS} for r in csv.DictReader(fh)]


def _is_article(doc_type: str) -> bool:
    d = doc_type.strip().lower()
    return d in ARTICLE_TYPES or "semantics/article" in d


_SICI_TAIL = re.compile(r"\d+-[0-9a-z]?", re.IGNORECASE)


def split_hints(value: str) -> list[str]:
    """Identifiers of one ``;``/whitespace-separated cell (``version_hint``, ``all_dois``).

    A SICI DOI contains ``;`` itself (``…>3.0.co;2-h``): a fragment that is only
    its check tail (``2-h``) is joined back to the identifier before it.
    """
    out: list[str] = []
    for part in re.split(r"\s+", value.strip()):
        for i, frag in enumerate(part.split(";")):
            if i and out and _SICI_TAIL.fullmatch(frag):
                out[-1] += ";" + frag
            elif frag:
                out.append(frag)
    return out


def _hint_key(hint: str) -> tuple[str, str]:
    """``("doi", doi)``, ``("openalex", Wn)`` or ``("record", id)`` for one hint."""
    low = hint.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/",
                   "http://dx.doi.org/", "doi:"):
        if low.startswith(prefix):
            return "doi", low[len(prefix):]
    if low.startswith("10."):
        return "doi", low
    oa = re.fullmatch(r"(?:https?://openalex\.org/|openalex:)?(w\d+)", low)
    if oa:
        return "openalex", oa.group(1).upper()
    return "record", hint


def _lanes(member_record_ids: str) -> set[str]:
    """Lanes of a work's lane members (``<lane>/<delivery>:<record_id>``)."""
    out = set()
    for rid in filter(None, member_record_ids.split(";")):
        prefix = rid.partition(":")[0]
        if "/" in prefix:
            out.add(prefix.split("/", 1)[0])
    return out


def _hint_index(pool: list[dict]) -> dict:
    """``{"doi"|"openalex"|"record": {key: pool index}}``; records as ``<lane>:<id>``."""
    index: dict = {"doi": {}, "openalex": {}, "record": {}}
    for i, p in enumerate(pool):
        for doi in split_hints(p["all_dois"]):
            index["doi"].setdefault(doi.lower(), i)
        for oa in split_hints(p["all_openalex_ids"]):
            index["openalex"].setdefault(oa.upper(), i)
        for rid in filter(None, p.get("member_record_ids", "").split(";")):
            prefix, _, bare = rid.partition(":")
            if "/" in prefix and bare:
                index["record"].setdefault(f"{prefix.split('/', 1)[0]}:{bare}", i)
    return index


_UNRESOLVED = {"doi": "doi_not_in_pool", "openalex": "openalex_not_in_pool",
               "record": "record_not_in_lane"}


def _resolve_hint(hint: str, p: dict, index: dict) -> tuple[int | None, str]:
    """Pool index the hint of work ``p`` names, or ``None`` and the cause."""
    kind, key = _hint_key(hint)
    if kind != "record":
        j = index[kind].get(key)
    else:
        rec = index["record"]
        hits = {rec[k] for lane in sorted(_lanes(p.get("member_record_ids", "")))
                if (k := f"{lane}:{key}") in rec}
        if len(hits) > 1:
            return None, "ambiguous"
        j = hits.pop() if hits else None
    return j, "" if j is not None else _UNRESOLVED[kind]


def version_families(pool: list[dict], included: list[bool] | None = None
                     ) -> tuple[list[dict], dict]:
    """Work families from ``version_hint`` links (union-find), one entry per work.

    A hint names another version of the same work: a DOI (bare, ``doi:`` or a
    ``doi.org`` URL), an OpenAlex id (bare or URL), or a lane ``record_id``.
    Hints are separated by ``;`` or whitespace. DOIs resolve against
    ``all_dois``, OpenAlex ids against ``all_openalex_ids``; a record id is
    namespaced by the hinting work's own lanes (``<lane>:<record_id>`` against
    ``member_record_ids`` = ``<lane>/<delivery>:<record_id>``), so equal bare
    ids of two lanes never meet. DOI-equal records are already one pool work.

    Representative (``family_id`` is its ``work_key``): an included member
    (``included``, the REL view's ``rel_included``) before any other, then a
    published article (``ARTICLE_TYPES``) before any other type, then the
    earliest year, then the smallest ``work_key`` (the tie-break between two
    articles). ``family_first_year`` is the earliest year over all members,
    included or not: the year of first dissemination of the work.

    Returns ``[{"family_id", "family_first_year", "family_size"}]`` and a
    summary. ``families_with_mixed_final_labels``: multi-work families whose
    members differ in ``included``. Unresolved hints are split by cause:
    ``doi_not_in_pool``, ``openalex_not_in_pool``, ``record_not_in_lane`` (no
    member of the hinting work's lanes has that id), ``ambiguous`` (two lanes
    resolve it to different works; not linked).
    """
    included = included or [False] * len(pool)
    index = _hint_index(pool)
    parent = list(range(len(pool)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    unresolved: Counter = Counter()
    for i, p in enumerate(pool):
        for hint in split_hints(p["version_hint"]):
            j, why = _resolve_hint(hint, p, index)
            if j is None:
                unresolved[why] += 1
            else:
                parent[find(i)] = find(j)
    members = defaultdict(list)
    for i in range(len(pool)):
        members[find(i)].append(i)
    out: list = [None] * len(pool)
    for group in members.values():
        rep = min(group, key=lambda i: (not included[i], not _is_article(pool[i]["doc_type"]),
                                        pool[i]["year"] or "9999", pool[i]["work_key"]))
        years = [pool[i]["year"] for i in group if pool[i]["year"]]
        fam = {"family_id": pool[rep]["work_key"], "family_first_year": min(years, default=""),
               "family_size": len(group)}
        for i in group:
            out[i] = fam
    multi = [g for g in members.values() if len(g) > 1]
    summary = {"families": len(members),
               "multi_work_families": len(multi),
               "works_in_multi_work_families": sum(len(g) for g in multi),
               "families_with_mixed_final_labels": sum(
                   len({included[i] for i in g}) > 1 for g in multi),
               "version_hints_unresolved": sum(unresolved.values()),
               "version_hints_unresolved_by_cause": dict(sorted(unresolved.items()))}
    return out, summary


def match_labels(pool: list[dict], labels: list[dict]) -> tuple[dict, list, Counter]:
    """``{pool index: [labels]}``, the unmatched labels, and the match methods."""
    by_key = {p["work_key"]: i for i, p in enumerate(pool)}
    by_oa, by_doi = {}, {}
    for i, p in enumerate(pool):
        for oa in filter(None, p["all_openalex_ids"].split(";")):
            by_oa.setdefault(oa, i)
        for doi in filter(None, p["all_dois"].split(";")):
            by_doi.setdefault(doi, i)
    matched, unmatched, how = defaultdict(list), [], Counter()
    for lab in labels:
        for method, i in (("work_key", by_key.get(lab["work_key"])),
                          ("openalex_id", by_oa.get(lab["openalex_id"]) if lab["openalex_id"] else None),
                          ("doi", by_doi.get(lab["doi"]) if lab["doi"] else None)):
            if i is not None:
                matched[i].append(lab)
                how[method] += 1
                break
        else:
            unmatched.append(lab)
    return matched, unmatched, how


def screen_rule(cfg: dict) -> dict:
    """The stage-1 exit rule of ``config/rel_screen.yaml``, checked.

    ``stage1_exit_labels`` and ``stage2_labels`` must partition the labels, so
    that every stage-1 label has exactly one fate. ``stage2_unsure_in_rel``
    (boolean, required) says whether a work left ``unsure`` by stage 2 stays in
    REL, flagged.
    """
    rule = {k: sorted(cfg.get(k) or []) for k in ("stage1_exit_labels", "stage2_labels")}
    exit_, s2 = set(rule["stage1_exit_labels"]), set(rule["stage2_labels"])
    if exit_ & s2 or exit_ | s2 != ics.LABELS:
        raise ics.IcfScreenError(
            f"stage1_exit_labels {sorted(exit_)} and stage2_labels {sorted(s2)} must "
            f"partition the labels {sorted(ics.LABELS)}")
    if not isinstance(cfg.get("stage2_unsure_in_rel"), bool):
        raise ics.IcfScreenError("stage2_unsure_in_rel must be true or false")
    rule["stage2_unsure_in_rel"] = cfg["stage2_unsure_in_rel"]
    rule["stage1_joint"] = joint_rule(cfg.get("stage1_joint"))
    return rule


def joint_rule(block: dict | None) -> dict | None:
    """The design-B block of ``config/rel_screen.yaml`` (``stage1_joint``), checked.

    ``llm_models`` and ``classifier_models``: non-empty, disjoint lists of
    exact model ids; ``classifier_p_out_min`` in (0, 1]. None when absent
    (no design-B rows are recognised then).
    """
    if block is None:
        return None
    llm = sorted(block.get("llm_models") or [])
    clf = sorted(block.get("classifier_models") or [])
    thr = block.get("classifier_p_out_min")
    if not llm or not clf or set(llm) & set(clf):
        raise ics.IcfScreenError("stage1_joint: llm_models and classifier_models must be "
                                 "non-empty and disjoint")
    if isinstance(thr, bool) or not isinstance(thr, (int, float)) or not 0 < thr <= 1:
        raise ics.IcfScreenError("stage1_joint: classifier_p_out_min must be in (0, 1]")
    return {"llm_models": llm, "classifier_models": clf, "classifier_p_out_min": float(thr)}


_P_OUT = re.compile(r"^p_out=(\S+)")


def p_out_of(lab: dict) -> float | None:
    """P(out) a classifier row carries at the start of its ``why`` (``p_out=<p>``).

    ``<p>`` is the float as Python writes it at full precision (``repr``), so
    scientific notation (``1e-05``) is read too; anything that is not a number
    in [0, 1] gives None, which never drops a work.
    """
    m = _P_OUT.match(lab.get("why") or "")
    if not m:
        return None
    try:
        p = float(m.group(1))
    except ValueError:
        return None
    return p if 0 <= p <= 1 else None


def joint_role(lab: dict, joint: dict | None) -> str | None:
    """``llm``, ``classifier`` or None: the design-B role of a stage-1 row, by model."""
    if not joint:
        return None
    if lab["model"] in joint["llm_models"]:
        return "llm"
    if lab["model"] in joint["classifier_models"]:
        return "classifier"
    return None


def stage1_decisions(s1: list[dict], rule: dict) -> list[dict]:
    """Stage-1 decisions of one work, in table order (``work_status`` combines them).

    A single-labeller row (Qwen, Haiku) is one decision: it exits when its
    label is in ``stage1_exit_labels``. The design-B rows of one ``run_id``
    (``rule["stage1_joint"]``) are one decision, placed at that run's last row:
    it exits, as ``out``, only when the LLM row is ``out`` and the classifier
    row is ``out`` with P(out) >= ``classifier_p_out_min``; otherwise
    (including a run holding one of the two rows) it sends the work to
    stage 2. Its ``label`` is then the LLM's label (the classifier's when the
    LLM row is missing), so a ``stage1_label`` of ``out`` with status
    ``pending_stage2`` is a design-B disagreement; ``joint`` spells it out.
    """
    joint = rule.get("stage1_joint")
    decisions, runs = [], defaultdict(dict)
    for pos, lab in enumerate(s1):
        role = joint_role(lab, joint)
        if role:
            runs[lab["run_id"]][role] = (pos, lab)
            continue
        decisions.append({"pos": pos, "label": lab["label"], "doc_type": lab["doc_type"],
                          "exits": lab["label"] in rule["stage1_exit_labels"],
                          "model": lab["model"], "run_id": lab["run_id"], "joint": ""})
    for run_id, roles in runs.items():
        llm, clf = roles.get("llm"), roles.get("classifier")
        p = p_out_of(clf[1]) if clf else None
        exits = bool(llm and clf and llm[1]["label"] == "out" and clf[1]["label"] == "out"
                      and p is not None and p >= joint["classifier_p_out_min"])
        shown = (llm or clf)[1]
        decisions.append({
            "pos": max(pos for pos, _ in roles.values()),
            "label": "out" if exits else shown["label"], "doc_type": shown["doc_type"],
            "exits": exits, "model": "+".join(r[1]["model"] for r in (llm, clf) if r),
            "run_id": run_id,
            "joint": ";".join([f"llm={llm[1]['label'] if llm else ''}",
                               f"classifier={clf[1]['label'] if clf else ''}",
                               f"p_out={'' if p is None else p}"])})
    return sorted(decisions, key=lambda d: d["pos"])


def work_status(labs: list[dict], rule: dict) -> dict:
    """Status of one work from its labels.

    Stage 1, recall first (2026-10-01): a work with several stage-1 decisions
    (``stage1_decisions``: a Qwen or Haiku row, a design-B pair, in any order)
    leaves at stage 1 only when every one of them exits; one decision that
    sends it to stage 2 is enough, whichever came later. Stage 2: the latest
    label wins and is final.
    """
    by_stage = defaultdict(list)
    for lab in labs:
        by_stage[lab["stage"]].append(lab)
    decisions = stage1_decisions(by_stage["1"], rule)
    # Recall first: the work leaves only if every stage-1 decision exits; else
    # the latest decision that sends it on is the one shown.
    passing = [d for d in decisions if not d["exits"]]
    s1 = (passing or decisions)[-1] if decisions else None
    s2 = by_stage["2"][-1] if by_stage["2"] else None
    conflict = [st for st, labels in (("1", {(d["label"], d["exits"]) for d in decisions}),
                                      ("2", {lab["label"] for lab in by_stage["2"]}))
                if len(labels) > 1]
    if s2:
        status = "unsure_unresolved" if s2["label"] == "unsure" else s2["label"]
        final = s2
    elif s1:
        status = f"stage1_{s1['label']}" if s1["exits"] else "pending_stage2"
        final = s1
    else:
        status, final = "unscreened", None
    flagged = status == "unsure_unresolved" and rule["stage2_unsure_in_rel"]
    return {
        "status": status,
        "rel_included": "true" if status == "icf" or flagged else "false",
        "rel_flag": "unsure" if flagged else "",
        "doc_type": final["doc_type"] if final else "",
        "studied_country": s2["studied_country"] if s2 else "",
        "stage1_label": s1["label"] if s1 else "", "stage1_doc": s1["doc_type"] if s1 else "",
        "stage1_model": s1["model"] if s1 else "", "stage1_run_id": s1["run_id"] if s1 else "",
        "stage1_joint": s1["joint"] if s1 else "",
        "stage2_label": s2["label"] if s2 else "", "stage2_doc": s2["doc_type"] if s2 else "",
        "stage2_model": s2["model"] if s2 else "", "stage2_run_id": s2["run_id"] if s2 else "",
        "n_audit": len(by_stage["audit"]), "n_labels": len(labs),
        "conflict": ";".join(f"stage{st}" for st in conflict),
    }


def build_view(pool: list[dict], labels: list[dict], window_cfg: dict,
               rule: dict) -> tuple[list[dict], dict]:
    """View rows (pool order) and the summary (label matching, and ``families``).

    ``rule``: ``screen_rule``.
    """
    matched, unmatched, how = match_labels(pool, labels)
    win = classify_rel_review_works(
        pd.DataFrame({"title": [p["title"] for p in pool],
                      "year": [p["year"] for p in pool]}), config=window_cfg)
    rows = []
    for i, p in enumerate(pool):
        row = {k: p[k] for k in ("work_key", "openalex_id", "doi", "title", "year",
                                 "in_catalogue", "sources", "version_hint")}
        row.update(work_status(matched.get(i, []), rule))
        row["rel_disposition"] = win["rel_disposition"].iat[i]
        row["rel_year_status"] = win["rel_year_status"].iat[i]
        rows.append(row)
    fams, fam_summary = version_families(pool, [r["rel_included"] == "true" for r in rows])
    for row, fam in zip(rows, fams):
        row.update(fam)
    unmatched_works: dict = defaultdict(set)
    for lab in unmatched:
        unmatched_works["no_title" if not lab["title_norm_year"] else "not_in_pool"].add(
            lab["work_key"])
    summary = {
        "rows": len(labels),
        "matched_rows": len(labels) - len(unmatched),
        "matched_by": {m: how[m] for m in ("work_key", "openalex_id", "doi")},
        "unmatched_rows": len(unmatched),
        "labelled_not_in_pool_works": {k: len(unmatched_works[k])
                                       for k in ("no_title", "not_in_pool")},
        "rows_by_stage": dict(sorted(Counter(lab["stage"] for lab in labels).items())),
        "rows_by_stage_model": {f"{s}|{m}": n for (s, m), n in sorted(
            Counter((lab["stage"], lab["model"]) for lab in labels).items())},
        "families": fam_summary,
    }
    return rows, summary
