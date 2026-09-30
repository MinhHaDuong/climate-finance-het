"""REL Gavard-Schoch lane (ticket 1651): one decision per reference, honest absences."""

import csv
import json
import os

import corpus_rel_gavard_schoch as gs
import pytest

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(__file__))
LANE = os.path.join(ROOT, "data", "rel", "gavard_schoch")


def _read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _ref(ref_id, scope, doi="", title="", first_author="", year="2021", alt_title=""):
    return {"ref_id": ref_id, "scope": scope, "doi": doi, "title": title or ref_id,
            "alt_title": alt_title, "first_author": first_author, "year": year,
            "zotero_key": f"K{ref_id}", "zotero_collection": "Climate finance audit (2026)",
            "authors": first_author, "venue": "", "item_type": "journalArticle",
            "pdf_files": "", "version_link": "", "scope_reason": "r", "evidence": "e"}


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
    [decision] = gs.run([ref], {"unified": pool})
    assert decision["decision"] == "doublon"
    assert decision["pool_match_method"] == "title_author_year"


def test_title_rule_refuses_another_author_and_a_distant_year():
    pool = _pool(("", "Green aid, aid fragmentation and carbon emissions", "A. Other", 2023),
                 ("", "Green aid, aid fragmentation and carbon emissions", "M. Pinar", 2019))
    ref = _ref("R2", "pertinent", title="Green aid, aid fragmentation and carbon emissions",
               first_author="Pinar", year="2023")
    [decision] = gs.run([ref], {"unified": pool})
    assert decision["decision"] == "inclus"
    assert decision["pool_match_method"] == "absent"


def test_every_scope_maps_to_one_decision_and_non_resolu_is_never_treated():
    refs = [_ref(f"R{i}", s, doi=f"10.1000/x{i}") for i, s in enumerate(gs.SCOPES)]
    decisions = gs.run(refs, {"unified": _pool(("10.1000/x0", "t0", "", 2021))})
    assert [d["decision"] for d in decisions] == ["doublon", "hors thème", "hors période",
                                                  "non résolu"]
    unresolved = [d for d in decisions if d["decision"] == "non résolu"]
    assert all(d["treated"] == "no" and d["needs_human"] == "yes" for d in unresolved)
    with pytest.raises(ValueError):
        gs.decide("peut-être", False)


def test_a_wrong_author_same_title_record_cannot_shadow_the_right_one():
    # The other author's record scores higher (exact title); the right one
    # carries a small title variant and must still be found.
    title = "Green aid, aid fragmentation and carbon emissions"
    pool = _pool(("", title, "A. Other", 2023),
                 ("", title + " revisited", "M. Pinar", 2023))
    ref = _ref("R5", "pertinent", title=title, first_author="Pinar", year="2023")
    hit, _near = gs.match_one(ref, pool)
    assert hit and hit[1]["author"] == "m pinar"


def test_surname_is_matched_as_whole_words():
    assert gs.surname_matches("li", "nan li")
    assert gs.surname_matches("le quere", "corinne le quere")
    assert not gs.surname_matches("li", "zirong lin")
    assert not gs.surname_matches("wu", "wuhan wang")
    title = "Climate related development finance and carbon emissions reduction"
    ref = _ref("R6", "pertinent", title=title, first_author="Li", year="2022")
    assert gs.match_one(ref, _pool(("", title, "Zirong Lin", 2022)))[0] is None


def test_a_hit_among_sibling_candidates_is_recorded_but_is_not_doublon():
    ref = _ref("R7", "pertinent", doi="10.1000/cand")
    cand = [dict(r, pool="rel_sud_1530", id="W99")
            for r in _pool(("10.1000/cand", "R7", "", 2021))]
    [d] = gs.run([ref], {"unified": _pool()}, {"rel_sud_1530": cand})
    assert d["decision"] == "inclus"
    assert d["in_catalogue"] == "no"
    assert d["pool_match_method"] == "doi"
    assert "rel_sud_1530=W99" in d["pool_matches"]


def _collections(n_items):
    return [{"query_id": "zotero-A", "collection_key": "A",
             "collection_name": "Climate finance audit (2026)", "n_items": str(n_items)}]


