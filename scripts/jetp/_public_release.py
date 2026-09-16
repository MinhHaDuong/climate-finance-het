"""Build and verify a self-contained public JETP release archive."""

import hashlib
import json
import os
import re
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

FORMAT_VERSION = 'jetp-public-release/1'
COUNTRIES = ('ZAF', 'IDN', 'VNM', 'SEN')
EDITION = re.compile(r'^\d{4}-\d{2}(?:-r[1-9]\d*)?$')
SITE = Path('deliverables/jetp-observatory')
REVIEWED_STATUSES = {'reviewed_fact', 'pending_candidate'}


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _git(root, *args):
    import subprocess
    return subprocess.check_output(['git', *args], cwd=root)


def _required_date(value, name):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError(f'{name} must be an ISO date')


def _archive_member(archive, name, data):
    member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    member.compress_type = zipfile.ZIP_BZIP2
    member.external_attr = 0o100644 << 16
    archive.writestr(member, data)


def _dictionary():
    return '''# JETP public release dictionary\n\nThis package is a frozen descriptive release of four Just Energy Transition\nPartnership portfolios: South Africa (ZAF), Indonesia (IDN), Viet Nam (VNM)\nand Senegal (SEN). It preserves source-specific observations and gaps.\n\n## Identifiers and hierarchy\n\n`project_id` identifies a canonical registry record. A programme, a component\nand a financing tranche are different records or observations. They must not be\nadded as independent projects or financing totals. Viet Nam's unpublished\nportfolio identities are count slots, not invented project IDs.\n\n## Dates and stages\n\n`event_date` is distinct from a source publication date, retrieval date and this\nrelease cutoff. A register or report date is not silently treated as a signature\nor payment date. Financial stages (need, announced, memorandum, approved,\nsigned and disbursed) are observations, not additive flows. Implementation\nstates are a separate evidence layer.\n\n## Totals and currencies\n\nCountry headlines reproduce the named national source and retain its currency,\nstage, scope and date. They are **not additive** across countries or project\nevents, and they do not establish a common disbursement total. Every visible\nheadline links to a source record through `site/data/provenance.json`. Missing\npayments remain unavailable rather than zero. Strict JETP attribution and the\nextended IPG-energy perimeter remain separate.\n\n## Coverage\n\nThe country downloads list named records, source links and the review state at\nthe stated cutoff. A missing direct source, blocked retrieval, count slot or\nunresolved relationship is a recorded gap, not evidence of absence or delivery.\n'''


def _terms():
    return '''# Reuse and redistribution terms\n\nThe release package may be copied and analysed under the repository licence.\nKeep the release edition, input commit, source attribution and stated limits\nwith any reuse. Do not represent the package as a payment, investment or causal\neffect dataset.\n\nThis archive contains no raw source documents. Individual sources remain subject\nto their own terms; their URLs, hashes and locators are supplied for attribution\nand verification. No permission to redistribute source PDFs, websites or other\nupstream material is granted by this package.\n'''


def _coverage(payloads):
    result = {'countries': {}, 'gaps_policy': 'Recorded gaps are not zero values or negative findings.'}
    for code in COUNTRIES:
        country = json.loads(payloads[f'site/data/{code}.json'])
        result['countries'][code] = {
            'name': country['country']['name'],
            'named_records': len(country['projects']),
            'unpublished_identity_slots': country['undisclosed'],
            'headline_source': country['country']['headline_source'],
            'headline_stage': country['country']['stage_label'],
            'headline_date': country['country']['headline_date'],
        }
    overview = json.loads(payloads['site/data/overview.json'])
    result['curated_source_count'] = overview['source_count']
    result['historical_reference_count'] = overview['historical_count']
    return result


def _reviewed_evidence(records):
    """Keep reviewed source assertions visible without making them a ledger."""
    if not isinstance(records, list):
        raise ValueError('reviewed_evidence must be a list')
    normalized, ids = [], set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('reviewed evidence record must be an object')
        item = dict(record)
        for key in ('id', 'country', 'status', 'label', 'notes'):
            if not isinstance(item.get(key), str) or not item[key]:
                raise ValueError(f'reviewed evidence requires {key}')
        if item['id'] in ids:
            raise ValueError('reviewed evidence IDs must be unique')
        ids.add(item['id'])
        if item['country'] not in COUNTRIES or item['status'] not in REVIEWED_STATUSES:
            raise ValueError('unknown reviewed evidence country or status')
        evidence = item.get('evidence')
        if not isinstance(evidence, list) or not evidence:
            raise ValueError('reviewed evidence requires source pedigree')
        for proof in evidence:
            if not isinstance(proof, dict) or any(
                    not isinstance(proof.get(key), str) or not proof[key]
                    for key in ('source_id', 'sha256', 'locator')):
                raise ValueError('reviewed evidence proof requires source_id, sha256 and locator')
            if not re.fullmatch(r'[0-9a-f]{64}', proof['sha256']):
                raise ValueError('reviewed evidence proof requires a SHA-256')
        item['evidence'] = sorted(evidence, key=lambda proof: (proof['source_id'], proof['locator']))
        item['aggregation'] = 'non_aggregate'
        normalized.append(item)
    return {'format_version': 'jetp-reviewed-evidence/1',
            'records': sorted(normalized, key=lambda item: item['id']),
            'analytical_snapshot': {'status': 'not_deployed'}}


