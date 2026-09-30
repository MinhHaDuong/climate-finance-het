"""Stage-1 input of the ICF screen: every unscreened REL pool work (ticket 1733).

Computes the REL view in memory from the pool and the ``icf_screen`` table
(``_rel_view.build_view``, as ``corpus_icf_stage2.py build`` does, so the input
is never staler than the table) and writes one JSON line per work whose status
is ``unscreened``, in the record format ``corpus_rel_sud_screen.py`` reads:
``work_key`` (the screener's ``--id-field``), ``openalex_id``, ``doi``,
``title``, ``year``, ``language``, ``journal``, ``countries`` (the list of
``affiliation_countries``) and ``abstract``. The screener's prompt shows the
same fields for these records as for the 1530 ones.

Order: by lane priority (``config/rel_screen.yaml`` → ``stage1.lane_priority``),
so that small, complete lanes finish before the long ones, then by
``work_key``. A work belongs to the highest-priority lane among its
``sources``; an entry ``t1650`` matches the lane directories ``t1650`` and
``t1650-<slug>``. A lane the list does not name ranks after it, by name, with a
warning. Works without a title are skipped and counted: the rule cannot be
applied to an empty record.

Outputs: ``--output`` (JSONL) and ``<output stem>.summary.json`` (inputs'
sha256, works written and skipped per lane, in order).

Usage:
    python scripts/corpus_icf_stage1_input.py --output DIR/screen_input.jsonl \\
        [--pool PATH] [--table PATH]
"""

import argparse
import json
import os
import sys
from collections import Counter

import _icf_screen as ics
import _rel_view as rv
import yaml
from pipeline_loaders import load_rel_review_config
from utils import get_logger

log = get_logger("corpus_icf_stage1_input")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_screen.yaml")


def lane_of(sources: str, priority: list[str]) -> str:
    """The highest-priority lane among a work's ``;``-separated sources."""
    def rank(src):
        for k, p in enumerate(priority):
            if src == p or src.startswith(p + "-"):
                return (k, src)
        return (len(priority), src)

    srcs = [s for s in sources.split(";") if s]
    if not srcs:
        return ""
    best = min(srcs, key=rank)
    k = rank(best)[0]
    return priority[k] if k < len(priority) else best


def record(p: dict) -> dict:
    """A pool work in the screener's record format."""
    return {"work_key": p["work_key"], "openalex_id": p["openalex_id"], "doi": p["doi"],
            "title": p["title"], "year": p["year"], "language": p["language"],
            "journal": p["journal"],
            "countries": [c.strip() for c in p["affiliation_countries"].split(";") if c.strip()],
            "abstract": p["abstract"]}


def select(pool: list[dict], view_rows: list[dict], priority: list[str]
           ) -> tuple[list[tuple[str, dict]], Counter, Counter]:
    """``[(lane, record)]`` in screening order, works per lane, skipped per lane."""
    unscreened = {r["work_key"] for r in view_rows if r["status"] == "unscreened"}
    order = {p: k for k, p in enumerate(priority)}
    picked, skipped = [], Counter()
    for p in pool:
        if p["work_key"] not in unscreened:
            continue
        lane = lane_of(p["sources"], priority)
        if not p["title"].strip():
            skipped[lane] += 1
            continue
        picked.append((lane, record(p)))
    unknown = sorted({lane for lane, _ in picked} - set(priority))
    if unknown:
        log.warning("lanes not in stage1.lane_priority, ranked after it by name: %s", unknown)
    picked.sort(key=lambda lr: (order.get(lr[0], len(priority)), lr[0], lr[1]["work_key"]))
    return picked, Counter(lane for lane, _ in picked), skipped


def run(pool_path: str, table_path: str, output: str, priority: list[str]) -> dict:
    ics.require_table(table_path)
    pool = rv.read_pool(pool_path)
    view, _ = rv.build_view(pool, ics.read_table(table_path), load_rel_review_config())
    picked, per_lane, skipped = select(pool, view, priority)
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    with open(output, "w", encoding="utf-8") as fh:
        for _, rec in picked:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    lanes = list(dict.fromkeys([lane for lane, _ in picked] + sorted(skipped)))
    summary = {
        "pool": os.path.basename(pool_path), "pool_sha256": rv.sha256_file(pool_path),
        "table": os.path.basename(table_path), "table_sha256": rv.sha256_file(table_path),
        "lane_priority": priority,
        "works": len(picked), "skipped_no_title": sum(skipped.values()),
        "per_lane": {lane: {"works": per_lane[lane], "skipped_no_title": skipped[lane]}
                     for lane in lanes},
    }
    with open(os.path.splitext(output)[0] + ".summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--pool", default=None, help="default: config pool")
    parser.add_argument("--table", default=None, help="default: config table")
    parser.add_argument("--output", required=True, help="stage-1 input JSONL")
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    try:
        summary = run(args.pool or cfg["pool"], args.table or cfg["table"], args.output,
                      list(cfg["stage1"]["lane_priority"]))
    except ics.IcfScreenError as exc:
        log.error("%s", exc)
        return 1
    log.info("%d unscreened works written to %s (%d skipped, no title); per lane %s",
             summary["works"], args.output, summary["skipped_no_title"], summary["per_lane"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
