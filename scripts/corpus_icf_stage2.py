"""Stage-2 and audit tables of the ICF screen, and their answers (ticket 1732).

Dispatcher over the REL view (``corpus_rel_view.build_view``, computed in
memory from the pool and the ``icf_screen`` table, so it is never stale):

``build``
    Works whose status is ``pending_stage2`` (stage-1 label in
    ``stage2_labels`` of ``config/rel_screen.yaml``: ``icf``/``unsure``/``aux``
    since 2026-09-30; no stage-2 label), sorted by ``work_key``, in numbered chunks of the 1530
    stage-2 format: ``chunkNN.txt`` (``n. [lang | year | journal |
    affiliations: CC, CC]``, ``Title:`` ≤ 220, ``Abstract:`` ≤ 650 characters),
    ``chunkNN.ids.json`` (the chunk's work keys, in order) and ``works.csv``
    (identifiers of every work, for the parser). The labeller gets the wrapper
    of ``stage2.prompt`` (``config/rel_stage2_prompt_v2.md`` since ticket 1840);
    the chunk never shows stage-1 labels.

``audit-sample``
    A random sample of works with a final stage-2 label, stratified by that
    label (``config/rel_screen.yaml`` → ``audit``: seed and size per label),
    shuffled, in the same chunk format, for the second-model audit.

``parse``
    Reads ``chunkNN.<suffix>.txt`` answers next to each ``chunkNN.ids.json``, in
    the format the wrapper declares (``--prompt``, default ``stage2.prompt``:
    ``n|label|doc|studied|why`` for version 1, ``n|label|doc|studied|contrib|
    field|ctype|why`` for version 2), and appends the labels to ``icf_screen``
    as stage ``2`` or ``audit``, with the model, run id and machine given on the
    command line. Version-2 answers also append the discipline fields to
    ``rel_dimensions`` (``dimensions_table``), same key, same prompt hash
    (ticket 1840); both batches are validated before either is written.
    A chunk with a malformed or duplicated answer line is refused whole (the
    numbering can no longer be trusted), and so is an answer file written for
    the other wrapper (``_format_mismatch``); unanswered records are reported and
    stay pending. The per-chunk report also counts, for version 2, answers with
    an ``unknown`` discipline value (``unknown_dimension``) and answers that break
    the wrapper's rule of ``na`` exactly for ``out`` (``na_off_rule``); both are
    stored as answered. Idempotent: labels already in the table are skipped.

``agreement``
    Cohen's kappa and the confusion matrix of the audit labels of one run
    against the stage-2 labels of the same pool works. The sample is
    stratified, so kappa describes the sample, not the population.

Usage:
    python scripts/corpus_icf_stage2.py build --output-dir DIR
    python scripts/corpus_icf_stage2.py audit-sample --output-dir DIR
    python scripts/corpus_icf_stage2.py parse --chunk-dir DIR --model M --run-id R \\
        --machine doudou [--stage 2|audit] [--suffix opus] [--labeller llm] [--prompt MD]
    python scripts/corpus_icf_stage2.py agreement --audit-run-id R --output FILE
"""

import argparse
import csv
import glob
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

import _icf_screen as ics
import _rel_view as rv
import yaml
from pipeline_loaders import load_rel_review_config
from utils import get_logger, normalize_title

log = get_logger("corpus_icf_stage2")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_screen.yaml")
WORKS_COLUMNS = ["work_key", "openalex_id", "doi", "title_norm_year", "chunk", "n"]
FINAL_STAGE2 = {"icf": "icf", "aux": "aux", "out": "out", "unsure_unresolved": "unsure"}
LABEL_ORDER = ["icf", "aux", "out", "unsure"]


class Stage2Error(Exception):
    """A refused build or parse."""


def _view(pool_path, table_path, rule):
    pool = rv.read_pool(pool_path)
    rows, _ = rv.build_view(pool, ics.read_table(table_path), load_rel_review_config(), rule)
    return pool, rows


def _record(p: dict) -> dict:
    return {"language": p["language"], "year": p["year"], "journal": p["journal"],
            "countries": [c for c in p["affiliation_countries"].split(";") if c],
            "title": p["title"], "abstract": p["abstract"]}


