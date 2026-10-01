"""The ``icf_screen`` table: every ICF label ever given, append-only (ticket 1732).

One row per label: which work (as it was screened), which stage (``1``, ``2``
or ``audit``), who labelled it (``llm``/``human``, model, prompt hash, run id,
machine), the label, the document type, the studied country, the reason, when,
and the provenance file. The table is a human-and-model judgement record, so
it never lives in a regenerable file (``.claude/rules/coding.md``, ticket
0372): this module only ever appends.

Guards, each one tested:

- the file is only opened for reading, appending, or exclusive creation;
  ``_open`` refuses any mode that could truncate or rewrite (``w``, ``+``);
- the header must be exactly ``COLUMNS``;
- a row whose key ``(work_key, stage, model, run_id)`` is already in the table
  (or twice in the batch) is refused, so a re-import cannot double-count.
  Keys compare byte-exact: no case folding, no whitespace trimming, no
  identifier normalisation (``openalex:W1`` and ``openalex:w1`` are two keys);
  a caller that wants folding normalises before it builds the row;
- the sidecar ``icf_screen.manifest.jsonl`` (also append-only, one line per
  append) records the file's byte length and sha256 after every append.
  Before reading or appending, the table must match the last manifest line
  exactly: a shorter file is a truncation, a longer file an unrecorded write,
  a same-length file with another hash a rewrite. Any of them aborts;
- a table missing where a ``.dvc`` pointer tracks it is an unfetched table:
  creating it is refused unless ``new_table`` is passed.

The manifest is self-anchored: it catches accidents, not a writer who edits
both files. The real tamper anchor is the DVC hash of ``data/rel_screen``
(table and manifest together) committed in git.

Readers go through ``read_table``, which runs the same verification.

The same guards serve a second append-only table, ``rel_dimensions`` (ticket
1840): the discipline fields of the version-2 stage-2 wrapper (contribution
test, field, contribution type), keyed like ``icf_screen`` so a dimension row
joins the ICF label it was given with. Every function that touches a table
takes a ``schema`` (``ICF``, the default, or ``DIMENSIONS``). ``rel_dimensions``
alone also takes stage ``catchup`` (ticket 1842: discipline fields asked after
the fact, ``scripts/corpus_rel_discipline_catchup.py``); ``icf_screen`` refuses
it, so a catch-up can never become a work's last stage-2 label.
"""

import csv
import hashlib
import io
import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import IO

COLUMNS = ["label_id", "work_key", "openalex_id", "doi", "title_norm_year", "stage",
           "labeller", "model", "prompt_sha256", "run_id", "machine", "label",
           "doc_type", "studied_country", "why", "labelled_at", "source"]
KEY = ("work_key", "stage", "model", "run_id")
STAGES = {"1", "2", "audit"}
# rel_dimensions also takes "catchup" (ticket 1842): the discipline fields asked
# alone, after the fact, of works stage 2 labelled before version 2. icf_screen
# never does: a catch-up row there would become the work's last stage-2 label.
DIMENSION_STAGES = STAGES | {"catchup"}
LABELLERS = {"llm", "human"}
LABELS = {"icf", "aux", "out", "unsure"}
DOC_TYPES = {"research", "institutional", "other", "unknown"}
WORK_KEY_PREFIXES = ("openalex:", "doi:", "url:", "title:")
REQUIRED = ["work_key", "stage", "labeller", "model", "prompt_sha256", "run_id",
            "machine", "label", "doc_type", "labelled_at", "source"]
UNKNOWN = "unknown"

# Closed vocabularies of the version-2 wrapper (config/rel_stage2_prompt_v2.md,
# where each value is defined). "na" is the answer for a work labelled out;
# "unknown" stores an out-of-vocabulary answer.
CONTRIB = {"yes", "no", "unsure", "na"}
FIELDS = {"economics", "politics", "law", "finance", "management", "data_science",
          "natural_science", "other", "na"}
CONTRIB_TYPES = {"empirical", "theory", "method", "policy", "review", "case", "other", "na"}
DIMENSION_COLUMNS = ["dim_id", "work_key", "stage", "labeller", "model", "prompt_sha256",
                     "run_id", "machine", "contrib", "field", "contrib_type", "labelled_at",
                     "source"]


