"""Scientific boundary checks for the observable website MVP."""

from jetp._observatory_data import historical_record, public_event, timeline


def test_register_dates_are_observations_not_verified_signatures():
    event = public_event({
        'event_id': 'e', 'financial_status': 'signed', 'event_date': '2021-01-01',
        'verification_status': 'official_register', 'source_id': 's',
        'amount_original': '10', 'currency_original': 'USD',
    })
    assert event['status'] == 'Registered financing'
    assert event['date'] is None
    assert event['recorded_date'] == '2021-01-01'
    assert event['amount'] == '10'


def test_timeline_uses_event_date_and_does_not_invent_missing_dates():
    rows = [{'date': None, 'status': 'Proposed'},
            {'date': '2025-11-30', 'status': 'Construction'},
            {'date': '2025-08-08', 'status': 'Operational'}]
    assert [r['date'] for r in timeline(rows)] == ['2025-08-08', '2025-11-30', None]


def test_historical_cohort_requires_closed_and_pre_jetp_energy():
    row = {'id': 'P1', 'project_name': 'Power', 'status': 'Closed',
           'boardapprovaldate': '2010-01-01T00:00:00Z',
           'closingdate': '1/1/2015 12:00:00 AM',
           'sector_namecode': [{'name': 'Energy Transmission and Distribution'}],
           'lendinginstr': 'Investment Project Financing'}
    item = historical_record(row, 'IDN', '2022-11-15')
    assert item['years'] > 4.9
    assert item['status'] == 'Closed'
    assert historical_record(dict(row, status='Active'), 'IDN', '2022-11-15') is None
    assert historical_record(dict(row, boardapprovaldate='2023-01-01'), 'IDN', '2022-11-15') is None
    assert historical_record(dict(row, sector_namecode=[]), 'IDN', '2022-11-15') is None
    assert historical_record(dict(row, closingdate=''), 'IDN', '2022-11-15')['years'] is None


def test_unknown_dates_and_report_dates_do_not_become_event_dates():
    event = public_event({'event_date': '2025-11-30', 'financial_status': 'approved',
                          'verification_status': 'official_report'})
    assert event['date'] is None
    assert event['observed_date'] == '2025-11-30'


def test_duplicate_observations_are_not_new_financing():
    import pytest
    from jetp.build_observatory import unique_rows

    row = {'event_id': 'e', 'amount_original': '10'}
    assert unique_rows([row, row.copy()], 'event_id') == [row]
    with pytest.raises(ValueError, match='Conflicting'):
        unique_rows([row, dict(row, amount_original='20')], 'event_id')


def test_disclosure_slots_are_not_published_as_project_identities():
    from jetp.build_observatory import country_data

    named = {'project_id': 'named', 'country': 'VNM', 'canonical_name': 'A programme',
             'verification_status': 'official_report'}
    slot = dict(named, project_id='slot', verification_status='official_count_slot')
    tables = {key: [] for key in ('events', 'implementation-events', 'source-claims',
                                 'project-source-links', 'project-coverage', 'sources', 'manifest')}
    tables['projects'] = [named, slot]
    config = {'countries': {'VNM': {'headline_source': ''}}}
    from pathlib import Path

    result = country_data(Path('/nonexistent'), 'VNM', config, tables)
    assert result['undisclosed'] == 1
    assert [p['id'] for p in result['projects']] == ['named']
    assert result['projects'][0]['finance_stage'] == 'Not documented'
    assert result['projects'][0]['events'] == []


def test_snapshot_rejects_incomplete_pagination(tmp_path):
    import json

    import pytest
    from jetp.build_wb_snapshot import freeze

    page = tmp_path / 'page.json'
    page.write_text(json.dumps({'total': '2', 'projects': {'P1': {'id': 'P1'}}}))
    with pytest.raises(ValueError, match='Incomplete API pagination'):
        freeze([page], 'ID', '2026-09-13')
