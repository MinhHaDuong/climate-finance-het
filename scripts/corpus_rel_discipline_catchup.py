"""Discipline catch-up of the works stage 2 relabelled before version 2 (ticket 1842).

The version-2 stage-2 wrapper (ticket 1840) asks three discipline questions
(contribution test, field, contribution type) beside the ICF label. Works
stage 2 labelled earlier lack them. This command asks those questions alone,
with the discipline-only wrapper ``catchup.prompt`` of ``config/rel_screen.yaml``,
and writes the answers to ``rel_dimensions`` only, under stage ``catchup``.
It never writes ``icf_screen``: the REL view takes a work's last stage-2 row
there, so a catch-up written as stage 2 would shadow its ICF label.

``build``
    Works whose final stage-2 label (REL view over the pool and ``icf_screen``)
    is in ``catchup.final_labels``, that have an abstract (no-abstract works are
    bibliometric only, ticket 1733) and whose work key has no ``rel_dimensions``
    row yet, sorted by work key, in stage-2 chunks (``chunkNN.txt``,
    ``chunkNN.ids.json``, ``works.csv``, ``build.json`` with the counts), then
    rendered. Refused when ``rel_dimensions`` is missing although
    ``icf_screen`` holds version-2 stage-2 rows (the table was lost, not empty).
    With ``--keys FILE`` (one work key per line), the validation mode: exactly
    those works, in that order, with no label or dimension selection (the gold
    set of ticket 1840); refused when a key is absent from the pool, repeated,
    or has no abstract. ``build.json`` then records kind ``keys`` and the file's
    hash.

``render``
    Writes ``chunkNN.prompt.txt`` (the wrapper with the chunk's records) next
    to each ``chunkNN.txt`` of a chunk directory, and ``render.json`` with the
    wrapper's hash; a directory rendered with one wrapper refuses another. The
    rendered prompt is the instrument for every route: an OpenRouter call sends
    it as the user message; a Claude Code subagent is told to follow it and
    write its reply to ``chunkNN.<suffix>.txt``.

``count-tokens``
    Input tokens of every rendered prompt, measured with the Anthropic
    ``count_tokens`` endpoint (free; ``--count-model``), to ``tokens.json``.

``submit`` / ``collect``
    OpenRouter Batch API (``POST /api/v1/batches``, asynchronous, 24-hour
    window, about half the synchronous price on ``:batch`` endpoints): one
    request per chunk, ``custom_id`` = chunk name. ``collect`` polls once
    (``--wait`` to poll until terminal); on a completed batch it writes the
    raw batch object, each reply verbatim (``chunkNN.<suffix>.raw.txt``), its
    answer lines (``chunkNN.<suffix>.txt``: the lines that start with a record
    number) and ``<suffix>.calls.jsonl``, rewritten whole, so a second collect
    does not double the cost log. An errored request, or a reply with no valid
    answer line, writes no answer file: the chunk stays pending.

``call``
    The same requests through the synchronous ``/chat/completions`` endpoint,
    for a model or a run without batch. Chunks that already have an answer
    file are skipped; each call appends its line to ``<suffix>.calls.jsonl``.

``parse``
    Reads ``chunkNN.<suffix>.txt`` (``n|contrib|field|ctype|why``) and appends
    the rows to ``rel_dimensions`` under stage ``catchup``, with the model, run
    id and machine given and the wrapper hash recorded by ``render``. A chunk
    with a malformed, duplicated or stage-2 line, or with no valid discipline
    value at all, refuses the whole parse; an incomplete chunk is accepted and
    reported, with its ``na`` answers (no climate-finance object at all) and
    those that put ``na`` in some but not all three fields (``na_off_rule``,
    stored as answered). A work that already has a ``rel_dimensions`` row under another
    stage, model or run id is skipped and counted, so a second run id never
    gives a work two catch-up answers. Idempotent for one run id. A ``build
    --keys`` directory (kind ``keys``) is refused unless ``--dimensions-table``
    is given explicitly, so validation rows never reach the production table.

``count-tokens``, ``submit``, ``call`` and ``parse`` refuse a directory whose
``render.json`` records another wrapper than the current one, before any call.

Spend guard (``submit``, ``call``): the bound is the input tokens (measured by
``count-tokens`` when ``tokens.json`` exists, else characters / 3) at the
listed input price, plus ``--max-tokens`` per chunk at the listed output price.
Reasoning tokens count as output and fall under ``--max-tokens``. Nothing is
sent when the bound exceeds ``--max-usd`` or a price is not a positive number.

Token and cost log (``<suffix>.calls.jsonl``, one line per chunk): records,
answered, prompt, completion and reasoning tokens, cost (``cost_source``:
``reported`` by OpenRouter, or ``derived`` from the model's listed per-token
price when the response carries no cost), cost per answered record. The model
is a parameter everywhere: the catch-up must use the model forward stage 2 uses.

Usage:
    python scripts/corpus_rel_discipline_catchup.py build --output-dir DIR [--keys FILE]
    python scripts/corpus_rel_discipline_catchup.py render --chunk-dir DIR
    python scripts/corpus_rel_discipline_catchup.py count-tokens --chunk-dir DIR
    python scripts/corpus_rel_discipline_catchup.py submit --chunk-dir DIR --model M \\
        --suffix S --max-usd X [--max-tokens N]
    python scripts/corpus_rel_discipline_catchup.py collect --chunk-dir DIR --suffix S [--wait]
    python scripts/corpus_rel_discipline_catchup.py call --chunk-dir DIR --model M --suffix S \\
        --max-usd X [--max-tokens N]
    python scripts/corpus_rel_discipline_catchup.py parse --chunk-dir DIR --suffix S --model M \\
        --run-id R --machine padme
"""

