"""Stage-2 / audit tables and their answers (ticket 1732)."""

import csv
import json

import _icf_screen as ics
import _rel_view as rv
import corpus_icf_stage2 as cs
import pytest

pytestmark = pytest.mark.domain_corpus

S2CFG = {"chunk_size": 2, "title_max_chars": 220, "abstract_max_chars": 650}


def _work(i, **kw):
    w = {"work_key": f"openalex:W{i}", "openalex_id": f"W{i}", "doi": "", "title": f"Title {i}",
         "year": "2020", "journal": "", "language": "fr", "abstract": "Résumé",
         "affiliation_countries": "SN;FR"}
    w.update(kw)
    return w


def _view_row(i, status):
    return {"work_key": f"openalex:W{i}", "status": status}


def test_select_pending_only():
    view = [_view_row(3, "pending_stage2"), _view_row(1, "stage1_out"),
            _view_row(2, "pending_stage2"), _view_row(4, "icf")]
    assert cs.select_pending(view) == ["openalex:W2", "openalex:W3"]


def test_chunks_in_1530_format(tmp_path):
    out = tmp_path / "s2"
    names = cs.write_chunks(str(out), [_work(1), _work(2), _work(3, year="")], S2CFG, {"kind": "build"})
    assert names == ["chunk01", "chunk02"]
    assert (out / "chunk01.txt").read_text(encoding="utf-8").startswith(
        "1. [fr | 2020 | ? | affiliations: SN, FR]\n   Title: Title 1\n   Abstract: Résumé\n2. [")
    assert json.loads((out / "chunk02.ids.json").read_text()) == ["openalex:W3"]
    works = list(csv.DictReader(open(out / "works.csv", encoding="utf-8")))
    assert [(w["chunk"], w["n"]) for w in works] == [("chunk01", "1"), ("chunk01", "2"), ("chunk02", "1")]
    assert works[2]["title_norm_year"] == "title 3|"
    with pytest.raises(cs.Stage2Error, match="already holds"):
        cs.write_chunks(str(out), [_work(1)], S2CFG, {})


def test_audit_sample_is_stratified_and_reproducible():
    view = ([_view_row(i, "icf") for i in range(50)] + [_view_row(100 + i, "aux") for i in range(5)]
            + [_view_row(200, "unsure_unresolved"), _view_row(300, "pending_stage2")])
    per = {"icf": 10, "aux": 3, "out": 4, "unsure": 2}
    a = cs.audit_sample(view, per, seed=7)
    assert a == cs.audit_sample(list(reversed(view)), per, seed=7), "order-independent"
    assert a != cs.audit_sample(view, per, seed=8)
    keys = set(a)
    assert len(a) == len(keys) == 10 + 3 + 1
    assert "openalex:W300" not in keys and "openalex:W200" in keys


def test_parse_appends_answers_and_refuses_malformed(tmp_path):
    out = tmp_path / "s2"
    cs.write_chunks(str(out), [_work(1), _work(2), _work(3)], S2CFG, {})
    (out / "chunk01.opus.txt").write_text("1|icf|research|SN|GCF readiness\n2|aux|research|?|\n")
    (out / "chunk02.opus.txt").write_text("")
    rows, _, report = cs.parse_answers(str(out), "opus", "2", "opus-x", "run1", "doudou", "llm",
                                    "p", "2026-10-01", "s2")
    assert [(r["work_key"], r["label"], r["studied_country"]) for r in rows] == [
        ("openalex:W1", "icf", "SN"), ("openalex:W2", "aux", "?")]
    assert report["chunk01"]["status"] == "complete" and report["chunk02"]["answered"] == 0
    table = str(tmp_path / "icf_screen.csv")
    assert ics.append_new(table, rows) == (2, 0)
    assert ics.append_new(table, rows) == (0, 2)
    (out / "chunk02.opus.txt").write_text("1|icf|research|?|x\n1|out|research|?|\n")
    with pytest.raises(cs.Stage2Error, match="refused"):
        cs.parse_answers(str(out), "opus", "2", "m", "r", "d", "llm", "p", "d", "s")


V2_PROMPT = ("# v2\n\n```\nWrite one line per record, in order, to <chunk>.opus.txt, format "
             "exactly:\nn|label|doc|studied|contrib|field|ctype|why\n```\n")


