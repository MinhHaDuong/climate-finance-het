"""REL view logic shared by the view script and the stage-2 tooling (ticket 1732).

Joins pool works (``data/rel_pool/pool.csv``) with ``icf_screen`` labels and
gives each work its status; ``corpus_rel_view.py`` documents the rules and
writes the outputs.
"""

import csv
import hashlib
from collections import Counter, defaultdict

import _icf_screen as ics
import pandas as pd
from pipeline_loaders import classify_rel_review_works

POOL_FIELDS = ["work_key", "openalex_id", "doi", "title", "year", "journal", "language",
               "abstract", "affiliation_countries", "doc_type", "version_hint",
               "all_dois", "all_openalex_ids", "in_catalogue", "sources", "member_record_ids"]

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


def version_families(pool: list[dict]) -> tuple[list[dict], dict]:
    """Work families from ``version_hint`` links (union-find), one entry per work.

    A hint names another version by DOI or by a lane ``record_id``; it is
    resolved against every work's ``all_dois`` and ``member_record_ids``
    (``<lane>/<delivery>:<record_id>``). DOI-equal records are already one
    pool work. Representative: a published article (``ARTICLE_TYPES``) before
    any other type, then the earliest year, then ``work_key``. Returns
    ``[{"family_id", "family_first_year", "family_size"}]`` and a summary.
    """
    ref: dict = {}
    for i, p in enumerate(pool):
        for doi in filter(None, p["all_dois"].split(";")):
            ref.setdefault(doi.strip().lower(), i)
        for rid in filter(None, p.get("member_record_ids", "").split(";")):
            prefix, _, bare = rid.partition(":")
            ref.setdefault(rid, i)
            if "/" in prefix and bare:
                ref.setdefault(bare, i)
    parent = list(range(len(pool)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    unresolved = 0
    for i, p in enumerate(pool):
        for hint in filter(None, (h.strip() for h in p["version_hint"].split(";"))):
            j = ref.get(hint, ref.get(hint.lower()))
            if j is None:
                unresolved += 1
            else:
                parent[find(i)] = find(j)
    members = defaultdict(list)
    for i in range(len(pool)):
        members[find(i)].append(i)
    out: list = [None] * len(pool)
    for group in members.values():
        rep = min(group, key=lambda i: (not _is_article(pool[i]["doc_type"]),
                                        pool[i]["year"] or "9999", pool[i]["work_key"]))
        years = [pool[i]["year"] for i in group if pool[i]["year"]]
        fam = {"family_id": pool[rep]["work_key"], "family_first_year": min(years, default=""),
               "family_size": len(group)}
        for i in group:
            out[i] = fam
    summary = {"families": len(members),
               "multi_work_families": sum(len(g) > 1 for g in members.values()),
               "works_in_multi_work_families": sum(len(g) for g in members.values() if len(g) > 1),
               "version_hints_unresolved": unresolved}
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
    return rule


def work_status(labs: list[dict], rule: dict) -> dict:
    """Status of one work from its labels (table order: the last one wins)."""
    by_stage = defaultdict(list)
    for lab in labs:
        by_stage[lab["stage"]].append(lab)
    s1 = by_stage["1"][-1] if by_stage["1"] else None
    s2 = by_stage["2"][-1] if by_stage["2"] else None
    conflict = [st for st in ("1", "2") if len({lab["label"] for lab in by_stage[st]}) > 1]
    if s2:
        status = "unsure_unresolved" if s2["label"] == "unsure" else s2["label"]
        final = s2
    elif s1:
        status = (f"stage1_{s1['label']}" if s1["label"] in rule["stage1_exit_labels"]
                  else "pending_stage2")
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
    fams, fam_summary = version_families(pool)
    win = classify_rel_review_works(
        pd.DataFrame({"title": [p["title"] for p in pool],
                      "year": [p["year"] for p in pool]}), config=window_cfg)
    rows = []
    for i, p in enumerate(pool):
        row = {k: p[k] for k in ("work_key", "openalex_id", "doi", "title", "year",
                                 "in_catalogue", "sources", "version_hint")}
        row.update(work_status(matched.get(i, []), rule))
        row.update(fams[i])
        row["rel_disposition"] = win["rel_disposition"].iat[i]
        row["rel_year_status"] = win["rel_year_status"].iat[i]
        rows.append(row)
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
