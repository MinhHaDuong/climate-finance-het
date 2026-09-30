"""Yield, sentinel recall, judge and delivery of the causal-map lane (ticket 1652)."""

import csv
import gzip
import json
import os
import types

import corpus_rel_causal_judge as judge
import corpus_rel_causal_yield as cy
import pytest

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(__file__))
REG = ["search_id", "question", "question_type", "group", "formulation", "language",
       "platform", "query_string", "filter", "run_at", "n_expected", "n_received",
       "pages", "cost_usd", "completed", "stop_reason"]
T1 = "Climate finance and the electricity grid in Africa"
T2 = "Aid fungibility in the energy sector of developing countries"


def _run_dir(path, platform, searches, recs):
    os.makedirs(path)
    with open(path / "registry.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, REG)
        w.writeheader()
        for sid, q, form, n in searches:
            w.writerow({"search_id": sid, "question": q, "question_type": "family", "group": 1,
                        "formulation": form, "language": "en", "platform": platform,
                        "query_string": f"q {sid}", "filter": f"f {sid}", "run_at": "2026-09-30T16:00:00+00:00",
                        "n_expected": n, "n_received": n, "pages": 1, "cost_usd": 0.001,
                        "completed": True, "stop_reason": ""})
        w.writerow({"search_id": "EL-x", "question": "grid", "platform": "econlit",
                    "stop_reason": "not run"})
    with gzip.open(path / "results.jsonl.gz", "wt", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")


@pytest.fixture
def lane(tmp_path):
    _run_dir(tmp_path / "oa", "openalex",
             [("RC-grid-IM-en", "grid", "IM", 2), ("RC-grid-IO-en", "grid", "IO", 1),
              ("RC-fiscal_substitution-IM-en", "fiscal_substitution", "IM", 1)],
             [{"search_id": "RC-grid-IM-en", "openalex_id": "W1", "doi": "10.1/a", "title": T1,
               "year": 2020, "abstract": "x"},
              {"search_id": "RC-grid-IM-en", "openalex_id": "W2", "doi": "", "title": T2, "year": 2019},
              {"search_id": "RC-grid-IO-en", "openalex_id": "W1", "doi": "10.1/a", "title": T1, "year": 2020},
              {"search_id": "RC-fiscal_substitution-IM-en", "openalex_id": "W2", "doi": "",
               "title": T2, "year": 2019}])
    _run_dir(tmp_path / "eds", "bibCNRS EDS (RePEc)",
             [("EDS-RePEc-grid-IM-en", "grid", "IM", 2)],
             [{"search_id": "EDS-RePEc-grid-IM-en", "eds_an": "edsrep.1", "doi": "",
               "title": T1.upper() + "!", "year": 2020},
              {"search_id": "EDS-RePEc-grid-IM-en", "eds_an": "edsrep.2", "doi": "10.9/wp",
               "title": "A working paper on transmission lines and donors", "year": 2025}])
    with open(tmp_path / "refined.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, ["source", "source_id", "doi", "title", "year", "abstract"])
        w.writeheader()
        w.writerow({"source": "openalex", "source_id": "W1", "doi": "10.1/a", "title": T1,
                    "year": "2020", "abstract": "climate finance for transmission lines"})
    with gzip.open(tmp_path / "sud.jsonl.gz", "wt", encoding="utf-8") as fh:
        fh.write(json.dumps({"openalex_id": "W2", "doi": "", "title": T2, "year": 2019}) + "\n")
    with open(tmp_path / "sent.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, ["sentinel", "family", "set", "source", "lang", "year", "doi",
                                "openalex_id", "title"])
        w.writeheader()
        w.writerow({"sentinel": "C1", "family": "grid", "set": "holdout", "source": "t",
                    "lang": "en", "year": "2020", "doi": "10.1/A", "openalex_id": "W1", "title": T1})
        w.writerow({"sentinel": "C2", "family": "grid", "set": "tuning", "source": "t",
                    "lang": "en", "year": "2011", "doi": "10.5/none", "openalex_id": "W9", "title": "Absent"})
    return tmp_path


def _args(p, labels=None):
    return types.SimpleNamespace(
        run_dir=str(p / "oa"), eds_dir=str(p / "eds"), refined=str(p / "refined.csv"),
        unified=str(p / "refined.csv"), sud_results=[str(p / "sud.jsonl.gz")], labels=labels,
        families=os.path.join(ROOT, "config", "rel_causal_families.yaml"),
        sentinels=str(p / "sent.csv"),
        search_config=os.path.join(ROOT, "config", "rel_causal_search.yaml"),
        archive_path="/archive/x", manifest_sha256="abc", output_dir=str(p / "out"))


def _csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_work_keys_join_doi_openalex_and_title():
    recs = cy.assign_work_keys([
        {"doi": "10.1/a", "openalex_id": "W1", "title": T1, "year": 2020},
        {"doi": "", "openalex_id": "W1", "title": T1, "year": 2020},
        {"doi": "", "openalex_id": "", "eds_an": "e", "title": T1.lower(), "year": 2020},
        {"doi": "", "openalex_id": "", "eds_an": "f", "title": "short", "year": 2020}])
    assert [r["work_key"] for r in recs] == ["doi:10.1/a"] * 3 + ["an:f"]


def test_yields_reference_sets_uniqueness_and_delivery(lane):
    assert cy.run(_args(lane)) == 0
    out = lane / "out"
    by_lane = {r["lane"]: r for r in _csv(out / "yield_by_lane.csv")}
    assert by_lane["openalex"]["raw_hits"] == "4" and by_lane["openalex"]["unique_works"] == "2"
    assert by_lane["openalex"]["absent_refined"] == "1" and by_lane["openalex"]["absent_sud"] == "1"
    assert by_lane["openalex"]["absent_all_three"] == "0"
    assert by_lane["eds"]["unique_works"] == "2" and by_lane["eds"]["absent_all_three"] == "1"
    forms = {(r["lane"], r["group"]): r for r in _csv(out / "yield_by_formulation.csv")}
    assert forms[("openalex", "IM|en")]["only_this_group"] == "1"   # W2 only by IM
    assert forms[("openalex", "IO|en")]["only_this_group"] == "0"
    rows = _csv(out / "delivery.csv")
    assert len(rows) == 6 and set(rows[0]) == set(cy.DELIVERY_FIELDS)
    assert {r["lane"] for r in rows} == {"1652"}
    assert rows[0]["archive_path"] == "/archive/x" and rows[0]["manifest_sha256"] == "abc"
    eds_title_match = [r for r in rows if r["eds_an"] == "edsrep.1"][0]
    assert eds_title_match["work_key"] == "doi:10.1/a" and eds_title_match["in_refined"] == "True"
    rec = {r["sentinel"]: r for r in _csv(out / "sentinel_recall.csv")}
    assert rec["C1"]["found_own_family"] == "True" and rec["C1"]["found_eds"] == "True"
    assert rec["C2"]["found_any_search"] == "False"
    with open(out / "judge_input.jsonl", encoding="utf-8") as fh:
        pairs = [json.loads(line) for line in fh]
    assert len(pairs) == 4  # (W1,grid) (W2,grid) (W2,fiscal) (wp,grid)
    assert all(p["mechanism"] for p in pairs)


def test_labels_count_relevant_per_question_and_feed_the_outcomes(lane):
    assert cy.run(_args(lane)) == 0
    labels = lane / "labels.jsonl"
    with open(labels, "w", encoding="utf-8") as fh:
        for pid, lab in (("grid::doi:10.1/a", "relevant"), ("grid::oa:W2", "not"),
                         ("fiscal_substitution::oa:W2", "relevant")):
            fh.write(json.dumps({"pair_id": pid, "label": lab}) + "\n")
    args = _args(lane, labels=str(labels))
    args.output_dir = str(lane / "out2")
    assert cy.run(args) == 0
    q = {r["group"]: r for r in _csv(lane / "out2" / "yield_by_question.csv") if r["lane"] == "openalex"}
    assert q["grid"]["relevant"] == "1" and q["fiscal_substitution"]["relevant"] == "1"
    out = {r["question"]: r for r in _csv(lane / "out2" / "family_outcome_inputs.csv")}
    assert out["grid"]["relevant_recognised_by_probe"] == "1"
    assert out["fiscal_substitution"]["relevant_absent_refined"] == "1"
    rows = _csv(lane / "out2" / "delivery.csv")
    assert {r["family_relevance"] for r in rows} == {"relevant", "not", ""}


def test_intake_delivery_has_one_record_per_work_and_lists_the_duplicates(lane):
    base = lane / "base.json"
    base.write_text(json.dumps({"lane": "t1652-causal-econlit", "ticket": "1652",
                                "delivery": "2026-09-30", "needs_human": [], "supersedes": None}))
    args = _args(lane)
    args.intake_dir, args.manifest_base = str(lane / "intake"), str(base)
    assert cy.run(args) == 0
    recs = _csv(lane / "intake" / "records.csv")
    exc = _csv(lane / "intake" / "excluded.csv")
    reg = _csv(lane / "intake" / "registry.csv")
    assert len(recs) == 3 and len({r["record_id"] for r in recs}) == 3
    assert len(recs) + len(exc) == 6 and {e["reason"] for e in exc} == {"duplicate_in_lane"}
    w1 = [r for r in recs if r["record_id"] == "1652:doi:10.1/a"][0]
    assert w1["platform"] == "openalex" and w1["all_query_ids"].count("|") == 2
    assert [r["platform"] for r in recs if r["doi"] == "10.9/wp"] == ["bibcnrs_eds_repec"]
    assert {r["completed"] for r in reg} == {"true", "false"}
    assert all(r["stop_reason"] for r in reg if r["completed"] == "false")
    manifest = json.loads((lane / "intake" / "manifest.json").read_text())
    assert manifest["counts"] == {"records": 3, "excluded": {"duplicate_in_lane": 3}}
    assert manifest["coverage"] == "incomplete"  # the EconLit rows were not run


def test_a_later_run_directory_supersedes_the_ids_it_reran(lane):
    _run_dir(lane / "oa2", "openalex", [("RC-grid-IO-en", "grid", "IO", 1)],
             [{"search_id": "RC-grid-IO-en", "openalex_id": "W7", "doi": "10.7/new",
               "title": "A rerun record", "year": 2024}])
    args = _args(lane)
    args.run_dir = [str(lane / "oa"), str(lane / "oa2")]
    assert cy.run(args) == 0
    rows = _csv(lane / "out" / "delivery.csv")
    io = [r for r in rows if r["search_id"] == "RC-grid-IO-en"]
    assert [r["doi"] for r in io] == ["10.7/new"]
    by_search = {r["group"] for r in _csv(lane / "out" / "yield_by_search.csv")}
    assert "RC-grid-IO-en" in by_search and len(rows) == 6


def test_an_unfinished_rerun_with_fewer_records_does_not_supersede(lane):
    _run_dir(lane / "oa2", "openalex", [("RC-grid-IM-en", "grid", "IM", 1)],
             [{"search_id": "RC-grid-IM-en", "openalex_id": "W7", "doi": "10.7/new",
               "title": "A rerun record", "year": 2024}])
    reg = _csv(lane / "oa2" / "registry.csv")
    reg[0]["completed"], reg[0]["stop_reason"] = "False", "error: RuntimeError"
    with open(lane / "oa2" / "registry.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, REG)
        w.writeheader()
        w.writerows(reg)
    args = _args(lane)
    args.run_dir = [str(lane / "oa"), str(lane / "oa2")]
    assert cy.run(args) == 0
    im = [r for r in _csv(lane / "out" / "delivery.csv") if r["search_id"] == "RC-grid-IM-en"]
    assert sorted(r["openalex_id"] for r in im) == ["W1", "W2"]


def test_judge_batches_one_mechanism_and_parses_labels(tmp_path):
    recs = [{"pair_id": f"{q}::{i}", "question": q, "mechanism": f"M {q}", "title": f"t{i}"}
            for q in ("b", "a") for i in range(3)]
    batches = judge.batches_by_question(recs, 2)
    assert [len(b) for b in batches] == [2, 1, 2, 1]
    assert all(len({r["question"] for r in b}) == 1 for b in batches)
    cfg = {"prompt_template": "{question}|{mechanism}|{answer_format}|{records}",
           "answer_format": "F", "title_max_chars": 50, "abstract_max_chars": 50,
           "batch_size": 2, "workers": 1, "model": "m", "max_tokens": 10}
    assert judge.build_prompt(batches[0], cfg).startswith("a|M a|F|")
    got = judge.parse_answer('[{"n": 1, "label": "Relevant"}, {"n": 2, "label": "icf"}]', batches[0])
    assert got == {"a::0": {"label": "relevant", "why": ""}}
    got = judge.parse_answer("1|not|\n2|relevant|GCF loans and debt\nnoise", batches[0])
    assert got == {"a::0": {"label": "not", "why": ""},
                   "a::1": {"label": "relevant", "why": "GCF loans and debt"}}
    inp = tmp_path / "in.jsonl"
    inp.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    args = types.SimpleNamespace(input=str(inp), output_dir=str(tmp_path / "j"), limit=0)
    fake = lambda prompt, model, max_tokens: '[{"n": 1, "label": "not"}, {"n": 2, "label": "unsure"}]'
    assert judge.run(cfg, args, call=fake) == 0
    with open(tmp_path / "j" / "labels.jsonl", encoding="utf-8") as fh:
        assert len(fh.readlines()) == 6
    with open(tmp_path / "j" / "judge_runs.jsonl", encoding="utf-8") as fh:
        assert "not the ICF inclusion screen" in fh.read()
