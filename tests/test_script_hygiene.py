"""Tests for coding-guidelines.md § Script hygiene and § Python style.

These tests enforce mechanically verifiable conventions. Each test is
designed to be red against the current codebase, documenting the gap
between guidelines and reality. Alignment tickets will fix the code;
these tests stay to prevent regression.

IMPORTANT: none of these changes may alter archive outputs. The
test_archive_bit_invariance class verifies that archive checksums
(expected_outputs.md5, checksums.md5) remain identical after refactoring.

Uses existing code checkers where available:
- ruff C901: McCabe cyclomatic complexity (threshold 10)
- ruff PLR0915: too many statements per function (threshold 50)
- ruff PLR0912: too many branches per function (threshold 12)
- ruff UP006/UP007/UP035: legacy typing imports
- ast: bare print() detection, sys.path hacks
"""

import ast
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from _script_discovery import all_script_files

# The entire file is rule-enforcement / lint / hygiene: ruff and mypy invocations,
# complexity and length smells, arch-rule and contract checks. It belongs to the
# adherence tier (ticket 0215) so the fast inner loop (`-m "not adherence"`,
# ticket 0214) deselects it — same convention as test_editorial_governance.py and
# test_manuscript_prose.py.
pytestmark = pytest.mark.adherence

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO, "scripts")
MAKEFILE = os.path.join(REPO, "Makefile")
# Archived scripts are preserved for reference but not subject to hygiene checks.
ARCHIVE_DIR = os.path.join(SCRIPTS_DIR, "archive")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_scripts():
    """Return sorted list of .py files in scripts/ and its subdirectories.

    Returns paths relative to SCRIPTS_DIR (e.g. "utils.py",
    "archive_traditions/detect_traditions_v1.py").

    Scripts under scripts/archive/ are excluded — they are superseded
    experimental scripts preserved for reference only, not active code.
    """
    result = []
    for dirpath, dirnames, filenames in os.walk(SCRIPTS_DIR):
        # Skip the archive/ subdirectory entirely — archived scripts are
        # preserved for reference and not subject to hygiene enforcement.
        rel_dir = os.path.relpath(dirpath, SCRIPTS_DIR)
        if rel_dir == "archive" or rel_dir.startswith("archive" + os.sep):
            dirnames.clear()
            continue
        for f in filenames:
            if f.endswith(".py") and not f.startswith("__"):
                rel = os.path.relpath(os.path.join(dirpath, f), SCRIPTS_DIR)
                result.append(rel)
    return sorted(result)


def _read_script(name):
    """Read a script by its path relative to SCRIPTS_DIR."""
    path = os.path.join(SCRIPTS_DIR, name)
    with open(path) as f:
        return f.read()


def _parse_script(name):
    return ast.parse(_read_script(name), filename=name)


def _scripts_with_main_guard():
    """Scripts that have if __name__ == '__main__'."""
    result = []
    for name in _all_scripts():
        source = _read_script(name)
        if re.search(r'if\s+__name__\s*==\s*["\']__main__["\']', source):
            result.append(name)
    return result


# Scripts that are pure libraries (no __main__ guard, imported by others).
# These are exempt from argparse checks (no __main__ guard).
LIBRARY_SCRIPTS = {
    "utils.py",
    "plot_style.py",
    "filter_flags.py",
    "filter_flags_llm.py",
    "clustering_methods.py",
    "qa_near_duplicates.py",
    "syllabi_config.py",
    "syllabi_crossref.py",
    "syllabi_harvest.py",
    "syllabi_io.py",
    "syllabi_process.py",
    "pipeline_text.py",
    "pipeline_io.py",
    "pipeline_loaders.py",
    "pipeline_progress.py",
}

# Subdirectory scripts that legitimately need sys.path.insert to reach
# the parent scripts/ directory for utils imports.
_SYSPATH_EXEMPT = {
    os.path.join("archive_traditions", f)
    for f in (
        "detect_traditions_v2.py",
        "detect_traditions_v3.py",
        "detect_traditions_pre2015.py",
        "detect_traditions_pre2020.py",
    )
}

# Resolve the tool binary via shutil.which, not a nested `uv run` (ticket 0236):
# pytest already runs inside the project venv under `make lint`, so a declared,
# lockfile-pinned tool is on PATH. A nested `uv run` re-enters uv from inside uv,
# forcing a per-call sync check that breaks under `UV_NO_SYNC` in a clean
# CI/cloud container. Mirrors the pattern in test_ruff.py.
_RUFF = shutil.which("ruff")
_RUFF_AVAILABLE = _RUFF is not None


# ---------------------------------------------------------------------------
# No sys.path hacks
# ---------------------------------------------------------------------------


class TestNoSysPathHacks:
    """scripts/ must not contain sys.path.insert() calls.

    The project should use pyproject.toml packaging instead.
    Subdirectory scripts that genuinely need sys.path to reach the parent
    scripts/ directory are listed in _SYSPATH_EXEMPT.
    """

    def test_no_sys_path_insert(self):
        """No script may use sys.path.insert() unless in _SYSPATH_EXEMPT."""
        violators = []
        for name in _all_scripts():
            if name in _SYSPATH_EXEMPT:
                continue
            source = _read_script(name)
            if "sys.path.insert" in source or "sys.path.append" in source:
                violators.append(name)
        assert not violators, (
            f"{len(violators)} scripts use sys.path hacks "
            f"(should use pyproject.toml packaging): {violators[:10]}..."
        )


# ---------------------------------------------------------------------------
# Centralized research parameters
# ---------------------------------------------------------------------------


