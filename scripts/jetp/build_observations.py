"""Build the per-country ledger observation views for the observatory.

The second stage-two product.  The M1a inventories freeze what a source
published about its own projects; these are the ledger rows analysts wrote from
those same documents, under a different schema.  Two extractions, served side
by side and never added together: a row here and a row there can describe the
same paragraph of the same PDF.

One invocation writes all four countries, like the M1a writer and unlike the
single ``--view`` of ``build_observatory.py``: the four files share one pass
over the three tables and one collection registry.
"""

import argparse
import csv
import json
from pathlib import Path

from jetp._ledger_headers import load_schema, write_table
from jetp._observatory_data import observation_entry

ROOT = Path(__file__).resolve().parents[2]
COUNTRIES = ('ZAF', 'IDN', 'VNM', 'SEN')
# Fixed order, and it is the served order: table, then the CSV's own row order.
# No further sort, so a regeneration is readable as a diff and a row keeps the
# position its ledger gives it.
OBSERVATION_TABLES = ('events', 'implementation-events', 'project-source-links')
RECORDED_AT = '2026-09-24'

# The old date ledger used a wider vocabulary while dates were still an
# attribute of events.  These are deliberately translations of date *roles*,
# not assertions that an unknown legacy date became an event date.
TIMING_ROLES = {
    'register': 'register_date',
    'reporting_cutoff': 'reporting_cutoff',
    'planned': 'planned',
    'publication': 'report_date',
    'event': 'event',
}


def attempt_rank(row):
    """Order collection attempts by what each can address, never by disk state.

    An attempt that recorded no digest cannot address a document at all; among
    those that did, a completed collection outranks a revalidation, and a later
    retrieval outranks an earlier one.  The digest closes the order: two
    attempts alike on every other term still resolve the same way whatever
    order ``manifest.csv`` lists them in, which is the whole point of ranking
    rather than keeping the last row seen.
    """
    digest = row.get('sha256') or ''
    if not digest:
        return (0, row.get('retrieved_at') or '', '')
    return (
        2 if row.get('status') == 'collected' else 1,
        row.get('retrieved_at') or '',
        digest,
    )


def build_registry(tables):
    """Collapse the collection registry to one attempt per source identifier.

    Twenty-one identifiers carry several attempts (ticket 0853) and six of them
    disagree on the digest, so the choice has to be made rather than left to the
    order of ``manifest.csv``.

    It is made on the digest, not on what happens to be staged on disk.  What
    this view publishes is a fingerprint; the local path is the renderer's
    business, resolved from ``data/documents.json`` in the browser.  Ranking on
    an archived copy — as ``index_documents`` does, correctly, for a page whose
    job is to open a file — would make the published value depend on whether
    the DVC snapshot happened to be checked out when the build ran, and one
    Senegal source did flip that way during this ticket's own development.
    """
    chosen = {}
    for row in tables['manifest']:
        source_id = row['source_id']
        if source_id not in chosen or attempt_rank(row) > attempt_rank(chosen[source_id]):
            chosen[source_id] = row
    return {
        source_id: {'sha256': row['sha256'] or None}
        for source_id, row in chosen.items()
    }


def country_observations(tables, registry, code):
    """One country's ledger rows, in served order: table, then the CSV's own.

    The same rows the country's observations view serves, so a fact's evidence
    (ticket 0839) and the Observations tab (ticket 0838) are one reading of the
    ledger, not two.
    """
    return [
        observation_entry(row, table, registry)
        for table in OBSERVATION_TABLES
        for row in tables[table]
        if row['country'] == code
    ]


def observations_by_country(tables, registry):
    """Group every ledger row under the country its own row names.

    A country with no row in a table gets an empty list, not a missing key: the
    absence is a fact about the ledger — Viet Nam has only link rows, and
    neither Viet Nam nor South Africa has an implementation event — and a view
    that dropped it would make the page unreachable for that country.
    """
    for table in OBSERVATION_TABLES:
        for row in tables[table]:
            if row['country'] not in COUNTRIES:
                raise ValueError(f"Unsupported observation country: {row['country']}")
    return {code: country_observations(tables, registry, code) for code in COUNTRIES}


