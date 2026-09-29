"""First-pass ICF relevance screen for the REL south-and-languages candidates (ticket 1530).

Reads the deduplicated candidate list, asks an LLM to label batches of records
against the ICF rule in ``config/rel_sud_screen.yaml`` and appends one result
per work to a JSONL file. Resumable: works already labelled are skipped, and
records whose label could not be parsed are left unlabelled so a rerun retries
them. A header line in ``screen_run.json`` records model, prompt hash and date.

Usage:
    python scripts/rel_sud_screen.py --input screen_input.jsonl \
        --output-dir data/rel_sud/screen1 [--limit 200] [--sample-seed 7]
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
import yaml
from syllabi_io import llm_call
from utils import get_logger

log = get_logger("rel_sud_screen")

LABELS = {"icf", "aux", "out", "unsure"}
DOCS = {"research", "institutional", "other"}


def format_record(n, rec, cfg):
    title = (rec.get("title") or "")[: cfg["title_max_chars"]]
    abstract = (rec.get("abstract") or "")[: cfg["abstract_max_chars"]] or "(no abstract)"
    where = ", ".join(rec.get("countries") or []) or "?"
    return (f"{n}. [{rec.get('language') or '?'} | {rec.get('year') or '?'} | "
            f"{rec.get('journal') or '?'} | affiliations: {where}]\n"
            f"   Title: {title}\n   Abstract: {abstract}")


def build_prompt(batch, cfg):
    records = "\n".join(format_record(i, r, cfg) for i, r in enumerate(batch, 1))
    return (cfg["prompt_template"].replace("{answer_format}", cfg["answer_format"])
            .replace("{records}", records))


def extract_list(text):
    """The JSON list in a reply, or None. The shared extractor tries `{` first,
    so a one-item list would come back as a bare object."""
    if not text:
        return None
    lo, hi = text.find("["), text.rfind("]")
    if lo == -1 or hi <= lo:
        return None
    try:
        data = json.loads(text[lo:hi + 1])
    except ValueError:
        return None
    return data if isinstance(data, list) else None


_LINE = re.compile(r"^\s*(\d+)\s*\|\s*(\w+)\s*\|\s*(\w+)\s*(?:\|(.*))?$")


def extract_lines(text):
    """Records from `n|label|doc|why` lines, as the dicts the JSON form yields."""
    items = []
    for line in (text or "").splitlines():
        m = _LINE.match(line)
        if m:
            items.append({"n": int(m.group(1)), "label": m.group(2),
                          "doc": m.group(3), "why": (m.group(4) or "").strip()})
    return items


def parse_answer(text, batch):
    """{openalex_id: result} for the records the answer labels validly."""
    data = extract_list(text) or extract_lines(text)
    out = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        n = item.get("n")
        if not isinstance(n, int) or not 1 <= n <= len(batch):
            continue
        label, doc = item.get("label"), item.get("doc")
        if label in LABELS and doc in DOCS:
            out[batch[n - 1]["openalex_id"]] = {
                "label": label, "doc": doc, "why": str(item.get("why", ""))[:160]}
    return out


def make_call(cfg):
    """OpenRouter through litellm by default; a llama-server when `api_base` is set.

    The local model thinks by default and a 20-record batch then spends the
    whole token budget on reasoning (0 of 20 parsed at 4000 tokens, 132 s);
    `request_extra` carries the per-request switch that turns it off.
    """
    if not cfg.get("api_base"):
        return llm_call

    def local_call(prompt, model, max_tokens):
        body = {"model": model, "temperature": 0, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                **cfg.get("request_extra", {})}
        try:
            resp = requests.post(cfg["api_base"].rstrip("/") + "/chat/completions",
                                 json=body, timeout=cfg.get("timeout", 900))
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"].get("content")
        except (requests.RequestException, KeyError, ValueError) as exc:
            log.error("local LLM call failed: %s", type(exc).__name__)
            return None

    return local_call


def screen_batch(batch, cfg, call=llm_call):
    reply = call(build_prompt(batch, cfg), model=cfg["model"], max_tokens=cfg["max_tokens"])
    return parse_answer(reply, batch)


def select_records(path, done, limit, seed):
    with open(path, encoding="utf-8") as fh:
        recs = [r for r in map(json.loads, fh) if r["openalex_id"] not in done]
    if limit and limit < len(recs):
        recs = random.Random(seed).sample(recs, limit)
    return recs


def run(cfg, args, call=None):
    call = call or make_call(cfg)
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "screen.jsonl")
    done = set()
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            done = {json.loads(line)["openalex_id"] for line in fh}
    recs = select_records(args.input, done, args.limit, args.sample_seed)
    size = cfg["batch_size"]
    batches = [recs[i:i + size] for i in range(0, len(recs), size)]
    with open(os.path.join(args.output_dir, "screen_run.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "model": cfg["model"], "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "prompt_sha256": hashlib.sha256(cfg["prompt_template"].encode()).hexdigest(),
            "input": args.input, "n_todo": len(recs), "n_batches": len(batches)}, fh, indent=1)
    by_id = {r["openalex_id"]: r for r in recs}
    n_ok = n_lost = 0
    with open(out_path, "a", encoding="utf-8") as out, \
            ThreadPoolExecutor(max_workers=cfg["workers"]) as pool:
        for batch, res in zip(batches, pool.map(lambda b: screen_batch(b, cfg, call), batches)):
            for oid, r in res.items():
                out.write(json.dumps({"openalex_id": oid, "title": by_id[oid]["title"],
                                      **r}, ensure_ascii=False) + "\n")
            out.flush()
            n_ok += len(res)
            n_lost += len(batch) - len(res)
    log.info("labelled %d, unlabelled %d (rerun to retry)", n_ok, n_lost)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="config/rel_sud_screen.yaml")
    ap.add_argument("--input", required=True)
    # Multi-output script (labels plus a run header): --output-dir, not --output.
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--limit", type=int, default=0, help="random sample size (0 = all)")
    ap.add_argument("--sample-seed", type=int, default=7)
    ap.add_argument("--backend", choices=["openrouter", "local"], default="openrouter",
                    help="local applies the `local:` block of the config (llama-server)")
    args = ap.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if args.backend == "local":
        cfg.update(cfg["local"])
    return run(cfg, args)


if __name__ == "__main__":
    sys.exit(main())
