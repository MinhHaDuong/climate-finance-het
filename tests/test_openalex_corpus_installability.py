"""Installability guards for the ``openalex-corpus`` path package.

Ticket 0211. The package's 25-test suite ran only standalone, so a clean-install
defect shipped to review: the package declared only ``pandas`` while
``crawl.py`` imports ``requests``. The shared dev env already had ``requests``,
so "green" masked a broken install (fixed in #956).

These two tests close that gap in a way a shared warm env cannot:

1. ``test_installs_cleanly_with_declared_deps`` — install the real package into
   a throwaway venv and exercise the HTTP layer. Regression guard: proves #956
   holds (all runtime imports are covered by declared deps).
2. ``test_installability_guard_catches_undeclared_dep`` — install a COPY whose
   ``requests`` dependency has been stripped, then import the submodule that
   needs it. Mutation-proof by construction: it reproduces the historical defect
   every run, so it can never rot into a tautology. It imports
   ``openalex_corpus.crawl`` (not bare ``openalex_corpus``): PEP 562 lazy
   ``__init__`` lets the bare import succeed without ``requests``; only the lazy
   submodule import surfaces the missing dependency.

Both spawn ``uv``/``python`` subprocesses against a ``tmp_path`` venv. They read
the shared uv cache read-only and never touch the project ``.venv`` or the
shared ``/data`` env — no ``uv sync``, nothing lands in git status.
See memory ``feedback_isolated_venv_proves_installability``.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_PKG_DIR = Path(__file__).resolve().parent.parent / "libs" / "openalex-corpus"

pytestmark = pytest.mark.integration


def _uv() -> str:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not on PATH")
    return uv


def _make_venv(uv: str, root: Path) -> Path:
    """Create an isolated venv under ``root`` and return its python interpreter."""
    venv = root / ".venv-check"
    subprocess.run([uv, "venv", str(venv)], check=True,
                   capture_output=True, text=True)
    py = venv / "bin" / "python"
    assert py.exists(), f"venv python missing: {py}"
    return py


def _install(uv: str, py: Path, pkg_dir: Path) -> subprocess.CompletedProcess:
    """Non-editable install of ``pkg_dir`` into the venv at ``py``."""
    return subprocess.run(
        [uv, "pip", "install", "--python", str(py), str(pkg_dir)],
        capture_output=True, text=True)


def _run_import(py: Path, code: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(py), "-c", code], capture_output=True, text=True)


def test_installs_cleanly_with_declared_deps(tmp_path):
    """The real package installs into a fresh venv and its HTTP layer imports."""
    uv = _uv()
    py = _make_venv(uv, tmp_path)
    install = _install(uv, py, _PKG_DIR)
    assert install.returncode == 0, f"install failed:\n{install.stderr}"

    # Exercise the lazy submodules that pull the third-party deps: crawl needs
    # requests, embedding path needs pandas via text/embedding conventions.
    check = _run_import(
        py,
        "import openalex_corpus; "
        "from openalex_corpus import retry_get, build_text, normalize_doi; "
        "import openalex_corpus.crawl; "
        "assert callable(retry_get)",
    )
    assert check.returncode == 0, (
        f"clean-install import failed:\n{check.stderr}")


def test_installability_guard_catches_undeclared_dep(tmp_path):
    """Stripping a declared runtime dep makes the dependent import fail.

    This is the mutation the guard must catch. If a future edit imports a new
    third-party module without declaring it, a clean install omits the module
    and this failure mode reproduces — surfaced by importing the submodule, not
    the lazy top-level package.
    """
    uv = _uv()

    # Copy the package and strip `requests` from its declared dependencies.
    pkg_copy = tmp_path / "pkg"
    shutil.copytree(_PKG_DIR, pkg_copy)
    manifest = pkg_copy / "pyproject.toml"
    text = manifest.read_text()
    stripped = text.replace('    "requests",\n', "")
    assert stripped != text, "expected to strip a `requests` dependency line"
    manifest.write_text(stripped)

    py = _make_venv(uv, tmp_path)
    install = _install(uv, py, pkg_copy)
    assert install.returncode == 0, f"stripped install failed:\n{install.stderr}"

    # Bare import stays lazy (PEP 562) and would succeed without requests; the
    # submodule import is what surfaces the undeclared dependency.
    submodule = _run_import(py, "import openalex_corpus.crawl")
    assert submodule.returncode != 0, (
        "guard is toothless: importing openalex_corpus.crawl succeeded even "
        "though requests was undeclared and uninstalled")
    assert "ModuleNotFoundError" in submodule.stderr or \
           "No module named 'requests'" in submodule.stderr, (
        f"expected a missing-requests failure, got:\n{submodule.stderr}")

    # Sanity: the bare package import DOES survive (proves the guard needs the
    # submodule import, not that the whole package is uninstallable).
    bare = _run_import(py, "import openalex_corpus")
    assert bare.returncode == 0, (
        f"bare import should stay lazy-safe without requests:\n{bare.stderr}")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