def append_event_timings(event_id, observation_id, line_id, source_rows, timings, pending):
    """Translate supported dates while preserving unmapped source roles."""
    for ordinal, row in enumerate(source_rows, start=1):
        role = TIMING_ROLES.get(row['date_role'])
        if role is None:
            pending.append({
                'legacy_table': 'event-timing', 'legacy_event_id': event_id,
                'legacy_project_id': '', 'source_id': '', 'locator': '',
                'reason': f"unmapped_date_role_{row['date_role']}",
            })
            continue
        if role in ('register_date', 'report_date'):
            day = row['reported_on']
            precision, lower, upper = 'day', day, day
        elif role == 'reporting_cutoff':
            day = row['observed_on']
            precision, lower, upper = 'day', day, day
        else:
            lower, upper = row['event_start'], row['event_end']
            precision = row['event_precision']
            day = lower if precision == 'day' and lower == upper else ''
        if not lower or not upper:
            raise ValueError(f'{event_id}: {role} has no supported date bounds')
        timings.append({
            'timing_id': f'timing-{event_id}-{ordinal}',
            'observation_id': observation_id,
            'date_role': role,
            'date': day or None,
            'date_precision': precision,
            'lower_bound': lower,
            'upper_bound': upper,
            'line_id': line_id,
            'recorded_at': RECORDED_AT,
        })
        if role == 'reporting_cutoff' and row['event_start']:
            if not row['event_end'] or row['event_precision'] != 'year':
                raise ValueError(f'{event_id}: approval year lacks bounds')
            timings.append({
                'timing_id': f'timing-{event_id}-{ordinal}-approval',
                'observation_id': observation_id,
                'date_role': 'approval',
                'date': None,
                'date_precision': 'year',
                'lower_bound': row['event_start'],
                'upper_bound': row['event_end'],
                'line_id': line_id,
                'recorded_at': RECORDED_AT,
            })


def normalize_event_tables(events, implementation_events, event_timings, dispositions):
    """Return the valid v2 event observations, timings, and explicit gaps.

    A legacy event can enter v2 only when ticket 0875 resolved both its subject
    and the line that supports it.  In particular, an event whose source was
    blocked has no line to cite; keeping it in ``pending`` is evidence
    preservation, whereas borrowing a line from another document would invent
    a citation.  The caller writes that pending register beside the tables.
    """
    disposition_by_old_id = {row['old_id']: row for row in dispositions}
    timing_by_event = {}
    for row in event_timings:
        timing_by_event.setdefault(row['event_id'], []).append(row)

    observations, timings, pending = [], [], []

    def append_pending(row, event_id, table, reason):
        pending.append({
            'legacy_table': table,
            'legacy_event_id': event_id,
            'legacy_project_id': row['project_id'],
            'source_id': row['source_id'],
            'locator': row['locator'],
            'reason': reason,
        })

    def target(row, event_id, table):
        disposition = disposition_by_old_id.get(row['project_id'])
        if disposition is None:
            append_pending(row, event_id, table, 'no_0875_disposition')
            return None
        if not disposition['new_id'] or not disposition['line_id']:
            append_pending(row, event_id, table, 'no_resolved_subject_and_cited_line')
            return None
        return disposition

    for row in events:
        event_id = row['event_id']
        disposition = target(row, event_id, 'events')
        if disposition is None:
            continue
        observation_id = f'observation-{event_id}'
        measure = 'estimate' if row['financial_status'] == 'need' else 'amount'
        subject_kind, subject_id = disposition['disposition'], disposition['new_id']
        if row['financial_status'] == 'need':
            subject_kind, subject_id = 'line', disposition['line_id']
        observations.append({
            'observation_id': observation_id,
            'subject_kind': subject_kind,
            'subject_id': subject_id,
            'axis': 'money',
            'measure': measure,
            'flow_type': None,
            'basis': 'unknown',
            'value': row['amount_original'] or None,
            'value_low': None,
            'value_high': None,
            'unit': row['currency_original'] or None,
            'currency': row['currency_original'] or None,
            'own_status': row['financial_status'],
            'indicator_code': None,
            'line_id': disposition['line_id'],
            'method': 'legacy_event',
            'method_version': '1',
            'recorded_at': RECORDED_AT,
            'status': 'accepted',
            'supersedes': None,
            'notes': f"Legacy event {event_id}; source={row['source_id']}; locator={row['locator']}",
        })
        append_event_timings(event_id, observation_id, disposition['line_id'],
                             timing_by_event.get(event_id, ()), timings, pending)

    for row in implementation_events:
        event_id = row['implementation_event_id']
        disposition = target(row, event_id, 'implementation-events')
        if disposition is None:
            continue
        observation_id = f'observation-{event_id}'
        observations.append({
            'observation_id': observation_id,
            'subject_kind': disposition['disposition'],
            'subject_id': disposition['new_id'],
            'axis': 'asset_state' if disposition['disposition'] == 'asset' else 'delivery',
            'measure': 'state',
            'flow_type': None,
            'basis': None,
            'value': row['capacity_mw'] or None,
            'value_low': None,
            'value_high': None,
            'unit': 'MW' if row['capacity_mw'] else None,
            'currency': None,
            'own_status': row['implementation_status'],
            'indicator_code': None,
            'line_id': disposition['line_id'],
            'method': 'legacy_implementation_event',
            'method_version': '1',
            'recorded_at': RECORDED_AT,
            'status': 'accepted',
            'supersedes': None,
            'notes': f"Legacy implementation event {event_id}; source={row['source_id']}; locator={row['locator']}",
        })
        append_event_timings(event_id, observation_id, disposition['line_id'],
                             timing_by_event.get(event_id, ()), timings, pending)
    return observations, timings, pending