@dataclass(frozen=True)
class Schema:
    """One append-only table: its header, id column, required columns and vocabularies."""

    columns: list
    id_column: str
    required: list
    enums: tuple  # ((column, allowed values), ...)


ICF = Schema(COLUMNS, "label_id", REQUIRED,
             (("stage", STAGES), ("labeller", LABELLERS), ("label", LABELS),
              ("doc_type", DOC_TYPES)))
DIMENSIONS = Schema(DIMENSION_COLUMNS, "dim_id",
                    [c for c in DIMENSION_COLUMNS if c != "dim_id"],
                    (("stage", DIMENSION_STAGES), ("labeller", LABELLERS),
                     ("contrib", CONTRIB | {UNKNOWN}), ("field", FIELDS | {UNKNOWN}),
                     ("contrib_type", CONTRIB_TYPES | {UNKNOWN})))


class IcfScreenError(Exception):
    """A refused write or a table that no longer matches its manifest."""


def manifest_path(table_path: str) -> str:
    return os.path.splitext(table_path)[0] + ".manifest.jsonl"


def dvc_pointer(table_path: str) -> str | None:
    """The ``.dvc`` file that tracks the table's directory (or the table), if any."""
    table_dir = os.path.dirname(os.path.abspath(table_path))
    for cand in (table_dir + ".dvc", os.path.abspath(table_path) + ".dvc"):
        if os.path.exists(cand):
            return cand
    return None


def require_table(table_path: str) -> None:
    """Refuse, with the fetch to run, when the table is absent (readers call this)."""
    if not os.path.exists(table_path):
        pointer = dvc_pointer(table_path)
        hint = (f"fetch it with `dvc pull {os.path.relpath(pointer)}` (make rel-pool-data) "
                "or `dvc checkout`" if pointer else "import labels first")
        raise IcfScreenError(f"{table_path} is missing: {hint}")


def _open(path: str, mode: str) -> IO[str]:
    """Open the table or its manifest; only non-destructive modes exist here."""
    if mode not in ("r", "a", "x"):
        raise IcfScreenError(f"icf_screen files are append-only: mode {mode!r} refused")
    return open(path, mode, encoding="utf-8", newline="")


def label_id(row: dict) -> str:
    """Stable id of a label: a hash of its key, so a rebuild gives the same ids."""
    return hashlib.sha256("\x1f".join(row[k] for k in KEY).encode()).hexdigest()[:16]


