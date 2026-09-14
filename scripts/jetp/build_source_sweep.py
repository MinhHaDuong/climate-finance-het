"""Build a bounded source-watch review handoff beside the authoritative MVP."""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

import yaml
from script_io_args import parse_io_args, validate_io

from jetp._contracts import _require, _time
from jetp._observatory_bundle import _protect_output, _protect_replacement
from jetp._source_crosswalk import _identity, migrate_sources
from jetp._source_watch import (
    SCHEMA_VERSION,
    change_report,
    freeze_sweep,
    link_acquisition,
    record_check,
    record_discovery,
    run_document_check,
    source_revision,
    summarize,
)

FIELDS = {'schema_version', 'admission_status', 'publication_action', 'handoff_ticket',
          'inputs', 'plan', 'checks', 'discoveries', 'acquisitions', 'summary',
          'archive_verifications', 'claim_review_queue', 'changes', 'change_report', 'source_revisions'}


def validate_candidate(candidate: dict) -> None:
    """Recognize a complete prior artifact; marker-only lookalikes are protected."""
    _require(isinstance(candidate, dict) and candidate.keys() == FIELDS, 'incomplete sweep candidate')
    _require(candidate['schema_version'] == SCHEMA_VERSION
             and candidate['admission_status'] == 'unadmitted_candidate'
             and candidate['publication_action'] == 'none' and candidate['handoff_ticket'] == '0728',
             'invalid candidate boundary')
    _require(isinstance(candidate['inputs'], dict) and bool(candidate['inputs']), 'input hashes required')
    for row in candidate['inputs'].values():
        _require(isinstance(row, dict) and isinstance(row.get('sha256'), str) and len(row['sha256']) == 64,
                 'input hash required')
    for key in ('checks', 'discoveries', 'acquisitions', 'archive_verifications', 'claim_review_queue', 'changes', 'source_revisions'):
        _require(isinstance(candidate[key], list) and all(isinstance(row, dict) for row in candidate[key]),
                 'invalid record collection')
    _require(candidate['summary'] == summarize(candidate['plan'], candidate['checks']), 'invalid sweep summary')
    plan, checks = candidate['plan'], candidate['checks']
    sources = candidate['source_revisions']
    _require(all(target['source'] in sources for target in plan['targets']), 'pinned source revisions missing')
    discoveries, acquisitions = [], []
    for row in candidate['discoveries']:
        discoveries = record_discovery(plan, checks, discoveries, row, sources)
    for row in candidate['acquisitions']:
        acquisitions = link_acquisition(plan, checks, discoveries, acquisitions, row, sources)
    _require(candidate['change_report'] == change_report(plan, checks, discoveries,
             [row['original_claim'] for row in candidate['claim_review_queue']], candidate['changes']),
             'invalid change report')
    for row in candidate['archive_verifications']:
        _require({'source_id', 'acquisition_id', 'document_sha256', 'storage_path', 'byte_status',
                  'check_scope', 'publisher_coverage_advanced'} <= row.keys(), 'incomplete archive verification')
        _require(row['check_scope'] == 'archived_material' and row['publisher_coverage_advanced'] is False,
                 'archive verification cannot advance publisher coverage')
    for row in candidate['claim_review_queue']:
        _require({'claim_id', 'source_id', 'original_claim', 'principal_source_id', 'principal_publication_date',
                  'source_publication_date', 'date_relation', 'origin_assessment', 'review_state',
                  'factual_promotion'} <= row.keys(), 'incomplete claim handoff')
        _require(row['review_state'] == 'pending_review' and row['factual_promotion'] is False,
                 'claim handoff cannot promote evidence')