class TestCentralizedConstants:
    """Research parameters must come from config/analysis.yaml, not hardcoded.

    CITE_THRESHOLD = 50 is currently defined in 8 scripts independently.
    It should be read via load_analysis_config()['clustering']['cite_threshold'].
    """

    # Constants that must not be defined as module-level literals in scripts.
    # They belong in config/analysis.yaml.
    FORBIDDEN_CONSTANTS = {
        "CITE_THRESHOLD": "clustering.cite_threshold",
    }

    def test_cite_threshold_not_hardcoded(self):
        """CITE_THRESHOLD must not be defined as a literal in any script."""
        violators = []
        for name in _all_scripts():
            source = _read_script(name)
            # Match lines like: CITE_THRESHOLD = 50
            if re.search(r"^CITE_THRESHOLD\s*=\s*\d+", source, re.MULTILINE):
                violators.append(name)
        assert not violators, (
            f"CITE_THRESHOLD hardcoded in {len(violators)} scripts "
            f"(should read from config/analysis.yaml): {violators}"
        )

    def test_config_has_cite_threshold(self):
        """config/analysis.yaml must define clustering.cite_threshold."""
        import yaml

        config_path = os.path.join(REPO, "config", "analysis.yaml")
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        assert "clustering" in cfg, "analysis.yaml missing 'clustering' section"
        assert "cite_threshold" in cfg["clustering"], (
            "analysis.yaml clustering section must define cite_threshold"
        )


# ---------------------------------------------------------------------------
# Every entry point gets argparse
# ---------------------------------------------------------------------------


class TestArgparsePresence:
    """Every script with __main__ guard must use argparse.

    All entry-point scripts now have argparse. This test prevents
    regressions — each must have a parser with at least --help.
    """

    def test_main_scripts_have_argparse(self):
        """Every __main__ script must import or use argparse."""
        main_scripts = _scripts_with_main_guard()
        violators = []
        for name in main_scripts:
            if name in LIBRARY_SCRIPTS:
                continue
            source = _read_script(name)
            if (
                "argparse" not in source
                and "ArgumentParser" not in source
                and "parse_io_args" not in source
            ):
                violators.append(name)
        assert not violators, (
            f"{len(violators)} entry-point scripts lack argparse "
            f"(coding guidelines require it): {violators}"
        )


# ---------------------------------------------------------------------------
# Ruff pyupgrade rules (modern Python 3.10+)
# ---------------------------------------------------------------------------


