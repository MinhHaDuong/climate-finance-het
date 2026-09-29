"""Served statement views use cited v2 rows and reviewed referents."""

from collections import Counter
from pathlib import Path

import pytest
from jetp._country_views_v2 import load_country_inputs
from jetp.build_observations import served_views

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.wp_jetp


def test_v2_statement_views_separate_observations_and_identity_citations():
    tables = load_country_inputs(ROOT / 'data/jetp')
    views = served_views(tables)
    assert {code: Counter(row['table'] for row in rows)
            for code, rows in views.items()} == {
        'ZAF': Counter(observations=260, **{'line-referents': 263}),
        'IDN': Counter(observations=90, **{'line-referents': 73}),
        'VNM': Counter(observations=3, **{'line-referents': 1}),
        'SEN': Counter(observations=52, **{'line-referents': 45}),
    }
    documents = {row['document_id'] for row in tables['documents']}
    line_hashes = {row['line_id']: row['sha256'] for row in tables['lines']}
    idn_observation_ids = {
        row['observation_id'] for row in views['IDN']
        if row['table'] == 'observations'
    }
    assert 'observation-idn-impl-nagajaya-2025' not in idn_observation_ids
    for rows in views.values():
        for row in rows:
            assert row['source_id'] in documents
            assert row['sha256'] == line_hashes[row['line_id']]
            assert row['subject_id']
            assert row['verification'] == 'accepted'