def _reviewed_evidence_summary(payload):
    return {'record_count': len(payload['records']),
            'by_status': dict(sorted(Counter(item['status'] for item in payload['records']).items())),
            'aggregation': 'record_level_non_aggregate',
            'analytical_snapshot': payload['analytical_snapshot']['status']}


def _data_build(payloads, release_cutoff):
    """Expose an older canonical data cutoff rather than silently relabelling it."""
    overview = json.loads(payloads['site/data/overview.json'])
    provenance = overview.get('provenance', {})
    data_cutoff = provenance.get('cutoff')
    if data_cutoff == release_cutoff:
        return None
    data_build = provenance.get('data_build')
    required = {'identity', 'observation_cutoff', 'relationship_to_release'}
    if not isinstance(data_build, dict) or required - data_build.keys():
        raise ValueError('release cutoff differs from overview; explicit data_build is required')
    if data_build['observation_cutoff'] != data_cutoff:
        raise ValueError('data_build cutoff must match overview provenance cutoff')
    return {key: data_build[key] for key in sorted(required)}


def _site_payloads(root, input_git_sha):
    root = Path(root)
    try:
        _git(root, 'cat-file', '-e', f'{input_git_sha}^{{commit}}')
    except Exception as exc:
        raise ValueError('input_git_sha must name an existing commit') from exc
    names = _git(root, 'ls-tree', '-r', '--name-only', input_git_sha, '--', str(SITE)).decode().splitlines()
    payloads = {}
    for name in names:
        if not name.startswith(str(SITE) + '/'):
            continue
        relative = Path(name).relative_to(SITE).as_posix()
        payloads['site/' + relative] = _git(root, 'show', f'{input_git_sha}:{name}')
    expected = {'site/index.html', 'site/app.js', 'site/styles.css',
                *(f'site/data/{view}.json' for view in ('overview', 'comparison', *COUNTRIES)),
                'site/data/provenance.json'}
    missing = expected - payloads.keys()
    if missing:
        raise ValueError(f'Input commit lacks public site files: {sorted(missing)}')
    return payloads


def _descriptor(edition, input_git_sha, cutoff, prepared_on, reviewer, payloads, *, rehearsal_of=None):
    if not isinstance(edition, str) or not EDITION.fullmatch(edition):
        raise ValueError('edition must be YYYY-MM or YYYY-MM-rN')
    _required_date(cutoff, 'cutoff')
    _required_date(prepared_on, 'prepared_on')
    if not isinstance(reviewer, str) or not reviewer:
        raise ValueError('reviewer is required')
    coverage = _coverage(payloads)
    payloads.update({'dictionary.md': _dictionary().encode(), 'TERMS.md': _terms().encode(),
                     'coverage.json': (json.dumps(coverage, indent=2, sort_keys=True) + '\n').encode()})
    files = [{'path': name, 'sha256': _digest(data), 'size_bytes': len(data)}
             for name, data in sorted(payloads.items())]
    descriptor = {
        'format_version': FORMAT_VERSION,
        'edition': edition,
        'release_state': 'prepared',
        'input_git_sha': input_git_sha,
        'observation_cutoff': cutoff,
        'release_prepared_date': prepared_on,
        'publication_date': None,
        'date_semantics': {'event_date': 'date of the observed event when reviewed',
                           'source_publication_date': 'date the source published',
                           'retrieval_date': 'date the source was retrieved',
                           'observation_cutoff': 'latest evidence admitted to this edition',
                           'release_prepared_date': 'date this package was prepared'},
        'reviewer': reviewer,
        'schema_version': 'jetp-contract/1',
        'aggregation_policy': {'reported_headlines': 'not_additive',
                               'programme_component_rule': 'do_not_sum_across_levels',
                               'financial_stage_rule': 'select_one_stage_per_claim',
                               'currency_rule': 'retain_reported_currency_no_cross_country_sum'},
        'currency_policy': {'reported_headlines': 'not_additive',
                            'conversion': 'none'},
        'source_redistribution': 'excluded',
        'coverage': coverage,
        'reviewed_evidence': _reviewed_evidence_summary(
            json.loads(payloads['site/data/reviewed-evidence.json'])),
        'files': files,
    }
    data_build = _data_build(payloads, cutoff)
    if data_build is not None:
        descriptor['data_build'] = data_build
    if rehearsal_of is not None:
        if not isinstance(rehearsal_of, str) or not EDITION.fullmatch(rehearsal_of):
            raise ValueError('rehearsal_of must name an edition')
        descriptor.update(rehearsal_of=rehearsal_of, no_scientific_change=True)
    return descriptor


