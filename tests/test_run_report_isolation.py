"""Tests must not write run reports into the real corpus directory.

Ticket 0346. `data/catalogs/run_reports/` is a DVC output. Six fixture files
were being rewritten there on every suite run — for four and a half months, and
into four committed DVC snapshots — by two independent mechanisms:

1. Patching ``utils.CATALOGS_DIR`` when ``save_run_report`` resolves
   ``pipeline_loaders.CATALOGS_DIR`` inside its own body. The patch is a no-op
   and the test still reports green.
2. Spawning a script as a subprocess with ``cwd=REPO_ROOT`` and no
   ``CLIMATE_FINANCE_DATA`` in its environment. A monkeypatch cannot cross a
   process boundary; the child resolves the real directory.

Both guards below are on the mechanism, not on the six filenames, so a new test
written the old way fails immediately rather than quietly polluting the corpus.
"""

import ast
import os
import re

import pytest
from utils import BASE_DIR

TESTS_DIR = os.path.join(BASE_DIR, "tests")


def _test_sources():
    for name in sorted(os.listdir(TESTS_DIR)):
        if name.startswith("test_") and name.endswith(".py"):
            path = os.path.join(TESTS_DIR, name)
            with open(path, encoding="utf-8") as fh:
                yield name, fh.read()


@pytest.mark.adherence
def test_no_test_patches_catalogs_dir_on_the_facade():
    """Patch the module that defines the constant, not a re-export of it.

    ``scripts/utils.py`` re-exports ``CATALOGS_DIR`` from ``pipeline_loaders``.
    Rebinding the re-export leaves the definition site untouched, so anything
    reading it at call time — ``save_run_report`` does — still sees the real
    corpus directory.
    """
    offenders = []
    for name, src in _test_sources():
        patches_facade = re.search(r"^\s*utils\.CATALOGS_DIR\s*=", src, re.M)
        if not patches_facade:
            continue
        # Patching the facade as well is fine — other code reads the re-export.
        # What is not fine is patching *only* the facade.
        patches_source = re.search(r"^\s*(?:pl|pipeline_loaders)\.CATALOGS_DIR\s*=", src, re.M) \
            or 'setattr("pipeline_loaders.CATALOGS_DIR"' in src
        if not patches_source:
            offenders.append(name)
    assert not offenders, (
        "tests rebind utils.CATALOGS_DIR, which does not redirect "
        "save_run_report: " + ", ".join(offenders) +
        " - patch pipeline_loaders.CATALOGS_DIR instead"
    )


def _spawns_repo_script_without_data_env(src):
    """Yield line numbers of subprocess calls that can reach the real corpus.

    A call qualifies when it runs with ``cwd=REPO_ROOT`` and passes no ``env``.
    Without ``env``, the child inherits the ambient environment, where
    ``CLIMATE_FINANCE_DATA`` is normally unset — so ``pipeline_loaders`` falls
    back to the repo's own ``.env`` (``data``), resolved against ``REPO_ROOT``.
    """
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "attr", None) or getattr(func, "id", None)
        if name not in {"run", "check_output", "Popen", "call"}:
            continue
        kwargs = {kw.arg for kw in node.keywords}
        if "cwd" not in kwargs or "env" in kwargs:
            continue
        cwd_kw = next(kw for kw in node.keywords if kw.arg == "cwd")
        if not (isinstance(cwd_kw.value, ast.Name) and cwd_kw.value.id == "REPO_ROOT"):
            continue
        # Only pipeline scripts can write a run report. Running ruff, make or
        # git under cwd=REPO_ROOT is not this defect.
        if not node.args:
            continue
        argsrc = ast.get_source_segment(src, node.args[0]) or ""
        if re.search(r"\.py[\"\']|HARVEST_DIR|ANALYSIS_DIR|SCRIPTS_DIR", argsrc):
            yield node.lineno


@pytest.mark.adherence
def test_no_test_spawns_a_repo_script_without_redirecting_data():
    """A child process needs the env; a monkeypatch cannot reach it.

    Two acceptable shapes: an explicit ``env=`` at each call, or one autouse
    fixture setting ``CLIMATE_FINANCE_DATA`` for the module. The second is
    preferred — a call site added later inherits the redirect instead of having
    to remember it — so a module using it is exempt wholesale.
    """
    offenders = []
    for name, src in _test_sources():
        if 'setenv("CLIMATE_FINANCE_DATA"' in src:
            continue
        for lineno in _spawns_repo_script_without_data_env(src):
            offenders.append(f"{name}:{lineno}")
    assert not offenders, (
        "tests spawn a script with cwd=REPO_ROOT and no env, so it resolves the "
        "real data/catalogs and its run report lands in the DVC output: "
        + ", ".join(offenders) +
        " - pass env={**os.environ, 'CLIMATE_FINANCE_DATA': str(tmp_path)}"
    )


def test_save_run_report_honours_the_patched_definition_site(tmp_path, monkeypatch):
    """The positive counterpart: patching the right module does redirect."""
    monkeypatch.setattr("pipeline_loaders.CATALOGS_DIR", str(tmp_path))
    from pipeline_io import save_run_report

    path = save_run_report({"n": 1}, "isolation-probe", "probe_script")
    assert os.path.realpath(path).startswith(os.path.realpath(str(tmp_path))), (
        f"run report escaped the tmp dir to {path}"
    )
