"""Stage South African register/report positions beside the unchanged legacy MVP."""

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from script_io_args import parse_io_args, validate_io

from jetp._compatibility import MVP_VIEWS, read_mvp_view
from jetp._contracts import validate_evidence_tuple
from jetp._country_migration import (
    SCHEMA_VERSION,
    inventory_positions,
    legacy_dispositions,
)
from jetp._observatory_bundle import _protect_output, _protect_replacement
from jetp._source_crosswalk import _identity, migrate_sources
from jetp._zaf_inventory import extract_inventory
from jetp._zaf_positions import migrate_positions
from jetp.build_zaf_investment_register import _project_id, _text


def encoded(value: object) -> bytes:
    """Stable, readable JSON recipe for the independent migration artifact."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def _source_context(source: dict, crosswalk: dict, rows: list[dict], recipe: dict, policy: dict) -> dict:
    attempts = [row for row in crosswalk['acquisitions']
                if all(row[key] == source[key] for key in ('source_id', 'retrieved_at', 'document_sha256'))]
    if len(attempts) != 1 or attempts[0]['byte_status'] != 'available':
        raise ValueError('Exactly selected saved acquisition must be recoverable')
    acquisition = attempts[0]
    edition = {'record_kind': 'edition', 'record_id': source['edition_id']}
    snapshot = {'record_kind': 'edition_snapshot', 'edition': edition,
                'document_sha256': source['document_sha256'],
                'acquisition_id': acquisition['acquisition_id'],
                'recorded_at': policy['recorded_at'], 'review_state': 'pending'}
    parser = {'name': 'pinned-register-json-and-pdfplumber',
              'pdfplumber_version': policy['parser_version'], 'recipe_inputs': recipe}
    extraction = {'extraction_id': _identity('extraction', [source['document_sha256'], parser]),
                  'document_sha256': source['document_sha256'], 'parser': parser,
                  'output_sha256': hashlib.sha256(encoded(rows)).hexdigest(),
                  'locators': [row['locator'] for row in rows],
                  'recorded_at': policy['recorded_at'], 'recorded_by': policy['recorded_by']}
    return {'role': source['role'], 'policy': source, 'acquisition': acquisition,
            'edition_snapshot': snapshot, 'extraction': extraction}


def _evidence(row: dict, context: dict) -> dict:
    evidence = {'document_sha256': context['policy']['document_sha256'],
                'edition': context['edition_snapshot']['edition'], 'locator': row['locator'],
                'acquisition_id': context['acquisition']['acquisition_id'],
                'extraction_id': context['extraction']['extraction_id'],
                'source_id': context['policy']['source_id']}
    validate_evidence_tuple(evidence, context['acquisition'], context['extraction'],
                            [context['edition_snapshot']])
    return evidence


def _register_inventory(rows: list[dict], projects: list[dict]) -> tuple[list[dict], dict]:
    """Join only the original register key and matching legacy source wording."""
    by_id = {row['project_id']: row for row in projects}
    inventory, joins = [], {}
    for ordinal, row in enumerate(rows, 1):
        inventory.append({'inventory_id': 'Register', 'ordinal': ordinal, 'source_role': 'register',
                          'source_wording': row['Project Name'], 'source_fields': row,
                          'locator': f"Overall - Data, Unique ID {row['Unique ID']}",
                          'classification': 'official_register_record_not_necessarily_asset'})
        project_id = _project_id(row['Unique ID'])
        legacy = by_id.get(project_id)
        if (legacy and legacy['canonical_name'] == _text(row['Project Name'])
                and f"official register id={row['Unique ID']};" in legacy.get('notes', '')):
            joins[f'Register:{ordinal}'] = {'project_ids': [project_id],
                'source_wording': row['Project Name'],
                'rationale': 'Exact original register Unique ID and source wording retained by legacy importer'}
    return inventory, joins


def build_migration(root: Path, *, source_root: Path | None = None) -> dict:
    """Freeze full selected inventories and every exactly country-linked legacy row."""
    root, source_root = Path(root), Path(source_root or root)
    policy = json.loads((root / 'config/jetp-zaf-migration.json').read_text())
    crosswalk = migrate_sources(root, source_root=source_root)
    extracted = extract_inventory(source_root / 'data/jetp/documents', policy)
    projects = [row for row in crosswalk['inputs']['data/jetp/projects.csv']['rows'] if row['country'] == 'ZAF']
    register, joins = _register_inventory(extracted['register_rows'], projects)
    rows = register + extracted['report_rows']
    recipe_paths = ['scripts/jetp/_zaf_inventory.py', 'scripts/jetp/_zaf_positions.py',
                    'scripts/jetp/_country_migration.py', 'scripts/jetp/build_zaf_positions.py',
                    'scripts/jetp/build_zaf_investment_register.py', 'config/jetp-zaf-migration.json']
    recipe = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in recipe_paths}
    selected = [_source_context(source, crosswalk, [r for r in rows if r['source_role'] == source['role']],
                                recipe, policy) for source in policy['sources']]
    contexts = {row['role']: row for row in selected}
    positions = inventory_positions('ZAF', rows, projects, joins)
    for position in positions:
        source = contexts[position['source_role']]
        position.update(evidence=_evidence(position, source),
                        cutoff_date=source['policy']['cutoff_date'],
                        publication_date=None, recorded_at=None, historical_admission='unknown',
                        candidate_created_at=policy['recorded_at'], eligible_for_account=False,
                        date_role=('register_date_label_retained_not_transition'
                                   if position['source_role'] == 'register' else 'report_cutoff'))
    semantic = migrate_positions(extracted['register_rows'], payments=policy['payments'])
    for position, inventory in zip(semantic['reported_positions'], positions[:len(register)], strict=True):
        position.update(evidence=inventory['evidence'], inventory_position_id=inventory['record_id'])
    semantic['reported_positions'].extend({
        'record_kind': 'position_candidate', 'record_id': _identity('report-position', row),
        'measure': 'reported_table_funding_or_count', 'basis': 'source_table_position',
        'source_fields': row['source_fields'], 'original_label': row['source_wording'],
        'perimeter': row['perimeter'], 'cutoff_date': contexts['report']['policy']['cutoff_date'],
        'inventory_position_id': row['record_id'], 'evidence': row['evidence'],
        'transition_date': None, 'payment_amount': None, 'eligible_for_account': False,
        'historical_admission': 'unknown', 'admission_status': 'unadmitted_candidate',
        'reason': 'Retain source cells, units and totals separately; no cross-perimeter sum or payment inference',
    } for row in positions[len(register):])
    legacy = legacy_dispositions(crosswalk, 'ZAF', {})
    selected_ids = {row['row_id'] for row in legacy}
    views = {view: read_mvp_view(root, view, supported_versions={'mvp/1'}) for view in sorted(MVP_VIEWS)}
    names = defaultdict(list)
    for row in projects:
        names[row['canonical_name']].append(row['project_id'])
    boundaries = [{'inventory_id': 'Register', 'disposition': 'selected', 'row_count': len(register)}]
    boundaries.extend({'inventory_id': spec['table_id'], 'disposition': 'selected',
                       'row_count': spec['table_rows'] - spec['header_rows'],
                       'physical_pages': [spec['page']], 'perimeter': spec['perimeter']}
                      for spec in policy['report_tables'])
    result = {'schema_version': SCHEMA_VERSION, 'country': 'ZAF',
              'admission_status': 'unadmitted_candidate', 'writer_owner': 'legacy', 'publication_mode': 'legacy',
              'inputs': {name: {k: v for k, v in info.items() if k != 'rows'}
                         for name, info in crosswalk['inputs'].items()},
              'recipe_inputs': recipe, 'recovery_inputs': crosswalk['recovery_inputs'],
              'selected_sources': selected, 'inventory_positions': positions, **semantic,
              'legacy_dispositions': legacy,
              'legacy_evidence': [r for r in crosswalk['evidence'] if r['legacy_row_id'] in selected_ids],
              'legacy_unresolved': [r for r in crosswalk['unresolved'] if r['legacy_row_id'] in selected_ids],
              'inventory_boundaries': boundaries + policy['inventory_exclusions'],
              'identity_review': [{'source_wording': name, 'project_ids': ids,
                  'disposition': 'distinct_register_keys_relationship_unresolved',
                  'reason': 'Repeated programme names do not establish equality, component membership or disjoint funding'}
                  for name, ids in sorted(names.items()) if len(ids) > 1],
              'source_regime': policy['source_regime'], 'report_context': extracted['report_context'],
              'mvp_views': views,
              'comparison': {'legacy_rows_by_table': dict(Counter(row['path'] for row in legacy)),
                  'inventory_rows_by_table': dict(Counter(row['inventory_id'] for row in rows)),
                  'existing_project_ids': [row['project_id'] for row in projects],
                  'register_status_counts': dict(Counter(row['Status'] for row in extracted['register_rows'])),
                  'added_public_project_ids': [], 'removed_public_project_ids': [],
                  'financial_event_additions': 0, 'website_semantic_changes': [],
                  'public_payload_bytes': {view: len((json.dumps(data, ensure_ascii=False,
                      separators=(',', ':')) + '\n').encode()) for view, data in views.items()},
                  'public_payload_limit_bytes': policy['publication_limit_bytes'],
                  'reason': 'Detailed migration is a separate DVC sidecar; all six public MVP views remain legacy'}}
    validate_migration(result)
    return result


def validate_migration(result: dict) -> None:
    """Validate complete row coverage, evidence tuples and the unchanged public boundary."""
    if result['writer_owner'] != 'legacy' or result['publication_mode'] != 'legacy':
        raise ValueError('Candidate cannot transfer writer or publication ownership')
    if set(result['mvp_views']) != MVP_VIEWS:
        raise ValueError('Candidate must retain every MVP view')
    contexts = {row['role']: row for row in result['selected_sources']}
    for boundary in result['inventory_boundaries']:
        if boundary['disposition'] == 'selected':
            rows = [r for r in result['inventory_positions'] if r['inventory_id'] == boundary['inventory_id']]
            if sorted(row['ordinal'] for row in rows) != list(range(1, boundary['row_count'] + 1)):
                raise ValueError('Incomplete selected official inventory')
    for row in result['inventory_positions']:
        if row['transition_date'] is not None or row['payment_amount'] is not None:
            raise ValueError('Inventory position cannot manufacture a transition or payment')
        context = contexts[row['source_role']]
        validate_evidence_tuple(row['evidence'], context['acquisition'], context['extraction'],
                                [context['edition_snapshot']])
    if any(row['eligible_for_account'] for row in result['reported_positions']):
        raise ValueError('Unreconciled funding positions cannot enter an account')
    if any(row['disposition'] != 'retained_legacy_authority' or not row['original']
           for row in result['legacy_dispositions']):
        raise ValueError('Incomplete legacy disposition')
    if any(size > result['comparison']['public_payload_limit_bytes']
           for size in result['comparison']['public_payload_bytes'].values()):
        raise ValueError('Public payload needs compatible chunking before publication')


def _country_output(output: Path) -> bool:
    try:
        previous = json.loads(output.read_bytes())
        records = {'selected_sources', 'inventory_positions', 'reported_positions', 'event_candidates',
                   'legacy_dispositions', 'legacy_evidence', 'legacy_unresolved', 'inventory_boundaries',
                   'identity_review', 'source_regime'}
        objects = {'inputs', 'recipe_inputs', 'recovery_inputs', 'mvp_views', 'comparison', 'report_context'}
        fields = records | objects | {'schema_version', 'country', 'admission_status', 'writer_owner', 'publication_mode'}
        if (not isinstance(previous, dict) or previous.keys() != fields
                or previous['schema_version'] != SCHEMA_VERSION or previous['country'] != 'ZAF'
                or previous['admission_status'] != 'unadmitted_candidate'
                or not all(isinstance(previous[key], dict) for key in objects)
                or not all(isinstance(view, dict) for view in previous['mvp_views'].values())
                or not all(isinstance(previous[key], list)
                           and all(isinstance(row, dict) for row in previous[key]) for key in records)):
            return False
        sources = previous['selected_sources']
        inventory = previous['inventory_positions']
        if (len(sources) != 2 or {row.get('role') for row in sources} != {'register', 'report'}
                or not all(all(isinstance(row.get(key), dict) and row[key]
                               for key in ('policy', 'acquisition', 'edition_snapshot', 'extraction'))
                           for row in sources)
                or not inventory or {row.get('source_role') for row in inventory} != {'register', 'report'}
                or not all(isinstance(row.get('source_fields'), dict) and row['source_fields']
                           and isinstance(row.get('locator'), str) and row['locator'] for row in inventory)
                or len(previous['reported_positions']) != len(inventory)
                or not previous['legacy_dispositions'] or not previous['inventory_boundaries']):
            return False
        for view in ('ZAF', 'IDN', 'VNM', 'SEN'):
            payload = previous['mvp_views'][view]
            if (not isinstance(payload.get('projects'), list) or not payload['projects']
                    or not all(isinstance(row, dict) for row in payload['projects'])
                    or not isinstance(payload.get('record_count'), int)
                    or not isinstance(payload.get('country'), dict)):
                return False
        validate_migration(previous)
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def write_migration(root: Path, output: Path, *, source_root: Path | None = None) -> dict:
    """Validate the lexical destination before replacing one complete candidate."""
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


def main():
    io_args, extra = parse_io_args()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args(extra)
    if not io_args.input or len(io_args.input) != 1:
        parser.error('requires --input CHECKOUT_ROOT')
    validate_io(output=io_args.output, inputs=io_args.input)
    write_migration(Path(io_args.input[0]), Path(io_args.output), source_root=args.source_root)


if __name__ == '__main__':
    main()
