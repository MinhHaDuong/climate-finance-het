"""Byte and row inventories for recoverable observatory bundles."""

import csv
import hashlib
import io
import json
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import yaml

VIEWS = ('overview', 'comparison', 'documents', 'ZAF', 'IDN', 'VNM', 'SEN')
COUNTRIES = ('ZAF', 'IDN', 'VNM', 'SEN')
SITE = Path('deliverables/jetp-observatory')
# The archived document bytes are a local preview convenience; the public
# edition carries the registry and the origin URL only.
SITE_EXCLUDE = ('documents',)
EXTRA_INPUTS = ('config/jetp_observatory.yaml', 'scripts/jetp/build_observatory.py',
                'scripts/jetp/_observatory_data.py', 'scripts/jetp/_publication.py',
                'scripts/jetp/build_observatory_provenance.py')


def digest(data):
    """Identify exact archived bytes."""
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    """Read repository provenance without changing the checkout."""
    return subprocess.check_output(['git', *args], cwd=root)


def table_inventory(data):
    """Retain every row, duplicate and candidate identifier without deduplication."""
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
    rows = list(reader)
    headers = reader.fieldnames or []
    columns = [name for name in headers if name.endswith('_id')]
    encoded = [json.dumps(row, sort_keys=True) for row in rows]
    counts = Counter(encoded)
    keys = {name: [row[name] for row in rows] for name in columns}
    return {'headers': headers, 'row_count': len(rows), 'key_columns': columns,
            'row_keys': keys, 'row_locators': list(range(2, len(rows) + 2)),
            'duplicate_rows': [{'row': json.loads(row), 'count': count}
                               for row, count in sorted(counts.items()) if count > 1],
            'duplicate_keys': {name: {key: count for key, count in Counter(values).items()
                                      if count > 1} for name, values in keys.items()}}


def site_files(site):
    """Walk the preview tree, leaving locally staged document bytes behind."""
    for path in sorted(site.rglob('*')):
        if path.is_file() and path.relative_to(site).parts[0] not in SITE_EXCLUDE:
            yield path


def routes(payloads):
    """Enumerate the renderer's stable hash routes and every view download."""
    result = ['#overview', '#countries', '#projects', '#comparison', '#documents', '#methods']
    for view in COUNTRIES:
        country = json.loads(payloads[f'site/data/{view}.json'])
        result.extend((f'#country/{view}', f'#projects?country={view}', f'#comparison?country={view}'))
        result.extend('#project/' + quote(row['id'], safe='') for row in country['projects'])
    return {'routes': sorted(set(result)),
            'downloads': [f'data/{view}.json' for view in VIEWS]}


def _dvc_sources(root, source_root):
    """Read and authenticate the pinned directory index from the local cache."""
    pointer = root / 'data/jetp/documents.dvc'
    if not pointer.exists():
        return {}
    outputs = yaml.safe_load(pointer.read_text()).get('outs', [])
    output = next((row for row in outputs if row.get('path') == 'documents'), {})
    identity = output.get('md5', '')
    if not identity.endswith('.dir'):
        return {}
    cache = source_root / '.dvc/cache/files/md5'
    index = cache / identity[:2] / identity[2:]
    if not index.is_file():
        return {}
    data = index.read_bytes()
    if hashlib.md5(data).hexdigest() != identity.removesuffix('.dir'):
        raise ValueError('DVC directory index hash mismatch')
    result = {}
    for row in json.loads(data):
        md5 = row['md5']
        if len(md5) != 32 or any(c not in '0123456789abcdef' for c in md5):
            raise ValueError('Invalid DVC source object hash')
        relative = row['relpath']
        if relative in result:
            raise ValueError('Duplicate DVC source path')
        result[relative] = {'path': cache / md5[:2] / md5[2:], 'md5': md5,
                            'index_md5': identity, 'index_location': str(index)}
    return result


def resolve_within(base, relative):
    """Resolve `relative` under `base`; a path that would escape it stops the build."""
    resolved = (base / relative).resolve()
    if not resolved.is_relative_to(base):
        raise ValueError(f'Unsafe source path: {relative}')
    return resolved


