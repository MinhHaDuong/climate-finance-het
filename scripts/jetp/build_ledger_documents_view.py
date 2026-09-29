"""Serve the ledger's documents table as the observatory's titles view (ticket 1290).

One invocation, one served file: ``data/jetp/documents.csv`` as
``{"documents": [...]}``, one row per document in key order, empty cells as
null. The Documents page joins it to ``documents.json`` (the retrievals) on
the document identifier at read time, to name each document by its title.

The projection keeps what identifies a document to a reader — identifier,
country, type, language, title, publication date, the edition it revises —
and drops three columns: ``url``, which the retrievals view already serves as
the address each attempt read; ``active``, a collector switch; and ``notes``,
the curators' working notes. Together they would double the file (134 kB
served whole against 66 kB, 2026-09-25), and it loads on every route. A separate script from
``build_observatory.py``, so a title correction rebuilds this file alone and
leaves the other views and their recorded input hashes where they are.

Each row also carries ``collection_state``, the state of our collection and
reading of that document (ticket 1610), derived here from the retrievals and
the lines and stored in no table: ``not_collected`` where no retrieval
yielded a snapshot; ``collected`` where a snapshot exists and no line was
read from it; ``stub`` where its only lines are the minimal line the
migration minted to hold a locator (``docs/jetp-ledger-migration.md`` step
3, ``method=legacy_link`` in the line's notes); ``extracted`` where an
extractor read at least one other line. The later states of the extraction
backlog (tracker 1500) are not shown yet.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from script_io_args import parse_io_args, validate_io

from jetp._country_views_v2 import _line_documents
from jetp._ledger_headers import load_schema, read_table

ROOT = Path(__file__).resolve().parents[2]
TABLE = 'documents'
COLUMNS = ('document_id', 'country', 'document_type', 'language', 'title',
           'published_date', 'edition_of')
STATES = ('not_collected', 'collected', 'stub', 'extracted')
# The mark ticket 0874 left in the notes of each minimal line it minted so a
# legacy discovery link had a locator to cite (35 lines, 2026-09-24).
STUB_LINE_NOTE = 'method=legacy_link;'


def _rows(ledger_dir, table, schema):
    rows, errors = read_table(ledger_dir, table, schema)
    if errors:
        raise ValueError(f'{table}: {errors[0]}')
    return [dict(zip(schema.header(table), row)) for row in rows]


def is_stub_line(line):
    return (line['notes'] or '').startswith(STUB_LINE_NOTE)


def collection_states(documents, retrievals, lines):
    """The state of each document, from what its retrievals yielded and what was read."""
    by_digest = defaultdict(set)
    for row in retrievals:
        if row['sha256']:
            by_digest[row['sha256']].add(row['document_id'])
    by_line = {row['line_id']: row for row in lines}
    read = defaultdict(list)
    for line_id, document_id in _line_documents(by_line, by_digest).items():
        read[document_id].append(by_line[line_id])
    collected = {document_id for members in by_digest.values() for document_id in members}
    states = {}
    for row in documents:
        document_id = row['document_id']
        if document_id not in collected:
            states[document_id] = 'not_collected'
        elif not read[document_id]:
            states[document_id] = 'collected'
        elif all(is_stub_line(line) for line in read[document_id]):
            states[document_id] = 'stub'
        else:
            states[document_id] = 'extracted'
    return states


def build(ledger_dir):
    """The served projection of the documents table, validated against the DDL header."""
    schema = load_schema()
    records = _rows(ledger_dir, TABLE, schema)
    states = collection_states(records, _rows(ledger_dir, 'retrievals', schema),
                               _rows(ledger_dir, 'lines', schema))
    return {'documents': [{**{c: r[c] for c in COLUMNS},
                           'collection_state': states[r['document_id']]}
                          for r in sorted(records, key=lambda r: r['document_id'])]}


def main(argv=None):
    io_args, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--ledger-dir', type=Path, default=ROOT / 'data/jetp')
    args = parser.parse_args(extra)
    output = Path(io_args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    validate_io(output=str(output))
    result = build(args.ledger_dir)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
