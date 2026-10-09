"""Recovery of the blank resource type (ticket 2050): metered, resumable, no live call in tests."""

import csv
import json
import types

import catalog_rel_doc_type_recover as dt
import pytest

pytestmark = pytest.mark.domain_corpus

POOL_COLUMNS = ["doi", "openalex_id", "doc_type", "year", "language", "catalogue_sources"]


class _Resp:
    def __init__(self, status=200, results=(), count=None, cost="0.0001", remaining="0.9", body=None):
        self.status_code = status
        self._body = body if body is not None else {
            "meta": {"count": len(results) if count is None else count}, "results": list(results)}
        self.headers = {"x-ratelimit-cost-usd": cost, "x-ratelimit-remaining-usd": remaining}

    def json(self):
        return self._body


def _pool(tmp_path, rows):
    path = tmp_path / "pool.csv"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=POOL_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in POOL_COLUMNS})
    return str(path)


def _args(tmp_path, pool, **kw):
    base = dict(pool=pool, output_dir=str(tmp_path / "out"), route="openalex", batch=100,
                lane_cap=1.0, daily_floor=0.0, max_batches=0, dry_run=False, cost_per_call=None,
                daily_budget=1.0, crossref_scope="unanswered", crossref_delay=0.0, merge=False)
    base.update(kw)
    return types.SimpleNamespace(**base)


def _work(i, typ="article", doi=""):
    return {"id": f"https://openalex.org/W{i}", "doi": f"https://doi.org/{doi}" if doi else None,
            "type": typ}


ROWS = [
    {"openalex_id": "W1", "year": "2010", "catalogue_sources": "openalex"},
    {"openalex_id": "W2", "doi": "10.1/b", "year": "2020", "catalogue_sources": "openalex"},
    {"doi": "10.1/c", "year": "2016", "catalogue_sources": "istex;scispace"},
    {"openalex_id": "W9", "doc_type": "report", "year": "2012"},   # not blank: never a target
    {"year": "2001"},                                               # no identifier: no target
]


def test_targets_are_the_blank_works_that_carry_an_identifier(tmp_path):
    targets = dt.read_targets(_pool(tmp_path, ROWS))
    assert [dt.lookup_key(t) for t in targets] == ["W1", "W2", "10.1/c"]
    assert [t["source"] for t in targets] == ["openalex", "openalex", "istex"]
    assert [t["period"] for t in targets] == ["2007-2014", "2015-2025", "2015-2025"]