def write_chunks(out_dir: str, works: list[dict], s2cfg: dict, manifest: dict) -> list[str]:
    """Chunk files, ids and works.csv for ``works`` (pool rows, in order)."""
    if os.path.isdir(out_dir) and glob.glob(os.path.join(out_dir, "chunk*")):
        raise Stage2Error(f"{out_dir} already holds chunk files; choose a new directory")
    os.makedirs(out_dir, exist_ok=True)
    size = s2cfg["chunk_size"]
    names, table = [], []
    for c in range(0, len(works), size):
        chunk = works[c:c + size]
        name = f"chunk{c // size + 1:02d}"
        with open(os.path.join(out_dir, f"{name}.txt"), "w", encoding="utf-8") as fh:
            for n, p in enumerate(chunk, 1):
                fh.write(ics.format_stage2_record(n, _record(p), s2cfg["title_max_chars"],
                                                  s2cfg["abstract_max_chars"]))
        with open(os.path.join(out_dir, f"{name}.ids.json"), "w", encoding="utf-8") as fh:
            json.dump([p["work_key"] for p in chunk], fh)
        for n, p in enumerate(chunk, 1):
            title = normalize_title(p["title"])
            table.append({"work_key": p["work_key"], "openalex_id": p["openalex_id"],
                          "doi": p["doi"], "title_norm_year": f"{title}|{p['year']}" if title else "",
                          "chunk": name, "n": n})
        names.append(name)
    with open(os.path.join(out_dir, "works.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=WORKS_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(table)
    with open(os.path.join(out_dir, "build.json"), "w", encoding="utf-8") as fh:
        json.dump({**manifest, "works": len(works), "chunks": names}, fh, indent=2,
                  ensure_ascii=False)
        fh.write("\n")
    return names


def select_pending(view_rows: list[dict]) -> list[str]:
    return sorted(r["work_key"] for r in view_rows if r["status"] == "pending_stage2")


def audit_sample(view_rows: list[dict], per_label: dict, seed: int) -> list[str]:
    """Work keys stratified by final stage-2 label, shuffled; reproducible from seed."""
    strata = defaultdict(list)
    for r in view_rows:
        if r["status"] in FINAL_STAGE2:
            strata[FINAL_STAGE2[r["status"]]].append(r["work_key"])
    rng = random.Random(seed)
    sample = []
    for label in LABEL_ORDER:
        keys = sorted(strata[label])
        sample += rng.sample(keys, min(int(per_label.get(label, 0)), len(keys)))
    rng.shuffle(sample)
    return sample


# ── parse ────────────────────────────────────────────────


_CHUNK = re.compile(r"^(chunk\d+)\.ids\.json$")


def _dims_table_is_new(table: str, dims_table: str, new_table: bool, prompt_sha: str) -> bool:
    """Whether a missing dimensions table may be started, checked before any write.

    It lives beside ``icf_screen`` under the same DVC pointer, so the first
    version-2 parse must create it without ``--new-table`` (which would also
    let ``icf_screen`` restart). It is missing for a wrong reason when
    ``icf_screen`` already holds rows of this wrapper: those parses wrote it,
    so it was lost or not fetched, and a new one would fork its history.
    """
    if new_table or os.path.exists(dims_table):
        return new_table
    if not os.path.exists(table):
        return False  # the icf_screen append decides, through _refuse_fork
    if any(r["prompt_sha256"] == prompt_sha for r in ics.read_table(table)):
        raise Stage2Error(f"{dims_table} is missing but {table} already holds rows of this "
                          "wrapper: fetch it (make rel-pool-data) before parsing; nothing written")
    return True


_DIM_HEAD = re.compile(r"^(yes|no|unsure|na)\|", re.IGNORECASE)


def _format_mismatch(answers: dict, fields: tuple) -> str:
    """Why an answer file looks written for the other wrapper, or "".

    Both tables are append-only, so an answer file parsed under the wrong
    ``--prompt`` cannot be corrected once written. A version-1 file read as
    version 2 leaves every discipline field ``unknown``; a version-2 file read
    as version 1 leaves every ``why`` starting with a discipline value. Either
    pattern over a whole chunk refuses it. One stray line stays an ``unknown``.
    """
    if not answers:
        return ""
    if fields == ics.V2_FIELDS:
        if all(a["contrib"] == a["field"] == a["ctype"] == ics.UNKNOWN for a in answers.values()):
            return ("no record has a valid discipline field: a version-1 answer file, "
                    "or every discipline value out of vocabulary?")
    elif all(_DIM_HEAD.match(a["why"]) for a in answers.values()):
        return "every why starts with a discipline value: a version-2 answer file?"
    return ""


def parse_answers(chunk_dir: str, suffix: str, stage: str, model: str, run_id: str,
                  machine: str, labeller: str, prompt_sha: str, labelled_at: str,
                  source_prefix: str, fields: tuple = ics.V1_FIELDS
                  ) -> tuple[list[dict], list[dict], dict]:
    """``icf_screen`` rows, ``rel_dimensions`` rows (version-2 answers only) for
    every answered record, and a per-chunk report."""
    with open(os.path.join(chunk_dir, "works.csv"), encoding="utf-8", newline="") as fh:
        works = {r["work_key"]: r for r in csv.DictReader(fh)}
    rows, dims, report = [], [], {}
    for name in sorted(os.listdir(chunk_dir)):
        m = _CHUNK.match(name)
        if not m:
            continue
        chunk = m.group(1)
        with open(os.path.join(chunk_dir, name), encoding="utf-8") as fh:
            ids = json.load(fh)
        answer = os.path.join(chunk_dir, f"{chunk}.{suffix}.txt")
        if not os.path.exists(answer):
            report[chunk] = {"ids": len(ids), "answered": 0, "status": "no answer file"}
            continue
        with open(answer, encoding="utf-8") as fh:
            answers, faults = ics.parse_stage2_answers(fh, ids, fields)
        hard = [f for f in faults if "unanswered" not in f]
        if hard:
            raise Stage2Error(f"{answer}: refused, {hard[:5]}")
        mismatch = _format_mismatch(answers, fields)
        if mismatch:
            raise Stage2Error(f"{answer}: refused, {mismatch}")
        report[chunk] = {"ids": len(ids), "answered": len(answers),
                         "status": "complete" if len(answers) == len(ids) else "incomplete"}
        if fields == ics.V2_FIELDS:
            report[chunk]["unknown_dimension"] = sum(
                ics.UNKNOWN in (a["contrib"], a["field"], a["ctype"]) for a in answers.values())
            # The wrapper asks na exactly for out; stored as answered, counted here.
            report[chunk]["na_off_rule"] = sum(
                (a["label"] == "out") != (a["contrib"] == "na") for a in answers.values())
        for key in ids:
            if key not in answers:
                continue
            a, w = answers[key], works[key]
            rows.append({"work_key": key, "openalex_id": w["openalex_id"], "doi": w["doi"],
                         "title_norm_year": w["title_norm_year"], "stage": stage,
                         "labeller": labeller, "model": model, "prompt_sha256": prompt_sha,
                         "run_id": run_id, "machine": machine, "label": a["label"],
                         "doc_type": a["doc"], "studied_country": a["studied"], "why": a["why"],
                         "labelled_at": labelled_at,
                         "source": f"{source_prefix}/{chunk}.{suffix}.txt"})
            if fields == ics.V2_FIELDS:
                dims.append({**{k: rows[-1][k] for k in ics.KEY + (
                    "labeller", "prompt_sha256", "machine", "labelled_at", "source")},
                    "contrib": a["contrib"], "field": a["field"], "contrib_type": a["ctype"]})
    return rows, dims, report


# ── agreement ────────────────────────────────────────────


def cohen_kappa(pairs: list[tuple[str, str]]) -> dict:
    """Observed agreement, Cohen's kappa and the confusion matrix of label pairs."""
    n = len(pairs)
    cats = [c for c in LABEL_ORDER if any(c in p for p in pairs)]
    matrix = {a: {b: sum(1 for x, y in pairs if x == a and y == b) for b in cats} for a in cats}
    if not n:
        return {"n": 0, "observed_agreement": None, "kappa": None, "confusion": matrix}
    po = sum(matrix[c][c] for c in cats) / n
    rows = Counter(x for x, _ in pairs)
    cols = Counter(y for _, y in pairs)
    pe = sum(rows[c] * cols[c] for c in cats) / (n * n)
    kappa = None if pe == 1 else (po - pe) / (1 - pe)
    return {"n": n, "observed_agreement": round(po, 4),
            "kappa": None if kappa is None else round(kappa, 4), "confusion": matrix}


def agreement(pool: list[dict], labels: list[dict], audit_run_id: str) -> dict:
    matched, _, _ = rv.match_labels(pool, labels)
    pairs, by_stratum = [], defaultdict(list)
    for labs in matched.values():
        s2 = [lab for lab in labs if lab["stage"] == "2"]
        au = [lab for lab in labs if lab["stage"] == "audit" and lab["run_id"] == audit_run_id]
        if s2 and au:
            pair = (s2[-1]["label"], au[-1]["label"])
            pairs.append(pair)
            by_stratum[pair[0]].append(pair)
    return {"audit_run_id": audit_run_id, "rows": "stage 2", "columns": "audit",
            **cohen_kappa(pairs),
            "by_stage2_label": {k: {"n": len(v), "agree": sum(a == b for a, b in v)}
                                for k, v in sorted(by_stratum.items())},
            "note": "stratified sample: kappa describes the sample, not the pool"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--pool", default=None, help="default: config pool")
    parser.add_argument("--table", default=None, help="default: config table")
    parser.add_argument("--dimensions-table", default=None,
                        help="default: config dimensions_table")
    sub = parser.add_subparsers(dest="cmd", required=True)
    # Multi-output: chunk files, ids, works.csv and build.json in one directory.
    for name in ("build", "audit-sample"):
        sub.add_parser(name).add_argument("--output-dir", required=True)
    pp = sub.add_parser("parse")
    pp.add_argument("--chunk-dir", required=True)
    pp.add_argument("--model", required=True)
    pp.add_argument("--run-id", required=True)
    pp.add_argument("--machine", required=True)
    pp.add_argument("--stage", choices=["2", "audit"], default="2")
    pp.add_argument("--suffix", default="opus", help="answer files chunkNN.<suffix>.txt")
    pp.add_argument("--labeller", choices=sorted(ics.LABELLERS), default="llm")
    pp.add_argument("--labelled-at", default=None, help="default: today (UTC)")
    pp.add_argument("--prompt", default=None,
                    help="wrapper the answers were given under (default: config stage2.prompt)")
    pp.add_argument("--new-table", action="store_true",
                    help="allow creating the table although a .dvc pointer tracks it")
    pa = sub.add_parser("agreement")
    pa.add_argument("--audit-run-id", required=True)
    pa.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    pool_path, table = args.pool or cfg["pool"], args.table or cfg["table"]
    try:
        if args.cmd != "parse":
            ics.require_table(table)
        if args.cmd in ("build", "audit-sample"):
            rule = rv.screen_rule(cfg)
            pool, view = _view(pool_path, table, rule)
            if args.cmd == "build":
                keys = select_pending(view)
            else:
                keys = audit_sample(view, cfg["audit"]["per_label"], cfg["audit"]["seed"])
            by_key = {p["work_key"]: p for p in pool}
            manifest = {"kind": args.cmd, "pool": os.path.basename(pool_path),
                        "pool_sha256": rv.sha256_file(pool_path),
                        "table_sha256": rv.sha256_file(table),
                        "prompt": cfg["stage2"]["prompt"],
                        "prompt_sha256": ics.stage2_prompt_sha256(cfg["stage2"]["prompt"]),
                        "rule": rule}
            if args.cmd == "audit-sample":
                manifest["audit"] = cfg["audit"]
            names = write_chunks(args.output_dir, [by_key[k] for k in keys], cfg["stage2"],
                                 manifest)
            log.info("%s: %d works in %d chunks under %s", args.cmd, len(keys), len(names),
                     args.output_dir)
        elif args.cmd == "parse":
            labelled_at = args.labelled_at or datetime.now(timezone.utc).date().isoformat()
            prompt = args.prompt or cfg["stage2"]["prompt"]
            rows, dims, report = parse_answers(
                args.chunk_dir, args.suffix, args.stage, args.model, args.run_id, args.machine,
                args.labeller, ics.stage2_prompt_sha256(prompt), labelled_at,
                os.path.basename(os.path.normpath(args.chunk_dir)),
                ics.stage2_answer_fields(prompt))
            dims_table = args.dimensions_table or cfg["dimensions_table"]
            note = f"parse {args.stage} {args.run_id}"
            bad = [e for r in dims for e in ics.validate_row(r, ics.DIMENSIONS)]
            if bad:
                raise Stage2Error(f"dimension rows refused, nothing written: {bad[:5]}")
            dims_new = _dims_table_is_new(table, dims_table, args.new_table,
                                          rows[0]["prompt_sha256"]) if dims else False
            added, skipped = ics.append_new(table, rows, note, args.new_table)
            log.info("chunks %s", report)
            log.info("%d answers, %d appended, %d already in %s", len(rows), added, skipped, table)
            if dims:
                d_added, d_skipped = ics.append_new(dims_table, dims, note, dims_new,
                                                    ics.DIMENSIONS)
                log.info("%d dimension rows appended, %d already in %s", d_added, d_skipped,
                         dims_table)
        else:
            res = agreement(rv.read_pool(pool_path), ics.read_table(table), args.audit_run_id)
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(res, fh, indent=2)
                fh.write("\n")
            log.info("agreement n=%d kappa=%s", res["n"], res["kappa"])
    except (Stage2Error, ics.IcfScreenError) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
