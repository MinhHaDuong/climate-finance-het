"""Build Indonesia's unadmitted migration sidecar beside the unchanged MVP."""

import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from jetp._compatibility import MVP_VIEWS, read_mvp_view
from jetp._contracts import validate_evidence_tuple
from jetp._country_migration import (
    SCHEMA_VERSION,
    inventory_positions,
    legacy_dispositions,
)
from jetp._idn_positions import migrate_positions
from jetp._observatory_bundle import _protect_output, _protect_replacement
from jetp._source_crosswalk import _identity, migrate_sources


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _source_context(policy: dict, crosswalk: dict, rows: list[dict], recipe: dict) -> dict:
    attempts = [row for row in crosswalk['acquisitions'] if all(
        row[key] == policy[key] for key in ('source_id', 'retrieved_at', 'document_sha256'))]
    if len(attempts) != 1 or attempts[0]['byte_status'] != 'available':
        raise ValueError('Selected Indonesian source bytes are not recoverable')
    edition = {'record_kind': 'edition', 'record_id': policy['edition_id']}
    snapshot = {'record_kind': 'edition_snapshot', 'edition': edition,
                'document_sha256': policy['document_sha256'],
                'acquisition_id': attempts[0]['acquisition_id'], 'review_state': 'pending'}
    parser = {'name': 'existing-pinned-idn-extractors', 'recipe_inputs': recipe}
    extraction = {'extraction_id': _identity('extraction', [policy['document_sha256'], parser]),
                  'document_sha256': policy['document_sha256'], 'parser': parser,
                  'output_sha256': hashlib.sha256(encoded(rows)).hexdigest(),
                  'locators': [row['locator'] for row in rows], 'admission_status': 'unadmitted_candidate'}
    return {'policy': policy, 'acquisition': attempts[0], 'edition_snapshot': snapshot,
            'extraction': extraction}


def _inventory(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        # Numbering restarts in each technology appendix/table.  Keep that
        # perimeter in the inventory identity instead of flattening it.
        result.append({'inventory_id': f"{row['source_id']}:{row['technology_group']}", 'ordinal': int(row['ordinal']),
                       'source_wording': row['project_name'], 'source_fields': row,
                       'locator': row['locator'], 'source_id': row['source_id'],
                       'classification': 'official_plan_inventory_position'})
    return result


def build_migration(root: Path, *, source_root: Path | None = None) -> dict:
    root, source_root = Path(root).resolve(), Path(source_root or root).resolve()
    policy = json.loads((root / 'config/jetp-idn-migration.json').read_text())
    crosswalk = migrate_sources(root, source_root=source_root)
    # The writer guards are importable without the PDF parser; extraction is only
    # needed once source bytes have passed the selected-acquisition checks.
    from jetp.build_idn_cipp_priority_projects import (
        extract_priority_projects as extract_cipp,
    )
    from jetp.build_idn_progress_priority_projects import (
        extract_priority_projects as extract_progress,
    )
    by_source = {entry['source_id']: entry for entry in policy['sources']}
    objects = source_root / 'data/jetp/documents/objects'
    cipp = extract_cipp(objects / '74/747283facac512780ad757313c493d1080c39705824e72c4b231e87ecb4102b5.pdf')
    progress = extract_progress(objects / '74/74fb460fd09e76607e3cff308f5ba2754f2ebd91b0c9b7613c1a041e7b361162.pdf')
    rows = cipp + progress
    if Counter(row['source_id'] for row in rows) != Counter({key: value['row_count'] for key, value in by_source.items()}):
        raise ValueError('Incomplete Indonesian official plan inventories')
    committed = crosswalk['inputs']['data/jetp/plan-projects.csv']['rows']
    committed_rows = [row for row in committed if row['country'] == 'IDN']
    if {row['plan_project_id']: row for row in rows} != {row['plan_project_id']: row for row in committed_rows}:
        raise ValueError('Pinned extraction differs from committed Indonesian plan inventory')
    recipe_paths = ['scripts/jetp/_idn_positions.py', 'scripts/jetp/build_idn_positions.py',
                    'scripts/jetp/build_idn_cipp_priority_projects.py',
                    'scripts/jetp/build_idn_progress_priority_projects.py',
                    'config/jetp-idn-migration.json']
    recipe = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in recipe_paths}
    contexts = {_policy['source_id']: _source_context(_policy, crosswalk,
                [row for row in rows if row['source_id'] == _policy['source_id']], recipe)
                for _policy in policy['sources']}
    projects = [row for row in crosswalk['inputs']['data/jetp/projects.csv']['rows'] if row['country'] == 'IDN']
    inventory = inventory_positions('IDN', _inventory(rows), projects, {})
    for position in inventory:
        context = contexts[position['source_id']]
        evidence = {'document_sha256': context['policy']['document_sha256'],
                    'edition': context['edition_snapshot']['edition'], 'locator': position['locator'],
                    'acquisition_id': context['acquisition']['acquisition_id'],
                    'extraction_id': context['extraction']['extraction_id'], 'source_id': position['source_id']}
        validate_evidence_tuple(evidence, context['acquisition'], context['extraction'], [context['edition_snapshot']])
        position.update(evidence=evidence, transition_date=None, payment_amount=None,
                        eligible_for_account=False, candidate_created_at=policy['recorded_at'])
    events = [row for row in crosswalk['inputs']['data/jetp/events.csv']['rows'] if row['country'] == 'IDN']
    semantic = migrate_positions(plan_rows=[{**row, 'source_wording': row['project_name']} for row in rows],
                                 approval_rows=[{**row, 'source_wording': row['notes']} for row in events
                                                if row['financial_status'] == 'approved'])
    observation_policies = {'__all__': {'classification': 'portfolio_observation_retained',
                            'reason': 'Official portal observation retained; matching report event stays a separate assertion'}}
    legacy = legacy_dispositions(crosswalk, 'IDN', observation_policies)
    selected_ids = {row['row_id'] for row in legacy}
    views = {view: read_mvp_view(root, view, supported_versions={'mvp/1'}) for view in sorted(MVP_VIEWS)}
    result = {'schema_version': SCHEMA_VERSION, 'country': 'IDN', 'admission_status': 'unadmitted_candidate',
              'writer_owner': 'legacy', 'publication_mode': 'legacy',
              'inputs': {name: {key: value for key, value in info.items() if key != 'rows'}
                         for name, info in crosswalk['inputs'].items()}, 'recipe_inputs': recipe,
              'recovery_inputs': crosswalk['recovery_inputs'], 'selected_sources': list(contexts.values()),
              'inventory_positions': inventory, **semantic, 'legacy_dispositions': legacy,
              'legacy_evidence': [row for row in crosswalk['evidence'] if row['legacy_row_id'] in selected_ids],
              'legacy_unresolved': [row for row in crosswalk['unresolved'] if row['legacy_row_id'] in selected_ids],
              'inventory_boundaries': [{'inventory_id': inventory_id, 'disposition': 'selected',
                                        'row_count': len(group)}
                                       for inventory_id, group in sorted(
                                           ((key, [row for row in _inventory(rows) if row['inventory_id'] == key])
                                            for key in {row['inventory_id'] for row in _inventory(rows)}),
                                           key=lambda item: item[0])],
              'source_regime': policy['source_regime'], 'mvp_views': views,
              'comparison': {'legacy_rows_by_table': dict(Counter(row['path'] for row in legacy)),
                             'inventory_rows_by_source': dict(Counter(row['source_id'] for row in rows)),
                             'existing_project_ids': [row['project_id'] for row in projects],
                             'added_public_project_ids': [], 'removed_public_project_ids': [],
                             'financial_event_additions': 0, 'website_semantic_changes': [],
                             'reason': 'Candidate sidecar retains legacy writer and all six MVP views'}}
    validate_migration(result)
    return result


