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
A run is keyed by ``openalex_id`` (1530 input, the catalogue run) or by
``work_key`` (``--id-field work_key``, the pool input of
``corpus_icf_stage1_input.py``, ticket 1733). The key is read from the run
header (``id_field``), or from the label lines of runs older than that field;
every label line must carry exactly that key, else the run is refused. A
``work_key`` label keeps the pool's key and the record's OpenAlex id, if any.
A ``work_key`` run is imported only against the pool its input was built on
and a table that has only grown since (``check_input_basis``, from the
input's ``.summary.json``); ``--allow-input-drift`` overrides.
``--skip-ids`` leaves out labels whose input id is not a real OpenAlex id: the
throwaway builder of the 2026-09-30 catalogue run took the first "W + digits"
inside any ``source_id``, so 7 EconBiz ids (``EDSZBW…``) and 3 SciSpace URLs came in
as false W-ids; a label keyed on one would sit forever on the wrong work.

``stage1-designb``: one run directory of ``corpus_icf_stage1_designb.py``
(design B, author decision of 2026-10-01): two stage-1 rows per work, the
LLM's and the classifier's (``designb_rows``), for the works both labelled;
served models must be listed in ``config/rel_screen.yaml`` → ``stage1_joint``.
A run counts as finished on the closing line of ``run.log`` or on the
``finished`` time its ``summary.json`` records with no ``stopped`` reason.

Stage 2 of ticket 1733 (imported by ticket 1995; ``corpus_icf_stage2.py
parse`` reads chunk answer files, these runs wrote other formats):

``stage2-sol``: runs that wrote one JSON label per line (``labels.jsonl``,
with ``manifest.json`` and ``prompt_template.txt``), merged in ``labelled_at``
order so the view's latest stage-2 row is the most recent label (``sol_rows``).
``stage2-relabel``: a relabelling of stage-2 ``unsure`` works
(``relabel_rows``). ``stage2-agree-rule``: the author's rule over a check of
the relabelled ``icf`` (``agree_rule_rows``). ``rows``: rows already written by
``append_new`` to a side table (the 72 front-matter exclusions). Every key is
a pool ``work_key``, compared byte-exact (some carry ``&lt;``: never unescaped).

Creating the table where ``data/rel_screen.dvc`` tracks it is refused (an
unfetched table, not a new one): ``dvc checkout`` first, or ``--new-table``.

Usage:
    python scripts/corpus_icf_import.py --output data/rel_screen/icf_screen.csv t1530 [--archive DIR]
    python scripts/corpus_icf_import.py --output TABLE stage1-run --run-dir DIR --machine padme \\
        [--input DIR/screen_input.jsonl] [--run-id NAME] [--skip-ids FILE]
    python scripts/corpus_icf_import.py --output TABLE stage1-designb --run-dir DIR \\
        [--input DIR/screen_input.jsonl] [--run-id NAME]
    python scripts/corpus_icf_import.py --output TABLE stage2-sol --run-dir A --run-dir B [--pool P]
    python scripts/corpus_icf_import.py --output TABLE stage2-relabel --run-dir DIR --run-id R \\
        --prompt-template FILE --labelled-at TS [--machine M] [--pool P]
    python scripts/corpus_icf_import.py --output TABLE stage2-agree-rule --checks JSON \\
        --check-model M --relabel-run-id R --run-id R2 --labelled-at TS
    python scripts/corpus_icf_import.py --output TABLE rows --rows-file CSV [--pool P]
"""

import argparse
import glob
import hashlib
import json
import os
import re
import sys

import _icf_screen as ics
import _rel_selection as selection
import _rel_view as rv
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


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def work_meta(rec: dict, id_field: str = "openalex_id") -> dict:
    """Identifier columns of a screened record (OpenAlex record or pool work)."""
    oid = rec.get("openalex_id") or ""
    title = normalize_title(rec.get("title") or "")
    year = rec.get("year")
    year = str(int(float(year))) if year not in (None, "") else ""
    key = rec["work_key"] if id_field == "work_key" else f"openalex:{oid}"
    return {"work_key": key, "openalex_id": oid,
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


def check_input_basis(input_path: str, pool_path: str, table_path: str) -> None:
    """Refuse a work_key run whose input was built on another pool or table.

    ``corpus_icf_stage1_input.py`` records the sha256 of the pool and of the
    table it read (``<input stem>.summary.json``). The pool must be the same
    file: a rebuilt pool can re-key works (a new DOI turns a ``title:`` work
    into a ``doi:`` one), and the labels would then match nothing. The table
    may only have grown since: its recorded hash must be one the manifest
    logged after an append, since appends are the only allowed change.
    """
    summary_path = os.path.splitext(input_path)[0] + ".summary.json"
    _require(os.path.exists(summary_path),
             f"{summary_path} is missing: the pool and table the input was built on are unknown")
    summary = _json(summary_path)
    selection.require_binding(summary.get("assessment_selection"), allow_append=True)
    _require(os.path.exists(pool_path) and _sha256(pool_path) == summary["pool_sha256"],
             f"{pool_path} is not the pool the run input was built on "
             f"(sha256 {summary['pool_sha256'][:12]}…): rebuild that pool first")
    grown_from = {e["sha256"] for e in ics._manifest_entries(table_path)} if os.path.exists(
        ics.manifest_path(table_path)) else set()
    _require(summary["table_sha256"] in grown_from,
             f"{table_path} did not grow from the table the run input was built on "
             f"(sha256 {summary['table_sha256'][:12]}…)")


def stage1_run_rows(run_dir: str, input_path: str, machine: str, run_id: str,
                    source: str, skip_ids: frozenset = frozenset(),
                    basis: tuple[str, str] | None = None,
                    stopped: str = "") -> list[dict]:
    """Table rows of a finished run; ``basis`` = (pool, table) checks a work_key
    run's input against them (``check_input_basis``), None skips that check.

    ``stopped``: the reason a run was stopped on purpose before its end (its
    log then has no closing line). Its labels are imported as they stand; the
    unlabelled rest of its input stays unscreened. Without it, a run with no
    closing line is refused as still running.
    """
    log_path = os.path.join(run_dir, "run.log")
    text = open(log_path, encoding="utf-8").read() if os.path.exists(log_path) else ""
    _require(bool(FINISHED.search(text)) or bool(stopped.strip()),
             f"{run_dir}: run.log has no closing 'labelled N, unlabelled M' line; "
             "the run is not finished (pass --stopped REASON for a run stopped on purpose)")
    invocations = _jsonl(os.path.join(run_dir, "screen_runs.jsonl"))
    _require(bool(invocations), f"{run_dir}: screen_runs.jsonl is empty")
    models = {i["model"] for i in invocations}
    prompts = {i["prompt_sha256"] for i in invocations}
    _require(len(models) == 1 and len(prompts) == 1,
             f"{run_dir}: invocations disagree on model {models} or prompt {prompts}")
    started = min(i["started"] for i in invocations)
    labels = _jsonl(os.path.join(run_dir, "screen.jsonl"))
    field = run_id_field(invocations, labels, run_dir)
    if field == "work_key" and basis:
        check_input_basis(input_path, *basis)
    records = _jsonl(input_path)
    bad = [n for n, r in enumerate(records, 1) if not isinstance(r, dict) or not r.get(field)]
    _require(not bad, f"{input_path}: {len(bad)} input records lack {field!r}, e.g. line {bad[:1]}")
    inputs = {r[field]: r for r in records}
    missing = [lab[field] for lab in labels if lab[field] not in inputs]
    _require(not missing, f"{len(missing)} labels outside the run input, e.g. {missing[:3]}")
    (model,), (prompt,) = models, prompts
    return [_stage1_row(work_meta(inputs[lab[field]], field), lab, run_id, model, prompt,
                        machine, started, source) for lab in labels
            if lab[field] not in skip_ids]


def designb_finished(run_dir: str) -> bool:
    """Whether a design-B run ended on its own: the closing line in ``run.log``,
    or ``summary.json`` with a ``finished`` time and no ``stopped`` reason.

    The runner logs its closing line to stdout; ``run.log`` holds it only when
    the launcher piped stdout there (the resumes of 2026-10-06 wrote
    ``stdout-*.log`` instead). ``summary.json`` is the runner's own record,
    rewritten at the end of every invocation, so it covers both.
    """
    log_path = os.path.join(run_dir, "run.log")
    text = open(log_path, encoding="utf-8").read() if os.path.exists(log_path) else ""
    if FINISHED.search(text):
        return True
    summary_path = os.path.join(run_dir, "summary.json")
    if not os.path.exists(summary_path):
        return False
    summary = _json(summary_path)
    return bool(summary.get("finished")) and not (summary.get("stopped") or "").strip()


def designb_rows(run_dir: str, input_path: str, run_id: str, joint: dict,
                 basis: tuple[str, str] | None = None,
                 stopped: str = "") -> tuple[list[dict], int]:
    """Table rows of a design-B run (``corpus_icf_stage1_designb.py``) and the
    number of works left out because only one labeller labelled them.

    Two stage-1 rows per work, one per labeller, both ``labeller=llm`` and
    ``run_id``: the LLM row (its label, doc, ``why``) and the classifier row,
    whose ``why`` is ``p_out=<P(out)>`` at full precision (``repr``: a value
    just under the threshold is never rounded up onto it), which the view's
    drop rule reads (``_rel_view.p_out_of``). ``model`` is the served model id, ``machine`` is
    ``openrouter/<provider>``. Only works labelled by both are imported, so the
    table never holds half a decision; the others stay unscreened for a rerun.
    Refused when the run has no closing line, when its invocations disagree on
    prompt hashes, when a served model is not in ``stage1_joint`` (so every
    imported row is one the view recognises), or, with ``basis``, when the
    input was built on another pool or table (``check_input_basis``).
    """
    _require(designb_finished(run_dir) or bool(stopped.strip()),
             f"{run_dir}: run.log has no closing 'labelled N, unlabelled M' line and "
             "summary.json records no finish (pass --stopped REASON for a run stopped on purpose)")
    invocations = _jsonl(os.path.join(run_dir, "screen_runs.jsonl"))
    _require(bool(invocations), f"{run_dir}: screen_runs.jsonl is empty")
    hashes = {(i["llm_prompt_sha256"], i["classifier_prompt_sha256"]) for i in invocations}
    _require(len(hashes) == 1 and {i.get("id_field") for i in invocations} == {"work_key"},
             f"{run_dir}: invocations disagree on prompt hashes {hashes} or are not work_key runs")
    (llm_sha, clf_sha), = hashes
    started = min(i["started"] for i in invocations)
    if basis:
        check_input_basis(input_path, *basis)
    inputs = {r["work_key"]: r for r in _jsonl(input_path)}
    llm = {x["work_key"]: x for x in _jsonl(os.path.join(run_dir, "llm.jsonl"))}
    clf = {x["work_key"]: x for x in _jsonl(os.path.join(run_dir, "classifier.jsonl"))}
    for name, labs, allowed in (("llm", llm, joint["llm_models"]),
                                ("classifier", clf, joint["classifier_models"])):
        bad = sorted({x["model"] for x in labs.values()} - set(allowed))
        _require(not bad, f"{run_dir}: {name} rows served by {bad}, not in stage1_joint")
        outside = [k for k in labs if k not in inputs]
        _require(not outside, f"{len(outside)} {name} labels outside the run input, "
                              f"e.g. {outside[:3]}")
    rows = []
    for key in (k for k in inputs if k in llm and k in clf):  # input order
        meta = work_meta(inputs[key], "work_key")
        for lab, sha, why, src in ((llm[key], llm_sha, llm[key].get("why") or "", "llm.jsonl"),
                                   (clf[key], clf_sha, f"p_out={float(clf[key]['p_out'])!r}",
                                    "classifier.jsonl")):
            rows.append(_stage1_row(meta, {**lab, "why": why}, run_id, lab["model"], sha,
                                    f"openrouter/{lab.get('provider') or 'unknown'}",
                                    started, f"{run_id}/{src}"))
    return rows, len(set(llm) ^ set(clf))


# ── Stage 2 of ticket 1733 (2026-10-06/07) ───────────────

ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_ANSWER = re.compile(r"^(\d+)\|")
AGREE_RULE = ("Author decision 2026-10-07 (ticket 1733): a work the relabelling run labelled icf "
              "stays icf only when the check model also labels it icf; otherwise it is unsure, "
              "kept in REL and flagged.")
RULE_MODEL = "rule:fable-opus-agree"


def pool_by_key(pool_path: str) -> dict:
    """Pool rows by ``work_key`` (byte-exact)."""
    return {p["work_key"]: p for p in rv.read_pool(pool_path)}


def _pool_meta(key: str, pool: dict, where: str) -> dict:
    """Identifier columns of a pool work; refused when ``key`` is not a pool key.

    Keys compare byte-exact. Some pool keys carry HTML entities (``&lt;`` in
    SICI DOIs, as the lane delivered them); a label keyed on the unescaped form
    names no pool work, and the reverse, so neither side is ever unescaped.
    """
    rec = pool.get(key)
    _require(rec is not None, f"{where}: {key!r} is not a pool work_key")
    return work_meta(rec, "work_key")


def sol_rows(run_dirs: list[str], pool: dict) -> tuple[list[dict], dict]:
    """Stage-2 rows of the ``labels.jsonl`` runs (one JSON label per line), all
    runs merged in ``labelled_at`` order, and a report.

    Each run directory holds ``labels.jsonl``, ``manifest.json`` (run id,
    model, tier, prompt hash) and ``prompt_template.txt``, whose sha256 must be
    the manifest's. Every line must carry the manifest's run id, model and
    prompt hash, a label of the vocabulary, a UTC ``labelled_at`` and a pool
    ``work_key``. The table key is ``(work_key, stage, model, run_id)``, so a
    work labelled twice within one run (a resumed chunk) keeps its latest label
    (``labelled_at``, then line order); the earlier ones are counted in
    ``superseded_in_run`` and stay in the run's file. Rows of all runs come out
    sorted by ``labelled_at`` (ties: run order, then line order): the REL view
    takes the last stage-2 row of a work, so a work labelled by two runs gets
    its most recent label.
    """
    stamped, report = [], {"lines": {}, "superseded_in_run": {}}
    for r_idx, run_dir in enumerate(run_dirs):
        run_dir = run_dir.rstrip("/")
        name = os.path.basename(run_dir)
        manifest = _json(os.path.join(run_dir, "manifest.json"))
        expected = {k: manifest[k] for k in ("run_id", "model", "prompt_sha256")}
        _require(_sha256(os.path.join(run_dir, "prompt_template.txt")) == expected["prompt_sha256"],
                 f"{run_dir}: prompt_template.txt does not hash to the manifest prompt_sha256")
        latest: dict = {}
        lines = _jsonl(os.path.join(run_dir, "labels.jsonl"))
        for n, lab in enumerate(lines, 1):
            where = f"{name}/labels.jsonl line {n}"
            got = {k: lab.get(k) for k in expected}
            _require(got == expected, f"{where}: {got} disagree with manifest {expected}")
            _require(lab.get("label") in ics.LABELS, f"{where}: label {lab.get('label')!r}")
            _require(bool(ISO_UTC.match(lab.get("labelled_at") or "")),
                     f"{where}: labelled_at {lab.get('labelled_at')!r} is not YYYY-MM-DDTHH:MM:SSZ")
            meta = _pool_meta(lab["work_key"], pool, where)
            order = (lab["labelled_at"], r_idx, n)
            if lab["work_key"] in latest and latest[lab["work_key"]][0] > order:
                continue
            latest[lab["work_key"]] = (order, {
                **meta, "stage": "2", "labeller": "llm", "model": lab["model"],
                "prompt_sha256": lab["prompt_sha256"], "run_id": lab["run_id"],
                "machine": f"openai/{manifest.get('tier') or 'unknown'}", "label": lab["label"],
                "doc_type": lab.get("doc") if lab.get("doc") in ics.DOC_TYPES else ics.UNKNOWN,
                "studied_country": lab.get("studied") or "", "why": lab.get("why") or "",
                "labelled_at": lab["labelled_at"], "source": f"{name}/labels.jsonl"})
        report["lines"][expected["run_id"]] = len(lines)
        report["superseded_in_run"][expected["run_id"]] = len(lines) - len(latest)
        stamped += latest.values()
    return [row for _, row in sorted(stamped, key=lambda x: x[0])], report


def _latest_stage2(table_rows: list[dict], before_run: str) -> dict:
    """``{work_key: last stage-2 row}`` in table order (keys as written), over
    the rows that precede the first row of run ``before_run`` (all rows when
    the run is not in the table yet), so that a re-run checks what the first
    run saw and stays idempotent."""
    out = {}
    for r in table_rows:
        if r["run_id"] == before_run:
            break
        if r["stage"] == "2":
            out[r["work_key"]] = r
    return out


def relabel_rows(run_dir: str, table_rows: list[dict], pool: dict, run_id: str,
                 prompt_sha: str, labelled_at: str, machine: str) -> list[dict]:
    """Stage-2 rows of a relabelling run over works whose stage-2 label is unsure.

    The run directory (the Fable pass of 2026-10-07) holds ``fable_labels.json``
    (``{work_key: {label, why}}``, the labels its script kept), ``summary.json``
    (served model) and the raw answers ``chunkNN.txt`` (``n|label|doc|studied|
    why``), sent in sorted work-key order. The labels file has no doc type or
    country; they are read from the answers, aligned with the sorted labelled
    keys, skipping answer lines whose label is out of vocabulary (the script
    kept no label for those works). Every aligned line must give back the
    label and ``why`` of the labels file, else the alignment is refused.
    Refused too when a relabelled work's latest stage-2 row in the table is not
    ``unsure`` (the relabelling replaces unsure only), or is not a pool work.
    """
    run_dir = run_dir.rstrip("/")
    name = os.path.basename(run_dir)
    model = _json(os.path.join(run_dir, "summary.json"))["model"]
    labels = _json(os.path.join(run_dir, "fable_labels.json"))
    keys = iter(sorted(labels))
    answers = {}
    for path in sorted(glob.glob(os.path.join(run_dir, "chunk*.txt"))):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not _ANSWER.match(line):
                    continue
                parts = line.rstrip("\n").split("|", 4)
                if len(parts) < 5 or parts[1].strip().lower() not in ics.LABELS:
                    continue
                key = next(keys, None)
                _require(key is not None, f"{path}: more answers than labels; cannot align")
                answers[key] = (parts, os.path.basename(path))
    _require(next(keys, None) is None and len(answers) == len(labels),
             f"{run_dir}: {len(answers)} answers for {len(labels)} labels; cannot align")
    latest = _latest_stage2(table_rows, run_id)
    rows = []
    for key in sorted(labels):
        (parts, chunk), lab = answers[key], labels[key]
        _require((parts[1].strip().lower(), parts[4].strip()) == (lab["label"], lab["why"]),
                 f"{chunk}: the answer for {key!r} does not align with fable_labels.json")
        prev = latest.get(key)
        _require(prev is not None and prev["label"] == "unsure",
                 f"{key!r}: latest stage-2 label is {prev and prev['label']!r}, not unsure")
        doc = parts[2].strip()
        rows.append({**_pool_meta(key, pool, name), "stage": "2", "labeller": "llm",
                     "model": model, "prompt_sha256": prompt_sha, "run_id": run_id,
                     "machine": machine, "label": lab["label"],
                     "doc_type": doc if doc in ics.DOC_TYPES else ics.UNKNOWN,
                     "studied_country": parts[3].strip(), "why": lab["why"],
                     "labelled_at": labelled_at, "source": f"{name}/{chunk}"})
    return rows


def agree_rule_rows(checks_path: str, check_model: str, table_rows: list[dict],
                    relabel_run_id: str, run_id: str, labelled_at: str) -> list[dict]:
    """Stage-2 rows of the agreement rule (``AGREE_RULE``) over the relabelled icf.

    ``checks_path``: ``{work_key: label}`` of the check model on every work the
    relabelling run (``relabel_run_id``, already in the table) labelled icf,
    and on no other. Each work gets one row, ``icf`` when the check says icf,
    ``unsure`` otherwise; the check's own label is in ``why``. Author decision
    applied mechanically to model labels: ``labeller`` llm, ``model``
    ``RULE_MODEL`` (the rule, not a served model), ``prompt_sha256`` the hash
    of the rule text; doc type and country are the
    relabelling row's. Refused unless the relabelling row is each work's latest
    stage-2 row (the rule decides on top of it).
    """
    checks = _json(checks_path)
    relabelled = {r["work_key"]: r for r in table_rows
                  if r["stage"] == "2" and r["run_id"] == relabel_run_id and r["label"] == "icf"}
    _require(bool(relabelled), f"no icf row of run {relabel_run_id!r} in the table")
    _require(set(checks) == set(relabelled),
             f"{checks_path}: {len(set(relabelled) - set(checks))} relabelled icf without a "
             f"check, {len(set(checks) - set(relabelled))} checks on other works")
    bad = sorted(k for k, v in checks.items() if v not in ics.LABELS)
    _require(not bad, f"{checks_path}: {len(bad)} checks without a label, e.g. {bad[:3]}")
    latest = _latest_stage2(table_rows, run_id)
    source = "/".join(os.path.normpath(checks_path).split(os.sep)[-2:])
    sha = hashlib.sha256(AGREE_RULE.encode()).hexdigest()
    short = check_model.rsplit("/", 1)[-1]
    rows = []
    for key in sorted(checks):
        base = relabelled[key]
        _require(latest[key]["label_id"] == base["label_id"],
                 f"{key!r}: the relabelling row is not its latest stage-2 row")
        label = "icf" if checks[key] == "icf" else "unsure"
        rows.append({k: base[k] for k in ("work_key", "openalex_id", "doi", "title_norm_year",
                                          "doc_type", "studied_country")}
                    | {"stage": "2", "labeller": "llm", "model": RULE_MODEL,
                       "prompt_sha256": sha, "run_id": run_id, "machine": "padme",
                       "label": label, "labelled_at": labelled_at, "source": source,
                       "why": f"{base['model'].rsplit('/', 1)[-1]} icf, {short} {checks[key]}: "
                              "icf only when both agree, else unsure (author decision "
                              "2026-10-07)"})
    return rows


def side_table_rows(path: str, pool: list[dict]) -> list[dict]:
    """Rows of a side table written by ``ics.append_new`` (verified against its
    own manifest), without their ``label_id``; refused when a row matches no
    pool work (by the view's matching: work_key, OpenAlex id, then DOI)."""
    rows = ics.read_table(path)
    _require(bool(rows), f"{path} holds no rows")
    _, unmatched, _ = rv.match_labels(pool, rows)
    _require(not unmatched, f"{path}: {len(unmatched)} rows match no pool work, e.g. "
                            f"{[r['work_key'] for r in unmatched[:3]]}")
    return [{k: v for k, v in r.items() if k != "label_id"} for r in rows]


ID_FIELDS = ("openalex_id", "work_key")


def run_id_field(invocations: list[dict], labels: list[dict], run_dir: str) -> str:
    """The record key of a run: its header's ``id_field``, else the label lines'.

    Refused when the invocations disagree, or when a label line does not carry
    exactly that key: a run keyed two ways would attach labels to the wrong
    works or drop them silently.
    """
    declared = {i.get("id_field") for i in invocations} - {None}
    _require(len(declared) <= 1 and declared <= set(ID_FIELDS),
             f"{run_dir}: invocations declare id fields {sorted(declared)}")
    keyed = {tuple(f for f in ID_FIELDS if f in lab) for lab in labels}
    if declared:
        field = next(iter(declared))
    elif len(keyed) == 1 and len(next(iter(keyed))) == 1:
        field = next(iter(keyed))[0]
    else:
        field = "openalex_id"
    _require(keyed <= {(field,)},
             f"{run_dir}: label lines are keyed {sorted(keyed)}, not by {field!r} alone")
    return field


STAGE2_COMMANDS = ("stage2-sol", "stage2-relabel", "stage2-agree-rule", "rows")


def _add_stage2_parsers(sub) -> None:
    p = sub.add_parser("stage2-sol", help="labels.jsonl runs (one JSON label per line)")
    p.add_argument("--run-dir", action="append", required=True,
                   help="repeatable; ties in labelled_at keep this order")
    p.add_argument("--pool", default=None, help="default: config pool")
    p = sub.add_parser("stage2-relabel", help="relabelling of stage-2 unsure works")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--prompt-template", required=True,
                   help="the template the relabeller received; its sha256 is recorded")
    p.add_argument("--labelled-at", required=True)
    p.add_argument("--machine", default="openrouter")
    p.add_argument("--pool", default=None, help="default: config pool")
    p = sub.add_parser("stage2-agree-rule", help="icf kept only when the check agrees")
    p.add_argument("--checks", required=True, help="JSON {work_key: label} of the check model")
    p.add_argument("--check-model", required=True)
    p.add_argument("--relabel-run-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--labelled-at", required=True)
    p = sub.add_parser("rows", help="rows of a side table written by append_new")
    p.add_argument("--rows-file", required=True)
    p.add_argument("--pool", default=None, help="default: config pool")


def _stage2_rows(args, cfg: dict, table: str) -> tuple[list[dict], str]:
    """Rows and manifest note of one ``STAGE2_COMMANDS`` invocation."""
    pool_path = getattr(args, "pool", None) or cfg["pool"]
    if args.cmd == "stage2-sol":
        rows, report = sol_rows(args.run_dir, pool_by_key(pool_path))
        log.info("stage-2 runs: %s", report)
        return rows, (f"import stage-2 runs {', '.join(sorted(report['lines']))} in "
                      f"labelled_at order (pool sha256 {rv.sha256_file(pool_path)[:12]}; "
                      f"superseded repeats within a run: {report['superseded_in_run']})")
    if args.cmd == "stage2-relabel":
        rows = relabel_rows(args.run_dir, selection.read_effective_table(table), pool_by_key(pool_path),
                            args.run_id, _sha256(args.prompt_template), args.labelled_at,
                            args.machine)
        return rows, f"import stage-2 relabelling {args.run_id} of unsure works"
    if args.cmd == "stage2-agree-rule":
        rows = agree_rule_rows(args.checks, args.check_model, selection.read_effective_table(table),
                               args.relabel_run_id, args.run_id, args.labelled_at)
        return rows, (f"agreement rule {args.run_id}: {args.relabel_run_id} icf kept only "
                      f"when {args.check_model} agrees")
    return (side_table_rows(args.rows_file, rv.read_pool(pool_path)),
            f"append rows of {args.rows_file}")


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
    p1.add_argument("--stage2-prompt", default=None,
                    help="default: config t1530_stage2_prompt (the frozen v1 wrapper)")
    p2 = sub.add_parser("stage1-run")
    p2.add_argument("--run-dir", required=True)
    p2.add_argument("--machine", required=True)
    p2.add_argument("--input", default=None, help="default: RUN_DIR/screen_input.jsonl")
    p2.add_argument("--run-id", default=None, help="default: the run directory name")
    p2.add_argument("--pool", default=None,
                    help="work_key runs: the pool the input was built on (default: config pool)")
    p2.add_argument("--allow-input-drift", action="store_true",
                    help="import a work_key run although pool or table differ from those its "
                         "input was built on")
    p2.add_argument("--stopped", default="",
                    help="reason the run was stopped on purpose before its end; imports "
                         "its labels as they stand (recorded in the manifest note)")
    p2.add_argument("--skip-ids", default=None,
                    help="file of input ids (one per line) whose labels are not imported, "
                         "e.g. ids that are not real OpenAlex ids")
    p3 = sub.add_parser("stage1-designb")
    p3.add_argument("--run-dir", required=True)
    p3.add_argument("--input", default=None, help="default: RUN_DIR/screen_input.jsonl")
    p3.add_argument("--run-id", default=None, help="default: the run directory name")
    p3.add_argument("--pool", default=None,
                    help="the pool the input was built on (default: config pool)")
    p3.add_argument("--stopped", default="",
                    help="reason the run was stopped on purpose before its end; imports the "
                         "works both labellers labelled (recorded in the manifest note)")
    p3.add_argument("--allow-input-drift", action="store_true",
                    help="import although pool or table differ from those the input was "
                         "built on")
    _add_stage2_parsers(sub)
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    table = args.output
    try:
        if args.cmd in STAGE2_COMMANDS:
            rows, note = _stage2_rows(args, cfg, table)
        elif args.cmd == "t1530":
            archive = os.path.expanduser(args.archive or cfg["t1530_archive"])
            rows = t1530_rows(archive, args.stage2_prompt or cfg["t1530_stage2_prompt"])
            note = f"import t1530 from {archive}"
        elif args.cmd == "stage1-designb":
            run_dir = args.run_dir.rstrip("/")
            run_id = args.run_id or os.path.basename(run_dir)
            joint = rv.joint_rule(cfg.get("stage1_joint"))
            if joint is None:
                raise ImportRefused(f"{args.config} has no stage1_joint block")
            input_path = args.input or os.path.join(run_dir, "screen_input.jsonl")
            basis = None if args.allow_input_drift else (args.pool or cfg["pool"], table)
            rows, half = designb_rows(run_dir, input_path, run_id, joint, basis,
                                      args.stopped)
            log.info("%d works labelled by one labeller only: left unscreened", half)
            note = f"import design-B stage-1 run {run_id}"
            if args.stopped.strip():
                note += f" (stopped before its end: {args.stopped.strip()})"
        else:
            run_dir = args.run_dir.rstrip("/")
            run_id = args.run_id or os.path.basename(run_dir)
            skip = frozenset()
            if args.skip_ids:
                with open(args.skip_ids, encoding="utf-8") as fh:
                    skip = frozenset(line.strip() for line in fh if line.strip())
            input_path = args.input or os.path.join(run_dir, "screen_input.jsonl")
            basis = None if args.allow_input_drift else (args.pool or cfg["pool"], table)
            rows = stage1_run_rows(run_dir, input_path, args.machine, run_id,
                                   f"{run_id}/screen.jsonl", skip, basis, args.stopped)
            log.info("skipped %d ids listed in --skip-ids", len(skip))
            note = f"import stage-1 run {run_id}"
            if args.stopped.strip():
                note += f" (stopped before its end: {args.stopped.strip()})"
            if basis is None:
                note += " (--allow-input-drift)"
        added, skipped = ics.append_new(table, rows, note, args.new_table)
    except (ImportRefused, ics.IcfScreenError) as exc:
        log.error("%s", exc)
        return 1
    log.info("%d labels read, %d appended, %d already in %s", len(rows), added, skipped, table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
