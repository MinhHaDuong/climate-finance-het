"""The profile counter over a small pool table (ticket 2043)."""

import csv
import gzip
import json

import _rel_profile as rp
import corpus_rel_profile as crp
import pytest

pytestmark = pytest.mark.domain_corpus

COLUMNS = ["work_key", "doi", "openalex_id", "title", "first_author", "all_authors", "year",
           "language", "doc_type", "sources", "all_dois", "all_openalex_ids", "member_record_ids"]


def _row(key, **kw):
    base = dict.fromkeys(COLUMNS, "") | {"work_key": key, "title": "T " + key, "year": "1999",
                                         "doc_type": "article", "sources": "laneA",
                                         "first_author": "A"}
    return base | kw


ROWS = [
    _row("w1", doi="10.1016/x.1"),                                     # complete
    _row("w2", doi="10.2139/ssrn.2", year="2010", language="es"),      # SSRN only: no publisher
    _row("w3", doi="10.1016/x.3", first_author="", year="2020"),       # no creator
    _row("w4", openalex_id="W4", year="2020", sources="laneB"),        # no publisher, no DOI
    _row("w5", doi="10.1016/x.5", doc_type="", language="en"),         # no resourceType
]


def _pool(tmp_path):
    path = tmp_path / "pool.csv"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(ROWS)
    return str(path)


def _run(tmp_path, backfill=None):
    profile = rp.load_profile()
    return crp.report(crp.count(_pool(tmp_path), backfill or {}, profile), profile, "p", None, 0)


def test_counts_and_waterfall(tmp_path):
    res = _run(tmp_path)
    six = res["scenarios"]["six_fields"]
    assert res["inputs"]["pool_works"] == 5 and six["excluded_works"] == 4
    assert six["first_failing_property"] == {"profile_missing_creator": 1,
                                             "profile_missing_publisher": 2,
                                             "profile_missing_resourceType": 1}
    assert res["scenarios"]["publisher_optional"]["excluded_works"] == 2
    assert res["scenarios"]["creator_ignored_publisher_optional"]["excluded_works"] == 1


def test_report_before_filter_and_first_act(tmp_path):
    b = _run(tmp_path)["before_filter"]
    assert b["first_act_1990_2006"] == {"works": 2, "share_of_pool": 0.4}
    assert b["by_lane"] == {"laneA": 4, "laneB": 1}
    assert b["non_english"]["language_known_works"] == 2 and b["non_english"]["works"] == 1
    assert b["non_english"]["language_unknown_works"] == 3


def test_backfill_joins_authors_and_host_org(tmp_path):
    bf = {"W4": ("B. Author", "B. Author", "Wiley")}
    res = _run(tmp_path, bf)
    # W4 now has a host organization: only the SSRN work and the no-creator, no-type works remain
    assert res["scenarios"]["six_fields"]["first_failing_property"].get(
        "profile_missing_publisher") == 1


def test_read_backfill_and_refuse_data_dir(tmp_path):
    path = tmp_path / "b.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(json.dumps({"openalex_id": "W9", "first_author": "X", "all_authors": ["X", "Y"],
                             "host_org_name": "Elsevier"}) + "\n")
    assert crp.read_backfill(str(path)) == {"W9": ("X", "X ; Y", "Elsevier")}
    assert crp.main(["--pool", "x", "--output-dir", rp.ROOT + "/data/rel_pool/out"]) == 1


# ── review fixes ─────────────────────────────────────────

@pytest.mark.parametrize("kind", ["data", "data/", "./data", "data/../data", "data/rel_pool",
                                  "symlink", "symlink/sub"])
def test_output_dir_in_or_equal_to_data_is_refused(kind, tmp_path, monkeypatch):
    """Each input wrote data/rel_profile_counts.json under the old prefix-only guard."""
    monkeypatch.chdir(rp.ROOT)
    out = kind
    if kind.startswith("symlink"):
        link = tmp_path / "link_to_data"
        link.symlink_to(rp.ROOT + "/data", target_is_directory=True)
        out = str(link) + kind[len("symlink"):]
    assert crp.under_data(out)
    assert crp.main(["--pool", "x", "--output-dir", out]) == 1


def test_output_dir_outside_data_is_allowed(tmp_path, monkeypatch):
    monkeypatch.chdir(rp.ROOT)
    assert not crp.under_data(str(tmp_path / "out"))
    assert not crp.under_data("data2")  # a sibling sharing the prefix is not data/


def _report_of(tmp_path, rows):
    path = tmp_path / "pool.csv"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    profile = rp.load_profile()
    return crp.report(crp.count(str(path), {}, profile), profile, "p", None, 0)


def test_empty_pool_reports_null_shares(tmp_path):
    res = _report_of(tmp_path, [])
    b = res["before_filter"]
    assert b["works"] == 0 and b["first_act_1990_2006"]["share_of_pool"] is None
    assert b["non_english"]["share_of_known_language"] is None
    assert res["scenarios"]["six_fields"]["excluded_share"] is None
    assert res["scenarios"]["six_fields"]["first_act_excluded_share"] is None


def test_all_blank_language_reports_null_not_zero(tmp_path):
    res = _report_of(tmp_path, [_row("a", doi="10.1016/x"), _row("b", doi="10.1016/y")])
    ne = res["before_filter"]["non_english"]
    assert ne["language_known_works"] == 0 and ne["share_of_known_language"] is None
    assert ne["share_of_pool"] == 0.0  # defined: 0 of 2


def test_no_first_act_work_reports_null_exclusion_share(tmp_path):
    res = _report_of(tmp_path, [_row("a", doi="10.1016/x", year="2020")])
    assert res["before_filter"]["first_act_1990_2006"] == {"works": 0, "share_of_pool": 0.0}
    assert res["scenarios"]["six_fields"]["first_act_excluded_share"] is None