def _recognized(output: Path) -> bool:
    if not output.is_file():
        return False
    try:
        validate_candidate(json.loads(output.read_text()))
        return True
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def build_sweep(root: Path, policy_path: Path) -> dict:
    """Verify actual saved material and freeze pending publisher-watch proposals.

    Historical manifest attempts retain their original IDs and retrieval times.
    Current local byte checks are not new acquisitions or live source coverage.
    """
    policy = yaml.safe_load(policy_path.read_text())
    crosswalk = migrate_sources(root)
    selected = {row['source_id']: row for row in crosswalk['sources']}
    sources, watches, deferrals = [], [], {}
    principal = {}
    for proposed in policy['watches']:
        prior = selected[proposed['source_id']]
        metadata = {**prior['metadata'], 'source_kind': proposed['source_kind']}
        revision = source_revision(metadata, policy['recorded_at'])
        revision['legacy_source_revision_id'] = prior['source_revision_id']
        sources.append(revision)
        watch = {**policy['defaults'], **proposed, 'source_revision_id': revision['source_revision_id'],
                 'recorded_at': policy['recorded_at'], 'review_state': 'pending_review',
                 'review_reference': None, 'route': metadata['url']}
        watch['watch_revision_id'] = _identity('watch-revision', watch)
        watches.append(watch)
        deferrals[watch['watch_id']] = 'Publisher refresh deferred until this proposed watch policy is reviewed; archive verification only.'
        principal[metadata['country']] = metadata
    policy_hash = hashlib.sha256(policy_path.read_bytes()).hexdigest()
    plan = freeze_sweep(sources, watches, sweep_id=policy['sweep_id'], created_at=policy['recorded_at'],
                        owner=policy['owner'], purpose=policy['purpose'],
                        registry_revision=crosswalk['inputs']['data/jetp/sources.csv']['sha256'],
                        configuration_revision=policy_hash, budget=policy['budget'],
                        deferrals=deferrals, allow_pending=True)
    verifications = [{key: row[key] for key in ('source_id', 'acquisition_id', 'document_sha256',
                                              'storage_path', 'byte_status', 'byte_reason', 'retrieved_at')}
                     | {'check_scope': 'archived_material', 'publisher_coverage_advanced': False,
                        'verified_at': policy['recorded_at']}
                     for row in crosswalk['acquisitions'] if row['source_id'] in {s['source_id'] for s in sources}]
    claims = crosswalk['inputs']['data/jetp/source-claims.csv']['rows']
    queue = []
    for claim in claims:
        anchor = principal.get(claim['country'])
        source = selected.get(claim['source_id'])
        if not anchor or not source:
            continue
        published = source['metadata'].get('published_date') or None
        baseline = anchor.get('published_date') or None
        relation = ('unknown' if not published or not baseline else 'after_principal' if published > baseline
                    else 'before_principal' if published < baseline else 'same_publication_date')
        queue.append({'claim_id': claim['claim_id'], 'source_id': claim['source_id'],
                      'original_claim': claim, 'principal_source_id': anchor['source_id'],
                      'principal_publication_date': baseline, 'source_publication_date': published,
                      'date_relation': relation, 'origin_assessment': {'intelligence_role': 'unknown',
                       'upstream_status': 'unknown', 'independence': 'unknown'},
                      'review_state': 'pending_review', 'factual_promotion': False})
    result = {'schema_version': SCHEMA_VERSION, 'admission_status': 'unadmitted_candidate',
              'publication_action': 'none', 'handoff_ticket': '0728',
              'inputs': {name: {'sha256': row['sha256'], 'row_count': row['row_count']}
                         for name, row in crosswalk['inputs'].items()},
              'plan': plan, 'checks': [], 'discoveries': [], 'acquisitions': [],
              'summary': summarize(plan, []), 'archive_verifications': verifications,
              'claim_review_queue': queue, 'changes': [], 'change_report': change_report(plan, [], [], claims, []),
              'source_revisions': sources}
    result['inputs'][policy_path.relative_to(root).as_posix()] = {'sha256': policy_hash}
    validate_candidate(result)
    return result


def _atomic_candidate(output: Path, result: dict) -> None:
    validate_candidate(result)
    payload = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)


