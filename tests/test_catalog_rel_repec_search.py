"""Ticket 1810: local replay of the REL query strings on the RePEc table, and its delivery."""

import csv
import json
import os

import _rel_local_query as lq
import catalog_rel_repec_search as rs
import pytest
import qa_rel_intake
import yaml

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def row(handle, title, abstract="", keywords="", jel="", year="2010", doi="", ttype="redif-paper"):
    return {"handle": handle, "template_type": ttype, "title": title, "abstract": abstract,
            "keywords": keywords, "jel": jel, "authors": "Doe, Jane; Roe, R.", "year": year,
            "creation_date": f"{year}-05-01" if year else "", "journal": "Some Series",
            "series_handle": ":".join(handle.split(":")[:3]).lower(), "volume": "", "issue": "",
            "pages": "", "number": "", "doi": doi, "language": "", "publication_status": "",
            "file_url": ""}


# --- the evaluator -------------------------------------------------------------

def test_fold_and_phrase_boundaries():
    t = lq.fold("Financement climatique: the Green-Climate Fund's REDD+ funds")
    assert lq.matches(t, "financement climatique")
    assert lq.matches(t, "Green Climate Fund")
    assert lq.matches(t, "REDD")
    assert lq.matches(t, "fund")            # plural "funds"
    assert not lq.matches(t, "clima")        # word boundary
    assert lq.matches(lq.fold("中国气候融资研究"), "气候融资")


def test_parse_precedence_and_evaluate():
    ast = lq.parse('("climate finance" OR "climate aid") AND ("cost of capital" OR guarantees) AND NOT "coal"')
    texts = [lq.fold(s) for s in (
        "climate finance and the cost of capital",
        "climate aid with guarantees but coal",
        "cost of capital only",
        "climate aid guarantees",
    )]
    hits = {p: set(v) for p, v in lq.phrase_hits(texts, lq.phrases(ast)).items()}
    assert lq.evaluate(ast, hits.__getitem__, lambda: set(range(4))) == {0, 3}


def test_parse_rejects_unbalanced():
    with pytest.raises(ValueError):
        lq.parse('("climate finance" OR "x"')


def test_jel_match_prefixes():
    assert lq.jel_match(["Q54", "F35"], [["Q54", "Q56"], ["F35", "O19"]])
    assert not lq.jel_match(["Q54"], [["Q54"], ["F2", "F3"]])
    assert lq.jel_match([" Q42", "F21"], [["Q4"], ["F2"]])


# --- the units, from the real configs ---------------------------------------------

@pytest.fixture(scope="module")
def units():
    with open(os.path.join(ROOT, "config", "rel_repec_search.yaml"), encoding="utf-8") as fh:
        return rs.plan_units(yaml.safe_load(fh))


def test_units_cover_every_source(units):
    ids = [u["query_id"] for u in units]
    assert len(ids) == len(set(ids))
    kinds = {u["kind"] for u in units}
    assert kinds == {"text", "jel_text", "jel"}
    assert "RP-RC-grid-IM-en" in ids and "RP-RC-grid-IM-fr" in ids
    assert "RP-RE-grid-JEL-en" in ids
    assert "RP-SUD-T1-en" in ids and "RP-SUD-T1-zh" in ids and "RP-SUD-gapfill-en" in ids
    assert "RP-JEL-climate-aid" in ids
    # SI rows become title searches of TUNING sentinels only
    sens = list(csv.DictReader(open(os.path.join(ROOT, "config", "rel_causal_sentinels.csv"),
                                    encoding="utf-8")))
    si = [u for u in units if u["formulation"] == "SI"]
    assert si
    holdout_titles = {s["title"] for s in sens if s["set"] == "holdout"}
    for u in si:
        assert not any(f'"{t}"' in u["query"] for t in holdout_titles)


