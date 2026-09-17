#!/usr/bin/env python3
"""Select a writable cache directory before Make launches uv or Ruff."""

import os
import sys
import tempfile
from pathlib import Path

ENVIRONMENTS = {
    "ruff": "RUFF_CACHE_DIR",
    "uv": "UV_CACHE_DIR",
}


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path):
            pass
    except OSError:
        return False
    return True


def resolve(kind: str) -> Path:
    """Keep a usable configured cache, otherwise allocate a task-owned fallback."""
    variable = ENVIRONMENTS[kind]
    configured = os.environ.get(variable)
    if configured:
        candidate = Path(configured).expanduser()
        if _is_writable(candidate):
            return candidate

    cache_home = Path(
        os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
    ).expanduser()
    default = cache_home / kind
    if not configured and _is_writable(default):
        return default

    fallback = (
        Path(os.environ.get("TMPDIR", "/tmp"))
        / f"climate-finance-het-{os.getuid()}"
        / kind
    )
    if not _is_writable(fallback):
        raise OSError(f"no writable {kind} cache: configured={configured!r}")
    return fallback


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ENVIRONMENTS:
        print("usage: resolve-task-cache.py {uv|ruff}", file=sys.stderr)
        return 2
    try:
        selected = resolve(sys.argv[1])
    except OSError as error:
        print(error, file=sys.stderr)
        return 1
    print(selected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
