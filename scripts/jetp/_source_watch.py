"""Immutable sweep candidates around the existing acquisition and evidence contracts.

All views are derived from frozen snapshots and append-only records. This module
has no publication operation and never admits evidence or edits the legacy registry.
"""

from copy import deepcopy
from datetime import timedelta

from jetp._contracts import _require, _time, validate_evidence_tuple
from jetp._source_crosswalk import _identity
from jetp.schemas import COUNTRIES

SCHEMA_VERSION = 'source-sweep/1'
SUCCESS = {'new_candidate', 'changed', 'checked_no_change'}
OUTCOMES = SUCCESS | {'blocked', 'error', 'partial'}


def _append(records: list[dict], row: dict, key: str) -> list[dict]:
    """Replay an attempt idempotently; reject reusing its ID for different facts."""
    previous = next((item for item in records if item[key] == row[key]), None)
    _require(previous is None or previous == row, f'immutable {key} collision')
    return deepcopy(records if previous is not None else [*records, row])


def source_revision(metadata: dict, recorded_at: str, *, supersedes: str | None = None) -> dict:
    """Record present metadata without inventing earlier admission or knowledge."""
    _time(recorded_at)
    _require(bool(metadata.get('source_id')), 'source identity required')
    row = {'source_id': metadata['source_id'], 'metadata': deepcopy(metadata),
           'source_kind': metadata.get('source_kind', 'unknown'),
           'triage_state': metadata.get('triage_state', 'unknown'),
           'recorded_at': recorded_at, 'supersedes': supersedes,
           'admission_status': 'unadmitted_candidate'}
    row['source_revision_id'] = _identity('source-revision', row)
    return row


def registry_at(revisions: list[dict], cutoff: str) -> list[dict]:
    """Select a metadata snapshot by recording time; later changes stay invisible."""
    limit = _time(cutoff)
    seen, selected = {}, {}
    for row in sorted(revisions, key=lambda item: (_time(item['recorded_at']), item['source_revision_id'])):
        identity = row['source_revision_id']
        _require(identity not in seen or seen[identity] == row, 'immutable source revision collision')
        seen[identity] = row
        if _time(row['recorded_at']) > limit:
            continue
        prior = selected.get(row['source_id'])
        if prior and prior != row:
            _require(row.get('supersedes') == prior['source_revision_id'], 'metadata revision needs prior revision')
        selected[row['source_id']] = deepcopy(row)
    return list(selected.values())


def validate_watch(watch: dict, *, allow_pending: bool = False) -> None:
    """Require an explicit bounded scheduling policy, not inferred publisher cadence."""
    required = {'watch_id', 'watch_revision_id', 'source_id', 'source_revision_id',
                'recorded_at', 'review_state', 'review_reference', 'owner', 'purpose',
                'active', 'priority', 'expected_publication_cadence', 'check_interval_days',
                'retry_days', 'max_retry_days', 'method', 'route', 'access_limitations',
                'scope', 'acceptance_criteria', 'budget'}
    _require(required <= watch.keys(), 'incomplete watch policy')
    _time(watch['recorded_at'])
    _require(watch['review_state'] == 'reviewed' and bool(watch['review_reference'])
             or allow_pending and watch['review_state'] == 'pending_review', 'watch must be reviewed')
    _require(all(isinstance(watch[key], str) and watch[key] for key in
                 ('watch_id', 'watch_revision_id', 'source_id', 'source_revision_id',
                  'owner', 'purpose', 'method', 'route', 'acceptance_criteria')), 'empty watch field')
    _require(isinstance(watch['active'], bool), 'active must be boolean')
    _require(all(type(watch[key]) is int and watch[key] > 0 for key in
                 ('priority', 'check_interval_days', 'retry_days', 'max_retry_days')), 'positive UTC day intervals required')
    _require(watch['retry_days'] <= watch['max_retry_days'], 'retry bounds inverted')
    scope = watch['scope']
    _require(isinstance(scope, dict) and scope.keys() == {'countries', 'sectors', 'languages', 'topics'}, 'invalid scope')
    _require(all(isinstance(values, list) and all(isinstance(value, str) and value for value in values)
                 for values in scope.values()), 'scope must contain string arrays')
    _require(set(scope['countries']) <= set(COUNTRIES), 'unknown country scope')
    _require(isinstance(watch['access_limitations'], list), 'access limitations must be a list')
    _require(watch['budget'].keys() == {'calls', 'seconds'} and all(
        type(value) is int and value > 0 for value in watch['budget'].values()), 'invalid watch budget')
    window = watch.get('expected_publication_window')
    if window:
        _require(_time(window['start']) <= _time(window['end']), 'publication window inverted')
        _require(type(window['interval_days']) is int and window['interval_days'] > 0,
                 'publication window needs explicit acceleration interval')