NON_REFERENCE = [{"zotero_key": "X1", "query_id": "zotero-A", "reason": "front_matter",
                  "title": "status page", "note": "n"}]


def test_intake_delivers_every_reference_whatever_its_scope_or_pool_presence(tmp_path):
    refs = [_ref(f"R{i}", s, doi=f"10.1000/x{i}") for i, s in enumerate(gs.SCOPES)]
    refs[1]["doi"] = ""
    refs[1]["year"] = "2021"
    decisions = gs.run(refs, {"unified": _pool(("10.1000/x0", "t0", "", 2021))})
    delivery = tmp_path / "t1651-gavard-schoch" / "2026-09-30"
    producer = {"script": "s", "commit": "c", "machine": "m"}
    gs.write_intake(str(delivery), refs, decisions, "2026-09-30", producer,
                    _collections(5), NON_REFERENCE)
    records = _read(delivery / "records.csv")
    registry = _read(delivery / "registry.csv")
    excluded = _read(delivery / "excluded.csv")
    manifest = json.loads((delivery / "manifest.json").read_text(encoding="utf-8"))
    # Relevance and pool presence are information, never a filter.
    assert [r["record_id"] for r in records] == [f"1651-R{i}" for i in range(4)]
    assert [r["lane_status"] for r in records] == [
        "already_in_pool", "off_topic_in_lane_view", "out_of_window_in_lane_view",
        "unresolved"]
    assert records[0]["openalex_id"] == "W0"
    assert records[0]["url"] == "https://doi.org/10.1000/x0"
    assert records[1]["url"] == ""
    assert set(records[0]) == set(gs.RECORD_COLUMNS)
    assert [(e["record_id"], e["reason"]) for e in excluded] == [
        ("1651-zotero-X1", "front_matter")]
    # 4 delivered + 1 excluded = 5 items: counted from the data, complete.
    assert [(q["n_received"], q["completed"]) for q in registry] == [("5", "true")]
    assert manifest["coverage"] == "complete"
    assert manifest["counts"] == {"records": 4, "excluded": {"front_matter": 1}}
    assert [n["item"].split()[0] for n in manifest["needs_human"]] == ["1651-R3"]


def test_a_collection_with_unaccounted_items_is_incomplete(tmp_path):
    refs = [_ref("R0", "pertinent", doi="10.1000/x0")]
    decisions = gs.run(refs, {"unified": _pool()})
    delivery = tmp_path / "t1651-gavard-schoch" / "2026-09-30"
    _, manifest = gs.write_intake(str(delivery), refs, decisions, "2026-09-30",
                                  {"script": "s", "commit": "c", "machine": "m"},
                                  _collections(3), [])
    [q] = _read(delivery / "registry.csv")
    assert (q["n_received"], q["completed"]) == ("1", "false") and q["stop_reason"]
    assert manifest["coverage"] == "incomplete"
    assert manifest["incomplete"] == [{"unit": "zotero-A", "reason": q["stop_reason"]}]


def test_committed_decision_list_gives_each_reference_exactly_one_decision():
    refs = _read(os.path.join(LANE, "references.csv"))
    decisions = _read(os.path.join(LANE, "decisions.csv"))
    collections = _read(os.path.join(LANE, "zotero_collections.csv"))
    non_refs = _read(os.path.join(LANE, "zotero_non_references.csv"))
    assert [r["ref_id"] for r in refs] == [d["ref_id"] for d in decisions]
    assert len({r["ref_id"] for r in refs}) == len(refs)
    for d in decisions:
        assert d["decision"] in gs.DECISIONS
        assert (d["treated"] == "yes") == (d["decision"] in gs.TREATED)
        assert d["evidence"].strip()
        if d["decision"] == "doublon":
            assert d["in_catalogue"] == "yes"
        if d["decision"] == "inclus":
            assert d["in_catalogue"] == "no"
    names = {c["collection_name"] for c in collections}
    assert {r["zotero_collection"] for r in refs} <= names
    # Every collection item is either a reference or a listed non-reference.
    for c in collections:
        n = (sum(r["zotero_collection"] == c["collection_name"] for r in refs)
             + sum(x["query_id"] == c["query_id"] for x in non_refs))
        assert n == int(c["n_items"]), c["query_id"]
