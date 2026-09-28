"""Derived commitment accounts preserve decisions, cutoffs and uncertainty."""

import json
import re
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from jetp.build_accounts import account_for, build
from jetp.build_observatory import perimeter_headlines

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.wp_jetp


def _add(conn, table, **fields):
    names = ', '.join(fields)
    marks = ', '.join('?' for _ in fields)
    conn.execute(f'INSERT INTO {table} ({names}) VALUES ({marks})', tuple(fields.values()))


def _fixture():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript((ROOT / 'config/jetp-ledger.sql').read_text())
    for identity in ('agreement-1', 'agreement-2', 'agreement-3'):
        _add(conn, 'agreements', agreement_id=identity, country='ZAF', currency='USD')
    _add(conn, 'perimeters', perimeter_row_id='scope.1', perimeter_id='scope',
         name='Fixture scope', definition='Fixture scope', recorded_at='2026-01-01',
         decided_by='reviewer', status='accepted')
    _add(conn, 'relations', relation_id='member-1', from_kind='agreement',
         from_id='agreement-1', relation='member_of', to_kind='perimeter',
         to_id='scope', status='accepted', method='review',
         decided_at='2026-01-01', decided_by='reviewer')
    for n, value in enumerate((5, 5, 7, 2, 3), 1):
        _add(conn, 'observations', observation_id=f'flow-{n}',
             subject_kind='agreement', subject_id='agreement-1', measure='flow',
             flow_type='commitment', basis='gross', value=value,
             currency='USD', line_id=f'line-{n}', method='review',
             recorded_at='2026-04-01', status='accepted')
        _add(conn, 'timings', timing_id=f'flow-time-{n}',
             observation_id=f'flow-{n}', date_role='event',
             date='2026-02-01', date_precision='day', recorded_at='2026-04-01')
    for identity, value, day in (('opening', 0, '2026-01-01'),
                                 ('closing', 20, '2026-03-31')):
        _add(conn, 'observations', observation_id=identity,
             subject_kind='agreement', subject_id='agreement-1', measure='amount',
             basis='gross', value=value, currency='USD', line_id=identity,
             method='review', recorded_at='2026-04-01', status='accepted')
        _add(conn, 'timings', timing_id=f'{identity}-time',
             observation_id=identity, date_role='reporting_cutoff',
             date=day, date_precision='day', recorded_at='2026-04-01')
    _add(conn, 'adjudications', adjudication_id='occ-1',
         decision_type='occurrence_membership', subject_kind='observation',
         subject_id='flow-1', verdict='accepted', status='accepted',
         decided_at='2026-04-01', decided_by='reviewer', recorded_at='2026-04-01')
    for identity in ('flow-1', 'flow-2'):
        _add(conn, 'adjudication_members', adjudication_id='occ-1',
             kind='observation', id=identity, role='occurrence')
    _add(conn, 'adjudications', adjudication_id='cover-1',
         decision_type='flow_coverage', subject_kind='agreement',
         subject_id='agreement-1', verdict='complete', status='accepted',
         decided_at='2026-04-01', decided_by='reviewer', recorded_at='2026-04-01')
    for identity, role in (('flow-3', 'covering_flow'),
                           ('flow-4', 'covered_movement'),
                           ('opening', 'opening'), ('closing', 'closing')):
        _add(conn, 'adjudication_members', adjudication_id='cover-1',
             kind='observation', id=identity, role=role)
    return conn


def _account(conn, knowledge='2026-04-02'):
    return account_for(conn, 'agreement-1', 'scope', 'USD', '2026-03-31', knowledge)


def test_three_agreements_five_flows_one_duplicate_and_residual():
    conn = _fixture()
    try:
        assert conn.execute('SELECT count(*) FROM agreements').fetchone()[0] == 3
        assert conn.execute("SELECT count(*) FROM observations WHERE measure='flow'").fetchone()[0] == 5
        account = _account(conn)
        assert account['status'] == 'exact'
        assert account['included_observation_ids'] == ['flow-1', 'flow-3', 'flow-5']
        assert account['excluded_observation_ids'] == ['flow-2', 'flow-4']
        assert Decimal(account['documented_subtotal']) == 15
        assert Decimal(account['reconstructed_closing']) == 15
        assert Decimal(account['residual']) == 5
        assert account['decision_ids'] == ['cover-1', 'occ-1']
    finally:
        conn.close()


