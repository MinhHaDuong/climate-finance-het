"""Build cited v2 observations and the per-country observatory views.

The second stage-two product.  The M1a inventories freeze what a source
published about its own projects; these are the ledger rows analysts wrote from
those same documents, under a different schema.  Two extractions, served side
by side and never added together: a row here and a row there can describe the
same paragraph of the same PDF.

One invocation writes all four countries. Accepted event rows in those views
come from v2 observations and their cited lines; unresolved event assertions
remain in the pending register. Legacy project links and presentation fields
stay until their separate migration.
"""

import argparse
import csv
import json
from pathlib import Path

from jetp._ledger_headers import load_schema, write_table
from jetp._m1a_document_links import pdf_page_of
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


def _served_event_entry(old, current, table, registry, line_by_id, event_id):
    """Keep browser-only fields while taking the assertion and citation from v2."""
    financial = table == 'events'
    expected_method = 'legacy_event' if financial else 'legacy_implementation_event'
    expected_axis = ('money' if financial else
                     'asset_state' if current['subject_kind'] == 'asset' else 'delivery')
    expected_measure = ('estimate' if old.get('financial_status') == 'need'
                        else 'amount') if financial else 'state'
    status_field = 'financial_status' if financial else 'implementation_status'
    value_field = 'amount_original' if financial else 'capacity_mw'
    old_currency = old['currency_original'] if financial else ''
    if (current['method'] != expected_method or current['status'] != 'accepted'
            or current['axis'] != expected_axis
            or current['measure'] != expected_measure
            or current['own_status'] != old[status_field]
            or (current['value'] or '') != old[value_field]
            or (current['currency'] or '') != old_currency):
        raise ValueError(f'{event_id}: v2 assertion differs from legacy source row')
    projected = dict(old)
    projected[status_field] = current['own_status']
    projected[value_field] = current['value'] or ''
    if financial:
        projected['currency_original'] = current['currency'] or ''
    entry = observation_entry(projected, table, registry)
    line = line_by_id.get(current['line_id'])
    if line is None:
        raise ValueError(f'{event_id}: cited line is absent')
    entry.update(observation_id=current['observation_id'],
                 line_id=current['line_id'],
                 subject_kind=current['subject_kind'],
                 subject_id=current['subject_id'],
                 locator=line['locator'], sha256=line['sha256'])
    entry['pdf_page'] = pdf_page_of(line['locator'])
    return entry


def served_observations_by_country(tables, registry, observations, timings, pending,
                                   lines, retrievals, citation_decisions=()):
    """Project reviewed v2 events into the existing public row contract.

    The browser still addresses legacy project IDs and project-source-links.
    Event membership and the asserted status/value now come from v2; the old
    rows provide only presentation fields that v2 does not store. An event
    without v2 evidence remains in the pending register and is absent from
    the public observations view. Ticket 0878 retires this bridge with the
    remaining legacy readers.
    """
    legacy = [(table, row, row['event_id' if table == 'events'
                                else 'implementation_event_id'])
              for table in ('events', 'implementation-events')
              for row in tables[table]]
    legacy_ids = {event_id for _, _, event_id in legacy}
    if len(legacy_ids) != len(legacy):
        raise ValueError('duplicate legacy event identifier in served view')
    accepted = {row['observation_id'].removeprefix('observation-'): row
                for row in observations}
    if len(accepted) != len(observations) or set(accepted) - legacy_ids:
        raise ValueError('v2 observation lacks a unique legacy event')
    held = {row['legacy_event_id']: row for row in pending
            if row['legacy_table'] != 'event-timing'}
    if (len(held) != sum(row['legacy_table'] != 'event-timing' for row in pending)
            or set(held) - legacy_ids):
        raise ValueError('pending event lacks a unique legacy event')
    errors = citation_provenance_errors(
        tables['events'], tables['implementation-events'], observations,
        pending, citation_decisions, lines, retrievals)
    if errors:
        raise ValueError('\n'.join(errors))
    line_by_id = {row['line_id']: row for row in lines}
    for timing in timings:
        event_id = timing['observation_id'].removeprefix('observation-')
        observation = accepted.get(event_id)
        if observation is None or timing['line_id'] != observation['line_id']:
            raise ValueError(f'{event_id}: timing lacks its cited observation line')

    served = {code: [] for code in COUNTRIES}
    for table, old, event_id in legacy:
        if old['country'] not in served:
            raise ValueError(f"Unsupported observation country: {old['country']}")
        current = accepted.get(event_id)
        hold = held.get(event_id)
        if (current is None) == (hold is None):
            raise ValueError(f'{event_id}: expected one accepted observation or named hold')
        if hold is not None:
            if (hold['legacy_table'] != table or hold['source_id'] != old['source_id']
                    or hold['legacy_project_id'] != old['project_id'] or not hold['reason']):
                raise ValueError(f'{event_id}: invalid pending event')
            continue
        served[old['country']].append(
            _served_event_entry(old, current, table, registry, line_by_id, event_id))
    for row in tables['project-source-links']:
        if row['country'] not in served:
            raise ValueError(f"Unsupported observation country: {row['country']}")
        served[row['country']].append(observation_entry(row, 'project-source-links', registry))
    return served


