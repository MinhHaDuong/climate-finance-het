"""Tests for worktree setup: post-checkout hook and .worktreeinclude.

.worktreeinclude auto-copies .env and .dvc/config.local into worktrees
created by EnterWorktree. The post-checkout hook only co-locates the uv
environment; DVC data is populated on demand via `make data`, never
eagerly at checkout time.
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "hooks" / "post-checkout"
WORKTREEINCLUDE = REPO / ".worktreeinclude"
MAKEFILE = REPO / "Makefile"

# Class-guard thresholds for worktree creation (see test_worktree_creation_is_fast_and_light).
# A fresh worktree checks out only tracked source (~22 MB) and symlinks .venv;
# the two historical regressions copied ~1.7-1.8 GB. 200 MB sits far above the
# real tree yet far below any GB-scale eager copy, so it catches the whole class.
MAX_WORKTREE_MB = 200
MAX_CHECKOUT_SECONDS = 15


def test_worktreeinclude_copies_env():
    """.worktreeinclude must list .env for auto-copy into worktrees."""
    contents = WORKTREEINCLUDE.read_text()
    assert ".env" in contents


def test_worktreeinclude_copies_dvc_config():
    """.worktreeinclude must list .dvc/config.local for auto-copy."""
    contents = WORKTREEINCLUDE.read_text()
    assert ".dvc/config.local" in contents


def test_hook_does_not_eagerly_checkout_data():
    """The hook must NOT run dvc checkout: that copied ~1.7 GB of DVC data into
    every worktree, timing out creation. Data population moved to `make data`."""
    source = HOOK.read_text()
    assert "dvc checkout" not in source


def test_makefile_data_target_checks_out_dvc():
    """Data is populated on demand: `make data` runs dvc checkout from the local
    cache (no network), so a worktree fetches data only when it actually needs it."""
    source = MAKEFILE.read_text()
    assert "\ndata:" in source
    # the data target's recipe runs dvc checkout
    recipe = source.split("\ndata:", 1)[1].split("\n\n", 1)[0]
    assert "dvc checkout" in recipe


def test_hook_is_executable():
    """post-checkout must be executable."""
    assert HOOK.stat().st_mode & 0o111, "post-checkout hook is not executable"


def test_hook_points_venv_at_shared_env_on_data():
    """The hook must symlink .venv to a shared env that lives beside the uv
    cache on /data, so uv hardlinks wheels instead of copying ~1.8 GB per
    worktree (a cross-filesystem copy that makes worktree creation time out)."""
    source = HOOK.read_text()
    assert "/data/envs" in source
    assert "ln -s" in source and ".venv" in source


def test_hook_precreates_shared_env_before_symlinking():
    """A dangling .venv symlink makes `uv run` error, so the shared env must be
    created (uv venv) before the symlink is made."""
    source = HOOK.read_text()
    assert "uv venv" in source
    # uv venv must appear before the symlink in the source order.
    assert source.index("uv venv") < source.index("ln -s")


def test_hook_skips_shared_env_without_data_filesystem():
    """The shared-env step must be guarded so the default local .venv is used
    where /data is absent (portability to machines without the data disk)."""
    source = HOOK.read_text()
    assert "[ -d /data/envs ]" in source


def test_hook_replaces_stale_venv_symlink():
    """A dangling .venv symlink (target deleted) must not wedge the hook: use
    ln -sfn so the link is replaced idempotently rather than erroring on a
    pre-existing symlink, and only when .venv is absent or itself a symlink."""
    source = HOOK.read_text()
    assert "ln -sfn" in source
    assert "[ -L .venv ]" in source


def test_hook_serializes_concurrent_env_creation():
    """Concurrent worktree checkouts (parallel raids) must not race to build the
    shared env; the first-ever creation is serialized with flock."""
    source = HOOK.read_text()
    assert "flock" in source


def _tree_size_mb(root: Path) -> float:
    """On-disk size of a checked-out tree in MB, excluding .git and NOT following
    symlinks. A symlinked .venv contributes only the link, not its GB-scale
    target — which is exactly the behaviour we want to reward; an eagerly copied
    env or dvc-checked-out data would be a real directory and get counted."""
    total = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        if ".git" in dirnames:
            dirnames.remove(".git")
        for name in filenames:
            fp = Path(dirpath) / name
            try:
                total += fp.lstat().st_size  # lstat: size of the link, not its target
            except OSError:
                pass
    return total / (1024 * 1024)


@pytest.mark.integration
def test_worktree_creation_is_fast_and_light():
    """Behavioural class-guard: creating a worktree runs the post-checkout hook,
    which must stay fast and must not copy GB-scale artifacts into the tree.

    The two historical regressions (copying the ~1.8 GB uv env, checking out
    ~1.7 GB of DVC data) each made worktree creation time out. The source-
    inspection tests above catch those exact strings; this test catches the
    whole class — any new eager heavy step (an `uv sync`, a `dvc pull`, a large
    copy) shows up as either a slow checkout or a bloated tree, regardless of
    wording. Portable: does not require /data to exist. A symlinked .venv is
    fine (it points off-tree); a copied .venv directory is not."""
    parent = tempfile.mkdtemp(prefix="wt-speed-guard-")
    wt = Path(parent) / "wt"
    try:
        start = time.monotonic()
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", str(wt), "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        elapsed = time.monotonic() - start
        assert result.returncode == 0, f"git worktree add failed:\n{result.stderr}"

        assert elapsed < MAX_CHECKOUT_SECONDS, (
            f"worktree creation took {elapsed:.1f}s (> {MAX_CHECKOUT_SECONDS}s): "
            "the post-checkout hook likely reintroduced an eager heavy step."
        )

        size_mb = _tree_size_mb(wt)
        assert size_mb < MAX_WORKTREE_MB, (
            f"fresh worktree tree is {size_mb:.0f} MB (> {MAX_WORKTREE_MB} MB): "
            "the hook copied heavy artifacts (env or DVC data) into the worktree "
            "instead of symlinking/deferring them."
        )

        # If .venv was materialised at checkout, it must be a symlink (off-tree),
        # never a copied directory. Absent .venv is fine (uv creates it lazily,
        # or /data is missing) — we only reject the copied-directory regression.
        venv = wt / ".venv"
        if venv.exists() or venv.is_symlink():
            assert venv.is_symlink(), (
                ".venv is a real directory in a fresh worktree: the hook copied "
                "the env instead of symlinking it to the shared env on /data."
            )
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=REPO,
            capture_output=True,
        )
        subprocess.run(["git", "worktree", "prune"], cwd=REPO, capture_output=True)
        shutil.rmtree(parent, ignore_errors=True)
