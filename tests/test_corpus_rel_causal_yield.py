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
             [{"search_id": "RC-grid-IM-en", "openalex_id": "W1", "doi": "10.1111/a", "title": T1,
               "year": 2020, "abstract": "x"},
              {"search_id": "RC-grid-IM-en", "openalex_id": "W2", "doi": "", "title": T2, "year": 2019},
              {"search_id": "RC-grid-IO-en", "openalex_id": "W1", "doi": "10.1111/a", "title": T1, "year": 2020},
              {"search_id": "RC-fiscal_substitution-IM-en", "openalex_id": "W2", "doi": "",
               "title": T2, "year": 2019}])
    _run_dir(tmp_path / "eds", "bibCNRS EDS (RePEc)",
             [("EDS-RePEc-grid-IM-en", "grid", "IM", 2)],
             [{"search_id": "EDS-RePEc-grid-IM-en", "eds_an": "edsrep.1", "doi": "",
               "title": T1.upper() + "!", "year": 2020},
              {"search_id": "EDS-RePEc-grid-IM-en", "eds_an": "edsrep.2", "doi": "10.9999/wp",
               "title": "A working paper on transmission lines and donors", "year": 2025}])
    with open(tmp_path / "refined.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, ["source", "source_id", "doi", "title", "year", "abstract"])
        w.writeheader()
        w.writerow({"source": "openalex", "source_id": "W1", "doi": "10.1111/a", "title": T1,
                    "year": "2020", "abstract": "climate finance for transmission lines"})
    with gzip.open(tmp_path / "sud.jsonl.gz", "wt", encoding="utf-8") as fh:
        fh.write(json.dumps({"openalex_id": "W2", "doi": "", "title": T2, "year": 2019}) + "\n")
    with open(tmp_path / "sent.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, ["sentinel", "family", "set", "source", "lang", "year", "doi",
                                "openalex_id", "title"])
        w.writeheader()
        w.writerow({"sentinel": "C1", "family": "grid", "set": "holdout", "source": "t",
                    "lang": "en", "year": "2020", "doi": "10.1111/A", "openalex_id": "W1", "title": T1})
        w.writerow({"sentinel": "C2", "family": "grid", "set": "tuning", "source": "t",
                    "lang": "en", "year": "2011", "doi": "10.5555/none", "openalex_id": "W9", "title": "Absent"})
    return tmp_path


def _args(p, labels=None):
    return types.SimpleNamespace(
        run_dir=str(p / "oa"), eds_dir=str(p / "eds"), refined=str(p / "refined.csv"),
        unified=str(p / "refined.csv"), sud_results=[str(p / "sud.jsonl.gz")], labels=labels,
        families=os.path.join(ROOT, "config", "rel_causal_families.yaml"),
        sentinels=str(p / "sent.csv"),
        search_config=os.path.join(ROOT, "config", "rel_causal_search.yaml"),
        archive_path="/archive/x", manifest_sha256="abc", output_dir=str(p / "out"),
        intake_dir=None, manifest_base=None, force_intake=False, doi_checks=None)


def _csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_work_keys_join_doi_openalex_and_title():
    recs = cy.assign_work_keys([
        {"doi": "10.1111/a", "openalex_id": "W1", "title": T1, "year": 2020},
        {"doi": "", "openalex_id": "W1", "title": T1, "year": 2020},
        {"doi": "", "openalex_id": "", "eds_an": "e", "title": T1.lower(), "year": 2020},
        {"doi": "", "openalex_id": "", "eds_an": "f", "title": "short", "year": 2020}])
    assert [r["work_key"] for r in recs] == ["doi:10.1111/a"] * 3 + ["an:f"]


