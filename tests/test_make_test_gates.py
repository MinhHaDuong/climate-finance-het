"""Contract tests for the Make test-gate wiring (ticket 0214).

The test tiers are gated by pytest `-m` marker expressions in the Makefile:

- `check-fast` — the inner loop: pure-Python logic only. Must deselect
  `slow`, `integration`, AND `adherence` (lint belongs in `make lint`).
- `lint` — the adherence tier (ruff / mypy / hygiene / contracts).
- `check` — everything (no `-m` filter).

These tests source-inspect the Makefile (no subprocess) so a future edit that
silently drops a tier from the fast loop, or removes `make lint`, turns red.
"""

import os
import re

import pytest

pytestmark = pytest.mark.adherence

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAKEFILE = os.path.join(REPO, "Makefile")


def _target_body(name: str) -> str:
    """Return the recipe lines of Make target `name` (until the next target)."""
    with open(MAKEFILE) as f:
        source = f.read()
    # Match "name:" at line start, then capture indented/continued recipe lines.
    m = re.search(
        rf"^{re.escape(name)}:.*?(?=\n\S)", source, re.MULTILINE | re.DOTALL
    )
    return m.group(0) if m else ""


class TestCheckFastDeselectsAllNonUnitTiers:
    """check-fast runs pure-logic unit tests only."""

    def test_check_fast_excludes_adherence(self):
        body = _target_body("check-fast")
        assert body, "check-fast target not found in Makefile"
        assert "not adherence" in body, (
            "check-fast must deselect the adherence (lint) tier so a cold "
            "mypy cache never taxes the inner loop — run lint via `make lint`"
        )

    def test_check_fast_excludes_slow_and_integration(self):
        body = _target_body("check-fast")
        assert "not slow" in body and "not integration" in body, (
            "check-fast must still deselect slow and integration"
        )


class TestLintTargetRunsAdherenceTier:
    """`make lint` is the adherence gate, run alongside tests not inside them."""

    def test_lint_target_exists(self):
        assert _target_body("lint"), "no `lint:` target in Makefile"

    def test_lint_selects_adherence(self):
        body = _target_body("lint")
        assert re.search(r"-m\s+adherence\b", body), (
            "`make lint` must select the adherence tier (`-m adherence`)"
        )
