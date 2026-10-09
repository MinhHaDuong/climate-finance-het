"""REL pool abstract selector (ticket 2045): quality, not rank."""

import _rel_pool_dedup as rd
import corpus_rel_pool as rp
import pytest
from _rel_pool_abstract import OLD_CUT, STUB_MAX, select_abstract

pytestmark = pytest.mark.domain_corpus

SENT = "Climate finance flows to developing countries are measured with some difficulty. "
FULL = (SENT * 30).strip()            # about 2,400 characters
CUT = FULL[:OLD_CUT]                  # what the old slim() left behind
REAL = "This paper studies the allocation of adaptation finance across vulnerable countries. " * 2
STUB = "Climate finance in Ecuador."   # under STUB_MAX, not boilerplate


def _m(origin, abstract, **kw):
    return {"origin": origin, "abstract": abstract, **kw}


def test_full_lane_abstract_beats_truncated_catalogue_copy():
    assert len(CUT) == OLD_CUT and len(FULL) > OLD_CUT
    text, source, flag = select_abstract([_m("catalogue", CUT), _m("lane-b", FULL)])
    assert (text, source, flag) == (FULL, "lane-b", "ok")


def test_truncated_copy_loses_when_the_longer_member_is_a_different_whitespace():
    longer = FULL.replace(". ", ".\n")
    assert select_abstract([_m("catalogue", CUT), _m("lane-b", longer)])[1] == "lane-b"


def test_ellipsis_cut_loses_to_its_full_text():
    cut = FULL[:200] + "..."
    assert select_abstract([_m("catalogue", cut), _m("lane-b", FULL)])[:2] == (FULL, "lane-b")


def test_truncated_copy_alone_is_supplied_and_flagged():
    assert select_abstract([_m("catalogue", CUT)]) == (CUT, "catalogue", "truncated_suspect")
    # the longer member is a different text: a different abstract, not a cut one
    other = "Another study entirely. " * 80
    assert select_abstract([_m("catalogue", CUT), _m("lane-b", other)])[1] == "lane-b"


def test_boilerplate_loses_to_a_real_abstract_whatever_the_rank():
    assert select_abstract([_m("catalogue", "International audience"), _m("lane-b", REAL)]) \
        == (REAL, "lane-b", "ok")
    # the title copied as abstract is boilerplate too, even when long
    title = "A very long title about the allocation of adaptation finance across vulnerable countries"
    assert select_abstract([_m("catalogue", title), _m("lane-b", REAL)], title=title)[1] == "lane-b"


def test_real_abstract_is_not_displaced_by_a_longer_boilerplate():
    boiler = "No access " + "x" * 400
    assert select_abstract([_m("catalogue", REAL), _m("lane-b", boiler)])[:2] == (REAL, "catalogue")


def test_stub_loses_to_a_full_abstract_but_stays_when_alone():
    assert len(STUB) < STUB_MAX
    assert select_abstract([_m("catalogue", STUB), _m("lane-b", REAL)])[:2] == (REAL, "lane-b")
    assert select_abstract([_m("catalogue", STUB)]) == (STUB, "catalogue", "stub")
    assert select_abstract([_m("catalogue", ","), _m("lane-b", STUB)])[2:] == ("stub",)
    assert select_abstract([_m("catalogue", "International audience")]) \
        == ("International audience", "catalogue", "stub")


def test_longest_then_rank_among_usable():
    a, b = REAL, REAL + "And it concludes."
    assert select_abstract([_m("l1", a), _m("l2", b)])[:2] == (b, "l2")
    twin = REAL.replace("adaptation", "mitigation")   # same length, other text
    assert len(twin) == len(REAL)
    assert select_abstract([_m("l1", REAL), _m("l2", twin)])[:2] == (REAL, "l1")


def test_no_abstract_agrees_with_blank_after_trimming():
    assert select_abstract([_m("catalogue", ""), _m("lane-b", "")]) == ("", "", "no_abstract")
    assert select_abstract([]) == ("", "", "no_abstract")
    # whitespace only: kept byte for byte as before, flagged like a blank
    assert select_abstract([_m("catalogue", "  \n")]) == ("  \n", "catalogue", "no_abstract")
    # a blank member never hides a real one behind it
    assert select_abstract([_m("catalogue", "  "), _m("lane-b", REAL)])[:2] == (REAL, "lane-b")


def _row(origin, record, **kw):
    cols = {c: "" for c in rp.META_COLUMNS}
    cols.update({"origin": origin, "delivery": f"{origin}/1", "record_id": f"{origin}/1:{record}",
                 "doi": "10.1/x", "openalex_id": "", "handle": "", "title": "Same work",
                 "year": "2020", "version_hint": "", "catalogue_source": ""})
    cols.update(kw)
    return cols


def test_pool_other_columns_stay_first_non_empty():
    rows = [_row("catalogue", "c", abstract=CUT, journal="", language="fr", first_author=""),
            _row("lane-b", "b", abstract=FULL, journal="J B", language="en", first_author="Zed"),
            _row("lane-c", "c2", abstract=REAL, journal="J C", language="de", first_author="Yu")]
    (p,) = rp.build_pool(rows, rd.cluster(rows), {"lane-b": 0, "lane-c": 1})
    assert (p["abstract"], p["abstract_source"], p["abstract_flag"]) == (FULL, "lane-b", "ok")
    # the abstract moved to lane-b; no other column followed it
    assert (p["journal"], p["language"], p["first_author"]) == ("J B", "fr", "Zed")
    assert p["sources"] == "catalogue;lane-b;lane-c"
    assert p["abstract_source"] in p["sources"].split(";")


def test_pool_columns_are_appended_not_inserted():
    assert rp.POOL_COLUMNS[-2:] == ["abstract_source", "abstract_flag"]
    assert rp.POOL_COLUMNS.index("abstract") == rp.META_COLUMNS.index("abstract") + 1