def test_dry_run_prices_the_calls_and_needs_no_key_no_call(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("a dry run must not call out")
    monkeypatch.setattr(dt.requests, "get", boom)
    monkeypatch.setattr(dt, "read_credential", boom)
    pool = _pool(tmp_path, ROWS)
    rc = dt.main(["--pool", pool, "--output-dir", str(tmp_path / "out"), "--dry-run",
                  "--cost-per-call", "0.0001"])
    assert rc == 0
    assert not (tmp_path / "out").exists()


def test_batches_split_by_key_kind_and_skip_what_is_done():
    targets = [{"openalex_id": "W1", "doi": ""}, {"openalex_id": "", "doi": "10.1/c"},
               {"openalex_id": "W3", "doi": "10.1/d"}]
    assert dt.oa_batches(targets, {}, size=2) == [
        ("ids.openalex", ["W1", "W3"]), ("doi", ["10.1/c"])]
    assert dt.oa_batches(targets, {"W1": "found"}, size=2) == [
        ("ids.openalex", ["W3"]), ("doi", ["10.1/c"])]


def test_the_request_asks_by_id_or_by_doi_with_the_ticket_select():
    seen = []

    def get(params):
        seen.append(params)
        return _Resp(results=[])
    meter = dt.Meter(1.0, 0.0)
    dt.fetch_openalex("ids.openalex", ["W1", "W2"], "K", meter, get=get)
    dt.fetch_openalex("doi", ["10.1/c"], "K", meter, get=get)
    assert seen[0]["filter"] == "ids.openalex:W1|W2" and seen[0]["select"] == "id,doi,type"
    assert seen[0]["per_page"] == 2
    assert seen[1]["filter"] == "doi:https://doi.org/10.1/c"


def test_run_records_found_with_their_type_and_absent_without(tmp_path, monkeypatch):
    pool = _pool(tmp_path, ROWS)
    monkeypatch.setattr(dt.requests, "get", lambda *a, **k: _Resp(results=[
        _work(1, "book"), _work(2, "preprint", "10.1/b"), _work(77, "other", "10.1/zzz")]))
    args = _args(tmp_path, pool)
    assert dt.run_openalex(args, dt.read_targets(pool), "K") == ""
    recs = dt.read_records(args.output_dir, "openalex")
    assert {k: v["type"] for k, v in recs.items()} == {"W1": "book", "W2": "preprint"}
    assert dt.read_done(args.output_dir, "openalex") == {
        "W1": "found", "W2": "found", "10.1/c": "absent"}


def test_429_stops_at_once_leaves_the_batch_pending_and_a_rerun_resumes(tmp_path, monkeypatch):
    pool = _pool(tmp_path, ROWS)
    calls = []

    def get(url, params=None, **kw):
        calls.append(params["filter"])
        return _Resp(status=429)
    monkeypatch.setattr(dt.requests, "get", get)
    args = _args(tmp_path, pool)
    stop = dt.run_openalex(args, dt.read_targets(pool), "K")
    assert "429" in stop and len(calls) == 1  # one call: no retry loop
    assert dt.read_done(args.output_dir, "openalex") == {}
    monkeypatch.setattr(dt.requests, "get", lambda *a, **k: _Resp(results=[_work(1), _work(2)]))
    assert dt.run_openalex(args, dt.read_targets(pool), "K") == ""
    assert set(dt.read_done(args.output_dir, "openalex")) == {"W1", "W2", "10.1/c"}


def test_lane_cap_and_daily_floor_stop_before_the_next_call(tmp_path, monkeypatch):
    pool = _pool(tmp_path, ROWS)
    monkeypatch.setattr(dt.requests, "get", lambda *a, **k: _Resp(results=[], cost="0.6"))
    args = _args(tmp_path, pool, lane_cap=0.5)
    stop = dt.run_openalex(args, dt.read_targets(pool), "K")
    assert stop.startswith("budget: lane cap")
    assert len(dt.read_done(args.output_dir, "openalex")) == 2  # first batch only
    args = _args(tmp_path / "b", pool, daily_floor=0.95)
    monkeypatch.setattr(dt.requests, "get", lambda *a, **k: _Resp(results=[], remaining="0.5"))
    assert dt.run_openalex(args, dt.read_targets(pool), "K").startswith("budget: daily remaining")


def test_a_short_page_and_an_insufficient_answer_mark_nothing_done(tmp_path, monkeypatch):
    pool = _pool(tmp_path, ROWS)
    args = _args(tmp_path, pool)
    monkeypatch.setattr(dt.requests, "get", lambda *a, **k: _Resp(results=[_work(1)], count=5))
    assert dt.run_openalex(args, dt.read_targets(pool), "K").startswith("short page")
    body = {"meta": {"count": 0, "error": "insufficient budget"}, "results": []}
    monkeypatch.setattr(dt.requests, "get", lambda *a, **k: _Resp(body=body))
    assert dt.run_openalex(args, dt.read_targets(pool), "K") == "insufficient budget"
    assert dt.read_done(args.output_dir, "openalex") == {}


def test_a_line_cut_by_a_crash_is_skipped_and_the_next_append_starts_a_new_line(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    dt.write_batch(str(out), "openalex", [{"key": "W1", "type": "book"}], [("W1", "found")])
    with open(out / "openalex.jsonl", "a", encoding="utf-8") as fh:
        fh.write('{"key": "W2", "ty')
    dt.write_batch(str(out), "openalex", [{"key": "W3", "type": "report"}], [("W3", "found")])
    assert set(dt.read_records(str(out), "openalex")) == {"W1", "W3"}


def test_no_archive_line_is_blank_when_a_batch_answers_nothing(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    dt.write_batch(str(out), "crossref", [], [("10.1/x", "absent")])
    assert not (out / "crossref.jsonl").exists()


def test_crossref_asks_only_the_dois_openalex_left_without_a_type_unless_scope_all(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    dt.write_batch(str(out), "openalex", [{"key": "W2", "type": "preprint"}],
                   [("W2", "found"), ("W1", "absent"), ("10.1/c", "absent")])
    targets = dt.read_targets(_pool(tmp_path, ROWS))
    assert dt.crossref_pending(targets, dt.read_records(str(out), "openalex"), {}, "unanswered") == ["10.1/c"]
    assert dt.crossref_pending(targets, dt.read_records(str(out), "openalex"), {}, "all") == ["10.1/b", "10.1/c"]


def test_crossref_records_found_and_404_and_stops_on_429_without_retry(tmp_path):
    pool = _pool(tmp_path, [{"doi": "10.1/a"}, {"doi": "10.1/b"}, {"doi": "10.1/c"}])
    answers = iter([_Resp(body={"message": {"type": "journal-article"}}), _Resp(status=404),
                    _Resp(status=429)])
    asked = []

    def get(doi):
        asked.append(doi)
        return next(answers)
    args = _args(tmp_path, pool, route="crossref", crossref_scope="all")
    (tmp_path / "out").mkdir()
    stop = dt.run_crossref(args, dt.read_targets(pool), get=get, sleep=lambda s: None)
    assert "429" in stop and asked == ["10.1/a", "10.1/b", "10.1/c"]
    assert dt.read_done(args.output_dir, "crossref") == {"10.1/a": "found", "10.1/b": "absent"}
    assert dt.read_records(args.output_dir, "crossref")["10.1/a"]["type"] == "journal-article"


def test_decision_rule_openalex_wins_crossref_fills_and_unknown_is_kept():
    assert dt.decide("article", "journal-article") == ("article", "openalex")
    assert dt.decide("preprint", "journal-article") == ("preprint", "openalex+crossref-differs")
    assert dt.decide("", "posted-content") == ("preprint", "crossref")
    assert dt.decide("grant", "") == ("grant", "openalex-unmapped")      # kept, never invented
    assert dt.decide("", "weird-type") == ("weird-type", "crossref-unmapped")
    assert dt.decide("", "") == ("", "none")


def test_merge_writes_only_recovered_blank_works_counts_unmapped_and_never_overwrites(tmp_path):
    pool = _pool(tmp_path, ROWS)
    out = tmp_path / "out"
    out.mkdir()
    dt.write_batch(str(out), "openalex",
                   [{"key": "W1", "openalex_id": "W1", "doi": "", "type": "grant"},
                    {"key": "W2", "openalex_id": "W2", "doi": "10.1/b", "type": "book"}],
                   [("W1", "found"), ("W2", "found"), ("10.1/c", "absent")])
    dt.write_batch(str(out), "crossref", [{"key": "10.1/c", "doi": "10.1/c", "type": "posted-content"}],
                   [("10.1/c", "found")])
    args = _args(tmp_path, pool)
    rows = dt.merge(args, dt.read_targets(pool))
    assert [(r[0], r[1], r[2]) for r in rows] == [
        ("W1", "", "grant"), ("W2", "10.1/b", "book"), ("", "10.1/c", "preprint")]
    with open(out / "doc_types.csv", encoding="utf-8", newline="") as fh:
        got = list(csv.DictReader(fh))
    assert "W9" not in {r["openalex_id"] for r in got}  # the non-blank pool work is never delivered
    with open(out / "coverage.csv", encoding="utf-8", newline="") as fh:
        cov = {(r["source"], r["period"]): r for r in csv.DictReader(fh)}
    assert cov[("openalex", "2007-2014")]["recovered"] == "1"
    assert cov[("istex", "2015-2025")]["crossref"] == "1"
    before = (out / "doc_types.csv").read_bytes()
    with pytest.raises(SystemExit):
        dt.merge(args, dt.read_targets(pool))
    assert (out / "doc_types.csv").read_bytes() == before


def test_run_refuses_without_a_key(tmp_path, monkeypatch):
    monkeypatch.setattr(dt, "read_credential", lambda *a: None)
    pool = _pool(tmp_path, ROWS)
    assert dt.main(["--pool", pool, "--output-dir", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out" / "openalex.jsonl").exists()


def test_the_cli_exits_nonzero_on_a_stop_and_zero_on_a_max_batches_probe(tmp_path, monkeypatch):
    monkeypatch.setattr(dt, "read_credential", lambda *a: "K")
    pool = _pool(tmp_path, ROWS)
    monkeypatch.setattr(dt.requests, "get", lambda *a, **k: _Resp(status=429))
    assert dt.main(["--pool", pool, "--output-dir", str(tmp_path / "o1")]) == 1
    monkeypatch.setattr(dt.requests, "get", lambda *a, **k: _Resp(results=[_work(1)]))
    assert dt.main(["--pool", pool, "--output-dir", str(tmp_path / "o2"), "--max-batches", "1"]) == 0
    with open(tmp_path / "o2" / "spend.jsonl", encoding="utf-8") as fh:
        assert json.loads(fh.readline())["stopped"] == "max batches 1"
