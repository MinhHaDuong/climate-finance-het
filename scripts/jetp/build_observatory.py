"""Build one offline, source-linked JSON handoff for the observatory."""

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

import yaml

from jetp._ledger_headers import load_schema, read_table
from jetp._observatory_data import (
    document_entry,
    historical_record,
    public_event,
    timeline,
)

ROOT = Path(__file__).resolve().parents[2]
LEGACY_PROJECTS = Path('data/jetp/migration/0875-projects-legacy.csv')
TABLES = ('projects', 'events', 'implementation-events', 'sources', 'source-claims',
          'project-source-links', 'project-coverage', 'manifest', 'event-timing')
STAGES = ('Signed', 'Approved', 'Registered financing', 'Mou', 'Announced', 'Need')


def read_inputs(root):
    """Load the named small registries without touching DVC or the network."""
    tables = {}
    for name in TABLES:
        path = (root / LEGACY_PROJECTS
                if name == 'projects' else root / 'data/jetp' / f'{name}.csv')
        with path.open() as stream:
            tables[name] = list(csv.DictReader(stream))
    timing = unique_rows(tables['event-timing'], 'event_id')
    ids = {r['event_id'] for r in tables['events']} | {r['implementation_event_id'] for r in tables['implementation-events']}
    if any(r['event_id'] not in ids for r in timing):
        raise ValueError('Timing registry references an unknown event')
    tables['event-timing'] = timing
    return tables


def unique_rows(rows, key):
    """Reject conflicting duplicate keys rather than silently overwriting evidence."""
    result = {}
    for row in rows:
        identity = row[key]
        if identity in result and result[identity] != row:
            raise ValueError(f'Conflicting {key}: {identity}')
        result[identity] = row
    return list(result.values())


def source_map(tables):
    """Join source identity to collection outcomes, retaining blocked sources."""
    sources = {}
    attempts = {r['source_id']: r for r in tables['manifest']}
    for row in tables['sources']:
        attempt = attempts.get(row['source_id'], {})
        sources[row['source_id']] = {
            'id': row['source_id'], 'title': row['title'], 'url': row['url'],
            'publisher': row.get('publisher', ''), 'date': row.get('published_date', ''),
            'retrieved': attempt.get('retrieved_at', ''),
            'collection': attempt.get('status', 'Not collected'),
            'sha256': attempt.get('sha256', ''),
        }
    return sources


def project_data(row, tables):
    """Expose project observations without summing currencies or repeated stages.

    The fact carries no copy of its ledger rows: they are served once, in
    ``observations/<CODE>.json`` (ticket 0838), and the renderer filters that
    view on ``project_id`` for the fold-out.  Ticket 0839 copied them here as
    ``evidence``; the copy put the ZAF view 280 kB over the publication cap
    that ``build_zaf_positions`` enforces, and even the lightest per-row
    reference list, about 42 kB for the ZAF view, would still cross it
    (ticket 0855).
    """
    pid = row['project_id']
    timings = {r['event_id']: r for r in tables.get('event-timing', [])}
    sources = source_map(tables)

    def export_event(r):
        eid = r.get('event_id', r.get('implementation_event_id'))
        return public_event(r, timings.get(eid), sources.get(r['source_id']))

    financial = [export_event(r) for r in unique_rows(tables['events'], 'event_id') if r['project_id'] == pid]
    physical = [export_event(r) for r in tables['implementation-events'] if r['project_id'] == pid]
    claims = [r for r in tables['source-claims'] if pid in r.get('matched_project_ids', '').split(';')]
    links = [r for r in tables['project-source-links'] if r['project_id'] == pid]
    coverage = next((r for r in tables['project-coverage'] if r['project_id'] == pid), {})
    source_ids = {r['source_id'] for r in financial + physical + claims + links}
    source_ids.update(coverage.get('source_ids', '').split(';'))
    stages = {e['status'] for e in financial}
    return {
        'id': pid, 'country': row['country'], 'name': row['canonical_name'],
        'technology': row.get('technology') or 'Not specified',
        'location': row.get('location') or 'Not specified',
        'operator': row.get('operator') or 'Not specified', 'notes': row.get('notes', ''),
        'coverage': coverage.get('review_status', 'Not assessed'),
        'coverage_note': coverage.get('notes', ''),
        'finance_stage': next((s for s in STAGES if s in stages), 'Not documented'),
        'funders': sorted({e['funder'] for e in financial if e['funder']}),
        'events': timeline(financial + physical),
        'claims': [{k: r[k] for k in ('claim_id', 'claim_summary', 'source_id', 'section', 'match_status', 'matched_project_ids', 'notes')} for r in claims],
        'source_links': links,
        'sources': sorted(source_ids - {''}),
    }


def editorial(root, code):
    """Load reviewed Markdown context for a country, if present."""
    path = root / 'data/jetp/editorial/countries' / f'{code}.md'
    if not path.exists():
        return ''
    text = path.read_text()
    if text.startswith('---\n'):
        _, header, body = text.split('---', 2)
        if yaml.safe_load(header).get('editorial_status') != 'reviewed':
            return ''
        return body.strip()
    return ''


