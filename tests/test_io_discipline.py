"""Tests for #509: Script I/O discipline — canonical main() pattern.

Covers:
- parse_io_args() shared argument parser
- Migrated scripts reject missing --output
- Makefile pattern rule exists for figure scripts
"""

import glob
import os
import subprocess
import sys

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
MAKEFILE = os.path.join(os.path.dirname(__file__), "..", "Makefile")
sys.path.insert(0, SCRIPTS_DIR)


# ---------------------------------------------------------------------------
# parse_io_args() utility
# ---------------------------------------------------------------------------

class TestParseIoArgs:
    """Shared I/O argument parser works correctly."""

    def test_parse_io_args_exists(self):
        from script_io_args import parse_io_args
        assert callable(parse_io_args)

    def test_output_required(self):
        """--output is required; missing it causes SystemExit."""
        from script_io_args import parse_io_args
        with pytest.raises(SystemExit):
            parse_io_args(["--input", "foo.csv"])

    def test_input_optional(self):
        """--input is optional (some scripts get input from CATALOGS_DIR)."""
        from script_io_args import parse_io_args
        args, _ = parse_io_args(["--output", "out.png"])
        assert args.output == "out.png"
        assert args.input is None

    def test_input_single(self):
        from script_io_args import parse_io_args
        args, _ = parse_io_args(["--input", "a.csv", "--output", "out.png"])
        assert args.input == ["a.csv"]

    def test_input_multiple(self):
        from script_io_args import parse_io_args
        args, _ = parse_io_args([
            "--input", "a.csv", "b.csv", "--output", "out.png"
        ])
        assert args.input == ["a.csv", "b.csv"]

    def test_extra_args_passed_through(self):
        """Script-specific flags pass through via parse_known_args."""
        from script_io_args import parse_io_args
        args, extra = parse_io_args([
            "--output", "out.png", "--pdf", "--v1-only"
        ])
        assert "--pdf" in extra
        assert "--v1-only" in extra

    def test_validate_io_checks_output_dir(self, tmp_path):
        """validate_io fails if output directory doesn't exist."""
        from script_io_args import validate_io
        with pytest.raises(FileNotFoundError, match="directory"):
            validate_io(output=str(tmp_path / "nonexistent" / "out.png"))

    def test_validate_io_passes_for_valid_paths(self, tmp_path):
        """validate_io succeeds for valid output paths."""
        from script_io_args import validate_io
        # Should not raise
        validate_io(output=str(tmp_path / "out.png"))


# ---------------------------------------------------------------------------
# Migrated scripts
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestMigratedScripts:
    """Migrated scripts enforce --output and produce expected files."""

    def test_plot_fig1_bars_requires_output(self):
        """plot_fig1_bars.py rejects invocation without --output."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "plot_fig1_bars.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_plot_fig2_composition_requires_output(self):
        """plot_fig2_composition.py rejects invocation without --output."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "plot_fig2_composition.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_plot_fig45_pca_scatter_requires_output(self):
        """plot_fig45_pca_scatter.py rejects invocation without --output."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "plot_fig45_pca_scatter.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_plot_fig_lexical_tfidf_requires_output(self):
        """plot_fig_lexical_tfidf.py rejects invocation without --output."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "plot_fig_lexical_tfidf.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_plot_fig_traditions_requires_output(self):
        """plot_fig_traditions.py rejects invocation without --output."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "plot_fig_traditions.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_plot_heatmap_communities_clusters_requires_output(self):
        """plot_heatmap_communities_clusters.py rejects without --output."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR,
             "plot_heatmap_communities_clusters.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_qa_bib_doi_requires_output(self):
        """qa_bib_doi.py rejects invocation without --output (ticket 0196)."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "qa_bib_doi.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_qa_bibliography_requires_output(self):
        """qa_bibliography.py rejects invocation without --output (ticket 0196)."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "qa_bibliography.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_qa_citations_requires_output(self):
        """qa_citations.py rejects invocation without --output (ticket 0196)."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "qa_citations.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_qa_missing_references_requires_output(self):
        """qa_missing_references.py rejects invocation without --output (ticket 0196)."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "qa_missing_references.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_qa_metadata_requires_output(self):
        """qa_metadata.py rejects invocation without --output (ticket 0203)."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "qa_metadata.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()

    def test_qa_embeddings_requires_output(self):
        """qa_embeddings.py rejects invocation without --output (ticket 0203)."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "qa_embeddings.py")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "output" in result.stderr.lower()


