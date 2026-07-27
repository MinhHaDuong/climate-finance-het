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
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

#: The module that defines the path constants. ``utils`` only re-exports them.
DEFINING_MODULE = "pipeline_loaders"
#: The pure re-export facade. Rebinding a constant here redirects nothing.
FACADE_MODULE = "utils"


def _test_sources():
    for name in sorted(os.listdir(TESTS_DIR)):
        if name.startswith("test_") and name.endswith(".py"):
            path = os.path.join(TESTS_DIR, name)
            with open(path, encoding="utf-8") as fh:
                yield name, fh.read()


def call_time_constants():
    """Return the constants a ``scripts/`` function re-imports at call time.

    A function-local ``from pipeline_loaders import X`` re-reads the definition
    site on every call, so rebinding X anywhere else — the ``utils`` facade, the
    calling module's own namespace — does not redirect it. That is the ticket
    0346 mechanism, and it is a property of the source, not of a name we
    happened to notice: discovering the set by AST keeps the guard correct when
    a new constant joins.

    Today this finds ``CATALOGS_DIR`` (``save_run_report``, ``latest_run_report``)
    and ``POOL_DIR`` (``pool_path``, ``load_pool_ids``, ``load_pool_records``).
    """
    found = set()
    for root, _dirs, files in os.walk(SCRIPTS_DIR):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            with open(os.path.join(root, fname), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for func in ast.walk(tree):
                if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for node in ast.walk(func):
                    if isinstance(node, ast.ImportFrom) and node.module == DEFINING_MODULE:
                        found.update(a.name for a in node.names if a.name.isupper())
    return found


def _module_aliases(tree):
    """Names by which this file refers to the defining module."""
    aliases = {DEFINING_MODULE}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == DEFINING_MODULE and a.asname:
                    aliases.add(a.asname)
    return aliases


def _rebinds(tree, constants):
    """Yield ``(module_name, constant)`` for every rebinding in the file.

    Three shapes, all in use in this suite: bare attribute assignment
    (``utils.CATALOGS_DIR = x``), the ``monkeypatch.setattr`` string target
    (``setattr("pipeline_loaders.CATALOGS_DIR", x)``), and the two-argument
    object form (``setattr(pl, "CATALOGS_DIR", x)``).
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (isinstance(tgt, ast.Attribute) and tgt.attr in constants
                        and isinstance(tgt.value, ast.Name)):
                    yield tgt.value.id, tgt.attr
        elif isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "setattr" \
                or isinstance(node, ast.Call) and getattr(node.func, "id", None) == "setattr":
            args = node.args
            if len(args) >= 2 and isinstance(args[0], ast.Constant) \
                    and isinstance(args[0].value, str) and "." in args[0].value:
                mod, _, const = args[0].value.rpartition(".")
                if const in constants:
                    yield mod, const
            elif len(args) >= 3 and isinstance(args[0], ast.Name) \
                    and isinstance(args[1], ast.Constant) and args[1].value in constants:
                yield args[0].id, args[1].value


def _facade_patch_offenders(sources):
    """Return ``"file: CONST"`` for each constant rebound on the facade alone.

    Scoped to the ``utils`` facade on purpose. Rebinding the constant on the
    *consuming* module is the correct idiom (ticket 0249) and must not be
    flagged: ``test_dedup_vars`` patches ``compute_vars.CATALOGS_DIR`` and does
    redirect its target, because ``dedup_stats`` passes the directory to
    ``latest_run_report`` as an argument rather than letting it re-import
    (ticket 0349 made that parameter injectable for exactly this reason). Only
    ``utils`` is a pure re-export with no reader of its own, so only a rebind
    there is unambiguously a no-op.

    Patching the facade *as well* is fine — code reading the re-export needs it.
    What is not fine is patching only the facade.
    """
    offenders = []
    constants = call_time_constants()
    for name, src in sources:
        tree = ast.parse(src)
        aliases = _module_aliases(tree)
        rebinds = list(_rebinds(tree, constants))
        patched_at_source = {c for m, c in rebinds if m in aliases}
        for const in sorted({c for m, c in rebinds if m == FACADE_MODULE}):
            if const not in patched_at_source:
                offenders.append(f"{name}: {const}")
    return offenders


@pytest.mark.adherence
def test_no_test_patches_a_call_time_constant_off_the_definition_site():
    """Patch the module that defines the constant, not a re-export of it.

    ``scripts/utils.py`` re-exports these constants from ``pipeline_loaders``.
    Rebinding the re-export leaves the definition site untouched, so anything
    reading it at call time — ``save_run_report`` does — still sees the real
    corpus directory, and the test reports green while writing there.
    """
    offenders = _facade_patch_offenders(_test_sources())
    assert not offenders, (
        "tests rebind a constant that its consumer re-imports from "
        f"{DEFINING_MODULE} at call time, so the patch does not redirect it: "
        + ", ".join(offenders)
        + f" - patch {DEFINING_MODULE}.<CONST> too"
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


SAMPLE_POOL_OFFENDER = """
import utils

def test_something(tmp_path):
    utils.POOL_DIR = str(tmp_path)
    from utils import pool_path
    pool_path("openalex", "probe")
"""

SAMPLE_POOL_CLEAN = """
import pipeline_loaders
import utils

def test_something(tmp_path, monkeypatch):
    monkeypatch.setattr("pipeline_loaders.POOL_DIR", str(tmp_path))
    from utils import pool_path
    pool_path("openalex", "probe")
"""


SAMPLE_CONSUMER_PATCH = """
import compute_vars

def test_something(tmp_path, monkeypatch):
    monkeypatch.setattr(compute_vars, "CATALOGS_DIR", str(tmp_path))
    compute_vars.dedup_stats({})
"""


@pytest.mark.adherence
def test_discovery_is_not_vacuous():
    """A guard driven by discovery passes trivially if discovery finds nothing.

    ``CATALOGS_DIR`` is pinned because the ticket-0346 invariant keeps the
    function-local import that puts it here — it breaks a circular import. If
    that ever changes, this fails and the guard gets re-derived deliberately
    rather than quietly protecting nothing.
    """
    constants = call_time_constants()
    assert "CATALOGS_DIR" in constants, (
        "pipeline_io no longer re-imports CATALOGS_DIR at call time; "
        "re-derive this guard instead of letting it pass vacuously"
    )


@pytest.mark.adherence
def test_facade_guard_detects_a_constant_it_was_never_told_about():
    """The guard must cover the mechanism, not the one constant that bit us.

    ``POOL_DIR`` has exactly the shape ``CATALOGS_DIR`` had: ``pipeline_io``
    re-imports it from ``pipeline_loaders`` inside ``pool_path`` and friends, so
    rebinding it on the ``utils`` facade is a no-op — and ``pool_path`` calls
    ``os.makedirs``, so the leak would create directories inside the DVC-tracked
    ``data/pool/``. No test exercises the pool helpers today, which is precisely
    why a name-based guard would not notice when one does.
    """
    assert _facade_patch_offenders([("sample_offender.py", SAMPLE_POOL_OFFENDER)])
    assert not _facade_patch_offenders([("sample_clean.py", SAMPLE_POOL_CLEAN)])


@pytest.mark.adherence
def test_facade_guard_leaves_the_consuming_module_idiom_alone():
    """Patching the consumer is the recommended idiom, not the defect.

    The first draft of this guard flagged ``test_dedup_vars`` for patching
    ``compute_vars.CATALOGS_DIR``. That is a false positive: ``dedup_stats``
    hands the directory to ``latest_run_report`` as an argument, so the patch
    does reach it. Flagging it would push authors toward the wrong fix.
    """
    assert not _facade_patch_offenders([("sample_consumer.py", SAMPLE_CONSUMER_PATCH)])


def test_save_run_report_honours_the_patched_definition_site(tmp_path, monkeypatch):
    """The positive counterpart: patching the right module does redirect."""
    monkeypatch.setattr("pipeline_loaders.CATALOGS_DIR", str(tmp_path))
    from pipeline_io import save_run_report

    path = save_run_report({"n": 1}, "isolation-probe", "probe_script")
    assert os.path.realpath(path).startswith(os.path.realpath(str(tmp_path))), (
        f"run report escaped the tmp dir to {path}"
    )
