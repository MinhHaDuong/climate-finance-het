"""Every row of the three JETP migration registers has an owner or a disposition.

Ticket 1590. The registers are records, not build outputs, so the guard reads
the committed files: the pending register names an owner on every row it
keeps, the dispositions register accounts for every row the three registers
held on 2026-09-29 (145 distinct keys), and a row it calls resolved names a
timing that exists.
"""
import csv
import glob
from pathlib import Path

import pytest

pytestmark = pytest.mark.wp_jetp

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / 'data' / 'jetp' / 'migration'


def _rows(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def test_every_pending_row_names_its_disposition_and_owner():
    rows = _rows(MIG / '0876-pending.csv')
    assert rows, 'the pending register is not empty'
    for row in rows:
        assert row.get('disposition') in {'pending', 'terminal'}, row['legacy_event_id']
        assert row.get('owner'), row['legacy_event_id']
        assert 'unmapped_date_role' not in row['reason'], (
            f"{row['legacy_event_id']}: the reason still names the legacy role, not what the page says")


def test_dispositions_register_accounts_for_every_register_row():
    register = _rows(MIG / '1590-register-dispositions.csv')
    keys = {(r['register'], r['row_key']) for r in register}
    assert len({r['row_key'] for r in register}) == 145
    pending = {('0876-pending', r['legacy_event_id']) for r in _rows(MIG / '0876-pending.csv')}
    assert pending <= keys
    citations = {('1160-citation-decisions', r['legacy_event_id'])
                 for r in _rows(MIG / '1160-citation-decisions.csv') if r['decision'] != 'accepted'}
    assert citations <= keys
    coverage = {('0884-coverage-dispositions', r['old_id']) for r in _rows(MIG / '0884-coverage-dispositions.csv')}
    assert coverage <= keys
    for row in register:
        assert row['decided_by'] and row['decided_at'] and row['disposition'], row
        if row['disposition'].startswith('pending'):
            assert row['owner'], row['row_key']
        if row['disposition'] == 'rejected' and row['register'] == '1160-citation-decisions':
            decisions = {r['legacy_event_id']: r['decision'] for r in _rows(MIG / '1160-citation-decisions.csv')}
            assert decisions[row['row_key']] == 'rejected', row['row_key']


def test_a_resolved_row_names_a_timing_that_exists():
    timing_ids = set()
    for path in glob.glob(str(ROOT / 'data' / 'jetp' / 'timings.d' / '*.csv')):
        timing_ids.update(r['timing_id'] for r in _rows(path))
    resolved = [r for r in _rows(MIG / '1590-register-dispositions.csv') if r['disposition'] == 'resolved']
    assert len(resolved) == 30
    for row in resolved:
        named = [token for token in row['note'].replace(';', ' ').split() if token.startswith('timing-')]
        assert named and all(t in timing_ids for t in named), row['row_key']
