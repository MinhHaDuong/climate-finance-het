"""The observatory's country projection respects v2 referent kinds."""

from pathlib import Path

import pytest
import yaml
from jetp._country_views_v2 import country_view, load_country_inputs

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.wp_jetp


def test_current_country_views_keep_agreements_out_of_project_counts():
    ledger = ROOT / 'data/jetp'
    config = yaml.safe_load((ROOT / 'config/jetp_observatory.yaml').read_text())
    tables = load_country_inputs(ledger)
    views = {code: country_view(ledger, code, country, tables=tables)
             for code, country in config['countries'].items()}

    assert {code: view['project_count'] for code, view in views.items()} == {
        'ZAF': 5, 'IDN': 13, 'VNM': 1, 'SEN': 45}
    assert {code: view['agreement_count'] for code, view in views.items()} == {
        'ZAF': 258, 'IDN': 57, 'VNM': 0, 'SEN': 0}
    assert sum(len(view['statements']) for view in views.values()) == 340
    for view in views.values():
        project_ids = {row['id'] for row in view['projects']}
        agreement_ids = {row['id'] for row in view['agreements']}
        assert not project_ids & agreement_ids
        for statement in view['statements']:
            assert statement['line_id'] and statement['sha256']
            assert statement['source_id'] in view['sources']
            assert statement['subject_id'] in (project_ids | agreement_ids | {
                row['asset_id'] for row in tables['assets']})