def test_yields_reference_sets_uniqueness_and_delivery(lane):
    assert cy.run(_args(lane)) == 0
    out = lane / "out"
    by_lane = {r["lane"]: r for r in _csv(out / "yield_by_lane.csv")}
    assert by_lane["openalex"]["raw_hits"] == "4" and by_lane["openalex"]["unique_works"] == "2"
    assert by_lane["openalex"]["absent_refined"] == "1" and by_lane["openalex"]["absent_sud"] == "1"
    assert by_lane["openalex"]["absent_all_three"] == "0"
    assert by_lane["eds"]["unique_works"] == "2" and by_lane["eds"]["absent_all_three"] == "1"
    # lane-level uniqueness compares the lanes: the working paper only EDS found
    assert by_lane["eds"]["only_this_group"] == "1" and by_lane["openalex"]["only_this_group"] == "1"
    forms = {(r["lane"], r["group"]): r for r in _csv(out / "yield_by_formulation.csv")}
    assert forms[("openalex", "IM|en")]["only_this_group"] == "1"   # W2 only by IM
    assert forms[("openalex", "IO|en")]["only_this_group"] == "0"
    rows = _csv(out / "delivery.csv")
    assert len(rows) == 6 and set(rows[0]) == set(cy.DELIVERY_FIELDS)
    assert {r["lane"] for r in rows} == {"1652"}
    assert rows[0]["archive_path"] == "/archive/x" and rows[0]["manifest_sha256"] == "abc"
    eds_title_match = [r for r in rows if r["eds_an"] == "edsrep.1"][0]
    assert eds_title_match["work_key"] == "doi:10.1111/a" and eds_title_match["in_refined"] == "True"
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
        for pid, lab in (("grid::doi:10.1111/a", "relevant"), ("grid::oa:W2", "not"),
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
    w1 = [r for r in recs if r["record_id"] == "1652:doi:10.1111/a"][0]
    assert w1["platform"] == "openalex" and w1["all_query_ids"].count("|") == 2
    # an EDS DOI is a hint in the note, never the delivered identifier
    wp = [r for r in recs if "10.9999/wp" in r["lane_note"]]
    assert [(r["platform"], r["doi"]) for r in wp] == [("bibcnrs_eds_repec", "")]
    assert {r["completed"] for r in reg} == {"true", "false"}
    assert all(r["stop_reason"] for r in reg if r["completed"] == "false")
    manifest = json.loads((lane / "intake" / "manifest.json").read_text())
    assert manifest["counts"] == {"records": 3, "excluded": {"duplicate_in_lane": 3}}
    assert manifest["coverage"] == "incomplete"  # the EconLit rows were not run


def _set_registry(path, **changes):
    reg = _csv(path)
    for sid, fields in changes.items():
        for r in reg:
            if r["search_id"] == sid:
                r.update(fields)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, REG)
        w.writeheader()
        w.writerows(reg)


def test_a_rerun_adds_to_a_search_and_never_drops_what_an_earlier_run_retrieved(lane):
    _run_dir(lane / "oa2", "openalex", [("RC-grid-IO-en", "grid", "IO", 1)],
             [{"search_id": "RC-grid-IO-en", "openalex_id": "W7", "doi": "10.7777/new",
               "title": "A rerun record", "year": 2024}])
    args = _args(lane)
    args.run_dir = [str(lane / "oa"), str(lane / "oa2")]
    assert cy.run(args) == 0
    io = [r for r in _csv(lane / "out" / "delivery.csv") if r["search_id"] == "RC-grid-IO-en"]
    assert sorted(r["doi"] for r in io) == ["10.1111/a", "10.7777/new"]


