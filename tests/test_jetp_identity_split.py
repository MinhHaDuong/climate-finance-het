"""The 0875 split keeps documentary bases and removes count-slot identities."""

import csv
from collections import Counter
from pathlib import Path

from jetp._ledger_headers import load_schema, read_table
from jetp.build_ledger import build as validate_ledger
from jetp.build_reconciliation import build, disposition

LEDGER = Path(__file__).resolve().parents[1] / 'data/jetp'


def rows(name):
    schema = load_schema()
    records, errors = read_table(LEDGER, name, schema)
    assert not errors
    return [dict(zip(schema.header(name), row)) for row in records]


def test_ten_cases_cover_the_five_dispositions():
    cases = [
        ('official_register', 'zaf-register-actip001', 'agreement'),
        ('official_register', 'zaf-register-fp001-1', 'agreement'),
        ('official_count_slot', 'vnm-project-initial-undisclosed-04', 'perimeter'),
        ('official_count_slot', 'vnm-project-screened-undisclosed-01', 'perimeter'),
        ('official_plan', 'sen-project-annex-01', 'project'),
        ('official_programme', 'zaf-programme-a', 'line'),
        ('official_report', 'idn-grant-wolcot', 'agreement'),
        ('official_report', 'idn-fin-isle-1', 'agreement'),
        ('secondary_news', 'idn-pipe-cirebon-1-retirement', 'asset'),
        ('official_project_page', 'vnm-project-bac-ai-pumped-hydro', 'project'),
    ]
    for status, old_id, expected in cases:
        assert disposition({'verification_status': status, 'project_id': old_id}) == expected


def test_committed_split_is_replayable_and_every_identity_has_a_line():
    generated, report = build(LEDGER)
    assert len(report) == 404
    assert len(rows('routes')) == 1907  # M1a row keys only; no legacy project mappings.
    schema = load_schema()
    for table in ('projects', 'assets', 'agreements', 'line_referents',
                  'relations', 'parties', 'party_names', 'perimeters'):
        assert [{key: None if record.get(key) is None else str(record[key])
                 for key in schema.header(table)}
                for record in generated[table]] == rows(table), table
    identities = {(kind, row[kind + '_id']) for kind in ('project', 'asset', 'agreement')
                  for row in generated[kind + 's']}
    accepted = {(row['referent_kind'], row['referent_id'])
                for row in generated['line_referents'] if row['status'] == 'accepted'}
    assert identities <= accepted
    assert not validate_ledger(LEDGER)


def test_register_allocations_slots_and_component_links():
    disposition_rows = list(csv.DictReader((LEDGER / 'migration/0875-dispositions.csv').open()))
    assert len(disposition_rows) == 404
    counts = Counter(row['disposition'] for row in disposition_rows)
    assert counts['agreement'] == 310  # 257 ZAF register plus IDN grants/finance.
    assert counts['perimeter'] == 21
    assert sum(row['old_id'].startswith('zaf-register-') and row['line_id'] != ''
               for row in disposition_rows) == 257
    old_slots = {row['old_id'] for row in disposition_rows
                 if row['disposition'] == 'perimeter'}
    assert not old_slots & {r['project_id'] for r in rows('projects')}
    assert sum(r['relation'] == 'component_of' and r['relation_id'].startswith('0875.')
               for r in rows('relations')) == 11
    assert any(r['asset_id'] == 'asset-idn-pelabuhan-ratu' for r in rows('assets'))
    for relation in rows('relations'):
        if not relation['relation_id'].startswith('0875.'):
            continue
        if relation['relation'] == 'party_in':
            assert (relation['from_kind'], relation['to_kind']) == ('party', 'agreement')
        if relation['relation'] == 'role_in':
            assert (relation['from_kind'], relation['to_kind']) == ('party', 'line')
