"""Contract tests for the Make test-gate wiring (ticket 0214).

The test tiers are gated by pytest `-m` marker expressions in the Makefile:

- `check-fast` — the inner loop: pure-Python logic only. Must deselect
  `slow`, `integration`, AND `adherence` (lint belongs in `make lint`).
- `lint` — the adherence tier (ruff / mypy / hygiene / contracts).
- `check` — everything (no `-m` filter).
- `check-library` / `check-corpus-wp` / `check-finance` / `check-jetp` /
  `check-writing` / `check-shared` — all tiers for their local WP marker.

These tests source-inspect the Makefile (no subprocess) so a future edit that
silently drops a tier from the fast loop, or removes `make lint`, turns red.
"""

import os
import re

import pytest

pytestmark = [
    pytest.mark.wp_shared,
    pytest.mark.adherence,
]

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


@pytest.mark.parametrize(
    ("target", "marker"),
    [
        ("check-library", "wp_library"),
        ("check-corpus-wp", "wp_corpus"),
        ("check-finance", "wp_finance"),
        ("check-jetp", "wp_jetp"),
        ("check-writing", "wp_writing"),
        ("check-shared", "wp_shared"),
    ],
)
def test_wp_gate_selects_local_pytest_marker(target, marker):
    body = _target_body(target)
    assert re.search(rf"-m\s+{marker}\b", body), (
        f"{target} must select its local pytest mark with -m {marker}"
    )
    assert "pytest tests/" in body or "pytest tests/ libs/openalex-corpus/tests/" in body


def test_corpus_wp_gate_includes_package_tests():
    assert "libs/openalex-corpus/tests/" in _target_body("check-corpus-wp")