def reconcile_timing_rows(event_timings, observations, timings, pending):
    """Account for every legacy timing row without assigning an unsupported role."""
    accepted = {row['timing_id'] for row in timings}
    observed = {row['observation_id'] for row in observations}
    event_gaps = {row['legacy_event_id']: row['reason'] for row in pending
                  if row['legacy_table'] != 'event-timing'}
    ordinals = {}
    reconciliation = []
    for source_row, row in enumerate(event_timings, start=2):
        event_id = row['event_id']
        ordinal = ordinals.get(event_id, 0) + 1
        ordinals[event_id] = ordinal
        timing_id = f'timing-{event_id}-{ordinal}'
        approval_id = f'{timing_id}-approval'
        if timing_id in accepted:
            outcome, reason = 'typed_timing', ''
            if row['date_role'] == 'reporting_cutoff' and row['event_start']:
                if approval_id not in accepted:
                    raise ValueError(f'{event_id}: approval-year timing missing')
            else:
                approval_id = ''
        elif f'observation-{event_id}' not in observed:
            outcome, reason = 'pending', event_gaps.get(event_id, 'no_observation')
            approval_id = ''
        elif row['date_role'] not in TIMING_ROLES:
            outcome, reason = 'pending', f"unmapped_date_role_{row['date_role']}"
            approval_id = ''
        else:
            raise ValueError(f'{event_id}: supported timing row has no output')
        reconciliation.append({
            'legacy_row_number': source_row,
            'legacy_event_id': event_id,
            'legacy_date_role': row['date_role'],
            'outcome': outcome,
            'timing_id': timing_id if outcome == 'typed_timing' else '',
            'approval_timing_id': approval_id,
            'reason': reason,
        })
    return reconciliation


def write_normalized_event_tables(ledger_dir, events, implementation_events, event_timings):
    """Write v2 event tables and their evidence-gap register to ``ledger_dir``."""
    ledger_dir = Path(ledger_dir)
    with (ledger_dir / 'migration' / '0875-dispositions.csv').open(
            encoding='utf-8', newline='') as handle:
        dispositions = list(csv.DictReader(handle))
    observations, timings, pending = normalize_event_tables(
        events, implementation_events, event_timings, dispositions)
    # A blocked retrieval is an acquisition gap; a collected document with no
    # resolved event line needs line-level review.  Keep those remedies apart.
    with (ledger_dir / 'retrievals.csv').open(encoding='utf-8', newline='') as handle:
        retrievals = list(csv.DictReader(handle))
    retrieved = {}
    for row in retrievals:
        retrieved.setdefault(row['document_id'], []).append(row)
    for row in pending:
        if row['reason'] != 'no_resolved_subject_and_cited_line':
            continue
        attempts = retrieved.get(row['source_id'], ())
        if not any(attempt['sha256'] for attempt in attempts):
            row['reason'] = 'missing_snapshot'
        else:
            row['reason'] = 'missing_precise_cited_line'
    timing_reconciliation = reconcile_timing_rows(
        event_timings, observations, timings, pending)
    schema = load_schema()
    write_table(ledger_dir, 'observations', observations, schema=schema)
    write_table(ledger_dir, 'timings', timings, schema=schema)
    write_table(ledger_dir, 'rates', [], schema=schema)
    pending_path = ledger_dir / 'migration' / '0876-pending.csv'
    with pending_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            'legacy_table', 'legacy_event_id', 'legacy_project_id', 'source_id', 'locator', 'reason'))
        writer.writeheader()
        writer.writerows(pending)
    reconciliation_path = ledger_dir / 'migration' / '0876-timing-reconciliation.csv'
    with reconciliation_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            'legacy_row_number', 'legacy_event_id', 'legacy_date_role',
            'outcome', 'timing_id', 'approval_timing_id', 'reason'), lineterminator='\n')
        writer.writeheader()
        writer.writerows(timing_reconciliation)
    return observations, timings, pending


def main():
    # Imported here, not at the top: build_observatory now consumes this module
    # for the country views, and a module-level import in both directions would
    # fail whichever side is loaded first.
    from jetp.build_observatory import read_inputs

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=ROOT / 'deliverables' / 'jetp-observatory' / 'data' / 'observations',
    )
    parser.add_argument(
        '--write-normalized', action='store_true',
        help='write v2 observations/timings/rates and the explicit pending register',
    )
    args = parser.parse_args()
    tables = read_inputs(ROOT)
    if args.write_normalized:
        write_normalized_event_tables(
            ROOT / 'data' / 'jetp', tables['events'], tables['implementation-events'],
            tables['event-timing'])
    by_country = observations_by_country(tables, build_registry(tables))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for code, entries in by_country.items():
        (args.output_dir / f'{code}.json').write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
        )


if __name__ == '__main__':
    main()
