"""Split the legacy JETP project register into justified identities (0875).

This is a one-time, deterministic migration.  The legacy register is retained
under ``migration/`` for the site's compatibility reader until ticket 0878.
Only an existing source line can mint an identity.  Unresolved legacy labels
stay in the disposition report, never as invented projects or public routes.
"""

import argparse
import csv
import hashlib
import io
import itertools
import json
import logging
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from jetp._evidence_layer_rules import name_key, slug
from jetp._ledger_headers import LEDGER_DIR, load_schema, read_table, write_table

RECORDED_AT = '2026-09-24'
DECIDED_BY = 'scripts/jetp/build_reconciliation.py'
LEGACY = Path('migration/0875-projects-legacy.csv')


def csv_rows(path):
    with Path(path).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def table_rows(ledger, table, schema):
    rows, errors = read_table(ledger, table, schema)
    if errors:
        raise ValueError('; '.join(errors))
    return [dict(zip(schema.header(table), row)) for row in rows]


def label_key(value):
    text = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '', text.lower())


def _line_index(lines):
    by_name, by_legacy, by_document, by_id = defaultdict(list), defaultdict(list), defaultdict(list), {}
    for line in lines:
        by_id[line['line_id']] = line
        by_name[line['country'], label_key(line['label'])].append(line)
        for match in re.findall(r'(?:^|; )legacy_project_id=([^;]+)', line['notes'] or ''):
            by_legacy[match].append(line)
        by_document[line['line_id'].rsplit('-', 2)[0]].append(line)
    return by_name, by_legacy, by_document, by_id


def _basis(row, lines, plans, candidates, by_name, by_legacy):
    """Choose only an explicit or unique exact line; do not promote fuzzy hits."""
    old_id = row['project_id']
    if row['verification_status'] == 'official_register':
        # The old slug removed punctuation and lowercased the register's key.
        # The note retains the publisher's actual ID (FP001.1, GR014b, …).
        match = re.search(r'official register id=([^;]+)', row['notes'])
        suffix = match.group(1) if match else old_id.removeprefix('zaf-register-').upper()
        matching = [line for line in lines if line['country'] == 'ZAF' and
                    line['classification'] == 'register_allocation' and
                    line['locator'].endswith('Unique ID ' + suffix)]
        if len(matching) == 1:
            return matching[0], 'register_id'
    explicit = by_legacy[old_id]
    if explicit:
        return sorted(explicit, key=lambda x: x['line_id'])[0], 'legacy_project_id'
    plan_lines = [line for plan in plans if plan['canonical_project_id'] == old_id
                  for line in lines if line['country'] == plan['country'] and
                  line['label'] == plan['project_name'] and
                  line['line_id'].startswith(plan['source_id'] + '-')]
    if plan_lines:
        return sorted(plan_lines, key=lambda x: x['line_id'])[0], 'reviewed_plan_match'
    exact = by_name[row['country'], label_key(row['canonical_name'])]
    if len(exact) == 1 and exact[0]['classification'] in ('named_item', 'submission'):
        return exact[0], 'exact_label'
    # 0874 retained the old links as candidates, including those without a
    # collected snapshot.  A single-line document with a confirmed match is
    # usable; a multi-line document is not narrowed by a document-level link.
    for candidate in sorted(candidates[old_id], key=lambda x: x['link_id']):
        if candidate['review_status'] != 'confirmed':
            continue
        document_lines = [line for line in lines if line['line_id'].startswith(
            candidate['source_id'] + '-')]
        if candidate['line_id']:
            document_lines = [line for line in document_lines if
                              line['line_id'] == candidate['line_id']]
        if len(document_lines) == 1 and document_lines[0]['classification'] == 'named_item':
            return document_lines[0], 'confirmed_document_link'
    return None, 'no_precise_line'


def disposition(row):
    old_id, status = row['project_id'], row['verification_status']
    if status == 'official_register':
        return 'agreement'
    if status == 'official_count_slot':
        return 'perimeter'
    if status == 'official_programme':
        return 'line'
    if old_id.startswith('idn-grant-') or old_id.startswith('idn-fin-'):
        return 'agreement'
    if old_id.startswith('idn-monitor-'):
        return 'line'
    if old_id == 'idn-pipe-cirebon-1-retirement':
        return 'asset'
    return 'project'


def _referent(line, kind, identity, method):
    return dict(referent_row_id=f'0875.{kind}.{identity}', line_id=line['line_id'],
                referent_kind=kind, referent_id=identity, status='accepted',
                method=method, method_version='1', confidence=1,
                justification_line_ids=line['line_id'], decided_at=RECORDED_AT,
                decided_by=DECIDED_BY)


