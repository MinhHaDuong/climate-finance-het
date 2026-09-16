"""Fail a LaTeX render when latexmk left unresolved references behind.

``latexmk`` can return success while the PDF still contains a missing citation
or cross-reference.  The JETP papers are plain LaTeX, so their render guard
must read the LaTeX log rather than reuse Quarto's placeholder resolver.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

UNRESOLVED_PATTERNS = (
    re.compile(r"Reference .+ undefined", re.IGNORECASE),
    re.compile(r"Citation .+ undefined", re.IGNORECASE),
    re.compile(r"Undefined control sequence", re.IGNORECASE),
)


def assert_clean_log(path: Path) -> None:
    """Raise when *path* records an unresolved LaTeX construct."""
    text = path.read_text(encoding="utf-8", errors="replace")
    offenders = [line for line in text.splitlines() if any(p.search(line) for p in UNRESOLVED_PATTERNS)]
    if offenders:
        raise ValueError("unresolved LaTeX reference in " + str(path) + ": " + " | ".join(offenders))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    try:
        assert_clean_log(args.log)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