def append_event_timings(event_id, observation_id, line_id, source_rows, timings, pending,
                         hold_reason=None):
    """Translate supported dates while preserving unmapped source roles."""
    for ordinal, row in enumerate(source_rows, start=1):
        if hold_reason:
            pending.append({
                'legacy_table': 'event-timing', 'legacy_event_id': event_id,
                'legacy_project_id': '', 'source_id': '', 'locator': '',
                'reason': hold_reason,
            })
            continue
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


def index_adjudications(adjudications):
    """Validate and index event-specific source and identity decisions."""
    indexed = {}
    for adjudication in adjudications:
        key = (adjudication['legacy_table'], adjudication['legacy_event_id'])
        if key in indexed:
            raise ValueError(f'duplicate event adjudication: {key}')
        if adjudication['promotion'] not in {'accept', 'hold'}:
            raise ValueError(f'{key}: unsupported promotion {adjudication["promotion"]}')
        if adjudication['referent_kind'] not in {'agreement', 'project', 'line'}:
            raise ValueError(f'{key}: unsupported referent kind {adjudication["referent_kind"]}')
        if not all(adjudication[field] for field in ('source_id', 'line_id', 'referent_id')):
            raise ValueError(f'{key}: incomplete adjudication target')
        if adjudication.get('timing_hold_reason') and adjudication['promotion'] != 'accept':
            raise ValueError(f'{key}: timing hold requires an accepted observation')
        indexed[key] = adjudication
    return indexed


def index_citation_decisions(decisions):
    """Index the event-level source review without losing an unresolved row."""
    indexed = {}
    for decision in decisions:
        key = (decision['legacy_table'], decision['legacy_event_id'])
        if key in indexed:
            raise ValueError(f'duplicate citation decision: {key}')
        if decision['decision'] not in {'accepted', 'pending'}:
            raise ValueError(f'{key}: unknown citation decision')
        if decision['decision'] == 'accepted' and not all(
                decision[field] for field in ('line_id', 'locator', 'source_sha256',
                                               'source_status')):
            raise ValueError(f'{key}: incomplete accepted citation')
        if decision['decision'] == 'pending' and (decision['line_id'] or not decision['reason']):
            raise ValueError(f'{key}: pending citation needs a reason and no line')
        indexed[key] = decision
    return indexed


def _pending_event(row, event_id, table, reason, locator=None):
    return {
        'legacy_table': table,
        'legacy_event_id': event_id,
        'legacy_project_id': row['project_id'],
        'source_id': row['source_id'],
        'locator': locator or row['locator'],
        'reason': reason,
    }


