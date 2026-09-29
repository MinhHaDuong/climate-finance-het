"""Project current JETP referents and their cited statements for country pages.

The ledger tables keep projects, agreements and document lines separate. A
country payload preserves that distinction; it never promotes a register row
or an agreement to a project merely to fill an old site card.
"""

from collections import defaultdict
from pathlib import Path

from jetp._ledger_headers import load_schema, read_table

MILESTONES = ('signed', 'approved', 'mou', 'announced', 'need')
MILESTONE_LABELS = {'signed': 'Signed', 'approved': 'Approved', 'mou': 'Mou',
                    'announced': 'Announced', 'need': 'Need', 'disbursed': 'Disbursed'}


def _rows(ledger_dir, table, schema):
    found, errors = read_table(ledger_dir, table, schema)
    if errors:
        raise ValueError(f'{table}: {errors[0]}')
    return [dict(zip(schema.header(table), row)) for row in found]


def _current(rows, key):
    """Return accepted terminal rows, including revocation by a later row."""
    superseded = {row['supersedes'] for row in rows if row.get('supersedes')}
    return [row for row in rows if row['status'] == 'accepted'
            and row[key] not in superseded]


def load_country_inputs(ledger_dir):
    """Read the v2 tables once for all four country views."""
    ledger_dir = Path(ledger_dir)
    schema = load_schema()
    names = ('projects', 'assets', 'agreements', 'coverage', 'documents',
             'document_publishers', 'party_names', 'retrievals', 'snapshots',
             'lines', 'line_referents', 'relations', 'observations', 'timings',
             'perimeters')
    return {name: _rows(ledger_dir, name, schema) for name in names}


def _document_index(tables):
    documents = {row['document_id']: row for row in tables['documents']}
    names = {row['name_row_id']: row['name'] for row in
             _current(tables['party_names'], 'name_row_id')}
    publishers = defaultdict(list)
    for row in tables['document_publishers']:
        name = names.get(row['name_row_id'])
        if name:
            publishers[row['document_id']].append(name)
    attempts = defaultdict(list)
    by_digest = defaultdict(set)
    for row in tables['retrievals']:
        attempts[row['document_id']].append(row)
        if row['sha256']:
            by_digest[row['sha256']].add(row['document_id'])
    sources = {}
    for document_id, row in documents.items():
        latest = max(attempts[document_id],
                     key=lambda item: (item['retrieved_at'] or '', item['retrieval_id']),
                     default={})
        sources[document_id] = dict(
            id=document_id, title=row['title'], url=row['url'],
            publisher='; '.join(publishers[document_id]),
            date=row['published_date'] or '',
            retrieved=latest.get('retrieved_at') or '',
            collection=latest.get('status') or 'Not collected',
            sha256=latest.get('sha256') or '',
        )
    return sources, by_digest


def _line_documents(lines, by_digest):
    found = {}
    for line_id, row in lines.items():
        candidates = by_digest[row['sha256']]
        if len(candidates) == 1:
            found[line_id] = next(iter(candidates))
        elif candidates:
            matching = [identity for identity in candidates
                        if line_id.startswith(identity + '-')]
            if matching:
                found[line_id] = max(matching, key=len)
    return found


def _timing(timings, observation_id):
    rows = timings.get(observation_id, ())
    by_role = {row['date_role']: row for row in rows if row['date']}
    event = by_role.get('event')
    start, end = by_role.get('period_start'), by_role.get('period_end')
    report = by_role.get('report_date')
    cutoff = by_role.get('reporting_cutoff')
    return dict(
        date=event['date'] if event and event['date_precision'] == 'day' else None,
        event_start=start['date'] if start else None,
        event_end=end['date'] if end else None,
        event_precision=(start or end or event or {}).get('date_precision'),
        observed_date=cutoff['date'] if cutoff else None,
        reported_on=report['date'] if report else None,
        date_basis=', '.join(sorted(by_role)) or 'No dated role reviewed',
    )


def _statement(row, lines, line_documents, timings, agreements, funders):
    line = lines[row['line_id']]
    subject = row['subject_id']
    agreement = agreements.get(subject, {}) if row['subject_kind'] == 'agreement' else {}
    status = MILESTONE_LABELS.get(row['own_status'], row['own_status'] or 'Not stated')
    return dict(
        id=row['observation_id'], subject_kind=row['subject_kind'], subject_id=subject,
        status=status, amount=row['value'], currency=row['currency'] or row['unit'] or '',
        funder='; '.join(sorted(funders.get(subject, ()))),
        instrument=agreement.get('instrument') or '',
        source_id=line_documents.get(row['line_id']) or '',
        locator=line['locator'], line_id=row['line_id'], sha256=line['sha256'],
        measure=row['measure'], basis=row['basis'] or '',
        notes=row['notes'] or '',
        **_timing(timings, row['observation_id']),
    )


def _funders(tables, agreement_rows):
    """Funders by agreement, from party_in rows, and by project, from its components.

    A project has no party_in row of its own (ticket 1610): its funders are
    those of the agreements recorded as its components, derived, never typed.
    A party in the `channel` role is the channel the money passes through,
    not a funder (author, 2026-09-29), and is listed under neither.
    """
    relations = _current(tables['relations'], 'relation_id')
    preferred = {row['party_id']: row['name'] for row in
                 _current(tables['party_names'], 'name_row_id')
                 if row['form_type'] == 'preferred'}
    funders = defaultdict(set)
    for row in relations:
        if row['from_kind'] == 'party' and row['relation'] == 'party_in' \
                and row['role'] == 'funder' \
                and row['to_kind'] == 'agreement' and row['to_id'] in agreement_rows:
            funders[row['to_id']].add(preferred.get(row['from_id'], row['from_id']))
    project_funders = defaultdict(set)
    for row in relations:
        if row['relation'] == 'component_of' and row['from_kind'] == 'agreement' \
                and row['to_kind'] == 'project':
            project_funders[row['to_id']] |= funders[row['from_id']]
    return funders, project_funders


