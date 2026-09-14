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
    build_candidate(ROOT, candidate, accepted=accepted)
    previous_candidate = candidate.read_bytes()
    calls = []

    def interrupted(root, view, output):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"partial":true}')
        calls.append(view)
        raise RuntimeError('interrupted after one output')

    with pytest.raises(RuntimeError, match='interrupted'):
        build_candidate(ROOT, candidate, accepted=accepted, builder=interrupted)
    assert len(calls) == 1
    assert candidate.read_bytes() == previous_candidate
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
    from jetp._observatory_bundle import write_comparison

    write_comparison(tmp_path, accepted, candidate, output)
    previous_report = output.read_bytes()

    def interrupted_replace(source, destination):
        assert output.read_bytes() == previous_report
        raise OSError('interrupted report publication')

    monkeypatch.setattr('os.replace', interrupted_replace)
    monkeypatch.setattr(sys, 'argv', ['bundle', '--mode', 'diff', '--root', str(tmp_path),
                                     '--input', str(accepted), str(candidate), '--output', str(output)])
    with pytest.raises(OSError, match='interrupted report publication'):
        main()
    assert output.read_bytes() == previous_report


@pytest.mark.parametrize('mode', ['freeze', 'candidate', 'diff'])
@pytest.mark.parametrize('name', ['config/jetp_observatory.yaml', 'scripts/jetp/build_observatory.py',
                                  'scripts/jetp/_observatory_data.py'])
def test_cli_modes_preserve_canonical_config_and_code(tmp_path, monkeypatch, mode, name):
    import sys

    from jetp.build_observatory_bundle import main

    target = tmp_path / name
    target.parent.mkdir(parents=True)
    target.write_bytes(b'canonical bytes')
    accepted, candidate = tmp_path / 'accepted.zip', tmp_path / 'candidate.zip'
    tiny_bundle(accepted)
    tiny_bundle(candidate)
    arguments = ['bundle', '--mode', mode, '--root', str(tmp_path), '--output', str(target)]
    if mode == 'candidate':
        arguments += ['--input', str(accepted)]
    elif mode == 'diff':
        arguments += ['--input', str(accepted), str(candidate)]
    monkeypatch.setattr(sys, 'argv', arguments)
    with pytest.raises(ValueError, match='separate|protected|alias'):
        main()
    assert target.read_bytes() == b'canonical bytes'


def test_boolean_numeric_changes_need_explicit_scientific_review(tmp_path):
    from jetp._observatory_bundle import compare_bundles

    accepted, candidate = tmp_path / 'accepted.zip', tmp_path / 'candidate.zip'
    tiny_bundle(accepted, event_date=True)
    tiny_bundle(candidate, event_date=1)
    unexplained = compare_bundles(accepted, candidate)
    assert len(unexplained['unexplained']) == 4
    assert not unexplained['metadata_only']
    path = 'site/data/ZAF.json/projects/0/date'
    documented = compare_bundles(accepted, candidate, intentional_paths={path: {
        'source': 'fixture-source', 'reviewer': 'fixture-reviewer', 'rationale': 'Explicit test change'}})
    assert [row['path'] for row in documented['intentional_scientific']] == [path]
    assert len(documented['unexplained']) == 3


@pytest.mark.parametrize('mode', ['freeze', 'candidate'])
@pytest.mark.parametrize('alias', ['same', 'hardlink'])
def test_external_source_recovery_bytes_cannot_be_archive_output(tmp_path, monkeypatch, mode, alias):
    from jetp import _observatory_bundle as bundles

    root = tmp_path / 'checkout'
    (root / 'deliverables/jetp-observatory').mkdir(parents=True)
    source = tmp_path / 'external-cache-object'
    source.write_bytes(b'verified source bytes')
    output = source
    if alias == 'hardlink':
        output = tmp_path / 'output.zip'
        output.hardlink_to(source)
    monkeypatch.setattr(bundles, '_capture', lambda *args: (
        {'sources': [{'recovery_location': str(source)}]}, {}))

    def unsafe_write(*args):
        raise AssertionError('Archive writer reached a protected source destination')

    monkeypatch.setattr(bundles, '_write_bundle', unsafe_write)
    rejection = FileExistsError if mode == 'freeze' else ValueError
    with pytest.raises(rejection):
        if mode == 'freeze':
            bundles.freeze_bundle(root, output, source_root=tmp_path)
        else:
            accepted = tmp_path / 'accepted.zip'
            tiny_bundle(accepted)
            bundles.build_candidate(root, output, accepted=accepted, source_root=tmp_path,
                                    builder=lambda *args: None)
    assert source.read_bytes() == b'verified source bytes'


@pytest.mark.parametrize('writer', ['candidate', 'comparison'])
@pytest.mark.parametrize('filename', ['candidate.zip.dvc', 'README.md', '.gitignore',
                                      'release.json', 'other.zip'])
