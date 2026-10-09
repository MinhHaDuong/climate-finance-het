"""REL pool enrichment tables (ticket 2052): fill blanks, change no key."""

import csv
import hashlib
import random

import _rel_pool_enrich as en
import corpus_rel_pool as rp
import pytest
from _rel_pool_report import RelPoolError

pytestmark = pytest.mark.domain_corpus

REAL = "This paper studies the allocation of adaptation finance across vulnerable countries. " * 2
OTHER = "A second, different study of mitigation finance in emerging markets and its effects. " * 2
HIGH = "Highlights:\n• Adaptation finance is studied.\n• " + "Flows are measured over time. " * 10
STUB = "Climate finance."
LANES = {"lane-a": 0}


def _row(rid, doi="", oa="", **kw):
    r = {c: "" for c in rp.META_COLUMNS}
    r.update({"origin": "lane-a", "delivery": "lane-a/d", "record_id": rid, "doi": doi,
              "openalex_id": oa, "handle": "", "repec": "", "version_hint": "",
              "catalogue_source": "", "title": f"title {rid}", "year": "2020"})
    r.update(kw)
    return r


def _build(rows, tables):
    from _rel_pool_dedup import cluster
    roots = cluster(rows, {})
    enrich = en.Enrichment(tables) if tables else None
    return rp.build_pool(rows, roots, LANES, enrich=enrich)


def _table(label, fills, rows, doi="doi", oa=None):
    return {"label": label, "doi": doi, "oa": oa, "fills": fills, "rows": rows, "sha256": "x"}


def _by_doi(pool):
    return {p["all_dois"]: p for p in pool}


def test_blank_abstract_is_filled_with_its_source():
    rows = [_row("a", doi="10.1/a")]
    t = _table("istex", {"abstract": "abstract"}, [{"doi": "10.1/A", "abstract": REAL}])
    p = _build(rows, [t])[0]
    assert (p["abstract"], p["abstract_source"], p["abstract_flag"]) == (REAL, "istex", "ok")


def test_a_table_value_never_overwrites_a_usable_abstract_or_a_doc_type():
    rows = [_row("a", doi="10.1/a", abstract=REAL, doc_type="article")]
    t1 = _table("istex", {"abstract": "abstract"}, [{"doi": "10.1/a", "abstract": OTHER + OTHER}])
    t2 = _table("types", {"doc_type": "t"}, [{"doi": "10.1/a", "t": "book"}])
    p = _build(rows, [t1, t2])[0]
    assert (p["abstract"], p["abstract_source"]) == (REAL, "lane-a")
    assert (p["doc_type"], p["doc_type_source"]) == ("article", "")


def test_weaker_abstract_is_replaced_but_not_by_a_worse_class():
    rows = [_row("a", doi="10.1/a", abstract=STUB), _row("b", doi="10.1/b", abstract=REAL)]
    t = _table("istex", {"abstract": "abstract"},
               [{"doi": "10.1/a", "abstract": OTHER}, {"doi": "10.1/b", "abstract": HIGH}])
    got = _by_doi(_build(rows, [t]))
    assert (got["10.1/a"]["abstract"], got["10.1/a"]["abstract_source"]) == (OTHER, "istex")
    assert got["10.1/b"]["abstract_source"] == "lane-a"


def test_highlights_are_flagged_and_outranked_by_a_real_abstract_from_any_table():
    rows = [_row("a", doi="10.1/a"), _row("b", doi="10.1/b", abstract=STUB)]
    hi = _table("istex", {"abstract": "abstract"},
                [{"doi": "10.1/a", "abstract": HIGH}, {"doi": "10.1/b", "abstract": HIGH}])
    got = _by_doi(_build(rows, [hi]))
    assert got["10.1/a"]["abstract_flag"] == "highlights"
    assert got["10.1/b"]["abstract_flag"] == "highlights"   # still above a stub
    real = _table("s2", {"abstract": "abstract"}, [{"doi": "10.1/a", "abstract": REAL}])
    for tables in ([hi, real], [real, hi]):
        a = _by_doi(_build(rows, tables))["10.1/a"]
        assert (a["abstract"], a["abstract_source"], a["abstract_flag"]) == (REAL, "s2", "ok")


def test_highlights_in_a_lane_member_are_not_reclassified():
    rows = [_row("a", doi="10.1/a", abstract=HIGH)]
    assert _build(rows, [])[0]["abstract_flag"] == "ok"


def test_a_key_reaching_two_works_joins_none_and_unmatched_is_counted():
    rows = [_row("a", doi="10.1/a", oa="W1"), _row("b", doi="10.1/b", oa="W2")]
    t = _table("types", {"doc_type": "t"},
               [{"doi": "10.1/a", "oa": "W2", "t": "book"},      # a's DOI, b's id
                {"doi": "10.1/zzz", "oa": "", "t": "book"},      # nothing
                {"doi": "10.1/b", "oa": "W2", "t": "report"}], oa="oa")
    enrich = en.Enrichment([t])
    from _rel_pool_dedup import cluster
    pool = rp.build_pool(rows, cluster(rows, {}), LANES, enrich=enrich)
    got = _by_doi(pool)
    assert got["10.1/a"]["doc_type"] == "" and got["10.1/b"]["doc_type"] == "report"
    st = enrich.report()["types"]
    assert (st["ambiguous"], st["unmatched"], st["matched"]) == (1, 1, 1)


