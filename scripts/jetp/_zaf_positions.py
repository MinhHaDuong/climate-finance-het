"""Stage register positions separately from explicitly evidenced payment assertions."""

from datetime import date
from decimal import Decimal, InvalidOperation

from jetp._contracts import validate_evidence_tuple
from jetp._source_crosswalk import _identity
from jetp.build_zaf_investment_register import _project_id


def migrate_positions(rows: list[dict], *, payments: list[dict]) -> dict:
    """Preserve register labels and dates; only separate payment evidence makes events."""
    positions = []
    project_ids = {_project_id(row['Unique ID']) for row in rows}
    if len(project_ids) != len(rows):
        raise ValueError('Duplicate register identities')
    for row in rows:
        positions.append({
            'record_kind': 'position_candidate',
            'record_id': _identity('zaf-register-position', row),
            'project_id': _project_id(row['Unique ID']), 'source_fields': dict(row),
            'measure': 'reported_register_funding', 'basis': 'reported_position',
            'original_label': 'Amount: Pledged', 'amount_original': row.get('Amount: Pledged'),
            'currency_original': row.get('Currency: Pledged'),
            'reported_usd': row.get('Total US$'), 'reported_zar': row.get('Total ZAR'),
            'implementation_status': row.get('Status'),
            'financial_instrument': row.get('Funding Instrument'),
            'date_role': 'register_date_label_retained_not_transition',
            'transition_date': None, 'payment_amount': None,
            'eligible_for_account': False, 'historical_admission': 'unknown',
            'reason': 'Register membership, funding and implementation labels do not establish a payment',
            'admission_status': 'unadmitted_candidate', 'review_state': 'pending'})
    events, seen = [], set()
    for payment in payments:
        try:
            validate_evidence_tuple(payment['evidence'], payment['acquisition'],
                                    payment['extraction'], [payment['edition_snapshot']])
            amount = Decimal(payment['amount_original'])
            date.fromisoformat(payment['event_date'])
            if (payment['project_id'] not in project_ids or not payment['source_wording']
                    or payment['amount_basis'] != 'incremental_payment'
                    or not amount.is_finite() or amount <= 0
                    or len(payment['currency_original']) != 3
                    or payment['event_id'] in seen):
                raise ValueError('Payment needs distinct identity, project, original amount and evidence')
        except (KeyError, TypeError, InvalidOperation) as exc:
            raise ValueError('Incomplete separately documented payment') from exc
        seen.add(payment['event_id'])
        events.append({**payment, 'record_kind': 'event_candidate',
                       'measure': 'gross_disbursement', 'eligible_for_account': False,
                       'historical_admission': 'unknown', 'admission_status': 'unadmitted_candidate',
                       'review_state': 'pending',
                       'reason': 'Payment evidence retained; occurrence, coverage and admission await account review'})
    return {'reported_positions': positions, 'event_candidates': events}
