"""CSV headers of the JETP ledger, generated from its one DDL (ticket 0871).

``config/jetp-ledger.sql`` declares every common table of the ledger
(``docs/jetp-ledger-storage.md`` sections 1 and 3). A column exists there and
nowhere else: the header a CSV must carry is read from the DDL, never typed.

This module also knows where a table lives on disk, which the storage contract
fixes: ``data/jetp/<table>.csv`` with underscores written as hyphens, ontology
tables under ``data/jetp/ontology/``, and a table too large for the
pre-commit file ceiling chunked by country and year into
``<table>.d/<CODE>-<year>.csv``, which stays one table. The ``.d`` suffix is
what keeps a chunk directory apart from a directory that merely shares a
table's name: ``data/jetp/documents/`` is the DVC snapshot store, and the
``documents`` table must never read from, write to or clean it.

A library: ``build_ledger.py`` is its command line, and a writer of ledger
rows calls ``write_table`` so its file carries the generated header.
"""

import csv
import io
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DDL_PATH = ROOT / 'config' / 'jetp-ledger.sql'
PRE_COMMIT = ROOT / '.githooks' / 'pre-commit'
LEDGER_DIR = ROOT / 'data' / 'jetp'

# Tables stored under data/jetp/ontology/ (ontology section 5, ticket 0880),
# in the order the ontology reader walks them.
ONTOLOGY_TABLES = ('terms', 'status_crosswalk', 'sector_crosswalk', 'perimeters',
                   'marker_coefficients')

# Files of the current ledger that share a path with a table of the new one.
# Ticket 0875 replaced projects.csv; its old rows are retained under
# migration/0875-projects-legacy.csv for compatibility readers until 0878.
LEGACY_FILES = {}

CHUNK_NAME = re.compile(r'^(?P<country>[A-Z]{3})-(?P<year>\d{4})\.csv$')


@dataclass(frozen=True)
class Schema:
    """Tables of the DDL in declaration order, with their columns and keys."""

    tables: dict  # table -> tuple of column names, in order
    keys: dict    # table -> tuple of primary-key column names

    def header(self, table):
        return list(self.tables[table])


def load_schema(ddl_path=DDL_PATH):
    """Read the DDL through SQLite itself, so the header is what SQLite parsed."""
    conn = sqlite3.connect(':memory:')
    try:
        conn.executescript(Path(ddl_path).read_text(encoding='utf-8'))
        names = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid")]
        tables, keys = {}, {}
        for name in names:
            info = conn.execute(f'PRAGMA table_info("{name}")').fetchall()
            tables[name] = tuple(row[1] for row in info)
            keys[name] = tuple(row[1] for row in sorted(
                (row for row in info if row[5]), key=lambda row: row[5]))
        return Schema(tables=tables, keys=keys)
    finally:
        conn.close()


def file_stem(table):
    return table.replace('_', '-')


def table_path(ledger_dir, table):
    """The single-file location of a table."""
    base = Path(ledger_dir) / 'ontology' if table in ONTOLOGY_TABLES else Path(ledger_dir)
    return base / f'{file_stem(table)}.csv'


def chunk_dir(ledger_dir, table):
    """The directory of a chunked table, ``<table>.d/`` beside its single file."""
    return table_path(ledger_dir, table).with_suffix('.d')


def file_ceiling(pre_commit=PRE_COMMIT):
    """The per-file byte ceiling, read from the hook that enforces it."""
    match = re.search(r'^\s*limit=(\d+)\s*$', Path(pre_commit).read_text(encoding='utf-8'),
                      re.MULTILINE)
    if match is None:
        raise ValueError(f'no limit= line in {pre_commit}')
    return int(match.group(1))


def legacy_reason(ledger_dir, table):
    """Why a present file is not read as this table, or None."""
    if Path(ledger_dir).resolve() != LEDGER_DIR.resolve():
        return None
    return LEGACY_FILES.get(table)


def _relative(path, ledger_dir):
    try:
        return str(Path(path).relative_to(ledger_dir))
    except ValueError:
        return str(path)


def table_files(ledger_dir, table):
    """The files that hold a table, and any layout error.

    Returns ``(files, errors)``; each file is ``(path, country, year)`` where
    country and year are None for an unchunked table.
    """
    if legacy_reason(ledger_dir, table):
        return [], []
    single = table_path(ledger_dir, table)
    directory = chunk_dir(ledger_dir, table)
    chunks, errors = [], []
    if directory.is_dir():
        for path in sorted(directory.glob('*.csv')):
            match = CHUNK_NAME.match(path.name)
            if match is None:
                errors.append(f'chunk: {_relative(path, ledger_dir)}: '
                              'a chunk is named <CODE>-<year>.csv')
            else:
                chunks.append((path, match['country'], match['year']))
    if single.is_file():
        if chunks:
            errors.append(f'chunk: {file_stem(table)} is both a file and a chunk directory')
        return [(single, None, None)], errors
    return chunks, errors


