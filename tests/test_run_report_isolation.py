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
    """Every test module, including conftest and nested test directories.

    ``conftest.py`` is the one file most likely to rebind a path constant for a
    whole package, and a top-level ``listdir`` filtered on ``test_*`` missed
    both it and any subdirectory.
    """
    for root, _dirs, files in os.walk(TESTS_DIR):
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            if not (name.startswith("test_") or name == "conftest.py"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as fh:
                yield os.path.relpath(path, TESTS_DIR), fh.read()


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
            path = os.path.join(root, fname)
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            try:
                tree = ast.parse(src)
            except SyntaxError:
                # A file this interpreter cannot parse is out of scope, and a
                # discovery helper is the wrong place to fail the suite over it.
                continue
            for func in ast.walk(tree):
                if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for node in ast.walk(func):
                    if isinstance(node, ast.ImportFrom) and node.module == DEFINING_MODULE:
                        found.update(a.name for a in node.names if a.name.isupper())
    return found


def _aliases_of(tree, module):
    """Names by which this file refers to ``module``.

    Applied to the facade as well as to the defining module: resolving one and
    matching the other literally would leave ``import utils as u`` unflagged,
    which is the alias blind spot the ticket-0251 guard already has.
    """
    aliases = {module}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == module and a.asname:
                    aliases.add(a.asname)
    return aliases


def _rebinds_in(node, constants):
    """Yield ``(module_name, constant)`` for a rebinding performed by ``node``.

    Three shapes, all in use in this suite: bare attribute assignment
    (``utils.CATALOGS_DIR = x``), the ``monkeypatch.setattr`` string target
    (``setattr("pipeline_loaders.CATALOGS_DIR", x)``), and the two-argument
    object form (``setattr(pl, "CATALOGS_DIR", x)``).
    """
    if isinstance(node, ast.Assign):
        for tgt in node.targets:
            if (isinstance(tgt, ast.Attribute) and tgt.attr in constants
                    and isinstance(tgt.value, ast.Name)):
                yield tgt.value.id, tgt.attr
        return
    if not isinstance(node, ast.Call):
        return
    name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
    if name not in {"setattr", "patch", "object"}:
        return
    # setattr accepts its arguments by keyword too, and monkeypatch names them
    # target/name/value. Reading node.args alone made the keyword form
    # invisible, which is a guard that can be stepped around by accident.
    kw = {k.arg: k.value for k in node.keywords}
    args = list(node.args)
    first = args[0] if args else kw.get("target")
    second = args[1] if len(args) > 1 else kw.get("name")
    if isinstance(first, ast.Constant) and isinstance(first.value, str) \
            and "." in first.value:
        mod, _, const = first.value.rpartition(".")
        if const in constants:
            yield mod, const
    elif isinstance(first, ast.Name) and isinstance(second, ast.Constant) \
            and second.value in constants:
        yield first.id, second.value


def _rebinds_by_scope(tree, constants):
    """Group rebindings by the function that performs them.

    Per function, not per file. A neighbour patching the definition site says
    nothing about this test: pairing them file-wide would exempt a genuine
    no-op merely for sitting next to a correct one.
    """
    scopes = {}

    def visit(node, scope):
        # Qualified by the enclosing class, not the bare name: two test classes
        # in one module routinely define identically named methods, and keying
        # on the name alone would merge their exemptions — the very laundering
        # this per-scope split exists to prevent, one nesting level down.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope = f"{scope}.{node.name}" if scope != "<module>" else node.name
        for pair in _rebinds_in(node, constants):
            scopes.setdefault(scope, []).append(pair)
        for child in ast.iter_child_nodes(node):
            visit(child, scope)

    visit(tree, "<module>")
    return scopes


def _facade_patch_offenders(sources):
    """Return ``"file: CONST"`` for each constant rebound on the facade alone.

    Scoped to the ``utils`` facade on purpose. Rebinding the constant on the
    *consuming* module is the correct idiom (ticket 0249) and must not be
    flagged: ``test_dedup_vars`` patches ``compute_vars.CATALOGS_DIR`` and does
    redirect its target, because ``dedup_stats`` passes the directory to
    ``latest_run_report`` as an argument rather than letting it re-import
    (ticket 0349 made that parameter injectable for exactly this reason).

    Patching the facade *as well* is fine — code reading the re-export needs it.
    What is not fine is patching only the facade.

    Coverage boundary, stated because the obvious reading is wrong: the facade
    is not readerless. ``compute_vars`` (:381, :535) and ``plot_alluvial_html``
    (:85) do function-local ``from utils import <CONST>``, so the mirror-image
    defect exists — for a constant read at call time off ``utils``, patching
    ``pipeline_loaders`` is the no-op instead. This guard covers one direction
    only: constants reached through ``pipeline_loaders``, which is where ticket
    0346's leak lived. The other direction reads rather than writes DVC data,
    so it cannot leak the same way, and folding it in would give a guard whose
    correct patch target flips per constant — a design call, not a widened
    regex. The assertion below says "patch ``pipeline_loaders.<CONST>`` *too*",
    additive on purpose, so following it stays safe either way.
    """
    offenders = []
    constants = call_time_constants()
    for name, src in sources:
        tree = ast.parse(src)
        defining = _aliases_of(tree, DEFINING_MODULE)
        facade = _aliases_of(tree, FACADE_MODULE)
        for scope, rebinds in sorted(_rebinds_by_scope(tree, constants).items()):
            patched_at_source = {c for m, c in rebinds if m in defining}
            for const in sorted({c for m, c in rebinds if m in facade}):
                if const not in patched_at_source:
                    offenders.append(f"{name}:{scope}: {const}")
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

SAMPLE_CROSS_FUNCTION = """
import pipeline_loaders
import utils

def test_correct(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_loaders, "CATALOGS_DIR", str(tmp_path))

def test_leaks(tmp_path):
    utils.CATALOGS_DIR = str(tmp_path)
"""

SAMPLE_FACADE_ALIAS = """
import utils as u

def test_something(tmp_path):
    u.CATALOGS_DIR = str(tmp_path)
"""

SAMPLE_KEYWORD_SETATTR = """
import utils

def test_something(tmp_path, monkeypatch):
    monkeypatch.setattr(target=utils, name="CATALOGS_DIR", value=str(tmp_path))
"""

SAMPLE_MOCK_PATCH = """
from unittest import mock

def test_something(tmp_path):
    with mock.patch("utils.CATALOGS_DIR", str(tmp_path)):
        pass
"""

SAMPLE_SAME_NAME_TWO_CLASSES = """
import pipeline_loaders
import utils

class TestCorrect:
    def test_it(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pipeline_loaders, "CATALOGS_DIR", str(tmp_path))

class TestLeaks:
    def test_it(self, tmp_path):
        utils.CATALOGS_DIR = str(tmp_path)
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


@pytest.mark.adherence
def test_facade_guard_scopes_the_exemption_to_one_function():
    """A correct neighbour must not launder the test next door.

    Patching the facade *as well as* the definition site is fine, so the guard
    needs an exemption — but keyed to the function performing both, not to the
    file. File-level pairing would have let a real no-op through whenever any
    sibling in the same module happened to patch ``pipeline_loaders``, which is
    the common case in a suite that mixes fixed and unfixed tests.
    """
    offenders = _facade_patch_offenders([("cross.py", SAMPLE_CROSS_FUNCTION)])
    assert offenders == ["cross.py:test_leaks: CATALOGS_DIR"], offenders


@pytest.mark.adherence
def test_facade_guard_distinguishes_same_named_methods_in_two_classes():
    """Qualify the scope by class, or the per-function split leaks one level down.

    Two classes each defining ``test_it`` is ordinary pytest style. Keyed on the
    bare function name they would share one exemption bucket, and the correct
    one would launder the leaking one — the file-level laundering this guard
    already rejects, merely nested.
    """
    offenders = _facade_patch_offenders([("two.py", SAMPLE_SAME_NAME_TWO_CLASSES)])
    assert offenders == ["two.py:TestLeaks.test_it: CATALOGS_DIR"], offenders


@pytest.mark.adherence
def test_facade_guard_sees_past_the_call_shape():
    """The rebinding shapes differ; the defect does not.

    ``setattr`` takes its arguments by keyword too, and ``unittest.mock`` offers
    a third spelling. A guard that reads positional ``setattr`` args alone is
    steppable by accident — nobody writes ``target=`` to evade a check, they
    write it because the call is long.
    """
    assert _facade_patch_offenders([("kw.py", SAMPLE_KEYWORD_SETATTR)])
    assert _facade_patch_offenders([("mockp.py", SAMPLE_MOCK_PATCH)])


@pytest.mark.adherence
def test_facade_guard_resolves_an_aliased_facade_import():
    """``import utils as u`` is the same defect wearing a different name.

    The 0251 guard matches the literal string ``utils`` and documents this as
    an accepted limitation. Repeating it here would be a poor trade for a guard
    that already walks the AST: ``_aliases_of`` resolves the facade exactly as
    it resolves the defining module.
    """
    assert _facade_patch_offenders([("alias.py", SAMPLE_FACADE_ALIAS)])


def test_save_run_report_honours_the_patched_definition_site(tmp_path, monkeypatch):
    """The positive counterpart: patching the right module does redirect."""
    monkeypatch.setattr("pipeline_loaders.CATALOGS_DIR", str(tmp_path))
    from pipeline_io import save_run_report

    path = save_run_report({"n": 1}, "isolation-probe", "probe_script")
    assert os.path.realpath(path).startswith(os.path.realpath(str(tmp_path))), (
        f"run report escaped the tmp dir to {path}"
    )