class TestRuffModernPython:
    """Ruff UP rules catch legacy typing imports and old-style unions.

    UP006: Use builtin types (list[] not List[])
    UP007: Use X | Y not Union[X, Y]
    UP035: Deprecated typing imports
    """

    @pytest.mark.skipif(not _RUFF_AVAILABLE, reason="ruff not available")
    def test_no_legacy_typing(self):
        """No legacy typing imports (List, Dict, Tuple, Optional, Union)."""
        result = subprocess.run(
            [
                _RUFF,
                "check",
                "--select",
                "UP006,UP007,UP035",
                "--exclude",
                ARCHIVE_DIR,
                "--no-fix",
                SCRIPTS_DIR,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Ruff found legacy typing patterns:\n{result.stdout}"
        )

    @pytest.mark.skipif(not _RUFF_AVAILABLE, reason="ruff not available")
    def test_no_future_annotations(self):
        """No from __future__ import annotations (we target 3.10+)."""
        violators = []
        for name in _all_scripts():
            source = _read_script(name)
            if "from __future__ import annotations" in source:
                violators.append(name)
        assert not violators, (
            f"Scripts with __future__ annotations (not needed on 3.10+): {violators}"
        )


# ---------------------------------------------------------------------------
# Complexity and length (ruff C901, PLR0915, PLR0912)
# ---------------------------------------------------------------------------


class TestFunctionComplexity:
    """Two-tier complexity thresholds: smell (warn) and wall (hard fail).

    Smell thresholds flag functions worth reviewing but don't block PRs.
    Wall thresholds catch genuinely unmaintainable god functions.

    Calibrated against the 63-script codebase:
    - C901:    smell 15, wall 25  (ruff default 10)
    - PLR0915: smell 80, wall 120 (ruff default 50)
    - PLR0912: smell 15, wall 25  (ruff default 12)
    """

    # --- Walls (hard fail) ---

    @pytest.mark.skipif(not _RUFF_AVAILABLE, reason="ruff not available")
    def test_mccabe_complexity(self):
        """No function exceeds McCabe complexity 25 (C901 wall)."""
        result = subprocess.run(
            [
                _RUFF,
                "check",
                "--select",
                "C901",
                "--config",
                "lint.mccabe.max-complexity = 25",
                "--exclude",
                ARCHIVE_DIR,
                "--no-fix",
                SCRIPTS_DIR,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Ruff C901: functions too complex (McCabe > 25):\n{result.stdout}"
        )

    @pytest.mark.skipif(not _RUFF_AVAILABLE, reason="ruff not available")
    def test_function_length(self):
        """No function exceeds 120 statements (PLR0915 wall)."""
        result = subprocess.run(
            [
                _RUFF,
                "check",
                "--select",
                "PLR0915",
                "--config",
                "lint.pylint.max-statements = 120",
                "--exclude",
                ARCHIVE_DIR,
                "--no-fix",
                SCRIPTS_DIR,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Ruff PLR0915: functions with too many statements (> 120):\n"
            f"{result.stdout}"
        )

    @pytest.mark.skipif(not _RUFF_AVAILABLE, reason="ruff not available")
    def test_branch_count(self):
        """No function exceeds 25 branches (PLR0912 wall)."""
        result = subprocess.run(
            [
                _RUFF,
                "check",
                "--select",
                "PLR0912",
                "--config",
                "lint.pylint.max-branches = 25",
                "--exclude",
                ARCHIVE_DIR,
                "--no-fix",
                SCRIPTS_DIR,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Ruff PLR0912: functions with too many branches (> 25):\n{result.stdout}"
        )

    # --- Smells (warn, don't fail) ---

    @pytest.mark.skipif(not _RUFF_AVAILABLE, reason="ruff not available")
    def test_mccabe_complexity_smell(self):
        """Warn when functions exceed McCabe complexity 15."""
        result = subprocess.run(
            [
                _RUFF,
                "check",
                "--select",
                "C901",
                "--config",
                "lint.mccabe.max-complexity = 15",
                "--exclude",
                ARCHIVE_DIR,
                "--no-fix",
                SCRIPTS_DIR,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            import warnings

            warnings.warn(f"C901 smells (complexity > 15):\n{result.stdout}")

    @pytest.mark.skipif(not _RUFF_AVAILABLE, reason="ruff not available")
    def test_function_length_smell(self):
        """Warn when functions exceed 80 statements."""
        result = subprocess.run(
            [
                _RUFF,
                "check",
                "--select",
                "PLR0915",
                "--config",
                "lint.pylint.max-statements = 80",
                "--exclude",
                ARCHIVE_DIR,
                "--no-fix",
                SCRIPTS_DIR,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            import warnings

            warnings.warn(f"PLR0915 smells (statements > 80):\n{result.stdout}")

    @pytest.mark.skipif(not _RUFF_AVAILABLE, reason="ruff not available")
    def test_branch_count_smell(self):
        """Warn when functions exceed 15 branches."""
        result = subprocess.run(
            [
                _RUFF,
                "check",
                "--select",
                "PLR0912",
                "--config",
                "lint.pylint.max-branches = 15",
                "--exclude",
                ARCHIVE_DIR,
                "--no-fix",
                SCRIPTS_DIR,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            import warnings

            warnings.warn(f"PLR0912 smells (branches > 15):\n{result.stdout}")


class TestModuleLength:
    """Modules must not grow unbounded.

    Two thresholds:
    - 500 lines: smell (warns, does not fail)
    - 800 lines: wall (hard fail — split the module)
    """

    SMELL_LINES = 500
    MAX_MODULE_LINES = 800

    def test_no_god_modules(self):
        """No script exceeds 800 lines."""
        violators = []
        for name in _all_scripts():
            path = os.path.join(SCRIPTS_DIR, name)
            with open(path) as f:
                lines = sum(1 for _ in f)
            if lines > self.MAX_MODULE_LINES:
                violators.append((name, lines))
        assert not violators, (
            f"{len(violators)} scripts exceed {self.MAX_MODULE_LINES} lines "
            f"(split into focused modules): "
            + ", ".join(f"{n} ({l}L)" for n, l in violators)
        )

    def test_module_length_smell(self):
        """Warn (not fail) when scripts exceed 500 lines."""
        smelly = []
        for name in _all_scripts():
            path = os.path.join(SCRIPTS_DIR, name)
            with open(path) as f:
                lines = sum(1 for _ in f)
            if lines > self.SMELL_LINES:
                smelly.append((name, lines))
        if smelly:
            import warnings

            warnings.warn(
                f"{len(smelly)} scripts exceed {self.SMELL_LINES} lines "
                f"(consider splitting): " + ", ".join(f"{n} ({l}L)" for n, l in smelly)
            )

    def test_utils_facade_under_500_lines(self):
        """utils.py must be a thin facade: ≤ 500 lines (ticket #431 exit criterion)."""
        path = os.path.join(SCRIPTS_DIR, "utils.py")
        with open(path) as f:
            lines = sum(1 for _ in f)
        assert lines <= self.SMELL_LINES, (
            f"utils.py is {lines} lines — must be a thin facade (≤ {self.SMELL_LINES}L). "
            "Split remaining code into pipeline_text.py / pipeline_io.py / "
            "pipeline_loaders.py / pipeline_progress.py"
        )

    def test_filter_flags_under_500_lines(self):
        """filter_flags.py must stay under 500 lines after LLM extraction (#559)."""
        path = os.path.join(SCRIPTS_DIR, "filter_flags.py")
        with open(path) as f:
            lines = sum(1 for _ in f)
        assert lines <= self.SMELL_LINES, (
            f"filter_flags.py is {lines} lines — must be ≤ {self.SMELL_LINES}L. "
            "LLM backend code belongs in filter_flags_llm.py (#559)"
        )

    def test_filter_flags_llm_exists(self):
        """filter_flags_llm.py must exist after LLM extraction (#559)."""
        path = os.path.join(SCRIPTS_DIR, "filter_flags_llm.py")
        assert os.path.exists(path), (
            "filter_flags_llm.py does not exist — extract Flag 6 LLM code from "
            "filter_flags.py (#559)"
        )

    def test_pipeline_modules_exist(self):
        """pipeline_text/io/loaders/progress.py must exist after split."""
        for name in (
            "pipeline_text.py",
            "pipeline_io.py",
            "pipeline_loaders.py",
            "pipeline_progress.py",
        ):
            path = os.path.join(SCRIPTS_DIR, name)
            assert os.path.exists(path), (
                f"{name} does not exist — create it as part of ticket #431 split"
            )


# ---------------------------------------------------------------------------
# Archive bit-invariance
# ---------------------------------------------------------------------------


class TestArchiveBitInvariance:
    """Refactoring must not change archive outputs.

    The archive recipes (archive-analysis, archive-manuscript) produce
    checksum files. After any refactoring PR, archive outputs must match
    the v1.0-submission baseline byte-for-byte.

    These tests verify the structural prerequisites:
    - Archive recipes generate checksum files
    - ANALYSIS_OUTPUTS is complete
    - Archive scripts list matches Makefile recipe
    """

    def _read_makefile(self):
        with open(MAKEFILE) as f:
            return f.read()

    def test_analysis_archive_has_verify_target(self):
        """The analysis archive Makefile must include a 'verify' target
        that checks md5sums, so reviewers can confirm bit-invariance."""
        archive_mk = os.path.join(
            REPO, "build", "templates", "Makefile.analysis-manuscript"
        )
        with open(archive_mk) as f:
            content = f.read()
        assert re.search(r"^verify\s*:", content, re.MULTILINE), (
            "Makefile.analysis-manuscript must have a 'verify' target "
            "that runs md5sum -c expected_outputs.md5"
        )

    @staticmethod
    def _read_analysis_build_script():
        script = os.path.join(REPO, "build", "build_analysis_archive.sh")
        with open(script) as f:
            return f.read()

    def test_analysis_archive_checksums_cover_all_outputs(self):
        """expected_outputs.md5 must be generated in the build script."""
        script = self._read_analysis_build_script()
        assert "expected_outputs.md5" in script, (
            "build_analysis_archive.sh must generate expected_outputs.md5"
        )

    def test_archive_scripts_match_recipe(self):
        """Every script copied into the archive must appear in ANALYSIS_OUTPUTS deps
        or the build script. No orphan scripts in the archive."""
        mk = self._read_makefile()
        script = self._read_analysis_build_script()
        # Extract all .py files from the build script's for-loop and cp lines
        copied_scripts = re.findall(r"(\w+\.py)", script)
        # Each copied script must either be in the Makefile's dep graph
        # or be a utility (utils.py, plot_style.py)
        utilities = {
            "utils.py",
            "plot_style.py",
            "pipeline_loaders.py",
            "pipeline_io.py",
            "pipeline_progress.py",
            "pipeline_text.py",
        }
        for s in copied_scripts:
            if s in utilities:
                continue
            # Script must appear as a dependency somewhere in the Makefile
            assert s in mk, (
                f"Archive copies {s} but it's not referenced "
                f"in Makefile dependency graph"
            )

    def test_archive_copies_all_needed_scripts(self):
        """Every scripts/*.py that is a prerequisite of an ANALYSIS_OUTPUTS
        target must be copied in the build script.

        This is the reverse of test_archive_scripts_match_recipe: it catches
        new script dependencies that were added to a Makefile rule but not
        to the archive's cp list."""
        mk = self._read_makefile()
        script = self._read_analysis_build_script()
        copied = set(re.findall(r"([\w.]+\.py)", script))
        # Extract ANALYSIS_OUTPUTS targets
        m_out = re.search(
            r"^ANALYSIS_OUTPUTS\s*:?=(.*?)(?=\n\S|\Z)",
            mk,
            re.MULTILINE | re.DOTALL,
        )
        assert m_out, "ANALYSIS_OUTPUTS not found"
        output_paths = re.findall(r"deliverables/\S+", m_out.group(1))
        # For each output, find its Makefile rule and collect script prereqs
        needed = set()
        for out in output_paths:
            escaped = re.escape(out)
            rule_m = re.search(
                rf"^{escaped}\b[^:]*:(.*?)$",
                mk,
                re.MULTILINE,
            )
            if rule_m:
                prereqs = rule_m.group(1)
                needed.update(re.findall(r"scripts/([\w.]+\.py)", prereqs))
        # Every needed script must be in the copied set
        missing = needed - copied
        assert not missing, (
            f"build_analysis_archive.sh is missing cp for scripts needed by "
            f"ANALYSIS_OUTPUTS targets: {sorted(missing)}"
        )


# ---------------------------------------------------------------------------
# No bare print() in pipeline scripts
# ---------------------------------------------------------------------------

# Pipeline script prefixes that must use logging, not print().
# Scripts outside these prefixes (CLI tools, one-off utilities) are not checked.
_PIPELINE_PREFIXES = (
    "compute_",
    "plot_",
    "enrich_",
    "catalog_",
    "qa_",
    "qc_",
    "build_",
    "export_",
    "analyze_",
    "filter_",
    "corpus_",
    "summarize_",
)

# CLI tools that happen to start with a pipeline prefix but produce
# human-readable console output (print is intentional, not a logging miss).
_PRINT_ALLOWLIST = {
    "compute_regression_hashes.py",
    "compute_regression_history.py",
}


class TestNoBarePrint:
    """Pipeline scripts must use logging, not print()."""

    def test_print_allowlist_not_stale(self):
        """Every script in _PRINT_ALLOWLIST must still exist."""
        all_names = set(_all_scripts())
        stale = _PRINT_ALLOWLIST - all_names
        assert not stale, f"Stale _PRINT_ALLOWLIST entries (script removed?): {stale}"

    def test_no_bare_print_in_pipeline_scripts(self):
        """Pipeline scripts may not use bare print() (use log.info())."""
        violators = []
        for name in _all_scripts():
            if not name.startswith(_PIPELINE_PREFIXES):
                continue
            if name in _PRINT_ALLOWLIST:
                continue
            tree = _parse_script(name)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                ):
                    violators.append(name)
                    break
        assert not violators, (
            f"{len(violators)} pipeline scripts use bare print() "
            f"(should use logging): {violators[:10]}"
        )


# ---------------------------------------------------------------------------
# Type annotations on core modules (mypy)
# ---------------------------------------------------------------------------

_MYPY = shutil.which("mypy")
_MYPY_AVAILABLE = _MYPY is not None


class TestTypingCoreModules:
    """Core library modules must be fully typed (mypy --disallow-untyped-defs).

    These modules are imported by many scripts — their type annotations
    serve as machine-readable interface documentation. The list grows
    as modules become shared infrastructure.
    """

    TYPED_MODULES = [
        "pipeline_text.py",
        "pipeline_io.py",
        "pipeline_progress.py",
        "enrich_dois.py",
    ]

    @pytest.mark.skipif(not _MYPY_AVAILABLE, reason="mypy not available")
    def test_mypy_passes(self):
        """Core modules must pass mypy --disallow-untyped-defs."""
        paths = [os.path.join(SCRIPTS_DIR, m) for m in self.TYPED_MODULES]
        result = subprocess.run(
            [
                _MYPY,
                "--ignore-missing-imports",
                "--disallow-untyped-defs",
                "--follow-imports=silent",
                "--no-error-summary",
            ]
            + paths,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"mypy errors in core modules:\n{result.stdout}"


# ---------------------------------------------------------------------------
# No phantom --pdf in non-plotting scripts
# ---------------------------------------------------------------------------


class TestPdfDiscipline:
    """Scripts that produce no figures should not accept --pdf.

    The --pdf flag controls PDF generation in plotting scripts. When
    non-plotting scripts accept it as a no-op "for interface compatibility",
    the flag becomes a phantom that misleads readers about what the script does.
    """

    # Scripts known to produce no figures (confirmed: no save_figure/savefig)
    NON_PLOTTING = [
        "analyze_bimodality.py",
        "compute_breakpoints.py",
        "compute_clusters.py",
        "compute_lexical.py",
        "analyze_100bn.py",
        "analyze_embeddings.py",
        "analyze_unfccc_topics.py",
        "harvest/compute_reranker_calibration.py",
        "plot_interactive_corpus.py",
    ]

    @pytest.mark.parametrize("script", NON_PLOTTING)
    def test_non_plotting_scripts_no_phantom_pdf_flag(self, script):
        path = os.path.join(SCRIPTS_DIR, script)
        src = Path(path).read_text()
        assert '"--pdf"' not in src, f"{script} accepts --pdf but produces no figures"


# ---------------------------------------------------------------------------
# Test marker discipline: @slow vs @integration
# ---------------------------------------------------------------------------

TESTS_DIR = os.path.join(REPO, "tests")


class TestMarkerDiscipline:
    """Enforce correct use of @pytest.mark.slow vs @pytest.mark.integration.

    - @integration: tests that spawn subprocesses (subprocess.run/Popen)
      or use sleep-based timing
    - @slow: tests that require network access or real corpus data
      (no subprocess spawning)

    A file that imports subprocess and marks tests @slow is almost certainly
    mislabeled — subprocess tests should be @integration.
    """

    # Files that legitimately use both @slow and subprocess. Under the
    # cost-based tiers (tickets 0213/0214) a single file may hold @integration
    # (subprocess) tests AND a @slow test (heavy numerical dep / heavy compute);
    # the two tiers describe different tests, not a mislabel.
    EXCEPTIONS = {
        # @integration subprocess tests + @slow TestPCABreakPreservation (dcor).
        "test_embedding_sensitivity.py",
        # @integration smoke class (subprocess) + @slow C2ST NullModel classes
        # (classifier-stack import ~5-8s). Different tests, not a mislabel (0216).
        "test_null_model_c2st.py",
    }

    def test_no_slow_in_subprocess_files(self):
        """Files that import subprocess must not use @slow (use @integration)."""
        violations = []
        for fname in sorted(os.listdir(TESTS_DIR)):
            if not fname.startswith("test_") or not fname.endswith(".py"):
                continue
            if fname in self.EXCEPTIONS:
                continue
            path = os.path.join(TESTS_DIR, fname)
            with open(path) as f:
                source = f.read()
            uses_subprocess = "import subprocess" in source
            # Match actual decorator lines (any indent), not string mentions
            uses_slow = bool(
                re.search(r"^\s*@pytest\.mark\.slow", source, re.MULTILINE)
            )
            if uses_subprocess and uses_slow:
                violations.append(fname)
        assert not violations, (
            f"Files using subprocess must mark tests @integration, not @slow: "
            f"{violations}"
        )

    def test_lint_tests_are_adherence(self):
        """Files invoking ruff/mypy must be in the adherence tier (ticket 0215).

        Rule-enforcement/lint tests belong to the `adherence` tier so that
        `-m "not adherence"` (the fast inner loop, ticket 0214) cleanly removes
        them — a cold `.mypy_cache` costs 9-19s and has no place on the keystroke
        loop. Detection is static (no subprocess): a file that spawns ruff or
        mypy (a quoted `"ruff"`/`"mypy"` command token alongside
        `import subprocess`) must declare a module-level
        `pytestmark = pytest.mark.adherence`, matching the convention already
        used by test_editorial_governance.py and test_manuscript_prose.py.
        """
        violations = []
        for fname in sorted(os.listdir(TESTS_DIR)):
            if not fname.startswith("test_") or not fname.endswith(".py"):
                continue
            path = os.path.join(TESTS_DIR, fname)
            with open(path) as f:
                source = f.read()
            invokes_lint = "import subprocess" in source and bool(
                re.search(r"""["'](ruff|mypy)["']""", source)
            )
            if not invokes_lint:
                continue
            has_module_adherence = bool(
                re.search(
                    r"^pytestmark\s*=.*pytest\.mark\.adherence",
                    source,
                    re.MULTILINE,
                )
            )
            if not has_module_adherence:
                violations.append(fname)
        assert not violations, (
            "Files invoking ruff/mypy must declare module-level "
            "`pytestmark = pytest.mark.adherence` so the fast loop deselects "
            f"them (ticket 0215): {violations}"
        )


# ---------------------------------------------------------------------------
# Wrong-namespace monkeypatch guard (ticket 0251; defect class from 0249)
# ---------------------------------------------------------------------------


class TestNoWrongNamespacePatch:
    """Forbid patching constants on the ``utils`` re-export facade in tests.

    ``utils`` is a re-export facade (architecture.md): every constant it
    exposes (CATALOGS_DIR, DATA_DIR, ...) is bound BY VALUE into consuming
    scripts at import time (``from utils import CATALOGS_DIR``). A test that
    patches the constant on ``utils`` therefore never reaches a consuming
    module already cached in sys.modules — the test passes in isolation and
    fails under xdist whenever a sibling test imports the module first.
    Ticket 0249 fixed two real instances of this class. The correct idiom
    patches the consuming module's namespace::

        import enrich_abstracts as ea
        monkeypatch.setattr(ea, "CATALOGS_DIR", str(tmp_path))

    Detected forms (lexical, per line): ``utils`` as the object argument of
    any setattr call — covers both ``monkeypatch.setattr`` and bare
    ``setattr`` — and the monkeypatch string-target form ``"utils.<CONST>"``.

    Known limitations of the lexical scan, accepted deliberately:

    - an aliased import (``import utils as u`` then patching ``u``) is not
      caught; no test file aliases utils today (checked 2026-07-11, ticket
      0251) and new code has no reason to start.
    - direct attribute assignment (``utils.CONST = x``) is not flagged. The
      two legitimate patterns found by the 0249 sweep use it and stay
      allowed: a test patching utils' own namespace before calling a
      function that lives in utils itself (test_robustness_observability.py
      save_run_report tests), and dual-namespace patching of utils AND the
      consuming module together (test_pipeline_e2e.py _patched_merge_dirs).
    """

    FORBIDDEN = [
        # utils as the object argument of a setattr call
        # (monkeypatch.setattr and bare setattr alike)
        re.compile(r"setattr\(\s*utils\s*,"),
        # monkeypatch string-target form: setattr with a "utils.CONST" string
        re.compile(r"""setattr\(\s*["']utils\."""),
    ]

    def test_no_setattr_on_utils_namespace(self):
        """No test may patch a constant on the utils module via setattr."""
        violations = []
        for fname in sorted(os.listdir(TESTS_DIR)):
            if not fname.endswith(".py"):
                continue
            path = os.path.join(TESTS_DIR, fname)
            with open(path) as f:
                lines = f.readlines()
            for lineno, line in enumerate(lines, start=1):
                if any(rx.search(line) for rx in self.FORBIDDEN):
                    violations.append(f"tests/{fname}:{lineno}: {line.strip()}")
        assert not violations, (
            "Wrong-namespace config patch (ticket 0249 defect class): utils "
            "is a re-export facade whose constants are bound by value into "
            "consuming scripts at import, so patching them on utils never "
            "reaches a cached module. Patch the consuming module's namespace "
            'instead, e.g. monkeypatch.setattr(ea, "CATALOGS_DIR", ...). '
            "Violations:\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# Script naming convention (#547)
# ---------------------------------------------------------------------------


class TestScriptNaming:
    """Every script in scripts/ must have a conforming prefix.

    Allowed prefixes: catalog_, enrich_, qa_, qc_, corpus_, plot_,
    analyze_, compute_, export_, summarize_, build_.

    Library modules (no prefix needed) are listed in LIBRARY_MODULES.
    """

    PREFIXES = (
        "catalog_",
        "enrich_",
        "qa_",
        "qc_",
        "corpus_",
        "plot_",
        "analyze_",
        "compute_",
        "export_",
        "summarize_",
        "build_",
        # Exploratory scout scripts: one-off empirical recon (reported negative
        # results), not production Phase-2. Kept in-repo for reproducibility.
        "scout_",
    )
    LIBRARY_MODULES = {
        "utils.py",
        "plot_style.py",
        "script_io_args.py",
        "pipeline_io.py",
        "pipeline_loaders.py",
        "pipeline_progress.py",
        "pipeline_text.py",
        "filter_flags.py",
        "filter_flags_llm.py",
        "clustering_methods.py",
        "schemas.py",
        # syllabi sub-modules (extracted from catalog_syllabi.py)
        "syllabi_config.py",
        "syllabi_crossref.py",
        "syllabi_harvest.py",
        "syllabi_io.py",
        "syllabi_process.py",
        # pool sub-module (extracted from catalog_openalex.py)
        "openalex_pool.py",
    }

    def test_all_scripts_have_conforming_prefix(self):
        for f in all_script_files():  # recursive, subdir-safe (ticket 0260)
            if f.name.startswith("_") or f.name in self.LIBRARY_MODULES:
                continue
            assert any(f.name.startswith(p) for p in self.PREFIXES), (
                f"{f.name} has non-conforming prefix"
            )


# ---------------------------------------------------------------------------
# Rules state intent only — mechanical details live in tests/hooks
# ---------------------------------------------------------------------------


class TestRulesIntentOnly:
    """Rule files must state intent, not duplicate mechanical details.

    When a rule encodes the same list, threshold, or pattern that an
    enforcing test or hook already contains, the two copies drift apart.
    The rule should point to the test; the test is the source of truth.
    """

    RULES_DIR = os.path.join(REPO, ".claude", "rules")

    def _read_rule(self, name):
        with open(os.path.join(self.RULES_DIR, name)) as f:
            return f.read()

    def test_coding_no_typed_module_list(self):
        """coding.md must not enumerate typed modules
        (TestTypingCoreModules owns that list)."""
        content = self._read_rule("coding.md")
        for mod in TestTypingCoreModules.TYPED_MODULES:
            assert mod not in content, (
                f"coding.md lists '{mod}' — that belongs in "
                f"TestTypingCoreModules.TYPED_MODULES, not the rule"
            )

    def test_coding_no_typing_syntax_examples(self):
        """coding.md must not list typing syntax
        (ruff UP rules enforce this)."""
        content = self._read_rule("coding.md")
        syntax_examples = ["list[str]", "dict[str", "Union[", "Optional["]
        found = [s for s in syntax_examples if s in content]
        assert not found, (
            f"coding.md contains typing syntax examples {found} — "
            f"ruff UP rules in TestRuffModernPython enforce this"
        )

    def test_git_no_hook_details(self):
        """git.md must not itemize pre-commit hook thresholds
        (hooks/pre-commit is the source)."""
        content = self._read_rule("git.md")
        assert ">500KB" not in content, (
            "git.md specifies file size threshold — hooks/pre-commit owns that"
        )

    def test_script_io_no_code_template(self):
        """script-io.md must not contain Python code blocks
        (agent should read a migrated script as example)."""
        content = self._read_rule("script-io.md")
        assert "```python" not in content, (
            "script-io.md contains a Python code template — "
            "the agent should read a migrated script as the example"
        )

    def test_coding_no_architecture_sections(self):
        """coding.md must not contain project architecture docs
        (those live in architecture.md)."""
        content = self._read_rule("coding.md")
        arch_headers = [
            "## Data location",
            "## Project structure",
            "## Pipeline phases",
        ]
        found = [h for h in arch_headers if h in content]
        assert not found, (
            f"coding.md contains architecture sections {found} — "
            f"these belong in architecture.md"
        )


class TestAlwaysLoadedContextBudget:
    """Always-on context (rules without path-scoping) must stay under budget.

    Claude Code loads ~150-200 instructions before compliance drops.
    AGENTS.md + unscoped rule files form the always-on context. Path-scoped
    rules (those with globs: or paths: frontmatter) load only when relevant
    files are touched, so they don't count against the budget.

    Budget: <= 300 lines total for always-loaded context.
    """

    AGENTS_MD = os.path.join(REPO, "AGENTS.md")
    RULES_DIR = os.path.join(REPO, ".claude", "rules")
    MAX_ALWAYS_LOADED_LINES = 300

    @staticmethod
    def _has_path_scope(filepath: str) -> bool:
        """Return True if the rule file has globs: or paths: frontmatter."""
        with open(filepath) as f:
            content = f.read()
        # Check for YAML frontmatter with globs: or paths:
        if not content.startswith("---"):
            return False
        # Find closing ---
        end = content.find("---", 3)
        if end == -1:
            return False
        frontmatter = content[3:end]
        return "globs:" in frontmatter or "paths:" in frontmatter

    def test_always_loaded_line_budget(self):
        """AGENTS.md + unscoped .claude/rules/*.md must be <= 300 lines.

        Path-scoped rules (with globs: or paths: frontmatter) don't count
        because they load only when the agent touches matching files.
        """
        total = 0
        contributors = []

        # Count AGENTS.md
        with open(self.AGENTS_MD) as f:
            n = sum(1 for _ in f)
        total += n
        contributors.append(f"AGENTS.md: {n}")

        # Count unscoped rule files
        for md in sorted(Path(self.RULES_DIR).glob("*.md")):
            if self._has_path_scope(str(md)):
                continue
            with open(md) as f:
                n = sum(1 for _ in f)
            total += n
            contributors.append(f"{md.name}: {n}")

        assert total <= self.MAX_ALWAYS_LOADED_LINES, (
            f"Always-loaded context is {total} lines "
            f"(budget: {self.MAX_ALWAYS_LOADED_LINES}).\n"
            f"Breakdown: {', '.join(contributors)}.\n"
            f"Fix: add globs: frontmatter to path-scope a rule file, "
            f"or trim content."
        )


# ---------------------------------------------------------------------------
# I/O discipline: --output flag (#549)
# ---------------------------------------------------------------------------


class TestOutputFlag:
    """Every script that produces files must accept --output (#549).

    Per script-io.md, scripts use parse_io_args() from script_io_args.py
    so the Makefile can pass output paths via $@.

    Scripts that are pure libraries, QA reporters (stdout only), catalog
    harvesters (DVC-managed), or interactive tools are exempt.
    """

    # Scripts with __main__ that legitimately don't need --output:
    OUTPUT_EXEMPT = {
        # QA reporters (stdout / fixed JSON)
        # qa_citations.py, qa_bibliography.py, qa_missing_references.py migrated
        # to parse_io_args with required --output (ticket 0196) — no longer exempt.
        # qa_embeddings.py, qa_metadata.py migrated likewise (ticket 0203).
        "qa_detect_language.py",
        "qa_detect_type.py",
        "qa_word_count.py",
        "qa_llm_judge_guards.py",
        # Catalog harvesters (DVC-managed)
        "catalog_bibcnrs.py",
        "catalog_grey.py",
        "catalog_istex.py",
        "catalog_merge.py",
        "catalog_openalex.py",
        "catalog_scispace.py",
        "catalog_scopus.py",
        "catalog_semanticscholar.py",
        # Teaching pipeline (DVC-managed or standalone)
        "build_teaching_canon.py",
        "build_teaching_yaml.py",
        "catalog_syllabi.py",
        "analyze_syllabi.py",
        "analyze_teaching_canon.py",
        # Interactive / exploratory tools
        "compute_clustering_comparison.py",
        "compute_temporal_communities.py",
        "analyze_communities_clusters.py",
        "plot_interactive_corpus.py",
        "enrich_openalex_keywords.py",
        # DVC join/merge stages
        "enrich_join.py",
        "corpus_merge_citations.py",
        "corpus_ref_match.py",
        "summarize_abstracts.py",
        "corpus_parse_citations_grobid.py",
        # Tool / utility scripts
        "build_smoke_fixture.py",
        "compute_regression_hashes.py",
        "compute_regression_history.py",
        "analyze_unfccc_topics.py",
        # Analysis-only reporters (stdout, no output file)
        "analyze_zscore_vs_pvalue.py",
    }

    def test_all_producing_scripts_accept_output(self):
        """Every script with __main__ that writes files must accept --output."""
        violators = []
        for f in all_script_files():  # recursive, subdir-safe (ticket 0260)
            src = f.read_text()
            if "__name__" not in src or "__main__" not in src:
                continue
            if f.name in LIBRARY_SCRIPTS:
                continue
            if f.name in self.OUTPUT_EXEMPT:
                continue
            if "--output" not in src and "parse_io_args" not in src:
                violators.append(f.name)
        assert not violators, (
            f"{len(violators)} scripts produce output but have no --output flag: "
            f"{sorted(violators)}"
        )

    # Scripts that can run with smoke fixtures (no network, no full corpus).
    # Each entry: (script, extra_args, output_extension)
    SMOKE = "tests/fixtures/smoke/catalogs"
    BLACKBOX_SCRIPTS = [
        # Phase 2 plots
        ("plot_fig1_bars.py", ["--input", f"{SMOKE}/refined_works.csv"], ".png"),
        ("plot_fig_dag.py", [], ".png"),
        # Phase 2 exports
        (
            "export_citation_coverage.py",
            ["--input", f"{SMOKE}/refined_works.csv", f"{SMOKE}/refined_citations.csv"],
            ".md",
        ),
        ("export_language_table.py", ["--input", f"{SMOKE}/refined_works.csv"], ".md"),
        (
            "export_tab_venues.py",
            [
                "--refined-works",
                f"{SMOKE}/refined_works.csv",
                "--pole-papers",
                f"{SMOKE}/tab_pole_papers.csv",
                "--min-papers",
                "1",
                "--core-threshold",
                "0",
            ],
            ".md",
        ),
        ("summarize_core_venues.py", ["--core", f"{SMOKE}/refined_works.csv"], ".csv"),
        # Remaining Phase 2 plot scripts (#549 wave 2)
        (
            "plot_fig45_pca_scatter.py",
            [
                "--input",
                f"{SMOKE}/refined_works.csv",
                f"{SMOKE}/refined_embeddings.npz",
            ],
            ".png",
        ),
        (
            "plot_fig_lexical_tfidf.py",
            ["--input", f"{SMOKE}/tab_lexical_tfidf.csv"],
            ".stamp",
        ),
        (
            "plot_fig_traditions.py",
            ["--input", f"{SMOKE}/refined_works.csv", f"{SMOKE}/refined_citations.csv"],
            ".png",
        ),
        (
            "plot_heatmap_communities_clusters.py",
            [
                "--input",
                f"{SMOKE}/refined_works.csv",
                f"{SMOKE}/refined_embeddings.npz",
                f"{SMOKE}/refined_citations.csv",
            ],
            ".png",
        ),
    ]

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "script,extra_args,ext", BLACKBOX_SCRIPTS, ids=[s[0] for s in BLACKBOX_SCRIPTS]
    )
    def test_output_file_created(self, script, extra_args, ext, tmp_path):
        """Run script --output /tmp/... and verify the file appears."""
        import subprocess

        from _source_roots import source_root_env

        out_path = tmp_path / f"test_output{ext}"
        cmd = [
            sys.executable,
            os.path.join(SCRIPTS_DIR, script),
            "--output",
            str(out_path),
        ] + extra_args
        # Source roots on PYTHONPATH (ticket 0253) so the script resolves flat
        # imports without an ambient PYTHONPATH or the retired wheel.
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                env=source_root_env())
        assert result.returncode == 0, (
            f"{script} failed (rc={result.returncode}):\n{result.stderr[-500:]}"
        )
        assert out_path.exists(), (
            f"{script} exited 0 but --output {out_path} was not created. "
            f"The script ignores --output and writes elsewhere."
        )


class TestNoValuesCallOnSeries:
    """Pandas Series .values is a property, not a method (#604).

    source_groups.values() raises TypeError at runtime because
    .values returns a numpy array, which is not callable.
    """

    COCITATION_SCRIPTS = [
        "scripts/analyze_communities_clusters.py",
        "scripts/compute_temporal_communities.py",
        "scripts/archive_traditions/detect_traditions_v2.py",
        "scripts/archive_traditions/detect_traditions_pre2015.py",
        "scripts/archive_traditions/detect_traditions_pre2020.py",
    ]

    @pytest.mark.parametrize("script", COCITATION_SCRIPTS)
    def test_source_groups_uses_property_not_method(self, script):
        """Verify source_groups.values is used, not source_groups.values()."""
        src = Path(script).read_text()
        assert "source_groups.values()" not in src, (
            f"{script} uses source_groups.values() — should be .values (property)"
        )


class TestNoHalfFinishedWork:
    """Ratchet: stubs (NotImplementedError), skip-marked tests
    (pytest.skip, @pytest.mark.skip), and TODO comments are signals
    of deferred work that someone "will come back to." Use a
    follow-up ticket instead.

    Escape hatch: `# noqa: hygiene` on the line if the marker is
    genuinely load-bearing or documents a known roadmap item with
    no immediate fix.
    """

    PATTERNS = [
        (r"raise\s+NotImplementedError", "NotImplementedError"),
        (r"@pytest\.mark\.skip\b|pytest\.skip\(", "pytest.skip"),
        (r"#\s*TODO\b", "TODO"),
    ]

    @pytest.mark.parametrize("pattern,name", PATTERNS, ids=[n for _, n in PATTERNS])
    def test_no_stubs_skips_or_todos(self, pattern, name):
        rx = re.compile(pattern)
        offenders = []
        for script in _all_scripts():
            src = _read_script(script)
            for i, line in enumerate(src.splitlines(), 1):
                if rx.search(line) and "noqa: hygiene" not in line:
                    offenders.append(f"{script}:{i}: {line.strip()}")
        assert not offenders, f"{name} found:\n  " + "\n  ".join(offenders)


class TestNoStaleRenamedScriptRefs:
    """Renamed scripts must not be referenced by their old basenames (0235).

    collect_syllabi.py  -> catalog_syllabi.py
    compare_clustering.py -> compute_clustering_comparison.py

    A lingering old name in a log hint or docstring sends a reader (or a
    future grep) to a script that no longer exists. Git history is exempt —
    this scans only live code under scripts/ and tests/.
    """

    OLD_NAMES = ("collect_syllabi", "compare_clustering")

    def test_no_old_script_basenames_in_code(self):
        offenders = []
        for name in _all_scripts():
            src = _read_script(name)
            for old in self.OLD_NAMES:
                if old in src:
                    offenders.append(f"scripts/{name}: {old}")
        # tests/ — exclude this guard file itself, which names the old
        # basenames as data (its OLD_NAMES list would otherwise self-match).
        self_name = os.path.basename(__file__)
        for fname in sorted(os.listdir(TESTS_DIR)):
            if not fname.endswith(".py") or fname == self_name:
                continue
            with open(os.path.join(TESTS_DIR, fname)) as f:
                src = f.read()
            for old in self.OLD_NAMES:
                if old in src:
                    offenders.append(f"tests/{fname}: {old}")
        assert not offenders, (
            "Stale references to pre-rename script basenames "
            "(update the reference, or move it to git history):\n  "
            + "\n  ".join(offenders)
        )


class TestPytestCollectionScope:
    """pytest must not recurse into .claude/worktrees/ (ticket 0234).

    `norecursedirs` REPLACES pytest's built-in defaults rather than
    appending to them. A value of just ["libs"] therefore silently dropped
    the default `.*` pattern that excludes dotdirs like `.claude`. From the
    primary checkout that made a tree-walking `pytest` descend into every
    live worktree's copy of tests/, inflating collection (duplicate test IDs)
    and surfacing confusing cross-worktree failures.
    """

    @staticmethod
    def _norecursedirs():
        import tomllib

        with open(os.path.join(REPO, "pyproject.toml"), "rb") as f:
            cfg = tomllib.load(f)
        return cfg["tool"]["pytest"]["ini_options"].get("norecursedirs", [])

    def test_claude_worktrees_excluded(self):
        """A norecursedirs pattern must match `.claude` so worktree copies of
        tests/ are never collected from the primary checkout."""
        import fnmatch

        patterns = self._norecursedirs()
        assert any(fnmatch.fnmatch(".claude", p) for p in patterns), (
            f"norecursedirs={patterns} does not exclude .claude — pytest will "
            "recurse into .claude/worktrees/*/tests/ from the primary checkout"
        )

    def test_libs_still_excluded(self):
        """The pre-existing libs exclusion must be preserved (an unscoped root
        `pytest` must not choke on libs/openalex-corpus)."""
        import fnmatch

        patterns = self._norecursedirs()
        assert any(fnmatch.fnmatch("libs", p) for p in patterns), (
            f"norecursedirs={patterns} no longer excludes libs — an unscoped "
            "root pytest run will choke on the openalex_corpus import"
        )
