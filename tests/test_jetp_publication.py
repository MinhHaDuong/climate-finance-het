"""Publication provenance is a bounded, fail-closed output contract."""

import pytest

pytestmark = pytest.mark.wp_jetp

def test_display_ids_are_unique_and_reverse_evidence_traversal_keeps_every_use():
    from jetp._publication import publish

    output = publish(
        release_id='2026-09-preview',
        displays=[
            {'display_id': 'overview-idn-headline', 'route': '#overview',
             'payload': 'data/IDN.json', 'pointer': '/country/headline',
             'role': 'reported_position', 'evidence': ['idn-report']},
            {'display_id': 'country-idn-headline', 'route': '#funding/IDN',
             'payload': 'data/IDN.json', 'pointer': '/country/headline',
             'role': 'reported_position', 'evidence': ['idn-report']},
            {'display_id': 'country-idn-headline-context', 'route': '#funding/IDN',
             'payload': 'data/IDN.json', 'pointer': '/country/headline',
             'role': 'reported_position', 'evidence': ['idn-report']},
        ],
        combinations=[{'subject': 'IDN', 'measure': 'reported_position',
                       'perimeter': 'national_headline', 'owner': 'legacy'}],
    )

    assert output['format_version'] == 'jetp-publication/1'
    assert output['by_evidence']['idn-report'] == [
        'country-idn-headline', 'country-idn-headline-context', 'overview-idn-headline']
    with pytest.raises(ValueError, match='Duplicate display ID'):
        publish('2026-09-preview', output['displays'] * 2, output['combinations'])


def test_partial_or_duplicate_owned_reconciled_financial_combination_cannot_publish():
    from jetp._publication import publish

    display = {'display_id': 'idn-account', 'route': '#funding/IDN',
               'payload': 'data/IDN.json', 'pointer': '/account',
               'role': 'gross_disbursement_account', 'evidence': ['account-review']}
    partial = {'subject': 'IDN', 'measure': 'gross_disbursement',
               'perimeter': 'national', 'owner': 'reconciled', 'accepted': True,
               'contributors': [
                   {'id': 'opening', 'owner': 'reconciled'},
                   {'id': 'flow-1', 'owner': 'legacy'},
               ]}
    with pytest.raises(ValueError, match='complete reconciled ownership'):
        publish('2026-09-preview', [display], [partial])
    duplicate = {**partial, 'contributors': [
        {'id': 'opening', 'owner': 'reconciled'},
        {'id': 'opening', 'owner': 'reconciled'},
    ]}
    with pytest.raises(ValueError, match='Duplicate contributor'):
        publish('2026-09-preview', [display], [duplicate])


def test_real_sidecar_traces_each_visible_country_headline():
    from pathlib import Path

    from jetp.build_observatory_provenance import build

    root = Path(__file__).resolve().parents[1]
    result = build(root, root / 'deliverables/jetp-observatory/data/provenance.json')
    assert result['format_version'] == 'jetp-publication/1'
    assert len(result['displays']) == 32
    assert {row['owner'] for row in result['combinations']} == {'legacy'}
    assert all(row['evidence'] for row in result['displays'])
    expected = {'/country/headline', '/country/headline_detail',
                '/country/stage_label', '/country/headline_date'}
    for code, country in result['by_evidence'].items():
        displays = [row for row in result['displays'] if row['display_id'] in country]
        assert len(displays) == 8, code
        assert {row['pointer'] for row in displays} == expected
        assert {row['route'] for row in displays} == {'#overview', '#funding/' + displays[0]['payload'][5:8]}


def test_candidate_bundle_keeps_provenance_sidecar_with_matching_release_bytes(tmp_path):
    from pathlib import Path

    from jetp._observatory_bundle import _read_bundle, build_candidate, freeze_bundle

    root = Path(__file__).resolve().parents[1]
    accepted, candidate = tmp_path / 'accepted.zip', tmp_path / 'candidate.zip'
    freeze_bundle(root, accepted)
    build_candidate(root, candidate, accepted=accepted)
    manifest, payloads = _read_bundle(candidate)
    sidecar = payloads['site/data/provenance.json']
    assert manifest['files']['site/data/provenance.json']['size_bytes'] == len(sidecar)
    assert b'jetp-publication/1' in sidecar
