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


def test_t1530_import_defaults_to_the_frozen_v1_wrapper(tmp_path, monkeypatch):
    """Ticket 1840: stage2.prompt moved to v2; the t1530 hash must still come from v1."""
    seen = {}

    def fake_rows(archive, prompt_md):
        seen["prompt"] = prompt_md
        return []

    monkeypatch.setattr(ci, "t1530_rows", fake_rows)
    a, _ = _archive(tmp_path)
    assert ci.main(["--output", str(tmp_path / "t.csv"), "t1530", "--archive", str(a)]) == 0
    assert seen["prompt"].endswith("config/rel_sud_stage2_prompt.md")
    assert ics.stage2_prompt_sha256(seen["prompt"]) == (
        "8ff53ea8c818c2d88542a06f62e24613c9446691b8298452e407d8114e51a93d")


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


def _pool_run_dir(tmp_path, header_field="work_key", labels=None):
    d = tmp_path / "2026-10-01-pool-stage1"
    _jsonl(d / "screen_input.jsonl", [
        {"work_key": "doi:10.3/y", "openalex_id": "", "doi": "10.3/Y", "title": "C d",
         "year": "2021"},
        {"work_key": "openalex:W9", "openalex_id": "W9", "doi": "", "title": "E", "year": ""}])
    _jsonl(d / "screen.jsonl", labels or [
        {"work_key": "doi:10.3/y", "title": "C d", "label": "icf", "doc": "research", "why": "x"},
        {"work_key": "openalex:W9", "title": "E", "label": "out", "doc": "other", "why": ""}])
    head = {"model": "qwen", "prompt_sha256": "p", "started": "2026-10-01T08:00:00+00:00"}
    if header_field:
        head["id_field"] = header_field
    _jsonl(d / "screen_runs.jsonl", [head])
    (d / "run.log").write_text("INFO labelled 2, unlabelled 0 (rerun to retry)\n")
    return d


def test_stage1_run_keyed_by_work_key(tmp_path):
    d = _pool_run_dir(tmp_path)
    table = str(tmp_path / "icf_screen.csv")
    assert ci.main(["--output", table, "stage1-run", "--run-dir", str(d), "--machine", "padme",
                    "--allow-input-drift"]) == 0
    rows = ics.read_table(table)
    assert [(r["work_key"], r["openalex_id"], r["doi"], r["title_norm_year"], r["label"])
            for r in rows] == [("doi:10.3/y", "", "10.3/y", "c d|2021", "icf"),
                               ("openalex:W9", "W9", "", "e|", "out")]
    assert ci.stage1_run_rows(str(d), str(d / "screen_input.jsonl"), "padme", "r", "s",
                              frozenset({"doi:10.3/y"}))[0]["work_key"] == "openalex:W9"


def test_stage1_run_key_is_detected_from_lines_without_header_field(tmp_path):
    d = _pool_run_dir(tmp_path, header_field=None)
    rows = ci.stage1_run_rows(str(d), str(d / "screen_input.jsonl"), "padme", "r", "s")
    assert [r["work_key"] for r in rows] == ["doi:10.3/y", "openalex:W9"]


def test_stage1_run_year_as_float_string(tmp_path):
    assert ci.work_meta({"openalex_id": "W1", "title": "A", "year": "2020.0"})[
        "title_norm_year"] == "a|2020"


def test_stage1_run_invocations_declaring_two_keys_are_refused(tmp_path):
    d = _pool_run_dir(tmp_path)
    _jsonl(d / "screen_runs.jsonl", [
        {"model": "qwen", "prompt_sha256": "p", "started": "x", "id_field": "work_key"},
        {"model": "qwen", "prompt_sha256": "p", "started": "y", "id_field": "openalex_id"}])
    with pytest.raises(ci.ImportRefused, match="declare id fields"):
        ci.stage1_run_rows(str(d), str(d / "screen_input.jsonl"), "padme", "r", "s")


def test_stage1_run_input_without_the_key_is_refused(tmp_path):
    d = _pool_run_dir(tmp_path)
    _jsonl(d / "screen_input.jsonl", [{"openalex_id": "W9", "title": "E"}])
    with pytest.raises(ci.ImportRefused, match="lack 'work_key'"):
        ci.stage1_run_rows(str(d), str(d / "screen_input.jsonl"), "padme", "r", "s")