def test_short_complete_rerun_does_not_hide_a_larger_capped_run(lane):
    """Replay of RC-construction_emissions-SY-en: run a capped at 800 of 1,944,
    rerun c 'complete' at 193 of 1,944. Nothing retrieved is lost and the row
    stays incomplete."""
    _set_registry(lane / "oa" / "registry.csv",
                  **{"RC-grid-IM-en": {"n_expected": "1944", "completed": "False",
                                       "stop_reason": "record cap"}})
    _run_dir(lane / "oa2", "openalex", [("RC-grid-IM-en", "grid", "IM", 1)],
             [{"search_id": "RC-grid-IM-en", "openalex_id": "W7", "doi": "10.7777/new",
               "title": "A rerun record", "year": 2024}])
    _set_registry(lane / "oa2" / "registry.csv",
                  **{"RC-grid-IM-en": {"n_expected": "1944", "completed": "True",
                                       "stop_reason": ""}})
    registry, _, records = cy.load_runs([str(lane / "oa"), str(lane / "oa2")])
    row = [r for r in registry if r["search_id"] == "RC-grid-IM-en"][0]
    assert row["completed"] == "False" and row["n_received"] == 3
    assert "short cursor" in row["stop_reason"] and "record cap" in row["stop_reason"]
    assert sorted(r["openalex_id"] for r in records if r["search_id"] == "RC-grid-IM-en") == \
        ["W1", "W2", "W7"]


def test_a_complete_row_needs_the_announced_count():
    rows = [{"search_id": "S", "n_received": "658", "n_expected": "659", "completed": "True",
             "stop_reason": "", "_run": "c"}]
    row = cy.merge_registry_rows(rows)
    assert row["completed"] == "False" and row["stop_reason"] == "c: short cursor (658 of 659)"
    rows[0]["n_received"] = "659"
    assert cy.merge_registry_rows(rows)["completed"] == "True"


def test_conservation_check_fails_when_a_retrieved_id_is_not_delivered(lane):
    dirs = [str(lane / "oa"), str(lane / "eds")]
    _, _, records = cy.load_runs(dirs)
    cy.assign_work_keys(records)
    delivered = {cy._raw_id(r) for r in records}
    assert cy.check_conservation(dirs, records, delivered) == len(delivered)
    with pytest.raises(SystemExit, match="conservation: 1"):
        cy.check_conservation(dirs, records, delivered - {"W2"})
    with pytest.raises(SystemExit, match="conservation: 1"):
        cy.check_conservation(dirs, [r for r in records if r["openalex_id"] != "W2"], delivered)


def test_an_eds_record_with_a_truncated_doi_joins_its_openalex_twin(lane):
    """EDS returned `10.1016/j.rser.2018.06.02` for `...06.025`: the work is one."""
    _run_dir(lane / "eds2", "bibCNRS EDS (ECONIS)", [("EDS-ECONIS-grid-IM-en", "grid", "IM", 1)],
             [{"search_id": "EDS-ECONIS-grid-IM-en", "eds_an": "zbw.1", "doi": "10.1111/",
               "title": T2, "year": 2019},
              {"search_id": "EDS-ECONIS-grid-IM-en", "eds_an": "zbw.2", "doi": "10.1111/a",
               "title": T1, "year": 2020}])
    _, _, records = cy.load_runs([str(lane / "oa"), str(lane / "eds2")])
    cy.assign_work_keys(records)
    keys = {r.get("eds_an") or r["openalex_id"]: r["work_key"] for r in records}
    assert keys["zbw.2"] == keys["W1"] == "doi:10.1111/a"
    # an exact EDS DOI still joins when the titles differ (working paper retitled)
    recs = cy.assign_work_keys([
        {"doi": "10.1111/abc", "openalex_id": "W1", "title": T1, "year": 2015},
        {"doi": "", "doi_eds": "10.1111/abc", "openalex_id": "", "eds_an": "e",
         "title": "Another title for the same working paper", "year": 2014}])
    assert recs[1]["work_key"] == "doi:10.1111/abc"
    assert keys["zbw.1"] == keys["W2"] == "oa:W2"


def test_an_openalex_record_without_doi_joins_its_eds_twin_by_title():
    recs = cy.assign_work_keys([
        {"doi": "", "openalex_id": "W1", "title": T1, "year": 2015},
        {"doi": "10.1111/abc", "openalex_id": "", "eds_an": "e1", "title": T1, "year": 2015},
        {"doi": "", "openalex_id": "W3", "title": T2, "year": 2016},
        {"doi": "", "openalex_id": "", "eds_an": "e2", "title": T2.upper(), "year": 2016}])
    assert [r["work_key"] for r in recs] == ["doi:10.1111/abc", "doi:10.1111/abc",
                                            "oa:W3", "oa:W3"]