def test_parse_main_writes_icf_and_dimension_rows_from_v2_answers(tmp_path):
    """Ticket 1840: one v2 answer file feeds icf_screen and rel_dimensions, same keys."""
    out = tmp_path / "s2"
    cs.write_chunks(str(out), [_work(1), _work(2)], S2CFG, {})
    (out / "chunk01.opus.txt").write_text(
        "1|icf|research|SN|yes|economics|policy|GCF readiness\n2|out|other|?|na|na|na|\n")
    prompt = tmp_path / "v2.md"
    prompt.write_text(V2_PROMPT)
    (tmp_path / "rs").mkdir()
    table, dims = str(tmp_path / "rs" / "icf_screen.csv"), str(tmp_path / "rs" / "dims.csv")
    args = ["--table", table, "--dimensions-table", dims, "parse", "--chunk-dir", str(out),
            "--model", "opus", "--run-id", "r", "--machine", "d", "--prompt", str(prompt)]
    assert cs.main(args) == 0
    icf = ics.read_table(table)
    dim = ics.read_table(dims, schema=ics.DIMENSIONS)
    assert [(r["work_key"], r["label"], r["why"]) for r in icf] == [
        ("openalex:W1", "icf", "GCF readiness"), ("openalex:W2", "out", "")]
    assert [(r["work_key"], r["contrib"], r["field"], r["contrib_type"]) for r in dim] == [
        ("openalex:W1", "yes", "economics", "policy"), ("openalex:W2", "na", "na", "na")]
    assert {ics.key_of(r) for r in icf} == {ics.key_of(r) for r in dim}
    assert icf[0]["prompt_sha256"] == dim[0]["prompt_sha256"] == ics.stage2_prompt_sha256(
        str(prompt))
    assert cs.main(args) == 0, "idempotent"
    assert len(ics.read_table(dims, schema=ics.DIMENSIONS)) == 2


def test_parse_v1_answers_write_no_dimension_rows(tmp_path):
    out = tmp_path / "s2"
    cs.write_chunks(str(out), [_work(1)], S2CFG, {})
    (out / "chunk01.opus.txt").write_text("1|icf|research|SN|x\n")
    prompt = tmp_path / "v1.md"
    prompt.write_text("# v1\n\n```\nformat exactly:\nn|label|doc|studied|why\n```\n")
    table, dims = str(tmp_path / "icf_screen.csv"), str(tmp_path / "dims.csv")
    assert cs.main(["--table", table, "--dimensions-table", dims, "parse", "--chunk-dir",
                    str(out), "--model", "m", "--run-id", "r", "--machine", "d",
                    "--prompt", str(prompt), "--new-table"]) == 0
    assert len(ics.read_table(table)) == 1 and not (tmp_path / "dims.csv").exists()


@pytest.mark.parametrize("answers, fields", [
    # a version-1 file whose why holds pipes, read as version 2 (red team, PR 1652)
    ("1|icf|research|SN|because a|b|c|d\n2|aux|research|?|x|y|z|w\n", ics.V2_FIELDS),
    # a version-2 file read as version 1
    ("1|icf|research|SN|yes|economics|policy|GCF\n2|out|other|?|na|na|na|\n", ics.V1_FIELDS),
])
def test_parse_refuses_an_answer_file_in_the_other_format(tmp_path, answers, fields):
    """Both tables are append-only: a wrong --prompt must refuse, not write."""
    out = tmp_path / "s2"
    cs.write_chunks(str(out), [_work(1), _work(2)], S2CFG, {})
    (out / "chunk01.opus.txt").write_text(answers)
    with pytest.raises(cs.Stage2Error, match="answer file"):
        cs.parse_answers(str(out), "opus", "2", "m", "r", "d", "llm", "p", "d", "s", fields)


def test_parse_counts_na_off_rule_without_refusing(tmp_path):
    out = tmp_path / "s2"
    cs.write_chunks(str(out), [_work(1), _work(2)], S2CFG, {})
    (out / "chunk01.opus.txt").write_text(
        "1|out|research|SN|yes|economics|policy|\n2|aux|other|?|BOGUS|na|na|\n")
    rows, dims, report = cs.parse_answers(str(out), "opus", "2", "m", "r", "d", "llm", "p",
                                          "d", "s", ics.V2_FIELDS)
    assert len(rows) == len(dims) == 2
    assert report["chunk01"]["na_off_rule"] == 1 and report["chunk01"]["unknown_dimension"] == 1


