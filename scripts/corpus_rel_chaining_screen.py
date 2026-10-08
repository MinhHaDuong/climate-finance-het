"""Bounded paid execution of existing REL screening instruments.

Multiple outputs under --output-dir: immutable request/reply files, prompt
hashes and charges. Shares the citation round's cumulative budget ledger.
The existing stage-2 parser owns label/dimension validation and append.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import _icf_chunks as chunks
import _rel_view as view
import requests
import yaml
from catalog_rel_citation_chaining import (
    ChainError,
    Store,
    dump,
    exact_rekey_map,
    now,
    rows,
    sha,
)
from pipeline_keystore import read_credential
from utils import get_logger

log = get_logger("rel_chaining_screen")


def stage1(store, input_path, output_dir, max_usd):
    summary = Path(output_dir) / "summary.json"
    previous = float(json.loads(summary.read_text())["spent_usd"]) if summary.exists() else 0
    call = store.reserve("openrouter-stage1-designb", max_usd - previous, {"input": str(input_path)})
    started = now()
    proc = subprocess.run([sys.executable, "scripts/corpus_icf_stage1_designb.py", "--input", str(input_path),
                           "--output-dir", str(output_dir), "--budget-usd", str(max_usd)], check=False)
    if not summary.exists():
        raise ChainError("stage1 outcome unknown; full cap remains reserved")
    report = json.loads(summary.read_text())
    if report.get("finished", "") < started:
        raise ChainError("stage1 summary predates this invocation; liability retained")
    spent = float(report["spent_usd"]) - previous
    delta = report.get("key_usage_delta_usd_this_invocation")
    if delta is not None:
        spent = max(spent, float(delta))
    store.settle(call, spent, {"summary": str(summary), "exit_code": proc.returncode})
    if proc.returncode:
        raise ChainError(f"stage1 exit {proc.returncode}; charges settled, outputs preserved")


def build_stage2(pool_path, table_path, baseline_pool, baseline_view, config_path, output_dir):
    cfg = yaml.safe_load(Path(config_path).read_text())
    pool, graded = chunks.view(pool_path, table_path, view.screen_rule(cfg))
    mapping, unresolved = exact_rekey_map(list(rows(baseline_pool)), pool)
    if unresolved:
        raise ChainError("baseline identity migration unresolved; refuse incremental stage2 build")
    accepted = {mapping.get(r["work_key"], r["work_key"]) for r in rows(baseline_view)
                if r["status"] in {"pending_stage2", "unscreened"}}
    eligible = {r["work_key"] for r in graded if r["status"] == "pending_stage2" and r["work_key"] not in accepted}
    picked = sorted((r for r in pool if r["work_key"] in eligible and r["abstract"].strip()), key=lambda r: r["work_key"])
    no_abstract = sorted(r["work_key"] for r in pool if r["work_key"] in eligible and not r["abstract"].strip())
    manifest = {"kind": "incremental-chaining", "pool_sha256": sha(pool_path), "table_sha256": sha(table_path),
                "baseline_view_sha256": sha(baseline_view), "accepted_baseline_pending_not_reopened": len(accepted),
                "no_abstract_bibliometric_only": no_abstract}
    chunks.write_chunks(str(output_dir), picked, cfg["stage2"], manifest)
    log.info("incremental stage2: %d works, %d bibliometric-only without abstracts", len(picked), len(no_abstract))


def prompt_for(wrapper, rule, record_text):
    block = wrapper.split("```", 2)[1]
    start = block.index("This is a second-stage review")
    block = block[start:]
    block = block.replace("Write one line per record, in order, to <chunk>.opus.txt, format exactly:",
                          "Return one line per record, in order, format exactly:")
    block = block.replace("No other text in the file. Then reply with only the count of each label.",
                          "Return only these answer lines, without commentary or counts.")
    definition = rule.split("{answer_format}")[0]
    return definition + "\n" + block + "\nRecords:\n" + record_text


def stage2(store, chunk_dir, output_dir, prompt_path, model, input_price, output_price,
           max_tokens, effort, tier, post=requests.post):
    chunk_dir, output_dir = Path(chunk_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    wrapper = Path(prompt_path).read_text(encoding="utf-8")
    rule_path = Path("config/rel_sud_screen.yaml")
    rule = yaml.safe_load(rule_path.read_text())["prompt_template"]
    basis = {"wrapper_sha256": hashlib.sha256(wrapper.encode()).hexdigest(), "model": model,
             "input_usd_per_token": input_price, "output_usd_per_token": output_price,
             "max_completion_tokens": max_tokens, "effort": effort, "tier": tier}
    basis.update({"rule_sha256": hashlib.sha256(rule_path.read_bytes()).hexdigest(),
                  "pricing_verified_at": "2026-10-08", "pricing_source": "https://developers.openai.com/api/docs/models/gpt-6.1-sol",
                  "flex_source": "https://developers.openai.com/api/docs/guides/flex-processing"})
    store.bind("screen_basis", basis)
    if input_price <= 0 or output_price <= 0:
        raise ChainError("positive verified token prices required")
    api_key = read_credential("openai", "OPENAI_API_KEY")
    if not api_key:
        raise ChainError("direct OpenAI credential absent; no paid request sent")
    for path in sorted(chunk_dir.glob("chunk*.txt")):
        if "." in path.stem:
            continue
        name = path.stem
        answer = chunk_dir / f"{name}.sol.txt"
        raw = output_dir / f"{name}.reply.json"
        request_path = output_dir / f"{name}.request.json"
        prompt = prompt_for(wrapper, rule, path.read_text(encoding="utf-8"))
        # UTF-8 bytes upper-bound input tokens; full output liability is reserved.
        bound = 2 * ((len(prompt.encode("utf-8")) + 1024) * input_price + max_tokens * output_price)
        body = {"model": model, "messages": [{"role": "user", "content": prompt}],
                "reasoning_effort": effort, "service_tier": tier, "max_completion_tokens": max_tokens}
        digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        if request_path.exists() and json.loads(request_path.read_text())["request_sha256"] != digest:
            raise ChainError(f"changed chunk/request basis: {name}")
        if answer.exists():
            if not raw.exists() or not request_path.exists():
                raise ChainError(f"answer without request/reply evidence: {name}")
            continue
        if raw.exists():
            record = json.loads(raw.read_text())
        else:
            if request_path.exists():
                raise ChainError(f"{name}: unresolved prior request; reconcile before resubmission")
            call = store.reserve("openai-stage2", bound, {"chunk": name, "request_sha256": digest})
            dump(request_path, {"request_sha256": digest, "request": body, "call": call, "basis": basis})
            try:
                response = post("https://api.openai.com/v1/chat/completions", json=body,
                                headers={"Authorization": "Bearer " + api_key}, timeout=900)
            except requests.RequestException as exc:
                raise ChainError(f"{name}: ambiguous transport; liability retained") from exc
            record = {"status": response.status_code, "retrieved_at": now(), "body": response.json()}
            dump(raw, record)
        req = json.loads(request_path.read_text())
        js = record["body"]
        usage = js.get("usage") or {}
        if record["status"] != 200:
            # A rejected request with no usage is unpaid; its evidence remains.
            store.settle(req["call"], 0, {"chunk": name, "http": record["status"], "usage": usage})
            raise ChainError(f"{name}: HTTP {record['status']}; inspect archived error before retry")
        actual_tier = js.get("service_tier")
        multiplier = 1 if actual_tier == tier else 2
        cost = multiplier * (usage.get("prompt_tokens", 0) * input_price + usage.get("completion_tokens", 0) * output_price)
        store.settle(req["call"], cost, {"chunk": name, "usage": usage, "served_model": js.get("model"),
                                       "served_tier": actual_tier, "prices": basis, "cost_basis": "derived_without_cache_discount"})
        if actual_tier != tier or not usage:
            raise ChainError(f"{name}: served tier/usage cannot substantiate charge ceiling")
        choice = (js.get("choices") or [{}])[0]
        if choice.get("finish_reason") != "stop":
            raise ChainError(f"{name}: incomplete response; preserve and reconcile before retry")
        text = choice.get("message", {}).get("content") or ""
        if not text.strip():
            raise ChainError(f"{name}: empty reply")
        answer.write_text(text + "\n", encoding="utf-8")
        log.info("%s answered; charge %.5f USD", name, cost)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "stage1", "stage2"])
    parser.add_argument("--output-dir", required=True, help="multi-output execution archive")
    parser.add_argument("--budget-ledger", required=True)
    parser.add_argument("--input")
    parser.add_argument("--chunk-dir")
    parser.add_argument("--max-usd", type=float)
    parser.add_argument("--prompt")
    parser.add_argument("--model")
    parser.add_argument("--input-price", type=float)
    parser.add_argument("--output-price", type=float)
    parser.add_argument("--max-tokens", type=int, default=12000)
    parser.add_argument("--effort", default="low")
    parser.add_argument("--tier", default="flex")
    parser.add_argument("--pool")
    parser.add_argument("--table")
    parser.add_argument("--baseline-view")
    parser.add_argument("--baseline-pool")
    parser.add_argument("--config", default="config/rel_screen.yaml")
    args = parser.parse_args()
    store = Store(args.output_dir, args.budget_ledger)
    store.bind("budget_usd", 20)
    try:
        if args.action == "build":
            build_stage2(args.pool, args.table, args.baseline_pool, args.baseline_view, args.config, args.output_dir)
        elif args.action == "stage1":
            stage1(store, args.input, args.output_dir, args.max_usd)
        else:
            stage2(store, args.chunk_dir, args.output_dir, args.prompt, args.model,
                   args.input_price, args.output_price, args.max_tokens, args.effort, args.tier)
    except (ChainError, requests.RequestException) as exc:
        log.error("checkpoint preserved: %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