def test_truncated_dois_are_dropped_and_untitled_works_are_not_retrievable():
    assert cy.valid_doi("https://doi.org/10.35219") == ""
    assert cy.valid_doi("10.1016/J.X.2020.1") == "10.1016/j.x.2020.1"
    reg = [{"search_id": "S1", "platform": "openalex", "run_at": "2026-09-30T10:00:00+00:00",
            "query_string": "q", "n_received": 2, "completed": "True"}]
    recs = cy.assign_work_keys([
        {"search_id": "S1", "platform": "openalex", "openalex_id": "W1", "doi": "", "title": "",
         "year": 2020, "question": "grid", "formulation": "IM", "in_refined": False,
         "in_unified": False, "in_sud": False},
        {"search_id": "S1", "platform": "openalex", "openalex_id": "W2", "doi": "", "title": "T",
         "year": 2021, "question": "grid", "formulation": "IM", "in_refined": False,
         "in_unified": False, "in_sud": False}])
    rows, _, excluded, delivered = cy.intake_rows(recs, reg, {})
    assert delivered == {"W1", "W2"}
    assert [r["openalex_id"] for r in rows] == ["W2"]
    assert [(e["record_id"], e["reason"]) for e in excluded] == [("1652:oa:W1", "not_retrievable")]


def test_intake_row_carries_the_authors_and_host_organization_of_the_slim_record():
    """Ticket 2041: the intake columns come from the record, not from a constant blank."""
    reg = [{"search_id": "S1", "platform": "openalex", "run_at": "2026-09-30T10:00:00+00:00",
            "query_string": "q", "n_received": 1, "completed": "True"}]
    recs = cy.assign_work_keys([
        {"search_id": "S1", "platform": "openalex", "openalex_id": "W2", "doi": "", "title": "T",
         "year": 2021, "question": "grid", "formulation": "IM", "in_refined": False,
         "in_unified": False, "in_sud": False, "first_author": "Ledec, G.",
         "all_authors": ["Ledec, G.", "Rapp, K."], "host_org_name": "Routledge",
         "issn": ["1111-2222"], "source_type": "ebook platform"}])
    (row,), _, _, _ = cy.intake_rows(recs, reg, {})
    assert (row["first_author"], row["all_authors"]) == ("Ledec, G.", "Ledec, G.; Rapp, K.")
    assert (row["issn"], row["host_org_name"], row["source_type"]) == (
        "1111-2222", "Routledge", "ebook platform")


# --- ticket 1755: the corrections of the replacement delivery

SURVEY = "Survey of Recent Developments"


def test_a_title_join_never_fuses_two_records_with_different_full_dois():
    """Replay of a pair the round-2 panel found fused (Bulletin of Indonesian
    Economic Studies, 2007): an OpenAlex record and an EDS record with the same
    title and year but two different, complete DOIs are two works; the EDS DOI
    becomes the record's identifier so the pool keeps them apart too."""
    recs = cy.assign_work_keys([
        {"doi": "10.1080/00074910701286370", "openalex_id": "W1", "title": SURVEY, "year": 2007},
        {"doi": "", "doi_eds": "10.1080/00074910701408040", "openalex_id": "", "eds_an": "e1",
         "title": SURVEY, "year": 2007},
        # a truncated EDS DOI is a prefix of its twin's and still joins it
        {"doi": "", "doi_eds": "10.1080/0007491070128", "openalex_id": "", "eds_an": "e2",
         "title": SURVEY.upper(), "year": 2007}], resolves=lambda d: True)
    assert [r["work_key"] for r in recs] == ["doi:10.1080/00074910701286370",
                                            "edsdoi:10.1080/00074910701408040",
                                            "doi:10.1080/00074910701286370"]
    assert recs[1]["doi"] == "10.1080/00074910701408040" and recs[2]["doi"] == ""


