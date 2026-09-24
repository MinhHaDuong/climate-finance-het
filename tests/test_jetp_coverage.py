"""Coverage migration preserves source rows without inventing referents."""

import csv

from jetp._ledger_headers import load_schema, write_table
from jetp.build_coverage import build
from jetp.build_observatory import coverage_data


def _write(path, name, rows):
    write_table(path, name, rows, schema=load_schema())


def _legacy(path, name, fields, rows):
    (path / name).parent.mkdir(parents=True, exist_ok=True)
    with (path / name).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_projects_authorities_and_count_slots_resolve_to_referents(tmp_path):
    _write(tmp_path, 'routes', [dict(old_id='old-project', kind='project', new_id='project-1')])
    _write(tmp_path, 'parties', [dict(party_id='authority-1')])
    _write(tmp_path, 'party_names', [dict(name_row_id='authority-1.name', party_id='authority-1',
                                          name='Authority One', form_type='preferred',
                                          recorded_at='2026-09-24', decided_by='fixture', status='accepted')])
    _legacy(tmp_path, 'migration/0875-dispositions.csv',
            ('old_id', 'disposition', 'new_id', 'basis_method', 'line_id'),
            [dict(old_id='count-slot', disposition='perimeter', new_id='vnm-portfolio', basis_method='count', line_id='')])
    _legacy(tmp_path, 'project-coverage.csv',
            ('country', 'project_id', 'review_status', 'source_ids', 'checked_at', 'query_or_route', 'notes'),
            [dict(country='ZAF', project_id='old-project', review_status='collected', source_ids='doc-1', checked_at='2026-09-24', query_or_route='route', notes=''),
             dict(country='VNM', project_id='count-slot', review_status='blocked', source_ids='doc-2', checked_at='2026-09-24', query_or_route='count route', notes='')])
    _legacy(tmp_path, 'authority-coverage.csv',
            ('country', 'authority_id', 'authority', 'authority_category', 'verdict', 'source_ids', 'checked_at', 'notes'),
            [dict(country='ZAF', authority_id='legacy-authority', authority='Authority One', authority_category='national_government', verdict='collected', source_ids='doc-3', checked_at='2026-09-24', notes='')])

    coverage, dispositions, reconciliation = build(tmp_path)

    assert {(r['referent_kind'], r['referent_id']) for r in coverage} == {
        ('project', 'project-1'), ('perimeter', 'vnm-portfolio'), ('party', 'authority-1')}
    assert not dispositions
    assert len(reconciliation) == 3


def test_row_without_a_resolved_referent_has_a_named_disposition(tmp_path):
    _write(tmp_path, 'routes', [])
    _write(tmp_path, 'parties', [])
    _write(tmp_path, 'party_names', [])
    _legacy(tmp_path, 'migration/0875-dispositions.csv',
            ('old_id', 'disposition', 'new_id', 'basis_method', 'line_id'), [])
    _legacy(tmp_path, 'project-coverage.csv',
            ('country', 'project_id', 'review_status', 'source_ids', 'checked_at', 'query_or_route', 'notes'),
            [dict(country='VNM', project_id='unresolved', review_status='blocked', source_ids='', checked_at='2026-09-24', query_or_route='', notes='')])
    _legacy(tmp_path, 'authority-coverage.csv',
            ('country', 'authority_id', 'authority', 'authority_category', 'verdict', 'source_ids', 'checked_at', 'notes'), [])

    coverage, dispositions, reconciliation = build(tmp_path)

    assert coverage == []
    assert dispositions == [dict(source_table='project-coverage.csv', old_id='unresolved',
                                 disposition='no_referent', detail='0875 has no resolved identity')]
    assert reconciliation[0]['outcome'] == 'disposition'


def test_several_legacy_count_slots_coalesce_on_their_one_perimeter(tmp_path):
    _write(tmp_path, 'routes', [])
    _write(tmp_path, 'parties', [])
    _write(tmp_path, 'party_names', [])
    _legacy(tmp_path, 'migration/0875-dispositions.csv',
            ('old_id', 'disposition', 'new_id', 'basis_method', 'line_id'),
            [dict(old_id=key, disposition='perimeter', new_id='vnm-portfolio', basis_method='count', line_id='')
             for key in ('slot-a', 'slot-b')])
    _legacy(tmp_path, 'project-coverage.csv',
            ('country', 'project_id', 'review_status', 'source_ids', 'checked_at', 'query_or_route', 'notes'),
            [dict(country='VNM', project_id='slot-a', review_status='blocked', source_ids='doc-a', checked_at='2026-09-23', query_or_route='first', notes='a'),
             dict(country='VNM', project_id='slot-b', review_status='blocked', source_ids='doc-b', checked_at='2026-09-24', query_or_route='second', notes='b')])
    _legacy(tmp_path, 'authority-coverage.csv',
            ('country', 'authority_id', 'authority', 'authority_category', 'verdict', 'source_ids', 'checked_at', 'notes'), [])

    coverage, dispositions, reconciliation = build(tmp_path)

    assert dispositions == []
    assert {row['referent_id'] for row in reconciliation} == {'vnm-portfolio'}
    assert coverage == [dict(referent_kind='perimeter', referent_id='vnm-portfolio',
                             review_status='blocked', checked_at='2026-09-24',
                             route='first | second', document_ids='doc-a;doc-b', notes='a | b')]


def test_coverage_view_serves_the_ledger_table(tmp_path):
    _write(tmp_path / 'data/jetp', 'coverage', [dict(referent_kind='project', referent_id='project-1',
                                                      review_status='collected', checked_at='2026-09-24')])

    assert coverage_data(tmp_path) == {'coverage': [dict(referent_kind='project', referent_id='project-1',
                                                           review_status='collected', checked_at='2026-09-24',
                                                           route=None, document_ids=None, notes=None)]}


def test_newer_conflicting_status_is_kept_once_with_its_note(tmp_path):
    _write(tmp_path, 'routes', [])
    _write(tmp_path, 'parties', [dict(party_id='authority-1')])
    _write(tmp_path, 'party_names', [dict(name_row_id='authority-1.name', party_id='authority-1',
                                          name='Authority One', form_type='preferred',
                                          recorded_at='2026-09-24', decided_by='fixture', status='accepted')])
    _legacy(tmp_path, 'migration/0875-dispositions.csv',
            ('old_id', 'disposition', 'new_id', 'basis_method', 'line_id'), [])
    _legacy(tmp_path, 'project-coverage.csv',
            ('country', 'project_id', 'review_status', 'source_ids', 'checked_at', 'query_or_route', 'notes'), [])
    _legacy(tmp_path, 'authority-coverage.csv',
            ('country', 'authority_id', 'authority', 'authority_category', 'verdict', 'source_ids', 'checked_at', 'notes'),
            [dict(country='ZAF', authority_id='first', authority='Authority One', authority_category='', verdict='blocked', source_ids='doc-a', checked_at='2026-09-23', notes='first note'),
             dict(country='IDN', authority_id='second', authority='Authority One', authority_category='', verdict='collected', source_ids='doc-b', checked_at='2026-09-24', notes='second note')])

    coverage, _, _ = build(tmp_path)

    assert coverage[0]['review_status'] == 'collected'
    assert coverage[0]['notes'] == 'Review status blocked: first note | Review status collected: second note'
