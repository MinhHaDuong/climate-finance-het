"""Keep the archived 0761 MVP baseline byte-identical to its inspection record."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.wp_jetp


def test_frozen_mvp_baseline_matches_recorded_inspection():
    baseline = (ROOT / 'data/jetp/releases/mvp-baseline-0761.zip').read_bytes()
    inspection = json.loads((ROOT / 'docs/jetp-mvp-baseline-0761.json').read_text())
    assert len(baseline) == inspection['archive_bytes']
    assert hashlib.sha256(baseline).hexdigest() == inspection['archive_sha256']
