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
               "all_dois", "all_openalex_ids", "in_catalogue", "sources"]

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
    that every stage-1 label has exactly one fate.
    """
    rule = {k: sorted(cfg.get(k) or []) for k in ("stage1_exit_labels", "stage2_labels")}
    exit_, s2 = set(rule["stage1_exit_labels"]), set(rule["stage2_labels"])
    if exit_ & s2 or exit_ | s2 != ics.LABELS:
        raise ics.IcfScreenError(
            f"stage1_exit_labels {sorted(exit_)} and stage2_labels {sorted(s2)} must "
            f"partition the labels {sorted(ics.LABELS)}")
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
    return {
        "status": status,
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
    """View rows (pool order) and the label-matching summary; ``rule``: ``screen_rule``."""
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
    }
    return rows, summary
