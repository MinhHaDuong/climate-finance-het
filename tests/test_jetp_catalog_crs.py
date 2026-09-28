"""The frozen CRS collector must not archive failed API responses."""

import gzip
import io
import urllib.error

import pytest
from jetp.catalog_crs import fetch, pull_year

pytestmark = pytest.mark.wp_jetp


@pytest.mark.parametrize('failure', ['404', 'empty'])
@pytest.mark.parametrize('existing', [False, True])
def test_failed_crs_response_does_not_create_or_replace_archive(
        monkeypatch, tmp_path, failure, existing):
    target = tmp_path / 'crs_IDN_2020_micro.csv.gz'
    original = gzip.compress(b'valid archived CRS data\n', mtime=0)
    if existing:
        target.write_bytes(original)

    def response(request, timeout):
        assert timeout == 900
        if failure == '404':
            raise urllib.error.HTTPError(
                request.full_url, 404, 'Not Found', {}, io.BytesIO(b'missing'))
        return io.BytesIO(b'')

    monkeypatch.setattr('jetp.catalog_crs.urllib.request.urlopen', response)
    with pytest.raises(ValueError, match='returned 404|empty response'):
        pull_year('IDN', 2020, ['23210'], 'DD', tmp_path, force=True)

    if existing:
        assert target.read_bytes() == original
    else:
        assert not target.exists()


def test_exhausted_crs_request_fails_the_collection(monkeypatch):
    def unavailable(request, timeout):
        raise urllib.error.URLError('offline')

    monkeypatch.setattr('jetp.catalog_crs.urllib.request.urlopen', unavailable)
    with pytest.raises(RuntimeError, match='failed after 1 attempts'):
        fetch('https://example.test/crs', retries=1, pause=0)


def test_successful_crs_response_still_writes_archive(monkeypatch, tmp_path):
    raw = b'RECIPIENT,TIME_PERIOD\nIDN,2020\n'
    monkeypatch.setattr('jetp.catalog_crs.urllib.request.urlopen',
                        lambda request, timeout: io.BytesIO(raw))

    target = pull_year('IDN', 2020, ['23210'], 'DD', tmp_path, force=False)

    assert gzip.decompress(target.read_bytes()) == raw
