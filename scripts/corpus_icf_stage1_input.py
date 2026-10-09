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
warning; a work without sources is lane ``unknown``. Works without a title are
not written unless exact native admission proves a nonempty source abstract. They are accepted
residue, not unscreened work: the summary names them (count per lane and
work keys), so a completeness check of stage 1 subtracts them by name.

``--exclude-input`` (repeatable) leaves out the works another stage-1 run
already takes: those of that run's input JSONL, matched by ``work_key``, else
OpenAlex id, else DOI (a rebuilt pool may re-key a work). Ticket 1733 uses it
for design B, which screens only what the running Qwen runs do not; the
summary counts the works left out per lane and per match.

Outputs: ``--output`` (JSONL) and ``<output stem>.summary.json`` (inputs'
sha256, works written per lane in order, the works excluded, and the residue).
``corpus_icf_import.py stage1-run`` checks a run against those hashes.

Usage:
    python scripts/corpus_icf_stage1_input.py --output DIR/screen_input.jsonl \\
        [--pool PATH] [--table PATH] [--exclude-input OTHER_RUN/screen_input.jsonl ...]
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

import _icf_screen as ics
import _rel_selection as selection
import _rel_view as rv
import yaml
from pipeline_loaders import load_rel_review_config
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("corpus_icf_stage1_input")

UNKNOWN_LANE = "unknown"
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
        return UNKNOWN_LANE
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


def select(pool: list[dict], view_rows: list[dict], priority: list[str], *, intake_root=None
           ) -> tuple[list[tuple[str, dict]], Counter, Counter]:
    """``[(lane, record)]`` in screening order, works per lane, and the
    ``{lane: [work_key]}`` of title-less works left out."""
    unscreened = {r["work_key"] for r in view_rows if r["status"] == "unscreened"}
    order = {p: k for k, p in enumerate(priority)}
    picked, skipped = [], defaultdict(list)
    for p in pool:
        if p["work_key"] not in unscreened:
            continue
        lane = lane_of(p["sources"], priority)
        from _rel_titleless_intake import pool_admission
        if not p["title"].strip():
            approved = pool_admission(p, intake_root)
            if approved and not p.get("abstract", "").strip():
                continue  # Explicit new source-absence policy, not the historical titleless residue.
            if not approved:
                skipped[lane].append(p["work_key"])
                continue
        picked.append((lane, record(p)))
    unknown = sorted({lane for lane, _ in picked} - set(priority))
    if unknown:
        log.warning("lanes not in stage1.lane_priority, ranked after it by name: %s", unknown)
    picked.sort(key=lambda lr: (order.get(lr[0], len(priority)), lr[0], lr[1]["work_key"]))
    return picked, Counter(lane for lane, _ in picked), {k: sorted(v) for k, v in skipped.items()}


def exclusion_index(paths: list[str]) -> dict[str, set[str]]:
    """``{"work_key"|"openalex_id"|"doi": ids}`` of the records of other runs' inputs."""
    index: dict[str, set[str]] = {"work_key": set(), "openalex_id": set(), "doi": set()}
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                for field, ids in index.items():
                    v = (r.get(field) or "").strip()
                    if v:
                        ids.add(v.lower() if field == "doi" else v)
    return index


def excluded_by(rec: dict, index: dict[str, set[str]]) -> str:
    """The field by which ``rec`` is in another run's input, or ``""``."""
    for field, ids in index.items():
        v = (rec.get(field) or "").strip()
        if v and (v.lower() if field == "doi" else v) in ids:
            return field
    return ""


def run(pool_path: str, table_path: str, output: str, priority: list[str],
        rule: dict, exclude_inputs: list[str] | None = None, *, intake_root=None) -> dict:
    """``rule``: ``_rel_view.screen_rule``; unscreened works do not depend on it."""
    ics.require_table(table_path)
    from _rel_titleless_intake import read_pool
    pool = read_pool(pool_path)
    view, _ = rv.build_view(pool, selection.read_effective_table(table_path), load_rel_review_config(), rule)
    picked, per_lane, skipped = select(pool, view, priority, intake_root=intake_root)
    index = exclusion_index(exclude_inputs or [])
    excluded: dict = defaultdict(Counter)
    kept = []
    for lane, rec in picked:
        how = excluded_by(rec, index)
        if how:
            excluded[lane][how] += 1
        else:
            kept.append((lane, rec))
    picked, per_lane = kept, Counter(lane for lane, _ in kept)
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    with open(output, "w", encoding="utf-8") as fh:
        for _, rec in picked:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    lanes = list(dict.fromkeys([lane for lane, _ in picked] + sorted(skipped)))
    unscreened = {r["work_key"] for r in view if r["status"] == "unscreened"}
    source_absence = sorted(p["work_key"] for p in pool if p["work_key"] in unscreened
                            and not p["title"].strip() and not p["abstract"].strip()
                            and p.get("native_titleless_provenance"))
    summary = {
        "assessment_selection": selection.binding(),
        "pool": os.path.basename(pool_path), "pool_sha256": rv.sha256_file(pool_path),
        "table": os.path.basename(table_path), "table_sha256": rv.sha256_file(table_path),
        "lane_priority": priority,
        "works": len(picked),
        "per_lane": {lane: per_lane[lane] for lane in lanes if per_lane[lane]},
        "excluded_other_runs": {
            "inputs": [{"path": p, "sha256": rv.sha256_file(p)} for p in exclude_inputs or []],
            "works": sum(sum(c.values()) for c in excluded.values()),
            "per_lane": {lane: dict(sorted(c.items())) for lane, c in excluded.items()}},
        "source_absence_policy_pending": {
            "works": len(source_absence), "work_keys": source_absence},
        "residue_no_title": {
            "note": "not screened: no title to apply the rule to; ordinary legacy residue of stage 1; newly admitted source-absence policy is separate, "
                    "not unscreened work",
            "works": sum(len(v) for v in skipped.values()),
            "per_lane": {lane: len(skipped[lane]) for lane in lanes if lane in skipped},
            "work_keys": sorted(k for v in skipped.values() for k in v)},
    }
    with open(os.path.splitext(output)[0] + ".summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return summary


def main(argv=None):
    io, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--pool", default=None, help="default: config pool")
    parser.add_argument("--table", default=None, help="default: config table")
    parser.add_argument("--titleless-intake-root", help="explicit source intake root for portable admission verification")
    parser.add_argument("--exclude-input", action="append", default=[],
                        help="another stage-1 run's input JSONL whose works are left out "
                             "(repeatable)")
    args = parser.parse_args(extra)
    args.output = io.output
    validate_io(args.output)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    try:
        summary = run(args.pool or cfg["pool"], args.table or cfg["table"], args.output,
                      list(cfg["stage1"]["lane_priority"]), rv.screen_rule(cfg),
                      args.exclude_input, intake_root=args.titleless_intake_root)
    except ics.IcfScreenError as exc:
        log.error("%s", exc)
        return 1
    log.info("%d unscreened works written to %s; per lane %s; residue without title %s; "
             "excluded as in other runs' inputs %s", summary["works"], args.output,
             summary["per_lane"], summary["residue_no_title"]["per_lane"],
             summary["excluded_other_runs"]["per_lane"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