def _relation(identifier, from_kind, from_id, relation, to_kind, to_id, line_id,
              role=None, status='accepted', method='reviewed_source'):
    return dict(relation_id=identifier, from_kind=from_kind, from_id=from_id,
                relation=relation, to_kind=to_kind, to_id=to_id, role=role,
                status=status, method=method, method_version='1',
                confidence=1 if status == 'accepted' else 0.5,
                decided_at=RECORDED_AT, decided_by=DECIDED_BY, line_id=line_id)


def tier2_candidates(ledger, lines, accepted_line_ids):
    """Exact normalized M1a labels across editions, candidate only.

    A generic quota label can name different capacity/year allocations; the
    candidate relation records the ambiguity for page-based adjudication.
    """
    config = json.loads((Path(__file__).resolve().parents[2] /
                         'config/jetp-matching.json').read_text())
    if config['tier2_candidate_similarity'] != 1.0:
        raise ValueError('the v1 exact-key generator requires threshold 1.0')
    groups = defaultdict(list)
    for document in config['m1a_documents']:
        fields_path = ledger / 'line-fields' / f'{document}.csv'
        if not fields_path.exists():
            continue
        fields = {r['line_id']: r for r in csv_rows(fields_path)}
        for line in lines:
            if line['line_id'] not in fields or line['line_id'] in accepted_line_ids:
                continue
            group = fields[line['line_id']].get('technology_group') or ''
            label = label_key(line['label'])
            if label and group:
                groups[line['country'], group, label].append((document, line))
    candidates = []
    for members in groups.values():
        for (first_doc, first), (second_doc, second) in itertools.combinations(members, 2):
            if first_doc == second_doc:
                continue
            digest = hashlib.sha256((first['line_id'] + '\n' + second['line_id']).encode()).hexdigest()[:16]
            candidate = _relation('0875.tier2.' + digest, 'line', first['line_id'],
                                  'same_as', 'line', second['line_id'], first['line_id'],
                                  status='candidate', method='normalized_label')
            candidate['method_version'] = config['tier2_method_version']
            candidates.append(candidate)
    return sorted(candidates, key=lambda r: r['relation_id'])


def _write_results(ledger, schema, tables, report, identity_for, existing_names, output_path):
    frozen = ledger / LEGACY
    frozen.parent.mkdir(exist_ok=True)
    if not frozen.exists():
        frozen.write_bytes((ledger / 'projects.csv').read_bytes())
    for name, rows in tables.items():
        write_table(ledger, name, rows, schema=schema)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(('old_id', 'disposition', 'new_id', 'basis_method', 'line_id'))
    for old_id, kind, target, method in report:
        writer.writerow((old_id, kind, '' if target == 'pending' else target,
                         method, identity_for.get(old_id, (None, None, ''))[2] or ''))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output.getvalue())
    _write_funder_audit(ledger, existing_names)


def _write_funder_audit(ledger, existing_names):
    """Account for event funders without inventing their future source lines."""
    funders = Counter(row['funder'].strip() for row in csv_rows(ledger / 'events.csv')
                      if row['funder'].strip())
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(('funder_text', 'event_count', 'disposition', 'party_id', 'note'))
    for form, count in sorted(funders.items(), key=lambda item: label_key(item[0])):
        key = name_key(form)
        if any(word in form.casefold() for word in ('undisclosed', 'to be confirmed',
                                                   'proposed financing')):
            status, party_id = 'not_a_named_party', ''
        elif key in existing_names:
            status, party_id = 'name_resolved_role_pending', existing_names[key]
        elif any(sep in form for sep in (' via ', ' and ', ' / ', ', ', ' through ')):
            status, party_id = 'composite_pending', ''
        else:
            status, party_id = 'authority_candidate_pending', ''
        writer.writerow((form, count, status, party_id,
                         'Event-specific source line and role follow in step 5'))
    (ledger / 'migration/0875-funder-strings.csv').write_text(output.getvalue())