def _target_event(row, event_id, table, dispositions, adjudications, citations, pending):
    """Choose one event's reviewed line and subject, or record its evidence gap."""
    citation = citations.get((table, event_id))
    if citation is not None:
        if citation['source_id'] != row['source_id']:
            raise ValueError(f'{event_id}: citation source differs from legacy source')
        source_value = row.get('amount_original', row.get('capacity_mw', ''))
        source_status = row.get('financial_status', row.get('implementation_status', ''))
        if citation['decision'] == 'accepted' and (
                citation['source_value'] != source_value
                or citation['source_currency'] != row.get('currency_original', '')
                or citation['source_status'] != source_status):
            raise ValueError(f'{event_id}: citation fields differ from legacy assertion')
        if citation['decision'] == 'pending':
            pending.append(_pending_event(row, event_id, table,
                                          f"1160_{citation['reason']}", citation['locator']))
            return None
    adjudication = adjudications.get((table, event_id))
    if adjudication is not None:
        if (adjudication['legacy_project_id'] != row['project_id']
                or adjudication['source_id'] != row['source_id']):
            raise ValueError(f'{event_id}: adjudication does not match legacy row')
        if adjudication['promotion'] == 'hold':
            pending.append(_pending_event(
                row, event_id, table, '0970_physical_state_hold',
                f"{row['locator']}; line_id={adjudication['line_id']}"))
            return None
        return {
            'disposition': adjudication['referent_kind'],
            'new_id': adjudication['referent_id'],
            'line_id': citation['line_id'] if citation else adjudication['line_id'],
            'timing_hold_reason': adjudication.get('timing_hold_reason') or None,
        }
    disposition = dispositions.get(row['project_id'])
    if disposition is None:
        pending.append(_pending_event(row, event_id, table, 'no_0875_disposition'))
        return None
    if not disposition['new_id'] or not disposition['line_id']:
        pending.append(_pending_event(row, event_id, table,
                                      'no_resolved_subject_and_cited_line'))
        return None
    if citation is None:
        return disposition
    return {**disposition, 'line_id': citation['line_id']}


def normalize_event_tables(events, implementation_events, event_timings, dispositions,
                           adjudications=(), citation_decisions=()):
    """Return the valid v2 event observations, timings, and explicit gaps.

    A legacy event can enter v2 only when ticket 0875 resolved both its subject
    and the line that supports it.  In particular, an event whose source was
    blocked has no line to cite; keeping it in ``pending`` is evidence
    preservation, whereas borrowing a line from another document would invent
    a citation.  The caller writes that pending register beside the tables.
    """
    disposition_by_old_id = {row['old_id']: row for row in dispositions}
    adjudication_by_event = index_adjudications(adjudications)
    citation_by_event = index_citation_decisions(citation_decisions)
    timing_by_event = {}
    for row in event_timings:
        timing_by_event.setdefault(row['event_id'], []).append(row)

    observations, timings, pending = [], [], []

    for row in events:
        event_id = row['event_id']
        disposition = _target_event(row, event_id, 'events', disposition_by_old_id,
                                    adjudication_by_event, citation_by_event, pending)
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
                             timing_by_event.get(event_id, ()), timings, pending,
                             disposition.get('timing_hold_reason'))

    for row in implementation_events:
        event_id = row['implementation_event_id']
        disposition = _target_event(row, event_id, 'implementation-events',
                                    disposition_by_old_id, adjudication_by_event,
                                    citation_by_event, pending)
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
    timing_gaps = {row['legacy_event_id']: row['reason'] for row in pending
                   if row['legacy_table'] == 'event-timing'}
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
        elif event_id in timing_gaps:
            outcome, reason = 'pending', timing_gaps[event_id]
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


