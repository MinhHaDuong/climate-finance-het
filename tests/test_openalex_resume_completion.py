"""An interrupted OpenAlex page sequence must not advance its checkpoint."""

import gzip
import json
from types import SimpleNamespace

import openalex_pool as pool
import pytest

pytestmark = pytest.mark.wp_corpus


class Response:
    def __init__(self, results=(), next_cursor=None, remaining="1", status=200):
        self.status_code = status
        self.headers = {"X-RateLimit-Remaining-USD": remaining}
        self._payload = {
            "results": [{"id": f"https://openalex.org/{work}"} for work in results],
            "meta": {"count": 3, "next_cursor": next_cursor},
        }

    def json(self):
        return self._payload


@pytest.mark.parametrize("interruption", ["zero_budget", "rate_limit"])
def test_interrupted_query_replays_original_window(monkeypatch, tmp_path, interruption):
    sidecar = tmp_path / "_query_dates.json"
    pool_file = tmp_path / "works.jsonl.gz"
    slug = pool.query_slug("climate finance")
    old_date = "2026-03-01"
    dates = {slug: old_date, "unrelated_query": "2026-04-01"}
    pool.save_query_dates(dates, str(sidecar))
    real_save = pool.save_query_dates
    monkeypatch.setattr(pool, "save_query_dates", lambda value: real_save(value, str(sidecar)))
    monkeypatch.setattr(pool, "pool_path", lambda source, query: str(pool_file))

    if interruption == "zero_budget":
        first = [Response(), Response(["W1"], "c2", remaining="0")]
    else:
        first = [Response(), Response(["W1"], "c2"), Response(status=429, remaining="?")]
    replay = [Response(), Response(["W1"], "c2"), Response(["W2", "W3"])]
    seen_filters = []
    responses = first

    def fake_get(url, params, **kwargs):
        seen_filters.append(params["filter"])
        return responses.pop(0)

    monkeypatch.setattr(pool, "polite_get", fake_get)
    args = SimpleNamespace(dry_run=False, delay=0, limit=0)
    tiers = {1: {"terms": ["climate finance"]}}
    ids = set()

    result = pool._download_tiers(tiers, args, ids, dates, None, 1990, 2026, "2026-09-28")
    assert result[:3] == (1, 0, 1)
    assert pool.load_query_dates(str(sidecar)) == {slug: old_date, "unrelated_query": "2026-04-01"}
    assert ids == {"W1"}
    assert responses == []

    responses = replay
    result = pool._download_tiers(tiers, args, ids, dates, None, 1990, 2026, "2026-09-28")
    assert result[:3] == (2, 1, 0)
    assert pool.load_query_dates(str(sidecar)) == {
        slug: "2026-09-28", "unrelated_query": "2026-04-01",
    }
    assert ids == {"W1", "W2", "W3"}
    with gzip.open(pool_file, "rt") as stream:
        assert [json.loads(line)["id"].rsplit("/", 1)[-1] for line in stream] == [
            "W1", "W2", "W3",
        ]
    assert all("from_created_date:2026-03-01" in value for value in seen_filters)


def test_record_limit_does_not_advance_date(monkeypatch, tmp_path):
    sidecar = tmp_path / "_query_dates.json"
    pool_file = tmp_path / "works.jsonl.gz"
    slug = pool.query_slug("climate finance")
    dates = {slug: "2026-03-01"}
    pool.save_query_dates(dates, str(sidecar))
    real_save = pool.save_query_dates
    monkeypatch.setattr(pool, "save_query_dates", lambda value: real_save(value, str(sidecar)))
    monkeypatch.setattr(pool, "pool_path", lambda source, query: str(pool_file))
    responses = [Response(), Response(["W1"], "c2")]
    monkeypatch.setattr(pool, "polite_get", lambda url, params, **kwargs: responses.pop(0))

    result = pool._download_tiers(
        {1: {"terms": ["climate finance"]}},
        SimpleNamespace(dry_run=False, delay=0, limit=1),
        set(), dates, None, 1990, 2026, "2026-09-28",
    )
    assert result[:3] == (1, 0, 1)
    assert pool.load_query_dates(str(sidecar)) == {slug: "2026-03-01"}
