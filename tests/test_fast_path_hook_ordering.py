"""Pin the fast-path auto-mark hook ordering (ticket 0228).

The collection-time auto-mark in ``tests/conftest.py`` relies on pytest firing
user ``pytest_collection_modifyitems`` hooks *before* its internal ``-m``
mark-filter deselection. If that order ever inverted, an auto-added ``slow``
marker would arrive too late to deselect the test and heavy-import modules would
silently rejoin the fast inner loop — with no failure in the rest of the suite
(the auto-mark failing open only *adds* work, never breaks a green run).

This test locks the ordering by spinning a real collection in a throwaway
directory whose ``conftest.py`` mirrors the production auto-mark hook (same
``file_has_heavy_import`` detection, same ``add_marker(slow)`` in
``pytest_collection_modifyitems``). ``--collect-only`` is used so the synthetic
module's lazy heavy import never actually fires — collection compiles the source
(which the static scanner reads) without executing test bodies.
"""

import os
import subprocess
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# A conftest that reproduces the production auto-mark: any test module whose
# source statically imports a heavy dependency is marked ``slow`` at collection.
# It reuses the real ``file_has_heavy_import`` so detection stays single-sourced;
# the only thing under test here is pytest's hook ordering.
_SYNTHETIC_CONFTEST = f'''\
import sys
sys.path.insert(0, {TESTS_DIR!r})
import pytest
from _tier_autoscan import file_has_heavy_import


def pytest_collection_modifyitems(config, items):
    for item in items:
        path = str(getattr(item, "path", None) or item.fspath)
        if file_has_heavy_import(path):
            item.add_marker(pytest.mark.slow)
'''

# Heavy-import module: torch is imported lazily inside a function body, so the
# static scanner flags it but the import never runs under ``--collect-only``.
_HEAVY_TEST = '''\
def _lazy():
    import torch  # noqa: F401 — never executed under --collect-only

    return _lazy


def test_heavy_module():
    assert True
'''

# Control module: no heavy import, must stay on the fast path.
_LIGHT_TEST = '''\
def test_light_module():
    assert True
'''

_FAST_PATH_SELECTOR = "not slow and not integration and not adherence"


def _collect(workdir: str, selector: str) -> set[str]:
    """Return the set of test function names pytest selects under ``selector``."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "-m",
            selector,
            ".",
        ],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"collection failed:\n{proc.stdout}\n{proc.stderr}"
    names = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if "::" in line:
            names.add(line.rsplit("::", 1)[-1])
    return names


@pytest.mark.integration
def test_auto_mark_deselects_on_fast_path(tmp_path):
    """The auto-added ``slow`` marker removes a heavy-import test from fast path.

    Pins pytest's ordering: user ``pytest_collection_modifyitems`` fires before
    the internal ``-m`` deselection, so the marker is honoured. If the order ever
    inverts, ``test_heavy_module`` would leak back onto the fast path and this
    assertion fails.
    """
    (tmp_path / "conftest.py").write_text(_SYNTHETIC_CONFTEST)
    (tmp_path / "test_heavy.py").write_text(_HEAVY_TEST)
    (tmp_path / "test_light.py").write_text(_LIGHT_TEST)

    selected = _collect(str(tmp_path), _FAST_PATH_SELECTOR)

    assert "test_light_module" in selected  # control stays on the fast path
    assert "test_heavy_module" not in selected  # auto-marked slow → deselected


@pytest.mark.integration
def test_auto_mark_selects_under_slow(tmp_path):
    """The same heavy-import test IS selected under ``-m slow``.

    Confirms the deselection above is the auto-added marker at work — not the
    module failing to collect for some unrelated reason.
    """
    (tmp_path / "conftest.py").write_text(_SYNTHETIC_CONFTEST)
    (tmp_path / "test_heavy.py").write_text(_HEAVY_TEST)
    (tmp_path / "test_light.py").write_text(_LIGHT_TEST)

    selected = _collect(str(tmp_path), "slow")

    assert "test_heavy_module" in selected  # auto-marked slow → selected
    assert "test_light_module" not in selected  # no heavy import → not slow