def _register_roles(ledger, schema, legacy, identity_for, register_fields, relations):
    old_names = table_rows(ledger, 'party_names', schema)
    parties = [r for r in table_rows(ledger, 'parties', schema)
               if r['notes'] != 'Funder or channel named by a register line']
    party_names = [r for r in old_names if r['decided_by'] not in
                   {DECIDED_BY, 'scripts/jetp/reconcile.py'}]
    existing_names = {name_key(r['name']): r['party_id'] for r in party_names}
    existing_forms = {(r['party_id'], r['name']) for r in party_names}
    used_party_ids = {r['party_id'] for r in parties}
    names_per_party = Counter(r['party_id'] for r in party_names)

    def party(form, line_id):
        key = name_key(form)
        if key in existing_names:
            party_id = existing_names[key]
        else:
            party_id = slug(form)
            if party_id in used_party_ids:
                party_id = f'{party_id}-{len(used_party_ids) + 1}'
            used_party_ids.add(party_id)
            parties.append(dict(party_id=party_id, notes='Funder or channel named by a register line'))
        if (party_id, form) in existing_forms:
            return party_id
        existing_forms.add((party_id, form))
        names_per_party[party_id] += 1
        party_names.append(dict(name_row_id=f'{party_id}.name.{names_per_party[party_id]}',
                                party_id=party_id, name=form,
                                form_type='preferred' if names_per_party[party_id] == 1 else
                                'spelling_or_case_variant',
                                line_id=line_id, recorded_at=RECORDED_AT,
                                decided_by=DECIDED_BY, status='accepted'))
        existing_names[key] = party_id
        return party_id

    for old_id, kind, target in ((r['project_id'], *identity_for.get(r['project_id'], (None, None))[:2])
                                 for r in legacy):
        if kind != 'agreement' or not old_id.startswith('zaf-register-'):
            continue
        line_id = identity_for[old_id][2]
        fields = register_fields[line_id]
        for role, column in (('funder', 'Funding Partners'), ('channel', 'Disbursement Channel')):
            form = fields[column].strip()
            if (not form or form.casefold() in {'service provider', 'tbd', 'tbc'}
                    or any(sep in form for sep in (';', ' and ', ', ', ' & ', ' / '))):
                continue
            party_id = party(form, line_id)
            relations.append(_relation(f'0875.{role}.{old_id}', 'party', party_id,
                                       'party_in', 'agreement', target, line_id, role=role))
        form = fields['Implementing Entity'].strip()
        if (form and form.casefold() not in {'tbd', 'tbc', 'to be confirmed', 'service provider',
                                            'embassy'} and
                'to be issued' not in form.casefold() and
                'secondee recruited' not in form.casefold() and
                not any(sep in form for sep in (';', ' and ', ', ', ' & ', ' / ',
                                                ' ie. ', ' or ', ' with '))):
            party_id = party(form, line_id)
            relations.append(_relation(f'0875.implementer.{old_id}', 'party', party_id,
                                       'role_in', 'line', line_id, line_id,
                                       role='implementing_entity'))

    for form in party_names:
        if form['decided_by'] != DECIDED_BY:
            continue
        match = re.fullmatch(r'(.+?) \(([A-Z]{2,8})\)', form['name'])
        if not match:
            continue
        other = existing_names.get(name_key(match.group(1)))
        if other and other != form['party_id']:
            digest = hashlib.sha256((form['party_id'] + '\n' + other).encode()).hexdigest()[:16]
            relations.append(_relation('0875.party-candidate.' + digest,
                                       'party', form['party_id'], 'same_as',
                                       'party', other, form['line_id'],
                                       status='candidate', method='parenthetical_acronym'))
    return parties, party_names, existing_names


