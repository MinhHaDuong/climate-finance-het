"""Build one offline, source-linked JSON handoff for the observatory."""

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from decimal import Decimal
from pathlib import Path

import yaml

from jetp._country_views_v2 import country_view, load_country_inputs
from jetp._ledger_headers import load_schema, read_table, table_files
from jetp._observatory_data import document_entry, historical_record

ROOT = Path(__file__).resolve().parents[2]
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


def country_data_v2(root, code, config, tables=None):
    """Serve reviewed referents without counting agreements as projects."""
    data = country_view(root / 'data/jetp', code, config['countries'][code],
                        tables=tables)
    metadata = data['country']
    if metadata.get('pledge_observation_id'):
        metadata.update(perimeter_headlines(root, metadata))
    data['editorial'] = editorial(root, code)
    data['stages'] = dict(Counter(row['finance_stage'] for row in data['projects']))
    data['technologies'] = dict(Counter(row['technology'] for row in data['projects']))
    return data


def perimeter_headlines(root, country_config):
    """Format reported money from cited perimeter observations, never YAML values."""
    schema = load_schema()
    rows, errors = read_table(root / 'data/jetp', 'observations', schema)
    if errors:
        raise ValueError(errors[0])
    by_id = {r['observation_id']: r for r in
             (dict(zip(schema.header('observations'), row)) for row in rows)}
    def indexed(table, key):
        table_rows, table_errors = read_table(root / 'data/jetp', table, schema)
        if table_errors:
            raise ValueError(table_errors[0])
        return {r[key]: r for r in
                (dict(zip(schema.header(table), row)) for row in table_rows)}

    lines = indexed('lines', 'line_id')
    documents = indexed('documents', 'document_id')
    retrieval_rows, retrieval_errors = read_table(root / 'data/jetp', 'retrievals', schema)
    if retrieval_errors:
        raise ValueError(retrieval_errors[0])
    retrievals = [dict(zip(schema.header('retrievals'), row)) for row in retrieval_rows]

    def cited(identity):
        row = by_id.get(identity)
        if (row is None or row['status'] != 'accepted'
                or row['subject_kind'] != 'perimeter' or row['measure'] != 'envelope'
                or row['value'] is None or not row['line_id']):
            raise ValueError(f'Headline needs an accepted cited perimeter envelope: {identity}')
        if any(other['supersedes'] == identity and other['status'] in
               ('accepted', 'rejected', 'withdrawn') for other in by_id.values()):
            raise ValueError(f'Headline observation has been superseded: {identity}')
        value = Decimal(row['value']) / Decimal('1000000000')
        symbol = {'USD': '$', 'EUR': '€'}.get(row['currency'])
        if symbol is None:
            raise ValueError(f'Headline currency needs a display format: {row["currency"]}')
        formatted = format(value, 'f')
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        label = f'{symbol}{formatted}bn'
        line = lines.get(row['line_id'])
        if line is None:
            raise ValueError(f'Headline line unavailable: {row["line_id"]}')
        document_ids = {r['document_id'] for r in retrievals if r['sha256'] == line['sha256']}
        if len(document_ids) != 1 or next(iter(document_ids)) not in documents:
            raise ValueError(f'Headline line has no unique document: {row["line_id"]}')
        document_id = next(iter(document_ids))
        document = documents[document_id]
        return label, {'observation_id': identity, 'perimeter_id': row['subject_id'],
                       'line_id': row['line_id'], 'currency': row['currency'],
                       'value': row['value'], 'locator': line['locator'],
                       'sha256': line['sha256'], 'document_id': document_id,
                       'document_title': document['title'], 'document_url': document['url']}

    pledge, pledge_citation = cited(country_config['pledge_observation_id'])
    result = {'pledge_label': pledge, 'pledge_citation': pledge_citation}
    if identity := country_config.get('headline_observation_id'):
        headline, citation = cited(identity)
        result['headline'] = ('≈' if country_config.get('headline_approximate') else '') + \
            f'{headline} {country_config["headline_qualifier"]}'
        result['headline_citation'] = citation
    return result


def comparison_data(root, config):
    """Build the closed-operation cohort from the ledger's frozen API snapshots."""
    schema = load_schema()

    def rows(table):
        found, errors = read_table(root / 'data/jetp', table, schema)
        if errors:
            raise ValueError(f'{table}: {errors[0]}')
        return [dict(zip(schema.header(table), row)) for row in found]

    documents = rows('documents')
    retrievals = {row['document_id']: row for row in rows('retrievals')
                  if row['document_id'].startswith('world-bank-projects-')}
    snapshots_by_hash = {row['sha256']: row for row in rows('snapshots')}
    members = {row['from_id'] for row in rows('relations')
               if row['from_kind'] == 'line' and row['relation'] == 'member_of'
               and row['to_kind'] == 'perimeter'
               and row['to_id'] == 'world-bank-pre-jetp-closed-energy'
               and row['status'] == 'accepted'}
    projects = []
    snapshots = {}
    for code, country in config['countries'].items():
        prefix = f"world-bank-projects-{country['iso2'].lower()}-"
        editions = [row['document_id'] for row in documents
                    if row['document_id'].startswith(prefix)]
        if not editions:
            raise ValueError(f'World Bank edition unavailable for {code}')
        document_id = max(editions)
        digest = retrievals[document_id]['sha256']
        storage = snapshots_by_hash[digest]['storage_path']
        source = (root / 'data/jetp/documents' / storage).resolve()
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f'World Bank snapshot digest mismatch: {document_id}')
        snapshot = json.loads(raw)
        snapshots[code] = {k: snapshot[k] for k in ('retrieved_on', 'pages', 'country_code', 'source_total')}
        snapshots[code]['source_updated_on'] = None
        for row in snapshot['records']:
            record = historical_record(row, code, country['signed_on'])
            if record:
                if f"{document_id}-{row['id']}" not in members:
                    raise ValueError(f"World Bank pool membership missing: {row['id']}")
                projects.append(record)
    return {'projects': sorted(projects, key=lambda row: row['approval'], reverse=True),
            'method': 'World Bank status Closed; approved before the country JETP announcement; at least one sector label contains energy, power or electric. All available approval years. Additional-financing operations are labelled separately. This is a descriptive pool, not a matched control group.',
            'date_note': 'Approval to reported closing date is an administrative financing window. Closed is not proof of physical completion. Only closed operations enter this view, so its distribution cannot estimate the speed of all projects.',
            'source': 'https://search.worldbank.org/api/v2/projects?format=json',
            'snapshots': snapshots}


