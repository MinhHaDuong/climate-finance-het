"""Worktree initialization must make JETP bytes available without shared writes."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".githooks" / "post-checkout"
DOCUMENTS = Path("data/jetp/documents")
pytestmark = pytest.mark.integration


def run(*args, cwd, env=None):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, check=True)


@pytest.fixture
def snapshot_worktree():
    # Reflinks need a supporting filesystem. Keep the fixture beside the repo:
    # /tmp may be tmpfs even when the worktrees themselves live on btrfs.
    scratch = REPO / ".pytest_cache"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="jetp-hook-", dir=scratch) as parent:
        main = Path(parent) / "main checkout"
        main.mkdir()
        run("git", "init", "-q", cwd=main)
        pointer = main / "data/jetp/documents.dvc"
        pointer.parent.mkdir(parents=True)
        pointer.write_text("outs:\n- md5: pinned.dir\n  path: documents\n")
        run("git", "add", ".", cwd=main)
        run("git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=Test",
            "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture", cwd=main)
        source = main / DOCUMENTS
        (source / "objects/aa").mkdir(parents=True)
        (source / "objects/aa/snapshot.pdf").write_bytes(b"%PDF-fixture")
        worktree = Path(parent) / "feature checkout"
        run("git", "-c", "core.hooksPath=/dev/null", "worktree", "add",
            "--detach", str(worktree), cwd=main)
        yield main, worktree, source


def invoke_hook(worktree, **overrides):
    env = {"PATH": os.environ["PATH"], **overrides}
    return run("sh", str(HOOK), cwd=worktree, env=env)


def require_reflink(source, worktree):
    probe = worktree / "probe.pdf"
    result = subprocess.run(
        ["cp", "--reflink=always", str(source / "objects/aa/snapshot.pdf"), str(probe)],
        capture_output=True, text=True,
    )
    probe.unlink(missing_ok=True)
    if result.returncode:
        pytest.skip("filesystem does not support reflinks; fallback tests still run")


def test_initialization_clones_bytes_with_private_inodes_and_is_idempotent(snapshot_worktree):
    main, worktree, source = snapshot_worktree
    require_reflink(source, worktree)
    # Exercise Git's real initialization path, including the configured hook.
    run("git", "config", "core.hooksPath", str(HOOK.parent), cwd=main)
    fresh = worktree.parent / "fresh checkout"
    run("git", "worktree", "add", "--detach", str(fresh), cwd=main)
    document = fresh / DOCUMENTS / "objects/aa/snapshot.pdf"
    original = source / "objects/aa/snapshot.pdf"
    assert document.read_bytes() == original.read_bytes()
    assert document.stat().st_ino != original.stat().st_ino
    assert not (fresh / DOCUMENTS).is_symlink()
    document.write_bytes(b"local edit")
    invoke_hook(fresh)
    assert document.read_bytes() == b"local edit"
    assert original.read_bytes() == b"%PDF-fixture"


@pytest.mark.parametrize("existing", ["directory", "file", "symlink", "dangling"])
def test_initialization_preserves_existing_documents(snapshot_worktree, existing):
    _, worktree, source = snapshot_worktree
    destination = worktree / DOCUMENTS
    if existing == "directory":
        destination.mkdir()
        (destination / "local-only").write_text("keep me")
    elif existing == "file":
        destination.write_text("keep me")
    else:
        destination.symlink_to(source if existing == "symlink" else source / "absent")
    before = destination.lstat()
    invoke_hook(worktree)
    assert destination.lstat() == before
    if existing == "directory":
        assert list(destination.iterdir()) == [destination / "local-only"]
        assert (destination / "local-only").read_text() == "keep me"


@pytest.mark.parametrize("unavailable", ["missing", "different_pointer", "no_reflink"])
def test_unavailable_snapshot_warns_without_leaving_partial_data(snapshot_worktree, unavailable):
    main, worktree, source = snapshot_worktree
    overrides = {}
    if unavailable == "missing":
        source.rename(source.with_name("unavailable"))
    elif unavailable == "different_pointer":
        (main / "data/jetp/documents.dvc").write_text("other revision\n")
    else:
        # A deliberately failing cp verifies no retry as a full copy, and
        # cleanup even after the reflink operation wrote a partial file.
        bindir = main / "bin"
        bindir.mkdir()
        copier = bindir / "cp"
        copier.write_text(
            '#!/bin/sh\n'
            f'echo called >> "{main}/cp-calls"\n'
            'for last do :; done\nmkdir -p "$last"\ntouch "$last/partial"\n'
            'case " $* " in *" --reflink=always "*) exit 1 ;; esac\n'
        )
        copier.chmod(0o755)
        overrides["PATH"] = f"{bindir}:{os.environ['PATH']}"
    result = invoke_hook(worktree, **overrides)
    assert not (worktree / DOCUMENTS).exists()
    assert "make jetp-data" in result.stderr
    assert sorted(path.name for path in (worktree / "data/jetp").iterdir()) == ["documents.dvc"]
    if unavailable == "no_reflink":
        assert (main / "cp-calls").read_text().splitlines() == ["called"]


def test_configured_snapshot_source_is_cloned(snapshot_worktree):
    _, worktree, source = snapshot_worktree
    require_reflink(source, worktree)
    configured = source.parent / "external snapshot"
    source.rename(configured)
    configured.with_suffix(".dvc").write_bytes(source.with_suffix(".dvc").read_bytes())
    invoke_hook(worktree, JETP_SNAPSHOT_SOURCE=str(configured))
    assert (worktree / DOCUMENTS / "objects/aa/snapshot.pdf").read_bytes() == b"%PDF-fixture"