def build(ledger=LEDGER_DIR, write=False, output=None):
    ledger = Path(ledger)
    schema = load_schema()
    old_path = ledger / LEGACY if (ledger / LEGACY).exists() else ledger / 'projects.csv'
    legacy = csv_rows(old_path)
    lines = table_rows(ledger, 'lines', schema)
    plans = csv_rows(ledger / 'plan-projects.csv')
    link_candidates = csv_rows(ledger / 'migration/0874-link-candidates.csv')
    candidates = defaultdict(list)
    for candidate in link_candidates:
        candidates[candidate['old_project_id']].append(candidate)
    by_name, by_legacy, _, line_ids = _line_index(lines)
    projects, assets, agreements, referents, report = [], [], [], [], []
    relations = [r for r in table_rows(ledger, 'relations', schema)
                 if not r['relation_id'].startswith('0875.')]
    identity_for = {}
    register_fields = {r['line_id']: r for r in csv_rows(
        ledger / 'line-fields/zaf-jet-investment-register-q1-2026.csv')}

    for old in legacy:
        old_id = old['project_id']
        kind = disposition(old)
        line, method = _basis(old, lines, plans, candidates, by_name, by_legacy)
        target_id = old_id
        if kind == 'perimeter':
            target_id = 'vnm-jetp-portfolio-2025'
        elif line is None:
            report.append((old_id, kind, 'pending', 'no precise line'))
            continue
        elif kind == 'line':
            target_id = line['line_id']
        elif kind == 'agreement':
            target_id = 'agreement-' + old_id
            fields = register_fields.get(line['line_id'], {})
            agreements.append(dict(agreement_id=target_id, country=old['country'],
                                   instrument=fields.get('Funding Instrument') or None,
                                   modality='unknown',
                                   currency=fields.get('Currency: Pledged') or None,
                                   sector=line['own_sector'] or None,
                                   notes=f'Legacy {old_id}; {old["canonical_name"]}'))
            referents.append(_referent(line, 'agreement', target_id, method))
        elif kind == 'asset':
            target_id = 'asset-' + old_id
            assets.append(dict(asset_id=target_id, country=old['country'],
                               name=old['canonical_name'], technology=old['technology'] or None,
                               location=old['location'] or None, notes=f'Legacy {old_id}'))
            referents.append(_referent(line, 'asset', target_id, method))
        else:
            target_id = 'project-' + old_id
            projects.append(dict(project_id=target_id, country=old['country'],
                                 canonical_name=old['canonical_name'],
                                 classification='project', sector=None,
                                 notes=f'Legacy {old_id}; {old["notes"]}'))
            referents.append(_referent(line, 'project', target_id, method))
        identity_for[old_id] = (kind, target_id, line['line_id'] if line else None)
        report.append((old_id, kind, target_id, method))

    # A named, source-defined perimeter exists before 0877 adds its two count
    # observations.  The 21 count slots never become project identities.
    perimeters = table_rows(ledger, 'perimeters', schema)
    if not any(row['perimeter_id'] == 'vnm-jetp-portfolio-2025' for row in perimeters):
        perimeters.append(dict(perimeter_row_id='vnm-jetp-portfolio-2025.1',
                               perimeter_id='vnm-jetp-portfolio-2025', country='VNM',
                               name='Viet Nam JETP portfolio reported in 2025',
                               definition='The portfolio whose initial and screened counts the 2025 Secretariat source reports.',
                               recorded_at=RECORDED_AT, decided_by=DECIDED_BY,
                               status='accepted', notes='Count observations follow in ticket 0877'))

    parties, party_names, existing_names = _register_roles(
        ledger, schema, legacy, identity_for, register_fields, relations)

    # Preserve reviewed component links; their target is the project's source
    # line until an independently justified project identity is minted.
    sources = {r['source_id']: r for r in csv_rows(ledger / 'sources.csv')}
    component_projects = {}
    for link in csv_rows(ledger / 'project-source-links.csv'):
        if link['relationship'] != 'project_page_component':
            continue
        source = identity_for.get(link['project_id'])
        if not source or not source[2]:
            raise ValueError(f'{link["link_id"]}: component has no source identity')
        source_id = link['source_id']
        if source_id not in component_projects:
            # The publisher's project page names an intervention containing
            # several register allocations.  A register line justifies this
            # project identity even when 0874 could not anchor a separate line
            # in the page bytes itself.
            project_id = 'project-page-' + source_id
            projects.append(dict(project_id=project_id, country=link['country'],
                                 canonical_name=sources[source_id]['title'],
                                 classification='project',
                                 notes=f'Project page {source_id}; register component'))
            referents.append(_referent(line_ids[source[2]], 'project', project_id,
                                       'reviewed_component'))
            component_projects[source_id] = project_id
        relations.append(_relation('0875.component.' + link['link_id'], source[0],
                                   source[1], 'component_of', 'project',
                                   component_projects[source_id], source[2]))

    # CIPP names these power stations as assets, independently of a project
    # stage.  Pelabuhan Ratu has no old projects.csv row, but its plan line is
    # an exact first-tier identifier and must not be lost in the split.
    pelabuhan = next(line for line in lines if line['line_id'] ==
                     'idn-cipp-2023-cpr-mirror-coal-retirement-1')
    assets.append(dict(asset_id='asset-idn-pelabuhan-ratu', country='IDN',
                       name='PLTU Pelabuhan Ratu', technology='coal-fired power plant',
                       notes='CIPP coal-retirement plan line; not a project stage'))
    referents.append(_referent(pelabuhan, 'asset', 'asset-idn-pelabuhan-ratu',
                               'plan_row'))

    accepted_line_ids = {r['line_id'] for r in referents if r['status'] == 'accepted'}
    relations.extend(tier2_candidates(ledger, lines, accepted_line_ids))

    tables = dict(projects=projects, assets=assets, agreements=agreements,
                  line_referents=referents, relations=relations,
                  parties=parties, party_names=party_names, perimeters=perimeters)
    if write:
        _write_results(ledger, schema, tables, report, identity_for, existing_names,
                       output or ledger / 'migration/0875-dispositions.csv')
    return tables, report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER_DIR)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--output', type=Path, help='Path for the old-ID disposition report')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    tables, report = build(args.ledger_dir, args.write, args.output)
    counts = Counter((disposition(r),) for r in csv_rows(args.ledger_dir /
                      (LEGACY if (args.ledger_dir / LEGACY).exists() else 'projects.csv')))
    logging.info('%s legacy rows; %s projects; %s agreements; %s assets',
                 len(report), len(tables['projects']), len(tables['agreements']),
                 len(tables['assets']))
    logging.info('dispositions: %s', dict(counts))
    logging.info('pending: %s', [r for r in report if r[2] in ('pending', 'document')])


if __name__ == '__main__':
    main()