def freeze_sweep(sources: list[dict], watches: list[dict], *, sweep_id: str,
                 created_at: str, owner: str, purpose: str, registry_revision: str,
                 configuration_revision: str, budget: dict, deferrals: dict | None = None,
                 allow_pending: bool = False, previous_sweeps: list[dict] | None = None) -> dict:
    """Freeze selected revisions and deferrals before acquisition starts."""
    instant = _time(created_at)
    _require(all((sweep_id, owner, purpose, registry_revision, configuration_revision)), 'incomplete plan identity')
    selected = {row['source_revision_id']: row for row in sources}
    _require(len(selected) == len(sources), 'duplicate source revisions')
    deferrals = deferrals or {}
    prior_checks = []
    for prior in previous_sweeps or []:
        summarize(prior['plan'], prior['checks'])
        _require(_time(prior['plan']['created_at']) < instant, 'prior sweep must precede new plan')
        for check in prior['checks']:
            _require(_time(check['recorded_at']) <= instant, 'future check cannot enter plan')
            prior_checks = _append(prior_checks, check, 'check_id')
    targets, ids = [], set()
    for watch in watches:
        validate_watch(watch, allow_pending=allow_pending)
        _require(watch['watch_id'] not in ids, 'duplicate watch target')
        ids.add(watch['watch_id'])
        source = selected.get(watch['source_revision_id'])
        _require(source is not None and source['source_id'] == watch['source_id'], 'watch source revision mismatch')
        _require(_time(source['recorded_at']) <= instant and _time(watch['recorded_at']) <= instant,
                 'future metadata cannot enter frozen sweep')
        reason = deferrals.get(watch['watch_id'])
        _require(watch['active'] or bool(reason), 'inactive watch must be deferred')
        _require(source['triage_state'] in {'accepted_for_use', 'context_only'}
                 or bool(reason), 'source needs reviewed triage or explicit deferral')
        _require(watch['review_state'] == 'reviewed' or bool(reason), 'pending watch cannot execute')
        targets.append({'watch': deepcopy(watch), 'source': deepcopy(source),
                        'initial_due_at': created_at, 'deferral_reason': reason,
                        'prior_checks': [row for row in prior_checks if row['watch_id'] == watch['watch_id']]})
    _require(set(deferrals) <= ids and all(deferrals.values()), 'unknown or empty deferral')
    _require(budget.keys() == {'calls', 'seconds'} and all(type(v) is int and v > 0 for v in budget.values()), 'invalid sweep budget')
    for key in budget:
        _require(sum(t['watch']['budget'][key] for t in targets if not t['deferral_reason']) <= budget[key],
                 'selected targets exceed frozen budget')
    plan = dict(sweep_id=sweep_id, created_at=created_at, owner=owner, purpose=purpose,
                registry_revision=registry_revision, configuration_revision=configuration_revision,
                budget=deepcopy(budget), targets=targets)
    plan['plan_digest'] = _identity('plan', plan)
    due = {row['watch_id']: row['next_check_at'] for row in summarize(plan, [])['targets']}
    for target in plan['targets']:
        target['initial_due_at'] = due[target['watch']['watch_id']]
    plan['plan_digest'] = _identity('plan', {key: value for key, value in plan.items() if key != 'plan_digest'})
    return plan


