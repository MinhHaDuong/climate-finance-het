"""Derive bounded original-currency gross commitment accounts from the v2 ledger.

The CSV ledger remains authoritative. This builder validates it through the
0871 SQLite DDL, then writes one deterministic JSON result. Without reviewed
coverage and exact opening/closing positions it reports a subtotal and gaps,
never an exact closing value or a residual.
"""

import argparse
import hashlib
import json
import sqlite3
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from jetp._ledger_headers import LEDGER_DIR, load_schema, read_table
from jetp._ontology import ontology_ref
from jetp.build_ledger import build as build_ledger

ROOT = Path(__file__).resolve().parents[2]
METRIC = 'gross_commitment_original_currency_v1'
POLICY_VERSION = '1'


def _rows(conn, table):
    return [dict(row) for row in conn.execute(f'SELECT * FROM {table}')]


def _current(rows, key, cutoff, time_field='recorded_at', review_field=None,
             superseding_statuses=('accepted', 'rejected', 'withdrawn')):
    known = [r for r in rows if r[time_field] <= cutoff
             and (review_field is None or r[review_field] <= cutoff)]
    superseded = {r['supersedes'] for r in known
                  if r['supersedes'] and r['status'] in superseding_statuses}
    return [r for r in known if r['status'] == 'accepted' and r[key] not in superseded]


def _amount(row, raw_values=None):
    try:
        raw = (raw_values or {}).get(row['observation_id'], {})
        value = Decimal(raw.get('value') if raw.get('value') is not None
                        else str(row['value']))
        low = raw.get('value_low', row['value_low'])
        high = raw.get('value_high', row['value_high'])
        low = Decimal(str(low)) if low not in (None, '') else None
        high = Decimal(str(high)) if high not in (None, '') else None
    except (InvalidOperation, TypeError):
        return None
    if (not value.is_finite() or value < 0
            or (not raw and value > 2**53)
            or ((low is None) != (high is None))
            or (low is not None and (low != value or high != value))):
        return None
    return value


def _exact_date(timings, observation_id, role, knowledge_cutoff):
    dates = [r for r in timings if r['observation_id'] == observation_id
             and r['date_role'] == role and r['recorded_at'] <= knowledge_cutoff
             and r['date_precision'] == 'day' and r['date']
             and (r['lower_bound'] is None or r['lower_bound'] == r['date'])
             and (r['upper_bound'] is None or r['upper_bound'] == r['date'])]
    return dates[0]['date'] if len(dates) == 1 else None


def _flow_interval(timings, observation_id, knowledge_cutoff):
    event = _exact_date(timings, observation_id, 'event', knowledge_cutoff)
    start = _exact_date(timings, observation_id, 'period_start', knowledge_cutoff)
    end = _exact_date(timings, observation_id, 'period_end', knowledge_cutoff)
    if event and not start and not end:
        return event, event
    if start and end and start <= end and not event:
        return start, end
    return None


def _members(members, decision_id, role):
    return {r['id'] for r in members if r['adjudication_id'] == decision_id
            and r['kind'] == 'observation' and r['role'] == role}


def _occurrence_exclusions(decisions, members, known_ids, knowledge_cutoff):
    """A rejected terminal ruling makes its entire known group unresolved."""
    relevant = {r['adjudication_id']: r for r in decisions
                if r['decision_type'] == 'occurrence_membership'
                and r['recorded_at'] <= knowledge_cutoff
                and r['decided_at'] <= knowledge_cutoff
                and r['status'] in ('accepted', 'rejected', 'withdrawn')}
    children = {r['supersedes']: r['adjudication_id'] for r in relevant.values()
                if r['supersedes'] in relevant}
    excluded, reasons, used = set(), [], []
    for root in relevant.values():
        if root['supersedes'] in relevant:
            continue
        historical_group = set()
        decision = root
        while True:
            historical_group.update(_members(members, decision['adjudication_id'], 'occurrence'))
            child = children.get(decision['adjudication_id'])
            if not child:
                break
            decision = relevant[child]
        if not historical_group & known_ids:
            continue
        if decision['status'] == 'accepted':
            terminal_group = _members(members, decision['adjudication_id'], 'occurrence')
            if decision['subject_id'] not in terminal_group or not terminal_group <= known_ids:
                excluded.update(terminal_group & known_ids)
                reasons.append(f'occurrence crosses account: {decision["adjudication_id"]}')
            else:
                excluded.update(terminal_group - {decision['subject_id']})
                used.append(decision['adjudication_id'])
        else:
            excluded.update(historical_group)
            reasons.append(f'occurrence unresolved: {decision["adjudication_id"]}')
    return excluded, reasons, used


