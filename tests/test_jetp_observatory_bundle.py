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
    from jetp._bundle_inventory import routes

    manifest = {**routes(payloads), 'files': {
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


@pytest.mark.parametrize('before,after', [(True, 1), (False, 0), (1, True), (0, False), (1, 1.0)])
@pytest.mark.parametrize('container', ['scalar', 'list', 'dict'])
def test_semantic_comparison_retains_json_type_changes(before, after, container):
    from jetp._observatory_bundle import _changes

    if container == 'list':
        before, after = [before], [after]
    elif container == 'dict':
        before, after = {'value': before}, {'value': after}
    changes = list(_changes(before, after, 'field'))
    assert len(changes) == 1
    assert type(changes[0]['before']) is not type(changes[0]['after'])


@pytest.mark.parametrize('field', ['routes', 'downloads'])
@pytest.mark.parametrize('change', ['add', 'remove'])
def test_bundle_rejects_fabricated_or_stale_derived_inventory(tmp_path, field, change):
    import json
    import zipfile

    from jetp._observatory_bundle import compare_bundles, restore_bundle

    accepted, altered = tmp_path / 'accepted.zip', tmp_path / 'altered.zip'
    tiny_bundle(accepted)
    with zipfile.ZipFile(accepted) as source, zipfile.ZipFile(altered, 'w') as dest:
        for name in source.namelist():
            data = source.read(name)
            if name == 'manifest.json':
                manifest = json.loads(data)
                if change == 'add':
                    manifest[field].append('#fabricated' if field == 'routes' else 'data/fake.json')
                else:
                    manifest[field].pop()
                data = json.dumps(manifest).encode()
            dest.writestr(name, data)
    with pytest.raises(ValueError, match='inventory'):
        compare_bundles(accepted, altered)
    with pytest.raises(ValueError, match='inventory'):
        restore_bundle(altered, tmp_path / 'restored')
    assert not (tmp_path / 'restored').exists()


@pytest.mark.parametrize('alias', ['same', 'resolved', 'symlink', 'hardlink'])
@pytest.mark.parametrize('input_index', [0, 1])
def test_diff_cli_cannot_overwrite_either_archive(tmp_path, monkeypatch, alias, input_index):
    import sys

    from jetp.build_observatory_bundle import main

    archives = [tmp_path / 'accepted.zip', tmp_path / 'candidate.zip']
    for archive in archives:
        tiny_bundle(archive)
    target = archives[input_index]
    output = target
    if alias == 'resolved':
        (tmp_path / 'child').mkdir()
        output = tmp_path / 'child' / '..' / target.name
    elif alias in ('symlink', 'hardlink'):
        output = tmp_path / 'alias.zip'
        if alias == 'symlink':
            output.symlink_to(target)
        else:
            output.hardlink_to(target)
    before = [archive.read_bytes() for archive in archives]
    monkeypatch.setattr(sys, 'argv', ['bundle', '--mode', 'diff', '--root', str(tmp_path),
                                     '--input', *map(str, archives), '--output', str(output)])
    with pytest.raises(ValueError, match='separate|protected|alias'):
        main()
    assert [archive.read_bytes() for archive in archives] == before
    assert output.read_bytes() == before[input_index]


@pytest.mark.parametrize('name', ['config/jetp_observatory.yaml', 'scripts/jetp/build_observatory.py',
                                  'scripts/jetp/_observatory_data.py', 'data/jetp/projects.csv',
                                  'deliverables/jetp-observatory/data/ZAF.json'])
@pytest.mark.parametrize('alias', ['same', 'symlink', 'hardlink'])
def test_all_canonical_inputs_are_protected_from_output(tmp_path, name, alias):
    from jetp._observatory_bundle import _protect_output

    target = tmp_path / name
    target.parent.mkdir(parents=True)
    target.write_bytes(b'canonical input bytes')
    output = target
    if alias != 'same':
        output = tmp_path / 'outside-output.zip'
        if alias == 'symlink':
            output.symlink_to(target)
        else:
            output.hardlink_to(target)
    with pytest.raises(ValueError, match='separate|protected|alias'):
        _protect_output(tmp_path, output)
    assert target.read_bytes() == b'canonical input bytes'


def test_diff_cli_atomic_report_failure_preserves_prior_report(tmp_path, monkeypatch):
    import sys

    from jetp.build_observatory_bundle import main

    accepted, candidate = tmp_path / 'accepted.zip', tmp_path / 'candidate.zip'
    tiny_bundle(accepted)
    tiny_bundle(candidate)
    output = tmp_path / 'report.json'
    output.write_bytes(b'previous complete report')

    def interrupted_replace(source, destination):
        assert output.read_bytes() == b'previous complete report'
        raise OSError('interrupted report publication')

    monkeypatch.setattr('os.replace', interrupted_replace)
    monkeypatch.setattr(sys, 'argv', ['bundle', '--mode', 'diff', '--root', str(tmp_path),
                                     '--input', str(accepted), str(candidate), '--output', str(output)])
    with pytest.raises(OSError, match='interrupted report publication'):
        main()
    assert output.read_bytes() == b'previous complete report'
