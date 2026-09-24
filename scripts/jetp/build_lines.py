"""Migrate the remaining legacy assertions into ledger lines (ticket 0874).

Each rule is named and versioned in its line notes. The local Viet Nam pilot
spreadsheets are frozen as byte-addressed snapshots because their source
documents have not yet entered the document store. Their rows identify the
original source and hash; they never assert that the external bytes were
retrieved by this ledger. Missing source snapshots stay in the pending file.
"""

import argparse
import csv
import hashlib
import json
import logging
import re
from collections import defaultdict
from pathlib import Path

from jetp._ledger_headers import LEDGER_DIR, load_schema, read_table, write_table

RECORDED_AT = '2026-09-24'
LOCAL_TABLES = ('vnm-pilot-manifest', 'vnm-pilot-observations')
GENERATED_METHODS = ('pilot_manifest', 'pilot_observation', 'idn_portfolio',
                     'source_claim', 'legacy_link')
PENDING_HEADER = ('kind', 'old_id', 'source_id', 'reason', 'old_project_id',
                  'relationship', 'review_status', 'locator')
log = logging.getLogger(__name__)


def read_csv(path):
    with Path(path).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def ledger_rows(ledger_dir, table, schema):
    rows, errors = read_table(ledger_dir, table, schema)
    if errors:
        raise ValueError('; '.join(errors))
    return [dict(zip(schema.header(table), row)) for row in rows]


def local_snapshot(ledger_dir, stem):
    """A git-tracked, content-addressed copy of a local pilot table."""
    source = Path(ledger_dir) / f'{stem}.csv'
    content = source.read_bytes()
    sha = hashlib.sha256(content).hexdigest()
    target = Path(ledger_dir) / 'ledger-snapshots' / f'{sha}.csv'
    target.parent.mkdir(exist_ok=True)
    if target.exists() and target.read_bytes() != content:
        raise ValueError(f'snapshot bytes changed: {target}')
    target.write_bytes(content)
    return sha, f'../ledger-snapshots/{sha}.csv', len(content)


def _line(line_id, country, sha, locator, ordinal, label, classification,
          method, notes='', **extra):
    return dict(line_id=line_id, country=country, sha256=sha, locator=locator,
                ordinal=ordinal, label=label, classification=classification,
                recorded_at=RECORDED_AT,
                notes=f'method={method}; version=1' + (f'; {notes}' if notes else ''),
                **extra)


def _classification(claim):
    text = claim['claim_summary'].lower()
    if any(word in text for word in ('not published', 'no project', 'none identified',
                                     'none of', 'not available', 'no finance')):
        return 'absence'
    # A match to one legacy project does not turn a portfolio count or total
    # into a named-item assertion (Growth Gateway is a concrete example).
    if re.match(r'^(?:pipeline:\s*)?\d+\s+(?:[\w-]+\s+){0,3}(?:smmes|firms|projects|programmes|grants)\b',
                text) and not re.search(r'\b(?:usd|eur|zar|gbp|fcfa)\b|\bR\d',
                                       claim['claim_summary']):
        return 'count'
    if 'investment need' in text and re.search(r'\bR\d|\b(?:usd|eur|zar|gbp|fcfa)\b',
                                                claim['claim_summary'], re.I):
        return 'envelope'
    if re.search(r'\b\d+\s+(?:projects?|programmes?|grants?|plants?)\b', text) and not re.search(
            r'\b(?:usd|eur|zar|gbp|fcfa|billion|million|bn|mn)\b', text):
        return 'count'
    if re.search(r'\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+'
                 r'(?:[\w-]+\s+){0,3}(?:grants?|municipalities|schools|firms|smmes)\b',
                 text) and not re.search(r'\b(?:usd|eur|zar|gbp|fcfa|billion|million|bn|mn)\b', text):
        return 'count'
    if (claim['claim_id'].endswith('aggregate') or
            re.search(r'\b(totalling|mobilised|pledge)\b', text)) and re.search(
            r'\b(?:usd|eur|zar|gbp|fcfa|billion|million|bn|mn)\b', text):
        return 'envelope'
    matched_ids = [item for item in claim['matched_project_ids'].split(';') if item]
    if matched_ids:
        return 'named_item' if len(matched_ids) == 1 else 'heading'
    return 'heading'


def _pilot_classification(row):
    """Type the assertion, using its portfolio role and stated total."""
    operation = row['operation'].lower()
    has_amount = row['amount_original'].isdigit()
    if 'absence' in operation or row['legacy_status'] == 'non décaissé':
        return 'absence'
    if row['project_count'] and not has_amount:
        return 'count'
    if has_amount and (row['portfolio_role'] or re.search(
            r'enveloppe|\btotal\b|agrégée|combinée|cumulé|cumulés|\bencours\b|'
            r'\bpart (?:publique|privée|ipg|gfanz)\b', operation)):
        return 'envelope'
    return 'named_item'


def _unique_locator(sha, locator, taken, suffix):
    locator = locator.strip() or suffix
    if (sha, locator) in taken:
        locator = f'{locator}; {suffix}'
    if (sha, locator) in taken:
        raise ValueError(f'duplicate place in snapshot {sha}: {locator}')
    taken.add((sha, locator))
    return locator


