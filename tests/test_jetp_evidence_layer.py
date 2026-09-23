"""The evidence layer rebuilt from sources.csv and manifest.csv (ticket 0872).

A fixture of five sources and eight collection attempts, two of them failed
and two of them returning the same bytes, becomes 5 documents, 8 retrievals
and 5 snapshots; a document declared co-published carries two publication
rows. The tables validate through the ledger DDL (ticket 0871) against the
real terms in force (ticket 0880), and the compatibility reader gives the
Documents view the same rows the manifest gave it.
"""

import csv
import shutil
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


@pytest.fixture
def tables():
    return evidence.reconstruct(SOURCES, MANIFEST, joint_publications=JOINT,
                                mirrors=MIRRORS, publisher_duplicates=())


def test_counts_of_the_rebuilt_layer(tables):
    assert len(tables['documents']) == 5
    assert len(tables['retrievals']) == 8
    assert len(tables['snapshots']) == 5
    assert len(tables['publishers']) == 5


def test_a_co_published_document_carries_two_publication_rows(tables):
    rows = [r for r in tables['document_publishers'] if r['document_id'] == 'sen-declaration']
    assert len(rows) == 2
    assert {r['role'] for r in rows} == {'author'}
    assert sum(r['document_id'] != 'sen-declaration' for r in tables['document_publishers']) == 4


def test_failed_retrievals_carry_no_fingerprint(tables):
    failed = [r for r in tables['retrievals'] if r['document_id'] == 'idn-cipp']
    assert [r['sha256'] for r in failed] == [None, None]
    assert [r['retrieval_id'] for r in failed] == ['idn-cipp:1', 'idn-cipp:2']


def test_the_mirror_receives_a_same_as_candidate(tables):
    (relation,) = [r for r in tables['relations'] if r['from_kind'] == 'document']
    assert (relation['from_id'], relation['relation'], relation['to_id']) == (
        'idn-cipp-mirror', 'same_as', 'idn-cipp')
    assert relation['status'] == 'candidate'


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


def test_the_compatibility_reader_serves_the_same_documents_view(tmp_path, tables):
    _write_ledger(tmp_path / 'ledger', tables)
    registry = retrieval_registry(tmp_path / 'ledger')
    assert registry == [dict(row) for row in sorted(MANIFEST, key=lambda r: r['source_id'])]
    assert documents_data(tmp_path, {'manifest': registry}) == documents_data(
        tmp_path, {'manifest': [dict(row) for row in MANIFEST]})


def test_the_committed_layer_matches_its_inputs():
    """The five tables in data/jetp/ are the reconstruction of the two old ones."""
    ledger = ROOT / 'data' / 'jetp'
    with (ledger / 'sources.csv').open(newline='', encoding='utf-8') as handle:
        sources = list(csv.DictReader(handle))
    with (ledger / 'manifest.csv').open(newline='', encoding='utf-8') as handle:
        manifest = list(csv.DictReader(handle))
    registry = retrieval_registry(ledger)
    assert registry == sorted(manifest, key=lambda r: r['source_id'])
    schema = ledger_headers.load_schema()
    documents, _ = ledger_headers.read_table(ledger, 'documents', schema)
    publishers, _ = ledger_headers.read_table(ledger, 'publishers', schema)
    snapshots, _ = ledger_headers.read_table(ledger, 'snapshots', schema)
    assert len(documents) == len(sources)
    assert len(publishers) == len({r['publisher'] for r in sources})
    assert len(snapshots) == len({r['sha256'] for r in manifest if r['sha256']})
