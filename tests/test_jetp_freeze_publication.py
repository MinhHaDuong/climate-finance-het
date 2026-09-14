"""Freezing cannot replace a baseline, even when the destination appears late."""

import copy

import pytest

from jetp import _observatory_bundle as bundles
from test_jetp_observatory_bundle import tiny_bundle


@pytest.fixture
def capture(tmp_path, monkeypatch):
    """Supply a complete new snapshot without invoking Git or the exporter."""
    accepted = tmp_path / 'accepted.zip'
    tiny_bundle(accepted)
    manifest, payloads = bundles._read_bundle(accepted)
    manifest.update(sources=[], captured_git_sha='next-capture')
    root = tmp_path / 'checkout'
    (root / 'deliverables/jetp-observatory').mkdir(parents=True)
    monkeypatch.setattr(bundles, '_capture', lambda *args: (copy.deepcopy(manifest), payloads.copy()))
    return root, accepted


def occupy(output, reference, kind):
    """Create each kind of destination entry that publication must preserve."""
    if kind == 'file':
        output.write_bytes(reference.read_bytes())
    elif kind == 'hardlink':
        output.hardlink_to(reference)
    else:
        output.symlink_to(reference if kind == 'symlink' else reference.with_name('missing'))


def assert_preserved(output, reference, kind, before):
    assert reference.read_bytes() == before
    if kind in ('symlink', 'dangling'):
        assert output.is_symlink()
        assert output.readlink() == (reference if kind == 'symlink' else reference.with_name('missing'))
    if kind == 'dangling':
        assert not output.exists()
    else:
        assert output.read_bytes() == before


@pytest.mark.parametrize('kind', ['file', 'symlink', 'hardlink', 'dangling'])
def test_freeze_rejects_existing_entries_before_capture(capture, tmp_path, monkeypatch, kind):
    root, accepted = capture
    before = accepted.read_bytes()
    output = tmp_path / 'baseline.zip'
    occupy(output, accepted, kind)

    def forbidden_capture(*args):
        raise AssertionError('An existing freeze destination must be rejected before capture')

    monkeypatch.setattr(bundles, '_capture', forbidden_capture)
    with pytest.raises(FileExistsError):
        bundles.freeze_bundle(root, output)
    assert_preserved(output, accepted, kind, before)


@pytest.mark.parametrize('kind', ['file', 'symlink', 'hardlink', 'dangling'])
def test_freeze_publication_cannot_clobber_a_late_destination(capture, tmp_path, monkeypatch, kind):
    root, accepted = capture
    before = accepted.read_bytes()
    output = tmp_path / 'new-baseline.zip'
    original_capture = bundles._capture

    def racing_capture(*args):
        snapshot = original_capture(*args)
        occupy(output, accepted, kind)
        return snapshot

    monkeypatch.setattr(bundles, '_capture', racing_capture)
    with pytest.raises(FileExistsError):
        bundles.freeze_bundle(root, output)
    assert_preserved(output, accepted, kind, before)


def test_freeze_creates_a_new_complete_bundle(capture, tmp_path):
    root, accepted = capture
    before = accepted.read_bytes()
    output = tmp_path / 'new-baseline.zip'
    bundles.freeze_bundle(root, output)
    manifest, _ = bundles._read_bundle(output)
    assert manifest['kind'] == 'baseline'
    assert manifest['captured_git_sha'] == 'next-capture'
    assert accepted.read_bytes() == before


def test_candidate_still_replaces_an_existing_complete_bundle(capture, tmp_path):
    root, accepted = capture
    before = accepted.read_bytes()
    output = tmp_path / 'candidate.zip'
    output.write_bytes(before)
    bundles.build_candidate(root, output, accepted=accepted, builder=lambda *args: None)
    manifest, _ = bundles._read_bundle(output)
    assert manifest['kind'] == 'candidate'
    assert output.read_bytes() != before
    assert accepted.read_bytes() == before
