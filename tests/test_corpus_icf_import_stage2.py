"""Importing the 2026-10-06/07 stage-2 labels of ticket 1733 into icf_screen (ticket 1995).

Sol ``labels.jsonl`` runs, the Fable relabelling of the unsure works, the
agreement rule over the Opus check, the 72 front-matter rows, and the
design-B finish read from ``summary.json``.
"""

import csv
import hashlib
import json

import _icf_screen as ics
import _rel_view as rv
import corpus_icf_import as ci
import pytest

pytestmark = pytest.mark.domain_corpus

SOL = "gpt-6.1-sol"
TEMPLATE = "strict wrapper {records}\n"
SHA = hashlib.sha256(TEMPLATE.encode()).hexdigest()
ESC = "doi:10.1002/(sici)1(1996)8:6&lt;735::aid&gt;3.0.co;2-8"   # a pool key, escaped as is


def _jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _pool(tmp_path, keys=("doi:10.1/a", "doi:10.1/b", "openalex:W3", ESC)):
    path = tmp_path / "pool.csv"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rv.POOL_FIELDS, lineterminator="\n")
        w.writeheader()
        for i, k in enumerate(keys):
            oa = k.split(":", 1)[1] if k.startswith("openalex:") else f"W{100 + i}"
            w.writerow({**{f: "" for f in rv.POOL_FIELDS}, "work_key": k, "openalex_id": oa,
                        "all_openalex_ids": oa, "doi": k[4:] if k.startswith("doi:") else "",
                        "title": f"Title {i}", "year": "2020"})
    return path


def _lab(key, label, at, run_id="r1", **kw):
    return {"work_key": key, "label": label, "doc": "research", "studied": "?", "why": "",
            "run_id": run_id, "model": SOL, "effort": "low", "tier": "flex", "chunk": 0,
            "prompt_sha256": SHA, "labelled_at": at, **kw}


def _sol_run(tmp_path, name, run_id, labels):
    d = tmp_path / name
    _jsonl(d / "labels.jsonl", labels)
    (d / "prompt_template.txt").write_text(TEMPLATE, encoding="utf-8")
    (d / "manifest.json").write_text(json.dumps({
        "run_id": run_id, "model": SOL, "effort": "low", "tier": "flex", "prompt_sha256": SHA}))
    return d


def _two_runs(tmp_path):
    a = _sol_run(tmp_path, "sol-a", "r1", [
        _lab("doi:10.1/a", "aux", "2026-10-06T15:00:00Z"),
        _lab("doi:10.1/b", "unsure", "2026-10-06T16:00:00Z", why="no abstract"),
        _lab(ESC, "out", "2026-10-06T15:30:00Z")])
    b = _sol_run(tmp_path, "sol-b", "r2", [
        _lab("doi:10.1/a", "icf", "2026-10-06T17:00:00Z", run_id="r2"),   # overlap: later
        _lab("openalex:W3", "out", "2026-10-06T14:00:00Z", run_id="r2"),
        _lab("openalex:W3", "icf", "2026-10-06T18:00:00Z", run_id="r2")])  # repeat in run
    return a, b


def test_sol_rows_are_written_in_labelled_at_order_and_keep_byte_exact_keys(tmp_path):
    a, b = _two_runs(tmp_path)
    pool = ci.pool_by_key(str(_pool(tmp_path)))
    rows, report = ci.sol_rows([str(a), str(b)], pool)
    assert [(r["work_key"], r["run_id"], r["label"]) for r in rows] == [
        ("doi:10.1/a", "r1", "aux"), (ESC, "r1", "out"), ("doi:10.1/b", "r1", "unsure"),
        ("doi:10.1/a", "r2", "icf"), ("openalex:W3", "r2", "icf")]
    assert report["superseded_in_run"] == {"r1": 0, "r2": 1}
    r = rows[0]
    assert (r["stage"], r["labeller"], r["model"], r["prompt_sha256"], r["machine"]) == (
        "2", "llm", SOL, SHA, "openai/flex")
    assert r["source"] == "sol-a/labels.jsonl" and r["openalex_id"] == "W100"
    assert r["title_norm_year"].endswith("|2020")
    assert rows[1]["work_key"] == ESC, "the escaped key is the pool's key: never unescaped"


