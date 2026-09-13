"""Scientific boundary checks for the observable website MVP."""

from jetp.observatory_data import historical_record, public_event, timeline


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
