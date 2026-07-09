"""Migration-safety guard: openalex_corpus.retry_get == pipeline_io.retry_get.

Ticket 0170 extracts the OpenAlex conventions into the standalone
``openalex-corpus`` package. Before the host modules are rewired to re-export
from it (the deferred shim slice), this test freezes the fact that the package
port is behaviourally identical to the original — same status codes, same
counter bookkeeping, same injected ``mailto`` param, same raised exceptions —
when the package is called with ``mailto=MAILTO``.

Once the shim lands, ``pipeline_io.retry_get`` IS the package function and the
comparison becomes trivially true; the guard remains harmless. Until the
package is a wired dependency, it is reached via an explicit path insert (the
package is not yet installed into the host env); the test skips if either side
is unimportable rather than failing the suite.
"""

import os
import sys

import pytest

_PKG_SRC = os.path.join(
    os.path.dirname(__file__), "..", "libs", "openalex-corpus", "src"
)
if _PKG_SRC not in sys.path:
    sys.path.insert(0, _PKG_SRC)

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
