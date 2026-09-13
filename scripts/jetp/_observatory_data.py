"""Evidence-preserving transforms for the public observatory."""

from datetime import datetime


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


def public_event(row):
    """Separate a register observation from an evidenced financing signature."""
    registered = row.get('verification_status') == 'official_register'
    reported = row.get('verification_status') == 'official_report'
    raw_date = row.get('event_date') or None
    return {
        'id': row.get('event_id', row.get('implementation_event_id', '')),
        'status': 'Registered financing' if registered else row.get(
            'financial_status', row.get('implementation_status', '')).replace('_', ' ').capitalize(),
        'date': None if registered or reported else iso_date(raw_date),
        'observed_date': raw_date if reported else None,
        'recorded_date': raw_date,
        'date_basis': 'Register date; signature not verified' if registered else (
            'Status reported as of this date' if reported else 'Source event date'),
        'amount': row.get('amount_original') or None,
        'currency': row.get('currency_original') or None,
        'funder': row.get('funder', ''), 'instrument': row.get('instrument', ''),
        'scope': row.get('scope', ''), 'source_id': row.get('source_id', ''),
        'locator': row.get('locator', ''), 'notes': row.get('notes', ''),
    }


def timeline(rows):
    """Sort known event dates, retaining undated observations at the end."""
    return sorted(rows, key=lambda row: (row.get('date') is None, row.get('date') or ''))


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
