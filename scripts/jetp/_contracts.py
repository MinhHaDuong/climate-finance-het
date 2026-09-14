"""Versioned candidate contracts; legacy CSVs retain all write authority.

The JSON interchange is deliberately small: typed immutable records and reviewed
replacement chains. It validates fixture/candidate inputs without publishing or
migrating them. Unknown versions and record kinds fail closed.
"""

from collections.abc import Collection
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

SCHEMA_VERSION = 'jetp-core-v1'
ASSERTIONS = {'financial_event', 'implementation_event', 'position'}
SUBJECTS = {'country', 'partnership', 'entity', 'agreement', 'perimeter'}
REQUIRED = {
    'country': set(), 'partnership': {'country'}, 'entity': {'country'},
    'agreement': {'country'},
    'perimeter': {'country', 'name', 'scope', 'definition', 'membership_basis'},
    **{kind: {'subject', 'measure', 'value_type', 'original_label'} for kind in ASSERTIONS},
    'occurrence': set(),
    'relation': {'from', 'to', 'relationship', 'valid_from', 'valid_to', 'date_precision'},
    'adjudication': {'decision_type', 'verdict', 'reason', 'reviewer', 'reviewed_at',
                     'policy_version', 'members'},
    'source': {'url'},
    'acquisition': {'source', 'retrieved_at', 'outcome'},
    'edition': {'publication_key', 'title', 'publisher', 'publication_date', 'publication_precision'},
    'edition_snapshot': {'edition', 'document_sha256'},
    'extraction': {'document_sha256', 'parser_version', 'locators'},
    'evidence': {'target', 'edition', 'acquisition', 'document_sha256', 'locator',
                 'extraction', 'support_role'},
    'study': {'name'},
    'protocol_revision': {'study', 'eligibility_rule', 'frozen_at', 'reviewer'},
    'frame': {'protocol', 'evidence_cutoff', 'eligibility_rule', 'population_coverage'},
    'frame_member': {'frame', 'unit', 'verdict', 'reason', 'baseline_maturity'},
    'observation_attempt': {'subject', 'sought', 'route', 'check_date', 'result'},
    'coverage_assessment': {'subject', 'sought', 'assessed_at', 'result', 'reason'},
}
RELATION_TYPES = {
    'component_of': ({'entity'}, {'entity'}),
    'finances': ({'agreement'}, {'entity'}),
    'tranche_of': ({'agreement'}, {'agreement'}),
    'member_of': (SUBJECTS - {'perimeter'}, {'perimeter'}),
    'perimeter_within': ({'perimeter'}, {'perimeter'}),
    'same_as': (SUBJECTS, SUBJECTS), 'alias_of': (SUBJECTS, SUBJECTS),
    'successor_of': (SUBJECTS, SUBJECTS),
}
# (allowed role, allowed kinds, minimum, maximum); None means unbounded.
DECISION_ROLES = {
    'acceptance': {'candidate': (set(REQUIRED) - {'adjudication'}, 1, 1)},
    'occurrence_membership': {
        'accepted': ({'financial_event', 'implementation_event'}, 1, None),
        'occurrence': ({'occurrence'}, 1, 1)},
    'flow_coverage': {'covering_flow': ({'position'}, 1, 1),
                      'covered_movement': (ASSERTIONS - {'implementation_event'}, 1, None)},
}
REF_FIELDS = {
    'subject': SUBJECTS, 'from': SUBJECTS, 'to': SUBJECTS,
    'perimeter': {'perimeter'}, 'source': {'source'}, 'edition': {'edition'},
    'acquisition': {'acquisition'}, 'extraction': {'extraction'},
    'target': set(REQUIRED) - {'adjudication'}, 'study': {'study'},
    'protocol': {'protocol_revision'}, 'frame': {'frame'}, 'unit': SUBJECTS,
}