def header_errors(found, expected, where):
    """Named differences between a file header and the header it must carry."""
    errors = []
    for position, (got, want) in enumerate(zip(found, expected), start=1):
        if got != want:
            errors.append(f"header: {where}: column {position} is '{got}', "
                          f"expected '{want}'")
            break
    if not errors and len(found) != len(expected):
        if len(found) < len(expected):
            missing = ', '.join(f"'{c}'" for c in expected[len(found):])
            errors.append(f'header: {where}: missing column {missing}')
        else:
            extra = ', '.join(f"'{c}'" for c in found[len(expected):])
            errors.append(f'header: {where}: unexpected column {extra}')
    return errors


def read_csv(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        return header, list(reader)


def read_table(ledger_dir, table, schema):
    """Rows of a table, reunited from its chunks, with every error found.

    A file whose header diverges contributes no rows: loading it by position
    would put values under the wrong column.
    """
    expected = schema.header(table)
    files, errors = table_files(ledger_dir, table)
    ceiling = file_ceiling()
    rows = []
    for path, country, year in files:
        where = _relative(path, ledger_dir)
        if path.stat().st_size > ceiling:
            errors.append(f'ceiling: {where} exceeds {ceiling} bytes; chunk it by country and year')
        header, body = read_csv(path)
        mismatch = header_errors(header, expected, where)
        if mismatch:
            errors.extend(mismatch)
            continue
        for number, row in enumerate(body, start=2):
            if len(row) != len(expected):
                errors.append(f'header: {where}: line {number} has {len(row)} fields, '
                              f'the header {len(expected)}')
                continue
            record = dict(zip(expected, row))
            if country is not None:
                errors.extend(_chunk_errors(record, country, year, where, number))
            rows.append(tuple(value if value != '' else None for value in row))
    return rows, errors


def _chunk_errors(record, country, year, where, number):
    errors = []
    if 'country' in record and record['country'] != country:
        errors.append(f"chunk: {where}: line {number} has country '{record['country']}'")
    if 'recorded_at' in record and not record['recorded_at'].startswith(year):
        errors.append(f"chunk: {where}: line {number} recorded_at "
                      f"'{record['recorded_at']}' is not in {year}")
    return errors


def check_headers(ledger_dir=LEDGER_DIR, schema=None):
    """Header and layout errors of every ledger table present in a directory."""
    schema = schema or load_schema()
    errors = []
    for table in schema.tables:
        files, layout = table_files(ledger_dir, table)
        errors.extend(layout)
        for path, _, _ in files:
            header, _ = read_csv(path)
            errors.extend(header_errors(header, schema.header(table),
                                        _relative(path, ledger_dir)))
    return errors


def _render(header, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\n')
    writer.writerow(header)
    for row in rows:
        writer.writerow(['' if row.get(c) is None else row.get(c) for c in header])
    return buffer.getvalue()


def write_table(ledger_dir, table, rows, ceiling=None, schema=None):
    """Write a table with its generated header, chunked when over the ceiling.

    ``rows`` are dicts keyed by column. Under the ceiling the table is one
    file; over it, one file per country and year of ``recorded_at``. Returns
    the paths written. A chunk that is still over the ceiling is written all
    the same and reported by ``read_table``, which is where the hook's rule is
    enforced.
    """
    schema = schema or load_schema()
    ceiling = file_ceiling() if ceiling is None else ceiling
    header = schema.header(table)
    single = table_path(ledger_dir, table)
    text = _render(header, rows)
    if len(text.encode('utf-8')) <= ceiling:
        single.parent.mkdir(parents=True, exist_ok=True)
        single.write_text(text, encoding='utf-8')
        _remove_stale_chunks(chunk_dir(ledger_dir, table))
        return [single]
    if 'country' not in header or 'recorded_at' not in header:
        raise ValueError(f'{table} is over {ceiling} bytes and has no country '
                         'and recorded_at to chunk it by')
    groups = {}
    for row in rows:
        groups.setdefault((row['country'], str(row['recorded_at'])[:4]), []).append(row)
    directory = chunk_dir(ledger_dir, table)
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for (country, year), members in sorted(groups.items()):
        path = directory / f'{country}-{year}.csv'
        path.write_text(_render(header, members), encoding='utf-8')
        written.append(path)
    _remove_stale_chunks(directory, keep=written)
    single.unlink(missing_ok=True)
    return written


def _remove_stale_chunks(directory, keep=()):
    """Delete the chunk files of a table that the last write did not produce.

    Only ``<CODE>-<year>.csv`` files directly in the table's own ``.d``
    directory are the writer's; anything else there is left alone, and the
    directory is removed only once it is empty.
    """
    if not directory.is_dir():
        return
    keep = {Path(path) for path in keep}
    for path in directory.glob('*.csv'):
        if CHUNK_NAME.match(path.name) and path not in keep:
            path.unlink()
    if not any(directory.iterdir()):
        directory.rmdir()
