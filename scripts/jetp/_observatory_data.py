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
        'collection_method': row.get('collection_method') or None,
        'local_path': (f'documents/{storage_path}'
                       if storage_path and storage_path in available else None),
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
