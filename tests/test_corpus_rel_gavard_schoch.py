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


def test_intake_delivers_every_reference_whatever_its_scope_or_pool_presence(tmp_path):
    refs = [_ref(f"R{i}", s, doi=f"10.1000/x{i}") for i, s in enumerate(gs.SCOPES)]
    decisions = gs.run(refs, {"unified": _pool(("10.1000/x0", "t0", "", 2021))})
    delivery = tmp_path / "t1651-gavard-schoch" / "2026-09-30"
    producer = {"script": "s", "commit": "c", "machine": "m"}
    gs.write_intake(str(delivery), refs, decisions, "2026-09-30", producer)
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
    assert set(records[0]) == set(gs.RECORD_COLUMNS)
    assert all(e["reason"] in {"duplicate_in_lane", "front_matter", "not_retrievable"}
               for e in excluded)
    assert {r["query_id"] for r in records} | {e["query_id"] for e in excluded} <= {
        q["query_id"] for q in registry}
    assert manifest["lane"] == "t1651-gavard-schoch"
    assert manifest["delivery"] == "2026-09-30"
    assert manifest["counts"]["records"] == len(records)
    assert [n["item"].split()[0] for n in manifest["needs_human"]] == ["1651-R3"]


def test_committed_decision_list_gives_each_reference_exactly_one_decision():
    refs = _read(os.path.join(LANE, "references.csv"))
    decisions = _read(os.path.join(LANE, "decisions.csv"))
    assert [r["ref_id"] for r in refs] == [d["ref_id"] for d in decisions]
    assert len({r["ref_id"] for r in refs}) == len(refs)
    for d in decisions:
        assert d["decision"] in gs.DECISIONS
        assert (d["treated"] == "yes") == (d["decision"] in gs.TREATED)
        assert d["evidence"].strip()
        if d["decision"] == "doublon":
            assert d["pool_match_method"] != "absent"
        if d["decision"] == "inclus":
            assert d["pool_match_method"] == "absent"
    assert {r["zotero_collection"] for r in refs} <= set(gs.ZOTERO_COLLECTIONS)
