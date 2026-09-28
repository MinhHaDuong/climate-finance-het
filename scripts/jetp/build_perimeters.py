"""Rebuild the JETP perimeters and their cited aggregate observations (0877).

The unpublished Viet Nam count slots are dispositions, not identities.  Their
two published counts cite the frozen pilot observation rows; no slot is minted.
"""

import argparse
import csv
import io
import logging
from pathlib import Path

from jetp._ledger_headers import (
    LEDGER_DIR,
    file_ceiling,
    load_schema,
    read_table,
    table_files,
    write_table,
)

RECORDED_AT = '2026-09-28'
DECIDED_BY = 'scripts/jetp/build_perimeters.py'

PARTNERSHIPS = {
    'ZAF': ('zaf-jetp', 'South Africa JETP', 'The South Africa Just Energy Transition Partnership'),
    'IDN': ('idn-jetp', 'Indonesia JETP', 'The Indonesia Just Energy Transition Partnership'),
    'VNM': ('vnm-jetp', 'Viet Nam JETP', 'The Viet Nam Just Energy Transition Partnership'),
    'SEN': ('sen-jetp', 'Senegal JETP', 'The Senegal Just Energy Transition Partnership'),
}

# The three additional lines quote collected founding documents.  A locator
# names the paragraph in those exact bytes, rather than a general source URL.
FOUNDING_LINES = (
    ('zaf-jetp-political-declaration-2021', 'ZAF',
     '8726b157774774fd5ec1404668c504593bae573f8809f57419fda155f092ea87',
     'PDF page 3, numbered paragraph 18, initial approximately USD 8.5 billion',
     'Initial approximately USD 8.5 billion to be mobilised over three to five years.'),
    ('idn-jetp-joint-statement-2022', 'IDN',
     '19386c5455eff22d7e82834fda0f7783878899360d135ffa0180a5c8835811ac',
     'Paragraph beginning "The United States has coordinated efforts", USD 20 billion',
     'USD 20 billion in combined resources from public and private partners.'),
    ('sen-political-declaration-fr-2023', 'SEN',
     'eb7c59e93e92427b1c92f430cf991b0eedb0a0d9d7517ca69969771e159ed11a',
     'PDF page 3, paragraph beginning "les membres de l’IPG", EUR 2.5 billion',
     'EUR 2.5 billion of new and additional finance over an initial three to five years.'),
)

# Values are source assertions, not sums of project or agreement rows.
AGGREGATES = (
    ('zaf-founding-pledge', 'ZAF', 'zaf-jetp-political-declaration-2021-0877',
     8_500_000_000, 'USD', 'approximate initial mobilisation pledge'),
    ('zaf-q126-allocated', 'ZAF', 'zaf-jet-quarterly-2026-q1-claim-150',
     6_120_000_000, 'USD', 'allocated across instruments at 2026-03-31; not disbursed'),
    ('idn-founding-pledge', 'IDN', 'idn-jetp-joint-statement-2022-0877',
     20_000_000_000, 'USD', 'combined public and private resources'),
    ('idn-2025-approved', 'IDN', 'idn-jetp-progress-report-2025-claim-3',
     3_100_000_000, 'USD', 'approved programmes and projects; not disbursed'),
    ('vnm-founding-pledge', 'VNM', 'vnm-pilot-observations-local-record-row-1',
     15_500_000_000, 'USD', 'at least; initial mobilisation over three to five years'),
    ('sen-founding-pledge', 'SEN', 'sen-political-declaration-fr-2023-0877',
     2_500_000_000, 'EUR', 'new and additional finance over three to five years'),
)

COUNTS = (
    ('initial', 7, 'vnm-pilot-observations-local-record-row-34',
     'initial projects identified in July 2025'),
    ('screened', 17, 'vnm-pilot-observations-local-record-row-35',
     'new proposals preliminarily screened as JETP-aligned in July 2025'),
)

TIMING_SPECS = (
    ('zaf-founding-pledge', 'report_date', '2021-11-02'),
    ('zaf-q126-allocated', 'reporting_cutoff', '2026-03-31'),
    ('zaf-q126-allocated', 'report_date', '2026-06-26'),
    ('idn-founding-pledge', 'report_date', '2022-11-15'),
    ('idn-2025-approved', 'report_date', '2025-12-02'),
    ('vnm-founding-pledge', 'report_date', '2022-12-14'),
    ('sen-founding-pledge', 'report_date', '2023-06-22'),
)


def table_rows(ledger_dir, table, schema):
    rows, errors = read_table(ledger_dir, table, schema)
    if errors:
        raise ValueError('\n'.join(errors))
    return [dict(zip(schema.header(table), (value or '' for value in row))) for row in rows]


