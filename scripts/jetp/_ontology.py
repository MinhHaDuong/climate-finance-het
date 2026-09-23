"""The JETP ontology as of a knowledge cutoff, and its reference hash (ticket 0880).

The ontology is five tables under ``data/jetp/ontology/``, declared in
``config/jetp-ledger.sql`` (``docs/jetp-ontology.md`` section 5). They are
revised by supersession, never edited in place, so the words the ledger used
at any date can be read back:

- ``ontology_as_of(ledger_dir, K)`` returns, per table, the rows in force at
  cutoff K: recorded on or before K, accepted, and superseded by no row
  recorded on or before K. Without K it is the current ontology, the same
  rows as the DDL's ``*_in_force`` views.
- ``shared_status(ontology, publisher_id, own_status)`` reads a status
  crosswalk in such an ontology, so a remapping recorded after K leaves the
  shared status read at K unchanged.
- ``ontology_ref(ledger_dir, ddl_path)`` is the hash of the ontology
  directory and the DDL, which every derived result records beside its run
  identifier and cutoffs.

A library: the builders of derived results call it.
"""

import hashlib
from pathlib import Path

from jetp._ledger_headers import DDL_PATH, LEDGER_DIR, load_schema, read_table

ONTOLOGY_TABLES = ('terms', 'status_crosswalk', 'sector_crosswalk', 'perimeters',
                   'marker_coefficients')


def _on_or_before(recorded_at, cutoff):
    """A row recorded at any time on day K is on or before K."""
    return recorded_at[:len(cutoff)] <= cutoff


def in_force(rows, row_key, cutoff=None):
    """The rows in force at ``cutoff``: accepted terminal rows of their chains."""
    known = [row for row in rows
             if cutoff is None or _on_or_before(row['recorded_at'], cutoff)]
    superseded = {row['supersedes'] for row in known if row['supersedes']}
    return [row for row in known
            if row['status'] == 'accepted' and row[row_key] not in superseded]


def ontology_as_of(ledger_dir=LEDGER_DIR, cutoff=None, schema=None):
    """Per ontology table, the rows (dicts) in force at ``cutoff`` (ISO date or time).

    Raises ``ValueError`` when a table's files do not match the DDL, since an
    ontology read from a misaligned file would be silently wrong.
    """
    schema = schema or load_schema()
    result = {}
    for table in ONTOLOGY_TABLES:
        rows, errors = read_table(ledger_dir, table, schema)
        if errors:
            raise ValueError('; '.join(errors))
        header = schema.header(table)
        records = [dict(zip(header, row)) for row in rows]
        result[table] = in_force(records, schema.keys[table][0], cutoff)
    return result


def shared_status(ontology, publisher_id, own_status):
    """``(axis, shared_status)`` of a publisher's own word, or None when unmapped."""
    for row in ontology['status_crosswalk']:
        if row['publisher_id'] == publisher_id and row['own_status'] == own_status:
            return row['axis'], row['shared_status']
    return None


def ontology_ref(ledger_dir=LEDGER_DIR, ddl_path=DDL_PATH):
    """``sha256:<hex>`` over the DDL and every file of ``<ledger_dir>/ontology/``.

    Files are hashed by relative path and content in path order, so the
    reference depends on what the files say and where they are, not on when
    or in what order they were written.
    """
    digest = hashlib.sha256()
    digest.update(b'ddl\0')
    digest.update(Path(ddl_path).read_bytes())
    directory = Path(ledger_dir) / 'ontology'
    files = sorted(p for p in directory.rglob('*') if p.is_file()) if directory.is_dir() else []
    for path in files:
        digest.update(b'\0file\0' + path.relative_to(directory).as_posix().encode('utf-8') + b'\0')
        digest.update(path.read_bytes())
    return f'sha256:{digest.hexdigest()}'
