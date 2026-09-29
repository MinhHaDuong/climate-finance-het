"""Derived commitment accounts preserve decisions, cutoffs and uncertainty."""

import hashlib
import json
import re
import sqlite3
from decimal import Decimal
from pathlib import Path

import jetp.build_accounts as module
import pytest
from jetp import build_ledger as ledger_build
from jetp.build_accounts import _latest_knowledge, account_for, build
from jetp.build_ledger import content_digest
from jetp.build_observatory import perimeter_headlines
from test_jetp_ledger_ddl import _valid_tables, _write

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.domain_jetp


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
    for identity, role in (('flow-1', 'covering_flow'),
                           ('flow-3', 'covering_flow'),
                           ('flow-5', 'covering_flow'),
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
                     "WHERE adjudication_id='cover-1' AND id='flow-3'")
        result = _account(conn)
        assert result['status'] == 'incomplete'
        assert Decimal(result['documented_subtotal']) == 0
        assert result['residual'] is None
        assert 'flow-4' in result['excluded_observation_ids']
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
        assert result['included_observation_ids'] == ['flow-1', 'flow-3']
        assert Decimal(result['documented_subtotal']) == 12
        assert result['status'] == 'incomplete'
        assert 'unreviewed flows: flow-2' in result['uncertainty']
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


def test_unreviewed_flow_cannot_create_a_false_exact_total():
    conn = _fixture()
    try:
        _add(conn, 'observations', observation_id='flow-extra',
             subject_kind='agreement', subject_id='agreement-1', measure='flow',
             flow_type='commitment', basis='gross', value=9, currency='USD',
             line_id='extra', method='review', recorded_at='2026-04-01', status='accepted')
        _add(conn, 'timings', timing_id='flow-extra-time', observation_id='flow-extra',
             date_role='event', date='2026-02-01', date_precision='day',
             recorded_at='2026-04-01')
        result = _account(conn)
        assert result['status'] == 'incomplete'
        assert Decimal(result['documented_subtotal']) == 15
        assert result['residual'] is None
        assert 'unreviewed flows: flow-extra' in result['uncertainty']
    finally:
        conn.close()


def test_future_review_cannot_complete_an_earlier_knowledge_account():
    conn = _fixture()
    try:
        conn.execute("UPDATE adjudications SET decided_at='2026-05-01' "
                     "WHERE adjudication_id='cover-1'")
        result = _account(conn)
        assert result['status'] == 'incomplete'
        assert result['reconstructed_closing'] is None and result['residual'] is None
        assert 'complete coverage not reviewed' in result['uncertainty']
    finally:
        conn.close()


def test_default_knowledge_advances_after_review_without_new_observation():
    conn = _fixture()
    try:
        assert _latest_knowledge(conn, '2026-03-31') == '2026-04-01'
        conn.execute("UPDATE adjudications SET decided_at='2026-05-01', "
                     "recorded_at='2026-05-01' WHERE adjudication_id='cover-1'")
        assert _latest_knowledge(conn, '2026-03-31') == '2026-05-01'
    finally:
        conn.close()


def test_membership_must_cover_opening_and_closing():
    conn = _fixture()
    try:
        conn.execute("UPDATE relations SET valid_from='2026-03-01'")
        result = _account(conn)
        assert result['status'] == 'incomplete'
        assert result['residual'] is None
        assert 'agreement perimeter membership unreviewed' in result['uncertainty']
    finally:
        conn.close()


def test_rejected_membership_successor_revokes_the_old_relation():
    conn = _fixture()
    try:
        _add(conn, 'relations', relation_id='member-revoked', from_kind='agreement',
             from_id='agreement-1', relation='member_of', to_kind='perimeter',
             to_id='scope', status='rejected', method='review',
             decided_at='2026-04-02', decided_by='reviewer', supersedes='member-1')
        result = _account(conn)
        assert result['status'] == 'incomplete'
        assert 'agreement perimeter membership unreviewed' in result['uncertainty']
    finally:
        conn.close()


def test_preopening_flow_is_outside_documented_subtotal():
    conn = _fixture()
    try:
        conn.execute("UPDATE timings SET date='2025-12-31' WHERE observation_id='flow-5'")
        result = _account(conn)
        assert Decimal(result['documented_subtotal']) == 12
        assert result['included_observation_ids'] == ['flow-1', 'flow-3']
        assert 'flow-5' not in result['included_observation_ids']
    finally:
        conn.close()


def test_equal_scalar_bounds_keep_exact_amount():
    conn = _fixture()
    try:
        conn.execute("UPDATE observations SET value_low=3, value_high=3 "
                     "WHERE observation_id='flow-5'")
        result = _account(conn)
        assert result['status'] == 'exact'
        assert Decimal(result['documented_subtotal']) == 15
    finally:
        conn.close()


def test_blank_raw_csv_bounds_are_absent():
    conn = _fixture()
    try:
        raw = {row['observation_id']: {'value': str(row['value']),
                                       'value_low': '', 'value_high': ''}
               for row in conn.execute('SELECT * FROM observations')}
        result = account_for(conn, 'agreement-1', 'scope', 'USD', '2026-03-31',
                             '2026-04-02', raw)
        assert result['status'] == 'exact'
        assert Decimal(result['documented_subtotal']) == 15
    finally:
        conn.close()


def test_covered_movement_must_fit_covering_flow_interval():
    conn = _fixture()
    try:
        conn.execute("UPDATE timings SET date='2026-03-15' WHERE observation_id='flow-4'")
        result = _account(conn)
        assert result['status'] == 'incomplete'
        assert result['residual'] is None
        assert 'covered movement outside covering flow: cover-1' in result['uncertainty']
    finally:
        conn.close()


