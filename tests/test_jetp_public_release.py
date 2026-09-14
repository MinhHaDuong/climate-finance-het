"""A public JETP edition is a self-contained, replayable publication package."""

import hashlib
import json
import zipfile
from pathlib import Path

import pytest


def test_public_release_keeps_four_country_downloads_traceable_and_replays_offline(tmp_path):
    from jetp._public_release import build_release, read_release, restore_release

    root = Path(__file__).resolve().parents[1]
    release = tmp_path / 'jetp-observatory-2026-09.zip'
    descriptor = build_release(
        root, release, edition='2026-09', input_git_sha='fba8e63ff6a8ad44076cd054871e60d99db6bd3f',
        cutoff='2026-09-13', prepared_on='2026-09-15', reviewer='JETP release review',
    )

    assert descriptor['format_version'] == 'jetp-public-release/1'
    assert descriptor['edition'] == '2026-09'
    assert descriptor['input_git_sha'] == 'fba8e63ff6a8ad44076cd054871e60d99db6bd3f'
    assert descriptor['currency_policy']['reported_headlines'] == 'not_additive'
    assert descriptor['observation_cutoff'] == '2026-09-13'
    assert descriptor['release_prepared_date'] == '2026-09-15'
    assert descriptor['publication_date'] is None
    assert set(descriptor['coverage']['countries']) == {'ZAF', 'IDN', 'VNM', 'SEN'}
    assert descriptor['coverage']['countries']['VNM']['unpublished_identity_slots'] == 21
    assert descriptor['source_redistribution'] == 'excluded'
    assert all(item['sha256'] and item['size_bytes'] >= 0 for item in descriptor['files'])

    loaded, payloads = read_release(release)
    assert loaded == descriptor
    assert all(not name.startswith('sources/') for name in payloads)
    for code in ('ZAF', 'IDN', 'VNM', 'SEN'):
        country = json.loads(payloads[f'site/data/{code}.json'])
        assert country['country']['code'] == code
    assert 'dictionary.md' in payloads
    assert 'TERMS.md' in payloads
    assert 'coverage.json' in payloads

    restored = tmp_path / 'offline-site'
    restore_release(release, restored)
    assert (restored / 'index.html').is_file()
    assert json.loads((restored / 'data/SEN.json').read_text())['country']['code'] == 'SEN'

    # The release archive exposes its own complete byte inventory, not a DVC route.
    with zipfile.ZipFile(release) as archive:
        assert hashlib.sha256(archive.read('site/data/ZAF.json')).hexdigest() == next(
            item['sha256'] for item in descriptor['files'] if item['path'] == 'site/data/ZAF.json')


def test_prepared_2026_09_release_descriptor_matches_the_downloadable_archive():
    from jetp._public_release import read_release

    root = Path(__file__).resolve().parents[1]
    release_path = root / 'data/jetp/releases/2026-09/jetp-observatory-2026-09.zip'
    descriptor_path = root / 'data/jetp/releases/2026-09/release.json'
    descriptor, payloads = read_release(release_path)

    assert json.loads(descriptor_path.read_text()) == descriptor
    assert descriptor['release_state'] == 'prepared'
    assert descriptor['input_git_sha'] == 'fba8e63ff6a8ad44076cd054871e60d99db6bd3f'
    assert set(descriptor['coverage']['countries']) == {'ZAF', 'IDN', 'VNM', 'SEN'}
    assert all(not name.startswith('sources/') for name in payloads)


def _assert_offline_release_replay(releases, edition, destination):
    from jetp._public_release import restore_release

    restore_release(releases / edition / f'jetp-observatory-{edition}.zip', destination)
    assert (destination / 'index.html').is_file()
    for code in ('ZAF', 'IDN', 'VNM', 'SEN'):
        assert json.loads((destination / f'data/{code}.json').read_text())['country']['code'] == code


