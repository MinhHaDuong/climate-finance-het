"""Shared test helpers for the divergence pipeline tests.

Also wires the fast-path tier guards (ticket 0216):

- ``pytest_collection_modifyitems`` auto-marks any test whose module statically
  imports a heavy dependency (dcor/torch/ot/sentence_transformers/matplotlib)
  ``slow`` — deterministically keeping the ~7s dcor import tax off the fast loop.
- ``pytest_runtest_logreport`` + ``pytest_sessionfinish`` record per-test
  durations (with tier markers) to a gitignored JSON file, which the ratchet in
  ``tests/test_fast_path_budget.py`` reads on the next run.
"""

import json
import os
import subprocess
import sys

import pytest
from _source_roots import source_root_env
from _tier_autoscan import (
    NON_FAST_MARKERS,
    durations_path,
    file_has_heavy_import,
)

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "smoke")
GOLDEN_DIR = os.path.join(FIXTURES_DIR, "golden")

# Flat imports (from utils import …) resolve via the `scripts` source root
# declared in [tool.pytest.ini_options] pythonpath (ticket 0253) — the old
# path-injection hack is retired. SCRIPTS_DIR remains for run_compute() below,
# which builds an absolute path to a script it launches as a subprocess.

# Class-level guard (ticket 0263): put the source roots on this process's own
# PYTHONPATH so every subprocess a test spawns inherits them, exactly as under
# make's export. Retiring the stale openalex-corpus wheel (0253) revealed 38
# tests across 9 files whose subprocess env forgot source_root_env(); this one
# line closes the class instead of patching each call site — per-call
# source_root_env() remains correct and takes precedence where used.
os.environ["PYTHONPATH"] = source_root_env()["PYTHONPATH"]


# ---------------------------------------------------------------------------
# Fast-path tier guards (ticket 0216)
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config, items):
    """Auto-mark heavy-import test modules ``slow``.

    Runs before pytest's built-in ``-m`` deselection (user conftest hooks fire
    before internal plugin hooks), so an auto-added ``slow`` mark correctly
    removes the test from ``make check-fast``. Idempotent: never touches a test
    that already carries slow / integration / adherence.
    """
    for item in items:
        if any(item.get_closest_marker(m) for m in NON_FAST_MARKERS):
            continue
        path = str(getattr(item, "path", None) or item.fspath)
        if file_has_heavy_import(path):
            item.add_marker(pytest.mark.slow)


# nodeid -> {"duration": float (summed over phases), "markers": list[str]}
_RECORDED_DURATIONS: dict[str, dict] = {}


def pytest_runtest_logreport(report):
    """Accumulate per-test wall time and tier markers.

    ``report.keywords`` carries the marker names — including any auto-added
    ``slow`` — so the ratchet sees the effective tier, not the source-declared
    one. Durations are summed across setup/call/teardown for an honest per-test
    total.
    """
    entry = _RECORDED_DURATIONS.setdefault(
        report.nodeid, {"duration": 0.0, "markers": []}
    )
    entry["duration"] += float(getattr(report, "duration", 0.0) or 0.0)
    marks = [m for m in NON_FAST_MARKERS if report.keywords.get(m)]
    if marks:
        entry["markers"] = sorted(set(entry["markers"]) | set(marks))


def pytest_sessionfinish(session, exitstatus):
    """Write recorded durations, but only for an opt-in *serial* run.

    ``report.duration`` is wall time; under ``-n N`` xdist oversubscription it
    inflates 3-5x (CPU contention), which would make a per-test budget fire on
    scheduling noise rather than true cost. So recording is gated two ways:

    - ``RECORD_TEST_DURATIONS`` must be set (avoids a stray single-file serial
      run clobbering the file with a partial record), and
    - the run must be serial (no active xdist workers).

    ``make test-durations`` sets both. The ratchet then reflects the last such
    run; a fresh checkout has no file and the guard skips (cold-start).
    """
    if not os.environ.get("RECORD_TEST_DURATIONS"):
        return
    if hasattr(session.config, "workerinput"):
        return  # xdist worker
    if session.config.getoption("numprocesses", None):
        return  # distributed controller — durations would be contention-inflated
    if not _RECORDED_DURATIONS:
        return
    records = [
        {"nodeid": nodeid, "duration": entry["duration"], "markers": entry["markers"]}
        for nodeid, entry in sorted(_RECORDED_DURATIONS.items())
    ]
    try:
        with open(durations_path(), "w", encoding="utf-8") as f:
            json.dump({"records": records}, f, indent=1)
    except OSError:
        pass  # never fail a run over a bookkeeping write.


def smoke_env():
    """Environment that redirects pipeline_loaders to fixture data.

    Sets the source roots on PYTHONPATH (ticket 0253) so the subprocess launched
    by run_compute() resolves flat imports (from utils import …, import
    openalex_corpus) without an ambient PYTHONPATH and without the retired wheel —
    the child inherits environment, not the parent's sys.path.
    """
    return source_root_env({
        **os.environ,
        "CLIMATE_FINANCE_DATA": FIXTURES_DIR,
        "PYTHONHASHSEED": "0",
        "SOURCE_DATE_EPOCH": "0",
    })


def run_compute(method, output_path, timeout=300, input_paths=None):
    """Run compute_divergence.py --method M --output P.

    input_paths : list[str] | None
        When provided, forwarded as ``--input <path...>`` so the method reads
        the given fixture files instead of the smoke corpus. Default (None)
        leaves the smoke-env corpus in place — existing call sites unchanged.
    """
    cmd = [
        sys.executable,
        os.path.join(SCRIPTS_DIR, "compute_divergence.py"),
        "--method", method,
        "--output", str(output_path),
    ]
    if input_paths:
        cmd += ["--input", *[str(p) for p in input_paths]]
    return subprocess.run(
        cmd,
        env=smoke_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