def _targets(plan: dict) -> dict:
    _require(plan.keys() == {'sweep_id', 'created_at', 'owner', 'purpose', 'registry_revision',
                             'configuration_revision', 'budget', 'targets', 'plan_digest'}, 'incomplete frozen plan')
    _require(isinstance(plan['targets'], list) and bool(plan['targets']), 'nonempty targets required')
    for target in plan['targets']:
        _require(target.keys() == {'watch', 'source', 'initial_due_at', 'deferral_reason', 'prior_checks'},
                 'incomplete frozen target')
        validate_watch(target['watch'], allow_pending=True)
        _require(target['watch']['review_state'] == 'reviewed' or bool(target['deferral_reason']),
                 'pending watch cannot execute')
        _require(target['source']['source_id'] == target['watch']['source_id'] and
                 target['source']['source_revision_id'] == target['watch']['source_revision_id'], 'target revision mismatch')
    body = {key: value for key, value in plan.items() if key != 'plan_digest'}
    _require(_identity('plan', body) == plan['plan_digest'], 'frozen plan was modified')
    return {target['watch']['watch_revision_id']: target for target in plan['targets']}


def record_check(plan: dict, checks: list[dict], check: dict) -> list[dict]:
    """Retain each scoped attempt; failures cannot replace successful history."""
    targets = _targets(plan)
    required = {'check_id', 'watch_revision_id', 'started_at', 'ended_at', 'recorded_at',
                'method', 'route', 'outcome', 'coverage_complete', 'coverage_limit', 'error', 'retry_reason'}
    _require(required <= check.keys(), 'incomplete check')
    target = targets.get(check['watch_revision_id'])
    _require(target is not None and not target['deferral_reason'], 'check is outside executable frozen plan')
    watch = target['watch']
    _require(check['method'] == watch['method'] and check['route'] == watch['route'], 'check route differs from frozen policy')
    _require(_time(plan['created_at']) <= _time(check['started_at']) <= _time(check['ended_at'])
             <= _time(check['recorded_at']), 'invalid check timing')
    _require(check['outcome'] in OUTCOMES and bool(check['coverage_limit']), 'invalid outcome or scope')
    _require(type(check['coverage_complete']) is bool, 'coverage must be explicit boolean')
    _require(not check['coverage_complete'] or check['outcome'] in SUCCESS, 'failed check cannot cover source')
    _require(check['outcome'] in SUCCESS or bool(check['error'] or check['retry_reason']), 'failed check needs reason')
    row = deepcopy(check)
    row['sweep_id'] = plan['sweep_id']
    row['watch_id'] = watch['watch_id']
    _require(check.get('sweep_id', plan['sweep_id']) == plan['sweep_id'], 'check sweep mismatch')
    _require(check.get('watch_id', watch['watch_id']) == watch['watch_id'], 'check watch mismatch')
    return _append(checks, row, 'check_id')


