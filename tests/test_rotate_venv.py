"""Tests for scripts/rotate-venv-to-shared.sh.

Rotates a real .venv directory into a symlink to the shared env on /data,
reclaiming /home space. The shared-env path is taken from $SHARED_ENV so the
test is hermetic (no dependency on /data existing).
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "rotate-venv-to-shared.sh"


def _run(target: Path, shared_env: Path):
    env = {**os.environ, "SHARED_ENV": str(shared_env)}
    return subprocess.run(
        ["bash", str(SCRIPT), str(target)],
        capture_output=True,
        text=True,
        env=env,
    )


def _make_real_venv(target: Path):
    venv = target / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr\n")
    return venv


@pytest.mark.integration
def test_real_venv_becomes_symlink(tmp_path):
    """A real .venv directory is replaced by a symlink to the shared env."""
    shared = tmp_path / "shared"
    shared.mkdir()
    target = tmp_path / "wt"
    target.mkdir()
    _make_real_venv(target)

    r = _run(target, shared)
    assert r.returncode == 0, r.stderr
    venv = target / ".venv"
    assert venv.is_symlink()
    assert os.readlink(venv) == str(shared)


@pytest.mark.integration
def test_idempotent(tmp_path):
    """Running twice is a no-op the second time (still a symlink, exit 0)."""
    shared = tmp_path / "shared"
    shared.mkdir()
    target = tmp_path / "wt"
    target.mkdir()
    _make_real_venv(target)

    _run(target, shared)
    r2 = _run(target, shared)
    assert r2.returncode == 0, r2.stderr
    assert (target / ".venv").is_symlink()


@pytest.mark.integration
def test_existing_symlink_left_intact(tmp_path):
    """An existing .venv symlink is not disturbed."""
    shared = tmp_path / "shared"
    shared.mkdir()
    target = tmp_path / "wt"
    target.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    (target / ".venv").symlink_to(other)

    r = _run(target, shared)
    assert r.returncode == 0, r.stderr
    assert os.readlink(target / ".venv") == str(other)


@pytest.mark.integration
def test_absent_venv_skipped(tmp_path):
    """No .venv → nothing created, no error."""
    shared = tmp_path / "shared"
    shared.mkdir()
    target = tmp_path / "wt"
    target.mkdir()

    r = _run(target, shared)
    assert r.returncode == 0, r.stderr
    assert not (target / ".venv").exists()


@pytest.mark.integration
def test_real_venv_kept_when_shared_env_absent(tmp_path):
    """Safety: a real .venv is NOT removed when the shared env does not exist."""
    shared = tmp_path / "does-not-exist"
    target = tmp_path / "wt"
    target.mkdir()
    venv = _make_real_venv(target)

    r = _run(target, shared)
    assert r.returncode == 0, r.stderr
    assert venv.is_dir() and not venv.is_symlink()


@pytest.mark.integration
def test_in_use_venv_kept(tmp_path):
    """Safety: a real .venv with an open file under it is not removed (lsof guard)."""
    if shutil.which("lsof") is None:
        pytest.skip("lsof not available — in-use guard cannot be exercised")
    shared = tmp_path / "shared"
    shared.mkdir()
    target = tmp_path / "wt"
    target.mkdir()
    venv = _make_real_venv(target)
    held = venv / "bin" / "held"
    held.write_text("x")
    with open(held):  # keep an fd open under the venv during the run
        r = _run(target, shared)
    assert r.returncode == 0, r.stderr
    assert venv.is_dir() and not venv.is_symlink()


@pytest.mark.integration
def test_multiple_targets(tmp_path):
    """All paths passed on the command line are rotated, not just the first."""
    shared = tmp_path / "shared"
    shared.mkdir()
    t1 = tmp_path / "a"
    t1.mkdir()
    _make_real_venv(t1)
    t2 = tmp_path / "b"
    t2.mkdir()
    _make_real_venv(t2)

    env = {**os.environ, "SHARED_ENV": str(shared)}
    r = subprocess.run(
        ["bash", str(SCRIPT), str(t1), str(t2)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    assert (t1 / ".venv").is_symlink()
    assert (t2 / ".venv").is_symlink()
