"""Reusable unadmitted country positions and lossless legacy dispositions.

Inventory rows are subjects in their own right. Identity links require an explicit
crosswalk; no name, place, count, status or date heuristics create domain events.
"""

from pathlib import Path

from jetp._source_crosswalk import _identity

SCHEMA_VERSION = 'country-migration/1'


def inventory_positions(country: str, rows: list[dict], projects: list[dict],
                        joins: dict) -> list[dict]:
    """Preserve row membership, including unmatched and multiasset proposals."""
    project_ids = {row['project_id'] for row in projects}
    result, seen = [], set()
    for row in rows:
        annex = row.get('annex', row['inventory_id'])
        key = f"{annex}:{row['ordinal']}"
        if key in seen:
            raise ValueError(f'Duplicate inventory row {key}')
        seen.add(key)
        join = joins.get(key)
        targets = join['project_ids'] if join else []
        if join and (not targets or not set(targets) <= project_ids
                     or join['source_wording'] != row['source_wording']
                     or not join.get('rationale')):
            raise ValueError(f'Unresolved explicit identity crosswalk {key}')
        identity = _identity('inventory-position', [country, row])
        result.append({**row, 'record_kind': 'position', 'record_id': identity,
                       'country': country, 'measure': 'official_inventory_membership',
                       'subject': {'record_kind': 'inventory_row', 'record_id': identity + '-row'},
                       'entity_ids': list(targets), 'value': 'listed',
                       'disposition': ('explicit_identity_mapping' if join else
                                       'unresolved_inventory_membership'),
                       'reason': join['rationale'] if join else
                           'Retain one source row; identity and any component split need review',
                       'cutoff_date': None, 'transition_date': None, 'payment_amount': None,
                       'date_role': 'source_plan_bounds_only', 'review_state': 'pending',
                       'admission_status': 'unadmitted_candidate'})
    if set(joins) - seen:
        raise ValueError('Identity crosswalk refers to absent inventory rows')
    return result


def legacy_dispositions(crosswalk: dict, country: str, policies: dict) -> list[dict]:
    """Keep every country row and exact source crosswalk address, including gaps."""
    originals = {row['legacy_row_id']: row for row in crosswalk['retained']}
    project_ids = {r['row']['project_id'] for r in originals.values()
                   if r['owner'] == 'projects' and r['row'].get('country') == country}
    event_ids = {r['row'].get('event_id') for r in originals.values()
                 if r['owner'] in {'financial_event', 'implementation_event'}
                 and (r['row'].get('country') == country
                      or r['row'].get('project_id') in project_ids)} - {None}
    result = []
    for mapping in crosswalk['mappings']:
        original = originals[mapping['row_id']]
        row = original['row']
        name = Path(mapping['path']).name
        linked_timing = name == 'event-timing.csv' and row.get('event_id') in event_ids
        if row.get('country') != country and row.get('project_id') not in project_ids and not linked_timing:
            continue
        classification = {'projects.csv': 'identity_retained',
            'project-coverage.csv': 'observation_coverage',
            'authority-coverage.csv': 'observation_coverage',
            'dry-searches.csv': 'search_history', 'news-leads.csv': 'unadmitted_lead',
            'manifest.csv': 'acquisition_history', 'vnm-pilot-manifest.csv': 'acquisition_history',
            'sources.csv': 'source_metadata', 'project-source-links.csv': 'discovery_link',
            'events.csv': 'legacy_event_assertion_needs_timing_review',
            'implementation-events.csv': 'legacy_state_assertion_needs_timing_review',
            'event-timing.csv': 'legacy_timing_retained',
            'source-claims.csv': 'legacy_claim_needs_measure_review',
            'plan-projects.csv': 'reported_inventory_position'}.get(name)
        policy = policies.get(row.get('observation_id'))
        # Older country-observation ledgers can have no durable observation_id.
        # A reviewed, file-wide policy retains those source rows without inventing
        # an identity from their title, amount or matched event.
        if policy is None and name.endswith('-observations.csv'):
            policy = policies.get('__all__')
        if name.endswith('-observations.csv'):
            if not policy:
                raise ValueError(f"Missing observation disposition: {row.get('observation_id')}")
            classification = policy['classification']
        if not classification:
            raise ValueError(f'Unclassified country input: {name}')
        result.append({**mapping, 'original': dict(row), 'classification': classification,
                       'disposition': 'retained_legacy_authority',
                       'candidate_record_ids': ([_identity('legacy-position', mapping['row_id'])]
                                                if policy else []),
                       'temporal_interpretation': 'legacy_date_preserved_not_promoted',
                       'transition_date': None, 'payment_amount': None,
                       'reason': policy['reason'] if policy else
                           'Original fields and owner retained; no inferred transition or ownership transfer'})
    used = {r['original'].get('observation_id') for r in result}
    if set(policies) - used - {'__all__'}:
        raise ValueError('Observation policy refers to absent country rows')
    return result