def summarize(plan: dict, checks: list[dict], *, cutoff: str | None = None) -> dict:
    """Derive UTC interval/retry scheduling, scoped success, and target accounting."""
    _targets(plan)
    validated = []
    for check in checks:
        validated = record_check(plan, validated, check)
    limit = _time(cutoff) if cutoff else None
    rows = []
    for target in plan['targets']:
        watch = target['watch']
        own = [row for row in validated if row['watch_revision_id'] == watch['watch_revision_id']]
        history = sorted((row for row in [*target['prior_checks'], *own]
                          if limit is None or _time(row['recorded_at']) <= limit),
                         key=lambda row: (_time(row['ended_at']), row['check_id']))
        success = [row for row in history if row['coverage_complete'] and row['outcome'] in SUCCESS
                   and row.get('check_scope', 'publisher_route') == 'publisher_route']
        changed = [row for row in success if row['outcome'] in {'changed', 'new_candidate'}]
        streak = 0
        for row in reversed(history):
            if row in success:
                break
            streak += 1
        last = history[-1] if history else None
        latest_own = next((row for row in reversed(history) if row in own), None)
        interval = watch['check_interval_days'] if streak == 0 else min(
            watch['max_retry_days'], watch['retry_days'] * 2 ** min(streak - 1, 20))
        anchor = last['ended_at'] if last else target['initial_due_at']
        window = watch.get('expected_publication_window')
        if window and not streak and _time(window['start']) <= _time(anchor) <= _time(window['end']):
            interval = min(interval, window['interval_days'])
        next_check = (_time(anchor) + timedelta(days=interval)).isoformat().replace('+00:00', 'Z') if last else anchor
        rows.append({'watch_id': watch['watch_id'], 'watch_revision_id': watch['watch_revision_id'],
                     'status': 'deferred' if target['deferral_reason'] else 'completed' if latest_own and latest_own in success
                     else 'partial_or_failed' if latest_own else 'missing',
                     'deferral_reason': target['deferral_reason'], 'check_ids': [row['check_id'] for row in history],
                     'last_attempt_at': last['started_at'] if last else None,
                     'last_successful_check_at': success[-1]['ended_at'] if success else None,
                     'last_changed_at': changed[-1]['ended_at'] if changed else None,
                     'failure_streak': streak, 'next_check_at': next_check})
    return {'targets': rows, 'complete': all(row['status'] != 'missing' for row in rows),
            'publication_action': 'none', 'evidence_action': 'preserve'}


def record_discovery(plan: dict, checks: list[dict], discoveries: list[dict], discovery: dict,
                     sources: list[dict]) -> list[dict]:
    """Keep independent sightings linked to the curated source identity, never URL identity."""
    summarize(plan, checks)
    check = next((row for row in checks if row['check_id'] == discovery['check_id']), None)
    _require(check is not None, 'discovery check not found')
    source = next((row for row in sources if row['source_revision_id'] == discovery['source_revision_id']), None)
    _require(source is not None and source['source_id'] == discovery['source_id'], 'discovery source revision mismatch')
    _require(bool(discovery.get('locator')) and bool(discovery.get('discovery_id')), 'discovery identity and locator required')
    _require(_time(discovery['recorded_at']) >= _time(check['ended_at']), 'discovery predates check')
    return _append(discoveries, discovery, 'discovery_id')


def link_acquisition(plan: dict, checks: list[dict], discoveries: list[dict], acquisitions: list[dict],
                     acquisition: dict, sources: list[dict]) -> list[dict]:
    """Pin each idempotent attempt to the consulted revision and check role."""
    check = next((row for row in checks if row['check_id'] == acquisition['check_id']), None)
    _require(check is not None, 'acquisition check not found')
    target = _targets(plan)[check['watch_revision_id']]
    revisions = {row['source_revision_id']: row for row in sources}
    source = revisions.get(acquisition['source_revision_id'])
    _require(source is not None and source['source_id'] == acquisition['source_id'], 'acquisition source revision mismatch')
    if acquisition['check_role'] == 'target':
        _require(acquisition['source_revision_id'] == target['source']['source_revision_id'], 'target acquisition differs from watch')
    else:
        _require(acquisition['check_role'] == 'discovered_document' and source['source_kind'] == 'document',
                 'invalid acquisition check role')
        _require(any(row['check_id'] == check['check_id'] and row['source_revision_id'] == acquisition['source_revision_id']
                     for row in discoveries), 'discovered document needs check discovery link')
    _require(bool(acquisition.get('acquisition_id')) and bool(acquisition.get('requested_url'))
             and bool(acquisition.get('final_url')), 'acquisition identity and routes required')
    _require(_time(check['started_at']) <= _time(acquisition['retrieved_at']) <= _time(check['ended_at']), 'acquisition outside check')
    if acquisition['check_role'] == 'target':
        _require(acquisition['requested_url'] == check['route'], 'acquisition requested route mismatch')
    digest = acquisition.get('document_sha256')
    _require(digest is None or len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'invalid material hash')
    _require(not digest or acquisition['outcome'] in {'collected', 'not_modified'}, 'failed attempt cannot support bytes')
    return _append(acquisitions, acquisition, 'acquisition_id')


