"""Freeze legacy source rows into an unadmitted, recoverable evidence crosswalk.

The candidate never selects the latest acquisition, infers publication equivalence,
or assigns historical admission dates. Explicit tuples can resolve to saved bytes;
legacy gaps remain review work, while every original cell survives in the snapshot.
"""

import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jetp._bundle_inventory import _dvc_sources, _source_record
from jetp._contracts import SCHEMA_VERSION as CORE_SCHEMA_VERSION
from jetp._contracts import ContractError, validate_evidence_tuple

SCHEMA_VERSION = 'source-crosswalk/1'
ACQUISITION_TABLES = {'manifest.csv', 'vnm-pilot-manifest.csv'}
EVIDENCE_TABLES = {'events.csv', 'implementation-events.csv', 'plan-projects.csv', 'project-source-links.csv',
                   'source-claims.csv', 'evidence-links.csv'}
OWNERS = {'authority-coverage.csv': 'authority_coverage',
          'project-coverage.csv': 'project_coverage', 'dry-searches.csv': 'observation_attempt',
          'news-leads.csv': 'news_lead', 'events.csv': 'financial_event',
          'implementation-events.csv': 'implementation_event'}


def _identity(kind: str, value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return kind + '-' + hashlib.sha256(encoded.encode()).hexdigest()


def _read_inputs(root: Path) -> tuple[dict, list[dict]]:
    inputs, rows = {}, []
    for path in sorted((root / 'data/jetp').glob('*.csv')):
        raw = path.read_bytes()
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        values = list(reader)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or any(None in row or None in row.values() for row in values):
            raise ContractError(f'Malformed CSV cannot be preserved losslessly: {path.name}')
        name = path.relative_to(root).as_posix()
        inputs[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'headers': headers,
                        'row_count': len(values), 'rows': values}
        occurrences: Counter[str] = Counter()
        for number, row in enumerate(values, 2):
            identity_row = {key: value for key, value in row.items() if value != ''}
            content_id = _identity('content', identity_row)
            occurrences[content_id] += 1
            rows.append({'row_id': _identity('row', [name, identity_row, occurrences[content_id]]),
                         'path': name, 'row_number': number, 'row': row})
    return inputs, rows


def _base(item: dict, kind: str, explicit: str = '') -> dict:
    row = item['row']
    return {'record_id': explicit or _identity(kind, item['row_id']), 'record_kind': kind,
            'legacy_row_id': item['row_id'], 'recorded_at': row.get('recorded_at') or None,
            'recorded_by': row.get('recorded_by') or None,
            'admission_status': 'declared' if row.get('recorded_at') else 'unknown'}


def _owner(name: str) -> str:
    if name.endswith('-observations.csv'):
        return 'country_observation'
    return OWNERS.get(name, name.removesuffix('.csv').replace('-', '_'))


def _source(item: dict) -> dict:
    row = item['row']
    result = _base(item, 'source_revision', row.get('source_revision_id', ''))
    result.update(source_revision_id=result['record_id'], source_id=row.get('source_id'),
                  metadata=dict(row), source_kind=row.get('source_kind') or 'unknown',
                  intelligence_role_default=row.get('intelligence_role_default') or 'unknown',
                  triage_state=row.get('triage_state') or 'unknown')
    return result


def _material(row: dict, source_root: Path, cached: dict) -> dict:
    digest = row.get('document_sha256') or row.get('sha256') or None
    result = {'document_sha256': digest, 'byte_status': 'unresolved',
              'storage_path': row.get('storage_path') or None, 'byte_reason': 'missing_storage_path'}
    if not digest:
        result['byte_reason'] = 'missing_document_hash'
        return result
    if len(digest) != 64 or any(char not in '0123456789abcdef' for char in digest):
        result['byte_reason'] = 'invalid_document_hash'
        return result
    if not row.get('storage_path'):
        return result
    inventory, path, _ = _source_record(row, source_root, cached)
    result['location_kind'] = inventory['location_kind']
    if not path.is_file():
        result['byte_reason'] = 'saved_bytes_unavailable'
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        result['byte_reason'] = 'saved_bytes_hash_mismatch'
    elif inventory.get('dvc_md5') and hashlib.md5(path.read_bytes()).hexdigest() != inventory['dvc_md5']:
        result['byte_reason'] = 'dvc_object_hash_mismatch'
    else:
        result.update(byte_status='available', byte_reason=None)
    for key in ('dvc_md5', 'dvc_index_md5'):
        if key in inventory:
            result[key] = inventory[key]
    return result


def _acquisition(item: dict, source_root: Path, cached: dict) -> dict:
    row = item['row']
    result = _base(item, 'acquisition', row.get('acquisition_id', ''))
    status = row.get('status') or row.get('collection_status') or 'unknown'
    outcome = {'collected': 'saved', 'saved': 'saved', 'not_modified': 'not_modified',
               'blocked': 'blocked'}.get(status, 'failed')
    result.update(acquisition_id=result['record_id'], source_id=row.get('source_id') or None,
                  source_revision_id=row.get('source_revision_id') or None,
                  check_id=None, sweep_id=None, check_role=None,
                  retrieved_at=row.get('retrieved_at') or None, legacy_status=status, outcome=outcome,
                  requested_url=row.get('requested_url') or row.get('url') or None,
                  final_url=row.get('final_url') or None,
                  report_edition_id=row.get('report_edition_id') or None,
                  error=row.get('error') or None)
    result.update(_material(row, source_root, cached))
    if outcome not in {'saved', 'not_modified'}:
        result.update(byte_status='unresolved', byte_reason='failed_acquisition')
    result['support_group_id'] = ('sha256:' + result['document_sha256']
                                  if result['document_sha256'] else None)
    result['independence'] = 'unknown'
    return result


def _add_declared_material(result: dict, items: list[dict]) -> None:
    """Retain declared editions and extraction recipes without inventing metadata."""
    editions, extractions = {}, {}
    for acquisition in result['acquisitions']:
        identity, digest = acquisition['report_edition_id'], acquisition['document_sha256']
        if identity:
            editions.setdefault(identity, {'report_edition_id': identity, 'record_kind': 'edition',
                                            'record_id': identity, 'recorded_at': None,
                                            'admission_status': 'unknown', 'publication_date': None,
                                            'publication_precision': 'unknown',
                                            'metadata_status': 'unresolved'})
        if identity and digest and acquisition['outcome'] in {'saved', 'not_modified'}:
            result['edition_snapshots'].append({
                'mapping_id': _identity('edition-snapshot', [identity, acquisition['acquisition_id'], digest]),
                'report_edition_id': identity, 'document_sha256': digest,
                'acquisition_id': acquisition['acquisition_id'],
                'legacy_row_id': acquisition['legacy_row_id'], 'review_status': 'legacy_declared'})
    for item in items:
        row = item['row']
        identity = row.get('extraction_id')
        digest = row.get('document_sha256') or row.get('sha256')
        locator = row.get('locator')
        if not (identity and digest and locator and row.get('parser_version')):
            continue
        extraction = {'extraction_id': identity, 'record_id': identity, 'record_kind': 'extraction',
                      'document_sha256': digest, 'parser_version': row['parser_version'],
                      'locators': [locator], 'recorded_at': row.get('recorded_at') or None,
                      'admission_status': 'declared' if row.get('recorded_at') else 'unknown',
                      'output_sha256': row.get('output_sha256') or None,
                      'parser_config': row.get('parser_config') or None,
                      'parser_config_sha256': row.get('parser_config_sha256') or None,
                      'correction_instructions': row.get('correction_instructions') or None,
                      'translation_author': row.get('translation_author') or None,
                      'recipe_status': 'legacy_declared'}
        previous = extractions.get(identity)
        recipe_keys = ('document_sha256', 'parser_version', 'parser_config', 'parser_config_sha256',
                       'output_sha256', 'correction_instructions', 'translation_author')
        if previous and any(previous[key] != extraction[key] for key in recipe_keys):
            previous['recipe_status'] = 'conflicting_declarations'
        elif previous:
            previous['locators'] = sorted(set(previous['locators'] + [locator]))
        else:
            extractions[identity] = extraction
    result['editions'] = list(editions.values())
    result['extractions'] = list(extractions.values())


def _acquisition_reasons(acquisition: dict | None, source: str | None, digest: str | None) -> list:
    reasons = []
    if acquisition:
        if acquisition['source_id'] != source:
            reasons.append('acquisition_source_mismatch')
        if acquisition['document_sha256'] != digest:
            reasons.append('acquisition_hash_mismatch')
        if acquisition['byte_status'] != 'available':
            reasons.append(acquisition['byte_reason'])
        if acquisition['source_revision_status'] == 'invalid':
            reasons.append('acquisition_source_revision_mismatch')
    return reasons


def _evidence(item: dict, acquisitions: dict, extractions: dict, snapshots: set) -> dict:
    row = item['row']
    result = _base(item, 'evidence', row.get('evidence_id', ''))
    digest = row.get('document_sha256') or row.get('sha256') or None
    source = row.get('source_id') or None
    selected = acquisitions.get(row.get('acquisition_id'), [])
    reasons = []
    if not row.get('acquisition_id'):
        reasons.append('missing_exact_acquisition')
    elif len(selected) != 1:
        reasons.append('ambiguous_acquisition' if selected else 'unknown_acquisition')
    acquisition = selected[0] if len(selected) == 1 else None
    if not digest:
        reasons.append('missing_exact_hash')
    if not source:
        reasons.append('missing_source_identity')
    reasons.extend(_acquisition_reasons(acquisition, source, digest))
    edition, extraction_id = row.get('report_edition_id') or None, row.get('extraction_id') or None
    if not edition or (edition, digest) not in snapshots:
        reasons.append('missing_edition_snapshot')
    extraction = extractions.get(extraction_id)
    locator = row.get('locator') or row.get('section') or None
    if not extraction:
        reasons.append('missing_exact_extraction')
    elif extraction['recipe_status'] != 'legacy_declared' or extraction['document_sha256'] != digest:
        reasons.append('extraction_hash_or_recipe_mismatch')
    elif locator not in extraction['locators']:
        reasons.append('extraction_locator_mismatch')
    if not locator:
        reasons.append('missing_locator')
    if not reasons:
        validate_evidence_tuple(
            {'document_sha256': digest, 'locator': locator,
             'edition': {'record_kind': 'edition', 'record_id': edition}}, acquisition, extraction,
            [{'record_kind': 'edition_snapshot', 'document_sha256': value,
              'edition': {'record_kind': 'edition', 'record_id': identity}}
             for identity, value in snapshots])
    target = next((row[key] for key in ('event_id', 'implementation_event_id', 'claim_id', 'link_id',
                                       'observation_id', 'plan_project_id', 'project_id') if row.get(key)), item['row_id'])
    result.update(evidence_id=result['record_id'], source_id=source,
                  target={'record_kind': _owner(Path(item['path']).name), 'record_id': target},
                  acquisition_id=row.get('acquisition_id') or None, document_sha256=digest,
                  report_edition_id=edition, extraction_id=extraction_id, locator=locator,
                  support_role=row.get('support_role') or 'unknown',
                  intelligence_role=row.get('intelligence_role') or 'unknown',
                  origin_rationale=row.get('origin_rationale') or None,
                  upstream_status=row.get('upstream_status') or 'unknown',
                  independence='unknown', support_group_id='sha256:' + digest if digest else None,
                  status='unresolved' if reasons else 'resolved', reasons=reasons)
    return result


def _validate_acquisitions(result: dict) -> None:
    revisions = {record['source_revision_id']: record for record in result['sources']}
    for records, key in ((result['sources'], 'source_revision_id'),
                         (result['acquisitions'], 'acquisition_id')):
        if len({record[key] for record in records}) != len(records):
            raise ContractError(f'Duplicate explicit {key}; immutable identities require review')
    available = {record['document_sha256']: record for record in result['acquisitions']
                 if record['byte_status'] == 'available'}
    for record in result['acquisitions']:
        revision = revisions.get(record['source_revision_id'])
        record['source_revision_status'] = ('unknown' if not record['source_revision_id'] else
                                            'valid' if revision and revision['source_id'] == record['source_id']
                                            else 'invalid')
        material = available.get(record['document_sha256'])
        if material and record['byte_reason'] == 'missing_storage_path' and record['outcome'] in {'saved', 'not_modified'}:
            record.update(byte_status='available', byte_reason=None,
                          recovered_storage_path=material['storage_path'],
                          location_kind=material['location_kind'])


def migrate_sources(root: Path, *, source_root: Path | None = None) -> dict:
    """Return a deterministic candidate, reading available checkout/DVC bytes only."""
    root, source_root = Path(root), Path(source_root or root)
    inputs, items = _read_inputs(root)
    cached = _dvc_sources(root, source_root)
    result = {'schema_version': SCHEMA_VERSION, 'core_contract_schema_version': CORE_SCHEMA_VERSION,
              'admission_status': 'unadmitted_candidate', 'inputs': inputs, 'mappings': [],
              'recovery_inputs': {},
              'sources': [], 'acquisitions': [], 'editions': [], 'edition_snapshots': [],
              'extractions': [], 'evidence': [], 'unresolved': [], 'retained': []}
    pointer = root / 'data/jetp/documents.dvc'
    if pointer.is_file():
        result['recovery_inputs'][pointer.relative_to(root).as_posix()] = {
            'sha256': hashlib.sha256(pointer.read_bytes()).hexdigest()}
    for item in items:
        name = Path(item['path']).name
        record = (_source(item) if name == 'sources.csv' else
                  _acquisition(item, source_root, cached) if name in ACQUISITION_TABLES else None)
        if record:
            result['sources' if name == 'sources.csv' else 'acquisitions'].append(record)
        retained = {**_base(item, 'retained'), 'owner': _owner(name), 'row': item['row']}
        result['retained'].append(retained)
        result['mappings'].append({key: item[key] for key in ('row_id', 'path', 'row_number')} | {
            'record_ids': [retained['record_id']] + ([record['record_id']] if record else []),
            'disposition': 'migrated' if record else 'retained_for_owner', 'owner': _owner(name),
            'transformation_version': SCHEMA_VERSION, 'review_state': 'pending',
            'reason': 'Frozen source/acquisition fields; unknown history remains unknown' if record else
                      'Original row retained for its existing domain owner; no domain migration'})
    _validate_acquisitions(result)
    _add_declared_material(result, items)
    acquisitions: dict[str, list] = defaultdict(list)
    for acquisition in result['acquisitions']:
        acquisitions[acquisition['acquisition_id']].append(acquisition)
    extractions = {record['extraction_id']: record for record in result['extractions']}
    snapshots = {(record['report_edition_id'], record['document_sha256'])
                 for record in result['edition_snapshots']}
    for item, mapping in zip(items, result['mappings'], strict=True):
        name = Path(item['path']).name
        if name not in EVIDENCE_TABLES and not name.endswith('-observations.csv'):
            continue
        evidence = _evidence(item, acquisitions, extractions, snapshots)
        result['evidence'].append(evidence)
        mapping['record_ids'].append(evidence['evidence_id'])
        if evidence['status'] == 'unresolved':
            result['unresolved'].append({'evidence_id': evidence['evidence_id'],
                                         'legacy_row_id': item['row_id'], 'reasons': evidence['reasons']})
    return result
