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


def _current(rows, key, cutoff, time_field='recorded_at'):
    known = [r for r in rows if r[time_field] <= cutoff]
    superseded = {r['supersedes'] for r in known if r['supersedes']}
    return [r for r in known if r['status'] == 'accepted' and r[key] not in superseded]


def _amount(row, raw_values=None):
    try:
        raw = (raw_values or {}).get(row['observation_id'])
        value = Decimal(raw if raw is not None else str(row['value']))
    except (InvalidOperation, TypeError):
        return None
    if (not value.is_finite() or value < 0
            or (raw is None and value > 2**53)
            or row['value_low'] is not None or row['value_high'] is not None):
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
                and r['recorded_at'] <= knowledge_cutoff}
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


def account_for(conn, agreement_id, perimeter_id, currency, valid_cutoff,
                knowledge_cutoff, raw_values=None):
    """One account. Selection and completeness require in-force decisions."""
    observations = _rows(conn, 'observations')
    timings = _rows(conn, 'timings')
    decisions = _rows(conn, 'adjudications')
    members = _rows(conn, 'adjudication_members')
    current = _current(decisions, 'adjudication_id', knowledge_cutoff)
    eligible = [r for r in _current(observations, 'observation_id', knowledge_cutoff)
                if r['subject_kind'] == 'agreement' and r['subject_id'] == agreement_id
                and r['measure'] == 'flow' and r['flow_type'] == 'commitment'
                and r['basis'] == 'gross' and r['currency'] == currency]
    reasons = []
    dated = []
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
    relation_rows = _current(_rows(conn, 'relations'), 'relation_id', knowledge_cutoff,
                             'decided_at')
    if not any(r['from_kind'] == 'agreement' and r['from_id'] == agreement_id
               and r['relation'] == 'member_of' and r['to_kind'] == 'perimeter'
               and r['to_id'] == perimeter_id
               and (r['valid_from'] is None or r['valid_from'] <= valid_cutoff)
               and (r['valid_to'] is None or valid_cutoff <= r['valid_to'])
               for r in relation_rows):
        reasons.append('agreement perimeter membership unreviewed')
    if not any(r['perimeter_id'] == perimeter_id for r in
               _current(_rows(conn, 'perimeters'), 'perimeter_row_id', knowledge_cutoff)):
        reasons.append('perimeter unavailable')

    excluded, occurrence_reasons, decision_ids = _occurrence_exclusions(
        decisions, members, {r['observation_id'] for r, _, _ in dated}, knowledge_cutoff)
    reasons += occurrence_reasons

    coverage = [r for r in current if r['decision_type'] == 'flow_coverage'
                and r['subject_kind'] == 'agreement' and r['subject_id'] == agreement_id]
    complete = [r for r in coverage if r['verdict'] == 'complete']
    if len(complete) != 1:
        reasons.append('complete coverage not reviewed')
    for decision in coverage:
        covering = _members(members, decision['adjudication_id'], 'covering_flow')
        covered = _members(members, decision['adjudication_id'], 'covered_movement')
        dated_ids = {row['observation_id'] for row, _, _ in dated}
        if covering and covered and covering | covered <= dated_ids and not covering & covered:
            excluded.update(covered)
            decision_ids.append(decision['adjudication_id'])
        elif covering or covered:
            reasons.append(f'coverage members unavailable: {decision["adjudication_id"]}')
    included = [(row, day, amount) for row, day, amount in dated
                if row['observation_id'] not in excluded]
    subtotal = sum((amount for _, _, amount in included), Decimal(0))
    reported = []
    opening = closing = None
    if complete:
        opening, closing, reported, position_reasons = _positions(
            observations, timings, members, complete[0], agreement_id, currency,
            valid_cutoff, knowledge_cutoff, raw_values)
        reasons += position_reasons
    if opening is None:
        reasons.append('verified opening unavailable')
    elif opening[1] >= valid_cutoff:
        reasons.append('opening outside reporting interval')
    elif any(interval[0] <= opening[1] for _, interval, _ in included):
        reasons.append('movement outside opening interval')
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
    id_index, value_index = columns.index('observation_id'), columns.index('value')
    raw_values = {row[id_index]: row[value_index] for row in raw_rows}
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
                knowledge_cutoff = conn.execute(
                    "SELECT max(recorded_at) FROM observations").fetchone()[0] or valid_cutoff
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
