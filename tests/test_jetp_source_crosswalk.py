"""Preserve historical evidence identities during candidate source migration."""

import csv
import hashlib
import json
from pathlib import Path

from jetp._source_crosswalk import migrate_sources


def table(root, name, rows):
    path = root / 'data/jetp' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def saved(root, content):
    digest = hashlib.sha256(content).hexdigest()
    path = Path('objects') / digest[:2] / f'{digest}.txt'
    target = root / 'data/jetp/documents' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return digest, str(path)


def attempt(source, identity, digest='', storage='', edition='edition-original'):
    return dict(source_id=source, acquisition_id=identity,
                retrieved_at='2026-09-01T12:00:00Z', status='collected' if digest else 'failed',
                sha256=digest, storage_path=storage, report_edition_id=edition,
                final_url=f'https://example.test/{source}', error='' if digest else 'timeout')


def fixture(root):
    old, old_path = saved(root, b'Original report')
    table(root, 'sources.csv', [dict(source_id='official', url='https://example.test/report',
                                   title='Report', publisher='Ministry', authority_category='government'),
                               dict(source_id='mirror', url='https://mirror.test/report',
                                    title='Report', publisher='Mirror')])
    rows = [attempt('official', 'a-old', old, old_path)]
    table(root, 'manifest.csv', rows)
    table(root, 'events.csv', [dict(event_id='old-assertion', source_id='official',
                                  document_sha256=old, locator='p1', acquisition_id='a-old',
                                  report_edition_id='edition-original', extraction_id='extract-old',
                                  parser_version='fixture/1')])
    return old, old_path, rows


def test_refresh_keeps_original_bytes_and_distinct_attempts(tmp_path):
    old, old_path, rows = fixture(tmp_path)
    before = migrate_sources(tmp_path)
    changed, changed_path = saved(tmp_path, b'Revised report')
    rows.extend([attempt('official', 'a-new', changed, changed_path, 'edition-revised'),
                 attempt('mirror', 'a-mirror', old, old_path), attempt('official', 'a-fail')])
    table(tmp_path, 'manifest.csv', rows)
    after = migrate_sources(tmp_path)
    evidence = after['evidence'][0]
    assert evidence['status'] == 'resolved'
    assert evidence['document_sha256'] == old
    assert evidence['acquisition_id'] == 'a-old'
    assert evidence['extraction_id'] == 'extract-old'
    assert evidence['evidence_id'] == before['evidence'][0]['evidence_id']
    assert len(after['acquisitions']) == 4
    assert len({row['acquisition_id'] for row in after['acquisitions']}) == 4
    assert all(row.get('check_id') is None for row in after['acquisitions'])
    assert all(row.get('sweep_id') is None for row in after['acquisitions'])
    assert evidence['report_edition_id'] == 'edition-original'
    assert json.dumps(after, sort_keys=True) == json.dumps(migrate_sources(tmp_path), sort_keys=True)