class TestQaScriptsUseSharedIo:
    """qa_* audit scripts adopt the shared parse_io_args parser (ticket 0196).

    Source inspection (not subprocess) per coding-python: cheap, no import cost.
    """

    QA_SCRIPTS = [
        "qa_bib_doi.py",
        "qa_bibliography.py",
        "qa_citations.py",
        "qa_embeddings.py",
        "qa_metadata.py",
        "qa_missing_references.py",
        "qa_pdf_content.py",
    ]

    @pytest.mark.parametrize("script", QA_SCRIPTS)
    def test_imports_parse_io_args(self, script):
        with open(os.path.join(SCRIPTS_DIR, script)) as f:
            source = f.read()
        assert "parse_io_args" in source, (
            f"{script} must import parse_io_args from script_io_args"
        )


class TestComputeBreakpointsOneOutput:
    """compute_breakpoints.py writes exactly one file to --output (#594)."""

    def test_no_companion_files(self):
        """Default mode must not write stem-derived companion files."""
        source_path = os.path.join(SCRIPTS_DIR, "compute_breakpoints.py")
        with open(source_path) as f:
            source = f.read()
        # The script should not derive companion filenames from the output stem
        assert 'out_stem.replace(' not in source, (
            "compute_breakpoints.py still derives companion filenames from "
            "--output stem; each mode should write only to io_args.output"
        )

    def test_k_sensitivity_not_hardcoded(self):
        """K-sensitivity output path must come from --output, not hardcoded."""
        source_path = os.path.join(SCRIPTS_DIR, "compute_breakpoints.py")
        with open(source_path) as f:
            source = f.read()
        assert '"tab_k_sensitivity.csv"' not in source, (
            "compute_breakpoints.py still hardcodes tab_k_sensitivity.csv; "
            "k-sensitivity mode should write to io_args.output"
        )

    def test_mutually_exclusive_modes(self):
        """--robustness and --k-sensitivity should be mutually exclusive."""
        source_path = os.path.join(SCRIPTS_DIR, "compute_breakpoints.py")
        with open(source_path) as f:
            source = f.read()
        assert "add_mutually_exclusive_group" in source, (
            "compute_breakpoints.py should use mutually exclusive argument "
            "group for --robustness and --k-sensitivity"
        )


# ---------------------------------------------------------------------------
# $(DERIVED) producers create their output dir before validate_io (ticket 0233)
# ---------------------------------------------------------------------------
#
# `validate_io` only *checks* the output dir exists (it raises on a missing
# dir; that raise is pinned by test_validate_io_checks_output_dir). It does not
# create it. `content/tables/` is git-tracked and always present, but
# `data/derived/` (= $(DERIVED)) is gitignored and regenerable — absent on a
# clean tree. So every producer whose Make target writes under $(DERIVED) must
# `os.makedirs(...)` before `validate_io`, or an isolated / `make -jN` build on
# a clean tree fails depending on which producer runs first (ticket 0218 fixed
# four; 0233 finishes the class and adds this standing guard).
#
# The guard is Makefile-driven, not a hardcoded script list: it discovers every
# $(DERIVED)-valued producer target from the Makefile, so a NEW producer that
# forgets the bootstrap is caught automatically.


def _makefile_text():
    """Concatenate the main Makefile and every included *.mk.

    Phase-2 analysis concern fragments moved under scripts/analysis/ (ticket
    0239); include them so the $(DERIVED)-producer scan still sees their targets.
    """
    root = os.path.join(os.path.dirname(__file__), "..")
    mk_files = [os.path.join(root, "Makefile")]
    mk_files += sorted(glob.glob(os.path.join(root, "*.mk")))
    mk_files += sorted(glob.glob(os.path.join(root, "scripts", "analysis", "*.mk")))
    text = ""
    for path in mk_files:
        with open(path) as f:
            text += f"\n# === {os.path.basename(path)} ===\n" + f.read()
    return text


