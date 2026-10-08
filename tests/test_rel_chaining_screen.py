"""Paid screening preserves instruments and refuses ambiguous resubmission."""

from pathlib import Path

import pytest
import yaml
from _rel_chaining import ChainError, Store, bounded_screen_post
from _rel_chaining import parse_stage1_batch_results
from corpus_rel_chaining_screen import build_stage2, prompt_for, stage2, stage2_local

pytestmark = pytest.mark.domain_corpus


def test_authorized_budget_change_is_shared_but_original_basis_is_immutable(tmp_path):
    ledger = tmp_path / "budget.sqlite"
    first, second = Store(tmp_path / "one", ledger), Store(tmp_path / "two", ledger)
    first.bind("budget_usd", 20)
    second.bind("budget_usd", 20)
    first.reserve("test", 19, {})
    with pytest.raises(ChainError, match="cumulative"):
        second.reserve("test", 2, {})
    first.authorize_budget(30, "Author explicitly approved30total")
    second.reserve("test", 10, {})
    assert second.config("budget_usd") == 20
    with pytest.raises(ChainError, match="cumulative"):
        first.reserve("test", 2, {})
    with pytest.raises(ChainError, match="existing liabilities"):
        first.authorize_budget(20, "cannot erase existing commitments")
    with pytest.raises(ChainError, match="positive cap"):
        first.authorize_budget(float("nan"), "invalid numeric authorization")
    with pytest.raises(ChainError, match="positive request"):
        first.reserve("test", float("nan"), {})


def test_batch_result_mapping_unordered_failed_and_duplicate_decisions():
    import json

    def success(ident, answers):
        return {"custom_id": ident, "result": {"type": "succeeded", "message": {
            "model": "claude-haiku-5-5", "stop_reason": "end_turn", "usage": {"input_tokens": 100, "output_tokens": 20},
            "content": [{"type": "thinking", "thinking": "private reasoning"}, {"type": "text", "text": json.dumps(answers)}]}}}

    answer = lambda n, label: {"n": n, "label": label, "doc": "research", "why": ""}
    mapping = {"a": ["work1", "work2"], "b": ["work3"], "c": ["work4"]}
    results = [success("c", [answer(1, "unsure")]), {"custom_id": "b", "result": {"type": "expired"}},
               success("a", [answer(1, "out"), answer(1, "icf"), answer(2, "aux")])]
    labels, receipts, faults = parse_stage1_batch_results(results, mapping)
    assert {(r["work_key"], r["label"]) for r in labels} == {("work2", "aux"), ("work4", "unsure")}
    assert next(r for r in receipts if r["custom_id"] == "b")["derived_cost"] == 0
    assert {k for f in faults for k in f["pending_keys"]} == {"work1", "work3"}
    with pytest.raises(ChainError, match="coverage"):
        parse_stage1_batch_results(results[:-1], mapping)
    with pytest.raises(ChainError, match="duplicate native"):
        parse_stage1_batch_results(results + results[:1], mapping)
    with pytest.raises(ChainError, match="unknown or duplicate"):
        parse_stage1_batch_results([success("unmapped", [answer(1, "out")])], mapping)


def test_local_v2_keeps_dimensions_title_only_and_native_bytes(tmp_path, monkeypatch):
    import json
    from _icf_screen import V2_FIELDS, parse_stage2_answers

    monkeypatch.setattr("corpus_rel_chaining_screen.read_credential", lambda *args: pytest.fail("local route read credential"))
    chunk_dir = tmp_path / "chunks"
    chunk_dir.mkdir()
    (chunk_dir / "chunk01.txt").write_text("1. [en] Title: Climate grants\n(no abstract)\n")
    answer = "1|icf|article|yes|yes|econ|theory|international climate grants"

    class Reply:
        status_code = 200
        text = json.dumps({"model": "qwen3.8-27b", "choices": [{"finish_reason": "stop", "message": {"content": answer}}]})

    def post(url, **kwargs):
        assert url == "http://127.0.0.1:8080/v1/chat/completions"
        prompt = kwargs["json"]["messages"][0]["content"]
        assert "(no abstract)" in prompt and "n|label|doc|studied|contrib|field|ctype|why" in prompt
        assert kwargs["json"]["chat_template_kwargs"]["enable_thinking"] is False
        return Reply()

    stage2_local(chunk_dir, tmp_path / "native", "config/rel_stage2_prompt_v2.md", post=post)
    saved = json.loads((tmp_path / "native" / "chunk01.reply.json").read_text())
    assert saved["raw_text"] == Reply.text
    assert (chunk_dir / "chunk01.qwen.txt").read_text().strip() == answer
    parsed, faults = parse_stage2_answers([answer], ["fixture"], V2_FIELDS)
    assert not faults
    assert parsed["fixture"]["label"] == "icf" and parsed["fixture"]["contrib"] == "yes"
    with pytest.raises(ChainError, match="established loopback model"):
        stage2_local(chunk_dir, tmp_path / "other", "config/rel_stage2_prompt_v2.md", model="remote-model", post=post)


