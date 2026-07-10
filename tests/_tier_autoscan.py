"""Shared logic for the fast-path tier guards (ticket 0216).

Two consumers import from here:

- ``conftest.py`` — the collection-time auto-mark hook (heavy-import detection)
  and the duration-recording hooks (config lookup, durations-file path).
- ``tests/test_fast_path_budget.py`` — the ratchet meta-test and its unit tests.

Keeping the pure functions here (not in ``conftest.py``) makes them importable
and unit-testable without triggering a real pytest collection, and gives the two
consumers a single source of truth.

The module name is underscore-prefixed so pytest never collects it as a test.
"""

import os
import re
from functools import lru_cache

import tomllib

# Heavy dependencies whose import dominates a test's wall time. ``import dcor``
# alone costs ~7s (numba JIT compiled at import, no on-disk cache). A module that
# imports any of these — at top level OR lazily inside a function body — has no
# place on the fast inner loop.
HEAVY_MODULES = ("dcor", "torch", "ot", "sentence_transformers", "matplotlib")

# Match `import <mod>` / `from <mod> import ...` at any indentation (lazy imports
# inside function bodies count). The trailing \b keeps `ot` from matching inside
# `other`, and `torch` from matching inside `torchvision`. A static source scan
# is deliberate — it mirrors the existing convention in
# test_script_hygiene.py::test_no_slow_in_subprocess_files (substring match) and
# never imports the heavy module just to classify it.
_HEAVY_RE = re.compile(
    r"^\s*(?:from|import)\s+(" + "|".join(HEAVY_MODULES) + r")\b",
    re.MULTILINE,
)

# Markers that remove a test from the fast inner loop
# (`-m "not slow and not integration and not adherence"`).
NON_FAST_MARKERS = frozenset({"slow", "integration", "adherence"})

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def heavy_imports_in_source(source: str) -> set[str]:
    """Return the set of heavy modules imported anywhere in ``source``."""
    return set(_HEAVY_RE.findall(source))


@lru_cache(maxsize=None)
def file_has_heavy_import(path: str) -> bool:
    """True if the Python file at ``path`` imports a heavy dependency.

    Cached per path — the auto-mark hook calls this once per collected item, but
    many items share one module file. Missing/unreadable files are treated as
    not-heavy (fail open; the ratchet backstops anything that slips through).
    """
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError:
        return False
    return bool(heavy_imports_in_source(source))


def is_fast_path(markers) -> bool:
    """True if a test carrying ``markers`` runs on the fast inner loop."""
    return not (NON_FAST_MARKERS & set(markers))


def fast_path_violations(records, budget: float) -> list[tuple[str, float]]:
    """Return (nodeid, duration) for each fast-path test exceeding ``budget``.

    ``records`` is a list of ``{"nodeid", "duration", "markers"}`` dicts. A test
    counts as fast-path only when it carries none of the non-fast markers.
    Sorted slowest first so the message leads with the worst offender.
    """
    violations = [
        (r["nodeid"], float(r["duration"]))
        for r in records
        if is_fast_path(r.get("markers", [])) and float(r["duration"]) > budget
    ]
    violations.sort(key=lambda t: t[1], reverse=True)
    return violations


def load_ratchet_config() -> dict:
    """Read the ratchet budget and durations-file path from pyproject.toml.

    The threshold lives in config (``[tool.fast_path_ratchet]``), never hardcoded
    — see the ticket 0216 invariant. Defaults keep the guard functional even if
    the table is absent.
    """
    with open(os.path.join(_REPO, "pyproject.toml"), "rb") as f:
        data = tomllib.load(f)
    cfg = data.get("tool", {}).get("fast_path_ratchet", {})
    return {
        "budget_seconds": float(cfg.get("budget_seconds", 5.0)),
        "durations_file": cfg.get("durations_file", ".test_durations.json"),
    }


def durations_path() -> str:
    """Absolute path to the recorded-durations JSON file."""
    return os.path.join(_REPO, load_ratchet_config()["durations_file"])


def load_durations() -> dict | None:
    """Load the recorded durations, or None if no run has recorded any yet."""
    import json

    path = durations_path()
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
