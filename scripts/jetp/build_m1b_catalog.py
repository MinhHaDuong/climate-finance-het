"""Publish the bounded M1b catalogue without rerunning matching or editing D2.

One invocation writes country views and their release descriptor, hence the
multi-output --output-dir interface. The DDL validates a disposable SQLite;
every identity and relation is projected from its terminal decision rows.
"""

import argparse
import csv
import hashlib
import json
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path

from utils import get_logger

from jetp._ledger_headers import ONTOLOGY_TABLES, file_stem, load_schema
from jetp._ontology import ontology_as_of, ontology_ref
from jetp.build_ledger import build

log = get_logger('jetp.build_m1b_catalog')
ROOT = Path(__file__).resolve().parents[2]
KINDS = {'project': ('projects', 'project_id'), 'asset': ('assets', 'asset_id'),
         'agreement': ('agreements', 'agreement_id'), 'party': ('parties', 'party_id')}


def records(conn, query, parameters=()):
    return [dict(row) for row in conn.execute(query, parameters)]


def terminal(conn, table, key):
    return records(conn, f'SELECT d.* FROM {table} AS d WHERE NOT EXISTS '
                   f'(SELECT 1 FROM {table} AS s WHERE s.supersedes = d.{key}) ORDER BY d.{key}')


def _justification(row, lines, key):
    """Accepted decisions must name an existing line and their deciding method."""
    cited = row.get('justification_line_ids') or row.get('line_id')
    if not cited or cited not in lines:
        raise ValueError(f'{row[key]}: missing justification line {cited!r}')
    if not row.get('method') or not row.get('decided_by') or not row.get('decided_at'):
        raise ValueError(f'{row[key]}: incomplete decision record')
    return cited


def _party_name(conn, identity, lines, justification_ids):
    names = records(conn, "SELECT * FROM party_names_in_force WHERE party_id = ? "
                    "AND form_type = 'preferred'", (identity,))
    if len(names) != 1:
        raise ValueError(f'missing preferred-name justification for party:{identity}')
    line_id = names[0]['line_id']
    if line_id:
        if line_id not in lines:
            raise ValueError(f'missing party-name justification line {line_id}')
        justification_ids.add(line_id)
    return names[0]


