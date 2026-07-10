"""Adherence guard: the whole repo must stay ruff-clean (ticket 0230).

Lives in the `adherence` tier (`make lint`), never in the fast inner loop —
running ruff inside `check-fast` is what caused the earlier red/green ping-pong.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_ruff_clean():
    """`ruff check .` returns 0 across the repo, including libs/.

    Resolves the binary with ``shutil.which`` rather than a nested ``uv run
    ruff``: pytest already runs inside the project venv under ``make lint``, so
    the lockfile-pinned ruff is on PATH. A nested ``uv run`` re-enters uv from
    inside uv, forcing a per-call sync check that breaks under ``UV_NO_SYNC`` in
    a clean CI/cloud container.
    """
    ruff = shutil.which("ruff")
    assert ruff is not None, (
        "ruff not found on PATH. It must be a declared dev dependency so a cold "
        "`uv sync` installs it — do not let this guard silently skip."
    )
    result = subprocess.run(
        [ruff, "check", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "ruff reported lint violations:\n" + result.stdout + result.stderr
    )
