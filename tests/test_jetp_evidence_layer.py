"""The evidence layer rebuilt from sources.csv and manifest.csv (ticket 0872).

A fixture of eight sources and eight collection attempts, two of them failed
and two of them returning the same bytes, becomes 8 documents, 8 retrievals
and 5 snapshots; a document declared co-published carries two publication
rows. Organisations are under authority control (decision of 2026-09-23): two
publisher texts that differ only by case are one party with two name forms, a
joint publisher text is two parties, and an acronym beside its expansion is a
tier-2 candidate, not a merge. The tables validate through the ledger DDL
(ticket 0871) against the real terms in force (ticket 0880), and the
compatibility reader gives the Documents view the same rows the manifest gave
it.
"""

import csv
import shutil
from collections import Counter
from pathlib import Path

import pytest
from jetp import _ledger_headers as ledger_headers
from jetp import build_evidence_layer as evidence
from jetp import build_ledger as ledger_build
from jetp.build_observatory import documents_data, retrieval_registry

ROOT = Path(__file__).resolve().parents[1]
SHA = {name: name * 64 for name in 'abcde'}

SOURCE_COLUMNS = ['source_id', 'country', 'authority_category', 'publisher', 'source_type',
                  'title', 'published_date', 'url', 'project_id', 'expected_format',
                  'priority', 'active', 'notes']
MANIFEST_COLUMNS = ['source_id', 'country', 'retrieved_at', 'status', 'http_status',
                    'content_type', 'etag', 'last_modified', 'sha256', 'size_bytes',
                    'storage_path', 'final_url', 'error']


def _source(source_id, country, category, publisher, kind, title):
    row = dict.fromkeys(SOURCE_COLUMNS, '')
    row.update(source_id=source_id, country=country, authority_category=category,
               publisher=publisher, source_type=kind, title=title,
               url=f'https://example.org/{source_id}', active='true')
    return row


def _attempt(source_id, country, when, status, sha=''):
    row = dict.fromkeys(MANIFEST_COLUMNS, '')
    row.update(source_id=source_id, country=country, retrieved_at=when, status=status,
               final_url=f'https://example.org/{source_id}')
    if sha:
        row.update(http_status='200', content_type='application/pdf', sha256=sha,
                   size_bytes='10', storage_path=f'objects/{sha[:2]}/{sha}.pdf')
    else:
        row.update(error='HTTP 403')
    return row


SOURCES = [
    _source('zaf-plan', 'ZAF', 'jetp_secretariat', 'JET PMU', 'investment_plan', 'Plan'),
    _source('zaf-register', 'ZAF', 'jetp_secretariat', 'JET PMU', 'project_list', 'Register'),
    _source('idn-cipp', 'IDN', 'jetp_secretariat', 'JETP Secretariat', 'investment_plan',
            'CIPP'),
    _source('idn-cipp-mirror', 'IDN', 'secondary_source', 'Mirror Host', 'investment_plan',
            'CIPP'),
    _source('sen-declaration', 'SEN', 'ipg', 'Government of France', 'political_declaration',
            'Déclaration'),
    # A case variant of a publisher text above, and a joint publisher text.
    _source('zaf-pmu-page', 'ZAF', 'jetp_secretariat', 'JET PMU', 'project_page', 'Page'),
    _source('zaf-joint', 'ZAF', 'ipg', 'Jet pmu and Agence Française de Développement',
            'political_declaration', 'Statement'),
    _source('zaf-afd', 'ZAF', 'bilateral_funder', 'AFD', 'project_page', 'AFD page'),
]