def country_view(ledger_dir, code, config, *, tables=None):
    """A site payload of reviewed projects, agreements and cited statements."""
    tables = tables or load_country_inputs(ledger_dir)
    sources, by_digest = _document_index(tables)
    lines = {row['line_id']: row for row in tables['lines']}
    line_documents = _line_documents(lines, by_digest)
    coverage = {(row['referent_kind'], row['referent_id']): row
                for row in tables['coverage']}
    agreement_rows = {row['agreement_id']: row for row in tables['agreements']
                      if row['country'] == code}
    projects = [row for row in tables['projects'] if row['country'] == code]
    funders, project_funders = _funders(tables, agreement_rows)
    timings = defaultdict(list)
    for row in tables['timings']:
        timings[row['observation_id']].append(row)
    country_subjects = {('project', row['project_id']) for row in projects}
    country_subjects |= {('agreement', identity) for identity in agreement_rows}
    country_subjects |= {('asset', row['asset_id']) for row in tables['assets']
                         if row['country'] == code}
    statements = [_statement(row, lines, line_documents, timings, agreement_rows, funders)
                  for row in _current(tables['observations'], 'observation_id')
                  if (row['subject_kind'], row['subject_id']) in country_subjects
                  and row['axis'] == 'money' and row['measure'] in ('amount', 'estimate', 'flow')]
    by_subject = defaultdict(list)
    for row in statements:
        by_subject[(row['subject_kind'], row['subject_id'])].append(row)
    citations = defaultdict(set)
    cited_lines = defaultdict(list)
    for row in _current(tables['line_referents'], 'referent_row_id'):
        if (row['referent_kind'], row['referent_id']) in country_subjects:
            document = line_documents.get(row['line_id'])
            if document:
                citations[(row['referent_kind'], row['referent_id'])].add(document)
                line = lines[row['line_id']]
                cited_lines[(row['referent_kind'], row['referent_id'])].append(dict(
                    line_id=row['line_id'], locator=line['locator'],
                    label=line['label'], source_id=document, sha256=line['sha256'],
                ))
    for row in statements:
        if row['source_id']:
            citations[(row['subject_kind'], row['subject_id'])].add(row['source_id'])

    def cited(kind, identity):
        return sorted(citations[(kind, identity)])

    project_views = []
    for row in projects:
        identity = row['project_id']
        events = by_subject[('project', identity)]
        stages = {event['status'].lower() for event in events}
        stage = next((MILESTONE_LABELS[s] for s in MILESTONES if s in stages),
                     'Not documented')
        review = coverage.get(('project', identity), {})
        # The coverage row is a review record: what was collected for the
        # project on checked_at, not what a document says (ticket 1610). Its
        # documents are served apart from the cited ones and never join them.
        project_views.append(dict(
            id=identity, country=code, name=row['canonical_name'],
            technology=row['sector'] or 'Not specified', location='Not specified',
            operator='Not specified', notes=row['notes'] or '',
            coverage=review.get('review_status') or 'Not assessed',
            coverage_note=review.get('notes') or '', finance_stage=stage,
            coverage_checked_at=review.get('checked_at') or '',
            coverage_documents=[d for d in (review.get('document_ids') or '').split(';') if d],
            funders=sorted(project_funders[identity]), events=events,
            sources=cited('project', identity),
            evidence=sorted(cited_lines[('project', identity)],
                            key=lambda item: item['line_id']),
        ))
    agreement_views = []
    for identity, row in agreement_rows.items():
        names = [lines[link['line_id']]['label'] for link in tables['line_referents']
                 if link['referent_kind'] == 'agreement' and link['referent_id'] == identity
                 and link['status'] == 'accepted' and link['line_id'] in lines]
        review = coverage.get(('agreement', identity), {})
        agreement_views.append(dict(
            id=identity, country=code, name=next((name for name in names if name), identity),
            instrument=row['instrument'] or '', modality=row['modality'] or '',
            sector=row['sector'] or '', currency=row['currency'] or '',
            funders=sorted(funders[identity]),
            coverage=review.get('review_status') or 'Not assessed',
            events=by_subject[('agreement', identity)],
            sources=cited('agreement', identity),
        ))
    needed = {source for item in (*project_views, *agreement_views)
              for source in item['sources']}
    needed.update(row['source_id'] for row in statements if row['source_id'])
    if config.get('headline_source'):
        needed.add(config['headline_source'])
    if missing := needed - sources.keys():
        raise ValueError(f'Unknown cited documents: {sorted(missing)}')
    collected = {d for item in project_views for d in item['coverage_documents']}
    if missing := collected - sources.keys():
        raise ValueError(f'Unknown collected documents: {sorted(missing)}')
    country_perimeters = {row['perimeter_id'] for row in tables['perimeters']
                          if row['country'] == code and row['status'] == 'accepted'}
    reported_counts = [dict(id=row['observation_id'], perimeter_id=row['subject_id'],
                            value=row['value'], unit=row['unit'], notes=row['notes'],
                            line_id=row['line_id'])
                       for row in _current(tables['observations'], 'observation_id')
                       if row['subject_kind'] == 'perimeter' and row['measure'] == 'count'
                       and row['subject_id'] in country_perimeters]
    return dict(
        country=dict(config, code=code), projects=project_views,
        agreements=agreement_views, statements=statements,
        reported_counts=reported_counts,
        sources={identity: sources[identity] for identity in sorted(needed)},
        project_count=len(project_views), agreement_count=len(agreement_views),
    )
