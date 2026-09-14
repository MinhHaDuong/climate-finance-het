"""Offline source recovery from the pinned local DVC object cache."""

import hashlib
import json

import pytest
from jetp._bundle_inventory import source_inventory


def cached_source(tmp_path):
    """Create a valid pinned DVC index with one locally cached source."""
    corpus = tmp_path / 'data/jetp'
    corpus.mkdir(parents=True)
    data = b'collected scientific source'
    sha = hashlib.sha256(data).hexdigest()
    md5 = hashlib.md5(data).hexdigest()
    relative = f'objects/{sha[:2]}/{sha}.pdf'
    index = json.dumps([{'md5': md5, 'relpath': relative}]).encode()
    index_md5 = hashlib.md5(index).hexdigest()
    cache = tmp_path / '.dvc/cache/files/md5'
    for identity, contents in ((md5, data), (index_md5 + '.dir', index)):
        path = cache / identity[:2] / identity[2:]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    (corpus / 'documents.dvc').write_text(f'outs:\n- md5: {index_md5}.dir\n  path: documents\n')
    (corpus / 'manifest.csv').write_text(
        f'source_id,status,sha256,storage_path\nsource,collected,{sha},{relative}\n')
    return cache / md5[:2] / md5[2:], cache / index_md5[:2] / (index_md5[2:] + '.dir')


def test_missing_checkout_recovers_verified_source_from_pinned_cache(tmp_path):
    cached, _ = cached_source(tmp_path)
    payloads = {}
    source, = source_inventory(tmp_path, tmp_path, payloads, True)
    assert source['verified'] is True
    assert source['embedded'] is True
    assert source['recovery_location'] == str(cached)
    assert source['dvc_md5'] == hashlib.md5(cached.read_bytes()).hexdigest()
    assert list(payloads.values()) == [cached.read_bytes()]


def test_corrupt_directory_index_cannot_supply_recovery_evidence(tmp_path):
    _, index = cached_source(tmp_path)
    index.write_text('[]')
    with pytest.raises(ValueError, match='DVC.*hash mismatch'):
        source_inventory(tmp_path, tmp_path, {}, False)


def test_corrupt_cached_source_is_rejected(tmp_path):
    cached, _ = cached_source(tmp_path)
    cached.write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='hash mismatch'):
        source_inventory(tmp_path, tmp_path, {}, False)
