"""Paid screening preserves instruments and refuses ambiguous resubmission."""

from pathlib import Path

import pytest
import yaml
from _rel_chaining import ChainError, Store, bounded_screen_post
from corpus_rel_chaining_screen import build_stage2, prompt_for, stage2

pytestmark = pytest.mark.domain_corpus


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