def execute_sweep(root: Path, output: Path, *, candidate: dict, attempt_id: str,
                  storage_root: Path, session=None, clock=None) -> dict:
    """Persist the frozen plan first, then each attempt before proceeding.

    Replaying an attempt ID resumes missing targets without fetching completed
    ones again. A fresh attempt ID retains previous successes and failures.
    Object storage must be a separate candidate directory, never the MVP tree.
    """
    root, output = Path(root).resolve(), Path(output)
    _protect_replacement(output, _recognized(output))
    output = output.resolve()
    _protect_output(root, output)
    _require(bool(attempt_id), 'attempt ID required')
    storage_root = Path(storage_root).resolve()
    _require(not storage_root.is_relative_to(root), 'live bytes require separate candidate storage')
    validate_candidate(candidate)
    result = json.loads(json.dumps(candidate))
    if output.exists():
        prior = json.loads(output.read_text())
        _require(prior['plan'] == result['plan'] and prior['inputs'] == result['inputs'], 'cannot replace another sweep')
        result = prior
    _atomic_candidate(output, result)
    sources = [target['source'] for target in result['plan']['targets']]
    for target in result['plan']['targets']:
        if target['deferral_reason']:
            continue
        watch = target['watch']
        identity = _identity('check', [result['plan']['sweep_id'], attempt_id, watch['watch_revision_id']])
        if any(row['check_id'] == identity for row in result['checks']):
            continue
        prior_checks = [row for row in result['checks'] if row['watch_revision_id'] == watch['watch_revision_id']]
        spent = sum((_time(row['ended_at']) - _time(row['started_at'])).total_seconds() for row in prior_checks)
        _require(len(prior_checks) < watch['budget']['calls'] and spent < watch['budget']['seconds'],
                 'frozen target budget exhausted; create a reviewed supplemental sweep')
        previous = next((row['manifest_row'] for row in reversed(result['acquisitions'])
                         if row['source_revision_id'] == watch['source_revision_id'] and row['document_sha256']), None)
        check, acquisition = run_document_check(result['plan'], watch['watch_revision_id'],
            check_id=identity, storage_root=storage_root, previous=previous, session=session, clock=clock,
            remaining_seconds=watch['budget']['seconds'] - spent)
        result['checks'] = record_check(result['plan'], result['checks'], check)
        result['acquisitions'] = link_acquisition(result['plan'], result['checks'], result['discoveries'],
                                                result['acquisitions'], acquisition, sources)
        if check['outcome'] == 'changed':
            result['changes'].append({'check_id': identity, 'source_id': watch['source_id'],
                                      'kind': 'byte_change', 'document_sha256': acquisition['document_sha256']})
        result['summary'] = summarize(result['plan'], result['checks'])
        result['change_report'] = change_report(result['plan'], result['checks'], result['discoveries'],
            [row['original_claim'] for row in result['claim_review_queue']], result['changes'])
        _atomic_candidate(output, result)
    return result


def write_sweep(root: Path, output: Path, *, policy_path: Path) -> dict:
    """Validate all inputs and complete output before atomic candidate replacement."""
    root, output, policy_path = Path(root).resolve(), Path(output), Path(policy_path).resolve()
    _protect_replacement(output, _recognized(output))
    output = output.resolve()
    _require(output.suffix == '.json', 'sweep candidate output must end in .json')
    releases = root / 'data/jetp/releases'
    protected = [policy_path, *releases.glob('*')]
    # A recognized candidate may replace itself; every other release member is protected.
    protected = [path for path in protected if path.resolve() != output or path == policy_path]
    _protect_output(root, output, inputs=protected)
    result = build_sweep(root, policy_path)
    if output.exists():
        prior = json.loads(output.read_text())
        _require(prior['plan'] == result['plan'], 'changed metadata requires a new immutable sweep destination')
    _atomic_candidate(output, result)
    return result


def main():
    """Build the bounded archived-material handoff; this command never fetches URLs."""
    io_args, extra = parse_io_args()
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--policy', type=Path)
    mode.add_argument('--execute-candidate', type=Path)
    parser.add_argument('--attempt-id')
    parser.add_argument('--storage-root', type=Path)
    args = parser.parse_args(extra)
    if not io_args.input or len(io_args.input) != 1:
        parser.error('requires --input CHECKOUT_ROOT')
    validate_io(output=io_args.output, inputs=io_args.input)
    if args.execute_candidate:
        if not args.attempt_id or not args.storage_root:
            parser.error('execution requires --attempt-id and --storage-root')
        execute_sweep(Path(io_args.input[0]), Path(io_args.output),
                      candidate=json.loads(args.execute_candidate.read_text()),
                      attempt_id=args.attempt_id, storage_root=args.storage_root)
    else:
        write_sweep(Path(io_args.input[0]), Path(io_args.output), policy_path=args.policy)


if __name__ == '__main__':
    main()
