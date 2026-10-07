"""Discipline catch-up: dimensions only, stage catchup, never icf_screen (ticket 1842)."""

import json
import os

import _icf_chunks as ch
import _icf_screen as ics
import corpus_rel_discipline_catchup as cc
import pytest

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATCHUP_PROMPT = os.path.join(ROOT, "config", "rel_discipline_catchup_prompt.md")
V2_PROMPT = os.path.join(ROOT, "config", "rel_stage2_prompt_v2.md")
S2CFG = {"chunk_size": 2, "title_max_chars": 220, "abstract_max_chars": 650}


def _work(i):
    return {"work_key": f"openalex:W{i}", "openalex_id": f"W{i}", "doi": "", "title": f"T{i}",
            "year": "2020", "journal": "", "language": "en", "abstract": "A",
            "affiliation_countries": ""}


def _icf_row(i, stage="2", label="icf"):
    return {"work_key": f"openalex:W{i}", "openalex_id": f"W{i}", "doi": "",
            "title_norm_year": f"t{i}|2020", "stage": stage, "labeller": "llm",
            "model": "opus", "prompt_sha256": "p", "run_id": "t1530", "machine": "doudou",
            "label": label, "doc_type": "research", "studied_country": "", "why": "",
            "labelled_at": "2026-09-29", "source": "s"}


@pytest.fixture
def chunks(tmp_path):
    out = tmp_path / "cu"
    ch.write_chunks(str(out), [_work(1), _work(2), _work(3)], S2CFG, {})
    cc.render(str(out), CATCHUP_PROMPT)
    return out


def test_wrapper_asks_the_v2_discipline_questions_word_for_word():
    """Same instrument as forward stage 2: the three definitions are copied, not paraphrased."""
    block, v2 = ics.catchup_prompt_template(CATCHUP_PROMPT), ics._prompt_block(V2_PROMPT)
    start = v2.index("- contrib:")
    definitions = v2[start:v2.index("For a record labelled out")].strip()
    assert definitions in block
    assert ics.stage2_prompt_sha256(CATCHUP_PROMPT) != ics.stage2_prompt_sha256(V2_PROMPT)


def test_stage2_parse_refuses_the_catchup_wrapper():
    """corpus_icf_stage2.py parse cannot read catch-up answers into icf_screen."""
    with pytest.raises(ics.IcfScreenError, match="neither"):
        ics.stage2_answer_fields(CATCHUP_PROMPT)


def test_icf_screen_refuses_a_catchup_row(tmp_path):
    """A catch-up row in icf_screen would become the work's last stage-2 label."""
    with pytest.raises(ics.IcfScreenError, match="stage='catchup'"):
        ics.append_rows(str(tmp_path / "icf_screen.csv"), [_icf_row(1, stage="catchup")],
                        new_table=True)
    assert not (tmp_path / "icf_screen.csv").exists()


def test_parse_writes_dimensions_only_under_stage_catchup(tmp_path, chunks):
    table = str(tmp_path / "icf_screen.csv")
    ics.append_rows(table, [_icf_row(1), _icf_row(2, label="unsure")], new_table=True)
    before = (tmp_path / "icf_screen.csv").read_bytes(), \
        (tmp_path / "icf_screen.manifest.jsonl").read_bytes()
    (chunks / "chunk01.or.txt").write_text("1|yes|economics|policy|\n2|no|finance|empirical|"
                                           "option pricing only\n")
    dims = str(tmp_path / "rel_dimensions.csv")
    args = ["--table", table, "--dimensions-table", dims, "parse", "--chunk-dir", str(chunks),
            "--model", "anthropic/claude-opus-5.5:batch", "--run-id", "t1842-catchup",
            "--machine", "padme", "--suffix", "or", "--new-table"]
    assert cc.main(args) == 0
    rows = ics.read_table(dims, ics.DIMENSIONS)
    assert [(r["work_key"], r["stage"], r["contrib"], r["field"], r["contrib_type"])
            for r in rows] == [("openalex:W1", "catchup", "yes", "economics", "policy"),
                               ("openalex:W2", "catchup", "no", "finance", "empirical")]
    assert {r["run_id"] for r in rows} == {"t1842-catchup"}
    assert rows[0]["prompt_sha256"] == ics.stage2_prompt_sha256(CATCHUP_PROMPT)
    after = (tmp_path / "icf_screen.csv").read_bytes(), \
        (tmp_path / "icf_screen.manifest.jsonl").read_bytes()
    assert after == before, "icf_screen untouched"
    assert cc.main(args) == 0 and len(ics.read_table(dims, ics.DIMENSIONS)) == 2, "idempotent"
    # Red team, PR 1660: a second run id must not give a work a second catch-up answer.
    (chunks / "chunk02.or.txt").write_text("1|yes|politics|policy|\n")
    assert cc.main(args[:-7] + ["--run-id", "t1842-again", "--machine", "padme",
                                "--suffix", "or"]) == 0
    rows = ics.read_table(dims, ics.DIMENSIONS)
    assert [(r["work_key"], r["run_id"]) for r in rows][2:] == [("openalex:W3", "t1842-again")]