def test_rejected_supersession_removes_duplicate_ruling_and_exact_residual():
    conn = _fixture()
    try:
        _add(conn, 'adjudications', adjudication_id='occ-2',
             decision_type='occurrence_membership', subject_kind='observation',
             subject_id='flow-1', verdict='rejected', status='rejected',
             decided_at='2026-04-02', decided_by='reviewer',
             recorded_at='2026-04-02', supersedes='occ-1')
        _add(conn, 'adjudication_members', adjudication_id='occ-2',
             kind='observation', id='flow-2', role='excluded')
        before = _account(conn, '2026-04-01')
        after = _account(conn)
        assert Decimal(before['documented_subtotal']) == 15
        assert Decimal(after['documented_subtotal']) == 10
        assert after['status'] == 'incomplete' and after['residual'] is None
        assert 'flow-1' in after['excluded_observation_ids']
        assert 'flow-2' in after['excluded_observation_ids']
        assert any('occurrence unresolved' in reason for reason in after['uncertainty'])
    finally:
        conn.close()


def test_partial_coverage_retains_subtotal_without_inventing_closing():
    conn = _fixture()
    try:
        conn.execute("UPDATE adjudications SET verdict='partial' WHERE adjudication_id='cover-1'")
        result = _account(conn)
        assert result['status'] == 'incomplete'
        assert Decimal(result['documented_subtotal']) == 15
        assert result['reconstructed_closing'] is None and result['residual'] is None
        assert 'complete coverage not reviewed' in result['uncertainty']
    finally:
        conn.close()


def test_coverage_cannot_remove_a_flow_outside_the_account():
    conn = _fixture()
    try:
        conn.execute("UPDATE adjudication_members SET id='flow-missing' "
                     "WHERE adjudication_id='cover-1' AND role='covering_flow'")
        result = _account(conn)
        assert result['status'] == 'incomplete'
        assert Decimal(result['documented_subtotal']) == 17
        assert result['residual'] is None
        assert 'flow-4' in result['included_observation_ids']
        assert 'coverage members unavailable: cover-1' in result['uncertainty']
    finally:
        conn.close()


def test_accepted_supersession_replaces_occurrence_members():
    conn = _fixture()
    try:
        _add(conn, 'adjudications', adjudication_id='occ-2',
             decision_type='occurrence_membership', subject_kind='observation',
             subject_id='flow-1', verdict='accepted', status='accepted',
             decided_at='2026-04-02', decided_by='reviewer',
             recorded_at='2026-04-02', supersedes='occ-1')
        for identity in ('flow-1', 'flow-5'):
            _add(conn, 'adjudication_members', adjudication_id='occ-2',
                 kind='observation', id=identity, role='occurrence')
        result = _account(conn)
        assert result['included_observation_ids'] == ['flow-1', 'flow-2', 'flow-3']
        assert Decimal(result['documented_subtotal']) == 17
    finally:
        conn.close()


def test_exact_period_flow_and_membership_validity():
    conn = _fixture()
    try:
        conn.execute("DELETE FROM timings WHERE observation_id='flow-5'")
        for role, day in (('period_start', '2026-02-01'),
                          ('period_end', '2026-02-28')):
            _add(conn, 'timings', timing_id=f'flow-5-{role}',
                 observation_id='flow-5', date_role=role, date=day,
                 date_precision='day', recorded_at='2026-04-01')
        assert _account(conn)['status'] == 'exact'
        conn.execute("UPDATE relations SET valid_from='2026-04-01'")
        result = _account(conn)
        assert result['status'] == 'incomplete'
        assert 'agreement perimeter membership unreviewed' in result['uncertainty']
    finally:
        conn.close()


def test_real_ledger_has_no_admitted_commitment_flow_and_build_is_stable():
    first = build(ROOT / 'data/jetp')
    second = build(ROOT / 'data/jetp')
    assert first == second
    assert first['accounts'] == []
    assert first['availability']
    assert first['ontology_ref'].startswith('sha256:')
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_served_headlines_match_cited_perimeter_observations():
    import yaml

    config_text = (ROOT / 'config/jetp_observatory.yaml').read_text()
    assert not re.search(r'[$€]|\d+(?:\.\d+)?bn', config_text)
    config = yaml.safe_load(config_text)
    served = json.loads((ROOT / 'deliverables/jetp-observatory/data/overview.json').read_text())
    expected = {'ZAF': ('$8.5bn', '$6.12bn allocated'),
                'IDN': ('$20bn', '≈$3.1bn approved'),
                'VNM': ('$15.5bn', 'Secretariat newsletter · March 2026'),
                'SEN': ('€2.5bn', '43 project / programme records')}
    for country in served['countries']:
        code = country['code']
        derived = perimeter_headlines(ROOT, config['countries'][code])
        assert (country['pledge_label'], country['headline']) == expected[code]
        assert country['pledge_citation'] == derived['pledge_citation']
        if 'headline_citation' in derived:
            assert country['headline_citation'] == derived['headline_citation']