def validate_migration(result: dict) -> None:
    if result['writer_owner'] != 'legacy' or result['publication_mode'] != 'legacy':
        raise ValueError('Candidate cannot transfer ownership')
    if set(result['mvp_views']) != MVP_VIEWS:
        raise ValueError('Candidate must retain every MVP view')
    for boundary in result['inventory_boundaries']:
        rows = [row for row in result['inventory_positions'] if row['inventory_id'] == boundary['inventory_id']]
        if sorted(row['ordinal'] for row in rows) != list(range(1, boundary['row_count'] + 1)):
            raise ValueError('Incomplete selected Indonesian plan inventory')
    if result['payment_candidates'] or result['account_total'] is not None:
        raise ValueError('Plan and approval candidate cannot create a payment account')
    if any(row['disposition'] != 'retained_legacy_authority' for row in result['legacy_dispositions']):
        raise ValueError('Incomplete legacy disposition')


def _country_output(output: Path) -> bool:
    """Only a complete prior IDN sidecar may be atomically replaced."""
    try:
        previous = json.loads(output.read_bytes())
        records = {'selected_sources', 'inventory_positions', 'plan_positions', 'approval_positions',
                   'payment_candidates', 'legacy_dispositions', 'legacy_evidence', 'legacy_unresolved',
                   'inventory_boundaries', 'source_regime'}
        objects = {'inputs', 'recipe_inputs', 'recovery_inputs', 'mvp_views', 'comparison'}
        fields = records | objects | {'schema_version', 'country', 'admission_status', 'writer_owner',
                                      'publication_mode', 'account_total'}
        if (not isinstance(previous, dict) or previous.keys() != fields
                or previous['schema_version'] != SCHEMA_VERSION or previous['country'] != 'IDN'
                or previous['admission_status'] != 'unadmitted_candidate'
                or not all(isinstance(previous[key], list) and all(isinstance(row, dict) for row in previous[key])
                           for key in records)
                or not all(isinstance(previous[key], dict) for key in objects)
                or not all(isinstance(value, dict) for value in previous['mvp_views'].values())):
            return False
        validate_migration(previous)
        return bool(previous['inventory_positions'] and previous['legacy_dispositions'])
    except (OSError, ValueError, KeyError, TypeError):
        return False


def write_migration(root: Path, output: Path, *, source_root: Path | None = None) -> dict:
    """Write only one complete candidate, preserving accepted routes and assets."""
    root, output = Path(root).resolve(), Path(output)
    _protect_replacement(output, _country_output(output))
    output = output.resolve()
    source_root = Path(source_root or root).resolve()
    if output.suffix != '.json':
        raise ValueError('Country candidate output must end in .json')
    for checkout in {root, source_root}:
        releases = [path for path in (checkout / 'data/jetp/releases').rglob('*')
                    if path.is_file() and path != output]
        _protect_output(checkout, output, inputs=releases)
    result = build_migration(root, source_root=source_root)
    payload = encoded(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
    return result
