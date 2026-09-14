"""Publication provenance is a bounded, fail-closed output contract."""

import pytest


def test_display_ids_are_unique_and_reverse_evidence_traversal_keeps_every_use():
    from jetp._publication import publish

    output = publish(
        release_id='2026-09-preview',
        displays=[
            {'display_id': 'overview-idn-headline', 'route': '#overview',
             'payload': 'data/IDN.json', 'pointer': '/country/headline',
             'role': 'reported_position', 'evidence': ['idn-report']},
            {'display_id': 'country-idn-headline', 'route': '#country/IDN',
             'payload': 'data/IDN.json', 'pointer': '/country/headline',
             'role': 'reported_position', 'evidence': ['idn-report']},
            {'display_id': 'country-idn-headline-context', 'route': '#country/IDN',
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

    display = {'display_id': 'idn-account', 'route': '#country/IDN',
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