def _derived_producer_scripts():
    """Scripts wired to a Make target whose output resolves under data/derived.

    Two-pass Make variable resolution scoped to $(DERIVED)-valued variables,
    then scan target lines for a `scripts/*.py` prerequisite.
    """
    import re

    text = _makefile_text()

    # Join `\`-continuation lines so a recipe target and its prerequisites
    # (often wrapped) are scanned as one logical line.
    text = re.sub(r"\\\n\s*", " ", text)

    # Pass 1: collect variables whose value expands under data/derived.
    assign = re.compile(r"^([A-Z][A-Z0-9_]*)\s*:?=\s*(.+?)\s*$", re.MULTILINE)
    values = {m.group(1): m.group(2) for m in assign.finditer(text)}

    def expands_to_derived(val, depth=0):
        if depth > 10:
            return False
        val = val.strip()
        if val.startswith("data/derived"):
            return True
        m = re.match(r"^\$\(([A-Z][A-Z0-9_]*)\)", val)
        if m and m.group(1) in values:
            return expands_to_derived(values[m.group(1)], depth + 1)
        return False

    derived_vars = {v for v, val in values.items() if expands_to_derived(val)}

    # Pass 2: target lines whose LHS resolves under data/derived. LHS forms:
    #   $(VAR):                  bare derived var  (e.g. $(SEMANTIC_CLUSTERS))
    #   $(DERIVEDVAR)/literal:   var + suffix      (e.g. $(DERIVED)/tab_x.csv)
    #   data/derived/literal:    literal path
    producers = {}
    target = re.compile(r"^(?!\t)(\S.*?):(?!=)\s*(.*)$")
    for line in text.splitlines():
        m = target.match(line)
        if not m:
            continue
        lhs = m.group(1).strip()
        var = re.match(r"^\$\(([A-Z][A-Z0-9_]*)\)", lhs)
        is_derived = (
            lhs.startswith("data/derived")
            or (var is not None and var.group(1) in derived_vars)
        )
        if not is_derived:
            continue
        script = re.search(r"scripts/(\S+\.py)", m.group(2))
        if script:
            producers[script.group(1)] = lhs
    return producers


class TestDerivedProducersMakedirs:
    """Every $(DERIVED)-writing producer creates its output dir before validate_io.

    Source inspection (adherence tier) — cheap, deterministic, no subprocess.
    Ticket 0233; the class the ticket 0218 fix belongs to.
    """

    pytestmark = pytest.mark.adherence

    PRODUCERS = _derived_producer_scripts()

    def test_discovery_nonempty(self):
        """The Makefile scan must find every known $(DERIVED) producer.

        Pinning the full known set (not just a sample) means a discovery
        regression that silently drops a producer — leaving it unguarded —
        fails here instead of passing vacuously.
        """
        found = set(self.PRODUCERS)
        expected = {
            "analyze_embeddings.py",
            "analyze_cocitation.py",
            "build_het_core.py",
            "compute_lexical.py",
            "compute_analytical_null.py",
            "compute_crossyear_zscore.py",
            "compute_sensitivity_grid.py",
            "compute_venue_concentration.py",
            # 0218's four (already fixed) — the guard must keep covering them.
            "compute_breakpoints.py",
            "compute_clusters.py",
            "analyze_bimodality.py",
            "analyze_genealogy.py",
        }
        missing = expected - found
        assert not missing, (
            f"Makefile scan lost known $(DERIVED) producers: {sorted(missing)}"
        )

    @pytest.mark.parametrize("script", sorted(_derived_producer_scripts()))
    def test_makedirs_before_validate_io(self, script):
        with open(os.path.join(SCRIPTS_DIR, script)) as f:
            source = f.read()
        if "validate_io(" not in source:
            pytest.skip(f"{script} does not use validate_io")
        # The makedirs must (a) target the output path — os.path.dirname of the
        # parsed output — and (b) sit in the main() prologue, between
        # parse_io_args() and validate_io(). Anchoring both defeats a decoy: an
        # unrelated makedirs elsewhere (e.g. analyze_genealogy's module-level
        # makedirs(TABLES_DIR), analyze_bimodality's makedirs(pole_dir)) must
        # NOT satisfy the guard, so deleting the real fix turns it RED.
        vi = source.index("validate_io(")
        pio = source.rfind("parse_io_args()", 0, vi)
        prologue = source[pio:vi] if pio != -1 else source[:vi]
        assert "os.makedirs(os.path.dirname(io_args.output)" in prologue, (
            f"{script} writes under $(DERIVED) but does not "
            f"os.makedirs(os.path.dirname(io_args.output) ...) between "
            f"parse_io_args() and validate_io — an isolated/clean-tree build "
            f"(no data/derived/) will fail. Add "
            f"os.makedirs(os.path.dirname(io_args.output) or '.', exist_ok=True) "
            f"immediately before validate_io (ticket 0233)."
        )
