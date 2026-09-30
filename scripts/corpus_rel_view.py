"""The REL view: pool × icf_screen labels → status per work and counts (ticket 1732).

Joins the REL pool (``data/rel_pool/pool.csv``, ticket 1731) with the
append-only label table (``data/rel_screen/icf_screen.csv``). Regenerable: the
outputs are a function of those two files and ``config/rel_review.yaml`` only
(same inputs, byte-identical outputs; no timestamp is written).

Matching a label to a pool work: its ``work_key`` equals the work's
``work_key``; else its OpenAlex id is one of the work's member ids
(``all_openalex_ids``); else its DOI is one of the work's DOIs (``all_dois``).
A label that matches nothing is kept in the table and counted here as
"labelled, not in pool", split by whether the screened record had a title.

Status per work (latest label wins within a stage, table order):

- ``unscreened``: no label;
- ``stage1_out`` / ``stage1_aux``: excluded at stage 1, no stage-2 label;
- ``pending_stage2``: stage-1 ``icf`` or ``unsure``, no stage-2 label yet;
- ``icf`` / ``aux`` / ``out``: the stage-2 label, final;
- ``unsure_unresolved``: stage-2 ``unsure``. The exit rule for these works is
  an open author decision (ticket 1655); they are counted apart, never folded.

A stage-2 label is final whatever the stage-1 label was (the 1530 Opus pilot
judged 160 works that stage 1 had excluded). ``audit`` labels never set a
status. Works whose labels disagree within a stage (several labellers or
models) are counted as conflicts.

Window: ``pipeline_loaders.classify_rel_review_works`` (``config/rel_review.yaml``)
on title and year; the pool carries no publication date, so a 2026 work is
quarantined as partial year and counted apart. Document type: that of the
label that sets the status; institutional documents are counted apart from
research and kept. Version linking (working paper → article) is an open author
decision: works are counted as pool works, and the REL works carrying a
``version_hint`` are counted, not merged.

Outputs (``--output-dir``, default ``data/rel_pool``): ``rel_view.csv`` (one row
per pool work) and ``rel_counts.json``.

Usage:
    python scripts/corpus_rel_view.py [--pool PATH] [--table PATH] [--output-dir DIR]
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict

import _icf_screen as ics
import _rel_view as rv
import yaml
from pipeline_loaders import load_rel_review_config
from utils import get_logger

log = get_logger("corpus_rel_view")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_screen.yaml")

VIEW_COLUMNS = ["work_key", "openalex_id", "doi", "title", "year", "in_catalogue", "sources",
                "version_hint", "status", "doc_type", "studied_country",
                "stage1_label", "stage1_doc", "stage1_model", "stage1_run_id",
                "stage2_label", "stage2_doc", "stage2_model", "stage2_run_id",
                "n_audit", "n_labels", "conflict", "rel_disposition", "rel_year_status"]
STATUSES = ["unscreened", "stage1_out", "stage1_aux", "pending_stage2",
            "icf", "aux", "out", "unsure_unresolved"]


def make_counts(rows: list[dict], summary: dict, window_cfg: dict, inputs: dict) -> dict:
    status = Counter(r["status"] for r in rows)
    by_window: dict = defaultdict(Counter)
    for r in rows:
        by_window[r["status"]][r["rel_disposition"]] += 1
    partial = str(window_cfg["partial_year"])

    def n(pred):
        return sum(1 for r in rows if pred(r))

    icf = [r for r in rows if r["status"] == "icf"]
    in_window = [r for r in icf if r["rel_disposition"] == "include"
                 and r["rel_year_status"] == "complete"]
    rel = {
        "icf_total": len(icf),
        "icf_research_in_window": sum(r["doc_type"] == "research" for r in in_window),
        "icf_institutional_in_window": sum(r["doc_type"] == "institutional" for r in in_window),
        "icf_other_in_window": sum(r["doc_type"] not in ("research", "institutional")
                                   for r in in_window),
        "icf_partial_year_by_doc": dict(sorted(Counter(
            r["doc_type"] for r in icf if r["year"] == partial).items())),
        "icf_by_disposition": dict(sorted(Counter(r["rel_disposition"] for r in icf).items())),
        "icf_research_in_window_with_version_hint": sum(
            r["doc_type"] == "research" and bool(r["version_hint"]) for r in in_window),
        "icf_with_version_hint": sum(bool(r["version_hint"]) for r in icf),
        "unsure_unresolved": status["unsure_unresolved"],
        "pending_stage2": status["pending_stage2"],
        "unscreened": status["unscreened"],
    }
    return {
        "inputs": inputs,
        "window": {k: str(v) for k, v in window_cfg.items()},
        "pool_works": len(rows),
        "status": {s: status[s] for s in STATUSES},
        "status_by_window": {s: dict(sorted(by_window[s].items())) for s in STATUSES},
        "rel": rel,
        "labels": summary,
        "conflicts": {"stage1": n(lambda r: "stage1" in r["conflict"]),
                      "stage2": n(lambda r: "stage2" in r["conflict"])},
        "notes": ("status: latest label within a stage wins; stage 2 is final. "
                  "unsure_unresolved awaits the author's exit rule (1655). "
                  "icf_research_in_window: final icf, research, rel_disposition include, "
                  "complete year. The partial year is counted apart by document type. "
                  "Works are pool works; version_hint is counted, not merged (open "
                  "decision, 1655)."),
    }


def run(pool_path: str, table_path: str, out_dir: str, window_cfg: dict) -> dict:
    labels = ics.read_table(table_path)
    pool = rv.read_pool(pool_path)
    rows, summary = rv.build_view(pool, labels, window_cfg)
    inputs = {"pool": {"path": os.path.basename(pool_path), "sha256": rv.sha256_file(pool_path)},
              "table": {"path": os.path.basename(table_path), "sha256": rv.sha256_file(table_path)}}
    counts = make_counts(rows, summary, window_cfg, inputs)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "rel_view.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=VIEW_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["work_key"]):
            w.writerow({c: r[c] for c in VIEW_COLUMNS})
    with open(os.path.join(out_dir, "rel_counts.json"), "w", encoding="utf-8") as fh:
        json.dump(counts, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--pool", default=None, help="default: config pool")
    parser.add_argument("--table", default=None, help="default: config table")
    # Multi-output: rel_view.csv and rel_counts.json in one directory.
    parser.add_argument("--output-dir", default=None, help="default: config view_dir")
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    try:
        counts = run(args.pool or cfg["pool"], args.table or cfg["table"],
                     args.output_dir or cfg["view_dir"], load_rel_review_config())
    except ics.IcfScreenError as exc:
        log.error("%s", exc)
        return 1
    log.info("pool %d works; status %s", counts["pool_works"], counts["status"])
    log.info("REL: %s", counts["rel"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