def _basis(tmp_path, d, pool_text="pool v1"):
    """A pool file and a one-append table, and the input summary built on them."""
    pool = tmp_path / "pool.csv"
    pool.write_text(pool_text)
    table = str(tmp_path / "t" / "icf_screen.csv")
    ics.append_rows(table, [{"work_key": "openalex:W1", "stage": "1", "labeller": "llm",
                             "model": "m", "prompt_sha256": "p", "run_id": "old",
                             "machine": "padme", "label": "out", "doc_type": "research",
                             "labelled_at": "2026-09-30", "source": "s"}], new_table=True)
    (d / "screen_input.summary.json").write_text(json.dumps({
        "pool_sha256": ci._sha256(str(pool)), "table_sha256": ci._sha256(table)}))
    return pool, table


def test_stage1_run_refused_on_another_pool_unless_overridden(tmp_path):
    d = _pool_run_dir(tmp_path)
    pool, table = _basis(tmp_path, d)
    args = ["--output", table, "stage1-run", "--run-dir", str(d), "--machine", "padme",
            "--pool", str(pool)]
    pool.write_text("pool v2, rebuilt")
    assert ci.main(args) == 1
    assert len(ics.read_table(table)) == 1
    assert ci.main(args + ["--allow-input-drift"]) == 0
    assert len(ics.read_table(table)) == 3


def test_stage1_run_accepts_a_table_that_only_grew(tmp_path):
    d = _pool_run_dir(tmp_path)
    pool, table = _basis(tmp_path, d)
    ics.append_rows(table, [{"work_key": "openalex:W2", "stage": "2", "labeller": "llm",
                             "model": "o", "prompt_sha256": "p", "run_id": "s2",
                             "machine": "doudou", "label": "icf", "doc_type": "research",
                             "labelled_at": "2026-10-01", "source": "s"}])
    ci.check_input_basis(str(d / "screen_input.jsonl"), str(pool), table)
    (d / "screen_input.summary.json").write_text(json.dumps({
        "pool_sha256": ci._sha256(str(pool)), "table_sha256": "0" * 64}))
    with pytest.raises(ci.ImportRefused, match="did not grow"):
        ci.check_input_basis(str(d / "screen_input.jsonl"), str(pool), table)


def test_stage1_run_keyed_two_ways_is_refused(tmp_path):
    mixed = [{"work_key": "doi:10.3/y", "title": "C d", "label": "icf", "doc": "research"},
             {"openalex_id": "W9", "title": "E", "label": "out", "doc": "other"}]
    for sub, field in (("a", "work_key"), ("b", None)):
        d = _pool_run_dir(tmp_path / sub, header_field=field, labels=mixed)
        with pytest.raises(ci.ImportRefused, match="keyed"):
            ci.stage1_run_rows(str(d), str(d / "screen_input.jsonl"), "padme", "r", "s")


GEMMA, JEV = "google/gemma-4-26b-a4b-it", "typesafe/jev-1.13-20260917"
JOINT = {"llm_models": [GEMMA], "classifier_models": [JEV], "classifier_p_out_min": 0.95}


def _designb_dir(tmp_path, clf_model=JEV, finished=True):
    d = tmp_path / "2026-10-01-designB-stage1"
    _jsonl(d / "screen_input.jsonl", [
        {"work_key": "title:a b|2020", "openalex_id": "", "doi": "", "title": "A b",
         "year": "2020"},
        {"work_key": "doi:10.5/z", "openalex_id": "", "doi": "10.5/z", "title": "Z",
         "year": "2019"},
        {"work_key": "openalex:W7", "openalex_id": "W7", "doi": "", "title": "S", "year": ""}])
    _jsonl(d / "llm.jsonl", [
        {"work_key": "title:a b|2020", "label": "out", "doc": "research", "why": "",
         "model": GEMMA, "provider": "NextBit"},
        {"work_key": "doi:10.5/z", "label": "icf", "doc": "institutional", "why": "GCF",
         "model": GEMMA, "provider": "Parasail"},
        {"work_key": "openalex:W7", "label": "out", "doc": "research", "why": "",
         "model": GEMMA, "provider": "NextBit"}])
    _jsonl(d / "classifier.jsonl", [
        {"work_key": "title:a b|2020", "label": "out", "doc": "research", "p_out": 0.971234,
         "model": clf_model, "provider": "TypeSafe"},
        {"work_key": "doi:10.5/z", "label": "icf", "doc": "unknown", "p_out": 0.0,
         "model": clf_model, "provider": "TypeSafe"}])          # W7: classifier missing
    _jsonl(d / "screen_runs.jsonl", [
        {"started": "2026-10-01T09:00:00+00:00", "id_field": "work_key",
         "llm_prompt_sha256": "lp", "classifier_prompt_sha256": "cp"}])
    (d / "run.log").write_text("INFO labelled 2, unlabelled 1 (rerun to retry)\n"
                               if finished else "INFO round 1\n")
    return d