def test_key_and_provenance_columns_do_not_change():
    rows = [_row("a", doi="10.1/a"), _row("b", doi="10.1/b", abstract=REAL),
            _row("c", oa="W3", doc_type="article")]
    t1 = _table("istex", {"abstract": "abstract"}, [{"doi": "10.1/a", "abstract": REAL}])
    t2 = _table("types", {"doc_type": "t"}, [{"doi": "10.1/a", "oa": "", "t": "book"},
                                             {"doi": "", "oa": "W3", "t": "report"}], oa="oa")
    before, after = _build(rows, []), _build(rows, [t1, t2])
    keep = ["work_key", "sources", "n_sources", "member_record_ids", "all_dois",
            "all_openalex_ids", "title", "year", "in_catalogue"]
    assert [{k: p[k] for k in keep} for p in before] == [{k: p[k] for k in keep} for p in after]
    assert [p["doc_type"] for p in after] == ["book", "", "article"]


def test_table_order_does_not_change_the_pool_and_running_twice_is_identical():
    rows = [_row(str(i), doi=f"10.1/{i}") for i in range(30)]
    ab = [_table("istex", {"abstract": "abstract"},
                 [{"doi": f"10.1/{i}", "abstract": REAL if i % 2 else OTHER} for i in range(30)]),
          _table("s2", {"abstract": "abstract", "doc_type": "t"},
                 [{"doi": f"10.1/{i}", "abstract": OTHER + REAL, "t": f"t{i % 3}"} for i in range(0, 30, 2)]),
          _table("types", {"doc_type": "t"}, [{"doi": f"10.1/{i}", "t": f"u{i % 4}"} for i in range(10, 25)])]
    ref = _build(rows, ab)
    assert ref == _build(rows, ab)
    for seed in range(4):
        shuffled = ab[:]
        random.Random(seed).shuffle(shuffled)
        assert _build(rows, shuffled) == ref


def _config_entry(path, **kw):
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"source": "istex", "path": str(path), "sha256": sha, "doi_column": "doi",
            "fills": {"abstract": "abstract"}, "rule": "fill_blank", **kw}


def _csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["doi", "abstract"])
        w.writeheader()
        w.writerows(rows)
    return path


def test_table_with_another_sha256_is_refused(tmp_path):
    path = _csv(tmp_path / "t.csv", [{"doi": "10.1/a", "abstract": REAL}])
    (t,) = en.load_tables([_config_entry(path)], "/")
    assert len(t["rows"]) == 1
    with pytest.raises(RelPoolError, match="sha256"):
        en.load_tables([_config_entry(path, sha256="0" * 64)], "/")
    path.write_text(path.read_text() + "10.1/b,changed\n")
    with pytest.raises(RelPoolError, match="sha256"):
        en.load_tables([{**_config_entry(path), "sha256": t["sha256"]}], "/")


@pytest.mark.parametrize("bad", [{"rule": "replace"}, {"fills": {"title": "abstract"}},
                                 {"fills": {"abstract": "nope"}}, {"doi_column": None}])
def test_malformed_entry_is_refused(tmp_path, bad):
    path = _csv(tmp_path / "t.csv", [{"doi": "10.1/a", "abstract": REAL}])
    with pytest.raises(RelPoolError):
        en.load_tables([_config_entry(path, **bad)], "/")


def test_duplicate_source_label_is_refused(tmp_path):
    path = _csv(tmp_path / "t.csv", [{"doi": "10.1/a", "abstract": REAL}])
    with pytest.raises(RelPoolError, match="twice"):
        en.load_tables([_config_entry(path), _config_entry(path)], "/")


def test_no_table_leaves_the_pool_columns_as_before():
    rows = [_row("a", doi="10.1/a")]
    assert "doc_type_source" not in _build(rows, [])[0]


def test_highlights_without_a_colon_are_flagged_but_a_sentence_starting_with_the_word_is_not():
    bullets = "Highlights\u2022We assess the economic impacts of climate metrics.\u2022" + "Results hold broadly. " * 12
    prose = "Highlights of the previous papers in this series are reviewed, and new methodology is developed. " * 2
    rows = [_row("a", doi="10.1/a"), _row("b", doi="10.1/b")]
    t = _table("istex", {"abstract": "abstract"},
               [{"doi": "10.1/a", "abstract": bullets}, {"doi": "10.1/b", "abstract": prose}])
    got = _by_doi(_build(rows, [t]))
    assert got["10.1/a"]["abstract_flag"] == "highlights"
    assert got["10.1/b"]["abstract_flag"] == "ok"
