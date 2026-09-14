"""Freeze, compare and restore complete static bundles without publication."""

import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import yaml

from jetp._bundle_inventory import (
    SITE,
    VIEWS,
    build_input_inventory,
    digest,
    git,
    input_inventory,
    routes,
    source_inventory,
)


def _read_bundle(path):
    """Verify the entire package before any extraction or comparison."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive members')
        for name in names:
            member = Path(name)
            if member.is_absolute() or '..' in member.parts:
                raise ValueError('Unsafe archive path')
        manifest = json.loads(archive.read('manifest.json'))
        if set(names) != set(manifest['files']) | {'manifest.json'}:
            raise ValueError('Archive inventory mismatch')
        payloads = {name: archive.read(name) for name in manifest['files']}
    for name, data in payloads.items():
        if digest(data) != manifest['files'][name]['sha256']:
            raise ValueError(f'Archive hash mismatch: {name}')
    _validate_site(payloads)
    return manifest, payloads


def _validate_site(payloads):
    """Require the matching renderer and every JSON download."""
    for asset in ('index.html', 'app.js', 'styles.css'):
        if f'site/{asset}' not in payloads:
            raise ValueError(f'Missing rendering asset: {asset}')
    for view in VIEWS:
        json.loads(payloads[f'site/data/{view}.json'])
    routes(payloads)


def _archive_member(archive, name, data):
    """Use stable container metadata so identical captures are byte-identical."""
    member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    member.compress_type = zipfile.ZIP_BZIP2
    member.external_attr = 0o100644 << 16
    archive.writestr(member, data)


def _write_bundle(output, manifest, payloads):
    """Publish one fully written archive through an atomic rename."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest['files'] = {name: {'sha256': digest(data), 'size_bytes': len(data)}
                         for name, data in sorted(payloads.items())}
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        archive_path = Path(scratch) / 'bundle.zip'
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_BZIP2) as archive:
            for name, data in sorted(payloads.items()):
                _archive_member(archive, name, data)
            _archive_member(archive, 'manifest.json', json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        _read_bundle(archive_path)
        os.replace(archive_path, output)
    return manifest


def _capture(root, site, source_root, include_sources):
    """Collect bytes once, so the inventory describes exactly what is archived."""
    payloads = {'site/' + path.relative_to(site).as_posix(): path.read_bytes()
                for path in sorted(site.rglob('*')) if path.is_file()}
    _validate_site(payloads)
    tables = input_inventory(root, payloads)
    build_inputs = build_input_inventory(root, payloads)
    sources = source_inventory(root, source_root, payloads, include_sources)
    manifest = {'format_version': 1,
                'working_tree_status': git(root, 'status', '--porcelain', '--', 'data/jetp',
                                           str(SITE), 'config/jetp_observatory.yaml',
                                           'scripts/jetp').decode().splitlines(), 'captured_git_sha': git(root, 'rev-parse', 'HEAD').decode().strip(),
                'tables': tables, **routes(payloads), 'build_inputs': build_inputs,
                'sources': sources, 'source_bytes_embedded': include_sources,
                'source_recovery_complete': all(r['embedded'] for r in sources if r['sha256']),
                'zaf_payload': {'size_bytes': len(payloads['site/data/ZAF.json']),
                                'limit_bytes': 512000,
                                'within_limit': len(payloads['site/data/ZAF.json']) <= 512000}}
    return manifest, payloads


def _protect_output(root, output):
    """Reject destinations inside the accepted static site or canonical inputs."""
    output = Path(output).resolve()
    if output.is_relative_to((root / SITE).resolve()) or (
            output.is_relative_to((root / 'data/jetp').resolve())
            and not output.is_relative_to((root / 'data/jetp/releases').resolve())):
        raise ValueError('Bundle output must be separate from accepted site and canonical inputs')


def freeze_bundle(root, output, *, source_root=None, include_sources=False):
    """Freeze existing website bytes; never run an exporter or regenerate data."""
    root = Path(root).resolve()
    _protect_output(root, output)
    manifest, payloads = _capture(root, root / SITE, Path(source_root or root), include_sources)
    manifest['kind'] = 'baseline'
    return _write_bundle(output, manifest, payloads)


def _build_view(root, view, output):
    """Reuse existing pure exporter functions for one candidate handoff."""
    from jetp.build_observatory import (
        comparison_data,
        country_data,
        overview,
        read_inputs,
    )

    config = yaml.safe_load((root / 'config/jetp_observatory.yaml').read_text())
    tables = read_inputs(root)
    if view == 'overview':
        result = overview(root, config, tables)
    elif view == 'comparison':
        result = comparison_data(root, config)
    else:
        result = country_data(root, view, config, tables)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')


def build_candidate(root, output, *, accepted, builder=None, source_root=None, include_sources=False):
    """Build all six views in isolation; failures preserve both archive destinations."""
    root = Path(root).resolve()
    _protect_output(root, output)
    if Path(output).resolve() == Path(accepted).resolve():
        raise ValueError('Candidate must be separate from accepted bundle')
    _read_bundle(accepted)
    with tempfile.TemporaryDirectory() as scratch:
        site = Path(scratch) / 'site'
        shutil.copytree(root / SITE, site)
        for view in VIEWS:
            (builder or _build_view)(root, view, site / 'data' / f'{view}.json')
        manifest, payloads = _capture(root, site, Path(source_root or root), include_sources)
        manifest.update(kind='candidate', accepted_sha256=digest(Path(accepted).read_bytes()))
        return _write_bundle(output, manifest, payloads)


def restore_bundle(bundle, destination):
    """Restore only the static website, offline, into a new directory."""
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f'Restore destination already exists: {destination}')
    manifest, payloads = _read_bundle(bundle)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as scratch:
        site = Path(scratch) / 'site'
        site.mkdir()
        for name, data in payloads.items():
            if name.startswith('site/'):
                target = site / name.removeprefix('site/')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        # Refuse replacement even if a destination appeared during verification.
        if destination.exists():
            raise FileExistsError(destination)
        os.rename(site, destination)
    return manifest


