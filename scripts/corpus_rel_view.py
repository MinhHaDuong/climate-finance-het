"""The REL view: pool × icf_screen labels → status per work and counts (ticket 1732),
then fuzzy membership and exclusions by reason, seriousness → ICF → discipline
(ticket 1843).

Joins the REL pool (``data/rel_pool/pool.csv``, ticket 1731) with the
append-only label table (``data/rel_screen/icf_screen.csv``), the append-only
discipline table (``data/rel_screen/rel_dimensions.csv``, tickets 1840 and
1842; absent until a version-2 run or the catch-up writes it) and the per-work
venue table (``data/rel_pool/rel_work_venues.csv``, ``make rel-venues``,
ticket 1841). Regenerable: the outputs are a function of those files,
``config/rel_review.yaml``, the stage-1 exit rule and the ``membership`` block
of ``config/rel_screen.yaml``, and the seriousness rule (switches (a, a')
``exclusion.exclude`` in ``config/rel_venue_registries.yaml``; switches (b),
(c), (d), the tier values and alpha in ``config/rel_venue_tiers.yaml``) only:
same inputs, byte-identical outputs; no timestamp is written;
``rel_counts.json`` records the sha256 of the four input files (``inputs``)
and the exit, seriousness and membership rules as values (``rule``).

Matching a label to a pool work: its ``work_key`` equals the work's
``work_key``; else its OpenAlex id is one of the work's member ids
(``all_openalex_ids``); else its DOI is one of the work's DOIs (``all_dois``).
A label that matches nothing is kept in the table and counted here as
"labelled, not in pool", split by whether the screened record had a title.

Status per work (stage 1: a work leaves only when every stage-1 verdict
exits; stage 2: the latest label wins, table order):

- ``unscreened``: no label;
- ``stage1_<label>``: stage-1 label in ``stage1_exit_labels`` (config), no
  stage-2 label: excluded at stage 1. Since the author decision of 2026-09-30
  only ``out`` exits (``stage1_out``); ``stage1_aux`` stays at zero unless the
  config restores the older rule. Design B (author decision of 2026-10-01,
  ``stage1_joint``): the two rows of one design-B run are one decision, which
  exits only when both labellers say ``out`` and the classifier's P(out)
  reaches the threshold (``_rel_view.stage1_decisions``). Several stage-1
  verdicts (Qwen rows, design-B runs, in any order): the work leaves only
  when every one exits, recall first (``_rel_view.work_status``).
  ``stage1_joint`` in the view spells out such a decision
  (``llm=…;classifier=…;p_out=…``);
- ``pending_stage2``: stage-1 label in ``stage2_labels`` (``icf``, ``unsure``,
  ``aux``), no stage-2 label yet;
- ``icf`` / ``aux`` / ``out``: the stage-2 label, final;
- ``unsure_unresolved``: stage-2 ``unsure``. Author decision of 2026-09-30
  (recall first): they stay in REL, flagged (``stage2_unsure_in_rel``).

REL membership: ``rel_included`` is ``true`` for a final ``icf`` and, under
that decision, for ``unsure_unresolved`` with ``rel_flag`` = ``unsure``; the
counts report the flagged works separately within REL.

A stage-2 label is final whatever the stage-1 label was (the 1530 Opus pilot
judged 160 works that stage 1 had excluded). ``audit`` labels never set a
status. Works whose labels disagree within a stage (several labellers or
models) are counted as conflicts; at stage 1 the unit is the decision, so the
two rows of one design-B run never count as a conflict by themselves.

Window: ``pipeline_loaders.classify_rel_review_works`` (``config/rel_review.yaml``)
on title and year; the pool carries no publication date, so a 2026 work is
quarantined as partial year and counted apart. Document type: that of the
label that sets the status; institutional documents are counted apart from
research and kept.

Counting unit (author decision of 2026-09-30): the work family. Works linked
by ``version_hint`` (a DOI, an OpenAlex id or a same-lane record id of another
version, e.g. a working paper and its article) form one family
(``_rel_view.version_families``, union-find; DOI-equal records are already one
pool work). ``family_id`` (the crisp grouping, stage 2) is its representative's
``work_key``: a ``rel_included`` member first, then a published article, then
the earliest year, then the smallest ``work_key``; ``family_first_year`` keeps
the year of first dissemination over all members. ``rel_family_id`` (the fuzzy
representative within the same family, below) is the member attaining the
maximum membership, the published article first on ties. Rows stay one per
pool work; REL counts are given in works and in families, and ``families``
counts the multi-work families whose members differ in ``rel_included`` and
the unresolved hints by cause.

Membership and reasons (``_rel_reasons``, whose docstring states the model):
REL is a fuzzy set; each work's membership ``mu`` is the minimum over the
facets seriousness → ICF → discipline, evaluated in that order (cheapest
first) and stopped at the first 0 or the first facet not graded yet. The crisp
set is the alpha-cut (``rel_final``). ``rel_reason`` is ``<facet>_excluded``
for the first facet attaining ``mu`` below alpha, ``<facet>_pending`` for the
first facet not graded, else ``included``. Counted in works and in families
(``rel_family_id``: a family's membership is the maximum over its members)
under ``reasons`` in ``rel_counts.json``; ``stage2_skip`` counts the
ICF-pending works by tier, those of seriousness 0 needing no screening. The
membership values are ``membership`` in ``config/rel_screen.yaml`` (ICF,
discipline) and the tier values and alpha of ``config/rel_venue_tiers.yaml``.
``abstract_flag`` marks a work with no abstract (blank after trimming) and
``rel_use`` splits the REL set into ``synthesis`` and ``bibliometric_only``
(author decision 2026-10-07); the flag never moves ``mu`` or the reason.

The configured v3.2 facet table loads when present (``--facets`` overrides its path): the deciding run's
native and quality-guarded memberships and input-quality provenance are exposed;
unscored historical rows have blank facets and ``icf_instrument=legacy_aggregate``.
Known nonabstract/truncated inputs use ``bibliometric_only`` with an explicit
``rel_use_reason``; the raw-empty ``abstract_flag`` rule remains unchanged.

Outputs (``--output-dir``, default ``data/rel_pool``): ``rel_view.csv`` (one row
per pool work), ``rel_counts.json``, which records the exit rule it applied
(``rule``), and ``rel_sensitivity.csv``, one row per seriousness setting (column ``scenario``:
the decided setting, then each switch flipped and the publisher and tier-A
variants), with the included works, families and mu-weighted count and the
works missing only the discipline facet (``discipline_pending_*``).

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
import _rel_facet_io as fio
import _rel_reasons as rr
import _rel_venues as rvn
import _rel_view as rv
import yaml
from pipeline_loaders import load_rel_review_config
from utils import get_logger

log = get_logger("corpus_rel_view")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_screen.yaml")
VENUE_REGISTRIES = os.path.join(ROOT, "config", "rel_venue_registries.yaml")
VENUE_TIERS = os.path.join(ROOT, "config", "rel_venue_tiers.yaml")

VIEW_COLUMNS = ["work_key", "openalex_id", "doi", "title", "year", "in_catalogue", "sources",
                "version_hint", "status", "doc_type", "studied_country",
                "stage1_label", "stage1_doc", "stage1_model", "stage1_run_id", "stage1_joint",
                "stage2_label", "stage2_doc", "stage2_model", "stage2_run_id",
                "n_audit", "n_labels", "conflict", "rel_disposition", "rel_year_status",
                "rel_included", "rel_flag", "family_id", "family_first_year", "family_size",
                *rr.VIEW_COLUMNS, *fio.VIEW_COLUMNS]
SENSITIVITY_COLUMNS = ["scenario", "exclude_registries", "tiers", "ngo_research_in_b",
                       "drop_publishers", "no_venue", "nonresearch", "included_works",
                       "included_families",
                       "included_mu_weighted", "discipline_pending_works",
                       "discipline_pending_families"]
STATUSES = ["unscreened", "stage1_out", "stage1_aux", "pending_stage2",
            "icf", "aux", "out", "unsure_unresolved"]


def make_counts(rows: list[dict], summary: dict, window_cfg: dict, inputs: dict,
                rule: dict) -> dict:
    status = Counter(r["status"] for r in rows)
    # Another exit rule may yield another stage1_<label>; never drop it from the counts.
    statuses = STATUSES + sorted(set(status) - set(STATUSES))
    by_window: dict = defaultdict(Counter)
    for r in rows:
        by_window[r["status"]][r["rel_disposition"]] += 1
    partial = str(window_cfg["partial_year"])

    def n(pred):
        return sum(1 for r in rows if pred(r))

    def window(rs):
        return [r for r in rs if r["rel_disposition"] == "include"
                and r["rel_year_status"] == "complete"]

    def families(rs):
        return len({r["family_id"] for r in rs})

    icf = [r for r in rows if r["status"] == "icf"]
    in_window = window(icf)
    included = [r for r in rows if r["rel_included"] == "true"]
    inc_research = [r for r in window(included) if r["doc_type"] == "research"]
    rel = {
        "icf_total": len(icf),
        "icf_research_in_window": sum(r["doc_type"] == "research" for r in in_window),
        "icf_research_in_window_families": families(
            [r for r in in_window if r["doc_type"] == "research"]),
        "included_works": len(included),
        "included_families": families(included),
        "included_unsure_flagged_works": sum(r["rel_flag"] == "unsure" for r in included),
        "included_research_in_window_works": len(inc_research),
        "included_research_in_window_families": families(inc_research),
        "included_research_in_window_unsure_flagged": sum(
            r["rel_flag"] == "unsure" for r in inc_research),
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
        "rule": rule,
        "window": {k: str(v) for k, v in window_cfg.items()},
        "pool_works": len(rows),
        "status": {s: status[s] for s in statuses},
        "status_by_window": {s: dict(sorted(by_window[s].items())) for s in statuses},
        "rel": rel,
        "labels": {k: v for k, v in summary.items() if k != "families"},
        "families": summary["families"],
        "stage1_joint": {"works": n(lambda r: bool(r["stage1_joint"])),
                         "stage1_out": n(lambda r: bool(r["stage1_joint"])
                                         and r["status"] == "stage1_out"),
                         "pending_stage2": n(lambda r: bool(r["stage1_joint"])
                                             and r["status"] == "pending_stage2")},
        "conflicts": {"stage1": n(lambda r: "stage1" in r["conflict"]),
                      "stage2": n(lambda r: "stage2" in r["conflict"])},
        "notes": ("status: stage 1 exits only when every stage-1 verdict exits (a "
                  "design-B pair is one verdict); stage 2: latest label wins, final. "
                  "included: final icf, plus unsure_unresolved flagged when "
                  "rule.stage2_unsure_in_rel. *_in_window: rel_disposition include, "
                  "complete year, per work. The partial year is counted apart by document "
                  "type. *_families: distinct family_id (version_hint links; representative: "
                  "an included member, then a published article) among the works counted."),
    }


def _input(path: str | None) -> dict:
    """Basename and sha256 of an input; ``sha256`` null for an absent optional one.

    For a file under a ``.dvc`` pointer (``data/rel_screen.dvc``), also the
    pointer's ``md5``: the DVC version the file was fetched at.
    """
    present = bool(path) and os.path.exists(path)
    out = {"path": os.path.basename(path or ""),
           "sha256": rv.sha256_file(path) if present else None}
    pointer = ics.dvc_pointer(path) if path else None
    if pointer:
        with open(pointer, encoding="utf-8") as fh:
            outs = (yaml.safe_load(fh) or {}).get("outs") or [{}]
        out["dvc_md5"] = outs[0].get("md5", "")
    return out


def read_dimensions(dims_path: str | None) -> list[dict]:
    """``rel_dimensions`` rows, or none when the table does not exist yet.

    The table lives in ``data/rel_screen`` with ``icf_screen``, under one DVC
    pointer: once ``icf_screen`` is present (``require_table``), an absent
    dimension table is a table no version-2 run or catch-up has started, not an
    unfetched one. Its absence is recorded (``sha256`` null) and every
    ICF-included work is then ``discipline_pending``.
    """
    if not dims_path or not os.path.exists(dims_path):
        return []
    return ics.read_table(dims_path, ics.DIMENSIONS)


def _write_csv(path: str, columns: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in columns})


def run(pool_path: str, table_path: str, out_dir: str, window_cfg: dict, rule: dict, *,
        dims_path: str | None, venues_path: str, seriousness_rule: dict,
        membership: dict, facets_path: str | None = None) -> dict:
    ics.require_table(table_path)
    labels = ics.read_table(table_path)
    dims = read_dimensions(dims_path)
    if not os.path.exists(venues_path):
        raise ics.IcfScreenError(f"{venues_path} is missing: build it with `make rel-venues`")
    venues = rvn.load_work_venues(venues_path)
    pool = rv.read_pool(pool_path)
    rows, summary = rv.build_view(pool, labels, window_cfg, rule)
    judgments = ics.read_table(facets_path, fio.SCHEMA) if facets_path and os.path.exists(facets_path) else []
    facet_summary = fio.assign_view(rows, judgments)
    try:
        dim_summary = rr.assign(rows, pool, dims, venues, seriousness_rule, membership)
    except ValueError as exc:
        raise ics.IcfScreenError(str(exc)) from exc
    inputs = {"pool": _input(pool_path), "table": _input(table_path),
              "dimensions": _input(dims_path), "venues": _input(venues_path)}
    if facets_path:
        inputs["facets"] = _input(facets_path)
    counts = make_counts(rows, summary, window_cfg, inputs,
                         dict(rule, seriousness=seriousness_rule, membership=membership))
    counts["reasons"] = dict(rr.reason_counts(rows), dimension_rows=dim_summary,
                             included_research_in_window=_in_window(rows),
                             discipline_note=rr.DISCIPLINE_NOTE,
                             seriousness_note=rr.SERIOUSNESS_NOTE)
    counts["facets"] = facet_summary
    counts["stage2_skip"] = rr.stage2_skip(rows)
    os.makedirs(out_dir, exist_ok=True)
    _write_csv(os.path.join(out_dir, "rel_view.csv"), VIEW_COLUMNS,
               sorted(rows, key=lambda r: r["work_key"]))
    _write_csv(os.path.join(out_dir, "rel_sensitivity.csv"), SENSITIVITY_COLUMNS,
               rr.sensitivity(rows, venues, seriousness_rule, membership))
    with open(os.path.join(out_dir, "rel_counts.json"), "w", encoding="utf-8") as fh:
        json.dump(counts, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return counts


def _in_window(rows: list[dict]) -> dict:
    """Included and discipline-pending research works of the window, works and families.

    A family with an included member is included (family MAX), so it never
    counts among the pending families.
    """
    def win(reason):
        return [r for r in rows if r["rel_reason"] == reason and r["doc_type"] == "research"
                and r["rel_disposition"] == "include" and r["rel_year_status"] == "complete"]
    included_fams = {r["rel_family_id"] for r in rows if r["rel_reason"] == "included"}
    out = {}
    for reason in ("included", "discipline_pending"):
        rs = win(reason)
        fams = {r["rel_family_id"] for r in rs}
        out[f"{reason}_works"] = len(rs)
        out[f"{reason}_families"] = len(fams if reason == "included" else fams - included_fams)
    out["discipline_pending_works_by_mu"] = dict(sorted(Counter(
        r["mu"] for r in win("discipline_pending")).items()))
    return out


def _yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--pool", default=None, help="default: config pool")
    parser.add_argument("--table", default=None, help="default: config table")
    parser.add_argument("--facets", default=None, help="optional actual facet judgments")
    parser.add_argument("--dimensions", default=None, help="default: config dimensions_table")
    parser.add_argument("--venues", default=None, help="default: config venues_table")
    parser.add_argument("--venue-registries", default=VENUE_REGISTRIES)
    parser.add_argument("--venue-tiers", default=VENUE_TIERS)
    # Multi-output: rel_view.csv and rel_counts.json in one directory.
    parser.add_argument("--output-dir", default=None, help="default: config view_dir")
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    srule = rr.seriousness_rule(_yaml(args.venue_registries), _yaml(args.venue_tiers))
    try:
        screen = rv.screen_rule(cfg)
        mrule = rr.membership_rule(cfg, screen, srule["alpha"])
    except (ics.IcfScreenError, ValueError) as exc:
        log.error("%s", exc)
        return 1
    try:
        counts = run(args.pool or cfg["pool"], args.table or cfg["table"],
                     args.output_dir or cfg["view_dir"], load_rel_review_config(),
                     screen, dims_path=args.dimensions or cfg["dimensions_table"],
                     venues_path=args.venues or cfg["venues_table"], seriousness_rule=srule, membership=mrule,
                     facets_path=args.facets or cfg.get("facets_table"))
    except ics.IcfScreenError as exc:
        log.error("%s", exc)
        return 1
    log.info("pool %d works; status %s", counts["pool_works"], counts["status"])
    log.info("REL: %s", counts["rel"])
    log.info("reasons (works): %s", counts["reasons"]["works"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