def test_parse_stamps_the_hash_of_the_rendered_wrapper(tmp_path, chunks):
    """Red team, PR 1660: rows carry the wrapper the model saw, not the one at parse time."""
    edited = tmp_path / "edited.md"
    edited.write_text(open(CATCHUP_PROMPT, encoding="utf-8").read().replace(
        "Read-only labelling task.", "Read-only labelling task, edited."))
    (chunks / "chunk01.or.txt").write_text("1|yes|economics|policy|\n")
    dims = str(tmp_path / "rel_dimensions.csv")
    assert cc.main(["--prompt", str(edited), "--dimensions-table", dims, "parse",
                    "--chunk-dir", str(chunks), "--model", "m", "--run-id", "r",
                    "--machine", "d", "--suffix", "or", "--new-table"]) == 0
    assert ics.read_table(dims, ics.DIMENSIONS)[0]["prompt_sha256"] == \
        ics.stage2_prompt_sha256(CATCHUP_PROMPT)
    with pytest.raises(cc.CatchupError, match="rendered with wrapper"):
        cc.render(str(chunks), str(edited))
    (chunks / "render.json").unlink()
    with pytest.raises(cc.CatchupError, match="render.json missing"):
        cc.rendered_sha(str(chunks))


def test_build_refuses_a_lost_dimensions_table(tmp_path):
    """Red team, PR 1660: a missing rel_dimensions beside v2 stage-2 rows is lost, not empty."""
    table = str(tmp_path / "icf_screen.csv")
    v2_sha = ics.stage2_prompt_sha256(V2_PROMPT)
    ics.append_rows(table, [_icf_row(1)], new_table=True)
    assert cc.dimension_rows(table, str(tmp_path / "dims.csv"), V2_PROMPT) == []
    ics.append_rows(table, [dict(_icf_row(2), prompt_sha256=v2_sha)])
    with pytest.raises(cc.CatchupError, match="missing"):
        cc.dimension_rows(table, str(tmp_path / "dims.csv"), V2_PROMPT)


@pytest.mark.parametrize("answers", [
    "1|icf|research|SN|yes|economics|policy|x\n2|out|other|?|na|na|na|\n",  # a v2 file
    "1|unsure|research|SN|unsure|other|other|x\n",                        # v2 line, unsure
    "1|yes|economics|policy|\n1|no|finance|empirical|x\n",                 # answered twice
    "the records are about climate finance\n",                              # prose
    "²|yes|economics|policy|\n",                                            # non-ASCII digit
    "9" * 5000 + "|yes|economics|policy|\n",                                # huge number
])
def test_parse_refuses_a_malformed_chunk_and_writes_nothing(tmp_path, chunks, answers):
    (chunks / "chunk01.or.txt").write_text(answers)
    dims = tmp_path / "rel_dimensions.csv"
    assert cc.main(["--dimensions-table", str(dims), "parse", "--chunk-dir", str(chunks),
                    "--model", "m", "--run-id", "r", "--machine", "d", "--suffix", "or",
                    "--new-table"]) == 1
    assert not dims.exists()


def test_parse_counts_na_and_unknown_and_skips_fences(chunks):
    """na is on the rule in all three fields; a partial na is counted off the rule."""
    (chunks / "chunk01.or.txt").write_text("```\n1|na|economics|policy|\n2|yes|BOGUS|case|\n```\n")
    dims, report = cc.parse_answers(str(chunks), "or", "m", "r", "d", "llm", "p", "d", "s")
    assert len(dims) == 2
    assert (report["chunk01"]["na"], report["chunk01"]["na_off_rule"],
            report["chunk01"]["unknown_dimension"]) == (1, 1, 1)
    assert report["chunk02"]["status"] == "no answer file"
    (chunks / "chunk02.or.txt").write_text("1|na|na|na|no climate-finance object\n")
    dims, report = cc.parse_answers(str(chunks), "or", "m", "r", "d", "llm", "p", "d", "s")
    assert (report["chunk02"]["na"], report["chunk02"]["na_off_rule"]) == (1, 0)
    assert [(d["contrib"], d["field"], d["contrib_type"]) for d in dims][2] == ("na", "na", "na")
    assert not [e for d in dims for e in ics.validate_row(d, ics.DIMENSIONS)]