@pytest.mark.parametrize('alias', ['direct', 'symlink', 'hardlink'])
@pytest.mark.parametrize('directory', ['data/jetp/releases', 'scratch'])
def test_writers_preserve_unrelated_outputs(tmp_path, monkeypatch, writer, filename, alias, directory):
    from jetp import _observatory_bundle as bundles

    accepted = tmp_path / 'accepted.zip'
    tiny_bundle(accepted)
    target = tmp_path / directory / filename
    target.parent.mkdir(parents=True)
    target.write_bytes(b'{"release_id":"accepted"}\n')
    output = target
    if alias != 'direct':
        output = tmp_path / 'output-alias'
        if alias == 'symlink':
            output.symlink_to(target)
        else:
            output.hardlink_to(target)
    (tmp_path / bundles.SITE).mkdir(parents=True)
    manifest, payloads = bundles._read_bundle(accepted)
    monkeypatch.setattr(bundles, '_capture', lambda *args: ({**manifest, 'sources': []}, payloads))
    before = site_hashes(tmp_path)
    with pytest.raises(ValueError, match='protected|recognized|alias'):
        if writer == 'candidate':
            bundles.build_candidate(tmp_path, output, accepted=accepted, builder=lambda *args: None)
        else:
            bundles.write_comparison(tmp_path, accepted, accepted, output)
    assert site_hashes(tmp_path) == before


@pytest.mark.parametrize('writer', ['candidate', 'comparison'])
def test_recognized_outputs_allow_deterministic_reruns(tmp_path, monkeypatch, writer):
    from jetp import _observatory_bundle as bundles

    accepted = tmp_path / 'accepted.zip'
    tiny_bundle(accepted)
    (tmp_path / bundles.SITE).mkdir(parents=True)
    manifest, payloads = bundles._read_bundle(accepted)
    monkeypatch.setattr(bundles, '_capture', lambda *args: ({**manifest, 'sources': []}, payloads))
    output = tmp_path / 'data/jetp/releases' / ('candidate.zip' if writer == 'candidate' else 'report.json')

    def write():
        if writer == 'candidate':
            bundles.build_candidate(tmp_path, output, accepted=accepted, builder=lambda *args: None)
        else:
            bundles.write_comparison(tmp_path, accepted, accepted, output)

    write()
    before = output.read_bytes()
    write()
    assert output.read_bytes() == before


@pytest.mark.parametrize('writer,previous_kind', [('candidate', 'baseline'),
                                                ('candidate', 'comparison'),
                                                ('comparison', 'baseline'),
                                                ('comparison', 'candidate')])
def test_writers_refuse_other_output_kinds(tmp_path, monkeypatch, writer, previous_kind):
    from jetp import _observatory_bundle as bundles

    accepted = tmp_path / 'accepted.zip'
    tiny_bundle(accepted)
    manifest, payloads = bundles._read_bundle(accepted)
    output = tmp_path / 'prior-output'
    if previous_kind == 'comparison':
        bundles.write_comparison(tmp_path, accepted, accepted, output)
    else:
        bundles._write_bundle(output, {**manifest, 'kind': previous_kind,
                                      'accepted_sha256': 'fixture'}, payloads)
    before = output.read_bytes()
    with pytest.raises(ValueError, match='recognized'):
        if writer == 'candidate':
            bundles.build_candidate(tmp_path, output, accepted=accepted)
        else:
            bundles.write_comparison(tmp_path, accepted, accepted, output)
    assert output.read_bytes() == before


@pytest.mark.parametrize('writer', ['candidate', 'comparison'])
@pytest.mark.parametrize('alias', ['symlink', 'hardlink'])
def test_recognized_output_aliases_are_not_rerun_destinations(tmp_path, monkeypatch, writer, alias):
    from jetp import _observatory_bundle as bundles

    accepted = tmp_path / 'accepted.zip'
    tiny_bundle(accepted)
    (tmp_path / bundles.SITE).mkdir(parents=True)
    manifest, payloads = bundles._read_bundle(accepted)
    monkeypatch.setattr(bundles, '_capture', lambda *args: ({**manifest, 'sources': []}, payloads))
    prior = tmp_path / 'data/jetp/releases/prior-output'

    def write(output):
        if writer == 'candidate':
            bundles.build_candidate(tmp_path, output, accepted=accepted, builder=lambda *args: None)
        else:
            bundles.write_comparison(tmp_path, accepted, accepted, output)

    write(prior)
    output = tmp_path / 'alias'
    if alias == 'symlink':
        output.symlink_to(prior)
    else:
        output.hardlink_to(prior)
    before = site_hashes(tmp_path)
    with pytest.raises(ValueError, match='alias'):
        write(output)
    assert site_hashes(tmp_path) == before


@pytest.mark.parametrize('field,value', [('unexplained', 1), ('routes_added', {}),
                                       ('metadata_only', {}),
                                       ('intentional_scientific', {'path': 3})])
def test_comparison_preserves_malformed_report_lookalikes(tmp_path, field, value):
    import json

    from jetp import _observatory_bundle as bundles

    accepted = tmp_path / 'accepted.zip'
    tiny_bundle(accepted)
    previous = bundles.compare_bundles(accepted, accepted)
    previous[field] = [value]
    output = tmp_path / 'data/jetp/releases/release.json'
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps(previous))
    before = output.read_bytes()
    with pytest.raises(ValueError, match='recognized'):
        bundles.write_comparison(tmp_path, accepted, accepted, output)
    assert output.read_bytes() == before
