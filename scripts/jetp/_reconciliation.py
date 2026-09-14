"""Fail-closed account construction for the first JETP financial metric.

This module only derives a single original-currency gross-disbursement account.
It accepts reviewed, typed input from a migration; it neither admits source claims
nor writes the canonical observatory payload.
"""

from decimal import Decimal, InvalidOperation


METRIC_BASIS = 'gross_disbursement'


class ReconciliationError(ValueError):
    """Reviewed account inputs cannot form a disjoint movement cover."""


def _money(value, label):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ReconciliationError(f'{label} amount is not a decimal') from exc
    if not amount.is_finite() or amount < 0:
        raise ReconciliationError(f'{label} amount must be a non-negative decimal')
    return amount


def _inside(item, opening_cutoff, cutoff, *, start='date', end='date'):
    return opening_cutoff < item[start] and item[end] <= cutoff


def _compatible(item, *, agreement_id, perimeter_id, currency):
    return (item and item.get('accepted') is True
            and item.get('agreement_id', agreement_id) == agreement_id
            and item.get('perimeter_id', perimeter_id) == perimeter_id
            and item.get('currency') == currency
            and item.get('basis') == METRIC_BASIS)


def _unavailable(reasons, *, included_ids=None, excluded_ids=None, subtotal='0'):
    return {
        'status': 'unavailable',
        'reasons': sorted(set(reasons)),
        'included_ids': included_ids or [],
        'excluded_ids': excluded_ids or [],
        'documented_subtotal': Decimal(subtotal),
        'reconstructed_closing': None,
        'residual': None,
    }


def reconcile_gross_disbursement(*, agreement_id, perimeter_id, currency, opening,
                                  movements, flows, coverage, cutoff, reported_closing,
                                  include_flow_ids=None, include_movement_ids=None):
    """Construct one bounded original-currency gross-disbursement account.

    The caller supplies accepted agreement/perimeter/occurrence decisions.  A flow
    replaces, rather than adds to, each explicitly covered occurrence.  The result
    is exact only with a reviewed opening and complete movement coverage.
    """
    reasons = []
    if not opening:
        reasons.append('opening')
        opening_cutoff = None
    elif not _compatible(opening, agreement_id=agreement_id, perimeter_id=perimeter_id,
                         currency=currency):
        reasons.append('opening compatibility')
        opening_cutoff = None
    else:
        opening_cutoff = opening.get('cutoff')
        if not opening_cutoff or opening_cutoff >= cutoff:
            reasons.append('opening cutoff')
    if not isinstance(coverage, dict) or not coverage.get('reviewer') or not coverage.get('decision_id'):
        reasons.append('coverage decision')
    elif coverage.get('complete') is not True:
        reasons.append('coverage')

    compatible_movements = []
    for movement in movements:
        if not _compatible(movement, agreement_id=agreement_id, perimeter_id=perimeter_id,
                           currency=currency):
            reasons.append('currency' if movement.get('currency') != currency else 'movement compatibility')
            continue
        if not movement.get('occurrence_id') or not movement.get('date'):
            raise ReconciliationError('movement needs reviewed occurrence and exact date')
        if opening_cutoff and not _inside(movement, opening_cutoff, cutoff):
            raise ReconciliationError('movement lies outside account interval')
        compatible_movements.append(movement)

    compatible_flows = []
    for flow in flows:
        if not _compatible(flow, agreement_id=agreement_id, perimeter_id=perimeter_id, currency=currency):
            reasons.append('currency' if flow.get('currency') != currency else 'flow compatibility')
            continue
        if not flow.get('coverage_start') or not flow.get('coverage_end'):
            raise ReconciliationError('flow needs exact coverage')
        if opening_cutoff and not _inside(flow, opening_cutoff, cutoff,
                                          start='coverage_start', end='coverage_end'):
            raise ReconciliationError('flow lies outside account interval')
        compatible_flows.append(flow)

    if reasons:
        return _unavailable(reasons)

    movements_were_selected = include_movement_ids is not None
    requested_flows = set(include_flow_ids if include_flow_ids is not None
                          else [f['id'] for f in compatible_flows])
    requested_movements = set(include_movement_ids if movements_were_selected
                              else [m['id'] for m in compatible_movements])
    selected_flows = [f for f in compatible_flows if f['id'] in requested_flows]
    movement_by_id = {m['id']: m for m in compatible_movements}
    covered = set()
    for flow in selected_flows:
        occurrences = flow.get('covered_occurrence_ids')
        if not isinstance(occurrences, list) or not occurrences:
            raise ReconciliationError('flow needs explicit covered occurrences')
        overlap = covered & set(occurrences)
        if overlap:
            raise ReconciliationError('overlap between selected flows')
        covered.update(occurrences)

    selected_movements = []
    seen_occurrences = {}
    excluded = []
    for movement in compatible_movements:
        if movement['id'] not in requested_movements or movement['occurrence_id'] in covered:
            excluded.append(movement['id'])
            continue
        prior = seen_occurrences.get(movement['occurrence_id'])
        if prior:
            if (_money(prior['amount'], 'movement') != _money(movement['amount'], 'movement')
                    or prior['date'] != movement['date']):
                raise ReconciliationError('duplicate occurrence has incompatible reports')
            excluded.append(movement['id'])
            continue
        seen_occurrences[movement['occurrence_id']] = movement
        selected_movements.append(movement)

    if set(movement_by_id) & requested_movements != requested_movements:
        raise ReconciliationError('selected movement is not compatible')
    if movements_were_selected and (set(requested_movements)
                                    & {m['id'] for m in compatible_movements
                                       if m['occurrence_id'] in covered}):
        raise ReconciliationError('overlap between selected flow and movement')

    included = selected_flows + selected_movements
    subtotal = sum((_money(item['amount'], 'movement') for item in included), Decimal('0'))
    reconstructed = _money(opening['amount'], 'opening') + subtotal
    result = {'status': 'exact', 'reasons': [], 'included_ids': [x['id'] for x in included],
              'excluded_ids': excluded, 'documented_subtotal': subtotal,
              'reconstructed_closing': reconstructed, 'residual': None,
              'coverage_decision_id': coverage['decision_id']}
    if reported_closing:
        if _compatible(reported_closing, agreement_id=agreement_id, perimeter_id=perimeter_id,
                       currency=currency) and reported_closing.get('cutoff') == cutoff:
            result['residual'] = _money(reported_closing['amount'], 'reported closing') - reconstructed
        else:
            result['reported_closing_comparability'] = 'failed'
    return result