def assess_origin(evidence: dict, *, intelligence_role: str = 'unknown', rationale: str = '',
                  upstream_status: str = 'unknown', citation: str | None = None,
                  dependencies: list[dict] | None = None, evidence_index: dict | None = None) -> dict:
    """Claim-specific origin is unknown until reviewed; citations are not acquired IDs."""
    _require(intelligence_role in {'primary', 'secondary', 'mixed', 'unknown'}, 'invalid intelligence role')
    _require(upstream_status in {'linked', 'cited_not_acquired', 'unknown', 'not_applicable'}, 'invalid upstream status')
    _require(intelligence_role == 'unknown' or bool(rationale), 'origin assessment needs rationale')
    dependencies = dependencies or []
    if upstream_status == 'cited_not_acquired':
        _require(bool(citation) and not dependencies, 'unacquired citation cannot invent a dependency')
    if upstream_status == 'linked':
        _require(bool(dependencies) and bool(evidence_index), 'linked origin needs acquired evidence dependencies')
    for dependency in dependencies:
        _require(dependency['downstream_evidence_id'] == evidence['evidence_id']
                 and dependency['relation'] in {'quotes', 'reproduces', 'derived_from', 'translation_of'}
                 and dependency['review_state'] == 'reviewed' and bool(dependency['rationale']), 'invalid reviewed dependency')
        for identity in (dependency['downstream_evidence_id'], dependency['upstream_evidence_id']):
            item = (evidence_index or {}).get(identity)
            _require(item is not None, 'dependency endpoint missing')
            validate_evidence_tuple(**item['tuple_arguments'])
    return {'evidence_id': evidence['evidence_id'], 'intelligence_role': intelligence_role,
            'origin_rationale': rationale, 'upstream_status': upstream_status,
            'upstream_citation': citation, 'dependency_ids': [row['dependency_id'] for row in dependencies],
            'review_state': 'pending_review', 'independence': 'unknown'}


def change_report(plan: dict, checks: list[dict], discoveries: list[dict], claims: list[dict],
                  changes: list[dict]) -> dict:
    """Queue late reports, corrections and editorial impacts without updating claims."""
    summary = summarize(plan, checks)
    targets = _targets(plan)
    queue = []
    by_check = {row['check_id']: row for row in checks}
    for change in changes:
        check = by_check.get(change['check_id'])
        _require(check is not None, 'change check missing')
        sources = {targets[check['watch_revision_id']]['source']['source_id']}
        sources.update(row['source_id'] for row in discoveries if row['check_id'] == check['check_id'])
        _require(change['source_id'] in sources, 'change source was not checked or discovered')
        _require(change['kind'] in {'new_candidate', 'byte_change', 'late_report', 'correction', 'editorial_impact'}, 'invalid change kind')
        _require(change['kind'] == 'editorial_impact' or check['outcome'] in {'changed', 'new_candidate', 'partial'},
                 'failed or unchanged check cannot assert a discovered change')
        affected = [deepcopy(claim) for claim in claims if claim['source_id'] == change['source_id']]
        queue.append({**deepcopy(change), 'affected_claims': affected,
                      'review_state': 'pending_review', 'factual_promotion': False,
                      'origin_assessments': [{'claim_id': claim['claim_id'], 'evidence_id': None,
                          'intelligence_role': 'unknown', 'upstream_status': 'unknown',
                          'independence': 'unknown', 'review_state': 'pending_review'} for claim in affected]})
    return {'summary': summary, 'queue': queue, 'handoff_ticket': '0728',
            'publication_action': 'none', 'admission_status': 'unadmitted_candidate'}


