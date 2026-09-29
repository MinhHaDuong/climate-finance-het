"""The IATI comparator slice preserves activity identity and transaction flow."""

import gzip
import io
import json

import pytest
from jetp._ledger_headers import LEDGER_DIR, load_schema, read_table
from jetp.build_iati_comparators import ingest
from jetp.catalog_iati_energy import collect, project

pytestmark = pytest.mark.domain_jetp


def _rows(directory, table):
    schema = load_schema()
    values, errors = read_table(directory, table, schema)
    assert not errors
    return [dict(zip(schema.header(table), row)) for row in values]


def test_two_activities_three_flows_and_no_partnership_project(tmp_path):
    ledger = tmp_path / 'jetp'
    (ledger / 'iati').mkdir(parents=True)
    source = {
        'source': 'https://datastore.codeforiati.org/api/1/access/activity.json',
        'country_code': 'ID', 'retrieved_at': '2026-10-01T12:00:00+00:00',
        'queries': [{'url': 'https://example.org/query', 'sha256': 'a' * 64,
                     'total': 2, 'returned': 2}],
        'source_total': 2, 'count': 2,
        'records': [
            {'id': 'XM-DAC-1-A', 'title': 'Solar A', 'status': '2',
             'reporting_org': 'XM-DAC-1', 'sectors': [{'code': '230', 'vocabulary': '2'}],
             'other_identifiers': [], 'source_transaction_count': 1,
             'unallocated_country_count': 0, 'unallocated_sector_count': 0,
             'transactions': [{'code': '2', 'value': '100', 'currency': 'USD',
                               'date': '2025-01-01'}]},
            {'id': 'XM-DAC-1-B', 'title': 'Grid B', 'status': '4',
             'reporting_org': 'XM-DAC-1', 'sectors': [{'code': '23110', 'vocabulary': '1'}],
             'other_identifiers': [], 'source_transaction_count': 4,
             'unallocated_country_count': 0, 'unallocated_sector_count': 0,
             'transactions': [{'code': '3', 'value': '40', 'currency': 'EUR',
                               'date': '2025-02-01'},
                              {'code': '3', 'value': '60', 'currency': 'EUR',
                               'date': '2025-03-01'},
                              {'code': '11', 'value': '70', 'currency': 'EUR',
                               'date': '2025-04-01'},
                              {'code': '13', 'value': '80', 'currency': 'EUR',
                               'date': '2025-05-01'}]},
        ],
    }
    path = ledger / 'iati' / 'ID.json.gz'
    path.write_bytes(gzip.compress(json.dumps(source).encode(), mtime=0))

    expected = {'flows': 3, 'lines': 2, 'unmapped_transactions': 2}
    assert ingest([path], ledger, recorded_at='2026-10-02') == expected
    lines = _rows(ledger, 'lines')
    assert len(lines) == 2
    assert {row['locator'] for row in lines} == {'XM-DAC-1-A', 'XM-DAC-1-B'}
    flows = _rows(ledger, 'observations')
    assert len(flows) == 3
    assert [row['flow_type'] for row in flows] == [
        'commitment', 'disbursement', 'disbursement']
    assert [row['value'] for row in flows] == ['100', '40', '60']
    assert {row['external_id'] for row in _rows(ledger, 'external_ids')
            if row['scheme'] == 'iati-activity-id'} == {'XM-DAC-1-A', 'XM-DAC-1-B'}
    assert _rows(ledger, 'projects') == []
    assert len(_rows(ledger, 'timings')) == 3
    assert ingest([path], ledger, recorded_at='2026-10-02') == expected
    assert len(_rows(ledger, 'observations')) == 3


def test_ingest_rejects_snapshot_outside_registered_location(tmp_path):
    path = tmp_path / 'ID.json.gz'
    path.write_bytes(b'not-read')
    with pytest.raises(ValueError, match='snapshot must live'):
        ingest([path], tmp_path / 'ledger', recorded_at='2026-10-02')


def test_collector_rejects_identifiers_that_collide_after_normalization(
        tmp_path, monkeypatch):
    activity = {
        'recipient-country': {'code': 'ID'},
        'sector': {'code': '230', 'vocabulary': '2'},
        'activity-status': {'code': '2'},
    }
    payload = json.dumps({'ok': True, 'total-count': 2, 'iati-activities': [
        {'iati-activity': {**activity, 'iati-identifier': 'X-1'}},
        {'iati-activity': {**activity, 'iati-identifier': 'X-1 '}},
    ]}).encode()
    monkeypatch.setattr('jetp.catalog_iati_energy.urlopen',
                        lambda *args, **kwargs: io.BytesIO(payload))
    with pytest.raises(ValueError, match='duplicate API page identifier: X-1'):
        collect('ID', tmp_path / 'ID.json.gz')