def _precise_locator(locator):
    text = locator.strip()
    if not text:
        return False
    return not re.search(
        r'\bwhole\b|\bproject narrative\b|^Related programme or geographic lead$'
        r'|^project profile$|^.* announcement$', text, re.I)


def _shortest_locator(links):
    return min((row for row in links if _precise_locator(row['locator'])),
               key=lambda row: (len(row['locator'].strip()), row['locator'].strip(),
                                row['link_id']), default=None)


def _register_local(ledger_dir, tables, retrieval_sha, write):
    """Register the two frozen pilot CSVs as local documents and snapshots."""
    documents = {row['document_id'] for row in tables['documents']}
    known_snapshots = {row['sha256'] for row in tables['snapshots']}
    local = {}
    for stem in LOCAL_TABLES:
        source = ledger_dir / f'{stem}.csv'
        content = source.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        path = f'../ledger-snapshots/{sha}.csv'
        if write:
            local_snapshot(ledger_dir, stem)
        doc_id = stem + '-local-record'
        local[stem] = (doc_id, sha)
        if doc_id not in documents:
            tables['documents'].append(dict(document_id=doc_id, country='VNM',
                title=f'Local Viet Nam pilot {stem} frozen migration record',
                active='false', notes='Research transcription; source document IDs and hashes are row fields'))
            documents.add(doc_id)
        else:
            record = next(row for row in tables['documents'] if row['document_id'] == doc_id)
            record['document_type'] = None
            record['language'] = None
        if sha not in known_snapshots:
            tables['snapshots'].append(dict(sha256=sha, storage_path=path,
                                           size_bytes=len(content), content_type='text/csv'))
            known_snapshots.add(sha)
        if doc_id in retrieval_sha and retrieval_sha[doc_id] != sha:
            raise ValueError(f'{stem}: local bytes changed; register a new retrieval')
        if doc_id not in retrieval_sha:
            tables['retrievals'].append(dict(retrieval_id=f'{doc_id}:1', document_id=doc_id,
                retrieved_at='2026-09-24T00:00:00Z', status='collected',
                content_type='text/csv', sha256=sha))
            retrieval_sha[doc_id] = sha
    return local


def _discovery_lines(ledger_dir, tables, retrieval_sha, document_titles,
                     existing_ids, taken, pending, counts):
    """Mine one precise line per new document and retain all link candidates."""
    by_source = defaultdict(list)
    for row in read_csv(ledger_dir / 'project-source-links.csv'):
        if row['relationship'] != 'project_page_component':
            by_source[row['source_id']].append(row)
    existing_sha = {row['sha256'] for row in tables['lines']}
    candidates = []
    for source_id, links in sorted(by_source.items()):
        sha = retrieval_sha.get(source_id)
        suitable = _shortest_locator(links)
        line_id = f'{source_id}-discovery-1' if f'{source_id}-discovery-1' in existing_ids else None
        if sha and sha not in existing_sha and suitable:
            line_id = f'{source_id}-discovery-1'
            locator = _unique_locator(sha, suitable['locator'], taken, suitable['link_id'])
            tables['lines'].append(_line(line_id, suitable['country'], sha, locator,
                1, document_titles.get(source_id) or suitable['locator'], 'named_item',
                'legacy_link', f"source_id={source_id}; migration_recorded_at={RECORDED_AT}; "
                f"legacy_links={json.dumps([{'project_id': x['project_id'], 'relationship': x['relationship'], 'review_status': x['review_status']} for x in links], ensure_ascii=False, separators=(',', ':'))}"))
            counts['discovery'] += 1
            existing_sha.add(sha)
        for link in links:
            reason = ('no snapshot' if not sha else 'no precise locator'
                      if not suitable and sha not in existing_sha else
                      'resolve to source line in 0875')
            candidates.append((link['link_id'], source_id, line_id or '',
                               link['project_id'], link['relationship'],
                               link['review_status'], link['locator'], reason))
            if reason in ('no snapshot', 'no precise locator'):
                pending.append(('link', link['link_id'], source_id, reason,
                                link['project_id'], link['relationship'],
                                link['review_status'], link['locator']))
    return candidates


def _write_results(ledger_dir, schema, tables, local, pending, candidates):
    for stem in LOCAL_TABLES:
        doc_id, _ = local[stem]
        fields = read_csv(ledger_dir / f'{stem}.csv')
        columns = list(fields[0])
        if not any(r['document_id'] == doc_id for r in tables['line_field_specs']):
            tables['line_field_specs'].append(dict(
                document_id=doc_id, columns=json.dumps(columns, ensure_ascii=False)))
        path = ledger_dir / 'line-fields' / f'{doc_id}.csv'
        path.parent.mkdir(exist_ok=True)
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerow(['line_id', *columns])
            writer.writerows([f'{doc_id}-row-{n}', *(row[c] for c in columns)]
                             for n, row in enumerate(fields, 1))
    for name, rows in tables.items():
        write_table(ledger_dir, name, rows, schema=schema)
    migration_dir = ledger_dir / 'migration'
    migration_dir.mkdir(exist_ok=True)
    for filename, header, rows in (
        ('0874-pending.csv', PENDING_HEADER, pending),
        ('0874-link-candidates.csv',
         ('link_id', 'source_id', 'line_id', 'old_project_id', 'relationship',
          'review_status', 'locator', 'reason'), candidates),
    ):
        with (migration_dir / filename).open('w', encoding='utf-8', newline='') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerow(header)
            writer.writerows(rows)