def test_two_eds_records_with_different_full_dois_stay_apart():
    """IMF pair: 10.5089/9781498318426.002 and 10.5089/9781484390429.002, both
    from EDS, same title and year, no OpenAlex twin."""
    title = "Republic of Mozambique: Selected Issues Paper"
    recs = cy.assign_work_keys([
        {"doi": "", "doi_eds": "10.5089/9781498318426.002", "openalex_id": "", "eds_an": "a",
         "title": title, "year": 2016},
        {"doi": "", "doi_eds": "10.5089/9781484390429.002", "openalex_id": "", "eds_an": "b",
         "title": title, "year": 2016},
        # a record of the same title that no DOI places keeps its own id, and
        # records with no id at all join only one another
        {"doi": "", "openalex_id": "W5", "title": title, "year": 2016},
        {"doi": "", "openalex_id": "", "eds_an": "c", "title": title, "year": 2016},
        {"doi": "", "openalex_id": "", "eds_an": "d", "title": title.upper(), "year": 2016}],
        resolves=lambda d: True)
    ty = "ty:" + cy.title_key(title, 2016)
    assert [r["work_key"] for r in recs] == ["edsdoi:10.5089/9781498318426.002",
                                            "edsdoi:10.5089/9781484390429.002", "oa:W5", ty, ty]
    assert [r["doi"] for r in recs] == ["10.5089/9781498318426.002",
                                        "10.5089/9781484390429.002", "", "", ""]


def test_a_truncated_eds_doi_is_never_promoted():
    """Round-1 review of PR #1637: `10.1111/j.0092-5853.2004.` was promoted.
    It is a strict prefix of a DOI elsewhere in the lane (another title), so
    it is truncated even if doi.org were to answer; and an EDS DOI that
    doi.org does not know (`..._v1`) is no identifier either. Both records
    join their title twin, as before the split."""
    ajps = "Policy Responsiveness and Electoral Incentives"
    osf = "Climate Finance Flows to Small Island States"
    recs = cy.assign_work_keys([
        {"doi": "10.1111/j.0092-5853.2004.00065.x", "openalex_id": "W1",
         "title": "A different article of the same issue", "year": 2004},
        {"doi": "10.2307/1519875", "openalex_id": "W2", "title": ajps, "year": 2004},
        {"doi": "", "doi_eds": "10.1111/j.0092-5853.2004.", "openalex_id": "", "eds_an": "e1",
         "title": ajps, "year": 2004},
        {"doi": "10.31219/osf.io/75vez", "openalex_id": "W3", "title": osf, "year": 2021},
        {"doi": "", "doi_eds": "10.31219/osf.io/75vez_v1", "openalex_id": "", "eds_an": "e2",
         "title": osf, "year": 2021}],
        resolves=lambda d: d != "10.31219/osf.io/75vez_v1")
    assert [r["work_key"] for r in recs[2:]] == ["doi:10.2307/1519875", "doi:10.31219/osf.io/75vez",
                                                "doi:10.31219/osf.io/75vez"]
    assert [r["doi"] for r in recs if r.get("eds_an")] == ["", ""]
    # without a resolver nothing is promoted and nothing splits
    recs = cy.assign_work_keys([
        {"doi": "10.1080/00074910701286370", "openalex_id": "W1", "title": SURVEY, "year": 2007},
        {"doi": "", "doi_eds": "10.1080/00074910701408040", "openalex_id": "", "eds_an": "e1",
         "title": SURVEY, "year": 2007}])
    assert recs[1]["work_key"] == "doi:10.1080/00074910701286370" and recs[1]["doi"] == ""