def citation_provenance_errors(events, implementation_events, observations, pending,
                               decisions, lines, retrievals):
    """Check each legacy event against an observation or an explicit hold."""
    source_by_event = {row['event_id']: row['source_id'] for row in events}
    source_by_event.update({row['implementation_event_id']: row['source_id']
                            for row in implementation_events})
    kind_by_event = {row['event_id']: 'events' for row in events}
    kind_by_event.update({row['implementation_event_id']: 'implementation-events'
                          for row in implementation_events})
    line_by_id = {row['line_id']: row for row in lines}
    source_digests = {}
    for row in retrievals:
        if row['sha256']:
            source_digests.setdefault(row['document_id'], set()).add(row['sha256'])
    decision_by_event = index_citation_decisions(decisions)
    accepted = {row['observation_id'].removeprefix('observation-'): row
                for row in observations}
    held = {row['legacy_event_id'] for row in pending
            if row['legacy_table'] != 'event-timing'}
    errors = []
    for event_id, source_id in source_by_event.items():
        if (event_id in accepted) == (event_id in held):
            errors.append(f'{event_id}: expected exactly one accepted or pending disposition')
            continue
        if event_id in held:
            continue
        line = line_by_id.get(accepted[event_id]['line_id'])
        if line is None:
            errors.append(f'{event_id}: cited line is absent')
            continue
        if line['sha256'] not in source_digests.get(source_id, set()):
            errors.append(f'{event_id}: cited line snapshot is not a retrieval of {source_id}')
        decision = decision_by_event.get((kind_by_event[event_id], event_id))
        if decision is not None and (
                line['sha256'] != decision['source_sha256']
                or line['locator'] != decision['locator']):
            errors.append(f'{event_id}: line differs from reviewed source snapshot/locator')
    for (kind, event_id), decision in decision_by_event.items():
        if event_id not in source_by_event:
            errors.append(f'{event_id}: citation decision has no legacy event')
        elif kind != kind_by_event[event_id]:
            errors.append(f'{event_id}: citation decision names the wrong legacy table')
        elif (event_id in accepted) != (decision['decision'] == 'accepted'):
            errors.append(f'{event_id}: citation decision differs from final disposition')
    return errors


def write_normalized_event_tables(ledger_dir, events, implementation_events, event_timings):
    """Write v2 event tables and their evidence-gap register to ``ledger_dir``."""
    ledger_dir = Path(ledger_dir)
    with (ledger_dir / 'migration' / '0875-dispositions.csv').open(
            encoding='utf-8', newline='') as handle:
        dispositions = list(csv.DictReader(handle))
    with (ledger_dir / 'migration' / '0970-event-adjudications.csv').open(
            encoding='utf-8', newline='') as handle:
        adjudications = list(csv.DictReader(handle))
    with (ledger_dir / 'migration' / '1160-citation-decisions.csv').open(
            encoding='utf-8', newline='') as handle:
        citation_decisions = list(csv.DictReader(handle))
    with (ledger_dir / 'migration' / '1120-event-adjudications.csv').open(
            encoding='utf-8', newline='') as handle:
        adjudications.extend(csv.DictReader(handle))
    observations, timings, pending = normalize_event_tables(
        events, implementation_events, event_timings, dispositions, adjudications,
        citation_decisions)
    # A blocked retrieval is an acquisition gap; a collected document with no
    # resolved event line needs line-level review.  Keep those remedies apart.
    with (ledger_dir / 'retrievals.csv').open(encoding='utf-8', newline='') as handle:
        retrievals = list(csv.DictReader(handle))
    lines = []
    for path in sorted((ledger_dir / 'lines.d').glob('*.csv')):
        with path.open(encoding='utf-8', newline='') as handle:
            lines.extend(csv.DictReader(handle))
    errors = citation_provenance_errors(
        events, implementation_events, observations, pending, citation_decisions,
        lines, retrievals)
    if errors:
        raise ValueError('\n'.join(errors))
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
            'legacy_table', 'legacy_event_id', 'legacy_project_id', 'source_id', 'locator', 'reason'),
            lineterminator='\n')
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
    ledger_dir = ROOT / 'data' / 'jetp'

    def rows(path):
        with path.open(encoding='utf-8', newline='') as handle:
            return list(csv.DictReader(handle))

    lines = [row for path in sorted((ledger_dir / 'lines.d').glob('*.csv'))
             for row in rows(path)]
    by_country = served_observations_by_country(
        tables, build_registry(tables), rows(ledger_dir / 'observations.csv'),
        rows(ledger_dir / 'timings.csv'),
        rows(ledger_dir / 'migration/0876-pending.csv'), lines,
        rows(ledger_dir / 'retrievals.csv'),
        rows(ledger_dir / 'migration/1160-citation-decisions.csv'))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for code, entries in by_country.items():
        (args.output_dir / f'{code}.json').write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
        )


if __name__ == '__main__':
    main()
