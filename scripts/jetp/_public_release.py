"""Build and verify a self-contained public JETP release archive."""

import hashlib
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path

FORMAT_VERSION = 'jetp-public-release/1'
COUNTRIES = ('ZAF', 'IDN', 'VNM', 'SEN')
EDITION = re.compile(r'^\d{4}-\d{2}(?:-r[1-9]\d*)?$')
SITE = Path('deliverables/jetp-observatory')


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


def _descriptor(edition, input_git_sha, cutoff, reviewer, payloads):
    if not isinstance(edition, str) or not EDITION.fullmatch(edition):
        raise ValueError('edition must be YYYY-MM or YYYY-MM-rN')
    _required_date(cutoff, 'cutoff')
    if not isinstance(reviewer, str) or not reviewer:
        raise ValueError('reviewer is required')
    coverage = _coverage(payloads)
    payloads.update({'dictionary.md': _dictionary().encode(), 'TERMS.md': _terms().encode(),
                     'coverage.json': (json.dumps(coverage, indent=2, sort_keys=True) + '\n').encode()})
    files = [{'path': name, 'sha256': _digest(data), 'size_bytes': len(data)}
             for name, data in sorted(payloads.items())]
    return {
        'format_version': FORMAT_VERSION,
        'edition': edition,
        'release_state': 'prepared',
        'input_git_sha': input_git_sha,
        'cutoff': cutoff,
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
        'files': files,
    }


def build_release(root, output, *, edition, input_git_sha, cutoff, reviewer):
    """Write a deterministic offline archive from site bytes pinned at one commit."""
    output = Path(output)
    if os.path.lexists(output):
        raise FileExistsError(f'Release destination already exists: {output}')
    payloads = _site_payloads(root, input_git_sha)
    descriptor = _descriptor(edition, input_git_sha, cutoff, reviewer, payloads)
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
    actual = [{'path': name, 'sha256': _digest(data), 'size_bytes': len(data)}
              for name, data in sorted(payloads.items())]
    if descriptor.get('files') != actual:
        raise ValueError('Release file inventory mismatch')
    if descriptor.get('source_redistribution') != 'excluded' or any(name.startswith('sources/') for name in payloads):
        raise ValueError('Public release must exclude raw source documents')
    coverage = _coverage(payloads)
    if descriptor.get('coverage') != coverage or json.loads(payloads['coverage.json']) != coverage:
        raise ValueError('Release coverage mismatch')
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