def csv_rows(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def append_new_lines(ledger_dir, rows, schema):
    """Append to each country's last shard without moving existing cited rows."""
    existing = {r['line_id'] for r in table_rows(ledger_dir, 'lines', schema)}
    new = [r for r in rows if r['line_id'] not in existing]
    files, errors = table_files(ledger_dir, 'lines')
    if errors:
        raise ValueError('\n'.join(errors))
    header = schema.header('lines')
    ceiling = file_ceiling()
    additions = {}
    for row in new:
        candidates = [path for path, country, year in files
                      if country == row['country'] and year == row['recorded_at'][:4]]
        if not candidates:
            raise ValueError(f'no existing country-year line shard for {row["line_id"]}')
        path = candidates[-1]
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator='\n')
        writer.writerow([row.get(col, '') for col in header])
        additions.setdefault(path, []).append(buffer.getvalue())
    for path, pieces in additions.items():
        if path.stat().st_size + len(''.join(pieces).encode('utf-8')) > ceiling:
            raise ValueError(f'last line shard is full: {path}')
    for path, pieces in additions.items():
        with path.open('a', encoding='utf-8', newline='') as handle:
            handle.write(''.join(pieces))


def merge_rows(current, added, key, prefix='0877.'):
    kept = [row for row in current if not row[key].startswith(prefix)]
    ids = {row[key] for row in kept}
    for row in added:
        if row[key] in ids:
            raise ValueError(f'duplicate {key}: {row[key]}')
        ids.add(row[key])
    return kept + added


def ruptl_memberships(plan_rows, routes, line_ids, expected_count=230):
    """Attach only source-marked, plan-only CIPP lines to their plan perimeter."""
    marked = [r for r in plan_rows if r['country'] == 'IDN' and r['ruptl'] == 'YES'
              and r['reconciliation_status'] == 'plan_only']
    if len(marked) != expected_count:
        raise ValueError(f'expected {expected_count} plan-only RUPTL rows, found {len(marked)}')
    result = []
    for plan in marked:
        line_id = routes.get(plan['plan_project_id'])
        if line_id not in line_ids:
            raise ValueError(f'RUPTL row lacks routed line: {plan["plan_project_id"]}')
        result.append(dict(
            relation_id=f'0877.ruptl.{plan["plan_project_id"]}',
            from_kind='line', from_id=line_id, relation='member_of',
            to_kind='perimeter', to_id='idn-cipp-ruptl-plan-lines',
            status='accepted', method='source_ruptl_flag', method_version='1',
            decided_at=RECORDED_AT, decided_by=DECIDED_BY, line_id=line_id))
    return result


