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

# A basename a living table reuses: data/jetp/comparison/crs/manifest.csv is
# the CRS projection manifest (ticket 0885), not the retired collection
# history. Only its path-anchored form counts, in scripts too.
REUSED = ('manifest.csv',)

pytestmark = pytest.mark.wp_jetp


def retired_names(text, anchored=False):
    """Retired names in one reader's source text.

    A bare basename counts, except for a reused one; ``anchored`` (readers
    outside ``scripts/jetp``) counts only the retired location ``data/jetp/``.
    """
    found = []
    for name in RETIRED:
        needle = f'data/jetp/{name}' if anchored or name in REUSED else name
        if needle in text:
            found.append(name)
    return sorted(found)


def test_guard_fails_on_retired_fixture():
    assert retired_names("reader = 'data/jetp/events.csv'") == ['events.csv']
    assert retired_names("reader = 'data/jetp/manifest.csv'") == ['manifest.csv']
    assert retired_names("path = source_dir / 'manifest.csv'") == []


def test_no_production_jetp_reader_names_retired_tables():
    readers = [*(ROOT / 'scripts/jetp').glob('*.py'),
               ROOT / 'Makefile', ROOT / 'scripts/analysis/jetp_observatory.mk',
               ROOT / 'deliverables/jetp-observatory/app.js']
    offenders = {}
    for path in readers:
        source = path.read_text()
        found = retired_names(source, anchored=path.parent != ROOT / 'scripts/jetp')
        if found:
            offenders[str(path.relative_to(ROOT))] = found
    assert offenders == {}
