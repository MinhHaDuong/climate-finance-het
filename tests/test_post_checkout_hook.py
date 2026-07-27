"""Tests for worktree setup: post-checkout hook and .worktreeinclude.

.worktreeinclude auto-copies .env and .dvc/config.local into worktrees
created by EnterWorktree. The post-checkout hook wires up the two shared,
off-tree resources — the uv environment and the DVC cache — by symlink. DVC
*data* is populated on demand via `make data`, never eagerly at checkout time.
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".githooks" / "post-checkout"
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


def test_hook_points_dvc_cache_at_the_shared_cache():
    """A worktree must share the primary checkout's DVC cache.

    `.dvc/` is not tracked wholesale: a worktree gets `config` from git and
    `config.local` from .worktreeinclude, but the cache is gitignored, so a
    fresh worktree starts with an empty private cache — and `config.local`
    carries only the remote URL, never cache.dir. `make data` (dvc checkout)
    then searches that empty cache and fails, which is what pushed corpus work
    back into the primary checkout (ticket 0360, via 0347).

    Symlinking is the same idiom the hook already uses for .venv. It is what
    makes `make data` able to find anything at all; it does not make the data
    free. cache.type is unset, so DVC's default is `copy` and each worktree that
    asks for data spends ~2.2 GB. Hardlinking would remove that cost and is
    rejected: Phase-1 scripts rewrite data/catalogs/*.csv in place, and a
    hardlinked checkout shares the cache blob's inode, so one rewrite would
    corrupt the cache for every checkout at once."""
    source = HOOK.read_text()
    assert ".dvc/cache" in source
    # The path must be derived from the repo, not hard-coded, so the fix
    # survives a clone somewhere else.
    assert "--git-common-dir" in source


def _dvc_block(source: str) -> str:
    """The hook's DVC-cache section, from its heading comment to end of file.

    Anchoring on the heading keeps the assertions below non-vacuous no matter
    how the comment above it grows; an offset window around the first literal
    `.dvc/cache` happened to work but would silently start covering the .venv
    block's `ln -sfn` after any edit that shifted it."""
    marker = "# Share the primary checkout's DVC cache."
    assert marker in source, "DVC-cache section heading not found in the hook"
    return source.split(marker, 1)[1]


def test_hook_replaces_stale_dvc_cache_symlink():
    """Same idempotence contract as .venv: replace a dangling or stale link
    rather than erroring, and never clobber a real cache directory that a
    standalone (non-worktree) checkout legitimately owns."""
    dvc_block = _dvc_block(HOOK.read_text())
    assert "ln -sfn" in dvc_block
    assert "-L .dvc/cache" in dvc_block


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


def _shared_cache() -> Path:
    """The DVC cache the hook should link to: the primary checkout's.

    Derived the same way the hook derives it, from --git-common-dir, so the
    expectation holds whether the suite runs in the primary checkout or in a
    worktree (REPO is itself a worktree during most agent sessions)."""
    common_dir = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.strip()
    return (Path(common_dir).resolve().parent / ".dvc" / "cache").resolve()


@pytest.mark.integration
def test_hook_never_clobbers_a_real_dvc_cache_directory():
    """The highest-consequence guard, tested behaviourally rather than by
    substring: a checkout that owns a real .dvc/cache directory keeps it.

    Only worktrees should be relinked. A standalone clone's cache is the only
    copy of its blobs, so replacing that directory with a symlink would orphan
    every one of them. The source pin above ("-L .dvc/cache") states the
    intent; this proves the shell actually honours it, sentinel and all.

    The assertion that bites is the directory-contents one, and the first draft
    of this test lacked it and passed with the guard deleted. `ln -sfn` does not
    clobber an existing *directory*: it creates the link inside it, leaving
    .dvc/cache/cache dangling off a real cache. That is the actual failure mode
    here, and it is invisible to an is_symlink()/sentinel check alone."""
    shared_cache = _shared_cache()
    if not shared_cache.is_dir():
        pytest.skip(f"no primary DVC cache at {shared_cache}; guard is unreachable")
    parent = tempfile.mkdtemp(prefix="wt-dvc-own-cache-")
    wt = Path(parent) / "wt"
    try:
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", str(wt), "HEAD"],
            cwd=REPO, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"git worktree add failed:\n{result.stderr}"

        # Stand in for a standalone checkout: a real cache directory holding a
        # blob that exists nowhere else.
        own_cache = wt / ".dvc" / "cache"
        own_cache.mkdir(parents=True, exist_ok=True)
        sentinel = own_cache / "sentinel-blob"
        sentinel.write_text("the only copy")

        hook = subprocess.run(["sh", str(HOOK)], cwd=wt, capture_output=True, text=True)
        assert hook.returncode == 0, f"post-checkout hook failed:\n{hook.stderr}"

        assert not own_cache.is_symlink(), (
            "the hook replaced a real .dvc/cache directory with a symlink: on a "
            "standalone checkout that orphans every blob in it."
        )
        assert own_cache.is_dir()
        assert sentinel.read_text() == "the only copy"
        assert sorted(p.name for p in own_cache.iterdir()) == ["sentinel-blob"], (
            "the hook wrote into a real .dvc/cache directory: ln -sfn onto an "
            "existing directory nests the link inside it (.dvc/cache/cache) "
            "rather than replacing it, so the guard must skip the link entirely."
        )
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=REPO, capture_output=True,
        )
        subprocess.run(["git", "worktree", "prune"], cwd=REPO, capture_output=True)
        shutil.rmtree(parent, ignore_errors=True)


@pytest.mark.integration
def test_fresh_worktree_shares_the_primary_dvc_cache():
    """Behavioural guard: a fresh worktree must resolve DVC's cache to the
    primary checkout's, so `make data` can check the corpus out of it.

    Source inspection above pins the hook's wording; this pins the outcome. It
    is the check that would have caught ticket 0360 — from the primary checkout
    everything looks fine, and the failure appears only inside a worktree, which
    is why it survived until a corpus rerun was pushed out of one.

    Asserts the link resolves to the shared cache AND that the worktree holds no
    real cache directory of its own, so a regression to per-worktree copying is
    caught by structure rather than by a GB-scale surprise later.

    The hook is invoked explicitly rather than relied upon to fire from
    `git worktree add`: whether git runs it depends on `core.hooksPath`, which
    is machine-local config this test has no business asserting. Driving the
    hook directly tests the hook's own behaviour, deterministically, on any
    checkout."""
    shared_cache = _shared_cache()
    if not shared_cache.is_dir():
        pytest.skip(
            f"no primary DVC cache at {shared_cache} (fresh clone before the "
            "first dvc pull): the hook correctly no-ops, nothing to assert"
        )
    parent = tempfile.mkdtemp(prefix="wt-dvc-cache-")
    wt = Path(parent) / "wt"
    try:
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", str(wt), "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"git worktree add failed:\n{result.stderr}"

        # Run the working-tree hook, not the fresh worktree's copy: the
        # worktree is checked out at HEAD, so its copy would be the committed
        # version and the test would grade the last commit instead of the
        # change under test.
        hook = subprocess.run(["sh", str(HOOK)],
                              cwd=wt, capture_output=True, text=True)
        assert hook.returncode == 0, f"post-checkout hook failed:\n{hook.stderr}"

        cache = wt / ".dvc" / "cache"
        assert cache.is_symlink(), (
            ".dvc/cache in a fresh worktree is not a symlink: the worktree has a "
            "private cache, so `make data` (dvc checkout) finds nothing and "
            "corpus work gets pushed back into the primary checkout (0360)."
        )
        assert cache.resolve() == shared_cache, (
            f".dvc/cache points at {cache.resolve()}, expected {shared_cache}"
        )
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=REPO,
            capture_output=True,
        )
        subprocess.run(["git", "worktree", "prune"], cwd=REPO, capture_output=True)
        shutil.rmtree(parent, ignore_errors=True)
