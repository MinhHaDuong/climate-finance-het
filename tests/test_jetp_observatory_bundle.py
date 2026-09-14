"""Recovery and candidate isolation for the accepted static observatory."""

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def site_hashes(root):
    """Include rendering assets and every download in the byte comparison."""
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


@pytest.mark.integration
def test_interrupted_candidate_preserves_accepted_and_restores_offline(tmp_path, monkeypatch):
    from jetp._observatory_bundle import build_candidate, freeze_bundle, restore_bundle

    accepted = tmp_path / 'accepted.zip'
    freeze_bundle(ROOT, accepted)
    repeat = tmp_path / 'repeated.zip'
    freeze_bundle(ROOT, repeat)
    assert accepted.read_bytes() == repeat.read_bytes()
    archive_hash = hashlib.sha256(accepted.read_bytes()).hexdigest()
    canonical = site_hashes(ROOT / 'deliverables/jetp-observatory')
    candidate = tmp_path / 'candidate.zip'
    candidate.write_bytes(b'previous complete candidate')
    calls = []

    def interrupted(root, view, output):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"partial":true}')
        calls.append(view)
        raise RuntimeError('interrupted after one output')

    with pytest.raises(RuntimeError, match='interrupted'):
        build_candidate(ROOT, candidate, accepted=accepted, builder=interrupted)
    assert len(calls) == 1
    assert candidate.read_bytes() == b'previous complete candidate'
    assert hashlib.sha256(accepted.read_bytes()).hexdigest() == archive_hash
    assert site_hashes(ROOT / 'deliverables/jetp-observatory') == canonical

    def forbidden(*args, **kwargs):
        raise AssertionError('Restoration must not call Git, DVC or the network')

    monkeypatch.setattr('subprocess.run', forbidden)
    monkeypatch.setattr('subprocess.check_output', forbidden)
    monkeypatch.setattr('socket.create_connection', forbidden)
    restored = tmp_path / 'restored'
    restore_bundle(accepted, restored)
    assert site_hashes(restored) == canonical


def test_semantic_diff_requires_evidence_for_intentional_changes(tmp_path):
    """A declared scientific change needs source, reviewer and rationale."""
    from jetp._observatory_bundle import compare_bundles

    with pytest.raises(ValueError, match='source|reviewer|rationale'):
        compare_bundles(tmp_path / 'accepted.zip', tmp_path / 'candidate.zip',
                        intentional_paths={'site/data/ZAF.json/country/headline': {}})


def tiny_bundle(path, *, headline='Accepted headline', revision='before', event_date=None):
    """A complete miniature site with a scientific field and build metadata."""
    import json
    import zipfile

    payloads = {f'site/{name}': b'asset' for name in ('index.html', 'app.js', 'styles.css')}
    payloads['site/data/overview.json'] = json.dumps({
        'provenance': {'input_git_sha': revision}}).encode()
    payloads['site/data/comparison.json'] = b'{"projects":[]}'
    for code in ('ZAF', 'IDN', 'VNM', 'SEN'):
        payloads[f'site/data/{code}.json'] = json.dumps({
            'country': {'headline': headline if code == 'ZAF' else 'Unchanged'},
            'projects': [{'id': code + '-one', 'date': event_date}]}).encode()
    manifest = {'routes': ['#project/ZAF-one'], 'files': {
        name: {'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data)}
        for name, data in payloads.items()}}
    with zipfile.ZipFile(path, 'w') as archive:
        for name, data in payloads.items():
            archive.writestr(name, data)
        archive.writestr('manifest.json', json.dumps(manifest))


def test_semantic_diff_separates_reviewed_science_metadata_and_unknown(tmp_path):
    from jetp._observatory_bundle import compare_bundles

    accepted, candidate = tmp_path / 'accepted.zip', tmp_path / 'candidate.zip'
    tiny_bundle(accepted)
    tiny_bundle(candidate, headline='Revised headline', revision='after', event_date='2026-01-01')
    path = 'site/data/ZAF.json/country/headline'
    evidence = {'source': 'official-report-page-4', 'reviewer': 'reviewer-one',
                'rationale': 'Corrected reported allocation, not a payment'}
    report = compare_bundles(accepted, candidate, intentional_paths={path: evidence})
    assert [row['path'] for row in report['intentional_scientific']] == [path]
    assert report['intentional_scientific'][0]['evidence'] == evidence
    assert [row['path'] for row in report['metadata_only']] == [
        'site/data/overview.json/provenance/input_git_sha']
    assert len(report['unexplained']) == 4
    assert all(row['path'].endswith('/projects/0/date') for row in report['unexplained'])


def test_restore_rejects_tampered_download_before_creating_destination(tmp_path):
    import zipfile

    from jetp._observatory_bundle import restore_bundle

    accepted = tmp_path / 'accepted.zip'
    tiny_bundle(accepted)
    tampered = tmp_path / 'tampered.zip'
    with zipfile.ZipFile(accepted) as source, zipfile.ZipFile(tampered, 'w') as dest:
        for name in source.namelist():
            dest.writestr(name, b'{"projects":[]}' if name.endswith('ZAF.json') else source.read(name))
    restored = tmp_path / 'restored'
    with pytest.raises(ValueError, match='hash mismatch'):
        restore_bundle(tampered, restored)
    assert not restored.exists()


def test_inventory_preserves_duplicate_rows_and_nonwebsite_keys():
    from jetp._bundle_inventory import table_inventory

    inventory = table_inventory(b'project_id,source_id,status\np1,s1,blocked\np1,s1,blocked\np2,s2,found\n')
    assert inventory['headers'] == ['project_id', 'source_id', 'status']
    assert inventory['row_count'] == 3
    assert inventory['row_keys']['project_id'] == ['p1', 'p1', 'p2']
    assert inventory['duplicate_rows'][0]['count'] == 2
    assert inventory['row_locators'] == [2, 3, 4]
