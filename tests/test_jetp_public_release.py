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


def test_prepared_2026_11_reviewed_evidence_extension_is_offline_and_non_aggregate(tmp_path):
    from jetp._public_release import read_release, restore_release

    root = Path(__file__).resolve().parents[1]
    release = root / 'data/jetp/releases/2026-11/jetp-observatory-2026-11.zip'
    descriptor, payloads = read_release(release)
    assert json.loads((release.parent / 'release.json').read_text()) == descriptor
    edition_history = json.loads(payloads['site/data/editions.json'])['editions']
    assert descriptor['edition'] in {row['edition'] for row in edition_history}
    overview = json.loads(payloads['site/data/overview.json'])
    data_build = overview['provenance']['data_build']
    assert data_build == descriptor['data_build']
    assert data_build['observation_cutoff'] == '2026-09-13'
    assert data_build['observation_cutoff'] != descriptor['observation_cutoff']
    assert data_build['relationship_to_release'] == 'canonical_data_build_precedes_release_extension'
    assert descriptor['reviewed_evidence'] == {
        'record_count': 3, 'by_status': {'reviewed_fact': 3},
        'aggregation': 'record_level_non_aggregate', 'analytical_snapshot': 'not_deployed',
    }
    evidence = json.loads(payloads['site/data/reviewed-evidence.json'])
    assert {row['country'] for row in evidence['records']} == {'ZAF', 'IDN', 'SEN'}
    assert len({row['id'] for row in evidence['records']}) == len(evidence['records'])
    assert {row['aggregation'] for row in evidence['records']} == {'non_aggregate'}
    assert evidence['analytical_snapshot'] == {'status': 'not_deployed'}
    assert '0822-comparative-snapshot' not in payloads
    restore_release(release, tmp_path / 'offline-2026-11')
    assert (tmp_path / 'offline-2026-11/data/reviewed-evidence.json').is_file()


def test_prepared_2026_11_r1_exposes_staged_depth_without_deploying_snapshot(tmp_path):
    from jetp._public_release import read_release, restore_release

    root = Path(__file__).resolve().parents[1]
    release = root / 'data/jetp/releases/2026-11-r1/jetp-observatory-2026-11-r1.zip'
    descriptor, payloads = read_release(release)
    assert json.loads((release.parent / 'release.json').read_text()) == descriptor
    assert descriptor['edition'] == '2026-11-r1'
    assert descriptor['reviewed_evidence']['evidence_depth'] == {
        'reviewed_canonical_records': 3,
        'canonical_named_records': 383,
        'frozen_source_documents': 301,
        'structured_atomic_observations': {
            'total': 1740,
            'by_country': {'ZAF': 257, 'IDN': 1148, 'VNM': 325, 'SEN': 10},
            'vnm_rmp_positions': 279,
            'status': 'not_deployed',
        },
    }
    assert '0822-comparative-snapshot' not in payloads
    restore_release(release, tmp_path / 'offline-2026-11-r1')
    restored = (tmp_path / 'offline-2026-11-r1/data/reviewed-evidence.json').read_text()
    assert '"vnm_rmp_positions": 279' in restored


def test_reviewed_evidence_records_are_distinct_non_aggregate_and_traceable(tmp_path):
    """A reviewed fact and a pending candidate never become one released total."""
    from jetp._public_release import build_release, read_release

    root = Path(__file__).resolve().parents[1]
    release = tmp_path / 'reviewed-evidence.zip'
    records = [
        {'id': 'reviewed-1', 'country': 'VNM', 'status': 'reviewed_fact',
         'label': 'Reviewed position', 'notes': 'A source-specific position.',
         'evidence': [{'source_id': 'source-1', 'sha256': 'a' * 64, 'locator': 'p. 1'}]},
        {'id': 'candidate-1', 'country': 'VNM', 'status': 'pending_candidate',
         'label': 'Pending position', 'notes': 'Needs identity adjudication.',
         'evidence': [{'source_id': 'source-2', 'sha256': 'b' * 64, 'locator': 'p. 2'}]},
    ]
    descriptor = build_release(
        root, release, edition='2026-11', input_git_sha='fba8e63ff6a8ad44076cd054871e60d99db6bd3f',
        cutoff='2026-09-13', prepared_on='2026-09-16', reviewer='JETP release review',
        reviewed_evidence=records,
    )

    _, payloads = read_release(release)
    evidence = json.loads(payloads['site/data/reviewed-evidence.json'])
    assert [row['id'] for row in evidence['records']] == ['candidate-1', 'reviewed-1']
    assert {row['aggregation'] for row in evidence['records']} == {'non_aggregate'}
    assert evidence['analytical_snapshot'] == {'status': 'not_deployed'}
    assert descriptor['reviewed_evidence']['record_count'] == 2
    assert descriptor['reviewed_evidence']['by_status'] == {
        'pending_candidate': 1, 'reviewed_fact': 1,
    }


def _assert_offline_release_replay(releases, edition, destination):
    """Replay every declared static handoff and navigation route without a browser."""
    from jetp._public_release import read_release, restore_release

    archive = releases / edition / f'jetp-observatory-{edition}.zip'
    descriptor, payloads = read_release(archive)
    declared_downloads = {
        item['path'] for item in descriptor['files']
        if item['path'].startswith('site/data/') and item['path'] != 'site/data/provenance.json'
    }
    expected_downloads = {
        'site/data/overview.json', 'site/data/comparison.json',
        *(f'site/data/{code}.json' for code in ('ZAF', 'IDN', 'VNM', 'SEN')),
    }
    assert declared_downloads == expected_downloads
    # This is the released site's local hash-navigation contract.  Edition
    # history is delivered through editions.json, rather than a separate page.
    static_routes = {
        '#overview': 'overviewPage',
        '#countries': 'countriesPage',
        '#projects': 'cataloguePage',
        '#comparison': 'comparisonPage',
        '#methods': 'methodsPage',
    }
    index, app = payloads['site/index.html'].decode(), payloads['site/app.js'].decode()
    assert all(f'href="{route}"' in index for route in static_routes)
    assert all(renderer in app for renderer in static_routes.values())

    restore_release(archive, destination)
    assert (destination / 'index.html').is_file()
    for member in sorted(expected_downloads):
        restored = destination / member.removeprefix('site/')
        assert restored.read_bytes() == payloads[member]
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
    assert [row['edition'] for row in editions['editions']] == ['2026-11-r1', '2026-11', '2026-10', '2026-09']

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
