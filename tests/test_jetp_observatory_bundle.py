"""Recovery and candidate isolation for the accepted static observatory."""

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def site_hashes(root):
    """Include rendering assets and every download in the byte comparison."""
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


@pytest.mark.integration
def test_interrupted_candidate_preserves_accepted_and_restores_offline(tmp_path, monkeypatch):
    from jetp._observatory_bundle import build_candidate, freeze_bundle, restore_bundle

    accepted = tmp_path / 'accepted.zip'
    freeze_bundle(ROOT, accepted)
    archive_hash = hashlib.sha256(accepted.read_bytes()).hexdigest()
    canonical = site_hashes(ROOT / 'deliverables/jetp-observatory')
    candidate = tmp_path / 'candidate.zip'
    candidate.write_bytes(b'previous complete candidate')
    calls = []

    def interrupted(root, view, output):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"partial":true}')
        calls.append(view)
        raise RuntimeError('interrupted after one output')

    with pytest.raises(RuntimeError, match='interrupted'):
        build_candidate(ROOT, candidate, accepted=accepted, builder=interrupted)
    assert len(calls) == 1
    assert candidate.read_bytes() == b'previous complete candidate'
    assert hashlib.sha256(accepted.read_bytes()).hexdigest() == archive_hash
    assert site_hashes(ROOT / 'deliverables/jetp-observatory') == canonical

    def forbidden(*args, **kwargs):
        raise AssertionError('Restoration must not call Git, DVC or the network')

    monkeypatch.setattr('subprocess.run', forbidden)
    monkeypatch.setattr('subprocess.check_output', forbidden)
    monkeypatch.setattr('socket.create_connection', forbidden)
    restored = tmp_path / 'restored'
    restore_bundle(accepted, restored)
    assert site_hashes(restored) == canonical


def test_semantic_diff_requires_evidence_for_intentional_changes(tmp_path):
    """A declared scientific change needs source, reviewer and rationale."""
    from jetp._observatory_bundle import compare_bundles

    with pytest.raises(ValueError, match='source|reviewer|rationale'):
        compare_bundles(tmp_path / 'accepted.zip', tmp_path / 'candidate.zip',
                        intentional_paths={'site/data/ZAF.json/country/headline': {}})
