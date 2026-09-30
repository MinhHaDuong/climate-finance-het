"""Family-relevance judge for the REL causal-map lane (ticket 1652).

Labels each (work, family or theme) pair of ``judge_input.jsonl`` (written by
``corpus_rel_causal_yield.py``) as relevant / not / unsure to the mechanism
the search targeted, with a cheap model. This measures lane yield; it is NOT
the ICF inclusion screen, which ticket 1655 runs once over the whole pool.

Resumable: labelled pairs are skipped and unparsed ones retried on a rerun.
``judge_runs.jsonl`` records model, backend, prompt SHA-256 and date.

Usage:
    python scripts/corpus_rel_causal_judge.py --input judge_input.jsonl \
        --output-dir JUDGE_DIR [--limit 200]
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import yaml
from corpus_rel_sud_screen import extract_list, format_record, make_call
from utils import get_logger

log = get_logger("rel_causal_judge")

LABELS = {"relevant", "not", "unsure"}


def build_prompt(batch, cfg):
    records = "\n".join(format_record(i, r, cfg) for i, r in enumerate(batch, 1))
    first = batch[0]
    return (cfg["prompt_template"].replace("{answer_format}", cfg["answer_format"])
            .replace("{question}", first["question"])
            .replace("{mechanism}", first["mechanism"])
            .replace("{records}", records))


_LINE = re.compile(r"^\s*(\d+)\s*\|\s*(\w+)\s*(?:\|(.*))?$")


def extract_lines(text):
    """Records from `n|label|why` lines, as the dicts the JSON form yields."""
    return [{"n": int(m.group(1)), "label": m.group(2), "why": (m.group(3) or "").strip()}
            for line in (text or "").splitlines() if (m := _LINE.match(line))]


def parse_answer(text, batch):
    """{pair_id: result} for the records the answer labels validly (JSON list
    or one `n|label|why` line per record)."""
    out = {}
    for item in extract_list(text) or extract_lines(text):
        if not isinstance(item, dict):
            continue
        n = item.get("n")
        if not isinstance(n, int) or not 1 <= n <= len(batch):
            continue
        label = str(item.get("label", "")).strip().lower()
        if label in LABELS:
            out[batch[n - 1]["pair_id"]] = {"label": label, "why": str(item.get("why", ""))[:160]}
    return out


def batches_by_question(recs, size):
    """Batches never mix questions: the prompt states one mechanism."""
    groups = defaultdict(list)
    for r in recs:
        groups[r["question"]].append(r)
    out = []
    for q in sorted(groups):
        g = groups[q]
        out += [g[i:i + size] for i in range(0, len(g), size)]
    return out


def run(cfg, args, call=None):
    call = call or make_call(cfg)
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "labels.jsonl")
    done = set()
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["pair_id"])
                except (ValueError, KeyError):
                    log.warning("skipping an unreadable line in %s", out_path)
    with open(args.input, encoding="utf-8") as fh:
        recs = [r for r in map(json.loads, fh) if r["pair_id"] not in done]
    if args.limit:
        recs = recs[: args.limit]
    batches = batches_by_question(recs, cfg["batch_size"])
    prompt_sha = hashlib.sha256((cfg["prompt_template"] + "\n" + cfg["answer_format"]).encode()).hexdigest()
    with open(os.path.join(args.output_dir, "judge_runs.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "model": cfg["model"], "backend": "local" if cfg.get("api_base") else "openrouter",
            "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "prompt_sha256": prompt_sha, "input": args.input,
            "n_todo": len(recs), "n_batches": len(batches),
            "note": "family-relevance judgment for lane yield, not the ICF inclusion screen"}) + "\n")

    def one(batch):
        reply = call(build_prompt(batch, cfg), model=cfg["model"], max_tokens=cfg["max_tokens"])
        return parse_answer(reply, batch)

    n_ok = n_lost = 0
    with open(out_path, "a", encoding="utf-8") as out, \
            ThreadPoolExecutor(max_workers=cfg["workers"]) as pool:
        for batch, res in zip(batches, pool.map(one, batches)):
            for pid, r in res.items():
                out.write(json.dumps({"pair_id": pid, **r, "model": cfg["model"]},
                                     ensure_ascii=False) + "\n")
            out.flush()
            n_ok += len(res)
            n_lost += len(batch) - len(res)
    log.info("labelled %d, unlabelled %d (rerun to retry)", n_ok, n_lost)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="config/rel_causal_judge.yaml")
    ap.add_argument("--input", required=True)
    # Multi-output script (labels plus run headers): --output-dir.
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return run(cfg, args)


if __name__ == "__main__":
    sys.exit(main())