def catalog_country(conn, country, scope_line_ids, document_ids):
    """A country's exact frozen inventory, with pending decisions kept separate.

    Relations belong here when they cite a scoped line or name a scoped line,
    referent or document. Thus a pending party alias stays visible beside the
    funder without merging their identities or manufacturing justification.
    """
    lines = {row['line_id']: row for row in records(conn, 'SELECT * FROM lines')}
    links = [row for row in terminal(conn, 'line_referents', 'referent_row_id')
             if row['line_id'] in scope_line_ids and row['referent_kind'] in KINDS]
    accepted_links = [row for row in links if row['status'] == 'accepted']
    candidate_links = [row for row in links if row['status'] == 'candidate']
    identities = {(row['referent_kind'], row['referent_id']) for row in accepted_links}

    def related(row):
        return (row['line_id'] in scope_line_ids or any(
            (row[f'{side}_kind'] == 'line' and row[f'{side}_id'] in scope_line_ids)
            or (row[f'{side}_kind'], row[f'{side}_id']) in identities
            or (row[f'{side}_kind'] == 'document' and row[f'{side}_id'] in document_ids)
            for side in ('from', 'to')))

    def grounded(row):
        return row['line_id'] in scope_line_ids or any(
            row[f'{side}_kind'] == 'line' and row[f'{side}_id'] in scope_line_ids
            for side in ('from', 'to'))

    all_relations = terminal(conn, 'relations', 'relation_id')
    relations = [row for row in all_relations if
                 (grounded(row) if row['status'] == 'accepted' else related(row))]
    accepted_relations = [row for row in relations if row['status'] == 'accepted']
    party_relations = [row for row in accepted_relations if row['relation'] in ('party_in', 'role_in')]
    party_ids = {row[f'{side}_id'] for row in party_relations for side in ('from', 'to')
                 if row[f'{side}_kind'] == 'party'}
    identities |= {('party', identity) for identity in party_ids}
    # A party's other accepted roles elsewhere do not widen the frozen scope.
    # Its pending aliases are relevant here, but remain entirely out of force.
    candidate_ids = {row['relation_id'] for row in relations}
    relations += [row for row in all_relations if row['status'] == 'candidate'
                  and row['relation_id'] not in candidate_ids and any(
                      row[f'{side}_kind'] == 'party' and row[f'{side}_id'] in party_ids
                      for side in ('from', 'to'))]
    candidate_relations = [row for row in relations if row['status'] == 'candidate']
    justification_ids = set()
    for row in accepted_links:
        justification_ids.add(_justification(row, lines, 'referent_row_id'))
    for row in accepted_relations:
        justification_ids.add(_justification(row, lines, 'relation_id'))
        for side in ('from', 'to'):
            if row[f'{side}_kind'] == 'line':
                line_id = row[f'{side}_id']
                if line_id not in lines:
                    raise ValueError(f"{row['relation_id']}: missing justification endpoint {line_id}")
                justification_ids.add(line_id)

    # Party endpoints are justified by a scoped role decision and their
    # accepted preferred-name record, following the register's party exception.
    referents = []
    for kind, identity in sorted(identities):
        table, key = KINDS[kind]
        rows = records(conn, f'SELECT * FROM {table} WHERE {key} = ?', (identity,))
        if len(rows) != 1:
            raise ValueError(f'missing accepted referent {kind}:{identity}')
        record = rows[0]
        name = record.get('canonical_name') or record.get('name')
        if kind == 'party':
            name_record = _party_name(conn, identity, lines, justification_ids)
            name = name_record['name']
        if not name:
            name = next((lines[row['line_id']]['label'] for row in accepted_links
                         if row['referent_kind'] == kind and row['referent_id'] == identity), identity)
        decisions = [row for row in accepted_links
                     if row['referent_kind'] == kind and row['referent_id'] == identity]
        referents.append({'kind': kind, 'id': identity, 'name': name, 'record': record,
                          'decision_ids': [row['referent_row_id'] for row in decisions],
                          'line_ids': sorted({row['line_id'] for row in decisions})})
        if kind == 'party':
            roles = [row for row in party_relations if any(
                row[f'{side}_kind'] == 'party' and row[f'{side}_id'] == identity
                for side in ('from', 'to'))]
            referents[-1].update(name_record=name_record,
                                 relation_decision_ids=[row['relation_id'] for row in roles],
                                 line_ids=sorted({row['line_id'] for row in roles}),
                                 evidence_country=country)

    cited_ids = justification_ids | {row['line_id'] for row in links}
    cited_ids |= {row['line_id'] for row in candidate_relations if row['line_id']}
    for row in candidate_relations:
        cited_ids |= {row[f'{side}_id'] for side in ('from', 'to') if row[f'{side}_kind'] == 'line'}
    accepted_line_ids = {row['line_id'] for row in accepted_links}
    candidate_line_ids = {row['line_id'] for row in candidate_links} - accepted_line_ids
    return {
        'country': country,
        'scope_line_ids': sorted(scope_line_ids),
        'counts': {'unit': 'referents by kind; candidates by decision table and relation',
                   'referents': {kind: sum(row['kind'] == kind for row in referents) for kind in KINDS},
                   'lines': len(scope_line_ids), 'lines_with_accepted_referent': len(accepted_line_ids),
                   'lines_with_candidate_only': len(candidate_line_ids),
                   'lines_without_referent': len(scope_line_ids - accepted_line_ids - candidate_line_ids),
                   'accepted_relations': dict(sorted(Counter(row['relation'] for row in accepted_relations).items())),
                   'candidate_relations': dict(sorted(Counter(row['relation'] for row in candidate_relations).items())),
                   'candidate_referents': dict(sorted(Counter(row['referent_kind'] for row in candidate_links).items()))},
        'referents': referents,
        'decisions': accepted_links,
        'relations': accepted_relations,
        'candidates': {'in_force': False, 'line_referents': candidate_links, 'relations': candidate_relations},
        'unresolved_line_ids': sorted(scope_line_ids - accepted_line_ids - candidate_line_ids),
        'lines': [lines[line_id] for line_id in sorted(cited_ids) if line_id in lines],
    }


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path, payload):
    path.write_bytes(_bytes(payload))


