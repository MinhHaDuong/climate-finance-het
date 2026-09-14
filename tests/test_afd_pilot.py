"""Acceptance contracts for the AFD historical observation pilot."""
from afd_pilot import reconcile, payment_observation


def test_cma123501_disappearance_is_not_an_outcome():
    row = {'id_concours': 'CMA123501', 'date_de_1er_versement_concours': None,
           'etat_du_projet': 'Exécution', 'date_de_signature_de_convention': '2019-06-28'}
    result = reconcile(row, None)
    assert result['observation_status'] == 'lost_visibility'
    assert result['outcome'] == 'unknown'
    assert result['last_observed_stage'] == 'signature'
    assert result['last_observed_snapshot'] == 'legacy-retrieved-2026-09-14'


def test_exact_payment_is_preserved_and_no_uncovered_interval():
    result = payment_observation('2022-08-30', ['2022-12-31'])
    assert result['date'] == '2022-08-30'
    assert result['precision'] == 'day'
    missing = payment_observation(None, ['2022-12-31'])
    assert missing['date'] is None
    assert missing['precision'] == 'unknown'
    assert missing['interval'] is None


def test_value_date_never_imputes_award_and_parent_never_joins():
    row = {'id_concours': 'CMA123501', 'date_d_octroi': None}
    result = reconcile(row, {'code_concours_simple': 'CMA123502', 'value_date': '2020-01-01'})
    assert result['award'] is None
    assert result['observation_status'] == 'lost_visibility'