MANIFEST = [
    _attempt('zaf-plan', 'ZAF', '2026-09-11T20:39:00Z', 'collected', SHA['a']),
    # A second attempt that returned the same bytes: one snapshot, two retrievals.
    _attempt('zaf-plan', 'ZAF', '2026-09-11T20:42:35Z', 'not_modified', SHA['a']),
    _attempt('zaf-register', 'ZAF', '2026-09-11T20:39:00Z', 'collected', SHA['b']),
    _attempt('idn-cipp', 'IDN', '2026-09-11T20:39:00Z', 'blocked'),
    _attempt('idn-cipp', 'IDN', '2026-09-12T08:00:00Z', 'fetch_error'),
    _attempt('idn-cipp-mirror', 'IDN', '2026-09-12T08:00:00Z', 'collected', SHA['c']),
    _attempt('sen-declaration', 'SEN', '2026-09-12T08:00:00Z', 'collected', SHA['d']),
    _attempt('sen-declaration', 'SEN', '2026-09-13T08:00:00Z', 'collected', SHA['e']),
]

JOINT = {'sen-declaration': ['Government of Senegal']}
MIRRORS = {'idn-cipp-mirror': 'idn-cipp'}
JOINT_LABELS = {'Jet pmu and Agence Française de Développement':
                ('Jet pmu', 'Agence Française de Développement')}
PARTS = {'Agence Française de Développement': ('bilateral_funder', None, None)}


@pytest.fixture
def tables():
    return evidence.reconstruct(SOURCES, MANIFEST, joint_publications=JOINT,
                                mirrors=MIRRORS, joint_labels=JOINT_LABELS,
                                name_candidates=(), part_attributes=PARTS)


def _names(tables, party_id):
    return {n['name']: n['form_type'] for n in tables['party_names']
            if n['party_id'] == party_id}


def test_counts_of_the_rebuilt_layer(tables):
    assert len(tables['documents']) == 8
    assert len(tables['retrievals']) == 8
    assert len(tables['snapshots']) == 5
    # JET PMU, JETP Secretariat, Mirror Host, Government of France, Government
    # of Senegal, Agence Française de Développement, AFD.
    assert len(tables['parties']) == 7


def test_case_variants_are_one_party_with_several_name_forms(tables):
    assert _names(tables, 'jet-pmu') == {'JET PMU': 'preferred',
                                         'Jet pmu': 'spelling_or_case_variant'}
    publications = [r for r in tables['document_publishers'] if r['party_id'] == 'jet-pmu']
    assert {r['document_id'] for r in publications} == {
        'zaf-plan', 'zaf-register', 'zaf-pmu-page', 'zaf-joint'}
    # Each publication shows the form its own document prints, not the preferred one.
    form = {n['name_row_id']: n['name'] for n in tables['party_names']}
    assert {r['document_id']: form[r['name_row_id']] for r in publications} == {
        'zaf-plan': 'JET PMU', 'zaf-register': 'JET PMU', 'zaf-pmu-page': 'JET PMU',
        'zaf-joint': 'Jet pmu'}


def test_a_joint_publisher_text_links_the_document_to_each_party(tables):
    rows = [r for r in tables['document_publishers'] if r['document_id'] == 'zaf-joint']
    assert sorted(r['party_id'] for r in rows) == ['agence-francaise-de-developpement',
                                                   'jet-pmu']
    (name,) = [n for n in tables['party_names']
               if n['name'] == 'Agence Française de Développement']
    assert name['document_id'] == 'zaf-joint'
    assert 'Jet pmu and Agence' in name['notes']
    (party,) = [p for p in tables['parties']
                if p['party_id'] == 'agence-francaise-de-developpement']
    assert party['authority_category'] == 'bilateral_funder'


def test_an_acronym_beside_its_expansion_is_a_candidate_not_a_merge(tables):
    assert {'afd', 'agence-francaise-de-developpement'} <= {
        p['party_id'] for p in tables['parties']}
    (relation,) = [r for r in tables['relations'] if r['from_kind'] == 'party']
    assert (relation['from_id'], relation['relation'], relation['to_id'],
            relation['status']) == ('afd', 'same_as', 'agence-francaise-de-developpement',
                                    'candidate')


def test_every_party_has_exactly_one_preferred_name(tables):
    preferred = Counter(n['party_id'] for n in tables['party_names']
                        if n['form_type'] == 'preferred')
    assert set(preferred) == {p['party_id'] for p in tables['parties']}
    assert set(preferred.values()) == {1}