def _bytes(payload):
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':')) + '\n').encode('utf-8')


def pack_view(view):
    """Column-oriented JSON keeps each country below the repository ceiling."""
    def table(rows):
        fields = sorted({key for row in rows for key in row})
        return {'fields': fields, 'rows': [[row.get(key) for key in fields] for row in rows]}
    result = dict(view)
    result['referent_records'] = {kind: table([row['record'] for row in view['referents']
                                             if row['kind'] == kind]) for kind in KINDS}
    positions = Counter()
    result['referents'] = []
    for row in view['referents']:
        record = {key: value for key, value in row.items() if key != 'record'}
        record['record_index'] = positions[row['kind']]
        positions[row['kind']] += 1
        result['referents'].append(record)
    for name in ('decisions', 'relations', 'lines'):
        result[name] = table(view[name])
    result['candidates'] = {'in_force': False,
                            'line_referents': table(view['candidates']['line_referents']),
                            'relations': table(view['candidates']['relations'])}
    return result


def coverage_dispositions(ledger_dir):
    """Keep the 17 handed-over legacy identifiers as recorded dispositions."""
    paths = [ledger_dir / 'migration/0884-coverage-dispositions.csv',
             ledger_dir / 'migration/1620-register-dispositions.csv']
    with paths[0].open(newline='', encoding='utf-8') as stream:
        legacy = [row for row in csv.DictReader(stream) if row['source_table'] == 'project-coverage.csv']
    with paths[1].open(newline='', encoding='utf-8') as stream:
        ownership = {row['row_key']: row for row in csv.DictReader(stream)
                     if row['register'] == '0884-coverage-dispositions' and row['owner'] == '0833'}
    if len(legacy) != 17 or set(ownership) != {row['old_id'] for row in legacy}:
        raise ValueError('M1b requires the 17 recorded coverage dispositions and their ownership records')
    review_path = ledger_dir / 'migration/0833-coverage-reviews.json'
    review = json.loads(review_path.read_text())
    outcomes = {row['legacy_id']: row for row in review['decisions']}
    if set(outcomes) != set(ownership):
        raise ValueError('Every handed-over coverage identifier needs an explicit M1b review outcome')
    related_path = ledger_dir / 'migration/0970-event-adjudications.csv'
    with related_path.open(newline='', encoding='utf-8') as stream:
        related = list(csv.DictReader(stream))
    return [{'legacy_id': row['old_id'], 'disposition': outcomes[row['old_id']]['outcome'],
             'detail': outcomes[row['old_id']]['basis'],
             'decision': {**outcomes[row['old_id']], 'method': review['method'],
                          'method_version': review['method_version'], 'reviewed_by': review['reviewed_by'],
                          'reviewed_at': review['reviewed_at']},
             'inherited_disposition': row['disposition'], 'ownership_decision': ownership[row['old_id']],
             'related_records': [record for record in related if record['legacy_project_id'] == row['old_id']],
             'in_force': False, 'catalogue_effect': 'no identity minted from a legacy coverage identifier'}
            for row in legacy], [*paths, review_path, related_path, ledger_dir / 'migration/0875-dispositions.csv']


def candidate_reviews(ledger_dir):
    path = ledger_dir / 'migration/0833-candidate-reviews.csv'
    with path.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    keys = [row['relation_id'] or row['referent_row_id'] for row in rows]
    if len(set(keys)) != len(keys) or any(not row['basis'] or not row['reviewed_by'] for row in rows):
        raise ValueError('Candidate reviews require unique decision targets and a reviewer/basis')
    return dict(zip(keys, rows)), path


