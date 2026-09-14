"""Bounded, versioned provenance for static JETP publication claims."""

from collections import defaultdict

FORMAT_VERSION = 'jetp-publication/1'


def _required(item, key, kind):
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f'{kind} requires {key}')
    return value


def _displays(displays):
    seen, normalized, evidence_index = set(), [], defaultdict(list)
    for display in displays:
        item = dict(display)
        display_id = _required(item, 'display_id', 'Display')
        if display_id in seen:
            raise ValueError(f'Duplicate display ID: {display_id}')
        seen.add(display_id)
        for key in ('route', 'payload', 'pointer', 'role'):
            _required(item, key, 'Display')
        evidence = item.get('evidence')
        if not isinstance(evidence, list) or not evidence or not all(
                isinstance(value, str) and value for value in evidence):
            raise ValueError('Display requires non-empty evidence')
        item['evidence'] = sorted(set(evidence))
        normalized.append(item)
        for source_id in item['evidence']:
            evidence_index[source_id].append(display_id)
    return sorted(normalized, key=lambda row: row['display_id']), evidence_index


def _combinations(combinations):
    selected, selected_keys = [], set()
    for combination in combinations:
        item = dict(combination)
        key = tuple(_required(item, name, 'Combination')
                    for name in ('subject', 'measure', 'perimeter'))
        if key in selected_keys:
            raise ValueError(f'Duplicate publication owner: {key}')
        selected_keys.add(key)
        owner = _required(item, 'owner', 'Combination')
        if owner not in {'legacy', 'reconciled'}:
            raise ValueError(f'Unknown publication owner: {owner}')
        contributors = item.get('contributors', [])
        if owner == 'reconciled':
            _validate_reconciled(item, contributors)
        elif contributors:
            raise ValueError('Legacy publication cannot mix contributor ownership')
        item['contributors'] = contributors
        selected.append(item)
    return sorted(selected, key=lambda row: (row['subject'], row['measure'], row['perimeter']))


def _validate_reconciled(item, contributors):
    if item.get('accepted') is not True:
        raise ValueError('Reconciled publication requires acceptance')
    if not contributors or any(row.get('owner') != 'reconciled' for row in contributors):
        raise ValueError('Reconciled publication requires complete reconciled ownership')
    ids = [row.get('id') for row in contributors]
    if any(not isinstance(value, str) or not value for value in ids):
        raise ValueError('Reconciled contributor requires ID')
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate contributor')


def publish(release_id, displays, combinations):
    """Validate publication selection and emit a reverse evidence index.

    The caller selects one writer per (subject, measure, perimeter). Reconciled
    financial claims are unavailable until every contributor has accepted
    reconciled ownership.
    """
    if not isinstance(release_id, str) or not release_id:
        raise ValueError('Publication requires release ID')
    normalized, evidence_index = _displays(displays)
    return {'format_version': FORMAT_VERSION, 'release_id': release_id,
            'displays': normalized, 'combinations': _combinations(combinations),
            'by_evidence': {key: sorted(value) for key, value in sorted(evidence_index.items())}}


def reported_position_sidecar(config, countries):
    """Trace each visible national reported position without duplicating payloads."""
    displays, combinations = [], []
    for code, country in sorted(countries.items()):
        source = country['country']['headline_source']
        for route, display_id in (('#overview', f'overview-{code}-headline'),
                                  (f'#country/{code}', f'country-{code}-headline'),
                                  (f'#country/{code}', f'country-{code}-headline-context')):
            displays.append({'display_id': display_id, 'route': route,
                             'payload': f'data/{code}.json', 'pointer': '/country/headline',
                             'role': 'reported_position', 'evidence': [source]})
        combinations.append({'subject': code, 'measure': 'reported_position',
                             'perimeter': 'national_headline', 'owner': 'legacy'})
    result = publish(config['edition'], displays, combinations)
    result['glossary'] = {
        'reported_position': 'A country headline reproduced from its named source; it is not a reconciled payment total.',
        'legacy': 'The frozen MVP writer remains authoritative for this published combination.',
        'reconciled': 'A selected reconstructed combination with accepted complete ownership.',
    }
    return result
