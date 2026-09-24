"""Migrate the legacy coverage registers into the ledger's ``coverage`` table.

The two old files remain inputs until ticket 0878 retires their compatibility
readers.  Project identifiers are resolved through ``routes`` where available
and through the identity-split disposition register otherwise; a count slot
therefore remains coverage of its perimeter rather than becoming a project.
Authority rows can be attached only to an existing party.  Ambiguous and
unresolved source rows are written to the migration disposition register so a
review is visible rather than silently manufacturing an identity.
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

from jetp._ledger_headers import load_schema, read_table, write_table


def _rows(ledger_dir, table):
    schema = load_schema()
    rows, errors = read_table(ledger_dir, table, schema)
    if errors:
        raise ValueError(errors[0])
    return [dict(zip(schema.header(table), row)) for row in rows]


def _legacy_rows(path):
    with Path(path).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def _name_key(value):
    return re.sub(r'[^a-z0-9]+', '', value.lower().removeprefix('the '))


def build(ledger_dir):
    """Return coverage, unresolved dispositions, and one reconciliation row per input."""
    ledger_dir = Path(ledger_dir)
    routes = {row['old_id']: (row['kind'], row['new_id'])
              for row in _rows(ledger_dir, 'routes')}
    # 0875 deliberately did not put unpublished project identifiers in routes:
    # their decisions are recorded here, including the VNM count-slot perimeter.
    split = {row['old_id']: row for row in _legacy_rows(
        ledger_dir / 'migration/0875-dispositions.csv')}
    parties = {row['party_id'] for row in _rows(ledger_dir, 'parties')}
    names = defaultdict(set)
    for row in _rows(ledger_dir, 'party_names'):
        names[_name_key(row['name'])].add(row['party_id'])

    coverage, dispositions, reconciliation = [], [], []
    by_referent = {}

    def add(kind, identity, *, review_status, checked_at, route, document_ids, notes):
        key = (kind, identity)
        previous = by_referent.get(key)
        if previous is None:
            previous = dict(referent_kind=kind, referent_id=identity,
                            review_status=review_status, checked_at=checked_at,
                            route=route, document_ids=document_ids, notes=notes)
            by_referent[key] = previous
            coverage.append(previous)
            return
        if previous['review_status'] != review_status:
            # A party can occur in more than one national authority register.
            # The key deliberately has no country, so retain the older verdict
            # in the note and let the most recently checked row be the table's
            # current review status.
            prior_status = previous['review_status']
            previous['notes'] = f"Review status {prior_status}: {previous['notes']}"
            notes = f'Review status {review_status}: {notes}'
            if checked_at >= previous['checked_at']:
                previous['review_status'] = review_status
        for field, separator in (('document_ids', ';'), ('route', ' | '), ('notes', ' | ')):
            values = [segment for value in (previous[field], locals()[field]) if value
                      for segment in value.split(separator)]
            previous[field] = separator.join(dict.fromkeys(values))
        previous['checked_at'] = max(previous['checked_at'], checked_at)

    for row in _legacy_rows(ledger_dir / 'project-coverage.csv'):
        resolved = routes.get(row['project_id'])
        if resolved is None:
            decision = split.get(row['project_id'])
            if decision and decision['new_id'] and ';' not in decision['new_id']:
                resolved = (decision['disposition'], decision['new_id'])
        if resolved is None:
            dispositions.append(dict(source_table='project-coverage.csv', old_id=row['project_id'],
                                     disposition='no_referent', detail='0875 has no resolved identity'))
            reconciliation.append(dict(source_table='project-coverage.csv', old_id=row['project_id'],
                                       outcome='disposition', referent_kind='', referent_id='',
                                       detail='0875 has no resolved identity'))
            continue
        add(*resolved, review_status=row['review_status'], checked_at=row['checked_at'],
            route=row['query_or_route'], document_ids=row['source_ids'], notes=row['notes'])
        reconciliation.append(dict(source_table='project-coverage.csv', old_id=row['project_id'],
                                   outcome='coverage', referent_kind=resolved[0], referent_id=resolved[1], detail=''))

    for row in _legacy_rows(ledger_dir / 'authority-coverage.csv'):
        candidates = {row['authority_id']} & parties
        candidates |= names[_name_key(row['authority'])]
        if len(candidates) != 1:
            detail = 'no matching party name' if not candidates else 'ambiguous party names: ' + ';'.join(sorted(candidates))
            dispositions.append(dict(source_table='authority-coverage.csv', old_id=row['authority_id'],
                                     disposition='no_referent', detail=detail))
            reconciliation.append(dict(source_table='authority-coverage.csv', old_id=row['authority_id'],
                                       outcome='disposition', referent_kind='', referent_id='', detail=detail))
            continue
        party_id = candidates.pop()
        add('party', party_id, review_status=row['verdict'], checked_at=row['checked_at'],
            route='', document_ids=row['source_ids'], notes=row['notes'])
        reconciliation.append(dict(source_table='authority-coverage.csv', old_id=row['authority_id'],
                                   outcome='coverage', referent_kind='party', referent_id=party_id, detail=''))
    return sorted(coverage, key=lambda row: (row['referent_kind'], row['referent_id'])), dispositions, reconciliation


def write(ledger_dir, output):
    coverage, dispositions, reconciliation = build(ledger_dir)
    write_table(ledger_dir, 'coverage', coverage)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=('source_table', 'old_id', 'disposition', 'detail'),
                                lineterminator='\n')
        writer.writeheader()
        writer.writerows(dispositions)
    reconciliation_path = output.with_name('0884-coverage-reconciliation.csv')
    with reconciliation_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=('source_table', 'old_id', 'outcome',
                                                     'referent_kind', 'referent_id', 'detail'),
                                lineterminator='\n')
        writer.writeheader()
        writer.writerows(reconciliation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True,
                        help='migration disposition CSV')
    args = parser.parse_args()
    write(args.ledger_dir, args.output)


if __name__ == '__main__':
    main()
