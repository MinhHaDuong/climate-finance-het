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
    is in ``catchup.final_labels`` and whose work key has no ``rel_dimensions``
    row yet, sorted by work key, in stage-2 chunks (``chunkNN.txt``,
    ``chunkNN.ids.json``, ``works.csv``, ``build.json`` with the counts), each
    rendered as ``chunkNN.prompt.txt``.

``render``
    Writes ``chunkNN.prompt.txt`` (the wrapper with the chunk's records) next
    to each ``chunkNN.txt`` of a chunk directory built elsewhere (a test set).
    The rendered prompt is the instrument for every route: an OpenRouter call
    sends it as the user message; a Claude Code subagent is told to follow it
    and write its reply to ``chunkNN.<suffix>.txt``.

``count-tokens``
    Input tokens of every rendered prompt, measured with the Anthropic
    ``count_tokens`` endpoint (free; ``--count-model``), to ``tokens.json``.

``submit`` / ``collect``
    OpenRouter Batch API (``POST /api/v1/batches``, asynchronous, 24-hour
    window, about half the synchronous price on ``:batch`` endpoints): one
    request per chunk, ``custom_id`` = chunk name. ``submit`` refuses when the
    estimated cost exceeds ``--max-usd``. ``collect`` polls once (``--wait`` to
    poll until terminal), then writes the raw batch object, each answer file
    ``chunkNN.<suffix>.txt`` and ``<suffix>.calls.jsonl``.

``call``
    The same requests through the synchronous ``/chat/completions`` endpoint,
    for a model or a run without batch.

``parse``
    Reads ``chunkNN.<suffix>.txt`` (``n|contrib|field|ctype|why``) and appends
    the rows to ``rel_dimensions`` under stage ``catchup``, with the model, run
    id and machine given. A chunk with a malformed or duplicated line, or with
    no valid discipline value at all (an answer file of another format), is
    refused; nothing is written unless every row validates. Idempotent.

Token and cost log (``<suffix>.calls.jsonl``, one line per chunk): records,
answered, prompt, completion and reasoning tokens, cost (``cost_source``:
``reported`` by OpenRouter, or ``derived`` from the model's listed per-token
price when the response carries no cost), cost per answered record. The model
is a parameter everywhere: the catch-up must use the model forward stage 2 uses.

Usage:
    python scripts/corpus_rel_discipline_catchup.py build --output-dir DIR
    python scripts/corpus_rel_discipline_catchup.py render --chunk-dir DIR
    python scripts/corpus_rel_discipline_catchup.py count-tokens --chunk-dir DIR
    python scripts/corpus_rel_discipline_catchup.py submit --chunk-dir DIR --model M \\
        --suffix S --max-usd X
    python scripts/corpus_rel_discipline_catchup.py collect --chunk-dir DIR --suffix S [--wait]
    python scripts/corpus_rel_discipline_catchup.py call --chunk-dir DIR --model M --suffix S \\
        --max-usd X
    python scripts/corpus_rel_discipline_catchup.py parse --chunk-dir DIR --model M --run-id R \\
        --machine padme [--suffix S]
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import _icf_chunks as ch
import _icf_screen as ics
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


class CatchupError(Exception):
    """A refused build, request or parse."""


# ── selection ────────────────────────────────────────────


def select_catchup(view_rows: list[dict], final_labels: list[str], with_dims: set) -> dict:
    """Work keys to catch up, sorted, and the counts behind the selection."""
    statuses = {s for s, lab in ch.FINAL_STAGE2.items() if lab in final_labels}
    eligible = sorted(r["work_key"] for r in view_rows if r["status"] in statuses)
    keys = [k for k in eligible if k not in with_dims]
    return {"keys": keys, "eligible": len(eligible),
            "already_with_dimensions": len(eligible) - len(keys)}


# ── prompts ──────────────────────────────────────────────


def chunk_names(chunk_dir: str) -> list[str]:
    return sorted(m.group(1) for m in map(_CHUNK.match, os.listdir(chunk_dir)) if m)


def render(chunk_dir: str, template: str) -> list[str]:
    """``chunkNN.prompt.txt`` for every chunk: the wrapper with the chunk's records."""
    names = chunk_names(chunk_dir)
    for name in names:
        with open(os.path.join(chunk_dir, f"{name}.txt"), encoding="utf-8") as fh:
            records = fh.read().rstrip("\n")
        with open(os.path.join(chunk_dir, f"{name}.prompt.txt"), "w", encoding="utf-8") as fh:
            fh.write(template.replace("{records}", records) + "\n")
    return names


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
    """Listed USD per token of an OpenRouter model id (``prompt``, ``completion``)."""
    resp = get(f"{OPENROUTER}/models", timeout=60)
    resp.raise_for_status()
    for m in resp.json()["data"]:
        if m["id"] == model:
            p = m["pricing"]
            return {"prompt": float(p["prompt"]), "completion": float(p["completion"])}
    raise CatchupError(f"{model} is not in the OpenRouter model list")


def estimate_usd(prompts: dict, n_records: int, pricing: dict, out_per_record: int,
                 tokens: dict | None = None) -> float:
    """Upper-side estimate for the spend guard: measured input tokens when known."""
    inp = sum((tokens or {}).get(k) or len(v) / CHARS_PER_TOKEN_FLOOR for k, v in prompts.items())
    return inp * pricing["prompt"] + n_records * out_per_record * pricing["completion"]


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


def _write_answer(chunk_dir: str, chunk: str, suffix: str, text: str) -> int:
    """Write the reply verbatim as the answer file; return how many records it answers."""
    with open(os.path.join(chunk_dir, f"{chunk}.{suffix}.txt"), "w", encoding="utf-8") as fh:
        fh.write(text if text.endswith("\n") or not text else text + "\n")
    answers, _ = ics.parse_discipline_answers(text.splitlines(), _ids(chunk_dir, chunk))
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


def _guard(chunk_dir: str, model: str, max_usd: float, out_per_record: int) -> dict:
    prompts = _prompts(chunk_dir)
    n = sum(len(_ids(chunk_dir, k)) for k in prompts)
    tokens = None
    tok_path = os.path.join(chunk_dir, "tokens.json")
    if os.path.exists(tok_path):
        with open(tok_path, encoding="utf-8") as fh:
            tokens = json.load(fh)["by_chunk"]
    pricing = model_pricing(model)
    est = estimate_usd(prompts, n, pricing, out_per_record, tokens)
    if est > max_usd:
        raise CatchupError(f"estimated {est:.3f} USD for {n} records exceeds --max-usd "
                           f"{max_usd}; nothing sent")
    log.info("%d records in %d chunks, estimated %.3f USD (cap %.2f)", n, len(prompts), est,
             max_usd)
    return {"prompts": prompts, "pricing": pricing, "estimate_usd": round(est, 4), "records": n}


# ── routes ───────────────────────────────────────────────


def submit(chunk_dir: str, model: str, suffix: str, max_usd: float, max_tokens: int,
           effort: str | None, out_per_record: int, post=requests.post) -> dict:
    meta_path = os.path.join(chunk_dir, f"{suffix}.batch.json")
    if os.path.exists(meta_path):
        raise CatchupError(f"{meta_path} exists: this suffix was already submitted")
    g = _guard(chunk_dir, model, max_usd, out_per_record)
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
            "estimate_usd": g["estimate_usd"], "records": g["records"],
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
    lines = []
    for res in batch["results"]:
        chunk = res["custom_id"]
        n = len(_ids(chunk_dir, chunk))
        body = (res.get("response") or {}).get("body") or {}
        answered = _write_answer(chunk_dir, chunk, suffix, _content(body)) if body else 0
        lines.append(usage_log(chunk, body, n, answered, meta["pricing"],
                               {"route": meta["route"], "model": meta["model"],
                                "batch_id": batch["id"], "error": res.get("error")}))
    _write_calls(chunk_dir, suffix, lines)
    summary = {"status": "completed", "batch_usage": batch.get("usage"), **_totals(lines)}
    log.info("collected: %s", summary)
    return summary


def call(chunk_dir: str, model: str, suffix: str, max_usd: float, max_tokens: int,
         effort: str | None, out_per_record: int, post=requests.post) -> dict:
    g = _guard(chunk_dir, model, max_usd, out_per_record)
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
        n = len(_ids(chunk_dir, chunk))
        answered = _write_answer(chunk_dir, chunk, suffix, _content(js))
        lines.append(usage_log(chunk, js, n, answered, g["pricing"],
                               {"route": "openrouter-sync", "model": model,
                                "latency_s": round(time.monotonic() - t0, 1)}))
        _write_calls(chunk_dir, suffix, lines[-1:])
    return _totals(lines)


def _write_calls(chunk_dir: str, suffix: str, lines: list[dict]) -> None:
    with open(os.path.join(chunk_dir, f"{suffix}.calls.jsonl"), "a", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")


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
                         # the wrapper offers yes/no/unsure only: na is off the rule
                         "na_off_rule": sum(a["contrib"] == "na" for a in answers.values())}
        for key in ids:
            if key in answers:
                a = answers[key]
                dims.append({"work_key": key, "stage": STAGE, "labeller": labeller,
                             "model": model, "prompt_sha256": prompt_sha, "run_id": run_id,
                             "machine": machine, "contrib": a["contrib"], "field": a["field"],
                             "contrib_type": a["ctype"], "labelled_at": labelled_at,
                             "source": f"{source_prefix}/{chunk}.{suffix}.txt"})
    return dims, report


# ── main ─────────────────────────────────────────────────


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--pool", default=None, help="default: config pool")
    parser.add_argument("--table", default=None, help="default: config table (read only)")
    parser.add_argument("--dimensions-table", default=None,
                        help="default: config dimensions_table")
    parser.add_argument("--prompt", default=None, help="default: config catchup.prompt")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").add_argument("--output-dir", required=True)
    for name in ("render", "count-tokens", "submit", "collect", "call", "parse"):
        sub.add_parser(name).add_argument("--chunk-dir", required=True)
    sub.choices["count-tokens"].add_argument("--count-model", default="claude-opus-5-5")
    for name in ("submit", "call"):
        p = sub.choices[name]
        p.add_argument("--model", required=True, help="OpenRouter model id")
        p.add_argument("--suffix", required=True)
        p.add_argument("--max-usd", type=float, required=True, help="refuse above this estimate")
        p.add_argument("--max-tokens", type=int, default=32000)
        p.add_argument("--reasoning-effort", default=None, help="default: the model's own")
        p.add_argument("--est-out-per-record", type=int, default=400,
                       help="output tokens per record (reasoning included) for the estimate")
    sub.choices["collect"].add_argument("--suffix", required=True)
    sub.choices["collect"].add_argument("--wait", action="store_true")
    pp = sub.choices["parse"]
    pp.add_argument("--model", required=True)
    pp.add_argument("--run-id", required=True)
    pp.add_argument("--machine", required=True)
    pp.add_argument("--suffix", default="opus")
    pp.add_argument("--labeller", choices=sorted(ics.LABELLERS), default="llm")
    pp.add_argument("--labelled-at", default=None, help="default: today (UTC)")
    pp.add_argument("--new-table", action="store_true",
                    help="allow creating the dimensions table although a .dvc pointer tracks it")
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    prompt = args.prompt or cfg["catchup"]["prompt"]
    dims_table = args.dimensions_table or cfg["dimensions_table"]
    try:
        template = ics.catchup_prompt_template(prompt)
        if args.cmd == "build":
            pool_path, table = args.pool or cfg["pool"], args.table or cfg["table"]
            ics.require_table(table)
            rule = rv.screen_rule(cfg)
            pool, view = ch.view(pool_path, table, rule)
            with_dims = {r["work_key"] for r in ics.read_table(dims_table, ics.DIMENSIONS)}
            sel = select_catchup(view, cfg["catchup"]["final_labels"], with_dims)
            by_key = {p["work_key"]: p for p in pool}
            manifest = {"kind": "catchup", "pool": os.path.basename(pool_path),
                        "pool_sha256": rv.sha256_file(pool_path),
                        "table_sha256": rv.sha256_file(table),
                        "prompt": prompt, "prompt_sha256": ics.stage2_prompt_sha256(prompt),
                        "rule": rule, "final_labels": cfg["catchup"]["final_labels"],
                        "eligible": sel["eligible"],
                        "already_with_dimensions": sel["already_with_dimensions"]}
            names = ch.write_chunks(args.output_dir, [by_key[k] for k in sel["keys"]],
                                    cfg["stage2"], manifest)
            render(args.output_dir, template)
            log.info("build: %d works (%d eligible, %d already with dimensions) in %d chunks "
                     "under %s", len(sel["keys"]), sel["eligible"],
                     sel["already_with_dimensions"], len(names), args.output_dir)
        elif args.cmd == "render":
            log.info("rendered %d prompts", len(render(args.chunk_dir, template)))
        elif args.cmd == "count-tokens":
            res = count_tokens(args.chunk_dir, args.count_model)
            log.info("%d input tokens over %d chunks", res["total"], len(res["by_chunk"]))
        elif args.cmd == "submit":
            submit(args.chunk_dir, args.model, args.suffix, args.max_usd, args.max_tokens,
                   args.reasoning_effort, args.est_out_per_record)
        elif args.cmd == "collect":
            res = collect(args.chunk_dir, args.suffix, args.wait)
            if res["status"] != "completed":
                log.error("batch %s: %s", res["status"], res.get("error"))
                return 1
        elif args.cmd == "call":
            log.info("call totals: %s", call(args.chunk_dir, args.model, args.suffix,
                                             args.max_usd, args.max_tokens,
                                             args.reasoning_effort, args.est_out_per_record))
        else:
            labelled_at = args.labelled_at or datetime.now(timezone.utc).date().isoformat()
            dims, report = parse_answers(
                args.chunk_dir, args.suffix, args.model, args.run_id, args.machine,
                args.labeller, ics.stage2_prompt_sha256(prompt), labelled_at,
                os.path.basename(os.path.normpath(args.chunk_dir)))
            bad = [e for r in dims for e in ics.validate_row(r, ics.DIMENSIONS)]
            if bad:
                raise CatchupError(f"dimension rows refused, nothing written: {bad[:5]}")
            added, skipped = ics.append_new(dims_table, dims, f"parse catchup {args.run_id}",
                                            args.new_table, ics.DIMENSIONS)
            log.info("chunks %s", report)
            log.info("%d answers, %d appended, %d already in %s", len(dims), added, skipped,
                     dims_table)
    except (CatchupError, ics.IcfScreenError, ch.Stage2Error, requests.RequestException) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
