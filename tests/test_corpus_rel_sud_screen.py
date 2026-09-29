"""The REL screen: strict parsing, resumable output, no silent label loss."""

import json
import os
import types

import corpus_rel_sud_screen as sc
import pytest
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


def test_compact_lines_parse_like_the_json_form_and_bad_lines_are_dropped():
    batch = _recs(4)
    reply = "1|out|research|\n2|icf|research|GCF allocation\n3|maybe|research|x\ngarbage\n4|unsure|other"
    assert sc.parse_answer(reply, batch) == {
        "W1": {"label": "out", "doc": "research", "why": ""},
        "W2": {"label": "icf", "doc": "research", "why": "GCF allocation"},
        "W4": {"label": "unsure", "doc": "other", "why": ""}}


def test_local_prompt_asks_for_compact_lines_and_default_prompt_for_json():
    local = {**_cfg(), **_cfg()["local"]}
    assert "n|label|doc|why" in sc.build_prompt(_recs(1), local)
    assert '"label": "icf"' in sc.build_prompt(_recs(1), _cfg())
    assert "{answer_format}" not in sc.build_prompt(_recs(1), local)


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


def test_labels_carry_their_model_and_headers_are_appended(tmp_path):
    inp = tmp_path / "in.jsonl"
    inp.write_text("\n".join(json.dumps(r) for r in _recs(2)) + "\n", encoding="utf-8")
    args = types.SimpleNamespace(input=str(inp), output_dir=str(tmp_path / "o"), limit=0, sample_seed=7)
    cfg = {**_cfg(), "batch_size": 5, "workers": 1}

    def label_all(prompt, model, max_tokens):
        n = prompt.count("Title:")
        return json.dumps([{"n": i, "label": "out", "doc": "other", "why": ""} for i in range(1, n + 1)])

    sc.run(cfg, args, call=label_all)
    sc.run({**cfg, "model": "other-model"}, args, call=label_all)
    lines = [json.loads(x) for x in open(tmp_path / "o" / "screen.jsonl", encoding="utf-8")]
    assert {x["model"] for x in lines} == {cfg["model"]}
    headers = [json.loads(x) for x in open(tmp_path / "o" / "screen_runs.jsonl", encoding="utf-8")]
    assert len(headers) == 2 and headers[1]["model"] == "other-model"


def test_resume_skips_an_unreadable_line_and_duplicate_input_ids(tmp_path):
    inp = tmp_path / "in.jsonl"
    recs = _recs(2) + _recs(1)
    inp.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    out = tmp_path / "o"
    out.mkdir()
    (out / "screen.jsonl").write_text(json.dumps({"openalex_id": "W1"}) + '\n{"openalex_id": "W', encoding="utf-8")
    args = types.SimpleNamespace(input=str(inp), output_dir=str(out), limit=0, sample_seed=7)
    asked = []

    def label_all(prompt, model, max_tokens):
        n = prompt.count("Title:")
        asked.append(n)
        return json.dumps([{"n": i, "label": "ICF", "doc": "Research", "why": ""} for i in range(1, n + 1)])

    sc.run({**_cfg(), "batch_size": 5, "workers": 1}, args, call=label_all)
    assert asked == [1]  # W1 is done; W2 is asked once despite the duplicate row
    last = [json.loads(x) for x in open(out / "screen.jsonl", encoding="utf-8") if x.strip().endswith("}")]
    assert last[-1]["label"] == "icf" and last[-1]["doc"] == "research"
