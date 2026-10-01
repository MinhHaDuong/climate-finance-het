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
    cc.render(str(out), ics.catchup_prompt_template(CATCHUP_PROMPT))
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


@pytest.mark.parametrize("answers", [
    "1|icf|research|SN|yes|economics|policy|x\n2|out|other|?|na|na|na|\n",  # a v2 file
    "1|yes|economics|policy|\n1|no|finance|empirical|x\n",                 # answered twice
    "the records are about climate finance\n",                              # prose
])
def test_parse_refuses_a_malformed_chunk_and_writes_nothing(tmp_path, chunks, answers):
    (chunks / "chunk01.or.txt").write_text(answers)
    dims = tmp_path / "rel_dimensions.csv"
    assert cc.main(["--dimensions-table", str(dims), "parse", "--chunk-dir", str(chunks),
                    "--model", "m", "--run-id", "r", "--machine", "d", "--suffix", "or",
                    "--new-table"]) == 1
    assert not dims.exists()


def test_parse_counts_na_and_unknown_and_skips_fences(chunks):
    (chunks / "chunk01.or.txt").write_text("```\n1|na|economics|policy|\n2|yes|BOGUS|case|\n```\n")
    dims, report = cc.parse_answers(str(chunks), "or", "m", "r", "d", "llm", "p", "d", "s")
    assert len(dims) == 2
    assert report["chunk01"]["na_off_rule"] == 1 and report["chunk01"]["unknown_dimension"] == 1
    assert report["chunk02"]["status"] == "no answer file"


def test_select_catchup_takes_final_icf_and_unsure_without_dimensions():
    view = [{"work_key": "openalex:W1", "status": "icf"},
            {"work_key": "openalex:W2", "status": "unsure_unresolved"},
            {"work_key": "openalex:W3", "status": "aux"},
            {"work_key": "openalex:W4", "status": "pending_stage2"},
            {"work_key": "openalex:W5", "status": "icf"}]
    sel = cc.select_catchup(view, ["icf", "unsure"], {"openalex:W5"})
    assert sel == {"keys": ["openalex:W1", "openalex:W2"], "eligible": 3,
                   "already_with_dimensions": 1}


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


def test_submit_refuses_above_the_cap_before_any_request(chunks, monkeypatch):
    monkeypatch.setattr(cc, "model_pricing", lambda m: {"prompt": 1e-3, "completion": 1e-3})

    def boom(*a, **k):
        raise AssertionError("no request may be sent")
    with pytest.raises(cc.CatchupError, match="exceeds"):
        cc.submit(str(chunks), "m", "or", 0.01, 1000, None, 400, post=boom)
    assert not (chunks / "or.batch.json").exists()


def test_collect_writes_answers_and_the_token_log(chunks, monkeypatch):
    monkeypatch.setattr(cc, "_headers", lambda: {})
    (chunks / "or.batch.json").write_text(json.dumps(
        {"batch_id": "b1", "model": "m:batch", "route": "openrouter-batch",
         "pricing": {"prompt": 2e-6, "completion": 1e-5}}))

    def body(text, cost):
        return {"model": "m", "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": cost}}
    batch = {"id": "b1", "status": "completed", "usage": {"cost": 0.3},
             "results": [{"custom_id": "chunk01", "response": {"body": body(
                 "1|yes|economics|policy|\n2|no|data_science|method|CER forecast\n", 0.2)}},
                         {"custom_id": "chunk02", "response": {"body": body(
                             "1|unsure|other|other|no abstract\n", 0.1)}}]}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return batch
    res = cc.collect(str(chunks), "or", wait=False, get=lambda *a, **k: Resp())
    assert res["answered"] == 3 and res["cost_usd"] == 0.3
    assert (chunks / "chunk02.or.txt").read_text() == "1|unsure|other|other|no abstract\n"
    calls = [json.loads(x) for x in (chunks / "or.calls.jsonl").read_text().splitlines()]
    assert [c["cost_per_answered_usd"] for c in calls] == [0.1, 0.1]
