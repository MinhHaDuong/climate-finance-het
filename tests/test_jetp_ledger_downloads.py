"""0870 closeout: precise downloads, bounded descent, and recorded decisions."""

import csv
import hashlib
import json
from pathlib import Path

import pytest
from jetp._ledger_headers import LEDGER_DIR, file_stem, load_schema, read_table
from jetp.build_ledger_downloads import BULK, build_downloads, terminal_observation_ids

pytestmark = [pytest.mark.domain_jetp, pytest.mark.slow]
SITE = Path(__file__).resolve().parents[1] / 'deliverables/jetp-observatory'


def test_inventory_names_every_contract_table_and_preserves_exact_downloads(tmp_path):
    inventory = build_downloads(LEDGER_DIR, tmp_path)
    entries = {row['table']: row for row in inventory['tables']}
    schema = load_schema()
    assert set(entries) == {file_stem(table) for table in schema.tables} | {
        'line-fields/<document_id>', 'dry-searches', 'decisions.md', 'news-leads'}
    for table in schema.tables:
        entry = entries[file_stem(table)]
        rows, errors = read_table(LEDGER_DIR, table, schema)
        assert not errors
        assert entry['rows'] == len(rows)
        assert entry['keys'] == list(schema.keys[table])
        assert entry['fully_served'] == (table not in BULK)
        if not entry['fully_served']:
            assert entry['reason'] and not entry['files']
        for artifact in entry['files']:
            relative = artifact['path'].removeprefix('data/ledger/')
            raw = (tmp_path / relative).read_bytes()
            assert raw == (LEDGER_DIR / relative).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == artifact['sha256']
        assert all(p['partial'] and p['reason'] for p in entry['projections'])
    for path in tmp_path.rglob('*'):
        if path.is_file():
            assert path.stat().st_size < 512000, path
            assert path.read_bytes() == (SITE / 'data/ledger' / path.relative_to(tmp_path)).read_bytes()
    assert not (tmp_path / 'decisions.md').exists()


def test_perimeter_projections_are_exact_rows_and_resolve_to_the_three_documents():
    schema = load_schema()
    projection_dir = SITE / 'data/ledger'
    projected = {}
    for table, stem in [('observations', 'vnm-perimeter-observations'),
                        ('lines', 'vnm-perimeter-lines')]:
        view = json.loads((projection_dir / f'{stem}.json').read_text())
        assert view['fields'] == schema.header(table)
        full, errors = read_table(LEDGER_DIR, table, schema)
        assert not errors
        assert all(tuple(row) in full for row in view['rows'])
        projected[table] = [dict(zip(view['fields'], row)) for row in view['rows']]
    assert {o['value'] for o in projected['observations']} == {'7', '17'}
    assert all(o['subject_kind'] == 'perimeter' and o['status'] == 'accepted'
               for o in projected['observations'])
    assert {o['line_id'] for o in projected['observations']} == {
        line['line_id'] for line in projected['lines']}
    assert all('publisher_locator=' in line['notes'] for line in projected['lines'])
    with (projection_dir / 'coverage.csv').open(newline='') as handle:
        coverage = [r for r in csv.DictReader(handle)
                    if r['referent_kind'] == 'perimeter'
                    and r['referent_id'] == 'vnm-jetp-portfolio-2025']
    assert len(coverage) == 1
    assert set(coverage[0]['document_ids'].split(';')) == {
        'vnm-moit-newsletter-05-2025-07', 'vnm-eeas-jetp-project-progress-2025',
        'vnm-moit-project-index-2026'}


def test_served_decisions_keep_all_rows_and_reviewers_verbatim():
    view = json.loads((SITE / 'data/ledger/register-decisions.json').read_text())
    with (LEDGER_DIR / 'migration/1620-register-dispositions.csv').open(newline='') as handle:
        reader = csv.reader(handle)
        assert view['fields'] == next(reader)
        assert view['rows'] == list(reader)
    assert len(view['rows']) == 152
    for field in ('stance', 'stance_confidence', 'evidence', 'fable_verdict',
                  'codex_verdict', 'vibe_verdict', 'panel_decided_by'):
        assert field in view['fields']


@pytest.mark.parametrize('status', ['accepted', 'candidate', 'rejected', 'withdrawn'])
def test_terminal_counts_exclude_superseded_acceptances_even_if_successor_is_pending(status):
    schema = load_schema()
    records = [{'observation_id': 'prior', 'status': 'accepted', 'supersedes': None},
               {'observation_id': 'successor', 'status': status, 'supersedes': 'prior'}]
    rows = [tuple(record.get(field) for field in schema.header('observations'))
            for record in records]
    assert terminal_observation_ids(rows, schema) == (
        {'successor'} if status == 'accepted' else set())


def test_download_build_repairs_missing_sidecars_and_prunes_only_manifest_owned_files(tmp_path):
    inventory = build_downloads(LEDGER_DIR, tmp_path)
    sidecar = tmp_path / 'register-decisions.json'
    baseline = sidecar.read_bytes()
    untouched = tmp_path / 'coverage.csv'
    timestamp = untouched.stat().st_mtime_ns
    sidecar.unlink()
    obsolete = tmp_path / 'obsolete-owned.csv'
    obsolete.write_text('old generated output\n')
    user_file = tmp_path / 'user-note.txt'
    user_file.write_text('preserve this unrelated file\n')
    inventory['owned_files'].append('obsolete-owned.csv')
    (tmp_path / 'inventory.json').write_text(json.dumps(inventory))
    build_downloads(LEDGER_DIR, tmp_path)
    assert sidecar.read_bytes() == baseline
    assert untouched.stat().st_mtime_ns == timestamp
    assert not obsolete.exists()
    assert user_file.read_text() == 'preserve this unrelated file\n'
