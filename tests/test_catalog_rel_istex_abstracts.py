"""Tests for scripts/catalog_rel_istex_abstracts.py (ticket 2046, stage A).

A fake transport stands in for api.istex.fr; no network.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import urllib.parse

import catalog_rel_istex_abstracts as m
import pytest

pytestmark = pytest.mark.domain_corpus

LONG = "Wind turbines are favoured in the switch-over to renewable energy. " * 4


def rec(doi, abstract=LONG, title="Wind turbine noise", year="2010", lang=("eng",)):
    r = {"doi": [doi], "title": title, "publicationDate": year, "language": list(lang),
         "corpusName": "elsevier", "arkIstex": "ark:/67375/X-%s" % doi[-3:]}
    if abstract is not None:
        r["abstract"] = abstract
    return r


class FakeIstex:
    """Answers the query the script builds: doi:("a" OR "b")."""

    def __init__(self, archive, status=200, absent_returns_all=False):
        self.archive, self.status, self.calls = archive, status, 0
        self.absent_returns_all = absent_returns_all

    def __call__(self, url):
        self.calls += 1
        if self.status != 200:
            return self.status, b"slow down"
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["q"][0]
        dois = re.findall(r'"([^"]+)"', q)
        hits = [self.archive[d] for d in dois if d in self.archive]
        if self.absent_returns_all and not hits:
            hits = [next(iter(self.archive.values()))]
        return 200, json.dumps({"total": len(hits), "hits": hits}).encode()


def archive_with_controls(extra=None):
    a = {m.POS_CONTROL_DOI: rec(m.POS_CONTROL_DOI)}
    a.update(extra or {})
    return a


def write_pool(path, rows):
    cols = ["work_key", "doi", "title", "year", "abstract", "language", "sources"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])


def pool_rows(n=45):
    return [{"work_key": "doi:10.1/%03d" % i, "doi": "10.1/%03d" % i, "title": "Wind turbine noise",
             "year": "2010", "sources": "t1650-sommaires"} for i in range(n)]


def fetch_args(tmp, pool, **kw):
    d = dict(pool=str(pool), output_dir=str(tmp / "arch"), delay=0, max_batches=None, base_url=m.BASE_URL)
    d.update(kw)
    return argparse.Namespace(**d)


def analyze_args(tmp, **kw):
    d = dict(output_dir=str(tmp / "arch"), analysis_dir="analysis", year_tolerance=1,
             title_threshold=0.8, min_chars=100, allow_partial=False)
    d.update(kw)
    return argparse.Namespace(**d)


def test_batches_of_twenty_and_url_quotes_dois():
    b = m.batches_of(["10.1/%d" % i for i in range(45)])
    assert [len(x) for x in b] == [20, 20, 5]
    url = m.build_url(['10.1/a"b', "10.1016/s0305-750x(02)00072-4"])
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["q"][0]
    assert q.startswith("doi:(") and '\\"' in q and "(02)" in q


def test_fetch_archives_resumes_and_never_rewrites(tmp_path):
    pool = tmp_path / "pool.csv"
    write_pool(pool, pool_rows())
    api = FakeIstex(archive_with_controls({"10.1/001": rec("10.1/001")}))
    assert m.cmd_fetch(fetch_args(tmp_path, pool, max_batches=1), api) == 0
    raw = tmp_path / "arch" / "raw"
    assert sorted(os.listdir(raw)) == ["b000001.json"]
    first = hashlib.sha256((raw / "b000001.json").read_bytes()).hexdigest()
    assert m.cmd_fetch(fetch_args(tmp_path, pool), api) == 0
    assert sorted(os.listdir(raw)) == ["b000001.json", "b000002.json", "b000003.json"]
    assert hashlib.sha256((raw / "b000001.json").read_bytes()).hexdigest() == first
    manifest = (tmp_path / "arch" / "MANIFEST.sha256").read_text()
    assert "raw/b000003.json" in manifest and "pool_input.csv" in manifest
    sha = open(tmp_path / "arch" / "pool_input.sha256").read().split()[0]
    assert sha == hashlib.sha256(pool.read_bytes()).hexdigest()


def test_http_error_stops_without_retry_and_archives_nothing(tmp_path):
    pool = tmp_path / "pool.csv"
    write_pool(pool, pool_rows())
    api = FakeIstex(archive_with_controls(), status=429)
    assert m.cmd_fetch(fetch_args(tmp_path, pool), api) == 2
    assert api.calls == 1  # the first control query; no second try
    assert os.listdir(tmp_path / "arch" / "raw") == []


def test_negative_control_failure_blocks_fetch(tmp_path):
    pool = tmp_path / "pool.csv"
    write_pool(pool, pool_rows())
    api = FakeIstex(archive_with_controls(), absent_returns_all=True)
    assert m.cmd_fetch(fetch_args(tmp_path, pool), api) == 2
    assert os.listdir(tmp_path / "arch" / "raw") == []


def test_truncated_answer_stops():
    def get(url):
        return 200, json.dumps({"total": 5, "hits": [rec("10.1/001")]}).encode()
    with pytest.raises(m.StopRun):
        m._query(get, m.build_url(["10.1/001"]))


def test_analyze_refuses_without_controls_or_with_partial_archive(tmp_path):
    pool = tmp_path / "pool.csv"
    write_pool(pool, pool_rows())
    api = FakeIstex(archive_with_controls())
    m.cmd_fetch(fetch_args(tmp_path, pool, max_batches=1), api)
    assert m.cmd_analyze(analyze_args(tmp_path)) == 2  # partial
    assert not (tmp_path / "arch" / "analysis").exists()
    os.remove(tmp_path / "arch" / "controls.jsonl")
    assert m.cmd_analyze(analyze_args(tmp_path, allow_partial=True)) == 2  # no controls


def test_analyze_counts_every_rejection_cause_and_is_not_overwritten(tmp_path):
    rows = pool_rows(10)
    arch = archive_with_controls({
        "10.1/000": rec("10.1/000"),                                           # accepted
        "10.1/001": rec("10.1/001", abstract="Abstract: " + LONG),             # accepted, label stripped
        "10.1/002": rec("10.1/002", year="2015"),                              # year
        "10.1/003": rec("10.1/003", title="A totally different paper on trade"),  # title
        "10.1/004": rec("10.1/004", abstract="International audience"),        # boilerplate
        "10.1/005": rec("10.1/005", abstract="A short note on wind turbine noise in rural Sweden."),  # stub
        "10.1/006": rec("10.1/006", abstract=None),                            # no abstract
        "10.1/007": rec("10.1/007", year="2011"),                              # within tolerance
    })
    pool = tmp_path / "pool.csv"
    write_pool(pool, rows)
    assert m.cmd_fetch(fetch_args(tmp_path, pool), FakeIstex(arch)) == 0
    assert m.cmd_analyze(analyze_args(tmp_path)) == 0
    ana = tmp_path / "arch" / "analysis"
    c = {(r["dimension"], r["value"], r["metric"]): int(r["n"])
         for r in csv.DictReader(open(ana / "counts.csv"))}
    g = lambda metric: c[("overall", "all", metric)]
    assert g("queried") == 10 and g("accepted") == 3 and g("not_found") == 2
    for cause in m.CAUSES:
        assert g("rejected_" + cause) == 1, cause
    assert g("with_abstract_after") == g("with_abstract_before") + 3 == 3
    assert c[("lane", "t1650-sommaires", "accepted")] == 3
    acc = {r["doi"]: r["abstract"] for r in csv.DictReader(open(ana / "istex_abstracts_accepted.csv"))}
    assert set(acc) == {"10.1/000", "10.1/001", "10.1/007"}
    assert not acc["10.1/001"].lower().startswith("abstract")
    with pytest.raises(FileExistsError):
        m._analyze(analyze_args(tmp_path))


def test_judge_never_replaces_a_pool_abstract():
    row = {"title": "t", "year": "2010", "abstract": "already here"}
    with pytest.raises(ValueError):
        m.judge(row, [rec("10.1/x")], "10.1/x", {"year_tolerance": 1, "title_threshold": 0.8, "min_chars": 100},
                lambda a, title=None: False)


def test_judge_red_guards():
    """Each guard fires on the defect that motivates it (replayed)."""
    cfg = {"year_tolerance": 1, "title_threshold": 0.8, "min_chars": 100}
    row = {"title": "Wind turbine noise", "year": "2010", "abstract": ""}
    bp = lambda a, title=None: a.lower() == "international audience"
    assert m.judge(row, [rec("d", year="2013")], "d", cfg, bp)["status"] == "rejected:year_mismatch"
    assert m.judge(row, [rec("d", title="Other")], "d", cfg, bp)["status"] == "rejected:title_mismatch"
    assert m.judge(row, [rec("d")], "d", cfg, bp)["status"] == "accepted"
    # several records on one DOI: the sound one wins over the wrong-year one
    assert m.judge(row, [rec("d", year="1999"), rec("d")], "d", cfg, bp)["status"] == "accepted"
