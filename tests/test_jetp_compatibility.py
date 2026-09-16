"""Version negotiation and MVP output contracts at the migration boundary."""

import hashlib
import json
from pathlib import Path

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
def test_all_mvp_views_match_authoritative_builder(view):
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


def test_frozen_mvp_baseline_matches_recorded_inspection():
    """Pin 0761 independently of the later canonical preview."""
    baseline = (ROOT / 'data/jetp/releases/mvp-baseline-0761.zip').read_bytes()
    inspection = json.loads((ROOT / 'docs/jetp-mvp-baseline-0761.json').read_text())
    assert len(baseline) == inspection['archive_bytes']
    assert hashlib.sha256(baseline).hexdigest() == inspection['archive_sha256']
