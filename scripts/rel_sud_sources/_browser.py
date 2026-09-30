"""A ``get(url, params, delay)`` that goes through headless Chromium (ticket 1790).

For sources whose plain-HTTP route is stopped by a JavaScript challenge that a
real browser passes: AJOL's AWS WAF answers HTTP 202 with
``x-amzn-waf-action: challenge`` and an empty body; loading the same URL in a
browser page runs the challenge script, which sets the ``aws-waf-token``
cookie, and the requests of the same browser context then go through.
Author's rule, 2026-09-30: "If you can't Playwright it, it's dead."

Limits this getter keeps: it identifies with the lane's User-Agent (no browser
disguise), waits ``delay`` seconds between requests at least, passes a plain
JavaScript challenge at most once per request and never touches a CAPTCHA
(a page that still answers the challenge after the browser has run it is
returned as is, and the adapter ends the query). robots.txt is the adapter's
business: only paths it allows are requested.

Requests use the context's HTTP client (``context.request``), which shares the
browser's cookies; the page is used only to run a challenge. Playwright is
imported lazily, so the adapters and their tests do not need it.
"""

import time
import types
from urllib.parse import urlencode

from pipeline_io import MAILTO
from utils import get_logger

log = get_logger("rel_sud_sources")

USER_AGENT = f"ClimateFinancePipeline/1.0 (mailto:{MAILTO})"
SETTLE_MS = 15_000  # time given to a challenge script in the page


def challenged(status, headers):
    return status == 202 and headers.get("x-amzn-waf-action") == "challenge"


class BrowserGet:
    """Callable getter over one headless Chromium context, started on first use."""

    def __init__(self, user_agent=USER_AGENT, timeout_ms=60_000):
        self.user_agent, self.timeout_ms = user_agent, timeout_ms
        self._pw = self._browser = self._ctx = self._page = None
        self._last = 0.0
        self.challenges = 0

    def _start(self):
        from playwright.sync_api import sync_playwright  # lazy: optional dependency
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._ctx = self._browser.new_context(user_agent=self.user_agent)
        self._page = self._ctx.new_page()

    def _wait(self, delay):
        gap = delay - (time.monotonic() - self._last)
        if gap > 0:
            time.sleep(gap)
        self._last = time.monotonic()

    def _request(self, url):
        r = self._ctx.request.get(url, timeout=self.timeout_ms)
        return r.status, dict(r.headers), r.body()

    def __call__(self, url, params=None, delay=0):
        if self._ctx is None:
            self._start()
        full = f"{url}?{urlencode(params)}" if params else url
        self._wait(delay)
        status, headers, body = self._request(full)
        if challenged(status, headers):
            self.challenges += 1
            log.info("JavaScript challenge on %s: loading it in the page", full)
            self._page.goto(full, timeout=self.timeout_ms)
            self._page.wait_for_timeout(SETTLE_MS)
            self._wait(delay)
            status, headers, body = self._request(full)
        return types.SimpleNamespace(status_code=status, headers=headers, content=body,
                                     text=body.decode("utf-8", errors="replace"))

    def close(self):
        if self._browser is not None:
            self._browser.close()
            self._pw.stop()
            self._browser = self._pw = self._ctx = self._page = None