def test_curly_and_straight_apostrophes_make_one_title():
    """Round-1 review of PR #1637: "China\u2019s" and "China's" were two lane
    title keys, one pool title; the lane now uses the pool's normaliser."""
    straight = "The Determinants of China's International Portfolio Equity Allocations"
    curly = straight.replace("'", "\u2019")
    assert cy.title_key(straight, 2020) == cy.title_key(curly, 2020)
    recs = cy.assign_work_keys([
        {"doi": "10.1057/s41308-020-00113-x", "openalex_id": "W1", "title": straight, "year": 2020},
        {"doi": "", "doi_eds": "10.1057/s41308-020-00113", "openalex_id": "", "eds_an": "e",
         "title": curly, "year": 2020},
        {"doi": "", "doi_eds": "10.1016/j.other.2020.1", "openalex_id": "", "eds_an": "f",
         "title": straight, "year": 2020}], resolves=lambda d: True)
    assert recs[1]["work_key"] == "doi:10.1057/s41308-020-00113-x" and recs[1]["doi"] == ""


def test_labels_follow_a_record_whose_title_key_changed_but_never_a_split_twin():
    """The judge labelled (work key, family) pairs under the earlier title key;
    a record whose key changed only with the normaliser keeps its label, a
    record split from a DOI twin does not inherit the twin's."""
    title = "Donors' Climate-Finance Pledges and Their Delivery"
    old_ty = "ty:" + cy._legacy_title_key(title, 2019)
    recs = cy.assign_work_keys([
        {"doi": "", "openalex_id": "", "eds_an": "a", "title": title, "year": 2019,
         "question": "grid"},
        {"doi": "10.1/x", "openalex_id": "W1", "title": SURVEY, "year": 2007, "question": "grid"},
        {"doi": "", "doi_eds": "10.1/y", "openalex_id": "", "eds_an": "b", "title": SURVEY,
         "year": 2007, "question": "grid"}], resolves=lambda d: True)
    assert recs[0]["work_key"] != old_ty and recs[2]["work_key"] == "edsdoi:10.1/y"
    raw = {cy.pair_id(old_ty, "grid"): "relevant", cy.pair_id("doi:10.1/x", "grid"): "not",
           cy.pair_id("ty:" + cy._legacy_title_key(SURVEY, 2007), "grid"): "relevant"}
    labels = {(recs[1]["work_key"], "grid"): "not"}
    assert cy.carry_labels(recs, labels, raw) == 1
    assert labels[(recs[0]["work_key"], "grid")] == "relevant"
    assert ("edsdoi:10.1/y", "grid") not in labels


def test_doi_checks_look_each_doi_up_once_and_keep_the_answer(tmp_path):
    calls = []
    checks = cy.DoiChecks(str(tmp_path / "doi_checks.csv"),
                          lookup=lambda d: calls.append(d) or d.endswith("x"))
    assert checks("10.1/x") is True and checks("10.1/y") is False and checks("10.1/x") is True
    assert calls == ["10.1/x", "10.1/y"]
    again = cy.DoiChecks(str(tmp_path / "doi_checks.csv"), lookup=lambda d: 1 / 0)
    assert again("10.1/y") is False
    assert [r["resolves"] for r in _csv(tmp_path / "doi_checks.csv")] == ["true", "false"]


def _run_with_repeats(path, sid, rows, distinct, expected, completed="True", stop=""):
    """A run directory whose cursor served ``rows`` rows for ``distinct`` ids."""
    _run_dir(path, "openalex", [(sid, "construction_emissions", "SY", expected)],
             [{"search_id": sid, "openalex_id": f"W{i % distinct}", "doi": "",
               "title": f"Construction emissions record number {i % distinct}", "year": 2020}
              for i in range(rows)])
    _set_registry(path / "registry.csv", **{sid: {"n_received": str(rows), "completed": completed,
                                                  "stop_reason": stop}})


