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


def test_hygiene_tool_probes_use_shutil_which():
    """The adherence hygiene tests must resolve ruff/mypy via ``shutil.which``.

    Ticket 0236: ``tests/test_script_hygiene.py`` used to gate its ruff and mypy
    tests on module-level ``subprocess.run(["uv", "run", <tool>, "--version"])``
    probes evaluated at collection time. A nested ``uv run`` re-enters uv from
    inside the venv pytest already runs in, spawning a per-call sync check that
    misbehaves under ``UV_NO_SYNC`` in a clean CI/cloud container. Resolve the
    binary with ``shutil.which`` instead, matching ``test_ruff_clean`` above.

    Checked from this sibling module (not in-file) so the test's own search
    tokens cannot self-match the source it inspects.
    """
    hygiene_src = (REPO_ROOT / "tests" / "test_script_hygiene.py").read_text()
    normalized = "".join(hygiene_src.split())
    assert '"uv","run"' not in normalized, (
        "nested `uv run` tool invocation remains in test_script_hygiene.py; "
        "resolve ruff/mypy binaries via shutil.which instead (ticket 0236)"
    )
    assert 'shutil.which("ruff")' in hygiene_src, (
        "ruff availability must resolve via shutil.which (ticket 0236)"
    )
    assert 'shutil.which("mypy")' in hygiene_src, (
        "mypy availability must resolve via shutil.which (ticket 0236)"
    )
