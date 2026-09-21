"""Registry-preserving checks for the observatory documents view."""

import pytest
from jetp._bundle_inventory import VIEWS, site_files
from jetp.build_observatory import documents_data

ROWS = [
    {'source_id': 'vnm-collected-pdf', 'country': 'VNM',
     'retrieved_at': '2026-09-11T20:39:00Z', 'status': 'collected',
     'content_type': 'application/pdf',
     'sha256': 'a' * 64, 'size_bytes': '120000',
     'storage_path': 'objects/aa/pdf.pdf',
     'final_url': 'https://example.test/rmp.pdf', 'error': ''},
    {'source_id': 'zaf-collected-html', 'country': 'ZAF',
     'retrieved_at': '2026-09-12T05:26:22Z', 'status': 'collected',
     'content_type': 'text/html; charset=utf-8',
     'sha256': 'b' * 64, 'size_bytes': '744406',
     'storage_path': 'objects/bb/reg.html',
     'final_url': 'https://example.test/register', 'error': ''},
    {'source_id': 'sen-blocked', 'country': 'SEN', 'retrieved_at': '',
     'status': 'blocked', 'content_type': '', 'sha256': '', 'size_bytes': '',
     'storage_path': '', 'final_url': 'https://example.test/sen',
     'error': 'HTTP 403'},
    {'source_id': 'idn-fetch-error', 'country': 'IDN', 'retrieved_at': '',
     'status': 'fetch_error', 'content_type': '', 'sha256': '',
     'size_bytes': '', 'storage_path': '',
     'final_url': 'https://example.test/idn', 'error': 'RetryError: ...'},
]


def build(tmp_path, rows=ROWS):
    """Write only the PDF's bytes, so availability cannot be read off status."""
    archived = tmp_path / 'data/jetp/documents/objects/aa'
    archived.mkdir(parents=True)
    (archived / 'pdf.pdf').write_bytes(b'%PDF-1.4\n')
    return documents_data(tmp_path, {'manifest': [dict(row) for row in rows]})


def entries(result):
    """Index the view by source identity for row-level assertions."""
    return {entry['id']: entry for entry in result['documents']}


def test_documents_view_keeps_every_registry_row_without_merging(tmp_path):
    """The registry is the only source of truth; no row is merged or invented."""
    by_id = entries(build(tmp_path))
    assert set(by_id) == {'vnm-collected-pdf', 'zaf-collected-html',
                          'sen-blocked', 'idn-fetch-error'}


def test_archived_copy_uses_the_registry_storage_path_verbatim(tmp_path):
    """Local paths come from the registry, never rebuilt from hash or type."""
    entry = entries(build(tmp_path))['vnm-collected-pdf']
    assert entry['local_path'] == 'documents/objects/aa/pdf.pdf'
    assert entry['country'] == 'VNM'
    assert entry['sha256'] == 'a' * 64
    assert entry['size_bytes'] == 120000
    assert entry['content_type'] == 'application/pdf'
    assert entry['collected_on'] == '2026-09-11T20:39:00Z'
    assert entry['url'] == 'https://example.test/rmp.pdf'


def test_collected_but_absent_snapshot_has_no_local_path(tmp_path):
    """Availability is a disk fact; a collected status cannot stand in for it."""
    entry = entries(build(tmp_path))['zaf-collected-html']
    assert entry['status'] == 'collected'
    assert entry['local_path'] is None


def test_failed_collections_keep_their_status_error_and_origin_url(tmp_path):
    """A blocked or failed source stays listed with its own recorded outcome."""
    by_id = entries(build(tmp_path))
    blocked, failed = by_id['sen-blocked'], by_id['idn-fetch-error']
    assert (blocked['status'], blocked['error']) == ('blocked', 'HTTP 403')
    assert (failed['status'], failed['error']) == ('fetch_error', 'RetryError: ...')
    assert blocked['url'] == 'https://example.test/sen'
    assert failed['url'] == 'https://example.test/idn'
    assert blocked['local_path'] is None
    assert failed['local_path'] is None
    assert blocked['size_bytes'] is None
    assert blocked['sha256'] is None
    assert blocked['collected_on'] is None
    assert blocked['content_type'] is None


def test_documents_view_is_ordered_deterministically_by_source_id(tmp_path):
    """A rebuilt view must be byte-stable, so ordering cannot follow file order."""
    result = build(tmp_path)
    assert [entry['id'] for entry in result['documents']] == sorted(
        row['source_id'] for row in ROWS)


def test_a_registry_path_escaping_the_snapshot_stops_the_build(tmp_path):
    """A link out of the site is a build failure, not a rendered anchor."""
    (tmp_path / 'data/jetp/documents').mkdir(parents=True)
    escaping = dict(ROWS[0], storage_path='../../../etc/passwd')
    with pytest.raises(ValueError, match='Unsafe source path'):
        documents_data(tmp_path, {'manifest': [escaping]})


def test_bundle_publishes_the_registry_view_but_never_archived_bytes(tmp_path):
    """The public edition carries the registry and origin URL, not the objects."""
    assert 'documents' in VIEWS
    site = tmp_path / 'site'
    (site / 'data').mkdir(parents=True)
    (site / 'data/documents.json').write_text('{}')
    (site / 'documents/objects/aa').mkdir(parents=True)
    (site / 'documents/objects/aa/pdf.pdf').write_bytes(b'%PDF-1.4\n')
    collected = {path.relative_to(site).as_posix() for path in site_files(site)}
    assert collected == {'data/documents.json'}


# Ticket 0853: twenty-one source identifiers carry more than one collection
# attempt, so the identifier is not a row key.  Two attempts of one source,
# in the two shapes the registry holds: same fingerprint (vnm-rmp-2023) and a
# different one (zaf-ntcsa-transmission-plans).
SHARED_ROWS = [
    dict(ROWS[0], sha256='c' * 64, storage_path='objects/cc/first.pdf'),
    dict(ROWS[0], retrieved_at='2026-09-13T08:00:00Z', sha256='c' * 64,
         storage_path='objects/cc/first.pdf'),
    dict(ROWS[1], sha256='d' * 64, storage_path='objects/dd/second.html'),
    dict(ROWS[1], retrieved_at='2026-09-14T08:00:00Z', sha256='e' * 64,
         storage_path='objects/ee/third.html'),
]


def test_shared_source_id_rows_get_distinct_row_keys_and_keep_their_source_id(tmp_path):
    """Two attempts of one source are two rows: distinct keys, same identifier,
    and the same keys again when the same registry is rebuilt."""
    result = build(tmp_path, rows=SHARED_ROWS)
    keys = [entry['row_key'] for entry in result['documents']]
    assert len(set(keys)) == len(SHARED_ROWS), keys
    assert [entry['id'] for entry in result['documents']] == sorted(
        row['source_id'] for row in SHARED_ROWS)
    for entry in result['documents']:
        assert entry['id'] in entry['row_key']
    rebuilt = documents_data(tmp_path, {'manifest': [dict(r) for r in SHARED_ROWS]})
    assert [entry['row_key'] for entry in rebuilt['documents']] == keys