def _sha256_prefix(path: str, n_bytes: int) -> str:
    h = hashlib.sha256()
    remaining = n_bytes
    with open(path, "rb") as fh:
        while remaining > 0:
            chunk = fh.read(min(1 << 20, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()


def _manifest_entries(table_path: str) -> list[dict]:
    with _open(manifest_path(table_path), "r") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def verify(table_path: str) -> dict | None:
    """Check the table against its manifest; the last entry, or None if absent.

    Raises ``IcfScreenError`` on a truncated, rewritten or extended-unrecorded
    table, on a table without manifest (or the reverse), and on a manifest
    whose own history is not monotone.
    """
    has_table = os.path.exists(table_path)
    has_manifest = os.path.exists(manifest_path(table_path))
    if not has_table and not has_manifest:
        return None
    if has_table != has_manifest:
        raise IcfScreenError(f"{table_path}: table and manifest must exist together")
    entries = _manifest_entries(table_path)
    if not entries:
        raise IcfScreenError(f"{manifest_path(table_path)} is empty")
    for prev, cur in zip(entries, entries[1:]):
        if cur["bytes"] <= prev["bytes"] or cur["rows_total"] <= prev["rows_total"]:
            raise IcfScreenError(f"{manifest_path(table_path)}: history not monotone")
    last = entries[-1]
    size = os.path.getsize(table_path)
    if size < last["bytes"]:
        raise IcfScreenError(f"{table_path} is truncated: {size} bytes, manifest records "
                             f"{last['bytes']}")
    if _sha256_prefix(table_path, last["bytes"]) != last["sha256"]:
        raise IcfScreenError(f"{table_path}: recorded rows were rewritten (sha256 mismatch)")
    if size > last["bytes"]:
        raise IcfScreenError(f"{table_path}: {size - last['bytes']} bytes appended without "
                             "a manifest entry")
    return last


def _read_rows(table_path: str, schema: Schema = ICF) -> list[dict]:
    with _open(table_path, "r") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != schema.columns:
            raise IcfScreenError(f"{table_path}: header {reader.fieldnames} is not "
                                 f"{schema.columns}")
        return list(reader)


def read_table(table_path: str, schema: Schema = ICF) -> list[dict]:
    """All rows, in append order, after verification; [] when there is no table."""
    last = verify(table_path)
    if last is None:
        return []
    rows = _read_rows(table_path, schema)
    if len(rows) != last["rows_total"]:
        raise IcfScreenError(f"{table_path}: {len(rows)} rows, manifest records "
                             f"{last['rows_total']}")
    return rows


def key_of(row: dict) -> tuple[str, ...]:
    return tuple(row[k] for k in KEY)


def validate_row(row: dict, schema: Schema = ICF) -> list[str]:
    """Faults of one row (empty list when it may be appended)."""
    errors = []
    extra = set(row) - set(schema.columns)
    if extra:
        errors.append(f"unknown columns {sorted(extra)}")
    for col in schema.required:
        if not (row.get(col) or "").strip():
            errors.append(f"{col} is empty")
    for col, allowed in schema.enums:
        if row.get(col) and row[col] not in allowed:
            errors.append(f"{col}={row[col]!r} not in {sorted(allowed)}")
    wk = row.get("work_key") or ""
    if wk and not wk.startswith(WORK_KEY_PREFIXES):
        errors.append(f"work_key {wk!r} lacks a prefix {WORK_KEY_PREFIXES}")
    return errors


def _refuse_fork(table_path: str, new_table: bool) -> None:
    """A missing table under a ``.dvc`` pointer is an unfetched one, not a new one.

    Creating it there would start a second history that the next ``dvc
    checkout`` or ``dvc add`` silently replaces or forks; ``new_table=True``
    (``--new-table``) is the explicit opt-in for a genuinely first table.
    """
    if new_table or os.path.exists(table_path):
        return
    pointer = dvc_pointer(table_path)
    if pointer:
        raise IcfScreenError(
            f"{table_path} is missing but {os.path.relpath(pointer)} tracks it: run "
            f"`dvc checkout {os.path.relpath(pointer)}` (or `dvc pull`, make rel-pool-data) "
            "first; pass --new-table only to start a new table on purpose")


def append_rows(table_path: str, rows: Iterable[dict], note: str = "",
                new_table: bool = False, schema: Schema = ICF) -> int:
    """Append ``rows`` (dicts over the schema's columns minus its id); return how many.

    Every row is validated and checked against the keys already in the table
    before a single byte is written: one bad row refuses the whole batch.
    Creating the table is refused when a ``.dvc`` pointer tracks it, unless
    ``new_table`` (see ``_refuse_fork``).
    """
    rows = [dict(r) for r in rows]
    if not rows:
        return 0
    _refuse_fork(table_path, new_table)
    existing = read_table(table_path, schema)
    seen = {key_of(r) for r in existing}
    faults = []
    for n, row in enumerate(rows, 1):
        for col in schema.columns:
            row.setdefault(col, "")
            row[col] = "" if row[col] is None else str(row[col])
        errors = validate_row(row, schema)
        if not errors:
            k = key_of(row)
            if k in seen:
                errors.append(f"key {k} already in the table")
            seen.add(k)
        if errors:
            faults.append(f"row {n}: " + "; ".join(errors))
        row[schema.id_column] = label_id(row) if not errors else ""
    if faults:
        raise IcfScreenError(f"{len(faults)} row(s) refused, nothing written:\n  "
                             + "\n  ".join(faults[:20]))

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=schema.columns, lineterminator="\n")
    new_table = not existing and not os.path.exists(table_path)
    if new_table:
        writer.writeheader()
    for row in rows:
        writer.writerow({c: row[c] for c in schema.columns})
    os.makedirs(os.path.dirname(os.path.abspath(table_path)), exist_ok=True)
    with _open(table_path, "x" if new_table else "a") as fh:
        fh.write(buf.getvalue())
        fh.flush()
        os.fsync(fh.fileno())
    size = os.path.getsize(table_path)
    entry = {"appended_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "rows_added": len(rows), "rows_total": len(existing) + len(rows),
             "bytes": size, "sha256": _sha256_prefix(table_path, size), "note": note}
    with _open(manifest_path(table_path), "x" if new_table else "a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def append_new(table_path: str, rows: Iterable[dict], note: str = "",
               new_table: bool = False, schema: Schema = ICF) -> tuple[int, int]:
    """Append the rows whose key is not in the table yet: ``(appended, skipped)``.

    The idempotent entry point for importers: a second run appends nothing.
    """
    rows = list(rows)
    _refuse_fork(table_path, new_table)
    seen = {key_of(r) for r in read_table(table_path, schema)}
    fresh = [r for r in rows if key_of({k: str(r.get(k) or "") for k in KEY}) not in seen]
    return append_rows(table_path, fresh, note, new_table, schema), len(rows) - len(fresh)


# ── Shared record formats (1530 stage 2) ─────────────────


def format_stage2_record(n: int, rec: dict, title_max: int, abstract_max: int) -> str:
    """One record as the 1530 stage-2 chunks show it (adhoc t1530-stage2-build.py).

    ``rec`` has ``language``, ``year``, ``journal``, ``countries`` (list),
    ``title``, ``abstract``. Blank language/year/journal print as ``?``.
    """
    where = ", ".join(rec.get("countries") or []) or "?"
    abstract = (rec.get("abstract") or "(no abstract)")[:abstract_max]
    return (f"{n}. [{rec.get('language') or '?'} | {rec.get('year') or '?'} | "
            f"{rec.get('journal') or '?'} | affiliations: {where}]\n"
            f"   Title: {(rec.get('title') or '')[:title_max]}\n   Abstract: {abstract}\n")


V1_FIELDS = ("n", "label", "doc", "studied", "why")
V2_FIELDS = ("n", "label", "doc", "studied", "contrib", "field", "ctype", "why")
CATCHUP_FIELDS = ("n", "contrib", "field", "ctype", "why")
_DIM_VOCAB = {"contrib": CONTRIB, "field": FIELDS, "ctype": CONTRIB_TYPES}


def parse_stage2_answers(lines: Iterable[str], ids: list[str],
                         fields: tuple = V1_FIELDS) -> tuple[dict, list[str]]:
    """``{id: answer}`` from answer lines in the ``fields`` format, and the faults.

    ``V1_FIELDS`` (``n|label|doc|studied|why``, the 1530 wrapper) or
    ``V2_FIELDS`` (``n|label|doc|studied|contrib|field|ctype|why``, ticket
    1840). Same acceptance as the 1530 consolidation: a line is kept when ``n``
    is in range and the label valid; ``why``, always last, keeps any further
    ``|``. A number answered twice, a short or out-of-range line is a fault,
    reported, never guessed. An out-of-vocabulary ``doc`` or discipline value
    is stored as ``unknown``. Blank lines are skipped.
    """
    answers: dict = {}
    faults = []
    shape = "|".join(fields)
    for lineno, line in enumerate(lines, 1):
        parts = line.rstrip("\n").split("|")
        if not line.strip():
            continue
        if len(parts) < len(fields) - 1 or not parts[0].strip().isdigit():
            faults.append(f"line {lineno}: not {shape}")
            continue
        n = int(parts[0])
        if not 1 <= n <= len(ids) or parts[1].strip() not in LABELS:
            faults.append(f"line {lineno}: n={n} or label={parts[1]!r} invalid")
            continue
        if ids[n - 1] in answers:
            faults.append(f"line {lineno}: record {n} answered twice")
            continue
        doc = parts[2].strip()
        answer = {"label": parts[1].strip(), "doc": doc if doc in DOC_TYPES else UNKNOWN,
                  "studied": parts[3].strip()}
        for i, name in enumerate(fields[4:-1], 4):
            value = parts[i].strip().lower()
            answer[name] = value if value in _DIM_VOCAB[name] else UNKNOWN
        answer["why"] = "|".join(parts[len(fields) - 1:]).strip()
        answers[ids[n - 1]] = answer
    missing = len(ids) - len(answers)
    if missing:
        faults.append(f"{missing} of {len(ids)} records unanswered")
    return answers, faults


def parse_discipline_answers(lines: Iterable[str], ids: list[str]) -> tuple[dict, list[str]]:
    """``{id: answer}`` from catch-up answer lines (``CATCHUP_FIELDS``), and the faults.

    The acceptance of ``parse_stage2_answers``: ``n`` in range and answered
    once, ``why`` last and keeping any further ``|``; an out-of-vocabulary
    discipline value is stored as ``unknown``. A line that reads as a stage-2
    answer (an ICF label ``icf``/``aux``/``out`` where ``contrib`` belongs, or a
    document type ``research``/``institutional`` where ``field`` belongs) is a
    fault. Blank lines and Markdown fence lines are skipped.
    """
    answers: dict = {}
    faults = []
    shape = "|".join(CATCHUP_FIELDS)
    for lineno, line in enumerate(lines, 1):
        if not line.strip() or line.strip().startswith("```"):
            continue
        parts = line.rstrip("\n").split("|")
        head = parts[0].strip()
        # ASCII digits only, and short: int() accepts "²" or "٣" and chokes on huge strings.
        if (len(parts) < len(CATCHUP_FIELDS) - 1 or not head.isascii() or not head.isdigit()
                or len(head) > 6):
            faults.append(f"line {lineno}: not {shape}")
            continue
        n = int(head)
        if not 1 <= n <= len(ids):
            faults.append(f"line {lineno}: n={n} out of range")
            continue
        if ids[n - 1] in answers:
            faults.append(f"line {lineno}: record {n} answered twice")
            continue
        # A stage-2 line reads n|label|doc|...: an ICF label where contrib belongs, or
        # a document type where field belongs.
        if (parts[1].strip().lower() in LABELS - CONTRIB
                or parts[2].strip().lower() in DOC_TYPES - FIELDS - {UNKNOWN}):
            faults.append(f"line {lineno}: {parts[1].strip()}|{parts[2].strip()} reads as a "
                          "stage-2 answer line (label|doc)")
            continue
        answer = {}
        for i, name in enumerate(CATCHUP_FIELDS[1:-1], 1):
            value = parts[i].strip().lower()
            answer[name] = value if value in _DIM_VOCAB[name] else UNKNOWN
        answer["why"] = "|".join(parts[len(CATCHUP_FIELDS) - 1:]).strip()
        answers[ids[n - 1]] = answer
    missing = len(ids) - len(answers)
    if missing:
        faults.append(f"{missing} of {len(ids)} records unanswered")
    return answers, faults


def _prompt_block(prompt_md_path: str) -> str:
    with open(prompt_md_path, encoding="utf-8") as fh:
        text = fh.read()
    parts = text.split("```")
    if len(parts) < 3:
        raise IcfScreenError(f"{prompt_md_path}: no fenced prompt block")
    return parts[1].strip("\n")


def stage2_answer_fields(prompt_md_path: str) -> tuple:
    """The answer format a stage-2 wrapper asks for: ``V1_FIELDS`` or ``V2_FIELDS``.

    Read from the line after "format exactly:" in the fenced wrapper, so the
    prompt file is the one place the format is declared.
    """
    m = re.search(r"format exactly:\s*\n\s*(\S+)", _prompt_block(prompt_md_path))
    found = tuple(m.group(1).split("|")) if m else None
    if found not in (V1_FIELDS, V2_FIELDS):
        raise IcfScreenError(f"{prompt_md_path}: answer format {found} is neither "
                             f"{'|'.join(V1_FIELDS)} nor {'|'.join(V2_FIELDS)}")
    return found


def catchup_prompt_template(prompt_md_path: str) -> str:
    """The fenced block of a catch-up wrapper, checked: ``CATCHUP_FIELDS``, one ``{records}``."""
    block = _prompt_block(prompt_md_path)
    m = re.search(r"format exactly:\s*\n\s*(\S+)", block)
    found = tuple(m.group(1).split("|")) if m else None
    if found != CATCHUP_FIELDS or block.count("{records}") != 1:
        raise IcfScreenError(f"{prompt_md_path}: not a catch-up wrapper (answer format "
                             f"{found}, exactly one {{records}} placeholder required)")
    return block


def stage2_prompt_sha256(prompt_md_path: str) -> str:
    """sha256 of the fenced wrapper of a prompt file (stage-2 or catch-up).

    That wrapper is the text each stage-2 labeller received, with the chunk
    file names filled in; the hash identifies the template. The version-1
    file (``t1530_stage2_prompt`` in ``config/rel_screen.yaml``) is frozen:
    its hash is on the t1530 Opus rows of ``icf_screen``.
    """
    return hashlib.sha256(_prompt_block(prompt_md_path).encode()).hexdigest()