def test_cohen_kappa_known_values():
    perfect = cs.cohen_kappa([("icf", "icf"), ("out", "out")])
    assert perfect["kappa"] == 1.0 and perfect["observed_agreement"] == 1.0
    # 2x2: agree 20 icf, 15 out; disagree 5+10 -> po=0.7, pe=(25*30+25*20)/50^2=0.5, kappa=0.4
    pairs = [("icf", "icf")] * 20 + [("icf", "out")] * 5 + [("out", "icf")] * 10 + [("out", "out")] * 15
    res = cs.cohen_kappa(pairs)
    assert res["kappa"] == 0.4 and res["confusion"]["icf"]["out"] == 5


def test_agreement_pairs_audit_run_with_stage2():
    pool = [{"work_key": f"openalex:W{i}", "all_openalex_ids": f"W{i}", "all_dois": ""}
            for i in range(3)]

    def lab(i, stage, label, run_id="r"):
        return {"work_key": f"openalex:W{i}", "openalex_id": f"W{i}", "doi": "",
                "stage": stage, "label": label, "run_id": run_id}
    labels = [lab(0, "2", "icf"), lab(0, "audit", "icf", "a1"), lab(1, "2", "out"),
              lab(1, "audit", "icf", "a1"), lab(2, "2", "aux"), lab(2, "audit", "aux", "a0")]
    res = cs.agreement(pool, labels, "a1")
    assert res["n"] == 2 and res["by_stage2_label"] == {"icf": {"n": 1, "agree": 1},
                                                          "out": {"n": 1, "agree": 0}}


@pytest.mark.parametrize("cmd", [["build", "--output-dir", "OUT"],
                                 ["agreement", "--audit-run-id", "a", "--output", "OUT"]])
def test_missing_table_is_a_clean_error(tmp_path, cmd):
    missing = str(tmp_path / "none" / "icf_screen.csv")
    args = [a.replace("OUT", str(tmp_path / "o")) for a in cmd]
    assert cs.main(["--pool", str(tmp_path / "pool.csv"), "--table", missing] + args) == 1


def test_parse_refuses_to_fork_a_dvc_tracked_table(tmp_path):
    out = tmp_path / "s2"
    cs.write_chunks(str(out), [_work(1)], S2CFG, {})
    # The default wrapper (config stage2.prompt) is version 2 since ticket 1840.
    (out / "chunk01.opus.txt").write_text("1|icf|research|SN|yes|economics|policy|x\n")
    (tmp_path / "rs.dvc").write_text("outs:\n- path: rs\n")
    table = str(tmp_path / "rs" / "icf_screen.csv")
    dims = str(tmp_path / "rs" / "rel_dimensions.csv")
    base = ["--table", table, "--dimensions-table", dims, "parse", "--chunk-dir", str(out),
            "--model", "m", "--run-id", "r", "--machine", "d"]
    assert cs.main(base) == 1
    assert not (tmp_path / "rs").exists()
    assert cs.main(base + ["--new-table"]) == 0
    assert len(ics.read_table(table)) == 1
    assert len(ics.read_table(dims, schema=ics.DIMENSIONS)) == 1


def test_build_sends_stage1_aux_to_stage2_under_the_config_rule(tmp_path):
    # Author decision 2026-09-30: stage 2 rereads icf, unsure and aux; only out leaves.
    pool = tmp_path / "pool.csv"
    with open(pool, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rv.POOL_FIELDS, restval="")
        w.writeheader()
        for i in range(1, 5):
            w.writerow({**_work(i), "all_openalex_ids": f"W{i}"})
    table = str(tmp_path / "icf_screen.csv")
    ics.append_rows(table, [
        {"work_key": f"openalex:W{i}", "openalex_id": f"W{i}", "doi": "",
         "title_norm_year": f"title {i}|2020", "stage": "1", "labeller": "llm", "model": "qwen",
         "prompt_sha256": "p", "run_id": "r", "machine": "padme", "label": label,
         "doc_type": "research", "studied_country": "", "why": "", "labelled_at": "2026-09-29",
         "source": "s"}
        for i, label in ((1, "icf"), (2, "aux"), (3, "out"), (4, "unsure"))])
    out = tmp_path / "s2"
    assert cs.main(["--pool", str(pool), "--table", table, "build", "--output-dir", str(out)]) == 0
    keys = [r["work_key"] for r in csv.DictReader(open(out / "works.csv", encoding="utf-8"))]
    assert keys == ["openalex:W1", "openalex:W2", "openalex:W4"]
    assert json.loads((out / "build.json").read_text())["rule"]["stage1_exit_labels"] == ["out"]