def test_stage1_each_retry_reserves_full_liability_and_ambiguous_calls_stop(tmp_path):
    import requests

    ledger = tmp_path / "budget.sqlite"
    store = Store(tmp_path / "run", ledger)
    store.bind("budget_usd", 20)
    sent = []

    def post(*args, **kwargs):
        sent.append(kwargs)
        raise requests.Timeout("unknown charge")

    send = bounded_screen_post(tmp_path / "run", ledger,
                               {"gemma": {"prompt": .001, "completion": .001}}, "fake", post)
    body = {"model": "gemma", "max_tokens": 1000, "messages": []}
    with pytest.raises(ChainError, match="ambiguous"):
        send("https://example.test", body, 1)
    assert len(sent) == 1
    reserved = store.db.execute("SELECT reserve,cost FROM budget.calls").fetchone()
    assert reserved["reserve"] > 3 and reserved["cost"] is None
    expensive = dict(body, max_tokens=20000)
    with pytest.raises(ChainError, match="cumulative budget"):
        send("https://example.test", expensive, 1)
    assert len(sent) == 1


def test_inline_v2_prompt_contains_icf_definition_disciplines_and_records():
    wrapper = Path("config/rel_stage2_prompt_v2.md").read_text()
    rule = yaml.safe_load(Path("config/rel_sud_screen.yaml").read_text())["prompt_template"]
    text = prompt_for(wrapper, rule, "1. [en] Title: Unique test record")
    assert "Unique test record" in text
    assert "INTERNATIONAL" in text
    assert "n|label|doc|studied|contrib|field|ctype|why" in text
    assert "Judge the contribution, never the journal's name" in text
    assert "<chunk>" not in text
    assert "Then reply with only the count" not in text


def test_ambiguous_request_retains_liability_and_refuses_retry(tmp_path, monkeypatch):
    import requests

    monkeypatch.setattr("corpus_rel_chaining_screen.read_credential", lambda *args: "fake")
    store = Store(tmp_path / "run")
    store.bind("budget_usd", 20)
    chunks = tmp_path / "chunks"
    chunks.mkdir()
    (chunks / "chunk01.txt").write_text("1. [en] Title: Test")

    def post(*args, **kwargs):
        raise requests.Timeout("uncertain result")

    args = (store, chunks, tmp_path / "replies", "config/rel_stage2_prompt_v2.md", "gpt-6.1-sol",
            .000001, .000005, 1000, "low", "flex", post)
    with pytest.raises(ChainError, match="ambiguous transport"):
        stage2(*args)
    with pytest.raises(ChainError, match="unresolved prior request"):
        stage2(*args)
    row = store.db.execute("SELECT status,reserve,cost FROM budget.calls").fetchone()
    assert row["status"] == "reserved" and row["reserve"] > 0 and row["cost"] is None


def test_provider_error_without_billing_evidence_retains_liability(tmp_path, monkeypatch):
    monkeypatch.setattr("corpus_rel_chaining_screen.read_credential", lambda *args: "fake")
    store = Store(tmp_path / "run")
    store.bind("budget_usd", 20)
    chunk_dir = tmp_path / "chunks"
    chunk_dir.mkdir()
    (chunk_dir / "chunk01.txt").write_text("1. Title: Public record")

    class Reply:
        status_code = 500

        def json(self):
            return {"error": {"type": "server_error"}}

    with pytest.raises(ChainError, match="HTTP 500"):
        stage2(store, chunk_dir, tmp_path / "replies", "config/rel_stage2_prompt_v2.md", "gpt-6.1-sol",
               .000001, .000005, 1000, "low", "flex", lambda *args, **kwargs: Reply())
    row = store.db.execute("SELECT status,reserve,cost FROM budget.calls").fetchone()
    assert row["status"] == "reserved" and row["reserve"] > 0 and row["cost"] is None


def test_incremental_build_keeps_accepted_baseline_and_no_abstract_routes(tmp_path, monkeypatch):
    import json

    pool = [{"work_key": key, "abstract": abstract, "openalex_id": "", "doi": "", "title": key,
             "year": "2026", "language": "en", "journal": "", "affiliation_countries": ""}
            for key, abstract in [("old", "baseline"), ("new", "new abstract"), ("noabstract", "")]]
    monkeypatch.setattr("corpus_rel_chaining_screen.chunks.view", lambda *args: (
        pool, [{"work_key": r["work_key"], "status": "pending_stage2"} for r in pool]))
    baseline_view = tmp_path / "view.csv"
    baseline_view.write_text("work_key,status\nold,pending_stage2\n")
    baseline_pool = tmp_path / "pool.csv"
    baseline_pool.write_text("work_key\nold\n")
    current = tmp_path / "current.csv"
    current.write_text("dummy input hash basis")
    screen = tmp_path / "screen.csv"
    screen.write_text("dummy screen hash basis")
    out = tmp_path / "chunks"
    build_stage2(current, screen, baseline_pool, baseline_view, "config/rel_screen.yaml", out)
    assert json.loads((out / "chunk01.ids.json").read_text()) == ["new", "noabstract"]
    meta = json.loads((out / "build.json").read_text())
    assert meta["accepted_baseline_pending_not_reopened"] == 1
    assert meta["no_abstract_title_adjudication"] == ["noabstract"]


