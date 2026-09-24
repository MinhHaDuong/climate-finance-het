"""Build reviewed publisher crosswalk rows from the M1a ledger (tickets 0887/0888).

The keys are publishing parties, resolved through document_publishers rather
than guessed from document IDs. Unlisted words have no implicit fallback.
"""

import argparse
import csv
import logging
from pathlib import Path

from jetp._ledger_headers import LEDGER_DIR, load_schema, read_table, write_table

RECORDED_AT = '2026-09-24'
DECIDED_BY = 'migration 0887/0888, reviewed source fields'
log = logging.getLogger(__name__)

# These are the register's verbatim Status cells. "Completed" means physical
# completion, the IATI finalisation state; it does not assert financial closure.
ZAF_DELIVERY = {
    'A. Planned': 'pipeline',
    'B. Approved': 'pipeline',
    'C. Implementation Phase': 'implementation',
    'D. Completed': 'finalisation',
}
# A portfolio combines different interventions; even "Energy Efficiency"
# includes technical assistance and green-building finance, not one CRS purpose.
ZAF_PURPOSE = {}

# Only publisher groups with a single defensible CRS purpose are mapped. The
# source's broad portfolio labels remain verbatim and unresolved.
IDN_PURPOSE = {
    'transmission': '23630',
    'hydro': '23220',
    'geothermal': '23260',
    'wind': '23240',
}


def _records(ledger_dir, table, schema):
    rows, errors = read_table(ledger_dir, table, schema)
    if errors:
        raise ValueError('; '.join(errors))
    return [dict(zip(schema.header(table), row)) for row in rows]


def publishing_party(ledger_dir, document_id, schema=None):
    schema = schema or load_schema()
    rows = _records(ledger_dir, 'document_publishers', schema)
    authors = {row['party_id'] for row in rows
               if row['document_id'] == document_id and row['role'] == 'author'}
    if len(authors) != 1:
        raise ValueError(f'{document_id}: expected one author party, got {sorted(authors)}')
    return authors.pop()


def distinct_field(ledger_dir, document_id, column):
    path = Path(ledger_dir) / 'line-fields' / f'{document_id}.csv'
    with path.open(encoding='utf-8', newline='') as handle:
        return {row[column] for row in csv.DictReader(handle) if row[column]}


def crosswalk_rows(ledger_dir=LEDGER_DIR, schema=None):
    schema = schema or load_schema()
    zaf = 'zaf-jet-investment-register-q1-2026'
    idn = 'idn-jetp-progress-report-2025'
    if distinct_field(ledger_dir, zaf, 'Status') != set(ZAF_DELIVERY):
        raise ValueError('register Status cells differ from reviewed vocabulary')
    status = []
    zaf_party = publishing_party(ledger_dir, zaf, schema)
    for number, (own, shared) in enumerate(ZAF_DELIVERY.items(), 1):
        status.append(dict(crosswalk_row_id=f'{zaf_party}.status.{number}',
                           publisher_id=zaf_party, own_status=own, axis='delivery',
                           shared_status=shared, recorded_at=RECORDED_AT,
                           decided_by=DECIDED_BY, status='accepted',
                           notes=f'{zaf}, Status; IATI ActivityStatus mapping'))

    # The report states approval for its finance rows even though the M1a
    # priority-project appendix does not print a status cell for each row.
    idn_party = publishing_party(ledger_dir, idn, schema)
    status.append(dict(crosswalk_row_id=f'{idn_party}.status.1',
                       publisher_id=idn_party, own_status='Approved', axis='money',
                       shared_status='approved', recorded_at=RECORDED_AT,
                       decided_by=DECIDED_BY, status='accepted',
                       notes=f'{idn}, financing approval; not an M1a appendix field'))

    fields = distinct_field(ledger_dir, idn, 'technology_group')
    sector = []
    for number, own in enumerate(sorted(ZAF_PURPOSE), 1):
        sector.append(dict(crosswalk_row_id=f'{zaf_party}.sector.{number}',
                           publisher_id=zaf_party, own_sector=own,
                           purpose_code=ZAF_PURPOSE[own], recorded_at=RECORDED_AT,
                           decided_by=DECIDED_BY, status='accepted',
                           notes='ZAF register Portfolios cell; OECD DAC CRS purpose code'))
    for number, own in enumerate(sorted(fields & IDN_PURPOSE.keys()), 1):
        sector.append(dict(crosswalk_row_id=f'{idn_party}.sector.{number}',
                           publisher_id=idn_party, own_sector=own,
                           purpose_code=IDN_PURPOSE[own], recorded_at=RECORDED_AT,
                           decided_by=DECIDED_BY, status='accepted',
                           notes='IDN M1a technology_group; OECD DAC CRS purpose code'))
    zaf_fields = distinct_field(ledger_dir, zaf, 'Portfolios')
    return status, sector, (fields - IDN_PURPOSE.keys()) | (zaf_fields - ZAF_PURPOSE.keys())


def write_crosswalks(ledger_dir=LEDGER_DIR):
    schema = load_schema()
    status, sector, unresolved = crosswalk_rows(ledger_dir, schema)
    write_table(ledger_dir, 'status_crosswalk', status, schema=schema)
    write_table(ledger_dir, 'sector_crosswalk', sector, schema=schema)
    # Keep the publisher's exact field value on its line. The crosswalk is
    # optional: a broad label can remain on the line without a CRS code.
    lines = _records(ledger_dir, 'lines', schema)
    by_id = {row['line_id']: row for row in lines}
    # The CIPP mirror has only a host attribution, no publishing party yet;
    # its fields remain in line-fields until authority is resolved.
    with (Path(ledger_dir) / 'line-fields' / 'idn-cipp-2023-cpr-mirror.csv').open(
            encoding='utf-8', newline='') as handle:
        for field in csv.DictReader(handle):
            by_id[field['line_id']]['own_sector'] = None
    for document_id, column in (
        ('zaf-jet-investment-register-q1-2026', 'Portfolios'),
        ('idn-jetp-progress-report-2025', 'technology_group'),
    ):
        path = Path(ledger_dir) / 'line-fields' / f'{document_id}.csv'
        with path.open(encoding='utf-8', newline='') as handle:
            for field in csv.DictReader(handle):
                if field['line_id'] not in by_id:
                    raise ValueError(f'{field["line_id"]}: line missing')
                by_id[field['line_id']]['own_sector'] = field[column] or None
    write_table(ledger_dir, 'lines', lines, schema=schema)
    return len(status), len(sector), unresolved


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--output-dir', type=Path, default=LEDGER_DIR)
    args = parser.parse_args()
    status, sector, unresolved = write_crosswalks(args.output_dir)
    log.info('JETP crosswalks: %d status, %d sector, %d unresolved source labels',
             status, sector, len(unresolved))


if __name__ == '__main__':
    main()