def test_covering_flow_before_opening_cannot_exclude_later_movement():
    conn = _fixture()
    try:
        conn.execute("UPDATE timings SET date='2025-12-31' WHERE observation_id='flow-3'")
        conn.execute("UPDATE timings SET date='2026-02-02' "
                     "WHERE observation_id IN ('flow-1', 'flow-2', 'flow-5')")
        result = _account(conn)
        assert result['status'] == 'incomplete'
        assert 'flow-4' in result['excluded_observation_ids']
        assert result['residual'] is None
        assert 'covered movement outside covering flow: cover-1' in result['uncertainty']
    finally:
        conn.close()


def test_pending_observation_correction_does_not_erase_accepted_flow():
    conn = _fixture()
    try:
        _add(conn, 'observations', observation_id='flow-5-pending',
             subject_kind='agreement', subject_id='agreement-1', measure='flow',
             flow_type='commitment', basis='gross', value=8, currency='USD',
             line_id='pending', method='review', recorded_at='2026-04-02',
             status='candidate', supersedes='flow-5')
        _add(conn, 'timings', timing_id='pending-time', observation_id='flow-5-pending',
             date_role='event', date='2026-02-01', date_precision='day',
             recorded_at='2026-04-02')
        result = _account(conn)
        assert result['status'] == 'exact'
        assert Decimal(result['documented_subtotal']) == 15
    finally:
        conn.close()


def _relayout(database, page_size):
    """Rewrite a SQLite file with another page size and reversed row order.

    Same content, different bytes: the layout a VACUUM INTO of another SQLite
    version would produce is not reproducible on demand, but any layout change
    stands in for it.
    """
    source = sqlite3.connect(database)
    statements = list(source.iterdump())
    source.close()
    head = [s for s in statements if not s.startswith('INSERT')]
    inserts = [s for s in statements if s.startswith('INSERT')]
    alternate = Path(str(database) + '.alt')
    alternate.unlink(missing_ok=True)
    target = sqlite3.connect(alternate)
    target.execute(f'PRAGMA page_size = {page_size}')
    target.executescript('\n'.join(head[:-1] + inserts[::-1] + head[-1:]))
    target.close()
    alternate.replace(database)


def test_ledger_digest_is_independent_of_the_sqlite_file_layout(tmp_path, monkeypatch):
    """Ticket 1545: the same ledger written two ways has one ledger_sha256."""
    ledger_dir = tmp_path / 'ledger'
    _write(ledger_dir, _valid_tables())
    raw = {}

    def relaid(ledger_dir, database, page_size):
        errors = ledger_build.build(ledger_dir, database)
        if not errors:
            _relayout(database, page_size)
            raw[page_size] = hashlib.sha256(Path(database).read_bytes()).hexdigest()
        return errors

    digests = {}
    for page_size in (1024, 8192):
        monkeypatch.setattr(module, 'build_ledger',
                            lambda d, db, p=page_size: relaid(d, db, p))
        digests[page_size] = module.build(ledger_dir, '2026-09-23')
    assert raw[1024] != raw[8192], 'control: the two files must differ byte-wise'
    assert digests[1024]['ledger_sha256'] == digests[8192]['ledger_sha256']
    assert digests[1024]['run_id'] == digests[8192]['run_id']


def test_one_cell_change_moves_the_ledger_digest(tmp_path):
    before, after = _valid_tables(), _valid_tables()
    after['lines'][0]['locator'] = 'p1 r3'
    digests = []
    for name, tables in (('before', before), ('after', after)):
        _write(tmp_path / name, tables)
        digests.append(build(tmp_path / name, '2026-09-23')['ledger_sha256'])
    assert digests[0] != digests[1]


def test_ledger_digest_encoding_separates_storage_classes():
    """NULL, '', 1, 1.0 and '1' are different cells, so different digests."""
    def digest_of(value):
        conn = sqlite3.connect(':memory:')
        conn.execute('CREATE TABLE t (k INTEGER PRIMARY KEY, v)')
        conn.execute('INSERT INTO t VALUES (1, ?)', (value,))
        try:
            return content_digest(conn)
        finally:
            conn.close()

    seen = [digest_of(value) for value in (None, '', 1, 1.0, '1', b'1', 'N', 'I1')]
    assert len(set(seen)) == len(seen)


@pytest.fixture(scope='session')
def real_ledger_build():
    """One build of the committed ledger per session (per xdist worker).

    Validating the real ledger takes about three minutes, so the tests that
    read this fixture are marked slow: they run in the JETP gate and the full
    check, not in the fast inner loop.
    """
    return build(ROOT / 'data/jetp')


@pytest.mark.slow
def test_committed_accounts_view_matches_a_rebuild(real_ledger_build):
    """The served accounts.json is the ledger's: a rebuild reproduces it byte for byte.

    Every field derives from committed inputs (the ledger CSVs, the ontology
    tables and config/jetp_observatory.yaml): none depends on the git
    revision, the clock or the machine, so the comparison is exact. It is
    also the determinism check: the served file is an earlier, independent
    build, on another day and possibly another machine.
    """
    served = (ROOT / 'deliverables/jetp-observatory/data/accounts.json').read_text(encoding='utf-8')
    rebuilt = json.dumps(real_ledger_build, sort_keys=True, separators=(',', ':')) + '\n'
    assert rebuilt == served


@pytest.mark.slow
def test_real_ledger_has_no_admitted_commitment_flow(real_ledger_build):
    assert real_ledger_build['accounts'] == []
    assert real_ledger_build['availability']
    assert real_ledger_build['ontology_ref'].startswith('sha256:')
    assert re.fullmatch(r'[0-9a-f]{64}', real_ledger_build['ledger_sha256'])


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