def country_data(root, code, config, tables):
    """Build a country package with separate named records and disclosure slots."""
    rows = [r for r in unique_rows(tables['projects'], 'project_id') if r['country'] == code]
    slots = [r for r in rows if r['verification_status'] == 'official_count_slot']
    named = [r for r in rows if r not in slots]
    projects = [project_data(r, tables) for r in named]
    sources = source_map(tables)
    needed = {sid for p in projects for sid in p['sources']}
    country_config = config['countries'][code]
    needed.update(
        source_id
        for source_id in (
            country_config.get('headline_source'),
            country_config.get('latest_news_source'),
        )
        if source_id
    )
    missing = needed - sources.keys() - {''}
    if missing:
        raise ValueError(f'Unknown source references: {missing}')
    metadata = dict(country_config, code=code)
    return {'country': metadata, 'projects': projects,
            'undisclosed': len(slots), 'record_count': len(rows),
            'sources': {sid: sources[sid] for sid in sorted(needed) if sid},
            'editorial': editorial(root, code),
            'stages': dict(Counter(p['finance_stage'] for p in projects)),
            'technologies': dict(Counter(p['technology'] for p in projects))}


def comparison_data(root, config):
    """Build the descriptive closed-operation cohort from frozen API projections."""
    projects = []
    snapshots = {}
    for code, country in config['countries'].items():
        source = root / 'data/jetp/comparison' / f"{country['iso2']}.json"
        snapshot = json.loads(source.read_text())
        snapshots[code] = {k: snapshot[k] for k in ('retrieved_on', 'pages', 'country_code', 'source_total')}
        snapshots[code]['source_updated_on'] = None
        for row in snapshot['records']:
            record = historical_record(row, code, country['signed_on'])
            if record:
                projects.append(record)
    return {'projects': sorted(projects, key=lambda row: row['approval'], reverse=True),
            'method': 'World Bank status Closed; approved before the country JETP announcement; at least one sector label contains energy, power or electric. All available approval years. Additional-financing operations are labelled separately. This is a descriptive pool, not a matched control group.',
            'date_note': 'Approval to reported closing date is an administrative financing window. Closed is not proof of physical completion. Only closed operations enter this view, so its distribution cannot estimate the speed of all projects.',
            'source': 'https://search.worldbank.org/api/v2/projects?format=json',
            'snapshots': snapshots}


def retrieval_registry(ledger_dir):
    """The collection registry read from the evidence layer (ticket 0872).

    A compatibility reader: it joins ``retrievals`` to ``documents`` and
    ``snapshots`` and returns the rows ``manifest.csv`` held, column for
    column and as strings, so the Documents view is built from the new tables
    without changing a byte. A retrieval's ordinal, the ``<n>`` of its
    ``<document_id>:<n>`` identifier, restores registry order within a
    document. Retired with the legacy readers (ticket 0878).
    """
    schema = load_schema()

    def rows(table):
        found, errors = read_table(ledger_dir, table, schema)
        if errors:
            raise ValueError(f'{table}: {errors[0]}')
        columns = schema.header(table)
        return [{c: '' if v is None else v for c, v in zip(columns, row)} for row in found]

    # Migration step 3 adds local pilot transcription documents. This reader
    # reconstructs the old manifest exactly until ticket 0878 retires it.
    legacy_sources = Path(ledger_dir) / 'sources.csv'
    legacy_ids = None
    if legacy_sources.is_file():
        with legacy_sources.open(encoding='utf-8', newline='') as handle:
            legacy_ids = {row['source_id'] for row in csv.DictReader(handle)}
    countries = {d['document_id']: d['country'] for d in rows('documents')}
    snapshots = {s['sha256']: s for s in rows('snapshots')}
    retrievals = sorted((r for r in rows('retrievals')
                         if legacy_ids is None or r['document_id'] in legacy_ids), key=lambda r: (
        r['document_id'], int(r['retrieval_id'].rsplit(':', 1)[1])))
    registry = []
    for r in retrievals:
        snapshot = snapshots.get(r['sha256'], {})
        registry.append({
            'source_id': r['document_id'], 'country': countries[r['document_id']],
            'retrieved_at': r['retrieved_at'], 'status': r['status'],
            'http_status': r['http_status'], 'content_type': r['content_type'],
            'etag': r['etag'], 'last_modified': r['last_modified'], 'sha256': r['sha256'],
            'size_bytes': snapshot.get('size_bytes', ''),
            'storage_path': snapshot.get('storage_path', ''),
            'final_url': r['final_url'], 'error': r['error'],
        })
    return registry