def retrieval_registry(ledger_dir):
    """Read collected documents from the ledger's retrieval and snapshot tables.

    The Documents page covers the archived document store. API comparator
    snapshots live elsewhere, and local transcription records are separate.
    A retrieval's identifier ordinal restores order within a document.
    """
    schema = load_schema()

    def rows(table):
        found, errors = read_table(ledger_dir, table, schema)
        if errors:
            raise ValueError(f'{table}: {errors[0]}')
        columns = schema.header(table)
        return [{c: '' if v is None else v for c, v in zip(columns, row)} for row in found]

    countries = {d['document_id']: d['country'] for d in rows('documents')}
    snapshots = {s['sha256']: s for s in rows('snapshots')}

    def in_document_store(retrieval):
        if retrieval['collection_method'] == 'local-record':
            return False
        path = snapshots.get(retrieval['sha256'], {}).get('storage_path') or ''
        return not path or path.startswith('objects/')

    retrievals = sorted((r for r in rows('retrievals')
                         if in_document_store(r)), key=lambda r: (
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
            'collection_method': r['collection_method'],
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
    paths = []
    ledger = root / 'data/jetp'
    for name in ('projects', 'assets', 'agreements', 'coverage', 'documents',
                 'document_publishers', 'party_names', 'retrievals', 'snapshots',
                 'lines', 'line_referents', 'relations', 'observations',
                 'timings', 'perimeters'):
        files, errors = table_files(ledger, name)
        if errors or not files:
            raise ValueError(errors[0] if errors else f'{name}: no ledger files')
        paths.extend(path for path, _, _ in files)
    paths += sorted((root / 'data/jetp/ledger-snapshots/world-bank').glob('*.json'))
    paths += sorted((root / 'data/jetp/editorial/countries').glob('*.md'))
    paths += [root / 'config/jetp_observatory.yaml', root / 'data/jetp/documents.dvc',
              root / 'config/jetp-ledger.sql', Path(__file__),
              root / 'scripts/jetp/_country_views_v2.py',
              root / 'scripts/jetp/_observatory_data.py',
              root / 'scripts/jetp/_ledger_headers.py']
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    relative = [str(p.relative_to(root)) for p in paths]
    tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', '--', *relative],
                             cwd=root, capture_output=True, check=False).returncode == 0
    clean = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', *relative],
                           cwd=root, check=False).returncode == 0
    return {'edition': config['edition'], 'cutoff': config['cutoff'],
            'data_build': {
                'identity': 'ontology_v2_observatory_preview',
                'observation_cutoff': config['cutoff'],
                'relationship_to_release': 'canonical_data_build_precedes_release_extension',
            },
            'input_git_sha': revision if tracked and clean else None,
            'build_base_git_sha': revision,
            'input_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'release_status': 'Local preview; source snapshots have different observation dates',
            'facts_policy': 'No project-level money totals are computed from repeated events. National finance headlines are separately attributed reported totals. Programme/component records are not counts of unique assets.',
            'data_terms': 'Source attribution retained. Repository reuse licence applies only where applicable; source-document redistribution rights are not asserted.'}


def overview_v2(root, config, tables=None):
    """Count reviewed project and agreement referents separately."""
    tables = tables or load_country_inputs(root / 'data/jetp')
    countries = []
    all_sources = set()
    for code in config['countries']:
        data = country_data_v2(root, code, config, tables)
        all_sources.update(data['sources'])
        countries.append(dict(data['country'], named=data['project_count'],
                              agreement_count=data['agreement_count'],
                              stages=data['stages'], technologies=data['technologies'],
                              headline_source_record=data['sources'].get(
                                  data['country']['headline_source'])))
    return {'countries': countries, 'source_count': len(all_sources),
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
    if args.view == 'overview':
        result = overview_v2(ROOT, config)
    elif args.view == 'comparison':
        result = comparison_data(ROOT, config)
    elif args.view == 'coverage':
        result = coverage_data(ROOT)
    elif args.view == 'documents':
        result = documents_data(ROOT, {'manifest': retrieval_registry(ROOT / 'data/jetp')})
    elif args.view == 'editions':
        result = edition_history(ROOT)
    else:
        result = country_data_v2(ROOT, args.view, config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
