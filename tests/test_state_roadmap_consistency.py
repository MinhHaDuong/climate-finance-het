"""Cross-check the lightweight project state and roadmap."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


pytestmark = pytest.mark.wp_writing

def test_published_data_paper_is_not_listed_as_awaiting_resubmission():
    state = (ROOT / "STATE.md").read_text(encoding="utf-8").lower()
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    data_paper = roadmap.split(
        "## Data paper manuscript next steps", maxsplit=1
    )[1].split("\n## ", maxsplit=1)[0]

    assert "data paper is published" in state
    assert "- [ ] Resubmit on the journal platform" not in data_paper
