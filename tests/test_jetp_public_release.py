"""A public JETP edition is a self-contained, replayable publication package."""

import hashlib
import json
import zipfile
from pathlib import Path


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
