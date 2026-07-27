"""Hartigan's dip test must actually run — no silent dependency-missing skip.

Ticket 0330. `analyze_bimodality.py` wrapped `import diptest` in a try/except
that logged "not available" and continued, while `diptest` was declared in
neither `pyproject.toml` nor `uv.lock`. The import therefore always failed and
`dip_pvalue` was empty in every row of `tab_bimodality.csv`, next to a module
docstring advertising "Dip test p-values".

Two guards, deliberately split:

- The source guard runs everywhere, including a clean checkout with no corpus.
  It is the one that stays meaningful in CI.
- The artifact guard needs the real derived table and so only runs on a machine
  that has built it (padme).

Same class as ticket 0314 (Flag 6 without torch), which PR #1127 hard-guarded.
"""

import ast
import os
import re

import pandas as pd
import pytest
from utils import BASE_DIR, DERIVED_TABLES_DIR

SCRIPT = os.path.join(BASE_DIR, "scripts", "analysis", "analyze_bimodality.py")
PYPROJECT = os.path.join(BASE_DIR, "pyproject.toml")


@pytest.mark.adherence
def test_diptest_is_a_declared_dependency():
    """An import the pipeline depends on must be declared, not hoped for."""
    with open(PYPROJECT, encoding="utf-8") as fh:
        pyproject = fh.read()
    assert re.search(r'^\s*"diptest', pyproject, re.MULTILINE), (
        "diptest is imported by analyze_bimodality.py but declared nowhere in "
        "pyproject.toml - the import fails on every machine and the dip test "
        "never runs"
    )


def _swallowing_import_handlers(source):
    """Yield line numbers of `except ImportError` blocks that do not re-raise.

    Catching ImportError is legitimate — the ticket-0314 idiom does it to
    replace a bare ModuleNotFoundError with an actionable message. What is not
    legitimate is a handler that returns control to the caller, because the run
    then continues with a degraded result. So the guard is on the *swallow*,
    not on the catch.
    """
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ExceptHandler):
            continue
        caught = ast.dump(node.type) if node.type is not None else "bare"
        if node.type is not None and "ImportError" not in caught:
            continue
        if not any(isinstance(child, ast.Raise) for child in ast.walk(node)):
            yield node.lineno


@pytest.mark.adherence
def test_diptest_import_failure_is_a_hard_error():
    """A missing dependency must stop the run, not downgrade the output.

    The failure mode this pins is not a crash but a plausible wrong artifact:
    a table shipping an empty column that its own docstring advertises.
    """
    with open(SCRIPT, encoding="utf-8") as fh:
        source = fh.read()

    assert "import diptest" in source, (
        "test is stale: analyze_bimodality.py no longer imports diptest"
    )
    swallowed = list(_swallowing_import_handlers(source))
    assert not swallowed, (
        f"analyze_bimodality.py swallows an ImportError at line(s) {swallowed} "
        "- a missing diptest must raise, not log and continue with an empty "
        "dip_pvalue column"
    )
    assert not re.search(r"log\.\w+\([^)]*not available", source), (
        "analyze_bimodality.py announces a missing dependency at log level and "
        "carries on; the run must stop instead"
    )


@pytest.mark.slow
@pytest.mark.skipif(
    not os.path.exists(os.path.join(DERIVED_TABLES_DIR, "tab_bimodality.csv")),
    reason="tab_bimodality.csv not built",
)
def test_bimodality_dip_column_is_not_silently_empty():
    """Either the dip test ran, or the column is gone. Never present-and-empty.

    Written to hold under both resolutions the ticket weighed, so it survives a
    later decision to drop the statistic.
    """
    df = pd.read_csv(os.path.join(DERIVED_TABLES_DIR, "tab_bimodality.csv"))
    if "dip_pvalue" not in df.columns:
        return
    assert df["dip_pvalue"].notna().any(), (
        "dip_pvalue is present but empty in every row - diptest is not "
        "installed and the skip is silent"
    )
