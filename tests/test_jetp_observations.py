"""Event observations enter v2 only through a resolved subject and cited line."""

import csv
import hashlib
import re
from decimal import Decimal
from pathlib import Path

from jetp.build_observations import (
    citation_provenance_errors,
    normalize_event_tables,
    reconcile_timing_rows,
)


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
             'event_start': '', 'event_end': '', 'observed_on': '2025-11-30'},
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


def test_0970_accepts_event_specific_targets_and_holds_physical_claims():
    observations, timings, pending = normalize_event_tables(
        [_financial('finance-1', 'legacy-finance', 'approved')],
        [_implementation('physical-1', 'legacy-physical')],
        [{'event_id': 'finance-1', 'date_role': 'reporting_cutoff',
          'event_precision': 'unknown', 'event_start': '', 'event_end': '',
          'observed_on': '2025-11-30'},
         {'event_id': 'physical-1', 'date_role': 'reporting_cutoff',
          'event_precision': 'unknown', 'event_start': '', 'event_end': '',
          'observed_on': '2025-11-30'}],
        [_disposition('legacy-finance', new_id='', line_id=''),
         _disposition('legacy-physical', new_id='', line_id='')],
        [{'legacy_table': 'events', 'legacy_event_id': 'finance-1',
          'legacy_project_id': 'legacy-finance', 'source_id': 'doc-1',
          'line_id': 'exact-finance-row', 'referent_kind': 'line',
          'referent_id': 'exact-finance-row', 'promotion': 'accept'},
         {'legacy_table': 'implementation-events', 'legacy_event_id': 'physical-1',
          'legacy_project_id': 'legacy-physical', 'source_id': 'doc-2',
          'line_id': 'exact-physical-row', 'referent_kind': 'project',
          'referent_id': 'project-physical', 'promotion': 'hold'}],
    )
    assert [(row['subject_kind'], row['subject_id'], row['line_id']) for row in observations] == [
        ('line', 'exact-finance-row', 'exact-finance-row')]
    assert [(row['observation_id'], row['date_role']) for row in timings] == [
        ('observation-finance-1', 'reporting_cutoff')]
    assert pending == [{
        'legacy_table': 'implementation-events', 'legacy_event_id': 'physical-1',
        'legacy_project_id': 'legacy-physical', 'source_id': 'doc-2',
        'locator': 'row 2; line_id=exact-physical-row',
        'reason': '0970_physical_state_hold',
    }]


def test_current_ledger_accounts_for_every_event_without_inventing_a_citation():
    root = Path(__file__).resolve().parents[1]

    def rows(path):
        with path.open(encoding='utf-8', newline='') as handle:
            return list(csv.DictReader(handle))

    ledger = root / 'data' / 'jetp'
    event_timings = rows(ledger / 'event-timing.csv')
    decisions = rows(ledger / 'migration' / '1160-citation-decisions.csv')
    observations, timings, pending = normalize_event_tables(
        rows(ledger / 'events.csv'), rows(ledger / 'implementation-events.csv'),
        event_timings, rows(ledger / 'migration' / '0875-dispositions.csv'),
        rows(ledger / 'migration' / '0970-event-adjudications.csv') +
        rows(ledger / 'migration' / '1120-event-adjudications.csv'), decisions)
    assert len(observations) == 443
    assert len(timings) == 362
    assert len(pending) == 91
    event_pending = [row for row in pending if row['legacy_table'] != 'event-timing']
    assert len(observations) + len(event_pending) == 451
    reconciliation = reconcile_timing_rows(event_timings, observations, timings, pending)
    assert len(reconciliation) == 451
    assert sum(row['outcome'] == 'typed_timing' for row in reconciliation) == 360
    assert sum(bool(row['approval_timing_id']) for row in reconciliation) == 2
    assert all(row['lower_bound'] and row['upper_bound'] for row in timings)
    assert all(row['date'] == row['lower_bound'] == row['upper_bound']
               for row in timings if row['date_role'] in
               {'register_date', 'report_date', 'reporting_cutoff'})
    committed_reconciliation = rows(ledger / 'migration' / '0876-timing-reconciliation.csv')
    assert [{key: value for key, value in row.items() if key != 'reason'}
            for row in committed_reconciliation] == [
        {key: str(value) for key, value in row.items() if key != 'reason'}
        for row in reconciliation]
    assert sum(row['reason'] == '0970_physical_state_hold'
               for row in committed_reconciliation) == 3
    committed_timings = rows(ledger / 'timings.csv')
    assert {row['timing_id']: (row['date_role'], row['date_precision'],
                               row['lower_bound'], row['upper_bound'])
            for row in committed_timings} == {
        row['timing_id']: (row['date_role'], row['date_precision'],
                           row['lower_bound'], row['upper_bound'])
        for row in timings}
    assert all(row['lower_bound'] and row['upper_bound'] for row in committed_timings)
    assert sum(row['reason'].startswith('unmapped_date_role_')
               for row in reconciliation) == 82
    assert {row['legacy_event_id'] for row in pending
            if row['reason'] == '0970_physical_state_hold'} == {
                'idn-impl-green-corridors-2025', 'idn-impl-dieng34-2025',
                'idn-impl-nagajaya-portal-2026'}
    # The article supports the approval but its date is publication; the
    # legacy event-day timing remains pending after the 1120 review.
    assert {row['observation_id'] for row in observations
            if row['observation_id'] == 'observation-zaf-murp-afdb-approved-2026'} == {
                'observation-zaf-murp-afdb-approved-2026'}
    assert {row['legacy_event_id'] for row in pending
            if row['reason'] == 'approval_day_unsupported_by_cited_article'} == {
                'zaf-murp-afdb-approved-2026'}
    assert {row['legacy_event_id'] for row in committed_reconciliation
            if row['reason'] == 'approval_day_unsupported_by_cited_article'} == {
                'zaf-murp-afdb-approved-2026'}
    assert {row['legacy_event_id'] for row in pending} >= {'zaf-murp-afdb-approved-2026'}


