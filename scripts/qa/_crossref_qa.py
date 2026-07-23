"""Shared Crossref-verification helpers for citation QA scripts.

Neutral module (0250/0254 pattern) so both `qa_citations.py` and
`qa_cocitation_edges.py` reuse the polite Crossref fetch and the Wilson
interval without a script-to-script import (Tier-2 surface rule,
ticket 0286).
"""

import time

import requests
from utils import MAILTO, normalize_doi

HEADERS = {"User-Agent": f"ClimateFinancePipeline/1.0 (mailto:{MAILTO})"}
CROSSREF_DELAY = 0.15  # seconds between API calls (polite rate limiting)


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson score interval for a binomial proportion.

    Returns (proportion, ci_lower, ci_upper). Handles edge cases (n=0, p=0, p=1).
    """
    if n == 0:
        return 0.0, 0.0, 0.0
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    spread = z * (p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5 / denom
    return round(p, 6), round(max(0.0, center - spread), 6), round(min(1.0, center + spread), 6)


def fetch_crossref_refs(doi: str) -> tuple[set[str], str]:
    """Fetch reference DOIs for a source DOI from Crossref.

    Returns (set_of_normalized_ref_dois, status_string).
    """
    url = f"https://api.crossref.org/works/{doi}"
    try:
        time.sleep(CROSSREF_DELAY)
        resp = requests.get(
            url, headers=HEADERS, timeout=30, params={"mailto": MAILTO}
        )
        if resp.status_code == 404:
            return set(), "not_in_crossref"
        if resp.status_code == 429:
            # Rate limited — wait and retry once
            time.sleep(2.0)
            resp = requests.get(
                url, headers=HEADERS, timeout=30, params={"mailto": MAILTO}
            )
        if resp.status_code != 200:
            return set(), f"HTTP {resp.status_code}"
        data = resp.json()["message"]
        refs = data.get("reference", [])
        doi_refs = set()
        for r in refs:
            d = normalize_doi(r.get("DOI", ""))
            if d not in ("", "nan", "none"):
                doi_refs.add(d)
        return doi_refs, "ok"
    except requests.exceptions.Timeout:
        return set(), "timeout"
    except Exception as e:
        return set(), f"error: {e}"
