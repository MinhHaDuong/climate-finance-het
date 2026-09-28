"""Adjudication members, typed references and defeasible decisions (0889)."""

import csv
import sqlite3

import pytest
from jetp._ledger_headers import load_schema, table_path
from jetp.build_ledger import build

pytestmark = pytest.mark.wp_jetp
SHA = 'a' * 64


def _term(value, list_name):
    return dict(term_row_id=f'{list_name}.{value}.1', term_id=value, kind='value',
                list=list_name, label=value, definition=value,
                mapping_relation='local', recorded_at='2026-01-01',
                decided_by='fixture', status='accepted')


def _decision(identity, decision_type, subject_kind, subject_id, verdict='accepted',
              status='accepted', supersedes=None, date='2026-02-01'):
    return dict(adjudication_id=identity, decision_type=decision_type,
                subject_kind=subject_kind, subject_id=subject_id, verdict=verdict,
                status=status, decided_at=date, decided_by='reviewer:fixture',
                recorded_at=date, supersedes=supersedes, notes='Fixture review')


def _member(decision, kind, identity, role):
    return dict(adjudication_id=decision, kind=kind, id=identity, role=role)


def _tables():
    terms = [_term(v, 'class') for v in ('line', 'observation', 'perimeter')]
    terms += [_term(v, 'decision_type') for v in (
        'occurrence_membership', 'flow_coverage', 'perimeter_compatibility',
        'identity')]
    terms += [_term(v, 'decision_status') for v in ('accepted', 'rejected', 'candidate')]
    terms += [_term('named_item', 'line_classification'),
              _term('flow', 'measure'), _term('commitment', 'flow_type'),
              _term('event', 'date_role'), _term('collected', 'retrieval_status')]
    terms += [_term(v, 'adjudication_role') for v in (
        'candidate', 'accepted', 'excluded', 'occurrence', 'covering_flow',
        'covered_movement', 'opening', 'closing', 'context')]
    observations = [dict(observation_id=f'flow-{n}', subject_kind='line',
                         subject_id=f'line-{n}', measure='flow',
                         flow_type='commitment', value='10', unit='USD',
                         currency='USD', line_id=f'line-{n}', method='fixture',
                         recorded_at='2026-01-01', status='accepted')
                    for n in (1, 2, 3)]
    return {
        'terms': terms,
        'documents': [dict(document_id='doc-1', title='Fixture')],
        'snapshots': [dict(sha256=SHA, storage_path='fixture', size_bytes='1')],
        'retrievals': [dict(retrieval_id='ret-1', document_id='doc-1',
                            retrieved_at='2026-01-01', status='collected',
                            sha256=SHA, collection_method='script')],
        'lines': [dict(line_id=f'line-{n}', country='ZAF', sha256=SHA,
                       locator=f'p1 r{n}', ordinal=str(n),
                       classification='named_item', recorded_at='2026-01-01')
                  for n in (1, 2, 3)],
        'observations': observations,
        'timings': [dict(timing_id=f'time-{n}', observation_id=f'flow-{n}',
                         date_role='event', date='2026-01-01',
                         recorded_at='2026-01-01') for n in (1, 2, 3)],
        'perimeters': [dict(perimeter_row_id='scope.1', perimeter_id='scope',
                            name='Fixture scope', definition='Fixture scope',
                            recorded_at='2026-01-01', decided_by='fixture',
                            status='accepted')],
        'adjudications': [
            _decision('same-payment', 'occurrence_membership', 'observation', 'flow-1'),
            _decision('outside-cover', 'flow_coverage', 'observation', 'flow-3',
                      verdict='excluded', status='rejected'),
            _decision('scope-compatible', 'perimeter_compatibility', 'perimeter',
                      'scope'),
            _decision('same-identity', 'identity', 'line', 'line-1'),
        ],
        'adjudication_members': [
            _member('same-payment', 'observation', 'flow-1', 'occurrence'),
            _member('same-payment', 'observation', 'flow-2', 'occurrence'),
            _member('outside-cover', 'observation', 'flow-3', 'excluded'),
            _member('scope-compatible', 'perimeter', 'scope', 'context'),
            _member('same-identity', 'line', 'line-2', 'candidate'),
        ],
    }


def _write(directory, tables):
    schema = load_schema()
    for table, rows in tables.items():
        path = table_path(directory, table)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=schema.header(table),
                                    lineterminator='\n', extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)


def test_four_types_members_and_history(tmp_path):
    tables = _tables()
    _write(tmp_path, tables)
    database = tmp_path / 'ledger.sqlite'
    assert build(tmp_path, database) == []
    with sqlite3.connect(database) as conn:
        assert conn.execute('SELECT count(*) FROM adjudications').fetchone()[0] == 4
        assert conn.execute('SELECT count(*) FROM adjudication_members').fetchone()[0] == 5
        assert conn.execute('SELECT count(*) FROM adjudications_in_force').fetchone()[0] == 3
        assert conn.execute('SELECT count(*) FROM adjudication_members_in_force').fetchone()[0] == 4


