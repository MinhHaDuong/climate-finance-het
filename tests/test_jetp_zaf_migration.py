"""South African migration covers each source row without changing the public MVP."""

import hashlib
from pathlib import Path

import pytest


@pytest.mark.slow
def test_zaf_candidate_reconciles_inventory_legacy_and_current_views(tmp_path):
    from jetp._compatibility import MVP_VIEWS, read_mvp_view
    from jetp.build_zaf_positions import _country_output, build_migration, encoded

    root = Path(__file__).resolve().parents[1]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (root / 'data/jetp').glob('*.csv')}
    result = build_migration(root)
    output = tmp_path / "candidate.json"
    output.write_bytes(encoded(result))
    assert _country_output(output)
    assert len(result['inventory_positions']) == 339
    assert len(result['reported_positions']) == 339
    assert len(result['legacy_dispositions']) == 1087
    assert result['comparison']['legacy_rows_by_table']['data/jetp/event-timing.csv'] == 259
    assert result['comparison']['legacy_rows_by_table']['data/jetp/dry-searches.csv'] == 10
    assert result['comparison']['legacy_rows_by_table']['data/jetp/source-claims.csv'] == 48
    assert len(result['comparison']['existing_project_ids']) == 263
    assert result['comparison']['register_status_counts']['C. Implementation Phase'] == 128
    assert result['comparison']['register_status_counts']['D. Completed'] == 88
    assert result['comparison']['financial_event_additions'] == 0
    assert result['event_candidates'] == []
    assert result['comparison']['public_payload_bytes']['ZAF'] == 509315
    assert result['writer_owner'] == result['publication_mode'] == 'legacy'
    register = [r for r in result['inventory_positions'] if r['inventory_id'] == 'Register']
    assert all(len(row['entity_ids']) == 1 for row in register)
    assert len({row['entity_ids'][0] for row in register}) == 257
    for view in MVP_VIEWS:
        assert result['mvp_views'][view] == read_mvp_view(root, view, supported_versions={'mvp/1'})
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in before.items())