def _positions(observations, timings, members, decision, agreement_id, currency,
               valid_cutoff, knowledge_cutoff, raw_values):
    positions = {r['observation_id']: r for r in
                 _current(observations, 'observation_id', knowledge_cutoff)}
    reported, reasons = [], []
    opening = closing = None
    for role in ('opening', 'closing'):
        ids = _members(members, decision['adjudication_id'], role)
        candidate = positions.get(next(iter(ids))) if len(ids) == 1 else None
        value = _amount(candidate, raw_values) if candidate else None
        day = (_exact_date(timings, candidate['observation_id'], 'reporting_cutoff',
                           knowledge_cutoff) if candidate else None)
        valid = candidate and candidate['subject_kind'] == 'agreement' and \
            candidate['subject_id'] == agreement_id and candidate['measure'] == 'amount' and \
            candidate['basis'] == 'gross' and candidate['currency'] == currency and value is not None
        if not valid or day is None or (role == 'closing' and day != valid_cutoff):
            reasons.append(f'exact {role} unavailable')
            continue
        position = {'observation_id': candidate['observation_id'],
                    'value': str(value), 'date': day}
        reported.append(position)
        if role == 'opening':
            opening = (value, day)
        else:
            closing = value
    return opening, closing, reported, reasons


def _eligible_intervals(observations, timings, agreement_id, currency,
                        valid_cutoff, knowledge_cutoff, raw_values):
    eligible = [r for r in _current(observations, 'observation_id', knowledge_cutoff)
                if r['subject_kind'] == 'agreement' and r['subject_id'] == agreement_id
                and r['measure'] == 'flow' and r['flow_type'] == 'commitment'
                and r['basis'] == 'gross' and r['currency'] == currency]
    dated, reasons = [], []
    for row in eligible:
        interval = _flow_interval(timings, row['observation_id'], knowledge_cutoff)
        amount = _amount(row, raw_values)
        if interval is None or amount is None:
            reasons.append(f'inexact flow: {row["observation_id"]}')
        elif interval[0] <= valid_cutoff:
            if interval[1] > valid_cutoff:
                reasons.append(f'flow overlaps cutoff: {row["observation_id"]}')
            else:
                dated.append((row, interval, amount))
    return eligible, dated, reasons


def _membership_reasons(conn, agreement_id, perimeter_id, opening, valid_cutoff,
                        knowledge_cutoff):
    relation_rows = _current(_rows(conn, 'relations'), 'relation_id', knowledge_cutoff,
                             'decided_at')
    reasons = []
    if not any(r['from_kind'] == 'agreement' and r['from_id'] == agreement_id
               and r['relation'] == 'member_of' and r['to_kind'] == 'perimeter'
               and r['to_id'] == perimeter_id and opening is not None
               and (r['valid_from'] is None or r['valid_from'] <= opening[1])
               and (r['valid_to'] is None or valid_cutoff <= r['valid_to'])
               for r in relation_rows):
        reasons.append('agreement perimeter membership unreviewed')
    if not any(r['perimeter_id'] == perimeter_id for r in
               _current(_rows(conn, 'perimeters'), 'perimeter_row_id', knowledge_cutoff)):
        reasons.append('perimeter unavailable')
    return reasons


def _interval_rows(dated, opening, valid_cutoff):
    rows, reasons = [], []
    if opening is not None and opening[1] < valid_cutoff:
        for row, interval, amount in dated:
            if interval[1] <= opening[1]:
                continue
            if interval[0] <= opening[1]:
                reasons.append(f'flow overlaps opening: {row["observation_id"]}')
            else:
                rows.append((row, interval, amount))
    return rows, reasons