def test_missing_perimeter_is_refused(tmp_path):
    tables = _tables()
    tables['adjudications'][2]['subject_id'] = 'missing-scope'
    _write(tmp_path, tables)
    assert any("perimeter 'missing-scope' does not exist" in error
               for error in build(tmp_path))


def test_superseding_rejection_revokes_without_erasing_history(tmp_path):
    tables = _tables()
    tables['adjudications'].append(_decision(
        'same-payment-revoked', 'occurrence_membership', 'observation',
        'flow-1', verdict='rejected', status='rejected',
        supersedes='same-payment', date='2026-03-01'))
    tables['adjudication_members'].append(
        _member('same-payment-revoked', 'observation', 'flow-2', 'excluded'))
    _write(tmp_path, tables)
    database = tmp_path / 'ledger.sqlite'
    assert build(tmp_path, database) == []
    with sqlite3.connect(database) as conn:
        assert conn.execute('SELECT count(*) FROM adjudications WHERE '
                            "adjudication_id LIKE 'same-payment%'").fetchone()[0] == 2
        assert conn.execute('SELECT count(*) FROM adjudications_in_force WHERE '
                            "adjudication_id LIKE 'same-payment%'").fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM adjudication_members_in_force WHERE '
                            "adjudication_id LIKE 'same-payment%'").fetchone()[0] == 0


@pytest.mark.parametrize('change,needle', [
    (lambda t: t['adjudication_members'].pop(), 'no typed members'),
    (lambda t: t['adjudications'][0].update(decision_type='unknown'),
     'not a term in force'),
    (lambda t: t['adjudication_members'][0].update(id='absent'), 'does not exist'),
    (lambda t: t['adjudication_members'][0].update(role='opening'),
     'is not valid for occurrence_membership'),
    (lambda t: (t['adjudications'][2].update(subject_kind='line', subject_id='line-1'),
                t['adjudication_members'][3].update(kind='line', id='line-1')),
     'names no perimeter'),
])
def test_invalid_decisions_are_refused(tmp_path, change, needle):
    tables = _tables()
    change(tables)
    _write(tmp_path, tables)
    assert any(needle in error for error in build(tmp_path))


def test_supersession_cannot_change_the_question(tmp_path):
    tables = _tables()
    tables['adjudications'].append(_decision(
        'different-question', 'identity', 'line', 'line-1',
        supersedes='same-payment', date='2026-03-01'))
    tables['adjudication_members'].append(
        _member('different-question', 'line', 'line-2', 'candidate'))
    _write(tmp_path, tables)
    assert any('of another question' in error for error in build(tmp_path))


def test_supersession_cycle_is_refused(tmp_path):
    tables = _tables()
    first = tables['adjudications'][0]
    first['supersedes'] = 'same-payment-revision'
    tables['adjudications'].append(_decision(
        'same-payment-revision', 'occurrence_membership', 'observation',
        'flow-1', supersedes='same-payment'))
    tables['adjudication_members'].append(
        _member('same-payment-revision', 'observation', 'flow-2', 'occurrence'))
    _write(tmp_path, tables)
    assert any('supersession cycle' in error for error in build(tmp_path))


def test_separator_inside_id_is_not_a_cycle(tmp_path):
    tables = _tables()
    tables['adjudications'][0]['adjudication_id'] = 'b'
    for member in tables['adjudication_members'][:2]:
        member['adjudication_id'] = 'b'
    tables['adjudications'].append(_decision(
        'a|b', 'occurrence_membership', 'observation', 'flow-1',
        supersedes='b'))
    tables['adjudication_members'] += [
        _member('a|b', 'observation', 'flow-1', 'occurrence'),
        _member('a|b', 'observation', 'flow-2', 'occurrence')]
    _write(tmp_path, tables)
    assert build(tmp_path) == []


def test_accepted_decisions_need_usable_member_sets(tmp_path):
    tables = _tables()
    tables['adjudication_members'] = [
        row for row in tables['adjudication_members']
        if not (row['adjudication_id'] == 'same-payment' and row['id'] == 'flow-2')]
    _write(tmp_path / 'one', tables)
    assert any('needs two occurrence observations' in error
               for error in build(tmp_path / 'one'))
    tables = _tables()
    tables['adjudications'][1]['status'] = 'accepted'
    _write(tmp_path / 'two', tables)
    assert any('needs covering_flow and covered_movement' in error
               for error in build(tmp_path / 'two'))
