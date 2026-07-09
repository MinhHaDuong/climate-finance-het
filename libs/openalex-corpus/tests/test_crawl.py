"""Contract tests for retry_get — the shared polite HTTP fetcher.

Uses requests-mock (no real network) and stubs sleep to keep the suite fast.
Freezes the retry/backoff contract both consuming repos depend on.
"""

import pytest
import requests
from openalex_corpus import retry_get


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Neutralise backoff/politeness delays so tests run instantly."""
    monkeypatch.setattr("openalex_corpus.crawl.time.sleep", lambda *_: None)


def test_success_returns_response(requests_mock):
    requests_mock.get("https://api.openalex.org/works", json={"ok": True})
    resp = retry_get("https://api.openalex.org/works")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_retries_429_then_succeeds(requests_mock):
    requests_mock.get(
        "https://api.openalex.org/works",
        [{"status_code": 429, "headers": {"Retry-After": "0"}},
         {"status_code": 200, "json": {"ok": True}}],
    )
    counters: dict[str, int] = {}
    resp = retry_get("https://api.openalex.org/works", counters=counters)
    assert resp.status_code == 200
    assert counters["rate_limited"] == 1
    assert requests_mock.call_count == 2


def test_retries_500_then_succeeds(requests_mock):
    requests_mock.get(
        "https://api.openalex.org/works",
        [{"status_code": 503}, {"status_code": 200, "json": {"ok": True}}],
    )
    counters: dict[str, int] = {}
    resp = retry_get("https://api.openalex.org/works", counters=counters)
    assert resp.status_code == 200
    assert counters["server_errors"] == 1


def test_persistent_429_returns_last_response_not_raise(requests_mock):
    requests_mock.get(
        "https://api.openalex.org/works",
        status_code=429, headers={"Retry-After": "0"},
    )
    resp = retry_get("https://api.openalex.org/works", max_retries=3)
    assert resp.status_code == 429  # graceful degrade, not RuntimeError


def test_4xx_raises_immediately(requests_mock):
    requests_mock.get("https://api.openalex.org/works", status_code=404)
    with pytest.raises(requests.exceptions.HTTPError):
        retry_get("https://api.openalex.org/works")


def test_persistent_500_exhausts_to_runtimeerror(requests_mock):
    requests_mock.get("https://api.openalex.org/works", status_code=500)
    with pytest.raises(RuntimeError, match="Failed after 2 attempts"):
        retry_get("https://api.openalex.org/works", max_retries=2)


def test_retries_timeout_then_succeeds(requests_mock):
    requests_mock.get(
        "https://api.openalex.org/works",
        [{"exc": requests.exceptions.Timeout},
         {"status_code": 200, "json": {"ok": True}}],
    )
    counters: dict[str, int] = {}
    resp = retry_get("https://api.openalex.org/works", counters=counters)
    assert resp.status_code == 200
    assert counters["retries"] == 1


class TestMailtoInjection:
    """mailto is injected by the caller, never hardcoded in the package."""

    def test_mailto_added_to_params_and_user_agent(self, requests_mock):
        requests_mock.get("https://api.openalex.org/works", json={})
        retry_get("https://api.openalex.org/works", mailto="a@b.org")
        req = requests_mock.last_request
        assert req.qs["mailto"] == ["a@b.org"]
        assert "mailto:a@b.org" in req.headers["User-Agent"]

    def test_no_mailto_means_no_mailto_param(self, requests_mock):
        requests_mock.get("https://api.openalex.org/works", json={})
        retry_get("https://api.openalex.org/works")
        assert "mailto" not in requests_mock.last_request.qs

    def test_explicit_user_agent_overrides_default(self, requests_mock):
        requests_mock.get("https://api.openalex.org/works", json={})
        retry_get("https://api.openalex.org/works", mailto="a@b.org",
                  user_agent="MyPipeline/2.0 (mailto:a@b.org)")
        assert requests_mock.last_request.headers["User-Agent"] == \
            "MyPipeline/2.0 (mailto:a@b.org)"

    def test_neither_mailto_nor_user_agent_sets_no_package_ua(self, requests_mock):
        # With neither given, the package injects no User-Agent — requests uses
        # its own default, not an openalex-corpus/mailto string.
        requests_mock.get("https://api.openalex.org/works", json={})
        retry_get("https://api.openalex.org/works")
        ua = requests_mock.last_request.headers.get("User-Agent", "")
        assert "openalex-corpus" not in ua
        assert "mailto:" not in ua