def _changes(before, after, path):
    """Yield exact semantic paths, preserving meaningful array order."""
    if before == after:
        return
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(before.keys() | after.keys()):
            escaped = key.replace('~', '~0').replace('/', '~1')
            child = f'{path}/{escaped}'
            if key not in before or key not in after:
                yield {'path': child, 'before': before.get(key), 'after': after.get(key),
                       'operation': 'add' if key in after else 'remove'}
            else:
                yield from _changes(before[key], after[key], child)
    elif isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        for index, (old, new) in enumerate(zip(before, after, strict=True)):
            yield from _changes(old, new, f'{path}/{index}')
    else:
        yield {'path': path, 'before': before, 'after': after, 'operation': 'replace'}


def compare_bundles(accepted, candidate, *, intentional_paths=None):
    """Separate reviewed scientific differences from unexplained changes and metadata."""
    intentional_paths = intentional_paths or {}
    for evidence in intentional_paths.values():
        if not all(evidence.get(key) for key in ('source', 'reviewer', 'rationale')):
            raise ValueError('Intentional changes require source, reviewer and rationale')
    old_manifest, before = _read_bundle(accepted)
    new_manifest, after = _read_bundle(candidate)
    report = {'intentional_scientific': [], 'unexplained': [], 'metadata_only': [],
              'routes_added': sorted(set(new_manifest['routes']) - set(old_manifest['routes'])),
              'routes_removed': sorted(set(old_manifest['routes']) - set(new_manifest['routes']))}
    metadata = ('/provenance/input_git_sha', '/provenance/build_base_git_sha',
                '/provenance/input_sha256', '/provenance/release_status')
    for name in sorted(before.keys() | after.keys()):
        if not name.startswith('site/') or before.get(name) == after.get(name):
            continue
        if name.endswith('.json') and name in before and name in after:
            changes = _changes(json.loads(before[name]), json.loads(after[name]), name)
        else:
            changes = [{'path': name, 'before_sha256': digest(before[name]) if name in before else None,
                        'after_sha256': digest(after[name]) if name in after else None}]
        for change in changes:
            path = change['path']
            if any(path == 'site/data/overview.json' + field or
                   path.startswith('site/data/overview.json' + field + '/') for field in metadata):
                group = 'metadata_only'
            elif path in intentional_paths:
                change['evidence'] = intentional_paths[path]
                group = 'intentional_scientific'
            else:
                group = 'unexplained'
            report[group].append(change)
    return report
