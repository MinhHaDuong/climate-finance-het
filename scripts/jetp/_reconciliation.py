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
            and item.get('agreement_id') == agreement_id
            and item.get('perimeter_id') == perimeter_id
            and item.get('currency') == currency
            and item.get('basis') == METRIC_BASIS)


def _reviewed(item):
    return (item.get('accepted') is True and bool(item.get('review_decision_id'))
            and isinstance(item.get('evidence_ids'), list) and bool(item['evidence_ids']))


def _unavailable(reasons, *, included_ids=None, excluded_ids=None, subtotal='0'):
    return {
        'status': 'unavailable', 'reasons': sorted(set(reasons)),
        'included_ids': included_ids or [], 'excluded_ids': excluded_ids or [],
        'documented_subtotal': Decimal(subtotal), 'reconstructed_closing': None,
        'residual': None,
    }


def _opening_and_coverage(opening, coverage, *, agreement_id, perimeter_id, currency, cutoff):
    reasons = []
    if not opening:
        reasons.append('opening')
        opening_cutoff = None
    elif not _compatible(opening, agreement_id=agreement_id, perimeter_id=perimeter_id,
                         currency=currency):
        reasons.append('opening compatibility')
        opening_cutoff = None
    elif not _reviewed(opening):
        reasons.append('opening evidence')
        opening_cutoff = None
    else:
        opening_cutoff = opening.get('cutoff')
        if not opening_cutoff or opening_cutoff >= cutoff:
            reasons.append('opening cutoff')
    if not isinstance(coverage, dict) or not coverage.get('reviewer') or not coverage.get('decision_id'):
        reasons.append('coverage decision')
    elif coverage.get('complete') is not True:
        reasons.append('coverage')
    return opening_cutoff, reasons


def _compatible_items(items, kind, *, agreement_id, perimeter_id, currency, opening_cutoff, cutoff):
    compatible, reasons = [], []
    for item in items:
        if not _compatible(item, agreement_id=agreement_id, perimeter_id=perimeter_id, currency=currency):
            reasons.append('currency' if item.get('currency') != currency else f'{kind} compatibility')
            continue
        if not _reviewed(item):
            reasons.append(f'{kind} evidence')
            continue
        start, end = ('date', 'date') if kind == 'movement' else ('coverage_start', 'coverage_end')
        if not item.get(start) or not item.get(end):
            raise ReconciliationError(f'{kind} needs exact {"date" if kind == "movement" else "coverage"}')
        if kind == 'movement' and not item.get('occurrence_id'):
            raise ReconciliationError('movement needs reviewed occurrence and exact date')
        if opening_cutoff and not _inside(item, opening_cutoff, cutoff, start=start, end=end):
            raise ReconciliationError(f'{kind} lies outside account interval')
        compatible.append(item)
    return compatible, reasons


def _selected(items, requested):
    explicit = requested is not None
    ids = set(requested if explicit else [item['id'] for item in items])
    if not ids <= {item['id'] for item in items}:
        raise ReconciliationError('selected input is not compatible')
    return [item for item in items if item['id'] in ids], ids, explicit


def _cover(flows, movements, movement_ids, movements_explicit):
    covered, excluded = set(), []
    for flow in flows:
        occurrences = flow.get('covered_occurrence_ids')
        if not isinstance(occurrences, list) or not occurrences:
            raise ReconciliationError('flow needs explicit covered occurrences')
        if covered & set(occurrences):
            raise ReconciliationError('overlap between selected flows')
        covered.update(occurrences)
    if movements_explicit and movement_ids & {m['id'] for m in movements if m['occurrence_id'] in covered}:
        raise ReconciliationError('overlap between selected flow and movement')
    selected, occurrences = [], {}
    for movement in movements:
        if movement['id'] not in movement_ids or movement['occurrence_id'] in covered:
            excluded.append(movement['id'])
            continue
        prior = occurrences.get(movement['occurrence_id'])
        if prior:
            if (_money(prior['amount'], 'movement') != _money(movement['amount'], 'movement')
                    or prior['date'] != movement['date']):
                raise ReconciliationError('duplicate occurrence has incompatible reports')
            excluded.append(movement['id'])
            continue
        occurrences[movement['occurrence_id']] = movement
        selected.append(movement)
    return selected, excluded


def reconcile_gross_disbursement(*, agreement_id, perimeter_id, currency, opening,
                                  movements, flows, coverage, cutoff, reported_closing,
                                  include_flow_ids=None, include_movement_ids=None):
    """Construct one bounded original-currency gross-disbursement account.

    The caller supplies accepted agreement/perimeter/occurrence decisions. A flow
    replaces, rather than adds to, each explicitly covered occurrence. The result
    is exact only with a reviewed opening and complete movement coverage.
    """
    request_reasons = []
    if not agreement_id:
        request_reasons.append('request agreement identity')
    if not perimeter_id:
        request_reasons.append('request perimeter identity')
    if request_reasons:
        return _unavailable(request_reasons)
    opening_cutoff, reasons = _opening_and_coverage(
        opening, coverage, agreement_id=agreement_id, perimeter_id=perimeter_id,
        currency=currency, cutoff=cutoff)
    accepted_movements, item_reasons = _compatible_items(
        movements, 'movement', agreement_id=agreement_id, perimeter_id=perimeter_id,
        currency=currency, opening_cutoff=opening_cutoff, cutoff=cutoff)
    accepted_flows, flow_reasons = _compatible_items(
        flows, 'flow', agreement_id=agreement_id, perimeter_id=perimeter_id,
        currency=currency, opening_cutoff=opening_cutoff, cutoff=cutoff)
    if reasons + item_reasons + flow_reasons:
        return _unavailable(reasons + item_reasons + flow_reasons)
    selected_flows, flow_ids, _ = _selected(accepted_flows, include_flow_ids)
    selected_movements, movement_ids, movements_explicit = _selected(
        accepted_movements, include_movement_ids)
    if set(item['id'] for item in accepted_movements) & movement_ids != movement_ids:
        raise ReconciliationError('selected movement is not compatible')
    selected_movements, excluded = _cover(
        selected_flows, accepted_movements, movement_ids, movements_explicit)
    included = selected_flows + selected_movements
    subtotal = sum((_money(item['amount'], 'movement') for item in included), Decimal('0'))
    result = {'status': 'exact', 'reasons': [], 'included_ids': [x['id'] for x in included],
              'excluded_ids': excluded, 'documented_subtotal': subtotal,
              'reconstructed_closing': _money(opening['amount'], 'opening') + subtotal,
              'residual': None, 'coverage_decision_id': coverage['decision_id']}
    if reported_closing:
        if (_compatible(reported_closing, agreement_id=agreement_id, perimeter_id=perimeter_id,
                        currency=currency) and _reviewed(reported_closing)
                and reported_closing.get('cutoff') == cutoff):
            result['residual'] = _money(reported_closing['amount'], 'reported closing') - result['reconstructed_closing']
        else:
            result['reported_closing_comparability'] = 'failed'
    return result