def _reviewed_cover(coverage, members, eligible, dated, interval_ids):
    if not coverage:
        return set(), set(), [], []
    if len(coverage) != 1:
        return set(), set(), ['coverage decisions ambiguous'], []
    decision = coverage[0]
    covering = _members(members, decision['adjudication_id'], 'covering_flow')
    covered = _members(members, decision['adjudication_id'], 'covered_movement')
    eligible_ids = {row['observation_id'] for row in eligible}
    if not (covering and covered and covering | covered <= eligible_ids
            and not covering & covered):
        return set(), set(), [f'coverage members unavailable: {decision["adjudication_id"]}'], []
    intervals = {row['observation_id']: interval for row, interval, _ in dated}
    if any(not any(cover_id in interval_ids and cover_id in intervals
                   and intervals[cover_id][0] <= intervals[move_id][0]
                   and intervals[move_id][1] <= intervals[cover_id][1]
                   for cover_id in covering)
           for move_id in covered & interval_ids):
        return set(), set(), [f'covered movement outside covering flow: {decision["adjudication_id"]}'], []
    return (covering & interval_ids, covered & interval_ids, [],
            [decision['adjudication_id']])


def account_for(conn, agreement_id, perimeter_id, currency, valid_cutoff,
                knowledge_cutoff, raw_values=None):
    """One account. Selection and completeness require in-force decisions."""
    observations = _rows(conn, 'observations')
    timings = _rows(conn, 'timings')
    decisions = _rows(conn, 'adjudications')
    members = _rows(conn, 'adjudication_members')
    current = _current(decisions, 'adjudication_id', knowledge_cutoff,
                       review_field='decided_at',
                       superseding_statuses=('accepted', 'rejected', 'withdrawn'))
    eligible, dated, reasons = _eligible_intervals(
        observations, timings, agreement_id, currency, valid_cutoff,
        knowledge_cutoff, raw_values)
    coverage = [r for r in current if r['decision_type'] == 'flow_coverage'
                and r['subject_kind'] == 'agreement' and r['subject_id'] == agreement_id]
    complete = [r for r in coverage if r['verdict'] == 'complete']
    if len(complete) != 1:
        reasons.append('complete coverage not reviewed')
    position_decision = complete[0] if len(complete) == 1 else (coverage[0] if len(coverage) == 1 else None)
    reported = []
    opening = closing = None
    if position_decision:
        opening, closing, reported, position_reasons = _positions(
            observations, timings, members, position_decision, agreement_id, currency,
            valid_cutoff, knowledge_cutoff, raw_values)
        reasons += position_reasons
    if opening is None:
        reasons.append('verified opening unavailable')
    elif opening[1] >= valid_cutoff:
        reasons.append('opening outside reporting interval')
    reasons += _membership_reasons(conn, agreement_id, perimeter_id, opening,
                                   valid_cutoff, knowledge_cutoff)
    interval_rows, interval_reasons = _interval_rows(dated, opening, valid_cutoff)
    reasons += interval_reasons
    interval_ids = {row['observation_id'] for row, _, _ in interval_rows}
    excluded, occurrence_reasons, decision_ids = _occurrence_exclusions(
        decisions, members, interval_ids, knowledge_cutoff)
    reasons += occurrence_reasons
    reviewed_covering, covered, cover_reasons, cover_decisions = _reviewed_cover(
        coverage, members, eligible, dated, interval_ids)
    excluded.update(covered)
    reasons += cover_reasons
    decision_ids += cover_decisions
    unreviewed = interval_ids - excluded - reviewed_covering
    if unreviewed:
        reasons.append('unreviewed flows: ' + ', '.join(sorted(unreviewed)))
        excluded.update(unreviewed)
    if reviewed_covering & excluded:
        reasons.append('covering flow unresolved')
    included = [(row, interval, amount) for row, interval, amount in interval_rows
                if row['observation_id'] in reviewed_covering
                and row['observation_id'] not in excluded]
    subtotal = sum((amount for _, _, amount in included), Decimal(0))
    exact = not reasons and closing is not None
    reconstructed = opening[0] + subtotal if exact else None
    return {
        'agreement_id': agreement_id, 'perimeter_id': perimeter_id,
        'metric': METRIC, 'currency': currency,
        'valid_cutoff': valid_cutoff, 'knowledge_cutoff': knowledge_cutoff,
        'status': 'exact' if exact else 'incomplete',
        'reported_positions': reported,
        'included_observation_ids': sorted(r['observation_id'] for r, _, _ in included),
        'excluded_observation_ids': sorted(excluded),
        'decision_ids': sorted(set(decision_ids)),
        'documented_subtotal': str(subtotal),
        'reconstructed_closing': str(reconstructed) if exact else None,
        'residual': str(closing - reconstructed) if exact else None,
        'uncertainty': sorted(set(reasons)),
    }


