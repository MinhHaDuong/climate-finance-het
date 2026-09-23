"""Load the JETP ledger CSVs into SQLite, where the DDL is the validator (ticket 0871).

CSV in git stays the system of record; the SQLite file under
``data/derived/jetp/`` is derived, disposable and never committed
(``docs/jetp-ledger-storage.md`` section 3). The build applies
``config/jetp-ledger.sql``, loads every table present (a chunked table is
reunited from its chunks), and collects every failure with a named reason:

- ``header:`` a file whose header is not the one generated from the DDL;
- ``chunk:`` / ``ceiling:`` a chunk misnamed or holding another country or
  year, or a file over the pre-commit ceiling;
- ``unique:`` / ``not_null:`` / ``check:`` a row refused by a constraint;
- ``foreign_key:`` a key that points at no row;
- ``<view>:`` a row of a named validation query ``violation_<view>``,
  among them ``closed_list:`` for a value that is not a term in force;
- ``line_fields:`` a per-document fields table without its spec or citing an
  unknown line (a diverging header there is a ``header:`` failure).

The output is deterministic for a given input: rows are inserted in key order
whatever their order in the files, the file is written by ``VACUUM INTO``, and
its modification time is ``SOURCE_DATE_EPOCH`` when that is set. On any
failure nothing is written and a previous output is removed.
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from utils import get_logger

from jetp._ledger_headers import (
    DDL_PATH,
    LEDGER_DIR,
    header_errors,
    load_schema,
    read_csv,
    read_table,
)

log = get_logger('jetp.build_ledger')

CONSTRAINT_REASONS = (
    ('UNIQUE constraint failed', 'unique'),
    ('NOT NULL constraint failed', 'not_null'),
    ('CHECK constraint failed', 'check'),
)


def _constraint_reason(message):
    for prefix, reason in CONSTRAINT_REASONS:
        if message.startswith(prefix):
            return reason
    return 'constraint'


def _load(conn, schema, ledger_dir):
    errors = []
    for table in schema.tables:
        rows, table_errors = read_table(ledger_dir, table, schema)
        errors.extend(table_errors)
        columns = schema.header(table)
        key_positions = [columns.index(k) for k in schema.keys[table]]
        rows.sort(key=lambda row: tuple(row[i] or '' for i in key_positions) + tuple(
            value or '' for value in row))
        placeholders = ', '.join('?' * len(columns))
        quoted = ', '.join(f'"{c}"' for c in columns)
        statement = f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders})'
        for row in rows:
            try:
                conn.execute(statement, row)
            except sqlite3.IntegrityError as exc:
                key = '/'.join(str(row[i]) for i in key_positions)
                errors.append(f'{_constraint_reason(str(exc))}: {table} {key}: {exc}')
    return errors


def _foreign_key_errors(conn):
    errors = []
    for table, rowid, parent, fkid in conn.execute('PRAGMA foreign_key_check'):
        columns = [row[3] for row in conn.execute(f'PRAGMA foreign_key_list("{table}")')
                   if row[0] == fkid]
        values = conn.execute(
            f'SELECT {", ".join(f"{chr(34)}{c}{chr(34)}" for c in columns)} '
            f'FROM "{table}" WHERE rowid = ?', (rowid,)).fetchone()
        shown = ', '.join(f"{table}.{c} = '{v}'" for c, v in zip(columns, values))
        errors.append(f'foreign_key: {shown} has no row in {parent}')
    return sorted(errors)


def _view_errors(conn):
    errors = []
    views = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'view' "
        "AND name LIKE 'violation\\_%' ESCAPE '\\' ORDER BY name")]
    for view in views:
        reason = view.removeprefix('violation_')
        details = sorted(row[0] for row in conn.execute(f'SELECT detail FROM "{view}"'))
        errors.extend(f'{reason}: {detail}' for detail in details)
    return errors


def _line_field_errors(conn, ledger_dir):
    """Each line-fields/<document_id>.csv against its line_field_specs row."""
    directory = Path(ledger_dir) / 'line-fields'
    if not directory.is_dir():
        return []
    specs = dict(conn.execute('SELECT document_id, columns FROM line_field_specs'))
    known = {row[0] for row in conn.execute('SELECT line_id FROM lines')}
    errors = []
    for path in sorted(directory.glob('*.csv')):
        where = f'line-fields/{path.name}'
        if path.stem not in specs:
            errors.append(f'line_fields: {where}: document {path.stem} has no row '
                          'in line_field_specs')
            continue
        header, body = read_csv(path)
        mismatch = header_errors(header, ['line_id', *json.loads(specs[path.stem])], where)
        if mismatch:
            errors.extend(mismatch)
            continue
        seen = set()
        for number, row in enumerate(body, start=2):
            line_id = row[0] if row else ''
            if line_id in seen:
                errors.append(f"line_fields: {where}: line {number} repeats line_id '{line_id}'")
            elif line_id not in known:
                errors.append(f"line_fields: {where}: line {number} line_id '{line_id}' "
                              'is not in lines')
            seen.add(line_id)
    return errors


def _write(conn, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(output.name + '.tmp')
    staging.unlink(missing_ok=True)
    conn.execute('VACUUM INTO ?', (str(staging),))
    epoch = os.environ.get('SOURCE_DATE_EPOCH')
    if epoch:
        os.utime(staging, (int(epoch), int(epoch)))
    os.replace(staging, output)


def build(ledger_dir=LEDGER_DIR, output=None, ddl_path=DDL_PATH):
    """Validate the ledger and, when it is clean and ``output`` is given, write it.

    Returns the list of failures, each prefixed by its named reason; an empty
    list means the ledger is valid.
    """
    ledger_dir = Path(ledger_dir)
    schema = load_schema(ddl_path)
    conn = sqlite3.connect(':memory:')
    try:
        conn.executescript(Path(ddl_path).read_text(encoding='utf-8'))
        errors = _load(conn, schema, ledger_dir)
        conn.commit()
        errors += _foreign_key_errors(conn)
        errors += _view_errors(conn)
        errors += _line_field_errors(conn, ledger_dir)
        if errors:
            if output is not None:
                Path(output).unlink(missing_ok=True)
            return errors
        if output is not None:
            _write(conn, output)
        return []
    finally:
        conn.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER_DIR)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path, help='SQLite file to write')
    mode.add_argument('--check', action='store_true', help='validate only, write nothing')
    args = parser.parse_args(argv)
    errors = build(args.ledger_dir, None if args.check else args.output)
    for error in errors:
        log.error('%s', error)
    if errors:
        log.error('jetp ledger: %d failure(s) in %s', len(errors), args.ledger_dir)
        return 1
    log.info('jetp ledger: valid (%s)%s', args.ledger_dir,
             '' if args.check else f', written to {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
