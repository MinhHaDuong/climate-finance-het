"""Import existing ICF labels into the append-only ``icf_screen`` table (ticket 1732).

Two sources, one subcommand each; both are idempotent (a label whose key
``(work_key, stage, model, run_id)`` is already in the table is skipped, so a
second run appends nothing) and never write into their inputs.

``t1530``: the labels of ticket 1530, from its read-only archive
(``config/rel_screen.yaml`` → ``t1530_archive``). Before writing anything, the
import checks that the archived copies agree with one another, and refuses
otherwise:

- stage 1 is ``padme-rel_sud_runs/screen2/screen.jsonl`` (30,466 lines), one
  file that grew over four runs. Lines 1-200 are the Haiku pilot
  (``local-work/screen-pilot``, identical lines), 201-12,491 the Haiku run
  (``local-work/screen-full``, identical to ``screen1/screen-haiku-first12491``),
  12,492-25,693 the Qwen run ``screen1`` (its ``screen.jsonl`` is that exact
  prefix) and 25,694-30,466 the Qwen run ``screen2``. Model and prompt hash
  come from each run's ``screen_run.json``;
- stage 2 is Opus: ``local-work/stage2/chunk*.opus.txt`` with
  ``chunk*.ids.json`` (4,752 labels), plus the 200-work Opus pilot
  (``local-work/pilot_opus.json`` in ``pilot_order.json`` order). The pilot
  judged a random 200 of the Haiku pilot, flagged or not; 40 of them were
  stage-1 ``icf``/``unsure``, which is how 1530 counted 4,792 stage-2 labels
  (4,752 + 40).

What is not knowable is written ``unknown``, never reconstructed: the Opus
model version (a Claude Code ``opus`` subagent; recorded as
``claude-code-subagent:opus``) and the pilot prompt. The stage-2 chunks carry
the hash of the wrapper in ``config/rel_sud_stage2_prompt.md``, which that
file records as used verbatim. ``labelled_at`` is the date of the runs,
2026-09-29 (the screener does not time each label). Machines: the Haiku and
Opus runs ran from the doudou session (``local-work`` is its ``/tmp`` data
directory), the Qwen runs on padme.

``stage1-run``: one finished run directory of ``corpus_rel_sud_screen.py``
(``screen.jsonl``, ``screen_runs.jsonl``, ``run.log``, and the input JSONL for
DOI and title). Refused while the run has not finished (``run.log`` has no
closing ``labelled N, unlabelled M`` line) and when its invocations disagree
on model or prompt hash. ``labelled_at`` is the first invocation's start.
``--skip-ids`` leaves out labels whose input id is not a real OpenAlex id: the
throwaway builder of the 2026-09-30 catalogue run took the first "W + digits"
inside any ``source_id``, so 7 EconBiz ids (``EDSZBW…``) and 3 SciSpace URLs came in
as false W-ids; a label keyed on one would sit forever on the wrong work.

Creating the table where ``data/rel_screen.dvc`` tracks it is refused (an
unfetched table, not a new one): ``dvc checkout`` first, or ``--new-table``.

Usage:
    python scripts/corpus_icf_import.py --output data/rel_screen/icf_screen.csv t1530 [--archive DIR]
    python scripts/corpus_icf_import.py --output TABLE stage1-run --run-dir DIR --machine padme \\
        [--input DIR/screen_input.jsonl] [--run-id NAME] [--skip-ids FILE]
"""

import argparse
import glob
import json
import os
import re
import sys

import _icf_screen as ics
import yaml
from utils import get_logger, normalize_doi, normalize_title

log = get_logger("corpus_icf_import")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_screen.yaml")

OPUS_MODEL = "claude-code-subagent:opus"
T1530_DATE = "2026-09-29"
FINISHED = re.compile(r"labelled \d+, unlabelled \d+")


class ImportRefused(Exception):
    """The inputs disagree with one another, or the run is not finished."""


def _jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def work_meta(rec: dict) -> dict:
    """Identifier columns of a screened OpenAlex record."""
    oid = rec["openalex_id"]
    title = normalize_title(rec.get("title") or "")
    year = rec.get("year")
    year = str(int(year)) if year not in (None, "") else ""
    return {"work_key": f"openalex:{oid}", "openalex_id": oid,
            "doi": normalize_doi(rec.get("doi")),
            "title_norm_year": f"{title}|{year}" if title else ""}


