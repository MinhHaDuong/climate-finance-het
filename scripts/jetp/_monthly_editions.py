"""Compare two reviewed snapshots without mutating either edition."""

from datetime import date


def _edition_date(snapshot, key):
    try:
        return date.fromisoformat(snapshot[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'{key} must be an ISO date') from exc


def _records(snapshot):
    rows = snapshot.get('records')
    if not isinstance(rows, list):
        raise ValueError('records must be a list')
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id']:
            raise ValueError('record requires a non-empty id')
        if row['id'] in result:
            raise ValueError(f'Duplicate record ID: {row["id"]}')
        result[row['id']] = row
    return result


def _sources(snapshot):
    rows = snapshot.get('sources')
    if not isinstance(rows, list):
        raise ValueError('sources must be a list')
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('source_id'), str) or not row['source_id']:
            raise ValueError('source requires a non-empty source_id')
        if row['source_id'] in result:
            raise ValueError(f'Duplicate source ID: {row["source_id"]}')
        result[row['source_id']] = row
    return result


def compare_editions(previous, current):
    """Classify a candidate edition while retaining an immutable prior snapshot."""
    if not isinstance(previous, dict) or not isinstance(current, dict):
        raise ValueError('editions must be objects')
    prior_cutoff, current_cutoff = _edition_date(previous, 'cutoff'), _edition_date(current, 'cutoff')
    if current_cutoff <= prior_cutoff:
        raise ValueError('current cutoff must be later than previous cutoff')
    prior_edition, edition = previous.get('edition'), current.get('edition')
    if not isinstance(prior_edition, str) or not prior_edition or not isinstance(edition, str) or not edition:
        raise ValueError('edition is required')
    if edition == prior_edition:
        raise ValueError('current edition must be later than previous edition')
    before, after = _records(previous), _records(current)
    missing = sorted(before.keys() - after.keys())
    if missing:
        raise ValueError(f"candidate omits prior record IDs: {', '.join(missing)}")
    _sources(previous)
    current_sources = _sources(current)
    unchanged, corrections, late_reports, retractions = [], [], [], []
    for record_id, row in sorted(after.items()):
        if record_id not in before:
            try:
                event_date = date.fromisoformat(row.get('event_date', ''))
            except ValueError as exc:
                raise ValueError(f'record {record_id} requires an ISO event_date') from exc
            if event_date <= prior_cutoff:
                late_reports.append(record_id)
            continue
        old = before[record_id]
        changed = sorted(key for key in old.keys() | row.keys() if old.get(key) != row.get(key))
        if not changed:
            unchanged.append(record_id)
        elif row.get('status') == 'retracted':
            retractions.append(record_id)
        else:
            corrections.append({'id': record_id, 'changed_fields': changed})
    failed = [{'source_id': source_id, 'status': row.get('status', '')}
              for source_id, row in sorted(current_sources.items())
              if row.get('status') not in {'found', 'unchanged'}]
    return {
        'edition': edition, 'previous_edition': prior_edition,
        'previous_cutoff': previous['cutoff'], 'cutoff': current['cutoff'],
        'unchanged': unchanged, 'corrections': corrections,
        'late_reports': late_reports, 'retractions': retractions,
        'failed_refreshes': failed, 'preserved_previous_record_ids': list(before),
    }


def release_history(releases):
    """Read immutable descriptors into the compact static-site history view."""
    import json
    from pathlib import Path

    fields = ('edition', 'observation_cutoff', 'release_state', 'release_prepared_date', 'publication_date')
    rows = []
    for path in Path(releases).glob('*/release.json'):
        try:
            descriptor = json.loads(path.read_text())
        except (OSError, ValueError, UnicodeError) as exc:
            raise ValueError(f'Invalid release descriptor: {path}') from exc
        if not all(field in descriptor for field in fields):
            raise ValueError(f'Incomplete release descriptor: {path}')
        rows.append({field: descriptor[field] for field in fields})
    editions = [row['edition'] for row in rows]
    if len(editions) != len(set(editions)):
        raise ValueError('Duplicate edition descriptor')
    return {'editions': sorted(rows, key=lambda row: row['edition'], reverse=True)}
