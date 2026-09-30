"""Serve exact ledger tables and explicitly bounded projections (ticket 0870).

Multi-output script: --output-dir is the static download directory. The
inventory distinguishes complete tables from projections and named omissions.
No register ingestion or identity decision is rerun by this build.
"""

import argparse
import csv
import hashlib
import json
import tempfile
from pathlib import Path

from jetp._country_views_v2 import _current
from jetp._ledger_headers import (
    LEDGER_DIR,
    file_stem,
    load_schema,
    read_table,
    table_files,
)

ROOT = Path(__file__).resolve().parents[2]
BULK = {
    'timings': 'Bulk comparator periods; country Statements retain selected dates, not the complete timing table.',
    'external_ids': 'Bulk comparator identifiers; complete identity decisions are served in line-referents and relations, but the identifier table is not downloaded.',
}


def terminal_observation_ids(rows, schema):
    """Accepted terminal observation IDs, using the full table's supersession chains."""
    objects = [dict(zip(schema.header('observations'), row)) for row in rows]
    return {row['observation_id'] for row in _current(objects, 'observation_id')}


def _render_downloads(ledger_dir, output_dir):
    """Return the inventory after writing one table per CSV, preserving source shards."""
    ledger_dir, output_dir = Path(ledger_dir), Path(output_dir)
    schema = load_schema()
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = []

    def publish(source):
        relative = source.relative_to(ledger_dir)
        target = output_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        if len(raw) >= 512000:
            raise ValueError(f'{relative}: served artifact exceeds the 512000-byte ceiling')
        target.write_bytes(raw)
        return {'path': 'data/ledger/' + relative.as_posix(),
                'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

    for table in schema.tables:
        rows, errors = read_table(ledger_dir, table, schema)
        if errors:
            raise ValueError('; '.join(errors))
        entry = {'table': file_stem(table), 'keys': list(schema.keys[table]),
                 'rows': len(rows), 'fully_served': table not in BULK,
                 'files': [], 'projections': [], 'reason': BULK.get(table, '')}
        if table not in BULK:
            sources, errors = table_files(ledger_dir, table)
            if errors:
                raise ValueError('; '.join(errors))
            entry['files'] = [publish(path) for path, _, _ in sources]
        inventory.append(entry)

    def projection(table, selected, filename, reason, in_force=None):
        target = output_dir / filename
        with target.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerow(schema.header(table))
            writer.writerows(selected)
        if target.stat().st_size >= 512000:
            raise ValueError(f'{filename}: projection exceeds the served file ceiling')
        entry = next(item for item in inventory if item['table'] == file_stem(table))
        entry['projections'].append({'path': 'data/ledger/' + filename,
                                     'rows': len(selected), 'reason': reason,
                                     'partial': True})
        target.with_suffix('.json').write_text(json.dumps(
            {'fields': schema.header(table), 'rows': selected,
             'in_force': in_force} if in_force is not None else
            {'fields': schema.header(table), 'rows': selected},
            ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')

    observations, _ = read_table(ledger_dir, 'observations', schema)
    selected = [row for row in observations if dict(zip(schema.header('observations'), row))
                .get('subject_id') == 'vnm-jetp-portfolio-2025']
    current_ids = terminal_observation_ids(observations, schema)
    projection('observations', selected, 'vnm-perimeter-observations.csv',
               'Only observations of the July 2025 Viet Nam portfolio perimeter; history retained, with terminal accepted IDs computed from the full ledger.',
               in_force=[row[0] for row in selected if row[0] in current_ids])
    line_ids = {dict(zip(schema.header('observations'), row))['line_id'] for row in selected}
    lines, _ = read_table(ledger_dir, 'lines', schema)
    cited = [row for row in lines if row[0] in line_ids]
    projection('lines', cited, 'vnm-perimeter-lines.csv',
               'Only the lines cited by the served Viet Nam perimeter observations; local transcription provenance is retained verbatim.')
    inventory.extend([
        {'table': 'line-fields/<document_id>', 'keys': ['line_id'],
         'rows': None, 'fully_served': False, 'files': [], 'projections': [],
         'reason': 'Per-document verbatim fields remain in the frozen country Document rows exports; the complete 97-document field collection is not served.'},
        {'table': 'dry-searches', 'keys': ['search_id'], 'rows': None,
         'fully_served': True, 'files': [publish(ledger_dir / 'dry-searches.csv')], 'projections': [], 'reason': ''},
        {'table': 'decisions.md', 'keys': [], 'rows': None,
         'fully_served': False, 'files': [], 'projections': [],
         'reason': 'Internal narrative adjudication log; structured 1620 decisions, evidence, readers and confidence are served separately below.'},
        {'table': 'news-leads', 'keys': [], 'rows': None,
         'fully_served': False, 'files': [], 'projections': [],
         'reason': 'Working watch file, not a ledger table or a set of accepted observations.'},
    ])
    decisions = publish(ledger_dir / 'migration/1620-register-dispositions.csv')
    with (ledger_dir / 'migration/1620-register-dispositions.csv').open(newline='', encoding='utf-8') as handle:
        reader = csv.reader(handle)
        decision_view = {'fields': next(reader), 'rows': list(reader)}
    (output_dir / 'register-decisions.json').write_text(json.dumps(
        decision_view, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    owned_files = sorted(path.relative_to(output_dir).as_posix()
                         for path in output_dir.rglob('*') if path.is_file())
    result = {'tables': inventory, 'decision_record': decisions,
              'owned_files': owned_files + ['inventory.json'],
              'register_policy': 'Legacy registers were read once into reviewed records. Building these downloads reads current records; it does not rerun ingestion, mint identities or rewrite decisions.'}
    (output_dir / 'inventory.json').write_text(
        json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    return result


def build_downloads(ledger_dir, output_dir):
    """Repair every expected sidecar and remove only stale manifest-owned outputs.

    The forced Make prerequisite checks this manifest on every invocation;
    unchanged files keep their bytes and timestamps. Planning completes before
    publication, so malformed sources cannot erase a previously usable export.
    """
    output_dir = Path(output_dir)
    with tempfile.TemporaryDirectory(prefix='t0870-ledger-downloads-') as staging:
        stage = Path(staging)
        result = _render_downloads(ledger_dir, stage)
        previous = output_dir / 'inventory.json'
        old_files = json.loads(previous.read_text()).get('owned_files', []) if previous.exists() else []
        for relative in old_files:
            path = output_dir / relative
            if not path.resolve().is_relative_to(output_dir.resolve()):
                raise ValueError(f'Unsafe owned output: {relative}')
        output_dir.mkdir(parents=True, exist_ok=True)
        for relative in result['owned_files']:
            source, target = stage / relative, output_dir / relative
            raw = source.read_bytes()
            if not target.exists() or target.read_bytes() != raw:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        for relative in sorted(set(old_files) - set(result['owned_files'])):
            target = output_dir / relative
            if target.is_file():
                target.unlink()
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER_DIR)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    build_downloads(args.ledger_dir, args.output_dir)


if __name__ == '__main__':
    main()
