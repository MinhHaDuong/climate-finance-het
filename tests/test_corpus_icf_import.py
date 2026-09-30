"""Importing the 1530 labels and finished stage-1 runs into icf_screen (ticket 1732)."""

import json

import _icf_screen as ics
import corpus_icf_import as ci
import pytest

pytestmark = pytest.mark.domain_corpus

PROMPT_MD = "# x\n\n```\nwrapper text\n```\n"


def _jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _lab(i, label):
    return {"openalex_id": f"W{i}", "title": f"T{i}", "label": label, "doc": "research",
            "why": ""}


def _archive(tmp_path):
    """A 1530 archive in miniature: 2 pilot + 1 Haiku + 2 Qwen screen1 + 1 Qwen screen2."""
    a = tmp_path / "rel_sud" / "2026-09-29"
    labels = [_lab(1, "icf"), _lab(2, "out"), _lab(3, "unsure"), _lab(4, "icf"),
              _lab(5, "aux"), _lab(6, "icf")]
    runs, lw = a / "padme-rel_sud_runs", a / "local-work"
    _jsonl(lw / "screen-pilot" / "screen.jsonl", labels[:2])
    _jsonl(lw / "screen-full" / "screen.jsonl", labels[:3])
    _jsonl(runs / "screen1" / "screen-haiku-first12491.jsonl", labels[:3])
    _jsonl(runs / "screen1" / "screen.jsonl", labels[:5])
    _jsonl(runs / "screen2" / "screen.jsonl", labels)
    for d, model, sha in ((lw / "screen-pilot", "haiku", "h1"), (lw / "screen-full", "haiku", "h1"),
                          (runs / "screen1", "qwen", "q1"), (runs / "screen2", "qwen", "q1")):
        (d / "screen_run.json").write_text(json.dumps({"model": model, "prompt_sha256": sha}))
    _jsonl(lw / "screen_input_final.jsonl", [
        {"openalex_id": f"W{i}", "doi": f"10.1/{i}" if i % 2 else "", "title": "" if i == 6 else f"T {i}",
         "year": 2020} for i in range(1, 8)])
    (lw / "pilot_order.json").write_text(json.dumps(["W1", "W2"]))
    (lw / "pilot_opus.json").write_text(json.dumps([
        {"n": 1, "label": "icf", "doc": "research", "why": "y"},
        {"n": 2, "label": "aux", "doc": "other", "why": ""}]))
    s2 = lw / "stage2"
    s2.mkdir()
    (s2 / "chunk01.ids.json").write_text(json.dumps(["W3", "W4"]))
    (s2 / "chunk01.opus.txt").write_text("1|unsure|research|?|no abstract\n2|icf|research|BR|GCF\n")
    prompt = tmp_path / "prompt.md"
    prompt.write_text(PROMPT_MD)
    return a, prompt


def test_t1530_rows_segments_models_and_unknowns(tmp_path):
    a, prompt = _archive(tmp_path)
    rows = ci.t1530_rows(str(a), str(prompt))
    s1 = [r for r in rows if r["stage"] == "1"]
    assert [r["run_id"] for r in s1] == ["t1530-haiku-pilot"] * 2 + ["t1530-haiku-full"] + \
        ["t1530-qwen-screen1"] * 2 + ["t1530-qwen-screen2"]
    assert [r["machine"] for r in s1] == ["doudou"] * 3 + ["padme"] * 3
    assert s1[0]["source"] == "rel_sud/2026-09-29/local-work/screen-pilot/screen.jsonl"
    s2 = [r for r in rows if r["stage"] == "2"]
    pilot = [r for r in s2 if r["run_id"] == "t1530-opus-pilot"]
    assert [(r["work_key"], r["label"], r["prompt_sha256"]) for r in pilot] == [
        ("openalex:W1", "icf", "unknown"), ("openalex:W2", "aux", "unknown")]
    chunks = [r for r in s2 if r["run_id"] == "t1530-opus-stage2"]
    assert [(r["work_key"], r["label"], r["studied_country"]) for r in chunks] == [
        ("openalex:W3", "unsure", "?"), ("openalex:W4", "icf", "BR")]
    assert chunks[0]["prompt_sha256"] == ics.stage2_prompt_sha256(str(prompt))
    assert s1[0]["doi"] == "10.1/1" and s1[0]["title_norm_year"].endswith("|2020")
    assert s1[5]["title_norm_year"] == "", "a title-less record keeps its label, no title key"


def test_t1530_import_is_idempotent(tmp_path):
    a, prompt = _archive(tmp_path)
    table = str(tmp_path / "t" / "icf_screen.csv")
    args = ["--output", table, "t1530", "--archive", str(a), "--stage2-prompt", str(prompt)]
    assert ci.main(args) == 0
    first = open(table, "rb").read()
    assert len(ics.read_table(table)) == 6 + 2 + 2
    assert ci.main(args) == 0
    assert open(table, "rb").read() == first, "a second import appends nothing"


def test_t1530_refuses_inconsistent_copies(tmp_path):
    a, prompt = _archive(tmp_path)
    _jsonl(a / "padme-rel_sud_runs" / "screen1" / "screen-haiku-first12491.jsonl",
           [_lab(1, "out"), _lab(2, "out"), _lab(3, "unsure")])
    with pytest.raises(ci.ImportRefused, match="haiku"):
        ci.t1530_rows(str(a), str(prompt))


def _run_dir(tmp_path, finished=True, models=("qwen",)):
    d = tmp_path / "2026-09-30-catalogue-stage1"
    _jsonl(d / "screen_input.jsonl", [{"openalex_id": "W7", "doi": "10.2/X", "title": "A b",
                                       "year": 2019}])
    _jsonl(d / "screen.jsonl", [_lab(7, "aux")])
    _jsonl(d / "screen_runs.jsonl", [{"model": m, "prompt_sha256": "p",
                                      "started": f"2026-09-30T1{k}:00:00+00:00"}
                                     for k, m in enumerate(models)])
    (d / "run.log").write_text("INFO labelled 1, unlabelled 0 (rerun to retry)\n" if finished
                               else "warnings\n")
    return d


def test_stage1_run_import(tmp_path):
    d = _run_dir(tmp_path)
    table = str(tmp_path / "icf_screen.csv")
    assert ci.main(["--output", table, "stage1-run", "--run-dir", str(d), "--machine", "padme"]) == 0
    (row,) = ics.read_table(table)
    assert (row["work_key"], row["run_id"], row["model"], row["doi"], row["labelled_at"]) == (
        "openalex:W7", "2026-09-30-catalogue-stage1", "qwen", "10.2/x", "2026-09-30T10:00:00+00:00")


def test_stage1_run_skip_ids(tmp_path):
    d = _run_dir(tmp_path)
    assert ci.stage1_run_rows(str(d), str(d / "screen_input.jsonl"), "padme", "r", "s",
                              frozenset({"W7"})) == []


def test_stage1_run_refused_while_running_or_mixed(tmp_path):
    with pytest.raises(ci.ImportRefused, match="not finished"):
        ci.stage1_run_rows(str(_run_dir(tmp_path, finished=False)), "", "padme", "r", "s")
    d = _run_dir(tmp_path / "b", models=("qwen", "haiku"))
    with pytest.raises(ci.ImportRefused, match="disagree"):
        ci.stage1_run_rows(str(d), str(d / "screen_input.jsonl"), "padme", "r", "s")
