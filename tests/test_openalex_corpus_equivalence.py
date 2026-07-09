"""Migration-safety guard: pipeline_io.retry_get delegates faithfully to the package.

Ticket 0170 extracts the OpenAlex conventions into the ``openalex-corpus``
package and rewires ``pipeline_io.retry_get`` into a thin shim that injects this
repo's ``MAILTO`` and User-Agent and delegates to ``openalex_corpus.retry_get``.
This test freezes the behavioural parity: same status codes, same counter
bookkeeping, same injected ``mailto`` param, same raised exceptions — asserting
``pipeline_io.retry_get(...) == openalex_corpus.retry_get(..., mailto=MAILTO)``
across every retry path. It is the safety net for that shim; if a future edit
diverges the two, this fails loudly. ``importorskip`` keeps it from breaking a
suite run in an env where the package is not installed.
"""

import pytest

pipeline_io = pytest.importorskip("pipeline_io")
_pkg = pytest.importorskip("openalex_corpus")

MAILTO = pipeline_io.MAILTO


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr("pipeline_io.time.sleep", lambda *_: None)
    monkeypatch.setattr("openalex_corpus.crawl.time.sleep", lambda *_: None)


def _run(fn, responses, requests_mock, **kwargs):
    """Drive one retry_get against a mocked endpoint; return an outcome tuple."""
    url = "https://api.openalex.org/w"
    requests_mock.get(url, responses)
    counters: dict[str, int] = {}
    try:
        resp = fn(url, counters=counters, **kwargs)
        status = resp.status_code
        exc = None
    except Exception as e:
        status = None
        exc = type(e).__name__
    mailto = requests_mock.last_request.qs.get("mailto")
    return status, counters, mailto, exc


SCENARIOS = {
    "success": [{"status_code": 200, "json": {"x": 1}}],
    "429_then_ok": [
        {"status_code": 429, "headers": {"Retry-After": "0"}},
        {"status_code": 200, "json": {}},
    ],
    "503_then_ok": [
        {"status_code": 503},
        {"status_code": 200, "json": {}},
    ],
    "429_exhaust": [{"status_code": 429, "headers": {"Retry-After": "0"}}] * 5,
    "404_raises": [{"status_code": 404}],
    "500_exhaust": [{"status_code": 500}] * 2,
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_retry_get_port_is_equivalent(name, requests_mock):
    responses = SCENARIOS[name]
    orig = _run(pipeline_io.retry_get, responses, requests_mock, max_retries=5
                if "exhaust" not in name or name == "429_exhaust" else 2)
    pkg = _run(_pkg.retry_get, responses, requests_mock,
               max_retries=5 if "exhaust" not in name or name == "429_exhaust" else 2,
               mailto=MAILTO)
    assert orig == pkg, f"{name}: orig={orig} pkg={pkg}"
