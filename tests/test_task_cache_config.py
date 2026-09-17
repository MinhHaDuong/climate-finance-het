"""Task caches must not make routine Make gates fail before tests start."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESOLVER = REPO / "scripts/resolve_task_cache.py"


def _resolve(kind: str, configured: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        f"{kind.upper()}_CACHE_DIR": str(configured),
        "TMPDIR": str(tmp_path),
    }
    return subprocess.run(
        [sys.executable, str(RESOLVER), kind],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )


def test_unwritable_configured_caches_fall_back_to_task_owned_tmp(tmp_path):
    configured = Path("/proc/climate-finance-read-only-cache")
    for kind in ("uv", "ruff"):
        result = _resolve(kind, configured, tmp_path)
        assert result.returncode == 0, result.stderr
        resolved = Path(result.stdout.strip())
        assert resolved != configured
        assert resolved.is_dir()
        assert resolved.is_relative_to(tmp_path)


def test_writable_configured_cache_is_preserved(tmp_path):
    configured = tmp_path / "configured"
    result = _resolve("uv", configured, tmp_path)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == configured


def test_make_exports_resolved_caches_before_tools_start(tmp_path):
    configured = "/proc/climate-finance-read-only-cache"
    env = {
        **os.environ,
        "UV_CACHE_DIR": configured,
        "RUFF_CACHE_DIR": configured,
        "TMPDIR": str(tmp_path),
    }
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "--eval",
            "print-task-caches:\n\t@printf '%s\\n' \"$$UV_CACHE_DIR\" \"$$RUFF_CACHE_DIR\"",
            "print-task-caches",
        ],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    caches = [Path(line) for line in result.stdout.splitlines()]
    assert len(caches) == 2
    assert all(path.is_dir() and path.is_relative_to(tmp_path) for path in caches)
