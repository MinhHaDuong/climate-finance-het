"""REL Gavard-Schoch lane (ticket 1651): one decision per reference, honest absences."""

import csv
import os

import corpus_rel_gavard_schoch as gs
import pytest

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(__file__))
LANE = os.path.join(ROOT, "data", "rel", "gavard_schoch")


def _read(name):
    with open(os.path.join(LANE, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _ref(ref_id, scope, doi="", title="", first_author="", year="2021", alt_title=""):
    return {"ref_id": ref_id, "scope": scope, "doi": doi, "title": title,
            "alt_title": alt_title, "first_author": first_author, "year": year}


def _pool(*rows):
    return [{"pool": "unified", "id": f"openalex:W{i}", "doi": gs.norm_doi(d),
             "title": t, "tnorm": gs.fold(t), "author": gs.fold(a), "year": y}
            for i, (d, t, a, y) in enumerate(rows)]


def test_doi_miss_title_hit_is_present_in_the_pool():
    # The pool holds the working paper without the DOI the register carries.
    pool = _pool(("", "Climate finance and emission reductions: what do the "
                      "last twenty years tell us", "Claire Gavard", 2021))
    ref = _ref("R1", "pertinent", doi="10.2139/ssrn.3799872",
               title="Climate Finance and Emission Reductions: What Do the Last "
                     "Twenty Years Tell Us?", first_author="Gavard", year="2022")
    decisions, delivery = gs.run([ref], {"unified": pool}, "2026-09-30")
    assert decisions[0]["decision"] == "doublon"
    assert decisions[0]["pool_match_method"] == "title_author_year"
    assert delivery == []


def test_title_rule_refuses_another_author_and_a_distant_year():
    pool = _pool(("", "Green aid, aid fragmentation and carbon emissions", "A. Other", 2023),
                 ("", "Green aid, aid fragmentation and carbon emissions", "M. Pinar", 2019))
    ref = _ref("R2", "pertinent", title="Green aid, aid fragmentation and carbon emissions",
               first_author="Pinar", year="2023")
    decisions, delivery = gs.run([ref], {"unified": pool}, "2026-09-30")
    assert decisions[0]["decision"] == "inclus"
    assert [d["ref_id"] for d in delivery] == ["R2"]


def test_every_scope_maps_to_one_decision_and_non_resolu_is_never_treated():
    refs = [_ref(f"R{i}", s, doi=f"10.1/x{i}", title=f"t{i}") for i, s in enumerate(gs.SCOPES)]
    decisions, delivery = gs.run(refs, {"unified": _pool(("10.1/x0", "t0", "", 2021))},
                                 "2026-09-30")
    assert [d["decision"] for d in decisions] == ["doublon", "hors thème", "hors période",
                                                  "non résolu"]
    unresolved = [d for d in decisions if d["decision"] == "non résolu"]
    assert all(d["treated"] == "no" and d["needs_human"] == "yes" for d in unresolved)
    # Absences are delivered whatever their scope: no relevance set-aside.
    assert {d["ref_id"] for d in delivery} == {"R1", "R2", "R3"}
    with pytest.raises(ValueError):
        gs.decide("peut-être", False)


def test_committed_lane_output_gives_each_reference_exactly_one_decision():
    refs = _read("references.csv")
    decisions = _read("decisions.csv")
    delivery = _read("delivery_1655.csv")
    assert [r["ref_id"] for r in refs] == [d["ref_id"] for d in decisions]
    assert len({r["ref_id"] for r in refs}) == len(refs)
    for d in decisions:
        assert d["decision"] in gs.DECISIONS
        assert (d["treated"] == "yes") == (d["decision"] in gs.TREATED)
        assert d["evidence"].strip()
        assert (d["decision"] in ("doublon",)) <= (d["pool_match_method"] != "absent")
    absent = {d["ref_id"] for d in decisions if d["pool_match_method"] == "absent"}
    assert {d["ref_id"] for d in delivery} == absent
    assert all(d["lane"] == "1651" and d["zotero_key"] and d["retrieval_date"]
               and d["pool_revision"] for d in delivery)
