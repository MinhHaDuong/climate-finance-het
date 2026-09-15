"""Contract for the fast prerequisite check in front of ``make check``.

The full suite includes corpus acceptance and isolated-environment integration
tests. A newly-created worktree commonly has neither DVC-materialized corpus
artifacts nor a usable task cache; explain those conditions before pytest spends
several minutes on failures that cannot answer whether a change regressed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PREFLIGHT = REPO / "scripts" / "qa_full_gate_preflight.py"
pytestmark = pytest.mark.integration


def test_preflight_reports_missing_corpus_and_unwritable_configured_cache(tmp_path):
    """Missing worktree data needs local checkout, never corpus harvesting."""
    data_root = tmp_path / "unmaterialized-data"
    cache_root = tmp_path / "read-only-cache"
    data_root.mkdir()
    cache_root.mkdir()
    cache_root.chmod(0o500)
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(PREFLIGHT),
                "--data-dir",
                str(data_root),
                "--uv-cache-dir",
                str(cache_root),
                "--skip-local-socket-check",
                "--skip-git-check",
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
    finally:
        cache_root.chmod(0o700)

    assert result.returncode == 1
    assert "refined_works.csv" in result.stderr
    assert "make data" in result.stderr
    assert "dvc checkout" in result.stderr
    assert "writable" in result.stderr.lower()
    assert "UV_CACHE_DIR" in result.stderr
    assert "`make corpus`" not in result.stderr
    assert "harvest" not in result.stderr.lower()
