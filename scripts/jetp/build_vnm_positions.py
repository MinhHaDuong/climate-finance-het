"""Build the Vietnam inventory candidate beside the unchanged MVP authority."""

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
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
from jetp._vnm_inventory import extract_inventory


def encoded(value: object) -> bytes:
    """Canonical JSON recipe used for output hashes and the candidate artifact."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def build_migration(root: Path, *, source_root: Path | None = None) -> dict:
    """Select one frozen acquisition; new extraction never repairs old evidence."""
    root, source_root = Path(root), Path(source_root or root)
    policy_path = root / 'config/jetp-vnm-migration.json'
    policy = json.loads(policy_path.read_text())
    crosswalk = migrate_sources(root, source_root=source_root)
    attempts = [r for r in crosswalk['acquisitions']
                if r['source_id'] == policy['source_id']
                and r['retrieved_at'] == policy['retrieved_at']
                and r['document_sha256'] == policy['document_sha256']]
    if len(attempts) != 1 or attempts[0]['byte_status'] != 'available':
        raise ValueError('Exactly selected saved acquisition must be recoverable')
    acquisition = attempts[0]
    pdf = source_root / 'data/jetp/documents' / acquisition['storage_path']
    rows = extract_inventory(pdf)
    projects = [r for r in crosswalk['inputs']['data/jetp/projects.csv']['rows']
                if r['country'] == 'VNM']
    positions = inventory_positions('VNM', rows, projects, policy['identity_joins'])
    recipe_paths = ['scripts/jetp/_vnm_inventory.py', 'scripts/jetp/_country_migration.py',
                    'scripts/jetp/build_vnm_positions.py', 'config/jetp-vnm-migration.json']
    recipe = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in recipe_paths}
    import pdfplumber
    parser = {'name': 'pdfplumber', 'version': pdfplumber.__version__, 'recipe_inputs': recipe}
    extraction_id = _identity('extraction', [policy['document_sha256'], parser])
    extraction = {'extraction_id': extraction_id, 'document_sha256': policy['document_sha256'],
                  'parser': parser, 'output_sha256': hashlib.sha256(encoded(rows)).hexdigest(),
                  'locators': [r['locator'] for r in rows],
                  'recorded_at': policy['recorded_at'], 'recorded_by': policy['recorded_by'],
                  'admission_status': 'unadmitted_candidate'}
    edition = {'record_kind': 'edition', 'record_id': policy['edition_id']}
    snapshot = {'record_kind': 'edition_snapshot', 'edition': edition,
                'document_sha256': policy['document_sha256'],
                'acquisition_id': acquisition['acquisition_id'],
                'recorded_at': policy['recorded_at'], 'review_state': 'pending'}
    for position in positions:
        evidence = {'document_sha256': policy['document_sha256'], 'edition': edition,
                    'locator': position['locator'], 'acquisition_id': acquisition['acquisition_id'],
                    'extraction_id': extraction_id, 'source_id': policy['source_id']}
        validate_evidence_tuple(evidence, acquisition, extraction, [snapshot])
        position.update(evidence=evidence, publication_date=policy['publication_date'],
                        recorded_at=None, historical_admission='unknown',
                        candidate_created_at=policy['recorded_at'])
    legacy = legacy_dispositions(crosswalk, 'VNM', policy['legacy_observations'])
    selected_ids = {r['row_id'] for r in legacy}
    legacy_positions = [{
        'record_kind': 'position_candidate', 'record_id': row['candidate_record_ids'][0],
        'legacy_row_id': row['row_id'], 'classification': row['classification'],
        'source_assertion': row['original'], 'transition_date': None, 'payment_amount': None,
        'cutoff_date': None, 'missing_reason': 'source_date_role_requires_review',
        'recorded_at': None, 'historical_admission': 'unknown',
        'admission_status': 'unadmitted_candidate', 'review_state': 'pending',
        'candidate_created_at': policy['recorded_at'], 'eligible_for_account': False,
    } for row in legacy if row['candidate_record_ids']]
    views = {view: read_mvp_view(root, view, supported_versions={'mvp/1'})
             for view in sorted(MVP_VIEWS)}
    input_manifest = {name: {key: value for key, value in info.items() if key != 'rows'}
                      for name, info in crosswalk['inputs'].items()}
    result = {'schema_version': SCHEMA_VERSION, 'country': 'VNM',
              'admission_status': 'unadmitted_candidate', 'writer_owner': 'legacy',
              'publication_mode': 'legacy', 'inputs': input_manifest,
              'recipe_inputs': recipe, 'recovery_inputs': crosswalk['recovery_inputs'],
              'selected_acquisition': acquisition, 'edition_snapshot': snapshot,
              'extraction': extraction, 'inventory_positions': positions,
              'legacy_dispositions': legacy, 'legacy_position_candidates': legacy_positions,
              'legacy_evidence': [r for r in crosswalk['evidence'] if r['legacy_row_id'] in selected_ids],
              'legacy_unresolved': [r for r in crosswalk['unresolved'] if r['legacy_row_id'] in selected_ids],
              'inventory_boundaries': policy['inventory_boundaries'],
              'identity_review': policy['identity_review'], 'mvp_views': views,
              'comparison': {'legacy_rows_by_table': dict(Counter(r['path'] for r in legacy)),
                             'inventory_rows_by_annex': dict(Counter(r['annex'] for r in rows)),
                             'existing_project_ids': [r['project_id'] for r in projects],
                             'added_public_project_ids': [], 'removed_public_project_ids': [],
                             'named_identity_additions': 0, 'financial_event_additions': 0,
                             'candidate_inventory_rows_added': len(rows),
                             'website_semantic_changes': [],
                             'reason': 'Inventory sidecar only; all six MVP views retain legacy authority'}}
    validate_migration(result)
    return result


def validate_migration(result: dict) -> None:
    """Require a complete selected inventory and unchanged publication ownership."""
    if result['writer_owner'] != 'legacy' or result['publication_mode'] != 'legacy':
        raise ValueError('Country candidate cannot transfer ownership')
    if set(result['mvp_views']) != MVP_VIEWS:
        raise ValueError('Candidate must preserve all MVP views')
    for boundary in result['inventory_boundaries']:
        if boundary['disposition'] == 'selected':
            rows = [r for r in result['inventory_positions'] if r['annex'] == boundary['annex']]
            if sorted(r['ordinal'] for r in rows) != list(range(1, boundary['row_count'] + 1)):
                raise ValueError(f"Incomplete selected inventory {boundary['annex']}")
    for row in result['inventory_positions']:
        if row['transition_date'] is not None or row['payment_amount'] is not None:
            raise ValueError('Inventory cannot establish a transition or payment')
        validate_evidence_tuple(row['evidence'], result['selected_acquisition'],
                                result['extraction'], [result['edition_snapshot']])
    for row in result['legacy_dispositions']:
        if row['disposition'] != 'retained_legacy_authority' or not row['original']:
            raise ValueError('Missing legacy disposition or source wording')


def _country_output(output: Path) -> bool:
    """Recognize the bounded candidate contract, not just identifying markers."""
    try:
        previous = json.loads(output.read_bytes())
        records = {'inventory_positions', 'legacy_dispositions', 'legacy_position_candidates',
                   'legacy_evidence', 'legacy_unresolved', 'inventory_boundaries', 'identity_review'}
        objects = {'inputs', 'recipe_inputs', 'recovery_inputs', 'selected_acquisition',
                   'edition_snapshot', 'extraction', 'mvp_views', 'comparison'}
        fields = records | objects | {'schema_version', 'country', 'admission_status',
                                      'writer_owner', 'publication_mode'}
        if (not isinstance(previous, dict) or previous.keys() != fields
                or previous['schema_version'] != SCHEMA_VERSION or previous['country'] != 'VNM'
                or previous['admission_status'] != 'unadmitted_candidate'
                or not all(isinstance(previous[key], dict) for key in objects)
                or not all(isinstance(view, dict) for view in previous['mvp_views'].values())
                or not all(isinstance(previous[key], list)
                           and all(isinstance(row, dict) for row in previous[key]) for key in records)):
            return False
        validate_migration(previous)
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def write_migration(root: Path, output: Path, *, source_root: Path | None = None) -> dict:
    """Protect all accepted artifacts and atomically replace only our candidate."""
    root, output = Path(root).resolve(), Path(output)
    # Shared guard sees the lexical file before resolution can erase its alias.
    _protect_replacement(output, _country_output(output))
    output = output.resolve()
    source_root = Path(source_root or root).resolve()
    if output.suffix != '.json':
        raise ValueError('Country candidate output must end in .json')
    for checkout in {root, source_root}:
        releases = [p for p in (checkout / 'data/jetp/releases').rglob('*')
                    if p.is_file() and p != output]
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
    """Write one independently reviewable JSON artifact; large outputs use DVC."""
    io_args, extra = parse_io_args()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args(extra)
    inputs = io_args.input or []
    if len(inputs) != 1:
        parser.error('requires --input CHECKOUT_ROOT')
    validate_io(output=io_args.output, inputs=inputs)
    write_migration(Path(inputs[0]), Path(io_args.output), source_root=args.source_root)


if __name__ == '__main__':
    main()