def test_a_co_published_document_carries_two_publication_rows(tables):
    rows = [r for r in tables['document_publishers'] if r['document_id'] == 'sen-declaration']
    assert len(rows) == 2
    assert {r['role'] for r in rows} == {'author'}


def test_failed_retrievals_carry_no_fingerprint(tables):
    failed = [r for r in tables['retrievals'] if r['document_id'] == 'idn-cipp']
    assert [r['sha256'] for r in failed] == [None, None]
    assert [r['retrieval_id'] for r in failed] == ['idn-cipp:1', 'idn-cipp:2']


def test_the_mirror_receives_a_same_as_candidate(tables):
    (relation,) = [r for r in tables['relations'] if r['from_kind'] == 'document']
    assert (relation['from_id'], relation['relation'], relation['to_id']) == (
        'idn-cipp-mirror', 'same_as', 'idn-cipp')
    assert relation['status'] == 'candidate'


SPLIT_SOURCES = [
    _source('sen-plan', 'SEN', 'operator', 'Senelec', 'investment_plan', 'Plan'),
    _source('sen-notice', 'SEN', 'operator', 'SENELEC via AFD dgMarket', 'project_page',
            'Notice'),
    _source('sen-audit', 'SEN', 'national_government', 'ARCOP / Grant Thornton', 'report',
            'Audit'),
    _source('sen-thesis', 'SEN', 'secondary_source', 'CESAG / Fatou Ndiaye', 'report',
            'Thesis'),
    _source('sen-esia', 'SEN', 'multilateral_funder', 'BOAD / Senelec', 'report', 'ESIA'),
]
SPLIT_WRITERS = {'Grant Thornton': 'firm', 'Fatou Ndiaye': 'person'}


@pytest.fixture
def split():
    return evidence.reconstruct(SPLIT_SOURCES, [], joint_publications={}, mirrors={},
                                joint_labels={}, name_candidates=(), part_attributes={},
                                writers=SPLIT_WRITERS)


def _roles(tables, document_id):
    return {r['party_id']: r['role'] for r in tables['document_publishers']
            if r['document_id'] == document_id}


def test_x_via_y_is_published_by_x_and_names_y_only_as_the_channel(split):
    # The channel is neither a party nor a name form; the publisher merges
    # with the party its own texts already name.
    assert _roles(split, 'sen-notice') == {'senelec': 'author'}
    assert _names(split, 'senelec') == {'Senelec': 'preferred',
                                        'SENELEC': 'spelling_or_case_variant'}
    assert not any('dgMarket' in n['name'] for n in split['party_names'])
    (document,) = [d for d in split['documents'] if d['document_id'] == 'sen-notice']
    assert "'SENELEC via AFD dgMarket'" in document['notes']
    assert 'retrieved through AFD dgMarket' in document['notes']


def test_x_slash_firm_links_the_firm_as_author_and_x_as_commissioner(split):
    assert _roles(split, 'sen-audit') == {'arcop': 'commissioner',
                                          'grant-thornton': 'author'}
    (firm,) = [p for p in split['parties'] if p['party_id'] == 'grant-thornton']
    assert firm['authority_category'] is None
    (arcop,) = [p for p in split['parties'] if p['party_id'] == 'arcop']
    assert arcop['authority_category'] == 'national_government'


def test_x_slash_person_keeps_the_person_in_the_document_notes(split):
    assert _roles(split, 'sen-thesis') == {'cesag': 'commissioner'}
    assert not any('Ndiaye' in n['name'] for n in split['party_names'])
    (document,) = [d for d in split['documents'] if d['document_id'] == 'sen-thesis']
    assert 'written by Fatou Ndiaye, a natural person' in document['notes']


def test_a_slash_text_without_a_reviewed_writer_stays_one_party(split):
    assert _roles(split, 'sen-esia') == {'boad-senelec': 'author'}
    (document,) = [d for d in split['documents'] if d['document_id'] == 'sen-esia']
    assert document['notes'] is None


