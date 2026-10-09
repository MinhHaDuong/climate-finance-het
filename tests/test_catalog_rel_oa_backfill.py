"""The id-batched OpenAlex backfill (ticket 2041): metered, resumable, no live call in tests."""

import gzip
import json
import types

import catalog_rel_oa_backfill as bf
import pytest

pytestmark = pytest.mark.domain_corpus


class _Resp:
    def __init__(self, status=200, results=(), count=None, cost="0.0005", remaining="0.9"):
        self.status_code = status
        self._body = {"meta": {"count": len(results) if count is None else count},
                      "results": list(results)}
        self.headers = {"x-ratelimit-cost-usd": cost, "x-ratelimit-remaining-usd": remaining,
                        "x-ratelimit-prepaid-remaining-usd": "4.5"}

    def json(self):
        return self._body


def _work(i):
    return {"id": f"https://openalex.org/W{i}",
            "authorships": [{"author": {"display_name": f"Author {i}"}}],
            "primary_location": {"source": {"host_organization": "https://openalex.org/P9",
                                            "host_organization_name": "Wiley", "type": "journal",
                                            "issn": ["1111-2222"]}},
            "locations": [{"source": {"host_organization_name": "Elsevier"}}]}


def _src(tmp_path, ids):
    p = tmp_path / "lane1" / "results.jsonl.gz"
    p.parent.mkdir()
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        for i in ids:
            fh.write(json.dumps({"openalex_id": f"W{i}", "year": 2016, "language": "fr"}) + "\n")
    return str(p)


def _args(tmp_path, src, **kw):
    base = dict(ids=[src], output_dir=str(tmp_path / "out"), batch=2, lane_cap=1.0,
                daily_floor=0.1, max_batches=0, delay=0, dry_run=False, cost_per_call=None,
                daily_budget=1.0)
    base.update(kw)
    return types.SimpleNamespace(**base)


def _patch_get(monkeypatch, responses, seen):
    it = iter(responses)

    def fake_get(url, params=None, delay=0):
        seen.append(params)
        return next(it)

    monkeypatch.setattr(bf, "polite_get", fake_get)


def test_dry_run_prices_batches_and_makes_no_call_and_needs_no_key(tmp_path, monkeypatch):
    monkeypatch.setattr(bf, "polite_get", lambda *a, **k: pytest.fail("live call in a dry run"))
    src = _src(tmp_path, range(1, 6))
    assert bf.run(_args(tmp_path, src, dry_run=True, cost_per_call=0.01), None) == 0
    assert not (tmp_path / "out").exists()


def test_run_refuses_without_a_key(tmp_path, monkeypatch):
    monkeypatch.setattr(bf, "polite_get", lambda *a, **k: pytest.fail("unauthenticated call"))
    assert bf.run(_args(tmp_path, _src(tmp_path, [1, 2])), "") == 2


def test_batch_asks_by_openalex_id_with_the_ticket_select_and_records_found_and_absent(
        tmp_path, monkeypatch):
    seen = []
    _patch_get(monkeypatch, [_Resp(results=[_work(1)])], seen)  # W2 no longer exists
    assert bf.run(_args(tmp_path, _src(tmp_path, [1, 2])), "k") == 0
    assert seen[0]["filter"] == "ids.openalex:W1|W2"
    assert seen[0]["select"] == "id,authorships,primary_location,locations"
    out = str(tmp_path / "out")
    assert bf.read_done(out) == {"W1": "found", "W2": "absent"}
    rec = bf.read_backfill(out)["W1"]
    assert (rec["all_authors"], rec["host_org_name"], rec["host_org_id"]) == (["Author 1"], "Wiley", "P9")
    assert rec["location_hosts"] == ["Elsevier"]
    spend = json.loads((tmp_path / "out" / "spend.jsonl").read_text().splitlines()[-1])
    assert spend["cost_per_call_usd"] == [0.0005] and spend["prepaid_remaining_usd_at_end"] == 4.5


def test_429_stops_the_run_and_leaves_the_batch_pending_then_a_rerun_resumes(tmp_path, monkeypatch):
    src = _src(tmp_path, [1, 2, 3, 4])
    _patch_get(monkeypatch, [_Resp(results=[_work(1), _work(2)]), _Resp(status=429)], [])
    bf.run(_args(tmp_path, src), "k")
    out = str(tmp_path / "out")
    assert set(bf.read_done(out)) == {"W1", "W2"}  # W3, W4 not counted done
    seen = []
    _patch_get(monkeypatch, [_Resp(results=[_work(3), _work(4)])], seen)
    bf.run(_args(tmp_path, src), "k")
    assert seen[0]["filter"] == "ids.openalex:W3|W4"  # done ids are not asked again
    assert set(bf.read_done(out)) == {"W1", "W2", "W3", "W4"}
    assert set(bf.read_backfill(out)) == {"W1", "W2", "W3", "W4"}


def test_daily_floor_stops_before_the_next_call(tmp_path, monkeypatch):
    src = _src(tmp_path, [1, 2, 3, 4])
    seen = []
    _patch_get(monkeypatch, [_Resp(results=[_work(1), _work(2)], remaining="0.05")], seen)
    bf.run(_args(tmp_path, src), "k")
    assert len(seen) == 1 and set(bf.read_done(str(tmp_path / "out"))) == {"W1", "W2"}


def test_lane_cap_stops_before_the_next_call(tmp_path, monkeypatch):
    seen = []
    _patch_get(monkeypatch, [_Resp(results=[_work(1), _work(2)], cost="0.01")], seen)
    bf.run(_args(tmp_path, _src(tmp_path, [1, 2, 3, 4]), lane_cap=0.01), "k")
    assert len(seen) == 1


def test_a_page_shorter_than_the_announced_count_is_not_recorded_as_done(tmp_path, monkeypatch):
    _patch_get(monkeypatch, [_Resp(results=[_work(1)], count=2)], [])
    bf.run(_args(tmp_path, _src(tmp_path, [1, 2])), "k")
    assert bf.read_done(str(tmp_path / "out")) == {}


def test_max_batches_makes_a_one_batch_probe(tmp_path, monkeypatch):
    seen = []
    _patch_get(monkeypatch, [_Resp(results=[_work(1), _work(2)])], seen)
    bf.run(_args(tmp_path, _src(tmp_path, [1, 2, 3, 4]), max_batches=1), "k")
    assert len(seen) == 1


def test_coverage_counts_authors_host_organization_and_neither_per_stratum(tmp_path):
    src = _src(tmp_path, [1, 2, 3])
    ids, meta = bf.read_ids([src])
    done = {"W1": "found", "W2": "found", "W3": "absent"}
    recs = {"W1": {"all_authors": ["A"], "host_org_name": "Wiley"},
            "W2": {"all_authors": ["B"], "host_org_name": ""}}
    ((key, row),) = bf.coverage(ids, meta, done, recs).items()
    assert key == ("lane1", "2015-2025", "fr")
    assert (row["n"], row["done"], row["authors"], row["host_org"], row["neither"]) == (3, 3, 2, 1, 1)