import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone

import _icf_chunks as ch
import _icf_screen as ics
import _rel_selection as selection
import _rel_view as rv
import requests
import yaml
from pipeline_keystore import read_credential
from utils import get_logger

log = get_logger("corpus_rel_discipline_catchup")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_screen.yaml")
STAGE = "catchup"
OPENROUTER = "https://openrouter.ai/api/v1"
ANTHROPIC_COUNT = "https://api.anthropic.com/v1/messages/count_tokens"
KEY_VAR = "OPENROUTER_API_KEY_CLIMATEFINANCE"
CHARS_PER_TOKEN_FLOOR = 3.0  # conservative, for the spend guard only
_CHUNK = re.compile(r"^(chunk\d+)\.ids\.json$")
_ANSWER_LINE = re.compile(r"^\s*\d+\s*\|")


class CatchupError(Exception):
    """A refused build, request or parse."""


# ── selection ────────────────────────────────────────────


def select_catchup(view_rows: list[dict], final_labels: list[str], with_dims: set,
                   no_abstract: set = frozenset()) -> dict:
    """Work keys to catch up, sorted, and the counts behind the selection.

    Works in ``no_abstract`` are left out: by the no-abstract policy (ticket
    1733, author decision 2026-10-07) they count in the bibliometric analysis
    only and are never sent to a model.
    """
    statuses = {s for s, lab in ch.FINAL_STAGE2.items() if lab in final_labels}
    eligible = sorted((r["work_key"], r["status"]) for r in view_rows if r["status"] in statuses)
    with_abstract = [(k, s) for k, s in eligible if k not in no_abstract]
    picked = [(k, s) for k, s in with_abstract if k not in with_dims]
    by_label = {lab: 0 for lab in final_labels}
    for _, s in picked:
        by_label[ch.FINAL_STAGE2[s]] += 1
    return {"keys": [k for k, _ in picked], "eligible": len(eligible),
            "no_abstract": len(eligible) - len(with_abstract),
            "already_with_dimensions": len(with_abstract) - len(picked), "by_label": by_label}


def select_keys(pool: list[dict], keys: list[str]) -> list[dict]:
    """Pool rows of ``keys``, in order; refused for a key absent, repeated or without abstract."""
    by_key = {p["work_key"]: p for p in pool}
    missing = [k for k in keys if k not in by_key]
    repeated = sorted({k for k in keys if keys.count(k) > 1})
    no_abstract = [k for k in keys if k in by_key and not (by_key[k]["abstract"] or "").strip()]
    if missing or repeated or no_abstract or not keys:
        raise CatchupError(f"keys refused: {len(keys)} keys, missing {missing[:5]}, repeated "
                           f"{repeated[:5]}, without abstract {no_abstract[:5]}; nothing built")
    return [by_key[k] for k in keys]


