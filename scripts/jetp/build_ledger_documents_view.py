"""Serve the ledger's documents table as the observatory's titles view (ticket 1290).

One invocation, one served file, one table: ``data/jetp/documents.csv`` as
``{"documents": [...]}``, one row per document in key order, empty cells as
null. The Documents page joins it to ``documents.json`` (the retrievals) on
the document identifier at read time, to name each document by its title.

The projection keeps what identifies a document to a reader — identifier,
country, type, language, title, publication date, the edition it revises —
and drops three columns: ``url``, which the retrievals view already serves as
the address each attempt read; ``active``, a collector switch; and ``notes``,
the curators' working notes. Together they would double the file (134 kB
served whole against 66 kB, 2026-09-25), and it loads on every route. The ledger table is the target of the migration that retires
``sources.csv`` (docs/jetp-ledger-migration.md), so the view is read from it
rather than from the legacy registry. A separate script from
``build_observatory.py``, so a title correction rebuilds this file alone and
leaves the other views and their recorded input hashes where they are.
"""

import argparse
import json
from pathlib import Path

from script_io_args import parse_io_args, validate_io

from jetp._ledger_headers import load_schema, read_table

ROOT = Path(__file__).resolve().parents[2]
TABLE = 'documents'
COLUMNS = ('document_id', 'country', 'document_type', 'language', 'title',
           'published_date', 'edition_of')


def build(ledger_dir):
    """The served projection of the documents table, validated against the DDL header."""
    schema = load_schema()
    rows, errors = read_table(ledger_dir, TABLE, schema)
    if errors:
        raise ValueError(f'{TABLE}: {errors[0]}')
    header = schema.header(TABLE)
    records = [dict(zip(header, row)) for row in rows]
    return {'documents': [{c: r[c] for c in COLUMNS}
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