def documents_data(root, tables):
    """List every collection attempt, marking availability from the snapshot on disk.

    One table, one key: the view is the collection registry and nothing
    derived from other tables.  What each document yielded and which facts
    rely on it is a join the Documents page makes at read time on the views
    that already serve those rows — ``m1a/<CODE>.json``,
    ``observations/<CODE>.json``, the country views and
    ``reviewed-evidence.json`` — filtered on ``source_id`` (ticket 0858).
    Ticket 0839 wrote that join here as ``by_source_id``: 874 kB copied out
    of tables served beside it, loaded on every route, growing with every
    collection, and refused by the pre-commit's 512 000 byte ceiling on the
    machine where the hooks run.
    """
    rows = sorted(tables['manifest'], key=lambda row: row['source_id'])
    snapshot = (Path(root) / 'data/jetp/documents').resolve()
    available = set()
    for row in rows:
        relative = row.get('storage_path') or ''
        if not relative:
            continue
        # A registry path that escapes the snapshot must stop the build rather
        # than become a link out of the site, as _source_record already does.
        archived = (snapshot / relative).resolve()
        if not archived.is_relative_to(snapshot):
            raise ValueError(f'Unsafe source path: {relative}')
        if archived.is_file():
            available.add(relative)
    # A source identifier is not a row key: 21 of them carry several collection
    # attempts (ticket 0853). The key is the identifier plus the attempt's
    # ordinal among that identifier's rows, in registry order — not the
    # fingerprint, which two attempts of vnm-rmp-2023 share, and not the
    # registry line, which no reader can check. ``id`` stays the identifier,
    # because it is what an inventory row resolves by (index_documents); it is
    # named first only so a reader of the JSON meets it before the key.
    attempts = Counter()
    entries = []
    for row in rows:
        entry = document_entry(row, available)
        attempts[entry['id']] += 1
        entries.append({'id': entry['id'], 'row_key': f"{entry['id']}:{attempts[entry['id']]}", **entry})
    return {'documents': entries}


def edition_history(root):
    from jetp._monthly_editions import release_history
    return release_history(root / 'data/jetp/releases')


def coverage_data(root):
    """Serve the ledger coverage table without reviving either legacy reader."""
    schema = load_schema()
    rows, errors = read_table(root / 'data/jetp', 'coverage', schema)
    if errors:
        raise ValueError(errors[0])
    return {'coverage': [dict(zip(schema.header('coverage'), row)) for row in rows]}


def provenance(root, config):
    """Hash every input and record the code checkout; make file bytes authoritative."""
    paths = [(root / LEGACY_PROJECTS
              if name == 'projects' else root / 'data/jetp' / f'{name}.csv')
             for name in TABLES]
    paths += sorted((root / 'data/jetp/comparison').glob('*.json'))
    paths += sorted((root / 'data/jetp/editorial/countries').glob('*.md'))
    paths += [root / 'config/jetp_observatory.yaml', root / 'data/jetp/documents.dvc',
              Path(__file__), root / 'scripts/jetp/_observatory_data.py',
              root / 'scripts/jetp/build_observations.py',
              root / 'scripts/jetp/_m1a_document_links.py']
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    relative = [str(p.relative_to(root)) for p in paths]
    tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', '--', *relative],
                             cwd=root, capture_output=True, check=False).returncode == 0
    clean = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', *relative],
                           cwd=root, check=False).returncode == 0
    return {'edition': config['edition'], 'cutoff': config['cutoff'],
            'data_build': {
                'identity': 'canonical_observatory_preview',
                'observation_cutoff': config['cutoff'],
                'relationship_to_release': 'canonical_data_build_precedes_release_extension',
            },
            'input_git_sha': revision if tracked and clean else None,
            'build_base_git_sha': revision,
            'input_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'release_status': 'Local preview; source snapshots have different observation dates',
            'facts_policy': 'No project-level money totals are computed from repeated events. National finance headlines are separately attributed reported totals. Programme/component records are not counts of unique assets.',
            'data_terms': 'Source attribution retained. Repository reuse licence applies only where applicable; source-document redistribution rights are not asserted.'}


def overview(root, config, tables):
    """Combine country-level coverage and reported headlines without pooling finance."""
    countries = []
    for code in config['countries']:
        data = country_data(root, code, config, tables)
        countries.append(dict(data['country'], named=len(data['projects']), undisclosed=data['undisclosed'],
                              stages=data['stages'], technologies=data['technologies'],
                              headline_source_record=data['sources'].get(data['country']['headline_source'])))
    return {'countries': countries, 'source_count': len(tables['sources']),
            'historical_count': len(comparison_data(root, config)['projects']),
            'provenance': provenance(root, config)}


def main():
    """Write one requested JSON view deterministically."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--view', choices=['overview', 'comparison', 'coverage', 'documents', 'editions',
                                           'ZAF', 'IDN', 'VNM', 'SEN'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load((ROOT / 'config/jetp_observatory.yaml').read_text())
    # Only the overview and the country views read the legacy registries.
    if args.view == 'overview':
        result = overview(ROOT, config, read_inputs(ROOT))
    elif args.view == 'comparison':
        result = comparison_data(ROOT, config)
    elif args.view == 'coverage':
        result = coverage_data(ROOT)
    elif args.view == 'documents':
        result = documents_data(ROOT, {'manifest': retrieval_registry(ROOT / 'data/jetp')})
    elif args.view == 'editions':
        result = edition_history(ROOT)
    else:
        result = country_data(ROOT, args.view, config, read_inputs(ROOT))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
