"""Serve the ontology tables to the observatory, one JSON file per table (ticket 0882).

The Glossary is generated from these files, so the words a reader meets are
the ones the validator applies. Storage contract section 2: every table is
served, one file per table, so a table with no row yet is served empty rather
than left out. Each file carries the table's columns verbatim, in DDL order,
every row including superseded ones (the Glossary shows a term's revision
history), and the keys of the rows in force now, as ``_ontology.in_force``
decides them: the page never re-derives the revision rule.

Like ``build_observations.py``, one invocation writes every file, and it is a
separate script from ``build_observatory.py`` so that the country views and
their recorded input hashes do not move when the ontology does.
"""

import argparse
import json
from pathlib import Path

from jetp._ledger_headers import (
    LEDGER_DIR,
    ONTOLOGY_TABLES,
    file_stem,
    load_schema,
    read_table,
)
from jetp._ontology import ontology_as_of

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / 'deliverables' / 'jetp-observatory' / 'data' / 'ontology'


def ontology_views(ledger_dir=LEDGER_DIR, schema=None):
    """``{file stem: view}`` for every ontology table, the empty ones included."""
    schema = schema or load_schema()
    current = ontology_as_of(ledger_dir, schema=schema)
    views = {}
    for table in ONTOLOGY_TABLES:
        rows, errors = read_table(ledger_dir, table, schema)
        if errors:
            raise ValueError('; '.join(errors))
        key = schema.keys[table][0]
        views[file_stem(table)] = {
            'table': table,
            'key': key,
            'fields': schema.header(table),
            'rows': [list(row) for row in rows],
            'in_force': [row[key] for row in current[table]],
        }
    return views


def write_views(ledger_dir, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for stem, view in ontology_views(ledger_dir).items():
        (output_dir / f'{stem}.json').write_text(
            json.dumps(view, ensure_ascii=False, separators=(',', ':')) + '\n',
            encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER_DIR)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    write_views(args.ledger_dir, args.output_dir)


if __name__ == '__main__':
    main()
