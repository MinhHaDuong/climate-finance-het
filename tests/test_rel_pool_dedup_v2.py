"""Pool dedup version 2 machinery behind ``dedup_version`` (ticket 2047).

Version 1 (the default) must build the pool byte for byte as before; version 2
joins on the new title key and the RePEc handle and writes only a report and
an append-only migration table outside the pool.
"""

import csv
import hashlib
import json
import random
from collections import defaultdict

import _rel_pool_dedup as rd
import _rel_pool_migration as rm
import corpus_rel_pool as rp
import pytest
import qa_rel_intake as ric

pytestmark = pytest.mark.domain_corpus

CAT_COLUMNS = ["source", "source_id", "doi", "title", "first_author", "year",
               "journal", "abstract", "affiliations", "cited_by_count", "language"]

# md5 of pool.csv built from this fixture by corpus_rel_pool at origin/main
# 2c29dcce (before ticket 2047), SOURCE_DATE_EPOCH set.
POOL_MD5_BEFORE_2047 = "e452dbe018351ab3f6716bad9280c6d7"


def _write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def _rec(rid, **kw):
    base = {"record_id": rid, "query_id": "q1", "platform": "x",
            "retrieved_at": "2026-09-29", "title": f"Title {rid}", "year": "2020"}
    base.update(kw)
    return base