def _latest_knowledge(conn, valid_cutoff):
    return conn.execute(
        "SELECT max(day) FROM ("
        "SELECT recorded_at AS day FROM observations UNION ALL "
        "SELECT recorded_at FROM timings UNION ALL "
        "SELECT recorded_at FROM perimeters UNION ALL "
        "SELECT recorded_at FROM adjudications UNION ALL "
        "SELECT decided_at FROM adjudications UNION ALL "
        "SELECT decided_at FROM relations)"
    ).fetchone()[0] or valid_cutoff


def build(ledger_dir=LEDGER_DIR, valid_cutoff=None, knowledge_cutoff=None):
    """Validate CSVs, derive available account requests, and pin both cutoffs."""
    if valid_cutoff is None:
        config = yaml.safe_load((ROOT / 'config/jetp_observatory.yaml').read_text())
        valid_cutoff = config['cutoff']
    schema = load_schema()
    raw_rows, raw_errors = read_table(ledger_dir, 'observations', schema)
    if raw_errors:
        raise ValueError('; '.join(raw_errors))
    columns = schema.header('observations')
    id_index = columns.index('observation_id')
    amount_columns = ('value', 'value_low', 'value_high')
    raw_values = {row[id_index]: {name: row[columns.index(name)] for name in amount_columns}
                  for row in raw_rows}
    with tempfile.TemporaryDirectory() as temporary:
        database = Path(temporary) / 'ledger.sqlite'
        errors = build_ledger(ledger_dir, database)
        if errors:
            raise ValueError('; '.join(errors))
        digest = hashlib.sha256(database.read_bytes()).hexdigest()
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        try:
            if knowledge_cutoff is None:
                knowledge_cutoff = _latest_knowledge(conn, valid_cutoff)
            flow_rows = conn.execute(
                "SELECT DISTINCT subject_id, currency FROM observations WHERE "
                "subject_kind='agreement' AND measure='flow' AND flow_type='commitment' "
                "AND basis='gross' AND status='accepted' AND recorded_at <= ?",
                (knowledge_cutoff,)).fetchall()
            accounts = []
            for agreement_id, currency in flow_rows:
                perimeters = conn.execute(
                    "SELECT DISTINCT to_id FROM relations WHERE from_kind='agreement' "
                    "AND from_id=? AND relation='member_of' AND to_kind='perimeter' "
                    "AND status='accepted'", (agreement_id,)).fetchall()
                for (perimeter_id,) in perimeters:
                    accounts.append(account_for(conn, agreement_id, perimeter_id, currency,
                                                valid_cutoff, knowledge_cutoff, raw_values))
        finally:
            conn.close()
    return {'run_id': hashlib.sha256(f'{digest}:{valid_cutoff}:{knowledge_cutoff}'.encode()).hexdigest()[:16],
            'ledger_sha256': digest, 'ontology_ref': ontology_ref(ledger_dir),
            'schema_version': 'jetp-ledger-v2', 'policy_version': POLICY_VERSION,
            'metric': METRIC, 'valid_cutoff': valid_cutoff,
            'knowledge_cutoff': knowledge_cutoff,
            'accounts': sorted(accounts, key=lambda a: (a['agreement_id'], a['perimeter_id'], a['currency'])),
            'availability': ('No exact gross commitment flow observations have been admitted.'
                             if not accounts else None)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER_DIR)
    parser.add_argument('--valid-cutoff')
    parser.add_argument('--knowledge-cutoff')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.ledger_dir, args.valid_cutoff, args.knowledge_cutoff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n',
                           encoding='utf-8')


if __name__ == '__main__':
    main()
