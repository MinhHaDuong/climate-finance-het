"""The REL screen: strict parsing, resumable output, no silent label loss."""

import hashlib
import json
import os
import types

import corpus_rel_sud_screen as sc
import pytest
import yaml

pytestmark = pytest.mark.domain_corpus

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


# ── Record key (ticket 1733) ─────────────────────────────

GOLDEN = [  # records whose prompt hashes were taken before --id-field existed
    {"openalex_id": "W1", "title": "Finance climat : le Fonds vert " * 10,
     "abstract": "Résumé " * 200, "language": "fr", "year": 2019,
     "journal": "Revue Tiers Monde", "countries": ["FR", "SN"]},
    {"openalex_id": "W2", "title": "No abstract here", "abstract": "", "language": "",
     "year": None, "journal": "", "countries": []}]


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def test_prompt_is_byte_identical_to_the_1530_screener_whatever_the_key():
    cfg = _cfg()
    local = {**cfg, **cfg["local"]}
    assert _sha(sc.build_prompt(GOLDEN, cfg)) == (
        "b6e6848e80ede5a23f8a82c9a48bb5413b7850855fd240162704c3a7473f97be")
    assert _sha(sc.build_prompt(GOLDEN, local)) == (
        "d9c1edccd296c7d3901fc2b3f90a68d952946b2cf83779a1b0e048e10a319a98")
    # a pool record as the stage-1 input builder writes it shows the same text
    pool_recs = [{**r, "work_key": f"openalex:{r['openalex_id']}", "doi": "10.1/x",
                  "year": "" if r["year"] is None else str(r["year"])} for r in GOLDEN]
    assert sc.build_prompt(pool_recs, local) == sc.build_prompt(GOLDEN, local)


def _pool_recs(n):
    return [{**r, "work_key": f"title:t{i}|2020", "openalex_id": ""}
            for i, r in enumerate(_recs(n), 1)]


def _label_lines(prompt, model, max_tokens):
    return "\n".join(f"{i}|out|research|" for i in range(1, prompt.count("Title:") + 1))


def _args(inp, out, id_field):
    return types.SimpleNamespace(input=str(inp), output_dir=str(out), limit=0, sample_seed=7,
                                 id_field=id_field)


def test_work_key_run_writes_work_key_lines_and_header(tmp_path):
    inp = tmp_path / "in.jsonl"
    inp.write_text("".join(json.dumps(r) + "\n" for r in _pool_recs(3)), encoding="utf-8")
    sc.run({**_cfg(), "batch_size": 2, "workers": 1}, _args(inp, tmp_path / "o", "work_key"),
           call=_label_lines)
    lines = [json.loads(x) for x in open(tmp_path / "o" / "screen.jsonl", encoding="utf-8")]
    assert [x["work_key"] for x in lines] == ["title:t1|2020", "title:t2|2020", "title:t3|2020"]
    assert all("openalex_id" not in x for x in lines)
    (head,) = [json.loads(x) for x in open(tmp_path / "o" / "screen_runs.jsonl", encoding="utf-8")]
    assert head["id_field"] == "work_key" and head["n_todo"] == 3


def test_resume_under_another_key_is_refused(tmp_path):
    inp = tmp_path / "in.jsonl"
    inp.write_text("".join(json.dumps(r) + "\n" for r in _pool_recs(2)), encoding="utf-8")
    out = tmp_path / "o"
    out.mkdir()
    (out / "screen.jsonl").write_text(json.dumps({"openalex_id": "W1", "label": "out"}) + "\n",
                                      encoding="utf-8")
    asked = []

    def call(prompt, model, max_tokens):
        asked.append(1)
        return ""

    with pytest.raises(SystemExit, match="keyed otherwise"):
        sc.run({**_cfg(), "batch_size": 5, "workers": 1}, _args(inp, out, "work_key"), call=call)
    assert asked == []


def test_input_record_without_the_key_is_refused(tmp_path):
    inp = tmp_path / "in.jsonl"
    inp.write_text("".join(json.dumps(r) + "\n" for r in _recs(2)), encoding="utf-8")
    with pytest.raises(SystemExit, match="line 1 has no 'work_key'"):
        sc.select_records(str(inp), set(), 0, 7, "work_key")