def _delivery(intake, lane, delivery, records, excluded=(), extra_columns=()):
    d = intake / lane / delivery
    d.mkdir(parents=True)
    _write_csv(d / "records.csv", ric.RECORD_COLUMNS + list(extra_columns), records)
    _write_csv(d / "registry.csv", ric.REGISTRY_REQUIRED, [{
        "query_id": "q1", "platform": "x", "query": "x", "run_at": "2026-09-29",
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
         "supersedes": None, "notes": ""}
    (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")


def _fixture(tmp_path):
    """Catalogue and three lanes exercising every cascade step and both versions."""
    cat_rows = [
        {"source": "openalex", "source_id": "W1", "doi": "10.1111/a",
         "title": "Emerging markets&rsquo; carbon pricing", "year": "2015", "language": "en"},
        {"source": "openalex", "source_id": "W2", "title": "Post-Kyoto climate finance",
         "year": "2001", "language": "en"},
        {"source": "istex", "source_id": "i1", "title": "La légitimité de la finance climat",
         "year": "1998", "language": "fr"},
        {"source": "istex", "source_id": "i2", "title": "Introduction", "year": "2010"},
        {"source": "istex", "source_id": "i3", "title": "Introduction", "year": "2010"},
    ]
    cat = tmp_path / "unified_works.csv"
    _write_csv(cat, CAT_COLUMNS, cat_rows)
    cfg = {"catalogue": {"md5": hashlib.md5(cat.read_bytes()).hexdigest(),
                         "rows": len(cat_rows)},
           "lane_order": ["t1652-causal", "t1810-repec"]}
    intake = tmp_path / "rel_intake"
    intake.mkdir()
    nfd = "La légitimité de la finance climat"
    _delivery(intake, "t1652-causal", "2026-09-30", [
        _rec("e1", title="Emerging markets’ carbon pricing", year="2015"),
        _rec("e2", title="Post Kyoto climate finance", year="2001",
             repec_handle="RePEc:abc:wpaper:7"),
        _rec("e3", title=nfd, year="1998", language="fr"),
        _rec("e4", title="<i>Climate</i> finance after Paris", year="2016", doi="10.1111/b"),
        _rec("e5", title="Aid and growth", year="2004", repec_handle="RePEc:nbr:nberwo:35497"),
        _rec("e6", title="Same handle other DOI", year="2004", doi="10.1111/c",
             repec_handle="RePEc:eee:wdevel:1"),
    ], extra_columns=["repec_handle"])
    _delivery(intake, "t1810-repec", "2026-10-01", [
        _rec("RePEc:nbr:nberwo:35497", title="Aid & growth revisited", year="2005"),
        _rec("RePEc:abc:wpaper:7", title="Post-Kyoto climate finance (WP)", year="2000"),
        _rec("RePEc:eee:wdevel:1", title="Same handle other DOI", year="2004", doi="10.1111/d"),
        _rec("RePEc:xyz:journl:9", title="<i>Climate</i> finance after Paris", year="2016"),
        _rec("oai:afres-id-1", title="Not a handle", year="2020"),
    ], excluded=[{"record_id": "RePEc:qqq:series:1", "query_id": "q1", "reason": "no_dedup_key",
                  "title": "A title only work with a handle"},
                 {"record_id": "x2", "query_id": "q1", "reason": "no_dedup_key",
                  "title": "Introduction"}])
    return cfg, cat, intake


def _build(tmp_path, monkeypatch, fixture=None, **kw):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1780000000")
    cfg, cat, intake = fixture or _fixture(tmp_path)
    out = tmp_path / "rel_pool"
    report = rp.run(cfg, str(cat), str(intake), str(out), **kw)
    return report, out


def test_version_1_pool_is_byte_identical_to_the_pool_before_2047(tmp_path, monkeypatch):
    _, out = _build(tmp_path, monkeypatch)
    assert hashlib.md5((out / "pool.csv").read_bytes()).hexdigest() == POOL_MD5_BEFORE_2047


def _v2(tmp_path, monkeypatch, fixture=None):
    mig = tmp_path / "migration"
    report, out = _build(tmp_path, monkeypatch, fixture, dedup_version=2, migration_dir=str(mig))
    with open(mig / "work_key_migration.csv", encoding="utf-8", newline="") as fh:
        table = list(csv.DictReader(fh))
    return report, out, mig, table


def _pairs(table):
    return {(r["old_work_key"], r["new_work_key"]): r for r in table}


def test_version_2_writes_report_and_migration_and_nothing_in_the_pool(tmp_path, monkeypatch):
    report, out, mig, table = _v2(tmp_path, monkeypatch)
    assert not out.exists(), "version 2 writes nothing in the pool directory"
    assert {p.name for p in mig.iterdir()} == {
        "work_key_migration.csv", "dedup_v2_works.csv", "dedup_v2_report.json", "dedup_v2_report.md"}
    pairs = _pairs(table)
    # The new title key joins the id-less lane row to the catalogue work.
    assert pairs[("title:emerging markets carbon pricing|2015", "openalex:W1")]["cause"] \
        == "title_key"
    # The RePEc handle joins the EDS row to the mirror row (titles and years differ).
    p = pairs[("title:aid and growth|2004", "repec:nbr:nberwo:35497")]
    assert (p["change"], p["cause"]) == ("merge", "repec_handle")
    # A title-only row whose record id is a handle is named by its handle.
    assert ("title:a title only work with a handle|", "repec:qqq:series:1") in pairs
    assert report["totals"]["works_v2"] < report["totals"]["works_v1"]


def test_repec_handle_never_joins_two_dois(tmp_path, monkeypatch):
    _, _, mig, _ = _v2(tmp_path, monkeypatch)
    with open(mig / "dedup_v2_works.csv", encoding="utf-8", newline="") as fh:
        works = list(csv.DictReader(fh))
    assert not [w for w in works if w["category"] == "multi_doi"]
    rows = [{"origin": "l", "delivery": "l/1", "doi": d, "openalex_id": "", "handle": "",
             "repec": "repec:eee:wdevel:1", "title": t, "year": "2004", "version_hint": ""}
            for d, t in (("10.1111/c", "One"), ("10.1111/d", "Two"), ("", "Three"))]
    roots = rd.cluster(rows, version=2)
    assert roots[0] != roots[1]
    assert len(set(rd.cluster(rows, version=1))) == 3


def test_repec_key_reads_handles_only():
    import _rel_pool_keys as rk
    assert rk.repec_key(" RePEc:NBR:nberwo:35497 ") == "repec:nbr:nberwo:35497"
    assert rk.repec_key("RePEc:nbr:nberwo:35497") == rk.repec_key("repec:nbr:NBERWO:35497")
    for not_a_handle in ("oai:afres-id-afres2025-025", "edsrep.p.nbr.nberwo.35497",
                         "1652:ty:aid and growth", "RePEc:nbr:nberwo", "", None):
        assert rk.repec_key(not_a_handle) == ""


def test_migration_table_is_append_only(tmp_path, monkeypatch):
    mig = tmp_path / "migration"
    mig.mkdir()
    (mig / "work_key_migration.csv").write_text(
        ",".join(rm.MIGRATION_COLUMNS) + "\n1,2,old-inputs,title:kept|2000,openalex:W9,rekey,title_key\n",
        encoding="utf-8")
    fixture = _fixture(tmp_path)
    _, _, _, first = _v2(tmp_path, monkeypatch, fixture)
    assert first[0]["old_work_key"] == "title:kept|2000", "an existing row is never rewritten"
    assert len(first) > 1
    report, _, _, second = _v2(tmp_path, monkeypatch, fixture)
    assert second == first and report["totals"]["migration_rows_appended"] == 0


def test_migration_table_of_another_shape_is_refused(tmp_path, monkeypatch):
    mig = tmp_path / "migration"
    mig.mkdir()
    (mig / "work_key_migration.csv").write_text("old,new\n", encoding="utf-8")
    with pytest.raises(ValueError, match="columns"):
        _v2(tmp_path, monkeypatch)


@pytest.mark.parametrize("where", ["pool", "inside", "parent"])
def test_migration_dir_must_be_outside_the_pool(tmp_path, where):
    cfg, cat, intake = _fixture(tmp_path)
    out = tmp_path / "rel_pool"
    mig = {"pool": out, "inside": out / "v2", "parent": tmp_path}[where]
    with pytest.raises(rp.RelPoolError, match="overlaps the pool"):
        rp.run(cfg, str(cat), str(intake), str(out), dedup_version=2, migration_dir=str(mig))
    assert not out.exists()


def test_dedup_version_comes_from_the_config_and_is_checked(tmp_path):
    cfg, cat, intake = _fixture(tmp_path)
    with pytest.raises(rp.RelPoolError, match="migration-dir is required"):
        rp.run({**cfg, "dedup_version": 2}, str(cat), str(intake), str(tmp_path / "p"))
    with pytest.raises(rp.RelPoolError, match="not one of"):
        rp.run(cfg, str(cat), str(intake), str(tmp_path / "p"), dedup_version=3)


def test_config_default_is_version_1():
    import yaml
    with open(rp.DEFAULT_CONFIG, encoding="utf-8") as fh:
        assert yaml.safe_load(fh)["dedup_version"] == 1


def test_report_counts_by_lane_period_language_and_first_act(tmp_path, monkeypatch):
    report, _, mig, _ = _v2(tmp_path, monkeypatch)
    merged = report["counts"]["merged"]
    assert merged["total"] == sum(merged["by_cause"].values()) > 0
    assert {"title_key", "repec_handle"} <= set(merged["by_cause"])
    assert sum(merged["by_period"].values()) == merged["total"]
    assert sum(merged["by_language"].values()) == merged["total"]
    assert report["first_act"]["merged"]["total"] == merged["by_period"]["1990-2006"] > 0
    assert "## First act, 1990-2006" in (mig / "dedup_v2_report.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("year, act", [("1989", "before 1990"), ("1990", "1990-2006"),
                                       ("2006", "1990-2006"), ("2007", "2007-2014"),
                                       ("2014", "2007-2014"), ("2015", "2015-2025"),
                                       ("2025", "2015-2025"), ("2026", "after 2025"),
                                       ("", "no year")])
def test_period_bounds(year, act):
    assert rm.period(year) == act


# ── Order independence, with a positive control ───────────

def _chain_rows():
    """Rows where a greedy step would decide by row order: two DOIs chained by
    Handles and RePEc handles, titles in both normalizations, title-only rows."""
    def r(doi="", oa="", handle="", repec="", title="x", year="2001", title_only=False):
        return {"origin": "l", "delivery": "l/1", "doi": doi, "openalex_id": oa,
                "handle": handle, "repec": repec, "title": title, "year": year,
                "version_hint": "", "title_only": title_only}
    return [r(doi="10.1111/a", handle="hdl:1/1", repec="repec:abc:s:1"),
            r(oa="W7", handle="hdl:1/1", repec="repec:abc:s:1"),
            r(oa="W7", handle="hdl:1/2", repec="repec:abc:s:2"),
            r(doi="10.1111/b", handle="hdl:1/2", repec="repec:abc:s:2"),
            r(doi="10.1111/e", repec="repec:abc:s:4"),
            r(oa="W8", repec="repec:abc:s:4"),
            r(oa="W8", repec="repec:abc:s:5"),
            r(doi="10.1111/f", repec="repec:abc:s:5"),
            r(repec="repec:abc:s:3", title="Post-Kyoto finance"),
            r(doi="10.1111/c", repec="repec:abc:s:3", title="Post Kyoto finance"),
            r(doi="10.1111/d", title="Post Kyoto finance"),
            r(title="Post-Kyoto finance"),
            r(title="Carbon markets’ futures in emerging economies", year="2003"),
            r(oa="W9", title="Carbon markets' futures in emerging economies", year="2003"),
            r(title="Carbon markets&rsquo; futures in emerging economies", year="",
              title_only=True)]


def _partition(rows, roots):
    comp = defaultdict(set)
    for i, root in enumerate(roots):
        comp[root].add(id(rows[i]))
    return {frozenset(c) for c in comp.values()}


def _order_independent(cluster, rows, seeds=range(12)):
    base = _partition(rows, cluster(rows))
    for seed in seeds:
        shuffled = rows[:]
        random.Random(seed).shuffle(shuffled)
        if _partition(shuffled, cluster(shuffled)) != base:
            return False
    return True


@pytest.mark.parametrize("version", [1, 2])
def test_partition_does_not_depend_on_row_order(version):
    rows = _chain_rows()
    roots = rd.cluster(rows, version=version)
    assert roots[0] != roots[3], "the chain never joins two DOIs"
    assert _order_independent(lambda rs: rd.cluster(rs, version=version), rows)


def test_order_test_catches_an_order_dependent_cascade(monkeypatch):
    """Positive control: a greedy Handle step (union as it goes, checked against
    the current components) is order-dependent, and the same test sees it."""
    def greedy(rows, uf, groups):
        for group in groups:
            for j in group[1:]:
                a, b = uf.find(group[0]), uf.find(j)
                dois = {r["doi"] for k, r in enumerate(rows) if r["doi"] and uf.find(k) in (a, b)}
                oas = {r["openalex_id"] for k, r in enumerate(rows)
                       if r["openalex_id"] and uf.find(k) in (a, b)}
                if len(dois) <= 1 and len(oas) <= 1:
                    uf.union(group[0], j)
        return []
    monkeypatch.setattr(rd, "_handle_unions", greedy)
    assert not _order_independent(lambda rs: rd.cluster(rs, version=2), _chain_rows())
