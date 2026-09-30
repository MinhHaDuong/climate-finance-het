"""The REL pool merge: dedup cascade, per-source report, contract gate (ticket 1731)."""

import csv
import hashlib
import json

import corpus_rel_pool as rp
import pytest
import qa_rel_intake as ric

pytestmark = pytest.mark.domain_corpus

CAT_COLUMNS = ["source", "source_id", "doi", "title", "first_author", "year",
               "journal", "abstract", "affiliations", "cited_by_count"]


def _write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def _catalogue(tmp_path, rows):
    path = tmp_path / "unified_works.csv"
    _write_csv(path, CAT_COLUMNS, rows)
    md5 = hashlib.md5(path.read_bytes()).hexdigest()
    return path, {"catalogue": {"md5": md5, "rows": len(rows)}, "lane_order": []}


def _rec(rid, **kw):
    base = {"record_id": rid, "query_id": "q1", "platform": "openalex",
            "retrieved_at": "2026-09-29", "title": f"Title {rid}", "year": "2020"}
    base.update(kw)
    return base


def _delivery(intake, lane, delivery, records, excluded=(), supersedes=None, manifest=None):
    d = intake / lane / delivery
    d.mkdir(parents=True)
    _write_csv(d / "records.csv", ric.RECORD_COLUMNS, records)
    _write_csv(d / "registry.csv", ric.REGISTRY_REQUIRED, [{
        "query_id": "q1", "platform": "openalex", "query": "x", "run_at": "2026-09-29",
        "n_received": str(len(records)), "completed": "true"}])
    _write_csv(d / "excluded.csv", ric.EXCLUDED_COLUMNS, list(excluded))
    counts = {}
    for e in excluded:
        counts[e["reason"]] = counts.get(e["reason"], 0) + 1
    m = {"lane": lane, "ticket": lane[1:5], "delivery": delivery,
         "delivered_at": "2026-09-29T12:00:00Z",
         "producer": {"script": "s.py", "commit": "abc", "machine": "padme"},
         "counts": {"records": len(records), "excluded": counts},
         "coverage": "complete", "incomplete": [], "needs_human": [],
         "supersedes": supersedes, "notes": ""}
    m.update(manifest or {})
    (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return d


def _run(tmp_path, cat_rows, deliveries):
    cat, cfg = _catalogue(tmp_path, cat_rows)
    intake = tmp_path / "rel_intake"
    intake.mkdir()
    for args in deliveries:
        _delivery(intake, *args)
    out = tmp_path / "rel_pool"
    report = rp.run(cfg, str(cat), str(intake), str(out))
    with open(out / "pool.csv", encoding="utf-8") as fh:
        pool = list(csv.DictReader(fh))
    return report, pool


def _row(rows, key):
    return next(r for r in rows if r["work_key"] == key)


def test_cascade_doi_then_openalex_then_title_year():
    rows = [
        {"origin": "catalogue", "delivery": "catalogue", "doi": "10.1111/a", "openalex_id": "",
         "title": "Alpha", "year": "2020", "version_hint": ""},
        {"origin": "l", "delivery": "l/1", "doi": "10.1111/a", "openalex_id": "W1",
         "title": "Other words", "year": "2021", "version_hint": ""},
        {"origin": "l", "delivery": "l/1", "doi": "", "openalex_id": "W1",
         "title": "x", "year": "", "version_hint": ""},
        {"origin": "l", "delivery": "l/1", "doi": "", "openalex_id": "",
         "title": "ALPHA!", "year": "2020", "version_hint": ""},
        {"origin": "l", "delivery": "l/1", "doi": "", "openalex_id": "",
         "title": "Alpha", "year": "2019", "version_hint": ""},
    ]
    roots = rp.cluster(rows)
    assert roots[0] == roots[1] == roots[2] == roots[3]
    assert roots[4] != roots[0], "a title never joins across years"


def test_transitive_join_through_a_record_carrying_two_keys(tmp_path):
    cat = [{"source": "openalex", "source_id": "W100", "doi": "", "title": "One", "year": "2010"},
           {"source": "istex", "source_id": "ab", "doi": "10.9999/two", "title": "Two", "year": "2011"}]
    recs = [_rec("r1", doi="10.9999/TWO", openalex_id="W100", title="Bridge")]
    report, pool = _run(tmp_path, cat, [("t1530-sud", "2026-09-29", recs)])
    assert len(pool) == 1
    work = pool[0]
    assert work["work_key"] == "openalex:W100"
    assert work["title"] == "One", "catalogue wins metadata ties"
    assert work["sources"] == "catalogue;t1530-sud" and work["n_sources"] == "2"
    assert report["reconciliation"]["catalogue_rows_joined"] == 1


def test_working_paper_and_article_stay_two_works_with_version_hint(tmp_path):
    title = "Who pays for adaptation? Evidence from climate funds"
    cat = [{"source": "openalex", "source_id": "W1", "doi": "10.1016/j.art.2021.1",
            "title": title, "year": "2021"}]
    recs = [
        _rec("wp", doi="10.2139/ssrn.123", title=title, year="2021",
             version_hint="10.1016/j.art.2021.1", doc_type="working-paper"),
        _rec("wp-early", title=title, year="2019", version_hint="wp"),
    ]
    report, pool = _run(tmp_path, cat, [("t1651-gs", "2026-10-01", recs)])
    assert len(pool) == 3
    wp = _row(pool, "doi:10.2139/ssrn.123")
    assert wp["version_hint"] == "10.1016/j.art.2021.1"
    assert wp["in_catalogue"] == "false"
    early = next(p for p in pool if p["year"] == "2019")
    assert early["version_hint"] == "wp"
    assert _row(pool, "openalex:W1")["member_record_ids"] == "openalex:W1"
    assert report["deliveries"]["t1651-gs/2026-10-01"]["new_to_pool"] == 2


def test_per_source_report_reconciles(tmp_path):
    cat = [{"source": "openalex", "source_id": "W1", "doi": "10.1111/a", "title": "A", "year": "2001"},
           {"source": "openalex", "source_id": "W2", "doi": "", "title": "B", "year": "2002"},
           {"source": "grey", "source_id": "g", "doi": "", "title": "C report", "year": "2003"}]
    lane_a = [_rec("a1", doi="10.1111/A"),                      # catalogue by doi
              _rec("a2", openalex_id="W2"),                  # catalogue by openalex id
              _rec("a3", title="C  Report", year="2003"),    # catalogue by title + year
              _rec("a4", doi="10.1111/shared"),                 # other lane only
              _rec("a5", doi="10.1111/new"),                    # new
              _rec("a6", doi="10.1111/new", title="dup")]       # dup within delivery
    lane_b = [_rec("b1", doi="10.1111/shared", openalex_id="W9"),
              _rec("b2", title="Only here", year="1999")]
    report, pool = _run(tmp_path, cat, [("t1650-toc", "2026-10-01", lane_a),
                                        ("t1653-sud", "2026-10-02", lane_b)])
    a = report["deliveries"]["t1650-toc/2026-10-01"]
    assert a["records"] == 6 and a["dup_within_delivery"] == 1 and a["works"] == 5
    assert a["with_doi"] == 4 and a["with_openalex_id"] == 1 and a["title_year_only"] == 1
    assert a["in_catalogue"] == {"total": 3, "by_doi": 1, "by_openalex_id": 1, "by_url": 0,
                                 "by_title_year": 1, "via_other_lane": 0}
    assert a["in_other_lane_only"] == 1 and a["new_to_pool"] == 1
    b = report["deliveries"]["t1653-sud/2026-10-02"]
    assert (b["in_other_lane_only"], b["new_to_pool"]) == (1, 1)
    assert report["pool"]["works"] == len(pool) == 3 + 3
    assert report["pool"]["works_per_n_sources"] == {"1": 2, "2": 4}
    assert all(v == "ok" for v in report["reconciliation"]["checks"].values())


def test_delivery_violating_the_contract_aborts(tmp_path):
    cat, cfg = _catalogue(tmp_path, [{"source": "openalex", "source_id": "W1", "title": "A",
                                      "year": "2001"}])
    intake = tmp_path / "rel_intake"
    _delivery(intake, "t1650-toc", "2026-10-01", [_rec("r1")],
              excluded=[{"record_id": "x", "query_id": "q1", "reason": "off_topic"}])
    with pytest.raises(rp.RelPoolError, match="off_topic"):
        rp.run(cfg, str(cat), str(intake), str(tmp_path / "out"))
    assert not (tmp_path / "out").exists()


def test_superseded_delivery_is_skipped(tmp_path):
    cat = [{"source": "openalex", "source_id": "W1", "title": "A", "year": "2001"}]
    report, pool = _run(tmp_path, cat, [
        ("t1650-toc", "2026-10-01", [_rec("old", doi="10.1111/old")]),
        ("t1650-toc", "2026-10-02", [_rec("new", doi="10.1111/new")], (), "2026-10-01"),
    ])
    assert list(report["deliveries"]) == ["t1650-toc/2026-10-02"]
    assert report["superseded_deliveries"] == ["t1650-toc/2026-10-01"]
    assert not any(p["doi"] == "10.1111/old" for p in pool)


def test_catalogue_with_another_md5_is_refused(tmp_path):
    cat, cfg = _catalogue(tmp_path, [{"source": "openalex", "source_id": "W1", "title": "A",
                                      "year": "2001"}])
    cfg["catalogue"]["md5"] = "0" * 32
    with pytest.raises(rp.RelPoolError, match="md5"):
        rp.run(cfg, str(cat), str(tmp_path / "none"), str(tmp_path / "out"))


def test_idless_generic_title_never_fuses_distinct_dois(tmp_path):
    cat = [{"source": "openalex", "source_id": "W1", "doi": "10.1111/ed1", "title": "Editorial",
            "year": "2020"},
           {"source": "istex", "source_id": "x", "doi": "10.1111/ed2", "title": "Editorial",
            "year": "2020"}]
    recs = [_rec("e1", title="EDITORIAL.", year="2020"), _rec("e2", title="Editorial", year="2020")]
    report, pool = _run(tmp_path, cat, [("t1650-toc", "2026-10-01", recs)])
    assert len(pool) == 3, "two DOI works plus one id-less work, never one fused work"
    assert report["reconciliation"]["ambiguous_title_groups"] == 1
    d = report["deliveries"]["t1650-toc/2026-10-01"]
    assert (d["dup_within_delivery"], d["new_to_pool"]) == (1, 1)


def test_title_joins_a_doi_only_and_an_openalex_only_component(tmp_path):
    cat = [{"source": "istex", "source_id": "x", "doi": "10.1111/a", "title": "Green aid",
            "year": "2015"}]
    recs = [_rec("r1", openalex_id="W5", title="Green Aid", year="2015")]
    report, pool = _run(tmp_path, cat, [("t1530-sud", "2026-09-29", recs)])
    assert len(pool) == 1 and pool[0]["work_key"] == "openalex:W5"
    assert report["deliveries"]["t1530-sud/2026-09-29"]["in_catalogue"]["by_title_year"] == 1


def test_malformed_catalogue_doi_is_kept_and_counted(tmp_path):
    cat = [{"source": "openalex", "source_id": "W1", "title": "A", "year": "2001",
            "doi": "10.1108/s1569 chapter 2"},
           {"source": "grey", "source_id": "g", "title": "B", "year": "2002", "doi": "RePEc:abc"}]
    report, pool = _run(tmp_path, cat, [])
    assert len(pool) == 2
    assert report["reconciliation"]["catalogue_doi_malformed"] == 2


def test_unparsable_manifest_aborts(tmp_path):
    intake = tmp_path / "rel_intake"
    d = _delivery(intake, "t1650-toc", "2026-10-01", [_rec("r1")])
    (d / "manifest.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(rp.RelPoolError, match="not valid JSON"):
        rp.find_deliveries(str(intake))


def test_supersedes_naming_no_delivery_aborts(tmp_path):
    intake = tmp_path / "rel_intake"
    _delivery(intake, "t1650-toc", "2026-10-02", [_rec("r1")], (), "2026-10-0l")
    with pytest.raises(rp.RelPoolError, match="no existing delivery"):
        rp.find_deliveries(str(intake))


def test_supersedes_cycle_aborts(tmp_path):
    intake = tmp_path / "rel_intake"
    _delivery(intake, "t1650-toc", "2026-10-01", [_rec("r1")], (), "2026-10-02")
    _delivery(intake, "t1650-toc", "2026-10-02", [_rec("r2")], (), "t1650-toc/2026-10-01")
    with pytest.raises(rp.RelPoolError, match="cycle"):
        rp.find_deliveries(str(intake))


def test_duplicate_catalogue_record_id_is_refused(tmp_path):
    cat, cfg = _catalogue(tmp_path, [
        {"source": "istex", "source_id": "x", "title": "A", "year": "2001"},
        {"source": "istex", "source_id": "x", "title": "B", "year": "2002"}])
    with pytest.raises(rp.RelPoolError, match="not unique"):
        rp.run(cfg, str(cat), str(tmp_path / "none"), str(tmp_path / "out"))


def test_norm_year_and_openalex():
    assert rp.norm_year("2026.0") == "2026"
    assert rp.norm_year("") == rp.norm_year("n.d.") == ""
    assert rp.norm_openalex("https://openalex.org/W123") == "W123"
    assert rp.norm_openalex("abc") == ""


def test_no_dedup_key_rows_enter_the_pool_as_title_only_works(tmp_path):
    cat = [{"source": "openalex", "source_id": "W1", "doi": "", "title": "Carbon funds", "year": "2001"},
           {"source": "grey", "source_id": "g1", "doi": "", "title": "Twice seen", "year": "2002"},
           {"source": "grey", "source_id": "g2", "doi": "10.1111/b", "title": "Twice seen", "year": "2003"}]

    def excl(rid, title):
        return {"record_id": rid, "query_id": "q1", "reason": rp.NO_DEDUP_KEY, "title": title,
                "note": "no DOI, id or year"}
    report, pool = _run(tmp_path, cat, [("t1653-sud", "2026-10-02", [_rec("r1")], [
        excl("x1", "CARBON funds."),       # joins the one catalogue work with that title
        excl("x2", "Twice seen"),          # two works carry the title: ambiguous, separate
        excl("x3", "Nowhere else"),        # no match: its own work
        excl("x4", "Nowhere  else")])])    # same title as x3: one work with it
    d = report["deliveries"]["t1653-sud/2026-10-02"]
    assert d["records"] == 1 and d["title_only_from_excluded"] == 4
    assert d["title_only_joined"] == 1
    assert "t1653-sud" in _row(pool, "openalex:W1")["sources"]
    assert _row(pool, "title:twice seen|")["member_record_ids"] == \
        "t1653-sud/2026-10-02:excluded:x2"
    assert _row(pool, "title:nowhere else|")["member_record_ids"].count("excluded:") == 2
    assert report["reconciliation"]["ambiguous_title_only"] == 1
    assert all(v == "ok" for v in report["reconciliation"]["checks"].values())


def test_norm_url_handles_and_resolvers():
    assert rp.norm_url("HTTPS://Repo.UWI.edu/handle/2139/99/") == "hdl:2139/99"
    assert rp.norm_url("http://hdl.handle.net/2139/99") == "hdl:2139/99"
    assert rp.norm_url("https://CEEW.in/Publications/x/") == "https://ceew.in/Publications/x"
    assert rp.norm_url("ftp://x/y") == rp.norm_url("") == ""
    assert rp.ids_from_url("https://doi.org/10.1111/AB", "", "") == ("10.1111/ab", "", "")
    assert rp.ids_from_url("https://openalex.org/W12", "", "") == ("", "W12", "")


def test_url_joins_two_lanes_and_keys_a_url_only_work(tmp_path):
    cat = [{"source": "openalex", "source_id": "W1", "doi": "", "title": "A", "year": "2001"}]
    lane_a = [_rec("a1", year="", url="https://repo.uwi.edu/handle/2139/99", title="Handle work"),
              _rec("a2", year="", url="https://ceew.in/pub/x/", title="CEEW report")]
    lane_b = [_rec("b1", year="2019", url="http://hdl.handle.net/2139/99", title="Other spelling")]
    report, pool = _run(tmp_path, cat, [("t1653-sud", "2026-10-02", lane_a),
                                        ("t1650-toc", "2026-10-03", lane_b)])
    assert _row(pool, "url:hdl:2139/99")["sources"] == "t1650-toc;t1653-sud"
    assert _row(pool, "url:https://ceew.in/pub/x")["n_sources"] == "1"
    a = report["deliveries"]["t1653-sud/2026-10-02"]
    assert a["with_url"] == 2 and a["title_year_only"] == 0
    assert (a["in_other_lane_only"], a["new_to_pool"]) == (1, 1)
    assert len(pool) == 3
    assert all(v == "ok" for v in report["reconciliation"]["checks"].values())



def test_dspace_default_handle_prefix_keeps_the_host():
    # 123456789 is DSpace's unregistered default prefix: two repositories reuse it.
    a = rp.norm_url("https://a.org/handle/123456789/1")
    b = rp.norm_url("https://b.org/handle/123456789/1")
    assert a != b and a == "hdl:a.org/123456789/1"
    assert rp.norm_url("https://hdl.handle.net/123456789/1") == "hdl:123456789/1"
    assert rp.norm_url("https://repo.org/handle/2139/99") == "hdl:2139/99"



def test_handle_url_query_and_fragment_are_dropped():
    assert rp.norm_url("https://repo.org/handle/2139/99?show=full") == "hdl:2139/99"
    assert rp.norm_url("https://repo.org/handle/2139/99/#a") == "hdl:2139/99"
    assert rp.norm_url("http://hdl.handle.net/2139/99?locatt=view:master") == "hdl:2139/99"



def test_shared_landing_url_never_joins_distinct_dois():
    rows = [_crow(doi="10.1/a", url="https://j.org/issue/5", title="A"),
            _crow(doi="10.1/b", url="https://j.org/issue/5", title="B"),
            _crow(url="https://j.org/issue/5", title="C")]
    for order in (rows, rows[::-1]):
        roots = rp.cluster(order)
        by_doi = {r["doi"]: roots[i] for i, r in enumerate(order) if r["doi"]}
        assert by_doi["10.1/a"] != by_doi["10.1/b"]
    same = [_crow(doi="10.1/a", url="https://j.org/p/1"), _crow(url="https://j.org/p/1")]
    assert len(set(rp.cluster(same))) == 1, "a URL still joins rows it does not set apart"



def test_url_chain_never_joins_distinct_dois():
    # A and B each share a URL with C (OpenAlex id only): the chain must not fuse them.
    rows = [_crow(doi="10.1/a", url="https://x.org/1"),
            _crow(openalex_id="W7", url="https://x.org/1"),
            _crow(openalex_id="W7", url="https://x.org/2"),
            _crow(doi="10.1/b", url="https://x.org/2")]
    for order in (rows, rows[::-1]):
        roots = rp.cluster(order)
        by_doi = {r["doi"]: roots[i] for i, r in enumerate(order) if r["doi"]}
        assert by_doi["10.1/a"] != by_doi["10.1/b"]



def _crow(doi="", url="", title="x", year="", openalex_id="", origin="l"):
    return {"origin": origin, "delivery": f"{origin}/1", "doi": doi,
            "openalex_id": openalex_id, "url": rp.norm_url(url), "title": title,
            "year": year, "version_hint": ""}



def test_different_urls_do_not_veto_a_title_year_join():
    rows = [_crow(doi="10.1/a", url="https://publisher.com/a", title="Carbon funds", year="2001"),
            _crow(url="https://repo.org/handle/9/9", title="Carbon funds", year="2001")]
    assert len(set(rp.cluster(rows))) == 1
    assert rp._compatible(rows[0], rows[1])