def test_two_real_fact_unchanged_rehearsal_releases_restore_offline(tmp_path):
    """0760: both immutable rehearsal packages replay without live dependencies."""
    from jetp._public_release import read_release

    root = Path(__file__).resolve().parents[1]
    releases = root / 'data/jetp/releases'
    previous_descriptor, _ = read_release(releases / '2026-09/jetp-observatory-2026-09.zip')
    current_descriptor, _ = read_release(releases / '2026-10/jetp-observatory-2026-10.zip')
    assert current_descriptor['edition'] == '2026-10'
    assert current_descriptor['rehearsal_of'] == '2026-09'
    assert current_descriptor['no_scientific_change'] is True
    assert current_descriptor['input_git_sha'] == previous_descriptor['input_git_sha']
    assert json.loads((releases / '2026-10/release.json').read_text()) == current_descriptor
    validation = json.loads((releases / '2026-10/validation.json').read_text())
    assert validation['rehearsal_of'] == '2026-09'
    assert validation['no_scientific_change'] is True
    assert validation['archive_sha256'] == hashlib.sha256(
        (releases / '2026-10/jetp-observatory-2026-10.zip').read_bytes()).hexdigest()
    editions = json.loads((root / 'deliverables/jetp-observatory/data/editions.json').read_text())
    assert [row['edition'] for row in editions['editions']] == ['2026-10', '2026-09']

    for edition in ('2026-09', '2026-10'):
        _assert_offline_release_replay(releases, edition, tmp_path / edition)


def test_interrupted_second_release_build_preserves_and_replays_first(tmp_path, monkeypatch):
    from jetp import _public_release as release

    root = Path(__file__).resolve().parents[1]
    releases = root / 'data/jetp/releases'
    first_archive = releases / '2026-09/jetp-observatory-2026-09.zip'
    first_descriptor = releases / '2026-09/release.json'
    archive_before, descriptor_before = first_archive.read_bytes(), first_descriptor.read_bytes()

    def interrupted(*args, **kwargs):
        raise RuntimeError('interrupted second release build')

    monkeypatch.setattr(release, '_archive_member', interrupted)
    with pytest.raises(RuntimeError, match='interrupted'):
        release.build_release(root, tmp_path / 'candidate.zip', edition='2026-10',
                              input_git_sha='fba8e63ff6a8ad44076cd054871e60d99db6bd3f',
                              cutoff='2026-09-13', prepared_on='2026-09-15',
                              reviewer='JETP release reviewer', rehearsal_of='2026-09')
    assert first_archive.read_bytes() == archive_before
    assert first_descriptor.read_bytes() == descriptor_before
    assert hashlib.sha256(first_archive.read_bytes()).hexdigest() == hashlib.sha256(archive_before).hexdigest()
    assert hashlib.sha256(first_descriptor.read_bytes()).hexdigest() == hashlib.sha256(descriptor_before).hexdigest()
    _assert_offline_release_replay(releases, '2026-09', tmp_path / 'restored-after-interruption')


def test_rejected_second_release_validation_preserves_and_replays_first(tmp_path, monkeypatch):
    from jetp import _public_release as release

    root = Path(__file__).resolve().parents[1]
    releases = root / 'data/jetp/releases'
    first_archive = releases / '2026-09/jetp-observatory-2026-09.zip'
    first_descriptor = releases / '2026-09/release.json'
    archive_before, descriptor_before = first_archive.read_bytes(), first_descriptor.read_bytes()
    validate = release.read_release

    def rejected_after_build(path):
        validate(path)
        raise ValueError('candidate rejected after validation')

    monkeypatch.setattr(release, 'read_release', rejected_after_build)
    with pytest.raises(ValueError, match='rejected after validation'):
        release.build_release(root, tmp_path / 'candidate.zip', edition='2026-10',
                              input_git_sha='fba8e63ff6a8ad44076cd054871e60d99db6bd3f',
                              cutoff='2026-09-13', prepared_on='2026-09-15',
                              reviewer='JETP release reviewer', rehearsal_of='2026-09')
    monkeypatch.setattr(release, 'read_release', validate)
    assert first_archive.read_bytes() == archive_before
    assert first_descriptor.read_bytes() == descriptor_before
    assert hashlib.sha256(first_archive.read_bytes()).hexdigest() == hashlib.sha256(archive_before).hexdigest()
    assert hashlib.sha256(first_descriptor.read_bytes()).hexdigest() == hashlib.sha256(descriptor_before).hexdigest()
    _assert_offline_release_replay(releases, '2026-09', tmp_path / 'restored-after-rejection')