def test_designb_import_writes_one_row_per_labeller(tmp_path):
    d = _designb_dir(tmp_path)
    rows, half = ci.designb_rows(str(d), str(d / "screen_input.jsonl"), "designB", JOINT)
    assert half == 1, "W7 has no classifier label: left unscreened"
    assert [(r["work_key"], r["model"], r["label"], r["why"], r["machine"], r["prompt_sha256"])
            for r in rows] == [
        ("title:a b|2020", GEMMA, "out", "", "openrouter/NextBit", "lp"),
        ("title:a b|2020", JEV, "out", "p_out=0.9712", "openrouter/TypeSafe", "cp"),
        ("doi:10.5/z", GEMMA, "icf", "GCF", "openrouter/Parasail", "lp"),
        ("doi:10.5/z", JEV, "icf", "p_out=0.0000", "openrouter/TypeSafe", "cp")]
    assert {(r["stage"], r["labeller"], r["run_id"]) for r in rows} == {("1", "llm", "designB")}
    assert rows[3]["doc_type"] == "unknown" and rows[2]["doc_type"] == "institutional"
    assert rows[0]["source"] == "designB/llm.jsonl"
    assert rows[1]["source"] == "designB/classifier.jsonl"


def test_designb_import_is_idempotent_and_reads_the_rule_from_config(tmp_path):
    d = _designb_dir(tmp_path)
    table = str(tmp_path / "icf_screen.csv")
    args = ["--output", table, "stage1-designb", "--run-dir", str(d), "--allow-input-drift"]
    assert ci.main(args) == 0 and ci.main(args) == 0
    assert len(ics.read_table(table)) == 4


@pytest.mark.parametrize("kw, match", [({"clf_model": "typesafe/jev-9"}, "not in stage1_joint"),
                                       ({"finished": False}, "closing")])
def test_designb_import_refusals(tmp_path, kw, match):
    d = _designb_dir(tmp_path, **kw)
    with pytest.raises(ci.ImportRefused, match=match):
        ci.designb_rows(str(d), str(d / "screen_input.jsonl"), "designB", JOINT)


def test_designb_import_refuses_disagreeing_invocations(tmp_path):
    d = _designb_dir(tmp_path)
    _jsonl(d / "screen_runs.jsonl", [
        {"started": "a", "id_field": "work_key", "llm_prompt_sha256": "lp",
         "classifier_prompt_sha256": "cp"},
        {"started": "b", "id_field": "work_key", "llm_prompt_sha256": "lp2",
         "classifier_prompt_sha256": "cp"}])
    with pytest.raises(ci.ImportRefused, match="disagree"):
        ci.designb_rows(str(d), str(d / "screen_input.jsonl"), "designB", JOINT)


def test_import_refuses_to_fork_a_dvc_tracked_table(tmp_path):
    a, prompt = _archive(tmp_path)
    (tmp_path / "t.dvc").write_text("outs:\n- path: t\n")
    table = str(tmp_path / "t" / "icf_screen.csv")
    args = ["--output", table, "t1530", "--archive", str(a), "--stage2-prompt", str(prompt)]
    assert ci.main(args) == 1
    assert not (tmp_path / "t" / "icf_screen.csv").exists()
    assert ci.main(["--new-table"] + args) == 0
    assert len(ics.read_table(table)) == 10
