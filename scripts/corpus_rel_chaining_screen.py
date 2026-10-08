"""Bounded paid execution of existing REL screening instruments.

Multiple outputs under --output-dir: immutable request/reply files, prompt
hashes and charges. Shares the citation round's cumulative budget ledger.
The existing stage-2 parser owns label/dimension validation and append.
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

import _icf_chunks as chunks
import _rel_view as view
import requests
import yaml
from _rel_chaining import (
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


def build_stage2(pool_path, table_path, baseline_pool, baseline_view, config_path, output_dir, correction_keys=()):
    cfg = yaml.safe_load(Path(config_path).read_text())
    pool, graded = chunks.view(pool_path, table_path, view.screen_rule(cfg))
    mapping, unresolved = exact_rekey_map(list(rows(baseline_pool)), pool)
    accepted_old = {r["work_key"] for r in rows(baseline_view)
                    if r["status"] in {"pending_stage2", "unscreened"}}
    if accepted_old & {r["old_key"] for r in unresolved}:
        raise ChainError("accepted baseline residue identity unresolved; refuse to reopen it")
    accepted = {mapping.get(key, key) for key in accepted_old}
    eligible = {r["work_key"] for r in graded if r["status"] == "pending_stage2" and r["work_key"] not in accepted}
    correction_keys = set(correction_keys)
    if correction_keys & accepted:
        raise ChainError("correction queue overlaps accepted baseline residues")
    eligible.update(correction_keys)
    picked = sorted((r for r in pool if r["work_key"] in eligible), key=lambda r: r["work_key"])
    no_abstract = sorted(r["work_key"] for r in pool if r["work_key"] in eligible and not r["abstract"].strip())
    manifest = {"kind": "incremental-chaining", "pool_sha256": sha(pool_path), "table_sha256": sha(table_path),
                "baseline_view_sha256": sha(baseline_view), "accepted_baseline_pending_not_reopened": len(accepted),
                "no_abstract_title_adjudication": no_abstract,
                "changed_family_correction_keys": sorted(correction_keys),
                "historical_unresolved_identity_rows": unresolved}
    chunks.write_chunks(str(output_dir), picked, cfg["stage2"], manifest)
    log.info("incremental stage2: %d works, %d title adjudications without abstracts", len(picked), len(no_abstract))


def build_family_facets(pool_path, table_path, baseline_pool, baseline_view, config_path,
                        output_dir, registry_path, input_path, proofs_path):
    """Normal facet rendering for exact changed families, never a pending bypass.

    Recompute source-member relations against the frozen baseline and current
    pool. Historical waived residues cannot be reopened by a correction roster.
    """
    import _rel_facet_io as facets

    registry = json.loads(Path(registry_path).read_text())
    for field, path in (("pool_sha256", pool_path), ("baseline_pool_sha256", baseline_pool),
                        ("baseline_view_sha256", baseline_view)):
        if registry.get(field) != sha(path):
            raise ChainError(f"changed-family registry {field} hash mismatch")
    old_records = registry["old_rows"]
    accepted_keys = {r["work_key"] for r in rows(baseline_view)
                     if r["status"] in {"pending_stage2", "unscreened"}}
    baseline = {r["work_key"]: r for r in rows(baseline_pool)
                if r["work_key"] in set(old_records) | accepted_keys}
    if any(baseline.get(key) != record for key, record in old_records.items()):
        raise ChainError("changed-family registry differs from exact baseline rows")
    members = lambda r: {m for m in r.get("member_record_ids", "").split(";") if m}
    target_members = set().union(*(members(r) for r in baseline.values()))
    by_member, current = {}, {}
    for record in rows(pool_path):
        relevant = members(record) & target_members
        if relevant:
            current[record["work_key"]] = record
        for member in relevant:
            by_member.setdefault(member, set()).add(record["work_key"])
    relations = {key: sorted(set().union(*(by_member.get(m, set()) for m in members(record))))
                 for key, record in old_records.items()}
    if (any(not members(r) for r in old_records.values())
            or relations != registry["relations"]
            or sorted(set().union(*(set(v) for v in relations.values()))) != sorted(registry["correction_keys"])):
        raise ChainError("changed-family registry lacks exact declared member relations")
    accepted_current = set()
    for key in accepted_keys:
        if key not in baseline:
            raise ChainError("accepted baseline residue identity unresolved")
        candidates = set().union(*(by_member.get(m, set()) for m in members(baseline[key])))
        if not candidates:
            raise ChainError("accepted baseline residue identity unresolved")
        accepted_current.update(candidates)
    records = [json.loads(line) for line in Path(input_path).read_text().split("\n") if line]
    keys = {r["work_key"] for r in records}
    if not records or len(keys) != len(records) or not keys <= set(registry["correction_keys"]):
        raise ChainError("facet reconciliation requires an exact declared changed family")
    if keys & accepted_current:
        raise ChainError("correction queue overlaps accepted baseline residues")
    for record in records:
        source = current[record["work_key"]]
        public = {f: source.get(f, "").replace("\r\n", "\n").replace("\r", "\n")
                  for f in facets.PUBLIC_FIELDS if f != "countries"}
        public["countries"] = [c.strip() for c in source.get("affiliation_countries", "").split(";") if c.strip()]
        if facets.public_record(record) != public:
            raise ChainError("facet reconciliation input differs from complete canonical pool fields")
    proofs = [json.loads(line) for line in Path(proofs_path).read_text().split("\n") if line]
    cfg = yaml.safe_load(Path(config_path).read_text())
    manifest = facets.write_chunks(str(output_dir), records, proofs, cfg["stage2_facets"],
                                    {key: facets.family_source_ids(current[key]) for key in keys})
    manifest["chaining_reconciliation"] = {"registry_sha256": sha(registry_path),
        "pool_sha256": sha(pool_path), "table_sha256": sha(table_path),
        "baseline_pool_sha256": sha(baseline_pool), "baseline_view_sha256": sha(baseline_view),
        "correction_keys": sorted(keys), "accepted_baseline_not_reopened": len(accepted_keys)}
    dump(Path(output_dir) / "build.json", manifest)
    return manifest


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


def stage2_local(chunk_dir, output_dir, prompt_path, model="qwen3.8-27b", max_tokens=12000,
                 post=requests.post):
    """Run the unchanged v2 instrument through the configured loopback server.

    Local predictions are a method substitution, not independent adjudication.
    Validation callers keep their outputs separate from authoritative tables.
    """
    cfg_path = Path("config/rel_sud_screen.yaml")
    cfg = yaml.safe_load(cfg_path.read_text())
    local = cfg["local"]
    if local["api_base"].rstrip("/") != "http://127.0.0.1:8080/v1" or model != local["model"]:
        raise ChainError("local stage2 requires the established loopback model; no remote fallback")
    chunk_dir, output_dir = Path(chunk_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    wrapper = Path(prompt_path).read_text(encoding="utf-8")
    basis = {"route": "local-only", "model": model, "config_sha256": sha(cfg_path),
             "wrapper_sha256": sha(prompt_path), "max_tokens": max_tokens,
             "method": "approved local Qwen v2 substitution; same-model stages"}
    dump(output_dir / "local_basis.json", basis)
    for path in sorted(chunk_dir.glob("chunk*.txt")):
        if "." in path.stem:
            continue
        name = path.stem
        answer = chunk_dir / f"{name}.qwen.txt"
        raw = output_dir / f"{name}.reply.json"
        request_path = output_dir / f"{name}.request.json"
        rendered = chunk_dir / f"{name}.prompt.txt"
        prompt = rendered.read_text(encoding="utf-8") if rendered.exists() else prompt_for(
            wrapper, cfg["prompt_template"], path.read_text(encoding="utf-8"))
        body = {"model": model, "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens, **local.get("request_extra", {})}
        digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        if request_path.exists() and json.loads(request_path.read_text())["request_sha256"] != digest:
            raise ChainError(f"changed local chunk/request basis: {name}")
        if answer.exists():
            if not raw.exists() or not request_path.exists():
                raise ChainError(f"local answer without native evidence: {name}")
            continue
        if not raw.exists():
            if request_path.exists():
                raise ChainError(f"{name}: unresolved local request; inspect before resubmission")
            dump(request_path, {"request_sha256": digest, "request": body, "basis": basis, "started_at": now()})
            started = time.monotonic()
            response = post(local["api_base"].rstrip("/") + "/chat/completions", json=body, timeout=900)
            # Preserve exact response bytes before decoding even malformed JSON.
            dump(raw, {"status": response.status_code, "retrieved_at": now(),
                       "elapsed_seconds": time.monotonic() - started, "raw_text": response.text})
        record = json.loads(raw.read_text())
        if record["status"] != 200:
            raise ChainError(f"{name}: local HTTP {record['status']}; native response retained")
        js = json.loads(record["raw_text"])
        if js.get("model") != model:
            raise ChainError(f"{name}: unexpected local served model")
        choice = (js.get("choices") or [{}])[0]
        text = choice.get("message", {}).get("content") or ""
        if choice.get("finish_reason") != "stop" or not text.strip():
            raise ChainError(f"{name}: incomplete local response; inspect native evidence")
        answer.write_text(text + "\n", encoding="utf-8")
        log.info("%s answered locally", name)


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
        rendered = chunk_dir / f"{name}.prompt.txt"
        prompt = rendered.read_text(encoding="utf-8") if rendered.exists() else prompt_for(
            wrapper, rule, path.read_text(encoding="utf-8"))
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
            # Only documented Flex rejection is known to be unpaid. Unknown
            # provider failures retain the full liability pending evidence.
            error = js.get("error") or {}
            if record["status"] == 429 and error.get("type") == "resource_unavailable":
                store.settle(req["call"], 0, {"chunk": name, "http": 429, "usage": usage,
                                             "disposition": "documented uncharged Flex ResourceUnavailable"})
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
    parser.add_argument("action", choices=["build", "build-family-facets", "stage2", "stage2-local"])
    parser.add_argument("--output-dir", required=True, help="multi-output execution archive")
    parser.add_argument("--budget-ledger", required=True)
    parser.add_argument("--input")
    parser.add_argument("--chunk-dir")
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
    parser.add_argument("--correction-keys", help="archived changed-family relations JSON, correction_keys field")
    parser.add_argument("--public-proofs", help="complete full-field public source proofs")
    parser.add_argument("--reconciliation-registry", help="exact source-member relations with pool/baseline hashes")
    parser.add_argument("--config", default="config/rel_screen.yaml")
    args = parser.parse_args()
    if args.action == "build-family-facets":
        try:
            build_family_facets(args.pool, args.table, args.baseline_pool, args.baseline_view,
                                args.config, args.output_dir, args.reconciliation_registry,
                                args.input, args.public_proofs)
        except (ChainError, ValueError) as exc:
            log.error("reconciliation refused: %s", exc)
            return 2
        return 0
    if args.action == "stage2-local":
        stage2_local(args.chunk_dir, args.output_dir, args.prompt, args.model or "qwen3.8-27b", args.max_tokens)
        return 0
    store = Store(args.output_dir, args.budget_ledger)
    store.bind("budget_usd", 20)
    try:
        if args.action == "build":
            corrections = json.loads(Path(args.correction_keys).read_text())["correction_keys"] if args.correction_keys else []
            build_stage2(args.pool, args.table, args.baseline_pool, args.baseline_view, args.config, args.output_dir, corrections)
        else:
            stage2(store, args.chunk_dir, args.output_dir, args.prompt, args.model,
                   args.input_price, args.output_price, args.max_tokens, args.effort, args.tier)
    except (ChainError, requests.RequestException) as exc:
        log.error("checkpoint preserved: %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