def test_projection_keeps_only_country_energy_transactions():
    activity = {
        'iati-identifier': 'XM-DAC-1-A',
        'title': {'narrative': [{'text': 'Solar  \n A'}]},
        'activity-status': {'code': '2'}, 'reporting-org': {'ref': 'XM-DAC-1'},
        'sector': [{'code': '230', 'vocabulary': '2'}],
        'transaction': [
            {'transaction-type': {'code': '2'}, 'value': {'text': '100', 'currency': 'USD'},
             'recipient-country': {'code': 'ID'}},
            {'transaction-type': {'code': '3'}, 'value': {'text': '90', 'currency': 'USD'},
             'recipient-country': {'code': 'SN'}},
        ],
    }
    projected = project(activity, 'ID')
    assert projected['title'] == 'Solar A'
    assert projected['source_transaction_count'] == 2
    assert [row['value'] for row in projected['transactions']] == ['100']


def test_projection_does_not_allocate_multicountry_or_mixed_sector_amounts():
    activity = {
        'iati-identifier': 'XM-DAC-1-C', 'title': {'narrative': 'Mixed activity'},
        'activity-status': {'code': '2'}, 'reporting-org': {'ref': 'XM-DAC-1'},
        'recipient-country': [{'code': 'ID'}, {'code': 'SN'}],
        'sector': [{'code': '230', 'vocabulary': '2'},
                   {'code': '151', 'vocabulary': '2'}],
        'transaction': [
            {'transaction-type': {'code': '2'}, 'value': {'text': '100'}},
            {'transaction-type': {'code': '3'}, 'value': {'text': '40'},
             'recipient-country': {'code': 'ID'}},
            {'transaction-type': {'code': '11'}, 'value': {'text': '60'},
             'recipient-country': {'code': 'ID'},
             'sector': {'code': '230', 'vocabulary': '2'}},
            {'transaction-type': {'code': '3'}, 'value': {'text': '70'},
             'recipient-country': {'code': 'ID'},
             'sector': {'code': '236', 'vocabulary': '11'}},
        ],
    }
    projected = project(activity, 'ID')
    assert [row['value'] for row in projected['transactions']] == ['60']
    assert projected['unallocated_country_count'] == 1
    assert projected['unallocated_sector_count'] == 1
    assert project({**activity, 'sector': {'code': '236', 'vocabulary': '11'},
                    'transaction': []}, 'ID') is None


def test_frozen_four_country_slice_has_identifiers_and_no_project_promotion():
    lines = [row for row in _rows(LEDGER_DIR, 'lines')
             if row['line_id'].startswith('iati-energy-')]
    assert {country: sum(row['country'] == country for row in lines)
            for country in ('IDN', 'SEN', 'VNM', 'ZAF')} == {
                'IDN': 344, 'SEN': 241, 'VNM': 411, 'ZAF': 305}
    assert all(row['locator'] for row in lines)
    ids = {row['id'] for row in _rows(LEDGER_DIR, 'external_ids')
           if row['scheme'] == 'iati-activity-id'}
    repeats = {row['from_id'] for row in _rows(LEDGER_DIR, 'relations')
               if row['relation'] == 'same_as' and
               row['method'] == 'exact_iati_identifier'}
    assert {row['line_id'] for row in lines} == ids | repeats
    assert len(ids) == 1207
    assert len(repeats) == 94
    project_ids = {row['project_id'] for row in _rows(LEDGER_DIR, 'projects')}
    assert not ({row['line_id'] for row in lines} & project_ids)
    flows = [row for row in _rows(LEDGER_DIR, 'observations')
             if row['line_id'].startswith('iati-energy-')]
    assert {country: sum(row['line_id'].startswith(f'iati-energy-{country}-')
                         for row in flows)
            for country in ('id', 'sn', 'vn', 'za')} == {
                'id': 4204, 'sn': 1240, 'vn': 1603, 'za': 723}
    assert not {row['own_status'] for row in flows} & {'11', '13'}
