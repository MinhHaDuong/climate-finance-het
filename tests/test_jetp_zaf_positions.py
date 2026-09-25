"""Register observations retain their source meaning instead of becoming payments."""

from decimal import Decimal

import pytest

pytestmark = pytest.mark.wp_jetp

def test_register_start_and_allocation_do_not_duplicate_a_separate_payment():
    from jetp._zaf_positions import migrate_positions

    register = [{'Unique ID': 'P1', 'Project Name': 'Programme and its components',
                 'Portfolios': 'Electricity', 'Status': 'C. Implementation Phase',
                 'Date of Financing Agreement Signed*': '2024-01-01T00:00:00',
                 'Amount: Pledged': 100, 'Currency: Pledged': 'EUR', 'Total US$': 110}]
    digest = 'a' * 64
    edition = {'record_kind': 'edition', 'record_id': 'payment-report'}
    payment = {'event_id': 'paid-once', 'project_id': 'zaf-register-p1',
               'event_date': '2024-03-14', 'amount_original': '25', 'currency_original': 'EUR',
               'amount_basis': 'incremental_payment', 'source_wording': 'EUR 25 paid on 14 March',
               'evidence': {'document_sha256': digest, 'edition': edition, 'locator': 'p7'},
               'acquisition': {'document_sha256': digest},
               'extraction': {'document_sha256': digest, 'locators': ['p7']},
               'edition_snapshot': {'record_kind': 'edition_snapshot', 'edition': edition,
                                    'document_sha256': digest}}
    result = migrate_positions(register, payments=[payment])
    position = result['reported_positions'][0]
    assert position['source_fields'] == register[0]
    assert position['transition_date'] is None
    assert position['payment_amount'] is None
    assert position['amount_original'] == 100
    assert position['original_label'] == 'Amount: Pledged'
    assert position['date_role'] == 'register_date_label_retained_not_transition'
    assert len(result['event_candidates']) == 1
    event = result['event_candidates'][0]
    assert event['event_id'] == 'paid-once'
    assert event['event_date'] == '2024-03-14'
    assert sum(Decimal(row['amount_original']) for row in result['event_candidates']) == 25
    assert event['eligible_for_account'] is False  # Occurrence/admission belongs to 0768.
    with pytest.raises(ValueError):
        migrate_positions(register, payments=[{**payment, 'evidence': {}}])
