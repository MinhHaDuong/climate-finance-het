"""The 0875 split keeps documentary bases and removes count-slot identities."""

import csv
import hashlib
from collections import Counter
from pathlib import Path

import pytest
from jetp._ledger_headers import load_schema, read_table
from jetp.build_ledger import build as validate_ledger
from jetp.build_reconciliation import build, disposition

LEDGER = Path(__file__).resolve().parents[1] / 'data/jetp'


pytestmark = pytest.mark.wp_jetp

def rows(name):
    schema = load_schema()
    records, errors = read_table(LEDGER, name, schema)
    assert not errors
    return [dict(zip(schema.header(name), row)) for row in records]


def test_ten_cases_cover_the_five_dispositions():
    cases = [
        ('official_register', 'zaf-register-actip001', 'agreement'),
        ('official_presentation', 'idn-pipe-hydro-quota-sulawesi', 'project'),
        ('official_count_slot', 'vnm-project-initial-undisclosed-04', 'perimeter'),
        ('official_count_slot', 'vnm-project-screened-undisclosed-01', 'perimeter'),
        ('official_plan', 'sen-project-annex-01', 'project'),
        ('official_programme', 'zaf-eepbip', 'line'),
        ('official_report', 'idn-grant-wolcot', 'agreement'),
        ('official_report', 'idn-fin-isle-1', 'agreement'),
        ('secondary_news', 'idn-pipe-cirebon-1-retirement', 'asset'),
        ('official_project_page', 'vnm-project-bac-ai-pumped-hydro', 'project'),
    ]
    legacy = {row['project_id']: row for row in csv.DictReader(
        (LEDGER / 'migration/0875-projects-legacy.csv').open())}
    report = {row['old_id']: row for row in csv.DictReader(
        (LEDGER / 'migration/0875-dispositions.csv').open())}
    for status, old_id, expected in cases:
        old = legacy[old_id]
        assert old['verification_status'] == status
        assert disposition(old) == expected
        assert report[old_id]['disposition'] == expected
        if old_id == 'idn-pipe-hydro-quota-sulawesi':
            assert not report[old_id]['new_id']
            assert report[old_id]['basis_method'] == 'no_precise_line'
        else:
            assert report[old_id]['new_id']
        if expected != 'perimeter' and old_id != 'idn-pipe-hydro-quota-sulawesi':
            assert report[old_id]['line_id']


def test_committed_split_is_replayable_and_every_identity_has_a_line():
    generated, report = build(LEDGER)
    assert len(report) == 404
    route_path = LEDGER / 'routes.csv'
    assert hashlib.sha256(route_path.read_bytes()).hexdigest() == (
        '879905b883f5071536d90530f6ec7ab9f008ec1694687ceee766f3e3fe7fd371')
    assert len(rows('routes')) == 1907
    schema = load_schema()
    additions_after_0875 = {'projects': 4, 'agreements': 9, 'line_referents': 14}
    for table in ('projects', 'assets', 'agreements', 'line_referents',
                  'relations', 'parties', 'party_names', 'perimeters'):
        committed = rows(table)
        assert [{key: None if record.get(key) is None else str(record[key])
                 for key in schema.header(table)}
                for record in generated[table]] == committed[:len(generated[table])], table
        assert len(committed) - len(generated[table]) == additions_after_0875.get(table, 0), table
    identities = {(kind, row[kind + '_id']) for kind in ('project', 'asset', 'agreement')
                  for row in generated[kind + 's']}
    accepted = {(row['referent_kind'], row['referent_id'])
                for row in generated['line_referents'] if row['status'] == 'accepted'}
    assert identities <= accepted
    assert not validate_ledger(LEDGER)


def test_register_allocations_slots_and_component_links():
    disposition_rows = list(csv.DictReader((LEDGER / 'migration/0875-dispositions.csv').open()))
    assert len(disposition_rows) == 404
    legacy_ids = {row['project_id'] for row in csv.DictReader(
        (LEDGER / 'migration/0875-projects-legacy.csv').open())}
    assert {row['old_id'] for row in disposition_rows} == legacy_ids
    route_ids = {row['old_id'] for row in rows('routes')}
    assert not legacy_ids & route_ids
    for row in disposition_rows:
        if row['disposition'] != 'perimeter' and row['basis_method'] in {
                'no_precise_line', 'multiple_legacy_lines'}:
            assert not row['new_id']
            if row['basis_method'] == 'no_precise_line':
                assert not row['line_id']
            else:
                assert len(row['line_id'].split(';')) == 2
        else:
            assert row['new_id']
    counts = Counter(row['disposition'] for row in disposition_rows)
    assert counts['agreement'] == 310  # 257 ZAF register plus IDN grants/finance.
    assert counts['perimeter'] == 21
    for old_id in ('idn-grant-jetp-etp', 'idn-grant-ietf'):
        pending = next(row for row in disposition_rows if row['old_id'] == old_id)
        assert pending['basis_method'] == 'multiple_legacy_lines'
        assert not pending['new_id']
        assert not any(row['agreement_id'] == 'agreement-' + old_id
                       for row in rows('agreements'))
    monitor = next(row for row in disposition_rows
                   if row['old_id'] == 'idn-monitor-cihaur-talaga-micro-hydro')
    assert len(monitor['line_id'].split(';')) == 2
    assert {row['new_id'] for row in disposition_rows
            if row['disposition'] == 'perimeter'} == {'vnm-jetp-portfolio-2025'}
    assert sum(row['old_id'].startswith('zaf-register-') and row['line_id'] != ''
               for row in disposition_rows) == 257
    old_slots = {row['old_id'] for row in disposition_rows
                 if row['disposition'] == 'perimeter'}
    assert not old_slots & {r['project_id'] for r in rows('projects')}
    assert len(rows('projects')) == 60 + 4  # 1120 resolved MURP, plus 0970 adjudications.
    assert sum(r['relation'] == 'component_of' and r['relation_id'].startswith('0875.')
               for r in rows('relations')) == 11
    assert any(r['asset_id'] == 'asset-idn-pelabuhan-ratu' for r in rows('assets'))
    tier2 = [r for r in rows('relations') if r['relation_id'].startswith('0875.tier2.')]
    assert len(tier2) == 10
    assert {(r['relation'], r['status'], r['method'], r['method_version'])
            for r in tier2} == {('same_as', 'candidate', 'normalized_label', '1')}
    assert sum(r['role'] == 'channel' and r['relation'] == 'party_in'
               for r in rows('relations') if r['relation_id'].startswith('0875.')) == 10
    for relation in rows('relations'):
        if not relation['relation_id'].startswith('0875.'):
            continue
        if relation['relation'] == 'party_in':
            assert (relation['from_kind'], relation['to_kind']) == ('party', 'agreement')
        if relation['relation'] == 'role_in':
            assert (relation['from_kind'], relation['to_kind']) == ('party', 'line')