def test_family_facet_registry_refuses_stale_arbitrary_or_waived_keys(tmp_path, monkeypatch):
    import csv
    import json
    from corpus_rel_chaining_screen import build_family_facets
    from _rel_chaining import sha

    old = {"work_key": "old", "member_record_ids": "source:record", "abstract": "full", "title": "Original", "year": "2020"}
    current = dict(old, work_key="current", all_openalex_ids="W123", openalex_id="W123", doi="", language="en", journal="", affiliation_countries="")
    pool = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    for path, row in [(pool, current), (baseline, old)]:
        with path.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
    baseline_view = tmp_path / "baseline-view.csv"
    baseline_view.write_text("work_key,status\nold,out\n")
    table = tmp_path / "labels.csv"
    table.write_text("unchanged labels")
    monkeypatch.setattr("corpus_rel_chaining_screen.chunks.view", lambda *args: ([current], [{"work_key": "current", "status": "unscreened"}]))
    registry = {"pool_sha256": sha(pool), "baseline_pool_sha256": sha(baseline), "baseline_view_sha256": sha(baseline_view), "old_rows": {"old": old}, "relations": {"old": ["current"]}, "correction_keys": ["current"]}
    authority = tmp_path / "scientific-disposition.md"
    authority.write_text("specific unassessed-family release")
    registry["scientific_disposition"] = {"path": str(authority), "sha256": sha(authority)}
    registry["scientifically_unassessed_keys"] = ["current"]
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry))
    input_path, proof_path = tmp_path / "input.jsonl", tmp_path / "proof.jsonl"
    input_path.write_text(json.dumps({"work_key": "arbitrary"}) + "\n")
    proof_path.write_text("")
    with pytest.raises(ChainError, match="declared changed family"):
        build_family_facets(pool, table, baseline, baseline_view, "config/rel_screen.yaml", tmp_path / "output", registry_path, input_path, proof_path)
    registry["pool_sha256"] = "stale"
    registry_path.write_text(json.dumps(registry))
    with pytest.raises(ChainError, match="hash"):
        build_family_facets(pool, table, baseline, baseline_view, "config/rel_screen.yaml", tmp_path / "output", registry_path, input_path, proof_path)
    registry["pool_sha256"] = sha(pool)
    baseline_view.write_text("work_key,status\nold,pending_stage2\n")
    registry["baseline_view_sha256"] = sha(baseline_view)
    registry_path.write_text(json.dumps(registry))
    input_path.write_text(json.dumps({"work_key": "current"}) + "\n")
    with pytest.raises(ChainError, match="accepted baseline"):
        build_family_facets(pool, table, baseline, baseline_view, "config/rel_screen.yaml", tmp_path / "output", registry_path, input_path, proof_path)
    # The registered historical group can use complete text through the normal
    # facet renderer without admitting altered bibliographic text.
    baseline_view.write_text("work_key,status\nold,out\n")
    registry["baseline_view_sha256"] = sha(baseline_view)
    registry_path.write_text(json.dumps(registry))
    import _rel_facet_io as facets
    record = {"work_key": "current", "openalex_id": "W123", "title": current["title"], "year": "2020",
              "abstract": "full", "language": "en", "journal": "", "countries": []}
    input_path.write_text(json.dumps(record) + "\n")
    proof_path.write_text(json.dumps({"work_key": "current", "native_openalex_id": "W123",
                                     "full_sixfield_sha256": facets.proof_hash(record)}) + "\n")
    result = build_family_facets(pool, table, baseline, baseline_view, "config/rel_screen.yaml",
                                tmp_path / "output", registry_path, input_path, proof_path)
    assert result["proven"] == 1 and result["unproven"] == []
    assert result["chaining_reconciliation"]["correction_keys"] == ["current"]
    assert "full" in (tmp_path / "output" / "chunk01.txt").read_text()
    record["abstract"] = "unverified altered public text"
    input_path.write_text(json.dumps(record) + "\n")
    with pytest.raises(ChainError, match="canonical pool fields"):
        build_family_facets(pool, table, baseline, baseline_view, "config/rel_screen.yaml",
                            tmp_path / "second-output", registry_path, input_path, proof_path)