def _stage1_row(meta, lab, run_id, model, prompt, machine, labelled_at, source):
    return {**meta, "stage": "1", "labeller": "llm", "model": model, "prompt_sha256": prompt,
            "run_id": run_id, "machine": machine, "label": lab["label"],
            "doc_type": lab.get("doc") if lab.get("doc") in ics.DOC_TYPES else ics.UNKNOWN,
            "studied_country": "", "why": lab.get("why") or "",
            "labelled_at": labelled_at, "source": source}


# ── 1530 ─────────────────────────────────────────────────


def _require(cond, msg):
    if not cond:
        raise ImportRefused(msg)


def t1530_rows(archive: str, stage2_prompt_md: str) -> list[dict]:
    """Every 1530 label as table rows, after the archive consistency checks."""
    a = archive.rstrip("/")
    rel = "rel_sud/" + os.path.basename(a) + "/"
    runs = os.path.join(a, "padme-rel_sud_runs")
    lw = os.path.join(a, "local-work")
    final = _jsonl(os.path.join(runs, "screen2", "screen.jsonl"))
    screen1 = _jsonl(os.path.join(runs, "screen1", "screen.jsonl"))
    haiku_padme = _jsonl(os.path.join(runs, "screen1", "screen-haiku-first12491.jsonl"))
    haiku_full = _jsonl(os.path.join(lw, "screen-full", "screen.jsonl"))
    haiku_pilot = _jsonl(os.path.join(lw, "screen-pilot", "screen.jsonl"))
    n_h, n_q1 = len(haiku_full), len(screen1)
    _require(haiku_padme == haiku_full, "screen-haiku-first12491 differs from local screen-full")
    _require(haiku_full[:len(haiku_pilot)] == haiku_pilot,
             "screen-full does not start with the Haiku pilot lines")
    _require(screen1[:n_h] == haiku_full, "screen1 does not start with the Haiku lines")
    _require(final[:n_q1] == screen1, "screen2 does not start with screen1")
    ids = [r["openalex_id"] for r in final]
    _require(len(ids) == len(set(ids)), "a work is labelled twice at stage 1")

    inputs = {r["openalex_id"]: r for r in _jsonl(os.path.join(lw, "screen_input_final.jsonl"))}
    _require(set(ids) <= set(inputs), "stage-1 labels outside screen_input_final")
    run_meta = {name: _json(os.path.join(p, "screen_run.json")) for name, p in (
        ("pilot", os.path.join(lw, "screen-pilot")), ("full", os.path.join(lw, "screen-full")),
        ("q1", os.path.join(runs, "screen1")), ("q2", os.path.join(runs, "screen2")))}
    segments = [  # (first line, end line, run_id, run meta, machine, source file)
        (0, len(haiku_pilot), "t1530-haiku-pilot", "pilot", "doudou",
         "local-work/screen-pilot/screen.jsonl"),
        (len(haiku_pilot), n_h, "t1530-haiku-full", "full", "doudou",
         "local-work/screen-full/screen.jsonl"),
        (n_h, n_q1, "t1530-qwen-screen1", "q1", "padme", "padme-rel_sud_runs/screen1/screen.jsonl"),
        (n_q1, len(final), "t1530-qwen-screen2", "q2", "padme",
         "padme-rel_sud_runs/screen2/screen.jsonl"),
    ]
    rows = []
    for lo, hi, run_id, meta_key, machine, source in segments:
        m = run_meta[meta_key]
        for lab in final[lo:hi]:
            rows.append(_stage1_row(work_meta(inputs[lab["openalex_id"]]), lab, run_id,
                                    m["model"], m["prompt_sha256"], machine, T1530_DATE,
                                    rel + source))

    # Stage 2: the Opus pilot first (it came first), then the chunks.
    order = _json(os.path.join(lw, "pilot_order.json"))
    pilot = _json(os.path.join(lw, "pilot_opus.json"))
    _require([p["n"] for p in pilot] == list(range(1, len(order) + 1)),
             "pilot_opus.json is not one answer per pilot_order entry")
    _require(order == [r["openalex_id"] for r in haiku_pilot],
             "pilot_order.json is not the Haiku pilot order")
    for p in pilot:
        rows.append({**work_meta(inputs[order[p["n"] - 1]]), "stage": "2", "labeller": "llm",
                     "model": OPUS_MODEL, "prompt_sha256": ics.UNKNOWN,
                     "run_id": "t1530-opus-pilot", "machine": "doudou", "label": p["label"],
                     "doc_type": p["doc"] if p["doc"] in ics.DOC_TYPES else ics.UNKNOWN,
                     "studied_country": "", "why": p.get("why") or "",
                     "labelled_at": T1530_DATE, "source": rel + "local-work/pilot_opus.json"})
    prompt = ics.stage2_prompt_sha256(stage2_prompt_md)
    for path in sorted(glob.glob(os.path.join(lw, "stage2", "chunk*.opus.txt"))):
        chunk_ids = _json(path.replace(".opus.txt", ".ids.json"))
        with open(path, encoding="utf-8") as fh:
            answers, faults = ics.parse_stage2_answers(fh, chunk_ids)
        _require(not faults, f"{os.path.basename(path)}: {faults}")
        for oid in chunk_ids:
            ans = answers[oid]
            rows.append({**work_meta(inputs[oid]), "stage": "2", "labeller": "llm",
                         "model": OPUS_MODEL, "prompt_sha256": prompt,
                         "run_id": "t1530-opus-stage2", "machine": "doudou",
                         "label": ans["label"], "doc_type": ans["doc"],
                         "studied_country": ans["studied"], "why": ans["why"],
                         "labelled_at": T1530_DATE,
                         "source": rel + "local-work/stage2/" + os.path.basename(path)})
    return rows