def build_rows(ledger_dir, schema=None):
    """Return complete replacement rows for the five tables this step owns."""
    ledger_dir = Path(ledger_dir)
    schema = schema or load_schema()
    lines = table_rows(ledger_dir, 'lines', schema)
    snapshots = {row['sha256'] for row in table_rows(ledger_dir, 'snapshots', schema)}
    line_ids = {row['line_id'] for row in lines}
    added_lines = []
    for document, country, sha, locator, label in FOUNDING_LINES:
        if sha not in snapshots:
            raise ValueError(f'founding snapshot missing: {document} {sha}')
        line_id = f'{document}-0877'
        if line_id in line_ids:
            continue
        added_lines.append(dict(line_id=line_id, country=country, sha256=sha,
                                locator=locator, ordinal=1, label=label,
                                classification='envelope', recorded_at=RECORDED_AT,
                                notes='Cited founding declaration; approximate or conditional wording retained.'))
    lines = merge_rows(lines, added_lines, 'line_id')
    line_ids = {row['line_id'] for row in lines}

    perimeters = table_rows(ledger_dir, 'perimeters', schema)
    added_perimeters = [dict(perimeter_row_id=f'0877.{ident}', perimeter_id=ident,
                             country=country, name=name, scope='partnership',
                             definition=definition, recorded_at=RECORDED_AT,
                             decided_by=DECIDED_BY, status='accepted')
                        for country, (ident, name, definition) in PARTNERSHIPS.items()]
    added_perimeters.append(dict(
        perimeter_row_id='0877.idn-cipp-ruptl-plan-lines',
        perimeter_id='idn-cipp-ruptl-plan-lines', country='IDN',
        name='CIPP plan-only lines marked RUPTL', scope='plan_lines',
        definition='The 230 Indonesia CIPP plan-only lines whose source row marks RUPTL=YES; '
                   'this is not the full RUPTL inventory.', recorded_at=RECORDED_AT,
        decided_by=DECIDED_BY, status='accepted'))
    perimeters = merge_rows(perimeters, added_perimeters, 'perimeter_row_id')
    perimeter_ids = {row['perimeter_id'] for row in perimeters}
    if 'vnm-jetp-portfolio-2025' not in perimeter_ids:
        raise ValueError('Viet Nam portfolio perimeter from 0880 is missing')

    observations = table_rows(ledger_dir, 'observations', schema)
    added_observations = []
    for suffix, country, line_id, value, currency, note in AGGREGATES:
        if line_id not in line_ids:
            raise ValueError(f'aggregate lacks cited line: {line_id}')
        added_observations.append(dict(
            observation_id=f'0877.{suffix}', subject_kind='perimeter',
            subject_id=PARTNERSHIPS[country][0], axis='money', measure='envelope',
            basis='unknown', value=value, unit=currency, currency=currency,
            line_id=line_id, method='source_aggregate', method_version='1',
            recorded_at=RECORDED_AT, status='accepted', notes=note))
    for suffix, value, line_id, note in COUNTS:
        if line_id not in line_ids:
            raise ValueError(f'count lacks cited line: {line_id}')
        added_observations.append(dict(
            observation_id=f'0877.vnm-2025-{suffix}-count', subject_kind='perimeter',
            subject_id='vnm-jetp-portfolio-2025', measure='count', value=value,
            unit='proposals', line_id=line_id, method='source_count',
            method_version='1', recorded_at=RECORDED_AT, status='accepted', notes=note))
    observations = merge_rows(observations, added_observations, 'observation_id')
    new_by_id = {r['observation_id']: r for r in added_observations}
    timings = table_rows(ledger_dir, 'timings', schema)
    added_timings = []
    for suffix, role, date in TIMING_SPECS:
        observation = new_by_id[f'0877.{suffix}']
        added_timings.append(dict(
            timing_id=f'0877.{suffix}.{role}', observation_id=observation['observation_id'],
            date_role=role, date=date, date_precision='day',
            lower_bound=date, upper_bound=date, line_id=observation['line_id'],
            recorded_at=RECORDED_AT))
    for suffix, _, _, _ in COUNTS:
        observation = new_by_id[f'0877.vnm-2025-{suffix}-count']
        added_timings.append(dict(
            timing_id=f'0877.vnm-2025-{suffix}-count.reporting_cutoff',
            observation_id=observation['observation_id'],
            date_role='reporting_cutoff', date_precision='month',
            lower_bound='2025-07-01', upper_bound='2025-07-31',
            line_id=observation['line_id'], recorded_at=RECORDED_AT))
    timings = merge_rows(timings, added_timings, 'timing_id')

    relations = table_rows(ledger_dir, 'relations', schema)
    plan_rows = csv_rows(ledger_dir / 'plan-projects.csv')
    routes = {r['old_id']: r['new_id'] for r in table_rows(ledger_dir, 'routes', schema)
              if r['kind'] == 'line'}
    added_relations = ruptl_memberships(plan_rows, routes, line_ids)
    # Agreements in the two official registers have an accepted line-referent
    # row.  Membership says where the source reports them, not that they count
    # as paid finance or are distinct from every other agreement.
    referents = table_rows(ledger_dir, 'line_referents', schema)
    agreements = {r['agreement_id']: r for r in table_rows(ledger_dir, 'agreements', schema)}
    for ref in referents:
        if ref['referent_kind'] != 'agreement' or ref['status'] != 'accepted':
            continue
        agreement = agreements.get(ref['referent_id'])
        if agreement is None or agreement['country'] not in ('ZAF', 'IDN'):
            continue
        added_relations.append(dict(
            relation_id=f'0877.partnership.{ref["referent_id"]}',
            from_kind='agreement', from_id=ref['referent_id'], relation='member_of',
            to_kind='perimeter', to_id=PARTNERSHIPS[agreement['country']][0],
            status='accepted', method='accepted_register_referent', method_version='1',
            decided_at=RECORDED_AT, decided_by=DECIDED_BY, line_id=ref['line_id']))
    relations = merge_rows(relations, added_relations, 'relation_id')
    return {'lines': lines, 'perimeters': perimeters,
            'observations': observations, 'timings': timings,
            'relations': relations}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER_DIR)
    parser.add_argument('--output', type=Path,
                        help='existing ledger directory to update in place')
    args = parser.parse_args(argv)
    rows = build_rows(args.ledger_dir)
    if args.output:
        if args.output.resolve() != args.ledger_dir.resolve():
            raise ValueError('--output must name --ledger-dir for this in-place migration')
        schema = load_schema()
        append_new_lines(args.ledger_dir, rows['lines'], schema)
        for table in ('perimeters', 'observations', 'timings', 'relations'):
            write_table(args.ledger_dir, table, rows[table], schema=schema)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    logging.info('perimeter migration: %s',
                 ' '.join(f'{table}={len(rows[table])}' for table in rows))


if __name__ == '__main__':
    main()