def _write_ledger(ledger_dir, tables):
    for table, rows in tables.items():
        ledger_headers.write_table(ledger_dir, table, rows)
    terms = ledger_headers.table_path(ROOT / 'data' / 'jetp', 'terms')
    target = ledger_headers.table_path(ledger_dir, 'terms')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(terms, target)


def test_the_layer_validates_against_the_terms_in_force(tmp_path, tables):
    _write_ledger(tmp_path, tables)
    assert ledger_build.build(tmp_path) == []


def _second_preferred(tables):
    variant = next(n for n in tables['party_names'] if n['name'] == 'Jet pmu')
    variant['form_type'] = 'preferred'


def _no_preferred(tables):
    tables['party_names'] = [n for n in tables['party_names'] if n['party_id'] != 'afd']


def _foreign_name_form(tables):
    row = next(r for r in tables['document_publishers'] if r['party_id'] == 'afd')
    row['name_row_id'] = 'jet-pmu.name.1'


@pytest.mark.parametrize('breakage, needle', [
    (_second_preferred, 'party_preferred_name: parties jet-pmu: 2 preferred'),
    (_no_preferred, 'party_preferred_name: parties afd: 0 preferred'),
    (_foreign_name_form, 'publication_name_form:'),
])
def test_name_form_breakages_are_named(tmp_path, tables, breakage, needle):
    breakage(tables)
    _write_ledger(tmp_path, tables)
    errors = ledger_build.build(tmp_path)
    assert any(needle in e for e in errors), errors


def test_the_compatibility_reader_serves_the_same_documents_view(tmp_path, tables):
    _write_ledger(tmp_path / 'ledger', tables)
    registry = retrieval_registry(tmp_path / 'ledger')
    assert registry == [dict(row) for row in sorted(MANIFEST, key=lambda r: r['source_id'])]
    assert documents_data(tmp_path, {'manifest': registry}) == documents_data(
        tmp_path, {'manifest': [dict(row) for row in MANIFEST]})


def test_the_committed_layer_matches_its_inputs():
    """The tables in data/jetp/ are the reconstruction of the two old ones."""
    ledger = ROOT / 'data' / 'jetp'
    with (ledger / 'sources.csv').open(newline='', encoding='utf-8') as handle:
        sources = list(csv.DictReader(handle))
    with (ledger / 'manifest.csv').open(newline='', encoding='utf-8') as handle:
        manifest = list(csv.DictReader(handle))
    registry = retrieval_registry(ledger)
    assert registry == sorted(manifest, key=lambda r: r['source_id'])
    schema = ledger_headers.load_schema()
    documents, _ = ledger_headers.read_table(ledger, 'documents', schema)
    snapshots, _ = ledger_headers.read_table(ledger, 'snapshots', schema)
    names, _ = ledger_headers.read_table(ledger, 'party_names', schema)
    publications, _ = ledger_headers.read_table(ledger, 'document_publishers', schema)
    assert len(documents) == len(sources)
    assert len(snapshots) == len({r['sha256'] for r in manifest if r['sha256']})
    # Every publisher text is a name form, or a joint, "via" or "/" text whose
    # parties' parts are.
    forms = {row[2] for row in names}
    for text in {r['publisher'] for r in sources}:
        if text in evidence.JOINT_LABELS:
            parts = set(evidence.JOINT_LABELS[text])
        else:
            publisher, writer, _ = evidence.split_label(text, evidence.WRITERS)
            parts = {publisher}
            if writer and evidence.WRITERS[writer] == 'firm':
                parts.add(writer)
        assert parts <= forms, text
    firm_written = sum(
        1 for r in sources if r['publisher'] not in evidence.JOINT_LABELS
        and (writer := evidence.split_label(r['publisher'], evidence.WRITERS)[1])
        and evidence.WRITERS[writer] == 'firm')
    assert len(publications) == len(sources) + len(evidence.JOINT_LABELS) + firm_written
    assert evidence.reconstruct(sources, manifest)['parties'] == [
        dict(zip(schema.header('parties'), row)) for row in
        ledger_headers.read_table(ledger, 'parties', schema)[0]]
