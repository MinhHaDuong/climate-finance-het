"""Country candidates retain evidence gaps and cannot overwrite accepted assets."""

import json

import pytest
from jetp import build_zaf_positions as builder
from jetp._compatibility import MVP_VIEWS


def candidate_fixture():
    """Small structurally complete candidate, without real-data extraction."""
    return dict(schema_version='country-migration/1', country='ZAF',
                admission_status='unadmitted_candidate', writer_owner='legacy',
                publication_mode='legacy', inputs={}, recipe_inputs={}, recovery_inputs={},
                selected_sources=[], reported_positions=[], event_candidates=[],
                inventory_positions=[], legacy_dispositions=[],
                legacy_evidence=[], legacy_unresolved=[], inventory_boundaries=[],
                identity_review=[], source_regime=[], report_context={},
                mvp_views={view: {} for view in MVP_VIEWS},
                comparison={'public_payload_limit_bytes': 512000, 'public_payload_bytes': {}})


@pytest.mark.parametrize('alias_kind', ['direct', 'symlink', 'hardlink'])
@pytest.mark.parametrize('relative', ['data/jetp/releases/recovery.json',
                                      'data/jetp/releases/README.md',
                                      'data/jetp/releases/.gitignore',
                                      'data/jetp/releases/candidate.json.dvc',
                                      'data/jetp/sources.csv',
                                      'deliverables/jetp-observatory/data/VNM.json'])
def test_writer_preserves_accepted_files_and_aliases(tmp_path, alias_kind, relative):
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    source.write_text('{"accepted": true}\n')
    output = source
    if alias_kind != 'direct':
        output = tmp_path / 'alias.json'
        if alias_kind == 'symlink':
            output.symlink_to(source)
        else:
            output.hardlink_to(source)
    original = source.read_bytes()
    with pytest.raises(ValueError):
        builder.write_migration(tmp_path, output)
    assert source.read_bytes() == original


def test_interruption_preserves_previous_candidate(tmp_path, monkeypatch):
    output = tmp_path / 'data/jetp/releases/candidate.json'
    candidate = candidate_fixture()
    monkeypatch.setattr(builder, 'build_migration', lambda *args, **kwargs: candidate)
    builder.write_migration(tmp_path, output)
    before = output.read_bytes()
    builder.write_migration(tmp_path, output)
    assert output.read_bytes() == before

    entered = []

    def fail(*args, **kwargs):
        entered.append(True)
        raise ValueError('incomplete extraction')

    monkeypatch.setattr(builder, 'build_migration', fail)
    with pytest.raises(ValueError, match='incomplete extraction'):
        builder.write_migration(tmp_path, output)
    assert entered == [True]
    assert output.read_bytes() == before


@pytest.mark.parametrize('alias_kind', ['symlink', 'hardlink'])
def test_recognized_candidate_alias_is_rejected_before_build(tmp_path, monkeypatch, alias_kind):
    output = tmp_path / 'candidates/previous.json'
    candidate = candidate_fixture()
    monkeypatch.setattr(builder, 'build_migration', lambda *args, **kwargs: candidate)
    builder.write_migration(tmp_path, output)
    before = output.read_bytes()
    alias = tmp_path / 'alias.json'
    if alias_kind == 'symlink':
        alias.symlink_to(output)
    else:
        alias.hardlink_to(output)

    def unexpected_build(*args, **kwargs):
        pytest.fail('Alias must be rejected before building')

    monkeypatch.setattr(builder, 'build_migration', unexpected_build)
    with pytest.raises(ValueError, match='alias'):
        builder.write_migration(tmp_path, alias)
    assert output.read_bytes() == before
    assert alias.read_bytes() == before
    if alias_kind == 'symlink':
        assert alias.is_symlink()


@pytest.mark.parametrize('alias_kind', ['direct', 'symlink', 'hardlink'])
@pytest.mark.parametrize('malformation', ['markers_only', 'record_member', 'view_member'])
def test_malformed_candidate_markers_are_not_replacement_permission(
        tmp_path, monkeypatch, alias_kind, malformation):
    target = tmp_path / 'malformed.json'
    candidate = candidate_fixture()
    if malformation == 'markers_only':
        candidate = {key: candidate[key] for key in ('schema_version', 'country', 'admission_status')}
    elif malformation == 'record_member':
        candidate['inventory_positions'] = ['not a position object']
    else:
        candidate['mvp_views']['ZAF'] = 'not an MVP payload'
    target.write_text(json.dumps(candidate))
    output = target
    if alias_kind != 'direct':
        output = tmp_path / 'alias.json'
        if alias_kind == 'symlink':
            output.symlink_to(target)
        else:
            output.hardlink_to(target)
    before = target.read_bytes()

    def unexpected_build(*args, **kwargs):
        pytest.fail('Malformed predecessor must be rejected before building')

    monkeypatch.setattr(builder, 'build_migration', unexpected_build)
    with pytest.raises(ValueError):
        builder.write_migration(tmp_path, output)
    assert target.read_bytes() == before
    assert output.read_bytes() == before


def test_empty_top_level_lookalike_is_not_replacement_permission(tmp_path, monkeypatch):
    candidate = candidate_fixture()
    for key, value in candidate.items():
        if isinstance(value, list):
            candidate[key] = []
    output = tmp_path / 'empty-descriptor.json'
    output.write_text(json.dumps(candidate))
    before = output.read_bytes()
    monkeypatch.setattr(builder, 'build_migration', lambda *args, **kwargs: candidate_fixture())
    with pytest.raises(ValueError):
        builder.write_migration(tmp_path, output)
    assert output.read_bytes() == before