def _source_record(row, source_root, cached):
    """Identify a checkout file or its pinned cache object without writing either."""
    item = {key: row.get(key, '') for key in ('source_id', 'status', 'sha256', 'storage_path')}
    item.update(verified=False, embedded=False)
    relative = Path(row.get('storage_path') or '.')
    base = (source_root / 'data/jetp/documents').resolve()
    source = resolve_within(base, relative)
    item['working_tree_available'] = source.is_file()
    item['location_kind'] = 'working_tree' if source.is_file() else 'unavailable'
    cache_entry = cached.get(relative.as_posix())
    if cache_entry:
        item.update(dvc_md5=cache_entry['md5'], dvc_index_md5=cache_entry['index_md5'],
                    dvc_index_location=cache_entry['index_location'])
        if not source.is_file() and cache_entry['path'].is_file():
            source = cache_entry['path']
            item['location_kind'] = 'dvc_cache'
    item['recovery_location'] = str(source)
    return item, source, relative


def source_inventory(root, source_root, payloads, include_sources):
    """Verify available document bytes; missing files remain explicit gaps."""
    manifest = root / 'data/jetp/manifest.csv'
    if not manifest.exists():
        return []
    cached = _dvc_sources(root, source_root)
    records = []
    for row in csv.DictReader(io.StringIO(manifest.read_text())):
        item, source, relative = _source_record(row, source_root, cached)
        if row.get('sha256') and source.is_file():
            data = source.read_bytes()
            if digest(data) != row['sha256']:
                raise ValueError(f'Source hash mismatch: {row["source_id"]}')
            if item.get('dvc_md5') and hashlib.md5(data).hexdigest() != item['dvc_md5']:
                raise ValueError(f'DVC source hash mismatch: {row["source_id"]}')
            item.update(verified=True, size_bytes=len(data))
            if include_sources:
                name = 'sources/' + relative.as_posix()
                payloads[name] = data
                item.update(embedded=True, archive_path=name)
        else:
            item['gap'] = 'Source bytes unavailable' if row.get('sha256') else 'No collected source hash'
        records.append(item)
    return records


def input_inventory(root, payloads):
    """Snapshot all tracked corpus inputs and untracked small registry files."""
    paths = set(git(root, 'ls-files', 'data/jetp').decode().splitlines())
    paths.update(str(p.relative_to(root)) for pattern in ('*.csv', '*.json', '*.md', '*.dvc')
                 for p in (root / 'data/jetp').rglob(pattern)
                 if 'documents' not in p.relative_to(root / 'data/jetp').parts)
    paths.update(EXTRA_INPUTS)
    tables = {}
    for name in sorted(paths):
        path = root / name
        if not path.is_file() or '/releases/' in name:
            continue
        data = path.read_bytes()
        payloads['inputs/' + name] = data
        if path.suffix == '.csv':
            tables[name] = table_inventory(data)
    return tables


def build_input_inventory(root, payloads):
    """Preserve historical exporter inputs separately from today's corpus."""
    provenance = json.loads(payloads['site/data/overview.json'])['provenance']
    revision = provenance.get('input_git_sha')
    report = {'recorded_input_git_sha': revision, 'files': {}}
    for name, expected in provenance.get('input_sha256', {}).items():
        current = payloads.get('inputs/' + name)
        historical = None
        if revision:
            try:
                historical = git(root, 'show', f'{revision}:{name}')
            except subprocess.CalledProcessError:
                pass
        data = historical if historical is not None and digest(historical) == expected else current
        verified = data is not None and digest(data) == expected
        report['files'][name] = {'expected_sha256': expected, 'verified': verified,
                                'current_matches': current is not None and digest(current) == expected,
                                'historical_matches': historical is not None and digest(historical) == expected}
        if verified:
            archive_path = 'inputs/' + name if data == current else 'build-inputs/' + name
            payloads[archive_path] = data
            report['files'][name]['archive_path'] = archive_path
    return report