def test_wrapper_offers_na_like_v2():
    """Ticket 1842 log, 2026-10-01: leaving na out cost the gold kappa; offer it as v2 does."""
    block = " ".join(ics.catchup_prompt_template(CATCHUP_PROMPT).split())
    assert "write na in all three fields" in block
    assert "contrib is yes, no, unsure or na" in block
    assert "Do not re-judge that." not in block


def test_select_catchup_takes_final_icf_and_unsure_without_dimensions():
    view = [{"work_key": "openalex:W1", "status": "icf"},
            {"work_key": "openalex:W2", "status": "unsure_unresolved"},
            {"work_key": "openalex:W3", "status": "aux"},
            {"work_key": "openalex:W4", "status": "pending_stage2"},
            {"work_key": "openalex:W5", "status": "icf"}]
    sel = cc.select_catchup(view, ["icf", "unsure"], {"openalex:W5"})
    assert sel == {"keys": ["openalex:W1", "openalex:W2"], "eligible": 3, "no_abstract": 0,
                   "already_with_dimensions": 1, "by_label": {"icf": 1, "unsure": 1}}


def test_select_catchup_leaves_out_works_without_abstract():
    """No-abstract policy (ticket 1733, 2026-10-07): bibliometric only, never sent to a model."""
    view = [{"work_key": "openalex:W1", "status": "icf"},
            {"work_key": "openalex:W2", "status": "unsure_unresolved"},
            {"work_key": "openalex:W3", "status": "icf"},
            {"work_key": "openalex:W4", "status": "unsure_unresolved"}]
    sel = cc.select_catchup(view, ["icf", "unsure"], set(),
                            no_abstract={"openalex:W3", "openalex:W4", "openalex:W9"})
    assert sel["keys"] == ["openalex:W1", "openalex:W2"]
    assert (sel["eligible"], sel["no_abstract"], sel["by_label"]) == (4, 2, {"icf": 1,
                                                                             "unsure": 1})


def test_build_sends_no_work_without_abstract(tmp_path, monkeypatch):
    pool = [_work(1), {**_work(2), "abstract": "  "}, {**_work(3), "abstract": ""}]
    view = [{"work_key": p["work_key"], "status": "icf"} for p in pool]
    monkeypatch.setattr(ch, "view", lambda *a: (pool, view))
    monkeypatch.setattr(cc.rv, "screen_rule", lambda cfg: {})
    monkeypatch.setattr(cc.rv, "sha256_file", lambda path: "x")
    monkeypatch.setattr(cc.ics, "require_table", lambda path: None)
    monkeypatch.setattr(cc, "dimension_rows", lambda *a: [])
    out = tmp_path / "cu"
    args = type("A", (), {"pool": "p", "table": "t", "output_dir": str(out)})()
    cfg = {"stage2": {**S2CFG, "prompt": V2_PROMPT},
           "catchup": {"final_labels": ["icf", "unsure"]}}
    cc._build(args, cfg, CATCHUP_PROMPT, "d")
    assert json.loads((out / "chunk01.ids.json").read_text()) == ["openalex:W1"]
    build = json.loads((out / "build.json").read_text())
    assert (build["works"], build["no_abstract"]) == (1, 2)


def test_render_fills_the_records(chunks):
    text = (chunks / "chunk01.prompt.txt").read_text(encoding="utf-8")
    assert "{records}" not in text and "1. [en | 2020 | ? | affiliations: ?]" in text
    assert text.index("n|contrib|field|ctype|why") < text.index("Title: T1")


def test_usage_log_reports_or_derives_cost():
    price = {"prompt": 2e-6, "completion": 1e-5}
    body = {"model": "m", "choices": [{"finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500,
                      "completion_tokens_details": {"reasoning_tokens": 300}}}
    line = cc.usage_log("chunk01", body, 3, 2, price, {})
    assert (line["cost_usd"], line["cost_source"], line["reasoning_tokens"]) == (0.007, "derived",
                                                                                 300)
    assert line["cost_per_answered_usd"] == 0.0035
    body["usage"]["cost"] = 0.004
    assert cc.usage_log("chunk01", body, 3, 2, price, {})["cost_source"] == "reported"


def _boom(*a, **k):
    raise AssertionError("no request may be sent")


def test_spend_guard_is_a_bound_on_max_tokens(chunks, monkeypatch):
    monkeypatch.setattr(cc, "model_pricing", lambda m: {"prompt": 1e-6, "completion": 1e-5})
    # input is tiny; two chunks x 1000 output tokens x 1e-5 = 0.02 USD
    with pytest.raises(cc.CatchupError, match="exceeds"):
        cc.submit(str(chunks), "m", "or", 0.019, 1000, None, post=_boom)
    for cap in (float("nan"), -1.0, 0.0):
        with pytest.raises(cc.CatchupError, match="must be positive"):
            cc.call(str(chunks), "m", "or", cap, 1000, None, post=_boom)
    assert not (chunks / "or.batch.json").exists()


@pytest.mark.parametrize("price", ["-1", "0", "nan"])
def test_spend_guard_refuses_a_model_without_a_positive_price(price):
    """Red team, PR 1660: a router model listed at -1 gave a negative estimate."""
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"id": "openrouter/auto",
                              "pricing": {"prompt": price, "completion": "1e-5"}}]}
    with pytest.raises(cc.CatchupError, match="no spend bound"):
        cc.model_pricing("openrouter/auto", get=lambda *a, **k: Resp())