def test_1160_every_mismatch_has_source_evidence_or_a_named_hold():
    root = Path(__file__).resolve().parents[1]
    ledger = root / 'data' / 'jetp'

    def rows(path):
        with path.open(encoding='utf-8', newline='') as handle:
            return list(csv.DictReader(handle))

    register = rows(root / 'docs/jetp-0876-citation-mismatches.csv')
    decisions = rows(ledger / 'migration/1160-citation-decisions.csv')
    events = rows(ledger / 'events.csv')
    implementation = rows(ledger / 'implementation-events.csv')
    observations = rows(ledger / 'observations.csv')
    pending = rows(ledger / 'migration/0876-pending.csv')
    lines = [row for path in sorted((ledger / 'lines.d').glob('*.csv'))
             for row in rows(path)]
    retrievals = rows(ledger / 'retrievals.csv')
    assert len(register) == len(decisions) == 120
    assert {row['legacy_event_id'] for row in register} == {
        row['legacy_event_id'] for row in decisions}
    assert len(observations) + sum(row['legacy_table'] != 'event-timing'
                                   for row in pending) == 451
    assert citation_provenance_errors(
        events, implementation, observations, pending, decisions, lines, retrievals) == []

    sources = {**{row['event_id']: row for row in events},
               **{row['implementation_event_id']: row for row in implementation}}
    line_by_id = {row['line_id']: row for row in lines}
    observation_by_id = {row['observation_id'].removeprefix('observation-'): row
                         for row in observations}
    for event_id, observation in observation_by_id.items():
        source = sources[event_id]
        assert line_by_id[observation['line_id']]['country'] == source['country']
        assert observation['own_status'] == source.get(
            'financial_status', source.get('implementation_status'))
        assert observation['value'] == source.get('amount_original',
                                                   source.get('capacity_mw', ''))
        assert observation['currency'] == source.get('currency_original', '')
    mismatch_by_id = {row['legacy_event_id']: row for row in register}
    manifest = rows(ledger / 'manifest.csv')
    snapshot_by_source = {(row['source_id'], row['sha256']): row['storage_path']
                          for row in manifest if row['sha256']}
    checked_snapshots = set()
    for decision in decisions:
        event_id = decision['legacy_event_id']
        original = sources[event_id]
        mismatch = mismatch_by_id[event_id]
        assert decision['source_id'] == mismatch['legacy_source_id'] == original['source_id']
        assert decision['source_sha256'] == mismatch['legacy_source_retrieval_sha256']
        if decision['decision'] == 'pending':
            assert event_id not in observation_by_id
            assert any(row['legacy_event_id'] == event_id and
                       row['reason'] == f"1160_{decision['reason']}" for row in pending)
            continue
        line = line_by_id[decision['line_id']]
        assert observation_by_id[event_id]['line_id'] == line['line_id']
        assert line['sha256'] == decision['source_sha256']
        assert line['locator'] == decision['locator']
        assert line['sha256'] != mismatch['current_line_sha256']
        status = decision['source_status']
        support_words = {
            'approved': ('approved',),
            'need': ('estimated plan cost',),
            'announced': ('in process', 'financing', 'allocated', 'grant', 'loan'),
            'mou': ('MOU',),
            'proposed': ('proposed', 'planned', 'prospective'),
            'procurement': ('tender', 'bids'),
            'preparation': ('studies', 'advisory'),
            'construction': ('construction', 'first stone'),
            'operational': ('mass production', 'put into service'),
            'suspended': ('halted',),
            'closure_proposed': ('proposed closure',),
        }
        assert any(word in line['label'] for word in support_words[status])
        if decision['source_value'] and decision['source_currency']:
            assert decision['source_value'] == original['amount_original']
            assert decision['source_currency'] == original['currency_original']
            if 'million' in line['label']:
                match = re.search(r'(\d+(?:\.\d+)?) million (CAD|EUR|GBP|USD)',
                                  line['label'])
                if match is None:
                    match = re.search(r'(CAD|EUR|GBP|USD) (\d+(?:\.\d+)?) million',
                                      line['label'])
                    assert match is not None
                    amount, currency = match[2], match[1]
                else:
                    amount, currency = match[1], match[2]
                assert Decimal(amount) * 1_000_000 == int(decision['source_value'])
                assert currency == decision['source_currency']
            elif decision['source_currency'] == 'JPY':
                match = re.search(r'JPY (\d+(?:\.\d+)?) billion', line['label'])
                assert match is not None
                assert Decimal(match[1]) * 1_000_000_000 == int(
                    decision['source_value'])
            else:
                raise AssertionError(f'{event_id}: no numeric source value in cited line')
        key = (decision['source_id'], decision['source_sha256'])
        if key not in checked_snapshots:
            archived = ledger / 'documents' / snapshot_by_source[key]
            assert hashlib.sha256(archived.read_bytes()).hexdigest() == key[1]
            checked_snapshots.add(key)

    wrong_line = dict(observation_by_id[register[0]['legacy_event_id']])
    wrong_line['line_id'] = register[0]['current_line_id']
    tampered = [wrong_line if row['observation_id'] == wrong_line['observation_id'] else row
                for row in observations]
    assert any('not a retrieval' in error for error in citation_provenance_errors(
        events, implementation, tampered, pending, decisions, lines, retrievals))
