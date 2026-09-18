"""Evidence-preserving transforms for the public observatory."""

from datetime import datetime

from jetp._m1a_document_links import resolve_document_link

# The three ledger tables served as explorable observations, and the kind each
# one carries.  Derived from the table, never read from a row: none of the
# three publishes a kind column, so a row cannot supply one.
OBSERVATION_KINDS = {
    'events': 'financial_event',
    'implementation-events': 'implementation_event',
    'project-source-links': 'project_source_link',
}
# The same decision under two column names, because the two ledgers were
# written years apart.  ``verification`` aliases whichever one a table
# publishes; the source column stays in the entry under its own name.
VERIFICATION_COLUMNS = {
    'events': 'verification_status',
    'implementation-events': 'verification_status',
    'project-source-links': 'review_status',
}


def iso_date(value):
    """Parse a source date without inventing a missing date."""
    if not value:
        return None
    for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(value.split('T')[0].split(' ')[0], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def public_event(row, timing=None, source=None):
    """Use explicit timing adjudication, never authority as a date-role proxy."""
    timing = timing or {}
    source = source or {}
    registered = row.get('verification_status') == 'official_register'
    role = timing.get('date_role', 'unreviewed')
    precision = timing.get('event_precision', 'unknown')
    if role not in {'event', 'reporting_cutoff', 'publication', 'observation', 'register',
                    'other_milestone', 'ambiguous', 'unknown', 'unreviewed'}:
        raise ValueError(f'Unknown date role: {role}')
    if precision not in {'day', 'month', 'year', 'interval', 'unknown'}:
        raise ValueError(f'Unknown event precision: {precision}')
    if precision == 'unknown' and (timing.get('event_start') or timing.get('event_end')):
        raise ValueError('Unknown timing cannot carry event bounds')
    if precision == 'day' and role != 'event':
        raise ValueError('A point event date requires explicit event adjudication')
    start, end = iso_date(timing.get('event_start')), iso_date(timing.get('event_end'))
    if precision == 'day' and (not start or start != end):
        raise ValueError('Day precision requires identical established bounds')
    if precision in ('year', 'month', 'interval') and (not start or not end or start > end):
        raise ValueError('Interval precision requires ordered established bounds')
    return {
        'id': row.get('event_id', row.get('implementation_event_id', '')),
        'status': 'Registered financing' if registered else row.get(
            'financial_status', row.get('implementation_status', '')).replace('_', ' ').capitalize(),
        'date': start if precision == 'day' else None,
        'date_role': role, 'event_precision': precision,
        **({'event_start': start, 'event_end': end} if start and end else {}),
        'observed_date': iso_date(timing.get('observed_on')),
        'reported_on': timing.get('reported_on') or None,
        'collected_on': source.get('retrieved') or None,
        'recorded_date': row.get('event_date') or None,
        'date_basis': timing.get('date_note') or 'Timing not reviewed; legacy date is not an event date',
        'amount': row.get('amount_original') or None,
        'currency': row.get('currency_original') or None,
        'funder': row.get('funder', ''), 'instrument': row.get('instrument', ''),
        'scope': row.get('scope', ''), 'source_id': row.get('source_id', ''),
        'locator': row.get('locator', ''), 'notes': row.get('notes', ''),
    }


def timeline(rows):
    """Sort known event dates, retaining undated observations at the end."""
    return sorted(rows, key=lambda row: (row.get('date') is None, row.get('date') or ''))


def document_entry(row, available):
    """Report a registry row's own collection outcome, never a derived verdict."""
    storage_path = row.get('storage_path') or ''
    return {
        'id': row.get('source_id', ''),
        'country': row.get('country', ''),
        'collected_on': row.get('retrieved_at') or None,
        'status': row.get('status', ''),
        'content_type': row.get('content_type') or None,
        'size_bytes': int(row['size_bytes']) if row.get('size_bytes') else None,
        'sha256': row.get('sha256') or None,
        'url': row.get('final_url') or None,
        'error': row.get('error') or None,
        'local_path': (f'documents/{storage_path}'
                       if storage_path and storage_path in available else None),
    }


def observation_entry(row, table, registry):
    """Serve one ledger row as it was written, addressed to its document.

    Every source column passes through verbatim, as the string ``csv.DictReader``
    read: an amount is never parsed, a status never recoded.  ``public_event``
    capitalises a financial status for a headline; this view must not, because
    what it publishes is the ledger's own word — ``secondary_only`` reaches the
    page as ``secondary_only``.

    The fingerprint comes from the collection registry, uniformly across the
    three tables, never from the ``document_sha256`` column two of them carry:
    one resolution path, one answer.  A source the collection never recorded
    (seven Viet Nam link rows) resolves to a null fingerprint rather than
    aborting the build — the page then shows the locator as text, which is what
    the renderer does for the same case, and the gap stays visible instead of
    emptying a country.
    """
    if table not in OBSERVATION_KINDS:
        raise ValueError(f'Unknown observation table: {table}')
    source_id = row['source_id']
    link = resolve_document_link(
        source_id, row.get('locator', ''), {source_id: registry.get(source_id, {})}
    )
    return {
        **dict(row),
        'table': table,
        'kind': OBSERVATION_KINDS[table],
        'verification': row[VERIFICATION_COLUMNS[table]],
        'sha256': link['sha256'],
        'pdf_page': link['pdf_page'],
    }


def historical_record(row, country, jetp_date):
    """Select administratively closed pre-JETP energy-related operations."""
    approval = iso_date(row.get('boardapprovaldate'))
    sectors = [x.get('name', '') for x in (row.get('sector_namecode') or [])]
    energy = any(any(term in name.lower() for term in ('energy', 'power', 'electric')) for name in sectors)
    if row.get('status') != 'Closed' or not approval or approval >= jetp_date or not energy:
        return None
    closing = iso_date(row.get('closingdate'))
    days = (datetime.fromisoformat(closing) - datetime.fromisoformat(approval)).days if closing else -1
    instrument = row.get('lendinginstr') or ''
    return {
        'id': row['id'], 'country': country, 'name': row.get('project_name', ''),
        'status': 'Closed', 'approval': approval, 'closing': closing,
        'years': round(days / 365.25, 2) if days >= 0 else None,
        'instrument': instrument or 'Not specified', 'sectors': sectors,
        'additional_financing': row.get('supplementprojectflg') == 'Y',
        'source_url': row.get('url') or f"https://projects.worldbank.org/en/projects-operations/project-detail/{row['id']}",
    }
