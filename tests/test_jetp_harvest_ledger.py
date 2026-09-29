"""The collector appends v2 retrievals and content-addressed snapshots."""

import pytest
from jetp._ledger_headers import load_schema, write_table
from jetp.corpus_collect_downloads import collect_downloads, uncollected_documents
from jetp.corpus_harvest_ledger import harvest_documents, load_inputs

pytestmark = pytest.mark.domain_jetp


class Response:
    def __init__(self, code, body=b'', headers=None):
        self.status_code = code
        self.body = body
        self.headers = headers or {}
        self.url = 'https://example.test/report.pdf'

    def iter_content(self, chunk_size):
        yield self.body

    def close(self):
        pass


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.headers = []

    def get(self, url, *, headers, **_):
        self.headers.append(headers)
        return self.responses.pop(0)


def ledger(tmp_path):
    schema = load_schema()
    write_table(tmp_path, 'documents', [dict(
        document_id='doc-a', country='ZAF', document_type='report', language='',
        title='Report', url='https://example.test/report.pdf', published_date='',
        edition_of='', active='true', notes='')], schema=schema)
    write_table(tmp_path, 'retrievals', [], schema=schema)
    write_table(tmp_path, 'snapshots', [], schema=schema)
    return tmp_path


def test_collected_then_not_modified_reuses_one_snapshot(tmp_path):
    root = ledger(tmp_path)
    storage = root / 'binary'
    first = Session(Response(200, b'%PDF-1.4\nhello',
                             {'Content-Type': 'application/pdf', 'ETag': 'one'}))
    harvest_documents(root, storage, timestamp='2026-09-28T15:00:00Z', session=first)
    _, attempts, snapshots = load_inputs(root)
    assert [(row['retrieval_id'], row['status']) for row in attempts] == [('doc-a:1', 'collected')]
    assert len(snapshots) == 1
    assert (storage / snapshots[0]['storage_path']).read_bytes() == b'%PDF-1.4\nhello'

    second = Session(Response(304, headers={'ETag': 'one'}))
    harvest_documents(root, storage, timestamp='2026-09-29T15:00:00Z', session=second)
    _, attempts, snapshots = load_inputs(root)
    assert second.headers == [{'If-None-Match': 'one'}]
    assert [(row['retrieval_id'], row['status']) for row in attempts] == [
        ('doc-a:1', 'collected'), ('doc-a:2', 'not_modified')]
    assert attempts[0]['sha256'] == attempts[1]['sha256'] == snapshots[0]['sha256']
    assert len(snapshots) == 1


def test_rejected_response_records_gap_without_snapshot(tmp_path):
    root = ledger(tmp_path)
    harvest_documents(root, root / 'binary', session=Session(Response(403)))
    _, attempts, snapshots = load_inputs(root)
    assert attempts[0]['status'] == 'blocked'
    assert attempts[0]['sha256'] == ''
    assert snapshots == []


def test_html_challenge_cannot_replace_a_pdf(tmp_path):
    root = ledger(tmp_path)
    session = Session(Response(200, b'<html><title>Access denied</title></html>',
                               {'Content-Type': 'text/html'}))
    harvest_documents(root, root / 'binary', session=session)
    _, attempts, snapshots = load_inputs(root)
    assert attempts[0]['status'] == 'invalid_content'
    assert snapshots == []


def test_browser_saved_file_needs_matching_origin(tmp_path):
    root = ledger(tmp_path / 'ledger')
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    report = downloads / 'report.pdf'
    report.write_bytes(b'%PDF-1.4\nmanual')
    rows, skipped = collect_downloads(root, root / 'binary', downloads, {})
    assert rows == [] and len(skipped) == 1
    rows, skipped = collect_downloads(root, root / 'binary', downloads,
                                      {report: 'https://example.test/report.pdf'})
    assert not skipped
    assert rows[0]['collection_method'] == 'browser-manual'
    _, attempts, snapshots = load_inputs(root)
    assert attempts[0]['sha256'] == snapshots[0]['sha256']


def test_local_record_projection_is_never_harvested(tmp_path):
    root = ledger(tmp_path)
    schema = load_schema()
    documents, _, _ = load_inputs(root)
    documents.append(dict(documents[0], document_id='world-bank-projects-test',
                          url='https://example.test/projects.json'))
    write_table(root, 'documents', documents, schema=schema)
    write_table(root, 'retrievals', [dict(
        retrieval_id='world-bank-projects-test:1', document_id='world-bank-projects-test',
        retrieved_at='2026-09-28', status='collected', http_status='',
        content_type='application/json', etag='', last_modified='', final_url='',
        error='', sha256='a' * 64, collection_method='local-record')], schema=schema)
    session = Session(Response(200, b'%PDF-1.4\nhello'))
    harvested = harvest_documents(root, root / 'binary', session=session)
    assert [row['document_id'] for row in harvested] == ['doc-a']
    assert len(session.headers) == 1
    with pytest.raises(ValueError, match='local-record documents'):
        harvest_documents(root, root / 'binary', document_ids={'world-bank-projects-test'},
                          session=Session())
    documents, attempts, _ = load_inputs(root)
    assert 'https://example.test/projects.json' not in uncollected_documents(documents, attempts)
