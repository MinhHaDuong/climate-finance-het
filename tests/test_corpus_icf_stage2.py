"""Stage-2 / audit tables and their answers (ticket 1732)."""

import csv
import json

import _icf_screen as ics
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
    rows, report = cs.parse_answers(str(out), "opus", "2", "opus-x", "run1", "doudou", "llm",
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
