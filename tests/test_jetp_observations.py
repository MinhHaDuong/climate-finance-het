"""Event observations enter v2 only through a resolved subject and cited line."""

from pathlib import Path

from jetp.build_observations import normalize_event_tables


def _financial(event_id, project_id, status, amount='10', currency='USD'):
    return {
        'event_id': event_id, 'project_id': project_id, 'country': 'ZAF',
        'financial_status': status, 'amount_original': amount,
        'currency_original': currency, 'source_id': 'doc-1', 'locator': 'row 1',
    }


def _implementation(event_id, project_id):
    return {
        'implementation_event_id': event_id, 'project_id': project_id,
        'country': 'IDN', 'implementation_status': 'preparation',
        'capacity_mw': '', 'source_id': 'doc-2', 'locator': 'row 2',
    }


def _disposition(old_id, kind='agreement', new_id='agreement-1', line_id='line-1'):
    return {'old_id': old_id, 'disposition': kind, 'new_id': new_id, 'line_id': line_id}


def test_document_rules_make_money_state_and_estimate_with_four_timings():
    observations, timings, pending = normalize_event_tables(
        [_financial('zaf-1', 'zaf-project', 'signed'),
         _financial('sen-1', 'sen-plan', 'need', amount='20', currency='EUR')],
        [_implementation('idn-1', 'idn-project')],
        [
            {'event_id': 'zaf-1', 'date_role': 'event', 'event_precision': 'day',
             'event_start': '2021-01-01', 'event_end': '2021-01-01'},
            {'event_id': 'idn-1', 'date_role': 'event', 'event_precision': 'year',
             'event_start': '2022-01-01', 'event_end': '2022-12-31'},
            {'event_id': 'idn-1', 'date_role': 'reporting_cutoff', 'event_precision': 'day',
             'event_start': '2025-11-30', 'event_end': '2025-11-30'},
            {'event_id': 'sen-1', 'date_role': 'planned', 'event_precision': 'year',
             'event_start': '2025-01-01', 'event_end': '2025-12-31'},
        ],
        [_disposition('zaf-project'), _disposition('idn-project', kind='project',
                                                    new_id='project-1', line_id='line-2'),
         _disposition('sen-plan', kind='line', new_id='line-3', line_id='line-3')],
    )
    assert pending == []
    assert [row['measure'] for row in observations] == ['amount', 'estimate', 'state']
    assert observations[2]['axis'] == 'delivery'
    assert observations[1]['subject_kind'] == 'line'
    assert observations[1]['subject_id'] == observations[1]['line_id'] == 'line-3'
    assert observations[1]['own_status'] == 'need'
    assert len(timings) == 4
    assert {(row['date_role'], row['date_precision']) for row in timings} >= {
        ('event', 'year'), ('reporting_cutoff', 'day')}


def test_missing_resolved_line_is_explicitly_pending_not_an_observation():
    observations, timings, pending = normalize_event_tables(
        [_financial('blocked-1', 'unresolved', 'approved')], [], [],
        [_disposition('unresolved', new_id='', line_id='')],
    )
    assert observations == []
    assert timings == []
    assert pending == [{
        'legacy_table': 'events', 'legacy_event_id': 'blocked-1',
        'legacy_project_id': 'unresolved', 'source_id': 'doc-1', 'locator': 'row 1',
        'reason': 'no_resolved_subject_and_cited_line',
    }]


def test_current_ledger_accounts_for_every_event_without_inventing_a_citation():
    root = Path(__file__).resolve().parents[1]
    import csv

    def rows(path):
        with path.open(encoding='utf-8', newline='') as handle:
            return list(csv.DictReader(handle))

    ledger = root / 'data' / 'jetp'
    observations, timings, pending = normalize_event_tables(
        rows(ledger / 'events.csv'), rows(ledger / 'implementation-events.csv'),
        rows(ledger / 'event-timing.csv'), rows(ledger / 'migration' / '0875-dispositions.csv'))
    assert len(observations) == len(timings) == 423
    assert len(pending) == 28
    assert len(observations) + len(pending) == 451
    assert {row['legacy_event_id'] for row in pending} >= {'zaf-murp-afdb-approved-2026'}
