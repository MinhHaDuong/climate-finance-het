"""Country candidates retain evidence gaps and cannot overwrite accepted assets."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jetp import build_vnm_positions as builder
from jetp._compatibility import MVP_VIEWS, read_mvp_view

pytestmark = pytest.mark.wp_jetp

def candidate_fixture():
    """Small structurally complete candidate, without real-data extraction."""
    digest = 'a' * 64
    edition = {'record_kind': 'edition', 'record_id': 'fixture'}
    evidence = {'document_sha256': digest, 'edition': edition, 'locator': 'fixture:1'}
    return dict(schema_version='country-migration/1', country='VNM',
                admission_status='unadmitted_candidate', writer_owner='legacy',
                publication_mode='legacy', inputs={'fixture': {}}, recipe_inputs={'fixture': digest},
                recovery_inputs={'fixture': {}}, selected_acquisition={'document_sha256': digest},
                edition_snapshot={'record_kind': 'edition_snapshot', 'edition': edition,
                                  'document_sha256': digest},
                extraction={'document_sha256': digest, 'locators': ['fixture:1']},
                inventory_positions=[{'annex': 'fixture', 'ordinal': 1,
                                      'transition_date': None, 'payment_amount': None,
                                      'evidence': evidence}],
                legacy_dispositions=[{'disposition': 'retained_legacy_authority',
                                      'original': {'project_id': 'fixture'}}],
                legacy_position_candidates=[{'record_id': 'fixture'}],
                legacy_evidence=[{'legacy_row_id': 'fixture'}],
                legacy_unresolved=[{'legacy_row_id': 'fixture'}],
                inventory_boundaries=[{'annex': 'fixture', 'row_count': 1,
                                       'disposition': 'selected'}],
                identity_review=[{'fixture': True}],
                mvp_views={**{view: {'projects': [], 'record_count': 24, 'country': {}}
                              for view in {'ZAF', 'IDN', 'VNM', 'SEN'}},
                           'overview': {'countries': 4}, 'comparison': {'projects': []}},
                comparison={'reason': 'fixture'})


@pytest.mark.parametrize('alias_kind', ['direct', 'symlink', 'hardlink'])
@pytest.mark.parametrize('relative', ['data/jetp/releases/recovery.json',
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

    def fail(*args, **kwargs):
        raise ValueError('incomplete extraction')

    monkeypatch.setattr(builder, 'build_migration', fail)
    with pytest.raises(ValueError, match='incomplete extraction'):
        builder.write_migration(tmp_path, output)
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
        candidate['mvp_views']['VNM'] = 'not an MVP payload'
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


def test_empty_top_level_lookalike_is_rejected_before_build(tmp_path, monkeypatch):
    """Identifying fields alone never authorize replacing an existing file."""
    output = tmp_path / 'empty-descriptor.json'
    candidate = candidate_fixture()
    for key, value in candidate.items():
        if isinstance(value, (dict, list)):
            candidate[key] = type(value)()
    output.write_text(json.dumps(candidate))
    before = output.read_bytes()

    def unexpected_build(*args, **kwargs):
        pytest.fail('Empty predecessor must be rejected before building')

    monkeypatch.setattr(builder, 'build_migration', unexpected_build)
    with pytest.raises(ValueError):
        builder.write_migration(tmp_path, output)
    assert output.read_bytes() == before


@pytest.mark.slow
def test_real_candidate_covers_inventory_legacy_and_all_country_views():
    root = Path(__file__).resolve().parents[1]
    pdf = root / 'data/jetp/documents/objects/b1/b145af2e7f4a441dc87d7ec2d99a29e1e6d7b265406d398dd64013dd4560733c.pdf'
    if not pdf.exists():
        pytest.skip('DVC checkout required for saved-RMP candidate audit')
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (root / 'data/jetp').glob('*.csv')}
    result = builder.build_migration(root)
    assert len(result['inventory_positions']) == 279
    # 227 before ticket 0854; its seven collected Viet Nam sources add seven
    # acquisition_history dispositions (data/jetp/manifest.csv rows 309-315),
    # and ticket 0859's two add rows 316-317.
    # This pin counts registry rows of the country, so it moves with every
    # collection; re-read the delta before re-pinning.
    # 0875 moved 23 project identities out of projects.csv; 0878 retires this legacy sidecar.
    assert len(result['legacy_dispositions']) == 213
    assert len(result['legacy_position_candidates']) == 46
    assert len(result['legacy_unresolved']) == 53
    assert len(result['comparison']['existing_project_ids']) == 1
    assert result['comparison']['added_public_project_ids'] == []
    assert result['selected_acquisition']['retrieved_at'] == '2026-09-11T20:39:00Z'
    assert result['selected_acquisition']['recorded_at'] is None
    assert result['extraction']['recorded_at'].startswith('2026-09-14')
    for view in MVP_VIEWS:
        assert result['mvp_views'][view] == read_mvp_view(root, view, supported_versions={'mvp/1'})
    assert builder.encoded(result) == builder.encoded(builder.build_migration(root))
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == value for p, value in before.items())
    encoded = json.dumps(result['legacy_dispositions'])
    for value in ('vnm-pilot-source-066', 'partial', '7040000000', '5520000000'):
        assert value in encoded
    invalid = copy.deepcopy(result)
    invalid['inventory_positions'][0]['evidence']['document_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='hash mismatch'):
        builder.validate_migration(invalid)