def test_completeness_counts_distinct_ids_and_names_the_exhausted_cursor(tmp_path):
    """Replay of run d, RC-construction_emissions-SY-en: the cursor served 1,946
    rows, 1,940 distinct ids, of 1,944 announced. The cursor was exhausted: the
    row is complete (lead's arbitration at the merge of #1609), but the state
    says so explicitly and the counts are distinct ids."""
    sid = "RC-construction_emissions-SY-en"
    _run_with_repeats(tmp_path / "d", sid, 1946, 1940, 1944)
    registry, _, _ = cy.load_runs([str(tmp_path / "d")])
    row = [r for r in registry if r["search_id"] == sid][0]
    assert row["n_received"] == 1940
    assert row["completed"] == "True" and row["cursor_state"] == "cursor_exhausted"
    assert row["cursor_note"] == "d: cursor exhausted (1946 rows, 1940 distinct ids of 1944 announced)"
    # a cursor that ended with fewer rows than announced is a short cursor, not complete
    _run_with_repeats(tmp_path / "a", sid, 658, 658, 659)
    row = cy.load_runs([str(tmp_path / "a")])[0][0]
    assert row["completed"] == "False" and row["cursor_state"] == "short_cursor"
    assert row["stop_reason"] == "a: short cursor (658 of 659)"
    # a capped run is neither
    _run_with_repeats(tmp_path / "c", sid, 800, 800, 1944, completed="False", stop="record cap")
    row = cy.load_runs([str(tmp_path / "c")])[0][0]
    assert row["completed"] == "False" and row["cursor_state"] == "record_cap"
    # all distinct ids announced: plainly complete
    _run_with_repeats(tmp_path / "b", sid, 441, 440, 440)
    row = cy.load_runs([str(tmp_path / "b")])[0][0]
    assert row["completed"] == "True" and row["cursor_state"] == "complete" and row["cursor_note"] == ""


def test_runs_that_jointly_received_every_announced_id_are_complete(tmp_path):
    """Replay of RC-construction_emissions-IM-en: run d exhausted its cursor at
    1,453 distinct ids of 1,454, and run a had retrieved the missing one."""
    sid = "RC-construction_emissions-IM-en"
    _run_with_repeats(tmp_path / "a", sid, 1, 1, 4, completed="False", stop="record cap")
    _run_dir(tmp_path / "d", "openalex", [(sid, "construction_emissions", "IM", 4)],
             [{"search_id": sid, "openalex_id": f"W{i}", "doi": "",
               "title": f"Construction emissions record number {i}", "year": 2020}
              for i in (1, 2, 3, 3, 2)])
    _set_registry(tmp_path / "d" / "registry.csv", **{sid: {"n_received": "5"}})
    row = cy.load_runs([str(tmp_path / "a")])[0][0]
    assert row["completed"] == "False"
    row = cy.load_runs([str(tmp_path / "d")])[0][0]
    assert row["cursor_state"] == "cursor_exhausted"
    row = cy.load_runs([str(tmp_path / "a"), str(tmp_path / "d")])[0][0]
    assert row["n_received"] == 4 and row["completed"] == "True"
    assert row["cursor_state"] == "complete"


def test_every_eds_doi_survives_in_the_delivery(lane):
    """An EDS retrieval joined to an OpenAlex record without DOI is a
    duplicate_in_lane; its DOI is carried by the kept record and the exclusion
    note, not left in the archive."""
    _run_dir(lane / "eds2", "bibCNRS EDS (ECONIS)", [("EDS-ECONIS-grid-IM-en", "grid", "IM", 1)],
             [{"search_id": "EDS-ECONIS-grid-IM-en", "eds_an": "zbw.9", "doi": "10.4444/fungib",
               "title": T2, "year": 2019}])
    registry, registry_all, records = cy.load_runs([str(lane / "oa"), str(lane / "eds2")])
    cy.assign_work_keys(records)
    for r in records:
        r.update(in_refined=False, in_unified=False, in_sud=False)
    rows, _, excluded, _ = cy.intake_rows(records, registry_all, {})
    w2 = [r for r in rows if r["openalex_id"] == "W2"][0]
    assert w2["doi"] == "" and w2["doi_eds_hint"] == "10.4444/fungib"
    assert "10.4444/fungib" in w2["lane_note"]
    zbw = [e for e in excluded if e["note"].startswith("zbw.9")][0]
    assert "10.4444/fungib" in zbw["note"]