def run_document_check(plan: dict, watch_revision_id: str, *, check_id: str,
                       storage_root, previous: dict | None = None, session=None,
                       clock=None, max_bytes: int = 16 * 1024 * 1024,
                       remaining_seconds: float | None = None) -> tuple[dict, dict]:
    """Execute one frozen HTTP target using the existing harvester's byte pipeline.

    The caller persists returned records in its candidate ledger. Attempt IDs are
    allocated before dispatch; retries use a new ID. Discovery pages remain scoped
    page checks, never automatic acquisitions of their linked documents.
    """
    import hashlib
    import time
    from datetime import datetime, timezone
    from pathlib import Path

    import requests

    from jetp.corpus_harvest_documents import _harvest_one

    target = _targets(plan).get(watch_revision_id)
    _require(target is not None and not target['deferral_reason'], 'target cannot execute')
    watch, source = target['watch'], target['source']
    validate_watch(watch)
    _require(watch['method'] == 'http_get', 'unsupported acquisition adapter')
    metadata = deepcopy(source['metadata'])
    metadata['url'] = watch['route']
    metadata['source_id'] = source['source_id']
    _require(previous is None or previous['source_id'] == source['source_id'], 'previous material source mismatch')
    now = clock or (lambda: datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
    started = now()
    deadline = time.monotonic() + min(watch['budget']['seconds'], remaining_seconds
                                    if remaining_seconds is not None else watch['budget']['seconds'])
    http = session or requests.Session()

    class BoundedSession:
        """One request with redirects/retries disabled: no hidden budget expansion."""

        def get(self, url, **kwargs):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise requests.Timeout('frozen time budget exhausted')
            kwargs.update(timeout=remaining, allow_redirects=False)
            response = http.get(url, **kwargs)
            original = response.iter_content

            def bounded_content(*args, **options):
                for chunk in original(*args, **options):
                    if time.monotonic() > deadline:
                        raise requests.Timeout('frozen stream time budget exhausted')
                    yield chunk

            response.iter_content = bounded_content
            return response

    try:
        material = _harvest_one(metadata, previous, Path(storage_root), started,
                                BoundedSession(), max_bytes)
    finally:
        if session is None:
            http.close()
    ended = now()
    if material['sha256']:
        stored = Path(storage_root) / material['storage_path']
        if not stored.is_file() or hashlib.sha256(stored.read_bytes()).hexdigest() != material['sha256']:
            material.update(status='invalid_content', error='saved material hash mismatch or unavailable',
                            sha256='', storage_path='', size_bytes='')
    success = material['status'] in {'collected', 'not_modified'}
    changed = success and (previous is None or previous['sha256'] != material['sha256'])
    outcome = ('changed' if changed else 'checked_no_change') if success else (
        'blocked' if material['status'] == 'blocked' else 'error')
    check = {'check_id': check_id, 'watch_revision_id': watch_revision_id,
             'started_at': started, 'ended_at': ended, 'recorded_at': ended,
             'method': watch['method'], 'route': watch['route'], 'outcome': outcome,
             'coverage_complete': success, 'coverage_limit': watch['acceptance_criteria'],
             'check_scope': 'publisher_route', 'error': material['error'],
             'retry_reason': '' if success else 'retry under frozen UTC policy'}
    check = record_check(plan, [], check)[0]
    acquisition = {'acquisition_id': _identity('acquisition', [plan['sweep_id'], check_id, 1]),
                   'check_id': check_id, 'check_role': 'target',
                   'source_id': source['source_id'], 'source_revision_id': source['source_revision_id'],
                   'retrieved_at': started, 'recorded_at': ended, 'outcome': material['status'],
                   'document_sha256': material['sha256'] or None,
                   'requested_url': watch['route'], 'final_url': material['final_url'] or watch['route'],
                   'manifest_row': material}
    link_acquisition(plan, [check], [], [], acquisition, [target['source']])
    return check, acquisition
