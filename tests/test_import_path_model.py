"""Import-path model contract (ticket 0253, epic 0240 wave-0b).

The repo resolves flat module names (``from utils import …``,
``from script_io_args import …``, ``import openalex_corpus``) via **relative
source roots** rather than a per-context hack, so an entry point keeps working
after it moves into a ``scripts/<phase>/`` subdir (the bulk moves are 0255-0258).

Two source roots carry the model:

- ``scripts`` — the flat pipeline modules (utils, pipeline_io, plot_style, …).
- ``libs/openalex-corpus/src`` — the ``openalex_corpus`` convention package,
  now imported *as source* rather than as a non-editable wheel.

pytest gets them via ``[tool.pytest.ini_options] pythonpath``; every Make/`.mk`
script invocation gets them via the top-level ``export PYTHONPATH``. Both
replace the retired ``tests/conftest.py`` ``sys.path.insert`` and the retired
``[tool.uv.sources]`` local install.

These contract tests (adherence) pin the config; the pilot test (integration)
proves the model end to end on one file moved into ``scripts/figures/``.
"""

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOTS = ["scripts", "libs/openalex-corpus/src"]
PILOT = "scripts/figures/plot_schematic_L3_burst.py"


def _pyproject() -> dict:
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


class TestPathModelConfig:
    """Config-level contract for the relative-source-root import model."""

    pytestmark = pytest.mark.adherence

    def test_pytest_declares_source_roots(self):
        """pytest resolves flat imports via pythonpath source roots."""
        cfg = _pyproject()["tool"]["pytest"]["ini_options"]
        pythonpath = cfg.get("pythonpath", [])
        for root in SOURCE_ROOTS:
            assert root in pythonpath, (
                f"[tool.pytest.ini_options] pythonpath must include {root!r}; "
                f"got {pythonpath}"
            )

    def test_conftest_has_no_scripts_syspath_hack(self):
        """The conftest path-injection hack is retired — pythonpath replaces it."""
        # Strip comments so a comment *naming* the retired hack does not trip the
        # guard; only an executable injection call should fail it.
        code_lines = [
            ln.split("#", 1)[0]
            for ln in (REPO_ROOT / "tests" / "conftest.py").read_text().splitlines()
        ]
        code = "\n".join(code_lines)
        assert "sys.path.insert" not in code and "sys.path.append" not in code, (
            "tests/conftest.py must not inject scripts/ onto sys.path — the "
            "pytest pythonpath source root replaces that hack (ticket 0253)."
        )

    def test_makefile_exports_pythonpath(self):
        """Every Make script invocation resolves flat imports via exported PYTHONPATH."""
        src = (REPO_ROOT / "Makefile").read_text()
        assert "export PYTHONPATH" in src, "Makefile must export PYTHONPATH"
        # The export line must carry both source roots.
        export_lines = [
            ln for ln in src.splitlines() if ln.strip().startswith("export PYTHONPATH")
        ]
        assert export_lines, "no `export PYTHONPATH` line found in Makefile"
        joined = "\n".join(export_lines)
        for root in SOURCE_ROOTS:
            assert root in joined, (
                f"Makefile PYTHONPATH export must include {root!r}; got:\n{joined}"
            )

    def test_openalex_corpus_not_a_local_install(self):
        """The non-editable wheel is retired: no dependency, no path source.

        The package is imported as source via PYTHONPATH. Its standalone
        packaging (`libs/openalex-corpus/pyproject.toml`) is retained for
        git-source consumers (AEDIST, ticket 0229) and is unaffected.
        """
        proj = _pyproject()
        deps = proj["project"]["dependencies"]
        assert not any("openalex-corpus" in d for d in deps), (
            "openalex-corpus must not be a [project] dependency — this repo "
            "imports it as source via PYTHONPATH (ticket 0253)."
        )
        sources = proj.get("tool", {}).get("uv", {}).get("sources", {})
        assert "openalex-corpus" not in sources, (
            "openalex-corpus must not be a [tool.uv.sources] local path install."
        )

    def test_libs_package_pyproject_retained(self):
        """The standalone package config stays for git-source consumers (0229)."""
        assert (REPO_ROOT / "libs" / "openalex-corpus" / "pyproject.toml").exists()


class TestPilotSubdirResolution:
    """The pilot: one entry point moved into scripts/figures/ resolves flat imports.

    Runs the moved script the way the Makefile does — a bare interpreter
    invocation with the two source roots on PYTHONPATH. Reaching argument
    parsing proves every module-level ``from utils import …`` /
    ``import openalex_corpus`` resolved from the subdir; an unresolved flat
    import would abort with ModuleNotFoundError before argparse runs.
    """

    @pytest.mark.integration
    def test_pilot_resolves_flat_imports_from_subdir(self):
        assert (REPO_ROOT / PILOT).exists(), f"pilot file missing: {PILOT}"
        env = {**os.environ, "PYTHONPATH": os.pathsep.join(SOURCE_ROOTS)}
        result = subprocess.run(
            [sys.executable, PILOT, "--output", "/tmp/_pilot_import_probe.png"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        for marker in ("ModuleNotFoundError", "ImportError", "No module named"):
            assert marker not in result.stderr, (
                f"pilot {PILOT} failed to resolve a flat import from its subdir:\n"
                f"{result.stderr[-1500:]}"
            )