def test_run_and_deliver_meets_the_contract(units, tmp_path):
    rows = [
        row("RePEc:aaa:wpaper:1", "Climate finance and the cost of capital in India",
            abstract="Derisking renewable investment.", jel="Q54; F35"),
        row("RePEc:aaa:wpaper:2", "Unrelated labour economics", jel="J31"),
        row("RePEc:bbb:journl:3", "Loss and damage finance", year="", doi=""),
        row("RePEc:bbb:journl:4", "Aid and environment", jel="F35; Q56", year="", doi="10.1000/ABC"),
        row("RePEc:bbb:journl:5", "", abstract="Climate finance without a title"),
    ]
    hits = rs.run_units(units, rows)
    assert 0 in hits["RP-SUD-T1-en"] and 0 in hits["RP-RC-cost_of_capital-IM-en"]
    assert 0 in hits["RP-JEL-climate-aid"] and 3 in hits["RP-JEL-climate-aid"]
    assert 2 in hits["RP-SUD-T4-en"]
    assert all(1 not in h for h in hits.values())
    out = tmp_path / rs.LANE / "2026-10-01"
    m = rs.deliver(units, hits, rows, str(out), "2026-10-01", "2026-10-01T10:00:00+00:00")
    assert m["counts"] == {"records": 2, "excluded": {"no_dedup_key": 1, "not_retrievable": 1}}
    recs = list(csv.DictReader(open(out / "records.csv", encoding="utf-8")))
    assert [r["record_id"] for r in recs] == ["RePEc:aaa:wpaper:1", "RePEc:bbb:journl:4"]
    r0 = recs[0]
    assert r0["query_id"] == r0["query_ids_all"].split(";")[0]
    assert r0["url"] == "https://econpapers.repec.org/RePEc:aaa:wpaper:1"
    assert r0["doc_type"] == "working-paper" and r0["first_author"] == "Doe, Jane"
    assert recs[1]["doi"] == "10.1000/abc" and recs[1]["url"] == "https://doi.org/10.1000/abc"
    flagged = {**row("RePEc:bre::node_1", "T"), "handle_valid": "0"}
    rec = rs.to_record(flagged, ["Q"], "2026-10-01")
    assert rec["url"] == "" and "malformed at source" in rec["lane_note"]
    assert rs.to_record({**flagged, "doi": "10.1000/x"}, ["Q"], "2026-10-01")["url"] == "https://doi.org/10.1000/x"
    bad = rs.to_record(row("RePEc:z:z:9", "T", doi="10.12/short"), ["Q"], "2026-10-01")
    assert bad["doi"] == "" and "malformed DOI" in bad["lane_note"]
    assert qa_rel_intake.main([str(out)]) == 0
    with pytest.raises(SystemExit):
        rs.deliver(units, hits, rows, str(out), "2026-10-01", "x")
    reg = list(csv.DictReader(open(out / "registry.csv", encoding="utf-8")))
    assert len(reg) == len(units) and all(r["completed"] == "true" for r in reg)
    assert json.load(open(out / "manifest.json"))["lane"] == rs.LANE


def test_sentinel_recall_positive_control(tmp_path):
    rows = [row("RePEc:x:y:1", "Low-carbon investment risks and de-risking", doi="10.1038/nclimate2112"),
            row("RePEc:x:y:2", "Coding error or statistical embellishment? reporting climate aid", year="2011")]
    sen = tmp_path / "s.csv"
    with open(sen, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, ["sentinel", "set", "year", "doi", "title"])
        w.writeheader()
        w.writerow({"sentinel": "C01", "set": "tuning", "year": "2014", "doi": "10.1038/NCLIMATE2112",
                    "title": "Low-carbon investment risks"})
        w.writerow({"sentinel": "S03", "set": "holdout", "year": "2011", "doi": "",
                    "title": "Coding error or statistical embellishment? Reporting climate aid"})
        w.writerow({"sentinel": "S99", "set": "holdout", "year": "2011", "doi": "", "title": "Absent"})
    res = rs.sentinel_recall(rows, {"RePEc:x:y:1": "Q1"}, [str(sen)])
    got = {r["sentinel"]: (r["in_mirror"], r["retrieved"]) for r in res}
    assert got == {"C01": (True, True), "S03": (True, False), "S99": (False, False)}
    summ = rs.summarize_sentinels(res)
    assert summ["reserve"]["s.csv"]["missed_in_mirror"] == ["S03"]
    assert summ["non_reserve"]["s.csv"]["retrieved"] == 1


def test_zero_hit_controls_show_each_and_group(units):
    rows = [row("RePEc:a:b:1", "Financement climatique et réseau"),
            row("RePEc:a:b:2", "تمويل المناخ")]
    keep = {}
    hits = rs.run_units(units, rows, keep=keep)
    ctl = {c["query_id"]: c for c in rs.zero_hit_controls(units, hits, keep["phrase_hits"], rows)}
    assert "RP-SUD-T1-ar" not in ctl                   # retrieved row 2
    g = ctl["RP-RC-grid-IM-fr"]["and_group_hits"].split("|")
    assert g[0] == "1" and g[1] == "0"                 # ICF block seen, mediator absent
    assert ctl["RP-SUD-T1-hi"]["titles_in_script"] == 0


def test_plan_matches_the_1652_entry_point():
    import catalog_rel_causal_search as cs
    causal = yaml.safe_load(open(os.path.join(ROOT, "config", "rel_causal_search.yaml"), encoding="utf-8"))
    fams = yaml.safe_load(open(os.path.join(ROOT, "config", "rel_causal_families.yaml"), encoding="utf-8"))
    sens = cs.load_sentinels(os.path.join(ROOT, "config", "rel_causal_sentinels.csv"))
    theirs = [(s["search_id"], s["query_string"]) for s in cs.plan_queries(causal, fams, sens)]
    ours = [(s["search_id"], s["query_string"]) for s in rs.plan_queries(causal, fams, sens)]
    assert ours == theirs


def test_no_phrase_match_across_fields():
    rows = [row("RePEc:a:b:1", "Aid and the climate", abstract="Finance flows to Africa")]
    texts = rs.folded_texts(rows)
    assert not lq.matches(texts[0], "climate finance")
    assert lq.matches(texts[0], "finance flow")


def test_indic_words_keep_their_vowel_signs():
    t = lq.fold("जलवायु वित्त और विकास")
    assert t == " जलवायु वित्त और विकास "
    assert lq.matches(t, "जलवायु वित्त")
    assert not lq.matches(t, "जलव")
    assert lq.fold("Financement climatique") == " financement climatique "