def rebuild(ledger_dir=LEDGER_DIR, write=False):
    """Return the resulting common tables and pending records; optionally write."""
    ledger_dir = Path(ledger_dir)
    schema = load_schema()
    names = ('documents', 'retrievals', 'snapshots', 'lines', 'line_field_specs')
    tables = {name: ledger_rows(ledger_dir, name, schema) for name in names}
    tables['lines'] = [row for row in tables['lines'] if not any(
        (row['notes'] or '').startswith(f'method={method}; version=1')
        for method in GENERATED_METHODS)]
    existing_ids = {row['line_id'] for row in tables['lines']}
    taken = {(row['sha256'], row['locator']) for row in tables['lines']}
    retrieval_sha = {row['document_id']: row['sha256'] for row in tables['retrievals']
                     if row['sha256']}
    document_titles = {row['document_id']: row['title'] for row in tables['documents']}
    pending = []
    counts = defaultdict(int)

    # The acquisition log and transcribed observations are local research
    # documents. A line cites their frozen CSV bytes, never uncollected HTML.
    local = _register_local(ledger_dir, tables, retrieval_sha, write)

    manifest_doc, manifest_sha = local['vnm-pilot-manifest']
    for n, row in enumerate(read_csv(ledger_dir / 'vnm-pilot-manifest.csv'), 1):
        line_id = f'{manifest_doc}-row-{n}'
        if line_id in existing_ids:
            continue
        tables['lines'].append(_line(line_id, 'VNM', manifest_sha,
            f'CSV row {n + 1}', n, row['source_id'], 'named_item', 'pilot_manifest',
            f"pilot_row_id={row['pilot_row_id']}; source_sha256={row['sha256'] or 'none'}; "
            f"collection_status={row['collection_status']}"))
        counts['pilot_manifest'] += 1

    obs_doc, obs_sha = local['vnm-pilot-observations']
    for n, row in enumerate(read_csv(ledger_dir / 'vnm-pilot-observations.csv'), 1):
        line_id = f'{obs_doc}-row-{n}'
        if line_id in existing_ids:
            continue
        classification = _pilot_classification(row)
        tables['lines'].append(_line(line_id, 'VNM', obs_sha,
            f'CSV row {n + 1}', n, row['operation'], classification, 'pilot_observation',
            f"observation_id={row['observation_id']}; source_filename={row['source_filename']}; "
            f"publisher_locator={row['locator']}"))
        counts['pilot_observation'] += 1

    for n, row in enumerate(read_csv(ledger_dir / 'idn-portfolio-observations.csv'), 1):
        line_id = f"{row['source_id']}-portfolio-{n}"
        if line_id in existing_ids:
            continue
        sha = retrieval_sha.get(row['source_id'])
        if not sha:
            pending.append(('portfolio', line_id, row['source_id'], 'no snapshot', '', '', '', ''))
            continue
        locator = _unique_locator(sha, f"Project heading: {row['title']}", taken, line_id)
        tables['lines'].append(_line(line_id, 'IDN', sha, locator, n, row['title'],
            'named_item', 'idn_portfolio', f"legacy_project_id={row['project_id']}; "
            f"period={row['period']}; reconciliation={row['reconciliation_status']}"))
        counts['portfolio'] += 1

    for n, row in enumerate(read_csv(ledger_dir / 'source-claims.csv'), 1):
        line_id = f"{row['source_id']}-claim-{n}"
        if line_id in existing_ids:
            continue
        sha = retrieval_sha.get(row['source_id'])
        if not sha:
            pending.append(('claim', row['claim_id'], row['source_id'], 'no snapshot',
                            '', '', '', row['section']))
            continue
        locator = _unique_locator(sha, f"{row['section']}: {row['claim_summary']}",
                                  taken, row['claim_id'])
        tables['lines'].append(_line(line_id, row['country'], sha, locator, n,
            row['claim_summary'], _classification(row), 'source_claim',
            f"claim_id={row['claim_id']}; match_status={row['match_status']}"))
        counts['claim'] += 1

    candidates = _discovery_lines(ledger_dir, tables, retrieval_sha, document_titles,
                                  existing_ids, taken, pending, counts)

    if write:
        _write_results(ledger_dir, schema, tables, local, pending, candidates)
    return counts, pending, candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--output-dir', type=Path, default=LEDGER_DIR)
    args = parser.parse_args()
    counts, pending, _ = rebuild(args.output_dir, write=True)
    log.info('JETP rest lines: %s, %d pending', dict(counts), len(pending))


if __name__ == '__main__':
    main()
