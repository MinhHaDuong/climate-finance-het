"""Paid screening preserves instruments and refuses ambiguous resubmission."""

from pathlib import Path

import pytest
import yaml
from catalog_rel_citation_chaining import ChainError, Store
from corpus_rel_chaining_screen import prompt_for, stage2

pytestmark = pytest.mark.domain_corpus


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