def test_write_intake_refuses_an_existing_delivery_without_force(lane, tmp_path):
    registry, registry_all, records = cy.load_runs([str(lane / "oa")])
    cy.assign_work_keys(records)
    for r in records:
        r.update(in_refined=False, in_unified=False, in_sud=False)
    base = {"lane": "t1652-causal-econlit", "ticket": "1652", "delivery": "2026-09-30b"}
    out = tmp_path / "delivery"
    cy.write_intake(str(out), records, registry_all, {}, base)
    (out / "records.csv").write_text("sentinel")
    with pytest.raises(SystemExit, match="--force-intake"):
        cy.write_intake(str(out), records, registry_all, {}, base)
    assert (out / "records.csv").read_text() == "sentinel"
    # any delivery file, not only records.csv, marks the directory as taken
    (out / "records.csv").unlink()
    with pytest.raises(SystemExit, match="--force-intake"):
        cy.write_intake(str(out), records, registry_all, {}, base)
    cy.write_intake(str(out), records, registry_all, {}, base, force=True)
    assert (out / "records.csv").read_text().startswith("record_id,")


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


def test_intake_carries_the_checked_repec_handle_and_the_eds_fields_and_passes_the_record_check(lane):
    import qa_rel_intake as qa
    with gzip.open(lane / "eds" / "results.jsonl.gz", "wt", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "search_id": "EDS-RePEc-grid-IM-en", "eds_an": "edsrep.p.nbr.nberwo.35497", "doi": "",
            "title": "A paper only the mirror knows about", "year": 2020, "authors": ["Doe, Jane", "Roe, Rik"],
            "issn": "1234-5678", "urls": ["https://ideas.repec.org/p/nbr/nberwo/35497.html"]}) + "\n")
        fh.write(json.dumps({
            "search_id": "EDS-RePEc-grid-IM-en", "eds_an": "edsrep.a.zzz.nope.v1y2020i1p1.2",
            "doi": "", "title": "An article the mirror does not hold", "year": 2021}) + "\n")
        fh.write(json.dumps({
            "search_id": "EDS-RePEc-grid-IM-en", "eds_an": "EDSZBW1968531777", "doi": "",
            "title": "A catalogue record without a DOI", "year": 2022}) + "\n")
    table = lane / "handles.csv"
    table.write_text("eds_an,status,handle\nedsrep.p.nbr.nberwo.35497,matched,RePEc:nbr:nberwo:35497\n"
                     "edsrep.a.zzz.nope.v1y2020i1p1.2,no_series,\n")
    base = lane / "base.json"
    base.write_text(json.dumps({"lane": "t1652-causal-econlit", "ticket": "1652",
                                "delivery": "2026-09-30", "needs_human": [], "supersedes": None}))
    args = _args(lane)
    args.intake_dir, args.manifest_base, args.eds_handles = str(lane / "intake"), str(base), str(table)
    assert cy.run(args) == 0
    recs = {r["platform_record_id"]: r for r in _csv(lane / "intake" / "records.csv")}
    ok = recs["edsrep.p.nbr.nberwo.35497"]
    assert ok["repec_handle"] == "RePEc:nbr:nberwo:35497" and ok["first_author"] == "Doe, Jane"
    assert ok["all_authors"] == "Doe, Jane; Roe, Rik" and ok["issn"] == "1234-5678"
    assert ok["url"].endswith("/p/nbr/nberwo/35497.html")
    lost = recs["edsrep.a.zzz.nope.v1y2020i1p1.2"]
    assert lost["repec_handle"] == "" and "no_series in the mirror" in lost["lane_note"]
    assert "RePEc:zzz:nope:v1y2020i1p1.2" in lost["lane_note"]
    assert "K10plus" in recs["EDSZBW1968531777"]["lane_note"]
    # records.csv alone: the fixture's registry and manifest are not contract-shaped
    header, rows = qa._read_csv(str(lane / "intake" / "records.csv"), [])
    assert qa.check_records(header, rows, None) == []