def test_sol_import_reproduces_the_latest_label_in_the_view_and_is_idempotent(tmp_path):
    a, b = _two_runs(tmp_path)
    pool_path = _pool(tmp_path)
    table = str(tmp_path / "icf_screen.csv")
    args = ["--output", table, "stage2-sol", "--run-dir", str(a), "--run-dir", str(b),
            "--pool", str(pool_path)]
    assert ci.main(args) == 0
    first = open(table, "rb").read()
    assert ci.main(args) == 0 and open(table, "rb").read() == first
    labels = ics.read_table(table)
    matched, _, _ = rv.match_labels(rv.read_pool(str(pool_path)), labels)
    last = {rv.read_pool(str(pool_path))[i]["work_key"]: [x for x in labs if x["stage"] == "2"][-1]
            ["label"] for i, labs in matched.items()}
    assert last == {"doi:10.1/a": "icf", "doi:10.1/b": "unsure", "openalex:W3": "icf",
                    ESC: "out"}


@pytest.mark.parametrize("bad, match", [
    ({"work_key": "doi:10.1/zz"}, "not a pool work_key"),
    ({"work_key": ESC.replace("&lt;", "<").replace("&gt;", ">")}, "not a pool work_key"),
    ({"model": "gpt-other"}, "disagree with manifest"),
    ({"prompt_sha256": "x" * 64}, "disagree with manifest"),
    ({"label": "maybe"}, "label"),
    ({"labelled_at": "2026-10-06 15:00"}, "labelled_at"),
])
def test_sol_rows_refusals(tmp_path, bad, match):
    d = _sol_run(tmp_path, "sol-a", "r1", [{**_lab("doi:10.1/a", "aux", "2026-10-06T15:00:00Z"),
                                            **bad}])
    with pytest.raises(ci.ImportRefused, match=match):
        ci.sol_rows([str(d)], ci.pool_by_key(str(_pool(tmp_path))))


def test_sol_rows_refuse_a_template_that_is_not_the_manifest_hash(tmp_path):
    d = _sol_run(tmp_path, "sol-a", "r1", [_lab("doi:10.1/a", "aux", "2026-10-06T15:00:00Z")])
    (d / "prompt_template.txt").write_text("another wrapper", encoding="utf-8")
    with pytest.raises(ci.ImportRefused, match="prompt_template"):
        ci.sol_rows([str(d)], ci.pool_by_key(str(_pool(tmp_path))))


# ── Fable relabelling and the agreement rule ─────────────


FABLE = "anthropic/claude-fable-5.1"


def _relabel_dir(tmp_path):
    """Three unsure works sent to Fable in sorted order; the second answer is off-vocabulary."""
    d = tmp_path / "unsure-fable"
    d.mkdir()
    (d / "summary.json").write_text(json.dumps({"model": FABLE, "effort": "low"}))
    (d / "chunk00.txt").write_text(
        "1|icf|institutional|global|Adaptation finance gap\n"
        "2|other|other|?|\n"
        "3|out|research|?|\n", encoding="utf-8")
    (d / "fable_labels.json").write_text(json.dumps({
        "doi:10.1/a": {"label": "icf", "why": "Adaptation finance gap"},
        "openalex:W3": {"label": "out", "why": ""}}))
    return d


def _table_with_sol(tmp_path, labels=("unsure", "unsure", "unsure")):
    pool_path = _pool(tmp_path)
    run = _sol_run(tmp_path, "sol-a", "r1", [
        _lab(k, lab, f"2026-10-06T1{i}:00:00Z")
        for i, (k, lab) in enumerate(zip(("doi:10.1/a", "doi:10.1/b", "openalex:W3"), labels))])
    table = str(tmp_path / "icf_screen.csv")
    assert ci.main(["--output", table, "stage2-sol", "--run-dir", str(run),
                    "--pool", str(pool_path)]) == 0
    return table, pool_path


