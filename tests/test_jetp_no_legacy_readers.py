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
    readers = [*(ROOT / 'scripts/jetp').glob('*.py'),
               ROOT / 'Makefile', ROOT / 'scripts/analysis/jetp_observatory.mk',
               ROOT / 'deliverables/jetp-observatory/app.js']
    offenders = {}
    for path in readers:
        source = path.read_text()
        found = (retired_names(source) if path.parent == ROOT / 'scripts/jetp'
                 else sorted(name for name in RETIRED if f'data/jetp/{name}' in source))
        if found:
            offenders[str(path.relative_to(ROOT))] = found
    assert offenders == {}