def dimension_rows(table: str, dims_table: str, v2_prompt: str) -> list[dict]:
    """``rel_dimensions`` rows; refuse a missing table that version-2 parses wrote.

    ``rel_dimensions`` starts with the first version-2 stage-2 parse. If it is
    missing while ``icf_screen`` holds rows of the version-2 wrapper, it was
    lost or not fetched: reading it as empty would plan every work again.
    """
    if not os.path.exists(dims_table):
        sha = ics.stage2_prompt_sha256(v2_prompt)
        if any(r["prompt_sha256"] == sha for r in ics.read_table(table)):
            raise CatchupError(f"{dims_table} is missing but {table} holds version-2 stage-2 "
                               "rows: fetch it (make rel-pool-data) first; nothing built")
    return selection.read_effective_table(dims_table, ics.DIMENSIONS)


# ── prompts ──────────────────────────────────────────────


def chunk_names(chunk_dir: str) -> list[str]:
    return sorted(m.group(1) for m in map(_CHUNK.match, os.listdir(chunk_dir)) if m)


def render(chunk_dir: str, prompt_path: str) -> list[str]:
    """``chunkNN.prompt.txt`` for every chunk, and ``render.json`` (the wrapper's hash)."""
    template = ics.catchup_prompt_template(prompt_path)
    meta_path = os.path.join(chunk_dir, "render.json")
    sha = _check_rendered(chunk_dir, prompt_path, missing_ok=True)
    names = chunk_names(chunk_dir)
    for name in names:
        with open(os.path.join(chunk_dir, f"{name}.txt"), encoding="utf-8") as fh:
            records = fh.read().rstrip("\n")
        with open(os.path.join(chunk_dir, f"{name}.prompt.txt"), "w", encoding="utf-8") as fh:
            fh.write(template.replace("{records}", records) + "\n")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump({"prompt": prompt_path, "prompt_sha256": sha, "chunks": names}, fh, indent=2)
        fh.write("\n")
    return names


def rendered_sha(chunk_dir: str) -> str:
    """The hash of the wrapper the chunk prompts were rendered with."""
    meta_path = os.path.join(chunk_dir, "render.json")
    if not os.path.exists(meta_path):
        raise CatchupError(f"{meta_path} missing: the prompts were not rendered by this command")
    with open(meta_path, encoding="utf-8") as fh:
        return json.load(fh)["prompt_sha256"]


def _check_rendered(chunk_dir: str, prompt_path: str, missing_ok: bool = False) -> str:
    """The current wrapper's hash; refused when the directory was rendered with another."""
    sha = ics.stage2_prompt_sha256(prompt_path)
    if missing_ok and not os.path.exists(os.path.join(chunk_dir, "render.json")):
        return sha
    prior = rendered_sha(chunk_dir)
    if prior != sha:
        raise CatchupError(f"{chunk_dir} was rendered with wrapper {prior[:12]}, not "
                           f"{sha[:12]}: build a new directory")
    return sha


def _prompts(chunk_dir: str) -> dict:
    out = {}
    for name in chunk_names(chunk_dir):
        path = os.path.join(chunk_dir, f"{name}.prompt.txt")
        if not os.path.exists(path):
            raise CatchupError(f"{path} missing: run render first")
        with open(path, encoding="utf-8") as fh:
            out[name] = fh.read()
    return out


def _ids(chunk_dir: str, name: str) -> list[str]:
    with open(os.path.join(chunk_dir, f"{name}.ids.json"), encoding="utf-8") as fh:
        return json.load(fh)


# ── cost ─────────────────────────────────────────────────


def model_pricing(model: str, get=requests.get) -> dict:
    """Listed USD per token of an OpenRouter model id; refused unless both are positive."""
    resp = get(f"{OPENROUTER}/models", timeout=60)
    resp.raise_for_status()
    for m in resp.json()["data"]:
        if m["id"] == model:
            p = {k: float(m["pricing"][k]) for k in ("prompt", "completion")}
            if not all(math.isfinite(v) and v > 0 for v in p.values()):
                raise CatchupError(f"{model} lists prices {p}: no spend bound possible")
            return p
    raise CatchupError(f"{model} is not in the OpenRouter model list")