def _template(tmp_path):
    p = tmp_path / "prompt_template.txt"
    p.write_text(TEMPLATE, encoding="utf-8")
    return p


def test_relabel_rows_align_answers_and_carry_doc_and_country(tmp_path):
    table, pool_path = _table_with_sol(tmp_path)
    rows = ci.relabel_rows(str(_relabel_dir(tmp_path)), ics.read_table(table),
                           ci.pool_by_key(str(pool_path)), "fable-run", SHA,
                           "2026-10-06T22:27:27Z", "openrouter")
    assert [(r["work_key"], r["label"], r["doc_type"], r["studied_country"], r["why"])
            for r in rows] == [
        ("doi:10.1/a", "icf", "institutional", "global", "Adaptation finance gap"),
        ("openalex:W3", "out", "research", "?", "")]
    assert {(r["stage"], r["model"], r["run_id"], r["prompt_sha256"]) for r in rows} == {
        ("2", FABLE, "fable-run", SHA)}
    assert rows[0]["source"] == "unsure-fable/chunk00.txt"


def test_relabel_rows_refuse_a_misaligned_answer_file(tmp_path):
    table, pool_path = _table_with_sol(tmp_path)
    d = _relabel_dir(tmp_path)
    (d / "chunk00.txt").write_text("1|icf|institutional|global|Something else\n2|other|other|?|\n"
                                   "3|out|research|?|\n", encoding="utf-8")
    with pytest.raises(ci.ImportRefused, match="align"):
        ci.relabel_rows(str(d), ics.read_table(table), ci.pool_by_key(str(pool_path)),
                        "fable-run", SHA, "t", "openrouter")


def test_relabel_rows_replace_unsure_only(tmp_path):
    table, pool_path = _table_with_sol(tmp_path, labels=("aux", "unsure", "unsure"))
    with pytest.raises(ci.ImportRefused, match="unsure"):
        ci.relabel_rows(str(_relabel_dir(tmp_path)), ics.read_table(table),
                        ci.pool_by_key(str(pool_path)), "fable-run", SHA, "t", "openrouter")


def _with_fable(tmp_path):
    table, pool_path = _table_with_sol(tmp_path)
    tmpl = _template(tmp_path)
    assert ci.main(["--output", table, "stage2-relabel", "--run-dir",
                    str(_relabel_dir(tmp_path)), "--run-id", "fable-run", "--prompt-template",
                    str(tmpl), "--labelled-at", "2026-10-06T22:27:27Z",
                    "--pool", str(pool_path)]) == 0
    return table, pool_path


def test_agree_rule_keeps_icf_only_when_the_check_agrees(tmp_path):
    table, pool_path = _with_fable(tmp_path)
    checks = tmp_path / "opus-check" / "opus.json"
    checks.parent.mkdir()
    checks.write_text(json.dumps({"doi:10.1/a": "aux"}))
    rows = ci.agree_rule_rows(str(checks), "anthropic/claude-opus-5.5", ics.read_table(table),
                              "fable-run", "rule-run", "2026-10-07T08:52:43Z")
    (r,) = rows
    assert (r["work_key"], r["label"], r["labeller"], r["model"], r["run_id"]) == (
        "doi:10.1/a", "unsure", "human", "author-decision", "rule-run")
    assert r["prompt_sha256"] == hashlib.sha256(ci.AGREE_RULE.encode()).hexdigest()
    assert r["doc_type"] == "institutional" and r["studied_country"] == "global"
    assert "claude-opus-5.5 aux" in r["why"] and r["source"] == "opus-check/opus.json"
    checks.write_text(json.dumps({"doi:10.1/a": "icf"}))
    (r,) = ci.agree_rule_rows(str(checks), "anthropic/claude-opus-5.5", ics.read_table(table),
                              "fable-run", "rule-run", "t")
    assert r["label"] == "icf"


