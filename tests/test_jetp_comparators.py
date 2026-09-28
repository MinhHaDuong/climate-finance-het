"""Comparator records stay source lines across API editions (ticket 0879)."""

import json
import shutil

import pytest
from jetp._ledger_headers import LEDGER_DIR, load_schema, read_table
from jetp.build_comparators import flow_type, ingest
from jetp.build_ledger import build

pytestmark = pytest.mark.wp_jetp


def rows(directory, table):
    schema = load_schema()
    values, errors = read_table(directory, table, schema)
    assert not errors
    return [dict(zip(schema.header(table), row)) for row in values]


def test_two_projects_on_two_editions(tmp_path):
    ledger = tmp_path / 'jetp'
    ledger.mkdir()
    for source in LEDGER_DIR.glob('*.csv'):
        shutil.copy2(source, ledger / source.name)
    for subdir in ('ontology', 'lines.d', 'line-fields'):
        shutil.copytree(LEDGER_DIR / subdir, ledger / subdir)
    (ledger / 'comparison').mkdir()

    fields = ['id', 'project_name', 'status', 'boardapprovaldate', 'closingdate',
              'lendinginstr', 'sector_namecode', 'supplementprojectflg', 'url']
    source_paths = []
    for day in ('2026-10-01', '2026-10-02'):
        records = []
        for number, status in ((1, 'Closed'), (2, 'Active')):
            records.append(dict(id=f'P99999{number}', project_name=f'Test {number}',
                status=status, boardapprovaldate='2020-01-01T00:00:00Z',
                closingdate='12/31/2021 12:00:00 AM', lendinginstr='Investment Loan',
                sector_namecode=[{'name': 'Energy', 'code': 'L'}],
                supplementprojectflg='N', url=f'https://example.org/P99999{number}'))
        path = ledger / 'comparison' / f'{day}.json'
        path.write_text(json.dumps(dict(country_code='ID', retrieved_on=day,
            source_total=2, projection_fields=fields, records=records)))
        source_paths.append(path)

    assert ingest(source_paths[:1], ledger, recorded_at='2026-10-03') == (2, 1)
    assert ingest(source_paths[1:], ledger, recorded_at='2026-10-03') == (2, 1)
    assert build(ledger) == []
    documents = {r['document_id']: r for r in rows(ledger, 'documents')}
    assert documents['world-bank-projects-id-2026-10-02']['edition_of'] == \
        'world-bank-projects-id-2026-10-01'
    lines = [r for r in rows(ledger, 'lines') if 'P99999' in r['line_id']]
    assert len(lines) == 4
    assert len([r for r in rows(ledger, 'relations')
                if r['relation'] == 'same_as' and r['from_id'] in {x['line_id'] for x in lines}]) == 2
    assert len([r for r in rows(ledger, 'relations')
                if r['relation'] == 'member_of' and r['from_id'] in {x['line_id'] for x in lines}]) == 2
    external = {r['external_id']: r for r in rows(ledger, 'external_ids')
                if r['scheme'] == 'world-bank-p-number'}
    assert set(external) >= {'P999991', 'P999992'}
    assert {external[key]['kind'] for key in ('P999991', 'P999992')} == {'line'}
    assert all(r['project_id'] not in {'P999991', 'P999992'} for r in rows(ledger, 'projects'))
    assert any(r['publisher_id'] == 'world-bank' and r['own_status'] == 'Closed'
               and r['shared_status'] == 'closed' for r in rows(ledger, 'status_crosswalk'))
    assert ingest(source_paths, ledger, recorded_at='2026-10-03') == (4, 2)
    assert build(ledger) == []
    assert len([r for r in rows(ledger, 'lines') if 'P99999' in r['line_id']]) == 4
    with pytest.raises(ValueError, match='duplicate country/date edition'):
        ingest([source_paths[0]] * 2, ledger, recorded_at='2026-10-03')


def test_flow_codes_and_invalid_code():
    assert flow_type('C') == 'commitment'
    assert flow_type('D') == 'disbursement'
    with pytest.raises(ValueError, match='unknown comparator flow type'):
        flow_type('X')


def test_deposited_bank_counts_and_pool():
    lines = [r for r in rows(LEDGER_DIR, 'lines')
             if r['line_id'].startswith('world-bank-projects-')]
    assert {code: sum(r['country'] == code for r in lines)
            for code in ('IDN', 'SEN', 'VNM', 'ZAF')} == {
                'IDN': 593, 'SEN': 216, 'VNM': 262, 'ZAF': 48}
    ids = {r['id'] for r in rows(LEDGER_DIR, 'external_ids')
           if r['scheme'] == 'world-bank-p-number'}
    assert {r['line_id'] for r in lines} == ids
    assert sum(r['relation'] == 'member_of' and
               r['to_id'] == 'world-bank-pre-jetp-closed-energy'
               for r in rows(LEDGER_DIR, 'relations')) == 97