def spend_bound_usd(prompts: dict, pricing: dict, max_tokens: int,
                    tokens: dict | None = None) -> float:
    """Most a run can cost: input tokens plus ``max_tokens`` of output per chunk."""
    inp = sum((tokens or {}).get(k) or len(v) / CHARS_PER_TOKEN_FLOOR for k, v in prompts.items())
    return inp * pricing["prompt"] + len(prompts) * max_tokens * pricing["completion"]


def usage_log(chunk: str, body: dict, n_records: int, n_answered: int, pricing: dict,
              extra: dict) -> dict:
    """One ``calls.jsonl`` line from a chat-completion body."""
    u = body.get("usage") or {}
    pt, ct = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
    reasoning = int((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
    if u.get("cost") is not None:
        cost, source = float(u["cost"]), "reported"
    else:
        cost, source = pt * pricing["prompt"] + ct * pricing["completion"], "derived"
    choice = (body.get("choices") or [{}])[0]
    return {"chunk": chunk, **extra, "model_served": body.get("model"),
            "generation_id": body.get("id"), "finish_reason": choice.get("finish_reason"),
            "records": n_records, "answered": n_answered, "prompt_tokens": pt,
            "completion_tokens": ct, "reasoning_tokens": reasoning,
            "cost_usd": round(cost, 6), "cost_source": source,
            "cost_per_answered_usd": round(cost / n_answered, 6) if n_answered else None}


def _content(body: dict) -> str:
    return (((body.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""


def _truncated(body: dict) -> bool:
    return ((body.get("choices") or [{}])[0].get("finish_reason")) == "length"


def _write_answer(chunk_dir: str, chunk: str, suffix: str, text: str,
                  truncated: bool = False) -> int:
    """Keep the reply verbatim (``.raw.txt``) and its answer lines; return records answered.

    Only lines that start with a record number go to the answer file, so a
    model's preamble or closing sentence does not refuse a paid chunk; the raw
    reply keeps them for audit. A reply with no valid answer line (empty,
    truncated, an error body, a table, or numbered lines none of which parses:
    a bare ``1 | yes``, a record number out of range, a stage-2 line) writes no
    answer file: the chunk stays pending, so ``call`` retries it and ``parse``
    reports it as unanswered instead of aborting on it.

    A ``truncated`` reply (``finish_reason`` length: output stopped at
    ``--max-tokens``) loses its last line, where output stopped: a value or the
    reason may be cut even when the line parses, and a cut line would refuse
    the whole parse. Its record stays unanswered.
    """
    stem = os.path.join(chunk_dir, f"{chunk}.{suffix}")
    with open(f"{stem}.raw.txt", "w", encoding="utf-8") as fh:
        fh.write(text)
    kept = text.splitlines()[:-1] if truncated else text.splitlines()
    lines = [ln for ln in kept if _ANSWER_LINE.match(ln)]
    answers = ics.parse_discipline_answers(lines, _ids(chunk_dir, chunk))[0] if lines else {}
    if not answers:
        log.warning("%s: no valid answer line in the reply (%d numbered of %d characters), "
                    "left pending", chunk, len(lines), len(text))
        if os.path.exists(f"{stem}.txt"):
            os.remove(f"{stem}.txt")
        return 0
    with open(f"{stem}.txt", "w", encoding="utf-8") as fh:
        fh.writelines(ln + "\n" for ln in lines)
    return len(answers)


def _headers() -> dict:
    key = read_credential("openrouter", KEY_VAR)
    if not key:
        raise CatchupError(f"no OpenRouter key ({KEY_VAR}) in the keystore")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _request_body(prompt: str, max_tokens: int, effort: str | None) -> dict:
    body = {"max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if effort:
        body["reasoning"] = {"effort": effort}
    return body


def _guard(chunk_dir: str, model: str, max_usd: float, max_tokens: int) -> dict:
    if not (math.isfinite(max_usd) and max_usd > 0) or max_tokens < 1:
        raise CatchupError(f"--max-usd {max_usd} and --max-tokens {max_tokens} must be positive")
    prompts = _prompts(chunk_dir)
    n = sum(len(_ids(chunk_dir, k)) for k in prompts)
    tokens = None
    tok_path = os.path.join(chunk_dir, "tokens.json")
    if os.path.exists(tok_path):
        with open(tok_path, encoding="utf-8") as fh:
            tokens = json.load(fh)["by_chunk"]
    pricing = model_pricing(model)
    bound = spend_bound_usd(prompts, pricing, max_tokens, tokens)
    if bound > max_usd:
        raise CatchupError(f"spend bound {bound:.3f} USD for {n} records exceeds --max-usd "
                           f"{max_usd}; nothing sent")
    log.info("%d records in %d chunks, spend bound %.3f USD (cap %.2f)", n, len(prompts),
             bound, max_usd)
    return {"prompts": prompts, "pricing": pricing, "bound_usd": round(bound, 4), "records": n}


# ── routes ───────────────────────────────────────────────


def submit(chunk_dir: str, model: str, suffix: str, max_usd: float, max_tokens: int,
           effort: str | None, post=requests.post) -> dict:
    meta_path = os.path.join(chunk_dir, f"{suffix}.batch.json")
    if os.path.exists(meta_path):
        raise CatchupError(f"{meta_path} exists: this suffix was already submitted")
    g = _guard(chunk_dir, model, max_usd, max_tokens)
    payload = {"endpoint": "/v1/chat/completions", "model": model,
               "requests": [{"custom_id": k, "body": _request_body(v, max_tokens, effort)}
                            for k, v in g["prompts"].items()]}
    resp = post(f"{OPENROUTER}/batches", headers=_headers(), data=json.dumps(payload),
                timeout=300)
    if resp.status_code not in (200, 202):
        raise CatchupError(f"batch submit refused: http {resp.status_code} {resp.text[:300]}")
    batch = resp.json()
    meta = {"batch_id": batch["id"], "model": model, "route": "openrouter-batch",
            "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "max_tokens": max_tokens, "reasoning_effort": effort, "pricing": g["pricing"],
            "bound_usd": g["bound_usd"], "records": g["records"],
            "chunks": list(g["prompts"])}
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
        fh.write("\n")
    log.info("batch %s submitted (%s)", batch["id"], batch.get("status"))
    return meta


TERMINAL = {"completed", "failed", "expired", "cancelled"}


def collect(chunk_dir: str, suffix: str, wait: bool, poll_s: int = 60,
            get=requests.get) -> dict:
    with open(os.path.join(chunk_dir, f"{suffix}.batch.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    while True:
        resp = get(f"{OPENROUTER}/batches/{meta['batch_id']}", headers=_headers(), timeout=300)
        resp.raise_for_status()
        batch = resp.json()
        log.info("batch %s: %s %s", batch["id"], batch["status"], batch.get("request_counts"))
        if batch["status"] in TERMINAL or not wait:
            break
        time.sleep(poll_s)
    if batch["status"] != "completed":
        return {"status": batch["status"], "error": batch.get("error")}
    with open(os.path.join(chunk_dir, f"{suffix}.batch_result.json"), "w",
              encoding="utf-8") as fh:
        json.dump(batch, fh, ensure_ascii=False)
    known = set(meta["chunks"])
    lines = []
    for res in batch.get("results") or []:
        chunk = res.get("custom_id")
        if chunk not in known:
            raise CatchupError(f"batch result for unknown custom_id {chunk!r}")
        body = (res.get("response") or {}).get("body") or {}
        answered = (_write_answer(chunk_dir, chunk, suffix, _content(body), _truncated(body))
                    if body else 0)
        lines.append(usage_log(chunk, body, len(_ids(chunk_dir, chunk)), answered,
                               meta["pricing"],
                               {"route": meta["route"], "model": meta["model"],
                                "batch_id": batch["id"], "error": res.get("error")}))
    with open(os.path.join(chunk_dir, f"{suffix}.calls.jsonl"), "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in lines)
    summary = {"status": "completed", "batch_usage": batch.get("usage"), **_totals(lines)}
    log.info("collected: %s", summary)
    return summary


def call(chunk_dir: str, model: str, suffix: str, max_usd: float, max_tokens: int,
         effort: str | None, post=requests.post) -> dict:
    g = _guard(chunk_dir, model, max_usd, max_tokens)
    lines = []
    for chunk, prompt in g["prompts"].items():
        if os.path.exists(os.path.join(chunk_dir, f"{chunk}.{suffix}.txt")):
            log.info("%s: answer file exists, skipped", chunk)
            continue
        t0 = time.monotonic()
        body = {"model": model, "usage": {"include": True},
                **_request_body(prompt, max_tokens, effort)}
        resp = post(f"{OPENROUTER}/chat/completions", headers=_headers(), json=body,
                    timeout=1800)
        if resp.status_code != 200:
            raise CatchupError(f"{chunk}: http {resp.status_code} {resp.text[:300]}")
        js = resp.json()
        answered = _write_answer(chunk_dir, chunk, suffix, _content(js), _truncated(js))
        lines.append(usage_log(chunk, js, len(_ids(chunk_dir, chunk)), answered, g["pricing"],
                               {"route": "openrouter-sync", "model": model,
                                "latency_s": round(time.monotonic() - t0, 1)}))
        with open(os.path.join(chunk_dir, f"{suffix}.calls.jsonl"), "a",
                  encoding="utf-8") as fh:
            fh.write(json.dumps(lines[-1], ensure_ascii=False) + "\n")
    return _totals(lines)


def _totals(lines: list[dict]) -> dict:
    keys = ("records", "answered", "prompt_tokens", "completion_tokens", "reasoning_tokens",
            "cost_usd")
    return {k: round(sum(x[k] for x in lines), 6) for k in keys}


def count_tokens(chunk_dir: str, count_model: str, post=requests.post) -> dict:
    key = read_credential("anthropic", "ANTHROPIC_API_KEY")
    if not key:
        raise CatchupError("no Anthropic key in the keystore")
    hdr = {"x-api-key": key, "anthropic-version": "2023-06-01",
           "content-type": "application/json"}
    by_chunk = {}
    for chunk, prompt in _prompts(chunk_dir).items():
        resp = post(ANTHROPIC_COUNT, headers=hdr, timeout=120,
                    json={"model": count_model,
                          "messages": [{"role": "user", "content": prompt}]})
        if resp.status_code != 200:
            raise CatchupError(f"{chunk}: count_tokens http {resp.status_code} "
                               f"{resp.text[:200]}")
        by_chunk[chunk] = resp.json()["input_tokens"]
    out = {"count_model": count_model, "measured_at": datetime.now(timezone.utc).isoformat(),
           "by_chunk": by_chunk, "total": sum(by_chunk.values())}
    with open(os.path.join(chunk_dir, "tokens.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    return out


# ── parse ────────────────────────────────────────────────


def parse_answers(chunk_dir: str, suffix: str, model: str, run_id: str, machine: str,
                  labeller: str, prompt_sha: str, labelled_at: str,
                  source_prefix: str) -> tuple[list[dict], dict]:
    """``rel_dimensions`` rows (stage ``catchup``) for every answered record, and a report."""
    dims, report = [], {}
    for chunk in chunk_names(chunk_dir):
        ids = _ids(chunk_dir, chunk)
        answer = os.path.join(chunk_dir, f"{chunk}.{suffix}.txt")
        if not os.path.exists(answer):
            report[chunk] = {"ids": len(ids), "answered": 0, "status": "no answer file"}
            continue
        with open(answer, encoding="utf-8") as fh:
            answers, faults = ics.parse_discipline_answers(fh, ids)
        hard = [f for f in faults if "unanswered" not in f]
        if hard:
            raise CatchupError(f"{answer}: refused, {hard[:5]}")
        if answers and all(a["contrib"] == a["field"] == a["ctype"] == ics.UNKNOWN
                           for a in answers.values()):
            raise CatchupError(f"{answer}: refused, no record has a valid discipline field "
                               "(an answer file of another format?)")
        report[chunk] = {"ids": len(ids), "answered": len(answers),
                         "status": "complete" if len(answers) == len(ids) else "incomplete",
                         "unknown_dimension": sum(ics.UNKNOWN in (a["contrib"], a["field"],
                                                                  a["ctype"])
                                                  for a in answers.values()),
                         "na": sum(a["contrib"] == "na" for a in answers.values()),
                         # the wrapper asks na in all three fields or in none
                         "na_off_rule": sum(0 < [a["contrib"], a["field"], a["ctype"]].count("na")
                                            < 3 for a in answers.values())}
        for key in ids:
            if key in answers:
                a = answers[key]
                dims.append({"work_key": key, "stage": STAGE, "labeller": labeller,
                             "model": model, "prompt_sha256": prompt_sha, "run_id": run_id,
                             "machine": machine, "contrib": a["contrib"], "field": a["field"],
                             "contrib_type": a["ctype"], "labelled_at": labelled_at,
                             "source": f"{source_prefix}/{chunk}.{suffix}.txt"})
    return dims, report


def drop_already_dimensioned(dims: list[dict], existing: list[dict]) -> tuple[list[dict], int]:
    """Rows whose work has no dimension row under another key; and how many were dropped.

    Rows with the same key stay, for ``append_new`` to skip (idempotent rerun).
    """
    keys = {ics.key_of(r) for r in existing}
    other = {r["work_key"] for r in existing}
    kept = [r for r in dims if r["work_key"] not in other or ics.key_of(r) in keys]
    return kept, len(dims) - len(kept)


# ── main ─────────────────────────────────────────────────


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--pool", default=None, help="default: config pool")
    parser.add_argument("--table", default=None, help="default: config table (read only)")
    parser.add_argument("--dimensions-table", default=None,
                        help="default: config dimensions_table")
    parser.add_argument("--prompt", default=None, help="default: config catchup.prompt")
    sub = parser.add_subparsers(dest="cmd", required=True)
    # Multi-output: build writes chunk files, ids, works.csv, build.json and the
    # rendered prompts into one directory; the other commands read and write
    # next to them in that --chunk-dir.
    sub.add_parser("build").add_argument("--output-dir", required=True)
    sub.choices["build"].add_argument("--keys", default=None,
                                      help="validation mode: these work keys, in order")
    for name in ("render", "count-tokens", "submit", "collect", "call", "parse"):
        sub.add_parser(name).add_argument("--chunk-dir", required=True)
    sub.choices["count-tokens"].add_argument("--count-model", default="claude-opus-5-5")
    for name in ("submit", "call"):
        p = sub.choices[name]
        p.add_argument("--model", required=True, help="OpenRouter model id")
        p.add_argument("--suffix", required=True)
        p.add_argument("--max-usd", type=float, required=True,
                       help="refuse when the spend bound exceeds this")
        p.add_argument("--max-tokens", type=int, default=32000,
                       help="output tokens per chunk, reasoning included (also the bound)")
        p.add_argument("--reasoning-effort", default=None, help="default: the model's own")
    sub.choices["collect"].add_argument("--suffix", required=True)
    sub.choices["collect"].add_argument("--wait", action="store_true")
    pp = sub.choices["parse"]
    pp.add_argument("--suffix", required=True)
    pp.add_argument("--model", required=True)
    pp.add_argument("--run-id", required=True)
    pp.add_argument("--machine", required=True)
    pp.add_argument("--labeller", choices=sorted(ics.LABELLERS), default="llm")
    pp.add_argument("--labelled-at", default=None, help="default: today (UTC)")
    pp.add_argument("--new-table", action="store_true",
                    help="allow creating the dimensions table although a .dvc pointer tracks it")
    return parser


def _build_keys(args, cfg: dict, prompt: str, pool_path: str) -> None:
    with open(args.keys, encoding="utf-8") as fh:
        keys = [ln.strip() for ln in fh if ln.strip()]
    works = select_keys(rv.read_pool(pool_path), keys)
    manifest = {"kind": "keys", "keys": args.keys, "keys_sha256": rv.sha256_file(args.keys),
                "pool": os.path.basename(pool_path), "pool_sha256": rv.sha256_file(pool_path),
                "prompt": prompt, "prompt_sha256": ics.stage2_prompt_sha256(prompt)}
    names = ch.write_chunks(args.output_dir, works, cfg["stage2"], manifest)
    render(args.output_dir, prompt)
    log.info("build --keys: %d works in %d chunks under %s", len(works), len(names),
             args.output_dir)


def _build(args, cfg: dict, prompt: str, dims_table: str) -> None:
    pool_path, table = args.pool or cfg["pool"], args.table or cfg["table"]
    if getattr(args, "keys", None):
        return _build_keys(args, cfg, prompt, pool_path)
    ics.require_table(table)
    with_dims = {r["work_key"] for r in dimension_rows(table, dims_table, cfg["stage2"]["prompt"])}
    rule = rv.screen_rule(cfg)
    pool, view = ch.view(pool_path, table, rule)
    no_abstract = {p["work_key"] for p in pool if not (p["abstract"] or "").strip()}
    sel = select_catchup(view, cfg["catchup"]["final_labels"], with_dims, no_abstract)
    by_key = {p["work_key"]: p for p in pool}
    manifest = {"kind": "catchup", "pool": os.path.basename(pool_path),
                "pool_sha256": rv.sha256_file(pool_path),
                "table_sha256": rv.sha256_file(table),
                "prompt": prompt, "prompt_sha256": ics.stage2_prompt_sha256(prompt),
                "rule": rule, "final_labels": cfg["catchup"]["final_labels"],
                "eligible": sel["eligible"], "no_abstract": sel["no_abstract"],
                "already_with_dimensions": sel["already_with_dimensions"],
                "by_label": sel["by_label"]}
    names = ch.write_chunks(args.output_dir, [by_key[k] for k in sel["keys"]], cfg["stage2"],
                            manifest)
    render(args.output_dir, prompt)
    log.info("build: %d works %s (%d eligible, %d without abstract left out, %d already with "
             "dimensions) in %d chunks under %s", len(sel["keys"]), sel["by_label"],
             sel["eligible"], sel["no_abstract"], sel["already_with_dimensions"], len(names),
             args.output_dir)


def _parse(args, dims_table: str) -> None:
    with open(os.path.join(args.chunk_dir, "build.json"), encoding="utf-8") as fh:
        build = json.load(fh)
        selection.require_binding(build.get("assessment_selection"), allow_append=True)
        kind = build.get("kind")
    if kind == "keys" and not args.dimensions_table:
        raise CatchupError(f"{args.chunk_dir} was built with --keys (kind keys, validation): "
                           "give --dimensions-table explicitly, the default is the production "
                           "table; nothing written")
    labelled_at = args.labelled_at or datetime.now(timezone.utc).date().isoformat()
    dims, report = parse_answers(args.chunk_dir, args.suffix, args.model, args.run_id,
                                 args.machine, args.labeller, rendered_sha(args.chunk_dir),
                                 labelled_at, os.path.basename(os.path.normpath(args.chunk_dir)))
    bad = [e for r in dims for e in ics.validate_row(r, ics.DIMENSIONS)]
    if bad:
        raise CatchupError(f"dimension rows refused, nothing written: {bad[:5]}")
    dims, dropped = drop_already_dimensioned(dims, selection.read_effective_table(dims_table, ics.DIMENSIONS))
    added, skipped = ics.append_new(dims_table, dims, f"parse catchup {args.run_id}",
                                    args.new_table, ics.DIMENSIONS)
    log.info("chunks %s", report)
    log.info("%d answers: %d appended, %d already in %s, %d skipped (work already has a "
             "dimension row under another key)", len(dims) + dropped, added, skipped,
             dims_table, dropped)


def main(argv=None):
    args = _parser().parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    prompt = args.prompt or cfg["catchup"]["prompt"]
    dims_table = args.dimensions_table or cfg["dimensions_table"]
    try:
        if args.cmd in ("count-tokens", "submit", "call", "parse"):
            _check_rendered(args.chunk_dir, prompt)
        if args.cmd == "build":
            _build(args, cfg, prompt, dims_table)
        elif args.cmd == "render":
            log.info("rendered %d prompts", len(render(args.chunk_dir, prompt)))
        elif args.cmd == "count-tokens":
            res = count_tokens(args.chunk_dir, args.count_model)
            log.info("%d input tokens over %d chunks", res["total"], len(res["by_chunk"]))
        elif args.cmd == "submit":
            submit(args.chunk_dir, args.model, args.suffix, args.max_usd, args.max_tokens,
                   args.reasoning_effort)
        elif args.cmd == "collect":
            res = collect(args.chunk_dir, args.suffix, args.wait)
            if res["status"] != "completed":
                log.error("batch %s: %s", res["status"], res.get("error"))
                return 1
        elif args.cmd == "call":
            log.info("call totals: %s", call(args.chunk_dir, args.model, args.suffix,
                                             args.max_usd, args.max_tokens,
                                             args.reasoning_effort))
        else:
            _parse(args, dims_table)
    except (CatchupError, ics.IcfScreenError, ch.Stage2Error, requests.RequestException) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