def build_release(root, output, *, edition, input_git_sha, cutoff, prepared_on, reviewer,
                  rehearsal_of=None, reviewed_evidence=None):
    """Write a deterministic offline archive from site bytes pinned at one commit."""
    output = Path(output)
    if os.path.lexists(output):
        raise FileExistsError(f'Release destination already exists: {output}')
    payloads = _site_payloads(root, input_git_sha)
    if reviewed_evidence is None:
        existing = payloads.get('site/data/reviewed-evidence.json')
        reviewed_evidence = json.loads(existing)['records'] if existing else []
    evidence_payload = _reviewed_evidence(reviewed_evidence)
    payloads['site/data/reviewed-evidence.json'] = (
        json.dumps(evidence_payload, indent=2, sort_keys=True) + '\n').encode()
    descriptor = _descriptor(edition, input_git_sha, cutoff, prepared_on, reviewer, payloads,
                             rehearsal_of=rehearsal_of)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        staged = Path(scratch) / 'release.zip'
        with zipfile.ZipFile(staged, 'w', compression=zipfile.ZIP_BZIP2) as archive:
            for name, data in sorted(payloads.items()):
                _archive_member(archive, name, data)
            _archive_member(archive, 'release.json', json.dumps(descriptor, indent=2, sort_keys=True).encode() + b'\n')
        read_release(staged)
        os.link(staged, output)
    return descriptor


def read_release(path):
    """Verify descriptor, inventory and safe member names before use."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or 'release.json' not in names:
            raise ValueError('Invalid release member inventory')
        if any(Path(name).is_absolute() or '..' in Path(name).parts for name in names):
            raise ValueError('Unsafe release path')
        descriptor = json.loads(archive.read('release.json'))
        payloads = {name: archive.read(name) for name in names if name != 'release.json'}
    if descriptor.get('format_version') != FORMAT_VERSION:
        raise ValueError('Unknown public release format')
    if 'rehearsal_of' in descriptor:
        if (not isinstance(descriptor['rehearsal_of'], str)
                or not EDITION.fullmatch(descriptor['rehearsal_of'])
                or descriptor.get('no_scientific_change') is not True):
            raise ValueError('Invalid rehearsal relationship')
    actual = [{'path': name, 'sha256': _digest(data), 'size_bytes': len(data)}
              for name, data in sorted(payloads.items())]
    if descriptor.get('files') != actual:
        raise ValueError('Release file inventory mismatch')
    if descriptor.get('source_redistribution') != 'excluded' or any(name.startswith('sources/') for name in payloads):
        raise ValueError('Public release must exclude raw source documents')
    coverage = _coverage(payloads)
    if descriptor.get('coverage') != coverage or json.loads(payloads['coverage.json']) != coverage:
        raise ValueError('Release coverage mismatch')
    data_build = _data_build(payloads, descriptor.get('observation_cutoff'))
    if descriptor.get('data_build') != data_build:
        raise ValueError('Release data-build provenance mismatch')
    evidence = json.loads(payloads.get('site/data/reviewed-evidence.json', b'{}'))
    if evidence:
        if evidence != _reviewed_evidence(evidence.get('records')):
            raise ValueError('Invalid reviewed evidence payload')
        if descriptor.get('reviewed_evidence') != _reviewed_evidence_summary(evidence):
            raise ValueError('Reviewed evidence summary mismatch')
    if not {'dictionary.md', 'TERMS.md', 'site/data/provenance.json'} <= payloads.keys():
        raise ValueError('Release documentation missing')
    return descriptor, payloads


def restore_release(path, destination):
    """Restore the public static site without DVC, Git or network access."""
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    _, payloads = read_release(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as scratch:
        site = Path(scratch) / 'site'
        for name, data in payloads.items():
            if name.startswith('site/'):
                target = site / name.removeprefix('site/')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        os.rename(site, destination)
