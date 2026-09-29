"""The REL screen: strict parsing, resumable output, no silent label loss."""

import json
import os
import types

import pytest
import rel_sud_screen as sc
import yaml

pytestmark = pytest.mark.wp_corpus

ROOT = os.path.dirname(os.path.dirname(__file__))


def _cfg():
    with open(os.path.join(ROOT, "config", "rel_sud_screen.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _recs(n):
    return [{"openalex_id": f"W{i}", "title": f"t{i}", "abstract": "", "language": "es",
             "year": 2020, "journal": "J", "countries": []} for i in range(1, n + 1)]


def test_prompt_numbers_records_and_keeps_placeholder_out():
    p = sc.build_prompt(_recs(2), _cfg())
    assert "{records}" not in p and "1. [es" in p and "2. [es" in p


def test_parse_keeps_valid_items_and_drops_invalid_ones():
    batch = _recs(3)
    reply = json.dumps([
        {"n": 1, "label": "icf", "doc": "research", "why": "GCF"},
        {"n": 2, "label": "maybe", "doc": "research", "why": "x"},
        {"n": 9, "label": "out", "doc": "other", "why": "x"},
    ])
    assert sc.parse_answer(reply, batch) == {
        "W1": {"label": "icf", "doc": "research", "why": "GCF"}}
    assert sc.parse_answer("not json", batch) == {}
    assert sc.parse_answer(None, batch) == {}


def test_local_backend_posts_the_thinking_switch_and_returns_content(monkeypatch):
    cfg = {**_cfg(), **_cfg()["local"]}
    sent = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "[]"}}]}

    def fake_post(url, json, timeout):
        sent.update(url=url, body=json, timeout=timeout)
        return Resp()

    monkeypatch.setattr(sc.requests, "post", fake_post)
    assert sc.make_call(cfg)("p", model=cfg["model"], max_tokens=10) == "[]"
    assert sent["url"].endswith("/v1/chat/completions")
    assert sent["body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert sc.make_call(_cfg()) is sc.llm_call


def test_local_backend_failure_returns_none_so_the_batch_stays_unlabelled(monkeypatch):
    cfg = {**_cfg(), **_cfg()["local"]}

    def boom(url, json, timeout):
        raise sc.requests.ConnectionError("down")

    monkeypatch.setattr(sc.requests, "post", boom)
    assert sc.make_call(cfg)("p", model="m", max_tokens=1) is None


def test_rerun_retries_unlabelled_records_and_skips_labelled_ones(tmp_path):
    inp = tmp_path / "in.jsonl"
    inp.write_text("\n".join(json.dumps(r) for r in _recs(3)) + "\n", encoding="utf-8")
    args = types.SimpleNamespace(input=str(inp), output_dir=str(tmp_path / "o"),
                                 limit=0, sample_seed=7)
    cfg = {**_cfg(), "batch_size": 3, "workers": 1}
    calls = []

    def flaky(prompt, model, max_tokens):
        calls.append(prompt.count("Title:"))
        # first call labels only record 1; the rerun labels the rest
        items = [{"n": 1, "label": "icf", "doc": "research", "why": "a"}]
        if len(calls) > 1:
            items = [{"n": i, "label": "out", "doc": "other", "why": "b"}
                     for i in range(1, calls[-1] + 1)]
        return json.dumps(items)

    sc.run(cfg, args, call=flaky)
    sc.run(cfg, args, call=flaky)
    lines = [json.loads(x) for x in open(tmp_path / "o" / "screen.jsonl", encoding="utf-8")]
    assert sorted(x["openalex_id"] for x in lines) == ["W1", "W2", "W3"]
    assert calls == [3, 2]
