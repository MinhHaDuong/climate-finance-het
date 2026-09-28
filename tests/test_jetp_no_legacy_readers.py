"""Retired JETP table names must not reappear in production readers."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RETIRED = (
    'sources.csv', 'manifest.csv', 'plan-projects.csv', 'events.csv',
    'implementation-events.csv', 'event-timing.csv',
    'project-source-links.csv', 'source-claims.csv',
    'idn-portfolio-observations.csv', 'vnm-pilot-manifest.csv',
    'vnm-pilot-observations.csv', 'project-coverage.csv',
    'authority-coverage.csv',
)

pytestmark = pytest.mark.wp_jetp


def retired_names(text):
    """Identify exact retired basenames in one reader's source text."""
    return sorted(name for name in RETIRED if name in text)


def test_guard_fails_on_retired_fixture():
    assert retired_names("reader = 'data/jetp/events.csv'") == ['events.csv']


def test_no_production_jetp_reader_names_retired_tables():
    offenders = {
        str(path.relative_to(ROOT)): retired_names(path.read_text())
        for path in (ROOT / 'scripts/jetp').glob('*.py')
        if retired_names(path.read_text())
    }
    assert offenders == {}