def check_catalog(root, output_dir):
    """Check the frozen artifact, independent of today's ledger and ontology."""
    root, output_dir = Path(root), Path(output_dir)
    release = json.loads((root / 'config/jetp-m1b-release.json').read_text())
    descriptor = json.loads((output_dir / 'manifest.json').read_text())
    if descriptor['ontology']['ontology_ref'] != release['ontology_ref']:
        raise ValueError('M1b artifact does not cite frozen O v1')
    for country, item in descriptor['countries'].items():
        for filename, checksum in [('file', 'sha256'), ('decisions_file', 'decisions_sha256')]:
            path = output_dir / item[filename]
            if path.parent != output_dir or not path.is_file() or _digest(path) != item[checksum]:
                raise ValueError(f'M1b artifact hash mismatch: {country}/{filename}')
    return descriptor


def write_catalog(root, output_dir):
    root, output_dir = Path(root), Path(output_dir)
    ledger_dir = root / 'data/jetp'
    if output_dir.resolve().is_relative_to(ledger_dir.resolve()):
        raise ValueError('The derived catalogue output must be outside the input ledger')
    ddl_path = root / 'config/jetp-ledger.sql'
    config_path = root / 'config/jetp-m1a-inventories.json'
    release_path = root / 'config/jetp-m1b-release.json'
    release = json.loads(release_path.read_text())
    current_ontology_ref = ontology_ref(ledger_dir, ddl_path)
    if current_ontology_ref != release['ontology_ref']:
        raise ValueError('Frozen O v1 changed; reproduce M1b from its recorded ontology inputs')
    specifications = json.loads(config_path.read_text())['layers']
    descriptor = {'schema_version': 'jetp-m1b-catalog/1', 'release_id': release['release_id'],
                  'scope': 'four frozen M1a inventories, six document snapshots; no matching rerun',
                  'review': {'budget': release['review_budget'],
                             'disposition': 'unverified proposals remain candidates, not in force'},
                  'ontology': {'release_id': release['ontology_release_id'], 'ontology_ref': current_ontology_ref},
                  'countries': {}, 'inputs': {}}
    schema = load_schema(ddl_path)
    ontology = ontology_as_of(ledger_dir, schema=schema)
    descriptor['ontology']['in_force'] = {
        file_stem(table): sorted(row[schema.keys[table][0]] for row in ontology[table])
        for table in ONTOLOGY_TABLES}
    # Explicit consumed inputs, including code: no clock or checkout-dependent
    # Git revision enters the bytes of this reproducible release descriptor.
    inputs = [ddl_path, config_path, release_path, root / '.githooks/pre-commit',
              root / 'scripts/jetp/build_m1b_catalog.py',
              root / 'scripts/jetp/build_ledger.py', root / 'scripts/jetp/_ledger_headers.py',
              root / 'scripts/jetp/_ontology.py']
    inputs += sorted(ledger_dir.glob('*.csv'))
    inputs += sorted(ledger_dir.glob('*.d/*.csv'))
    inputs += sorted((ledger_dir / 'ontology').rglob('*.csv'))
    inputs += sorted((ledger_dir / 'line-fields').glob('*.csv'))
    dispositions, disposition_paths = coverage_dispositions(ledger_dir)
    reviews, review_path = candidate_reviews(ledger_dir)
    inputs += disposition_paths
    inputs.append(review_path)
    descriptor['review']['excluded_candidates'] = [row for row in reviews.values()
                                                  if row['status'] == 'outside_m1a_review_scope']
    descriptor['inputs'] = {path.relative_to(root).as_posix(): _digest(path) for path in inputs}
    payloads = {}
    with tempfile.TemporaryDirectory() as temporary:
        database = Path(temporary) / 'ledger.sqlite'
        errors = build(ledger_dir, database, ddl_path)
        if errors:
            raise ValueError('; '.join(errors))
        with sqlite3.connect(database) as conn:
            conn.row_factory = sqlite3.Row
            for country in ('ZAF', 'IDN', 'VNM', 'SEN'):
                scope, documents = set(), set()
                layers = [spec for spec in specifications if spec['country'] == country]
                for spec in layers:
                    document_id = spec['source_id']
                    field_path = ledger_dir / 'line-fields' / f'{document_id}.csv'
                    # The per-document fields table is the extraction boundary;
                    # later prose with the same snapshot never enters M1b.
                    with field_path.open(newline='', encoding='utf-8') as stream:
                        field_ids = {row['line_id'] for row in csv.DictReader(stream)}
                    members = {row['line_id'] for row in conn.execute(
                        'SELECT line_id FROM lines WHERE sha256 = ?', (spec['source_sha256'],))
                        if row['line_id'].startswith(document_id + '-') and row['line_id'] in field_ids}
                    if len(members) != spec['expected_rows']:
                        raise ValueError(f'frozen M1a membership changed: {document_id}')
                    scope |= members
                    documents.add(document_id)
                view = catalog_country(conn, country, scope, documents)
                for row in [*view['candidates']['relations'], *view['candidates']['line_referents']]:
                    key = row.get('relation_id') or row['referent_row_id']
                    if key not in reviews or reviews[key]['status'] != 'retain_candidate':
                        raise ValueError(f'Visible candidate needs a retained-candidate review: {key}')
                    row['review'] = reviews[key]
                view['legacy_coverage_dispositions'] = [row for row in dispositions
                                                       if row['legacy_id'].split('-')[0].upper() == country]
                for disposition in view['legacy_coverage_dispositions']:
                    for related in disposition['related_records']:
                        related['scope'] = 'within_m1a' if related['line_id'] in scope else 'outside_m1a'
                        related['accepted_decision_ids'] = [row['referent_row_id'] for row in
                            terminal(conn, 'line_referents', 'referent_row_id')
                            if row['status'] == 'accepted' and row['line_id'] == related['line_id']
                            and row['referent_id'] == related['referent_id']]
                    pairs = {(row['referent_kind'], row['referent_id'])
                             for row in disposition['related_records'] if row['accepted_decision_ids']}
                    disposition['related_mapping'] = ('one_to_one_related_referent' if len(pairs) == 1
                                                       else 'one_to_many_related_referents' if len(pairs) > 1
                                                       else 'no_related_accepted_referent')
                packed = pack_view(view)
                decision_tables = {key: packed.pop(key) for key in ('decisions', 'relations', 'candidates')}
                decision_payload = _bytes(decision_tables)
                payload = _bytes(packed)
                if max(len(payload), len(decision_payload)) > 512000:
                    raise ValueError(f'{country} catalogue exceeds repository file ceiling')
                payloads[f'{country}.json'] = payload
                payloads[f'{country}-decisions.json'] = decision_payload
                descriptor['countries'][country] = {'file': f'{country}.json',
                                                    'sha256': hashlib.sha256(payload).hexdigest(),
                                                    'decisions_file': f'{country}-decisions.json',
                                                    'decisions_sha256': hashlib.sha256(decision_payload).hexdigest(),
                                                    'counts': view['counts'],
                                                    'documents': sorted(documents)}
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        (output_dir / name).write_bytes(payload)
    _write(output_dir / 'manifest.json', descriptor)
    log.info('M1b catalogue written to %s (%s)', output_dir, descriptor['ontology']['ontology_ref'])
    return descriptor


def main():
    # Multi-output catalogue: country files plus the release descriptor.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--check', action='store_true', help='validate frozen artifact hashes only')
    args = parser.parse_args()
    if args.check:
        check_catalog(args.root, args.output_dir)
    else:
        write_catalog(args.root, args.output_dir)


if __name__ == '__main__':
    main()