def test_agree_rule_refuses_checks_that_are_not_the_relabelled_icf(tmp_path):
    table, _ = _with_fable(tmp_path)
    checks = tmp_path / "opus.json"
    for bad in ({}, {"doi:10.1/a": "icf", "openalex:W3": "icf"}, {"doi:10.1/a": None}):
        checks.write_text(json.dumps(bad))
        with pytest.raises(ci.ImportRefused):
            ci.agree_rule_rows(str(checks), "m", ics.read_table(table), "fable-run", "rr", "t")


def test_agree_rule_import_sets_the_final_label_and_is_idempotent(tmp_path):
    table, pool_path = _with_fable(tmp_path)
    checks = tmp_path / "opus.json"
    checks.write_text(json.dumps({"doi:10.1/a": "unsure"}))
    args = ["--output", table, "stage2-agree-rule", "--checks", str(checks), "--check-model",
            "anthropic/claude-opus-5.5", "--relabel-run-id", "fable-run", "--run-id", "rule-run",
            "--labelled-at", "2026-10-07T08:52:43Z"]
    assert ci.main(args) == 0 and ci.main(args) == 0
    labels = ics.read_table(table)
    s2 = [x for x in labels if x["stage"] == "2" and x["work_key"] == "doi:10.1/a"]
    assert [x["label"] for x in s2] == ["unsure", "icf", "unsure"]
    assert len(labels) == 3 + 2 + 1


# ── The 72 front-matter rows and the design-B finish ─────


def test_rows_file_is_appended_with_its_own_ids_dropped(tmp_path):
    side = str(tmp_path / "side" / "rows.csv")
    row = {"work_key": "openalex:W3", "openalex_id": "W3", "doi": "", "title_norm_year": "",
           "stage": "2", "labeller": "human", "model": "author-decision", "prompt_sha256": "p",
           "run_id": "t1733-frontmatter-exclusion", "machine": "padme", "label": "out",
           "doc_type": "other", "studied_country": "", "why": "front matter",
           "labelled_at": "2026-10-06", "source": "x"}
    ics.append_new(side, [row], "side", new_table=True)
    pool_path = _pool(tmp_path)
    table = str(tmp_path / "icf_screen.csv")
    args = ["--output", table, "rows", "--rows-file", side, "--pool", str(pool_path)]
    assert ci.main(args) == 0 and ci.main(args) == 0
    (got,) = ics.read_table(table)
    assert {k: got[k] for k in row} == row


def test_rows_file_refuses_rows_that_match_no_pool_work(tmp_path):
    side = str(tmp_path / "side" / "rows.csv")
    ics.append_new(side, [{"work_key": "openalex:W999", "openalex_id": "W999", "stage": "2",
                           "labeller": "human", "model": "m", "prompt_sha256": "p",
                           "run_id": "r", "machine": "padme", "label": "out",
                           "doc_type": "other", "labelled_at": "d", "source": "s"}],
                   "side", new_table=True)
    with pytest.raises(ci.ImportRefused, match="no pool work"):
        ci.side_table_rows(side, rv.read_pool(str(_pool(tmp_path))))


def test_designb_run_finished_by_its_summary_without_a_closing_log_line(tmp_path):
    d = tmp_path / "designB"
    (d).mkdir()
    (d / "run.log").write_text("INFO round 1: 2000/16 works sent\n")
    assert not ci.designb_finished(str(d))
    (d / "summary.json").write_text(json.dumps({"stopped": "cap", "finished": "2026-10-06"}))
    assert not ci.designb_finished(str(d)), "a run stopped by its cap is not finished"
    (d / "summary.json").write_text(json.dumps({"stopped": "", "finished": "2026-10-06"}))
    assert ci.designb_finished(str(d))