def test_collect_writes_answers_and_the_token_log(chunks, monkeypatch):
    monkeypatch.setattr(cc, "_headers", lambda: {})
    (chunks / "or.batch.json").write_text(json.dumps(
        {"batch_id": "b1", "model": "m:batch", "route": "openrouter-batch",
         "chunks": ["chunk01", "chunk02"], "pricing": {"prompt": 2e-6, "completion": 1e-5}}))

    def body(text, cost):
        return {"model": "m", "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": cost}}
    reply = "Here are the answers:\n1|yes|economics|policy|\n2|no|data_science|method|CER\n"
    batch = {"id": "b1", "status": "completed", "usage": {"cost": 0.3},
             "results": [{"custom_id": "chunk01", "response": {"body": body(reply, 0.2)}},
                         {"custom_id": "chunk02", "response": None,
                          "error": {"message": "overloaded"}}]}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return batch
    res = cc.collect(str(chunks), "or", wait=False, get=lambda *a, **k: Resp())
    assert res["answered"] == 2 and res["cost_usd"] == 0.2
    # the preamble stays in the raw reply, out of the answer file
    assert (chunks / "chunk01.or.raw.txt").read_text() == reply
    assert (chunks / "chunk01.or.txt").read_text() == "\n".join(reply.splitlines()[1:]) + "\n"
    assert not (chunks / "chunk02.or.txt").exists(), "an errored request leaves it pending"
    cc.collect(str(chunks), "or", wait=False, get=lambda *a, **k: Resp())
    calls = [json.loads(x) for x in (chunks / "or.calls.jsonl").read_text().splitlines()]
    assert [c["cost_per_answered_usd"] for c in calls] == [0.1, None], "rewritten, not doubled"
    assert calls[1]["error"] == {"message": "overloaded"}


@pytest.mark.parametrize("reply", ["", "| n | contrib |\n|---|---|\n", "Sorry, I cannot."])
def test_a_reply_without_answer_lines_leaves_the_chunk_pending(chunks, monkeypatch, reply):
    """Review round 3, PR 1660: an empty answer file made call skip a chunk for good."""
    monkeypatch.setattr(cc, "_headers", lambda: {})
    monkeypatch.setattr(cc, "model_pricing", lambda m: {"prompt": 1e-6, "completion": 1e-6})
    sent = []

    class Resp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": reply}, "finish_reason": "length"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 0}}

    def post(*a, **k):
        sent.append(1)
        return Resp()
    cc.call(str(chunks), "m", "or", 1.0, 100, None, post=post)
    assert not (chunks / "chunk01.or.txt").exists() and (chunks / "chunk01.or.raw.txt").exists()
    cc.call(str(chunks), "m", "or", 1.0, 100, None, post=post)
    assert len(sent) == 4, "both chunks retried"


@pytest.mark.parametrize("reply", ["1 | yes", "7|yes|economics|empirical|why",
                                   "1|icf|research|VN|why\n2|out|institutional||why"])
def test_a_reply_without_a_valid_answer_leaves_the_chunk_pending(chunks, monkeypatch, reply):
    """Reroll round 1, PR 1660: numbered lines with no valid answer wrote an answer file,
    so call skipped the chunk for good and parse aborted on it."""
    monkeypatch.setattr(cc, "_headers", lambda: {})
    monkeypatch.setattr(cc, "model_pricing", lambda m: {"prompt": 1e-6, "completion": 1e-6})
    sent = []

    class Resp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": reply}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5}}

    def post(*a, **k):
        sent.append(1)
        return Resp()
    cc.call(str(chunks), "m", "or", 1.0, 100, None, post=post)
    assert not (chunks / "chunk01.or.txt").exists()
    assert (chunks / "chunk01.or.raw.txt").read_text() == reply
    calls = [json.loads(x) for x in (chunks / "or.calls.jsonl").read_text().splitlines()]
    assert [c["answered"] for c in calls] == [0, 0]
    cc.call(str(chunks), "m", "or", 1.0, 100, None, post=post)
    assert len(sent) == 4, "both chunks retried"
    _, report = cc.parse_answers(str(chunks), "or", "m", "r", "x", "llm", "h", "2026-10-07", "p")
    assert report["chunk01"]["status"] == "no answer file"
