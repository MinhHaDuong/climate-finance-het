"""Version negotiation and unchanged MVP output at the migration boundary."""

import json
import os
from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml
from jetp import build_observatory as legacy
from jetp._compatibility import MVP_SCHEMA_VERSION, read_mvp_view

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ('overview', 'comparison', 'ZAF', 'IDN', 'VNM', 'SEN')


@pytest.mark.parametrize('versions', [(), ('mvp/2',)])
def test_consumer_must_support_requested_version_before_reading(tmp_path, versions):
    with pytest.raises(ValueError, match='Consumer does not support'):
        read_mvp_view(tmp_path, 'ZAF', supported_versions=versions)


def test_reader_rejects_unknown_schema_before_reading(tmp_path):
    with pytest.raises(ValueError, match='Unsupported MVP schema'):
        read_mvp_view(tmp_path, 'ZAF', schema_version='mvp/2',
                      supported_versions=('mvp/2',))


def test_reader_rejects_unknown_view_before_reading(tmp_path):
    with pytest.raises(ValueError, match='Unknown MVP view'):
        read_mvp_view(tmp_path, '../ZAF', supported_versions=(MVP_SCHEMA_VERSION,))


@pytest.mark.slow
@pytest.mark.parametrize('view', VIEWS)
def test_all_mvp_views_match_authoritative_builder_and_frozen_baseline(view):
    config = yaml.safe_load((ROOT / 'config/jetp_observatory.yaml').read_text())
    tables = legacy.read_inputs(ROOT)
    if view == 'overview':
        expected = legacy.overview(ROOT, config, tables)
    elif view == 'comparison':
        expected = legacy.comparison_data(ROOT, config)
    else:
        expected = legacy.country_data(ROOT, view, config, tables)
    actual = read_mvp_view(ROOT, view, supported_versions=(MVP_SCHEMA_VERSION,))
    assert actual == expected
    serialized = json.dumps(actual, ensure_ascii=False, separators=(',', ':')) + '\n'
    with ZipFile(ROOT / 'data/jetp/releases/mvp-baseline-0761.zip') as bundle:
        frozen_bytes = bundle.read(f'site/data/{view}.json')
    if view != 'overview':
        assert serialized.encode() == frozen_bytes
    else:
        frozen = json.loads(frozen_bytes)
        # Only checkout identity changes: all input hashes and scientific fields
        # must still equal the accepted, immutable publication.
        for key in ('input_git_sha', 'build_base_git_sha'):
            actual['provenance'].pop(key)
            frozen['provenance'].pop(key)
        # Full-suite collection can import the legacy module via tests/../scripts.
        # Canonicalize only equivalent path spellings; preserve every byte hash.
        for payload in (actual, frozen):
            hashes = payload['provenance']['input_sha256']
            normalized = {os.path.normpath(path): digest for path, digest in hashes.items()}
            assert len(normalized) == len(hashes)
            payload['provenance']['input_sha256'] = normalized
        assert actual == frozen
