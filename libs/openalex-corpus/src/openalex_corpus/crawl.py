"""OpenAlex crawl convention — polite, resilient HTTP GET.

``retry_get`` is the shared HTTP fetcher: bounded exponential backoff with
jitter, 429/5xx retry, graceful 429-exhaustion, and optional counter tracking.

Deployment config is injected, never shipped: the caller supplies its own
``mailto`` (for the polite ``mailto`` query param and User-Agent) and, if it
wants a branded agent string, ``user_agent``. The package hardcodes no email,
no API key, no product name.
"""

import logging
import random
import time
from typing import Any
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]

_log = logging.getLogger("openalex_corpus.crawl")

RETRY_MAX_RETRIES = 5    # enrichment fetchers (heavy, fewer URLs)


def retry_get(url: str, params: dict[str, Any] | None = None,
              headers: dict[str, str] | None = None, delay: float = 0.2,
              max_retries: int = RETRY_MAX_RETRIES,
              timeout: float = 60, counters: dict[str, int] | None = None,
              backoff_base: float = 2.0, jitter_max: float = 1.0,
              mailto: str | None = None,
              user_agent: str | None = None) -> requests.Response:
    """HTTP GET with bounded exponential backoff+jitter and optional counter tracking.

    Parameters
    ----------
    url : str
        Request URL.
    params : dict, optional
        Query parameters.
    headers : dict, optional
        HTTP headers.
    delay : float
        Base polite delay before each attempt (seconds).
    max_retries : int
        Maximum retry attempts for 429/5xx/timeout.
    timeout : float
        Per-request timeout in seconds.
    counters : dict, optional
        Mutable dict updated with keys ``retries``, ``rate_limited``,
        ``server_errors``, ``client_errors``.
    backoff_base : float
        Base for exponential backoff (seconds).
    jitter_max : float
        Maximum random jitter added to each backoff (seconds).
    mailto : str, optional
        Contact email for OpenAlex's polite pool. When given and absent from
        ``params``/``url``, it is added as the ``mailto`` query param and used
        in the default User-Agent. Injected by the caller — never hardcoded.
    user_agent : str, optional
        Explicit User-Agent. Overrides the ``mailto``-derived default.

    Returns
    -------
    requests.Response on success.

    Raises
    ------
    RuntimeError after all retries are exhausted.

    """
    if params is None:
        params = {}
    if mailto and "mailto" not in params and "mailto" not in url:
        params["mailto"] = mailto
    if headers is None:
        headers = {}
    if user_agent is not None:
        headers.setdefault("User-Agent", user_agent)
    elif mailto:
        headers.setdefault("User-Agent", f"openalex-corpus/1.0 (mailto:{mailto})")
    if counters is None:
        counters = {}

    host = urlparse(url).hostname or url

    last_exc = None
    for attempt in range(max_retries):
        try:
            time.sleep(delay)
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout as exc:
            last_exc = exc
            counters["retries"] = counters.get("retries", 0) + 1
            backoff = min(backoff_base ** attempt + random.uniform(0, jitter_max), 60)
            _log.warning("Timeout on attempt %d/%d, retrying in %.1fs...",
                         attempt + 1, max_retries, backoff)
            time.sleep(backoff)
            continue
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            counters["retries"] = counters.get("retries", 0) + 1
            backoff = min(backoff_base ** attempt + random.uniform(0, jitter_max), 60)
            time.sleep(backoff)
            continue

        if resp.status_code == 429:
            counters["rate_limited"] = counters.get("rate_limited", 0) + 1
            counters["retries"] = counters.get("retries", 0) + 1
            if attempt == max_retries - 1:
                # Return the 429 response instead of raising — lets callers
                # inspect budget headers and degrade gracefully.
                _log.warning("Rate limited (429) by %s after %d attempts, returning response.",
                             host, max_retries)
                return resp
            retry_after = min(
                int(resp.headers.get("Retry-After", backoff_base ** (attempt + 1))), 120
            )
            jitter = random.uniform(0, min(jitter_max * 2, 2))
            wait = retry_after + jitter
            _log.warning("Rate limited (429) by %s, waiting %.1fs...", host, wait)
            time.sleep(wait)
            continue
        if resp.status_code >= 500:
            counters["server_errors"] = counters.get("server_errors", 0) + 1
            counters["retries"] = counters.get("retries", 0) + 1
            backoff = min(backoff_base ** attempt + random.uniform(0, jitter_max), 60)
            _log.warning("Server error %d on attempt %d/%d, retrying in %.1fs...",
                         resp.status_code, attempt + 1, max_retries, backoff)
            time.sleep(backoff)
            last_exc = resp.status_code
            continue
        if resp.status_code >= 400:
            counters["client_errors"] = counters.get("client_errors", 0) + 1
            resp.raise_for_status()
        return resp

    raise RuntimeError(
        f"Failed after {max_retries} attempts: {url} "
        f"(last error: {last_exc})"
    )
