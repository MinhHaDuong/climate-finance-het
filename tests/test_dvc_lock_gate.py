"""Ticket 0362 — a corpus re-run must never publish dvc.lock to main on its own.

`scripts/run_corpus_pipeline.sh` used to branch, commit, merge into main and
`git push origin main` whenever `dvc.lock` was the only changed file. The
publish decision belongs to a human, behind the branch-and-PR gate.

The refusal lives in `scripts/dvc_lock_gate.sh` so it can be driven directly:
the tail of `run_corpus_pipeline.sh` is unreachable in a throwaway repo (the
padme / dvc / GROBID guards fire first). Each test spawns a real subprocess —
never source-in-shell — against a throwaway git repo.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "scripts" / "dvc_lock_gate.sh"

pytestmark = pytest.mark.integration


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def throwaway_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "dvc.lock").write_text("schema: '2.0'\n")
    (repo / "other.txt").write_text("hello\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "initial")
    # The gate lives outside the repo: a copy inside it would show up as an
    # untracked file and change the very `git status` the gate reads.
    shutil.copy(GATE, tmp_path / "dvc_lock_gate.sh")
    return repo


def _run_gate(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(repo.parent / "dvc_lock_gate.sh")],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_dvc_lock_change_is_refused_and_main_is_untouched(throwaway_repo: Path):
    repo = throwaway_repo
    before = _git(repo, "rev-parse", "main")

    (repo / "dvc.lock").write_text("schema: '2.0'\nchanged: true\n")
    result = _run_gate(repo)

    assert result.returncode != 0, (
        f"gate must exit non-zero when dvc.lock changed; got 0\n{result.stdout}"
    )
    assert _git(repo, "rev-parse", "main") == before, "main must not advance"
    assert _git(repo, "status", "--porcelain") != "", (
        "the change must be left in the working tree, not committed"
    )
    branches = _git(repo, "branch", "--format=%(refname:short)").split()
    assert branches == ["main"], f"gate must create no branch; found {branches}"
    assert "dvc.lock" in result.stdout, "the operator message must name dvc.lock"
    assert "0362" in result.stdout, "the message must cite the ticket"


def test_clean_tree_is_a_no_op(throwaway_repo: Path):
    result = _run_gate(throwaway_repo)
    assert result.returncode == 0, result.stderr
    assert "unchanged" in result.stdout


def test_other_files_changed_keeps_the_warning_path(throwaway_repo: Path):
    repo = throwaway_repo
    (repo / "other.txt").write_text("modified\n")
    result = _run_gate(repo)

    assert result.returncode == 0, result.stderr
    assert "WARNING" in result.stdout
    assert "other.txt" in result.stdout
    assert _git(repo, "status", "--porcelain") != ""


def test_pipeline_script_no_longer_pushes_to_main():
    text = (REPO / "scripts" / "run_corpus_pipeline.sh").read_text()
    assert "git push origin main" not in text, (
        "run_corpus_pipeline.sh must not push to main (ticket 0362)"
    )
    assert "dvc_lock_gate.sh" in text, "the tail must delegate to the gate helper"