# ── One finished stage-1 run ─────────────────────────────


def stage1_run_rows(run_dir: str, input_path: str, machine: str, run_id: str,
                    source: str, skip_ids: frozenset = frozenset()) -> list[dict]:
    log_path = os.path.join(run_dir, "run.log")
    text = open(log_path, encoding="utf-8").read() if os.path.exists(log_path) else ""
    _require(bool(FINISHED.search(text)),
             f"{run_dir}: run.log has no closing 'labelled N, unlabelled M' line; "
             "the run is not finished")
    invocations = _jsonl(os.path.join(run_dir, "screen_runs.jsonl"))
    _require(bool(invocations), f"{run_dir}: screen_runs.jsonl is empty")
    models = {i["model"] for i in invocations}
    prompts = {i["prompt_sha256"] for i in invocations}
    _require(len(models) == 1 and len(prompts) == 1,
             f"{run_dir}: invocations disagree on model {models} or prompt {prompts}")
    started = min(i["started"] for i in invocations)
    inputs = {r["openalex_id"]: r for r in _jsonl(input_path)}
    labels = _jsonl(os.path.join(run_dir, "screen.jsonl"))
    missing = [lab["openalex_id"] for lab in labels if lab["openalex_id"] not in inputs]
    _require(not missing, f"{len(missing)} labels outside the run input, e.g. {missing[:3]}")
    (model,), (prompt,) = models, prompts
    return [_stage1_row(work_meta(inputs[lab["openalex_id"]]), lab, run_id, model, prompt,
                        machine, started, source) for lab in labels
            if lab["openalex_id"] not in skip_ids]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    # --output is the append-only icf_screen table the labels are appended to.
    parser.add_argument("--output", required=True)
    parser.add_argument("--new-table", action="store_true",
                        help="allow creating --output although a .dvc pointer tracks it")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("t1530")
    p1.add_argument("--archive", default=None, help="default: config t1530_archive")
    p1.add_argument("--stage2-prompt", default=None, help="default: config stage2.prompt")
    p2 = sub.add_parser("stage1-run")
    p2.add_argument("--run-dir", required=True)
    p2.add_argument("--machine", required=True)
    p2.add_argument("--input", default=None, help="default: RUN_DIR/screen_input.jsonl")
    p2.add_argument("--run-id", default=None, help="default: the run directory name")
    p2.add_argument("--skip-ids", default=None,
                    help="file of input ids (one per line) whose labels are not imported, "
                         "e.g. ids that are not real OpenAlex ids")
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    table = args.output
    try:
        if args.cmd == "t1530":
            archive = os.path.expanduser(args.archive or cfg["t1530_archive"])
            rows = t1530_rows(archive, args.stage2_prompt or cfg["stage2"]["prompt"])
            note = f"import t1530 from {archive}"
        else:
            run_dir = args.run_dir.rstrip("/")
            run_id = args.run_id or os.path.basename(run_dir)
            skip = frozenset()
            if args.skip_ids:
                with open(args.skip_ids, encoding="utf-8") as fh:
                    skip = frozenset(line.strip() for line in fh if line.strip())
            rows = stage1_run_rows(run_dir, args.input or os.path.join(run_dir, "screen_input.jsonl"),
                                   args.machine, run_id, f"{run_id}/screen.jsonl", skip)
            log.info("skipped %d ids listed in --skip-ids", len(skip))
            note = f"import stage-1 run {run_id}"
        added, skipped = ics.append_new(table, rows, note, args.new_table)
    except (ImportRefused, ics.IcfScreenError) as exc:
        log.error("%s", exc)
        return 1
    log.info("%d labels read, %d appended, %d already in %s", len(rows), added, skipped, table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