class ContractError(ValueError):
    """A candidate cannot satisfy the declared versioned contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _key(reference: dict[str, str]) -> tuple[str, str]:
    _require(isinstance(reference, dict) and set(reference) == {'record_kind', 'record_id'},
             'reference must be an exact typed pair')
    kind, identity = reference['record_kind'], reference['record_id']
    _require(isinstance(kind, str) and isinstance(identity, str) and bool(identity),
             'reference kind and ID must be nonempty strings')
    return kind, identity


def _time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        _require(result.tzinfo is not None, 'timestamp must include timezone')
        return result
    except (AttributeError, TypeError, ValueError) as exc:
        raise ContractError(f'invalid timestamp: {value!r}') from exc


def _day(value: str) -> date:
    try:
        _require(isinstance(value, str) and len(value) == 10, 'date must be ISO calendar day')
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f'invalid date: {value!r}') from exc


def _decimal(value: str) -> Decimal:
    _require(isinstance(value, str) and bool(value), 'decimal must be a lossless string')
    try:
        result = Decimal(value)
        _require(result.is_finite(), 'decimal must be finite')
        return result
    except InvalidOperation as exc:
        raise ContractError('invalid decimal') from exc


def _bounds(record: dict, first: str, last: str, precision: str) -> None:
    start, end = record.get(first), record.get(last)
    if start is None and end is None:
        return
    _require(bool(start) and bool(end), f'{first}/{last} need both bounds')
    _require(_day(start) <= _day(end), f'{first}/{last} bounds reversed')
    _require(record.get(precision) in {'day', 'month', 'quarter', 'year', 'range'},
             f'{precision} is required')
    if record[precision] == 'day' and first != 'coverage_start':
        _require(start == end, 'day precision requires one exact day')


def _validate_value(record: dict) -> None:
    kind = record['value_type']
    _require(kind in {'money', 'number', 'count', 'status', 'text'}, 'unknown value_type')
    numeric, textual = record.get('value_decimal'), record.get('value_text')
    missing = record.get('missing_reason')
    _require((numeric is not None) + (textual is not None) == (0 if missing else 1),
             'exactly one scalar or explicit missing_reason required')
    if not missing:
        if kind in {'money', 'number', 'count'}:
            value = _decimal(numeric)
            if kind == 'count':
                _require(value >= 0 and value == value.to_integral_value(), 'count must be nonnegative integer')
            low = _decimal(record['value_lower']) if record.get('value_lower') is not None else value
            high = _decimal(record['value_upper']) if record.get('value_upper') is not None else value
            _require(low <= value <= high, 'value outside uncertainty bounds')
        else:
            _require(isinstance(textual, str) and bool(textual), 'text/status needs value_text')
    if kind == 'money':
        currency = record.get('currency')
        _require(isinstance(currency, str) and len(currency) == 3 and currency.isupper()
                 and currency.isalpha(), 'money needs currency')
        _require(record.get('unit') == currency, 'money must use whole currency units')
        _require('perimeter' in record or bool(record.get('coverage_gap')), 'money needs perimeter or coverage_gap')
        _require(bool(record.get('original_value')) and bool(record.get('original_scale')),
                 'money needs original value and scale')
        scales = {'unit': Decimal(1), 'thousand': Decimal(1000),
                  'million': Decimal(1000000), 'billion': Decimal(1000000000)}
        _require(record['original_scale'] in scales, 'unknown original amount scale')
        if not missing:
            _require(_decimal(record['original_value']) * scales[record['original_scale']] == value,
                     'whole-unit amount disagrees with original scale')
    if kind == 'count':
        _require(bool(record.get('unit')) and bool(record.get('classification_level'))
                 and ('perimeter' in record or bool(record.get('coverage_gap'))),
                 'count needs unit, classification level and coverage')
    if record['subject']['record_kind'] in {'partnership', 'perimeter'}:
        _require('perimeter' in record or bool(record.get('coverage_gap')), 'aggregate needs coverage')
    _require(bool(record.get('evidence')) or bool(record.get('evidence_gap')), 'assertion needs evidence or gap')
    roles = set()
    for timing in record.get('timing', []):
        role = timing.get('date_role')
        _require(role in {'event', 'observed_state', 'registered', 'unreviewed'}, 'invalid date role')
        _require(role not in roles, 'duplicate typed date role')
        roles.add(role)
        _bounds(timing, 'event_start', 'event_end', 'event_precision')
    if record['record_kind'] == 'position':
        _require(not record.get('timing'), 'positions own cutoff/coverage dates, not event timing')
        basis = record.get('basis')
        _require(basis in {'cumulative_amount', 'period_flow', 'balance', 'status', 'inventory_membership'},
                 'position needs basis')
        _bounds(record, 'cutoff_earliest', 'cutoff_latest', 'cutoff_precision')
        _bounds(record, 'coverage_start', 'coverage_end', 'coverage_precision')
        if basis == 'period_flow':
            _require(bool(record.get('coverage_start')) or bool(record.get('coverage_gap')),
                     'period flow needs coverage or explicit gap')
        else:
            _require(bool(record.get('cutoff_earliest')) or bool(record.get('cutoff_gap')),
                     'position needs cutoff or explicit gap')


def _acyclic(edges: dict[tuple, list[tuple]], label: str) -> None:
    visited, visiting = set(), set()

    def visit(node: tuple) -> None:
        _require(node not in visiting, f'{label} cycle')
        if node in visited:
            return
        visiting.add(node)
        for target in edges.get(node, []):
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in edges:
        visit(node)


class ContractStore:
    """Validated immutable input copy; all query results are independent copies."""

    def __init__(self, document: dict[str, Any]):
        self._document = deepcopy(document)
        self._records: dict[tuple[str, str], dict] = {}
        _require(isinstance(document.get('records'), list), 'records must be a list')
        for record in self._document['records']:
            _require(isinstance(record, dict), 'record must be an object')
            key = _key({name: record.get(name) for name in ('record_kind', 'record_id')})
            _require(key[0] in REQUIRED, f'unregistered record kind {key[0]}')
            _require(key not in self._records, f'duplicate typed identity {key}')
            _require(REQUIRED[key[0]] | {'recorded_at', 'recorded_by'} <= record.keys(),
                     f'missing fields for {key}')
            _require(bool(record['recorded_by']), 'recorded_by required')
            _time(record['recorded_at'])
            self._records[key] = record
        for key, record in self._records.items():
            self._validate_record(key, record)
        edges = {key: [_key(r['supersedes'])] for key, r in self._records.items() if r.get('supersedes')}
        _acyclic(edges, 'supersession')
        for record in self._records.values():
            if record['record_kind'] == 'evidence':
                self._validate_evidence(record)

    def _resolve(self, reference: dict, kinds: set[str]) -> dict:
        key = _key(reference)
        _require(key[0] in kinds and key in self._records, f'unresolved or invalid typed reference {key}')
        return self._records[key]

    def _validate_record(self, key: tuple[str, str], record: dict) -> None:
        kind = key[0]
        for field, kinds in REF_FIELDS.items():
            if record.get(field) is not None and (field != 'unit' or kind == 'frame_member'):
                self._resolve(record[field], kinds)
        for reference in record.get('evidence', []):
            evidence = self._resolve(reference, {'evidence'})
            _require(_key(evidence['target']) == key, 'evidence target does not match assertion')
        if record.get('supersedes'):
            old = self._resolve(record['supersedes'], {kind})
            _require(bool(record.get('correction_reason')), 'supersession needs correction_reason')
            _require(_time(old['recorded_at']) <= _time(record['recorded_at']), 'supersession predates original')
            for field in ('subject', 'measure') if kind in ASSERTIONS else ():
                _require(record[field] == old[field], f'supersession changes {field}')
            if kind == 'adjudication':
                _require(record['decision_type'] == old['decision_type'], 'decision replacement changes type')
        validators = {'relation': self._validate_relation, 'adjudication': self._validate_decision,
                      'acquisition': self._validate_acquisition}
        if kind in ASSERTIONS:
            subject = self._resolve(record['subject'], SUBJECTS)
            _require(subject.get('identity_type') != 'legacy_count_slot',
                     'legacy count slot cannot represent an inferred project subject')
            _validate_value(record)
        elif kind in validators:
            validators[kind](record)
        self._validate_metadata(kind, record)

    def _validate_relation(self, record: dict) -> None:
        relationship = record['relationship']
        _require(relationship in RELATION_TYPES, 'unknown relationship')
        source_kinds, target_kinds = RELATION_TYPES[relationship]
        self._resolve(record['from'], source_kinds)
        self._resolve(record['to'], target_kinds)
        if relationship in {'alias_of', 'same_as', 'successor_of'}:
            _require(record['from']['record_kind'] == record['to']['record_kind'], 'identity type mismatch')
        for field in ('valid_from', 'valid_to'):
            if record[field] not in {'unknown', 'open'}:
                _day(record[field])
        if record['valid_from'] not in {'unknown', 'open'} and record['valid_to'] not in {'unknown', 'open'}:
            _require(record['valid_from'] < record['valid_to'], 'empty or reversed half-open validity')
        _require(record['date_precision'] in {'day', 'month', 'year', 'range', 'unknown'}, 'invalid relation precision')

    def _validate_decision(self, record: dict) -> None:
        _time(record['reviewed_at'])
        _require(all(isinstance(record[f], str) and record[f] for f in ('reason', 'reviewer', 'policy_version')),
                 'decision needs reviewer, reason and policy')
        _require(record['verdict'] in {'accepted', 'rejected', 'withdrawn', 'pending'}, 'invalid verdict')
        roles = DECISION_ROLES.get(record['decision_type'])
        _require(roles is not None, 'unsupported decision type')
        _require(isinstance(record['members'], list), 'members must be a list')
        seen = set()
        for member in record['members']:
            _require(isinstance(member, dict) and set(member) == {'role', 'target'}, 'invalid decision member')
            role = member['role']
            _require(role in roles, 'invalid decision role')
            self._resolve(member['target'], roles[role][0])
            pair = (role, _key(member['target']))
            _require(pair not in seen, 'duplicate decision member')
            seen.add(pair)
        for role, (_, minimum, maximum) in roles.items():
            count = sum(m['role'] == role for m in record['members'])
            _require(count >= minimum and (maximum is None or count <= maximum), 'decision cardinality')

    @staticmethod
    def _validate_acquisition(record: dict) -> None:
        _time(record['retrieved_at'])
        _require(record['outcome'] in {'saved', 'not_modified', 'failed', 'blocked'}, 'invalid acquisition outcome')
        if record['outcome'] in {'saved', 'not_modified'}:
            _require(bool(record.get('document_sha256')), 'successful acquisition needs hash')
        else:
            _require(not record.get('document_sha256'), 'failed acquisition cannot carry material')

    @staticmethod
    def _validate_metadata(kind: str, record: dict) -> None:
        if kind == 'edition':
            if record['publication_date'] is not None:
                _day(record['publication_date'])
        elif kind == 'evidence':
            _require(record['support_role'] in {'supporting', 'contradicting', 'contextual'}, 'invalid support role')
        elif kind == 'protocol_revision':
            _time(record['frozen_at'])
        elif kind == 'frame':
            _time(record['evidence_cutoff'])
            _require(record['population_coverage'] in {'reconstructed', 'unresolved', 'completed_only'},
                     'frame needs population coverage verdict')
        elif kind == 'frame_member':
            _require(record['verdict'] in {'included', 'excluded', 'unresolved'}, 'invalid frame verdict')
        elif kind == 'coverage_assessment':
            _time(record['assessed_at'])
            _require(record['result'] == 'not_sought', 'unknown coverage assessment')
        elif kind == 'observation_attempt':
            _day(record['check_date'])
            _require(record['result'] in {'found', 'not_published', 'blocked', 'unreadable', 'loss_of_visibility'},
                     'not_sought is an assessment, not an observation attempt')
            if record['result'] == 'found':
                _require(bool(record.get('evidence')), 'found document requires evidence')
        if record.get('document_sha256') is not None:
            digest = record['document_sha256']
            _require(isinstance(digest, str) and len(digest) == 64
                     and all(c in '0123456789abcdef' for c in digest), 'invalid document hash')

    def _validate_evidence(self, record: dict) -> None:
        acquisition = self._resolve(record['acquisition'], {'acquisition'})
        extraction = self._resolve(record['extraction'], {'extraction'})
        digest = record['document_sha256']
        _require(acquisition.get('document_sha256') == digest, 'evidence acquisition hash mismatch')
        _require(extraction['document_sha256'] == digest, 'evidence extraction hash mismatch')
        _require(record['locator'] in extraction['locators'], 'evidence locator not in extraction')
        _require(any(r['record_kind'] == 'edition_snapshot' and r['edition'] == record['edition']
                     and r['document_sha256'] == digest for r in self._records.values()),
                 'evidence hash not mapped to edition')
        target = self._resolve(record['target'], set(REQUIRED) - {'adjudication'})
        if target['record_kind'] in ASSERTIONS:
            _require({'record_kind': 'evidence', 'record_id': record['record_id']} in target.get('evidence', []),
                     'evidence target must link back to evidence')

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self._document)

    def at(self, evidence_cutoff: str, *, policy_version: str) -> 'ContractView':
        return ContractView(self._records, evidence_cutoff, policy_version)


def read_contract(document: dict[str, Any], *, supported_versions: Collection[str]) -> ContractStore:
    """Read only the explicitly negotiated candidate schema; never write stores."""
    _require(isinstance(document, dict), 'contract document must be an object')
    version = document.get('schema_version')
    _require(version == SCHEMA_VERSION and version in supported_versions, 'unsupported schema version')
    return ContractStore(document)


class ContractView:
    """Knowledge-cutoff projection, with world validity applied to relationships."""

    def __init__(self, records: dict[tuple[str, str], dict], cutoff: str, policy: str):
        self.evidence_cutoff, self.policy_version = cutoff, policy
        limit = _time(cutoff)
        admitted = {key: deepcopy(record) for key, record in records.items()
                    if _time(record['recorded_at']) <= limit
                    and (key[0] != 'adjudication' or
                         (_time(record['reviewed_at']) <= limit and record['policy_version'] == policy))}
        # Dependency cycles (assertion <-> evidence) are intentional. Prune to a
        # fixed point instead of recursive traversal that mistakes them for history.
        while True:
            unavailable = {key for key, record in admitted.items()
                           if not self._dependencies_admitted(record, admitted)}
            if not unavailable:
                break
            for key in unavailable:
                del admitted[key]
        self.records = admitted
        decisions = {key: r for key, r in admitted.items()
                     if key[0] == 'adjudication' and r['verdict'] != 'pending'}
        decisions = self._live(decisions, admitted, 'decision supersession')
        self.decisions = decisions
        states: dict[tuple[str, str], str] = {}
        for decision in decisions.values():
            if decision['decision_type'] == 'acceptance':
                target = _key(decision['members'][0]['target'])
                _require(target not in states, f'conflicting active acceptance decisions for {target}')
                states[target] = decision['verdict']
        accepted = {key: admitted[key] for key, verdict in states.items() if verdict == 'accepted'}
        self._accepted = self._live(accepted, admitted, 'assertion supersession')
        self._occurrences: dict[tuple[str, str], dict] = {}
        for decision in decisions.values():
            if decision['decision_type'] != 'occurrence_membership' or decision['verdict'] != 'accepted':
                continue
            occurrence = next(m['target'] for m in decision['members'] if m['role'] == 'occurrence')
            for member in decision['members']:
                if member['role'] != 'accepted':
                    continue
                target = _key(member['target'])
                if target not in self._accepted:
                    continue
                _require(target not in self._occurrences, 'multiple active occurrence assignments')
                self._occurrences[target] = occurrence

    @staticmethod
    def _dependencies_admitted(record: dict, admitted: dict) -> bool:
        references = [record[f] for f in REF_FIELDS if record.get(f) is not None
                      and (f != 'unit' or record['record_kind'] == 'frame_member')]
        references += record.get('evidence', [])
        references += [m['target'] for m in record.get('members', [])]
        # Historical supersession does not require the replaced record to remain
        # live, but its admission is required before the replacement can operate.
        if record.get('supersedes'):
            references.append(record['supersedes'])
        if any(_key(r) not in admitted for r in references):
            return False
        if record['record_kind'] == 'evidence':
            return any(r['record_kind'] == 'edition_snapshot' and r['edition'] == record['edition']
                       and r['document_sha256'] == record['document_sha256'] for r in admitted.values())
        return True

    @staticmethod
    def _live(records: dict, admitted: dict, label: str) -> dict:
        ancestors = {}
        for key, record in records.items():
            chain = set()
            while record.get('supersedes'):
                parent = _key(record['supersedes'])
                chain.add(parent)
                record = admitted[parent]
            ancestors[key] = chain
        live = {key: r for key, r in records.items()
                if not any(key in chain for chain in ancestors.values())}
        keys = list(live)
        for index, key in enumerate(keys):
            for other in keys[index + 1:]:
                _require(not (ancestors[key] & ancestors[other]), f'{label} fork')
        return live

    def accepted(self, reference: dict[str, str]) -> bool:
        return _key(reference) in self._accepted

    def occurrence_for(self, reference: dict[str, str]) -> dict | None:
        return deepcopy(self._occurrences.get(_key(reference)))

    def relations_at(self, world_date: str) -> list[dict]:
        """Resolve exact half-open validity; unknown consequential bounds fail."""
        day = _day(world_date)
        relations = []
        for key, record in self._accepted.items():
            if key[0] != 'relation':
                continue
            start, end = record['valid_from'], record['valid_to']
            _require('unknown' not in {start, end} and record['date_precision'] == 'day',
                     'unresolved relation validity')
            if (start == 'open' or _day(start) <= day) and (end == 'open' or day < _day(end)):
                relations.append(record)
        for relationship in RELATION_TYPES:
            edges: dict[tuple, list[tuple]] = {}
            for record in relations:
                if record['relationship'] == relationship:
                    edges.setdefault(_key(record['from']), []).append(_key(record['to']))
            if relationship in {'component_of', 'tranche_of', 'perimeter_within', 'alias_of'}:
                _acyclic(edges, relationship)
            if relationship in {'tranche_of', 'alias_of'}:
                _require(all(len(targets) == 1 for targets in edges.values()),
                         f'multiple active {relationship} targets')
            if relationship == 'alias_of':
                _require(not any(target in edges for targets in edges.values() for target in targets),
                         'active alias target is itself an alias')
        return deepcopy(relations)

    def frozen_frame(self, reference: dict[str, str]) -> list[dict]:
        """Resolve the frame's own freeze; later reviews cannot change its members."""
        key = _key(reference)
        _require(key[0] == 'frame' and key in self.records, 'unavailable frame reference')
        frame = self.records[key]
        _require(frame['population_coverage'] == 'reconstructed', 'unreconstructed historical population')
        _require(_time(frame['evidence_cutoff']) <= _time(self.evidence_cutoff), 'frame freeze is in the future')
        protocol = self.records[_key(frame['protocol'])]
        _require(_time(protocol['frozen_at']) <= _time(frame['evidence_cutoff']), 'protocol not frozen at cutoff')
        frozen = ContractView(self.records, frame['evidence_cutoff'], self.policy_version)
        members = [record for key, record in frozen._accepted.items()
                   if key[0] == 'frame_member' and record['frame'] == reference]
        units = [_key(record['unit']) for record in members]
        _require(len(units) == len(set(units)), 'multiple operative frame verdicts')
        return deepcopy(members)

    def closing_status(self) -> dict[str, str | None]:
        """Foundation has no certified coverage or account engine (ticket 0768)."""
        return {'reconstructed_closing': None, 'residual': None,
                'missing_reason': 'Account reconstruction and complete coverage are not implemented'}

    def to_dict(self) -> dict[str, Any]:
        return {'schema_version': SCHEMA_VERSION, 'evidence_cutoff': self.evidence_cutoff,
                'policy_version': self.policy_version,
                'records': deepcopy(list(self.records.values())),
                'accepted': [dict(record_kind=k, record_id=i) for k, i in self._accepted]}
