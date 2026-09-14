"""First bounded original-currency gross-disbursement account (ticket 0768)."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from jetp._reconciliation import ReconciliationError, reconcile_gross_disbursement


def payment(identity, occurrence, amount, date='2024-04-15', **extra):
    return dict(id=identity, occurrence_id=occurrence, amount=str(amount), currency='EUR',
                date=date, agreement_id='vnm-agreement-a', perimeter_id='vnm-jetp',
                basis='gross_disbursement', accepted=True, **extra)


def test_complete_flow_replaces_itemised_payments_and_duplicate_report_once():
    """First test: exact closure needs a disjoint, complete reviewed movement cover."""
    account = reconcile_gross_disbursement(
        agreement_id='vnm-agreement-a', perimeter_id='vnm-jetp', currency='EUR',
        opening=dict(id='opening', amount='0', currency='EUR', cutoff='2024-03-31',
                     basis='gross_disbursement', accepted=True),
        movements=[payment('payment-1a', 'payment-1', 5),
                   payment('payment-1b', 'payment-1', 5),
                   payment('payment-2', 'payment-2', 4),
                   payment('payment-3', 'payment-3', 6)],
        flows=[dict(id='q2-flow', amount='15', currency='EUR', coverage_start='2024-04-01',
                    coverage_end='2024-06-30', agreement_id='vnm-agreement-a',
                    perimeter_id='vnm-jetp', basis='gross_disbursement', accepted=True,
                    covered_occurrence_ids=['payment-1', 'payment-2', 'payment-3'])],
        coverage=dict(complete=True, reviewer='fixture-reviewer', decision_id='coverage-q2'),
        cutoff='2024-06-30',
        reported_closing=dict(id='closing', amount='15', currency='EUR', cutoff='2024-06-30',
                              basis='gross_disbursement', accepted=True),
    )
    assert account['status'] == 'exact'
    assert account['reconstructed_closing'] == Decimal('15')
    assert account['residual'] == Decimal('0')
    assert account['included_ids'] == ['q2-flow']
    assert account['excluded_ids'] == ['payment-1a', 'payment-1b', 'payment-2', 'payment-3']


@pytest.mark.parametrize('change, reason', [
    ({'opening': None}, 'opening'),
    ({'coverage': dict(complete=False, reviewer='fixture-reviewer', decision_id='partial')}, 'coverage'),
    ({'currency': 'USD'}, 'currency'),
])
def test_missing_opening_partial_coverage_or_incompatible_currency_blocks_exact_closure(change, reason):
    kwargs = dict(
        agreement_id='vnm-agreement-a', perimeter_id='vnm-jetp', currency='EUR',
        opening=dict(id='opening', amount='0', currency='EUR', cutoff='2024-03-31',
                     basis='gross_disbursement', accepted=True),
        movements=[payment('payment-1', 'payment-1', 5)], flows=[],
        coverage=dict(complete=True, reviewer='fixture-reviewer', decision_id='coverage-q2'),
        cutoff='2024-06-30', reported_closing=None,
    )
    kwargs.update(change)
    result = reconcile_gross_disbursement(**kwargs)
    assert result['status'] == 'unavailable'
    assert reason in result['reasons']


def test_overlapping_flow_and_uncovered_movement_are_rejected():
    with pytest.raises(ReconciliationError, match='overlap'):
        reconcile_gross_disbursement(
            agreement_id='vnm-agreement-a', perimeter_id='vnm-jetp', currency='EUR',
            opening=dict(id='opening', amount='0', currency='EUR', cutoff='2024-03-31',
                         basis='gross_disbursement', accepted=True),
            movements=[payment('payment-1', 'payment-1', 5)],
            flows=[dict(id='flow', amount='5', currency='EUR', coverage_start='2024-04-01',
                        coverage_end='2024-06-30', agreement_id='vnm-agreement-a',
                        perimeter_id='vnm-jetp', basis='gross_disbursement', accepted=True,
                        covered_occurrence_ids=['payment-1'])],
            coverage=dict(complete=True, reviewer='fixture-reviewer', decision_id='coverage-q2'),
            cutoff='2024-06-30', reported_closing=None,
            include_flow_ids=['flow'], include_movement_ids=['payment-1'],
        )


def test_zaf_migration_is_an_evidence_based_unavailable_account_case():
    """The real candidate does not silently turn pledges or register dates into payments."""
    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / 'config/jetp-zaf-migration.json').read_text(encoding='utf-8'))
    report = (root / 'docs/jetp-zaf-gross-disbursement-0768.md').read_text(encoding='utf-8')
    assert policy['payments'] == []
    assert 'gross-disbursement account unavailable' in report
    assert 'register dates are not payment dates' in report
    assert 'no reconstructed closing or residual is published' in report
