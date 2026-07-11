"""Tests for Phase 1 Makefile contract — #52, updated for DVC delegation (#129).

Tests verify:
- Phase 1 target definitions exist in correct order
- corpus meta-target delegates to run_corpus_pipeline.sh (which calls dvc repro)
- Artifact dependency contracts are expressed in dvc.yaml (not Makefile recipes)
- The old cheap pre-filter is absent from corpus-discover
"""

import os
import re
from pathlib import Path

import yaml
from _mk_discovery import all_makefiles

MAKEFILE = os.path.join(os.path.dirname(__file__), "..", "Makefile")
DVC_YAML = os.path.join(os.path.dirname(__file__), "..", "dvc.yaml")


def read_makefile():
    with open(MAKEFILE) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Target presence
# ---------------------------------------------------------------------------

class TestTargetPresence:
    def test_corpus_discover_target_exists(self):
        mk = read_makefile()
        assert re.search(r"^corpus-discover\s*:", mk, re.MULTILINE), \
            "corpus-discover target missing"

    def test_corpus_enrich_target_exists(self):
        mk = read_makefile()
        assert re.search(r"^corpus-enrich\s*:", mk, re.MULTILINE), \
            "corpus-enrich target missing"

    def test_corpus_extend_target_exists(self):
        mk = read_makefile()
        assert re.search(r"^corpus-extend\s*:", mk, re.MULTILINE), \
            "corpus-extend target missing (new Phase 1c)"

    def test_corpus_filter_target_exists(self):
        mk = read_makefile()
        assert re.search(r"^corpus-filter\s*:", mk, re.MULTILINE), \
            "corpus-filter target missing (new Phase 1d)"

    def test_corpus_target_delegates_to_script(self):
        """The 'corpus' meta-target must delegate to run_corpus_pipeline.sh.

        The pipeline logic (guards, dvc repro, auto-commit) lives in a
        standalone bash script for testability and readability. The Makefile
        simply invokes it.
        """
        mk = read_makefile()
        m = re.search(r"^corpus\s*:(.*?)(?=\n\S|\Z)", mk, re.MULTILINE | re.DOTALL)
        assert m, "corpus meta-target not found"
        body = m.group(0)
        assert "run_corpus_pipeline.sh" in body, \
            "corpus meta-target must delegate to scripts/run_corpus_pipeline.sh"

    def test_corpus_pipeline_script_calls_dvc_repro(self):
        """The extracted corpus pipeline script must call 'dvc repro'.

        Since DVC owns the dependency graph (dvc.yaml), the script must
        delegate to 'dvc repro' rather than chaining individual phase targets.
        """
        script = (Path(__file__).resolve().parent.parent / "scripts" / "run_corpus_pipeline.sh").read_text()
        assert "dvc repro" in script, \
            "run_corpus_pipeline.sh must call 'dvc repro' (DVC owns the pipeline DAG)"


# ---------------------------------------------------------------------------
# No cheap pre-filter in corpus-discover
# ---------------------------------------------------------------------------

class TestNoCheapPrefilter:
    def test_corpus_discover_does_not_call_cheap(self):
        """corpus-discover must not invoke corpus_filter.py --cheap."""
        mk = read_makefile()
        # Find the corpus-discover recipe (lines after the target until next target)
        m = re.search(
            r"^corpus-discover\s*:.*?\n((?:\t.*\n?)*)",
            mk, re.MULTILINE
        )
        assert m, "corpus-discover target not found"
        recipe = m.group(1)
        assert "--cheap" not in recipe, \
            "corpus-discover still invokes corpus_filter.py --cheap (remove it)"

    def test_corpus_discover_does_not_call_corpus_filter(self):
        """corpus-discover must not call corpus_filter.py at all."""
        mk = read_makefile()
        m = re.search(
            r"^corpus-discover\s*:.*?\n((?:\t.*\n?)*)",
            mk, re.MULTILINE
        )
        assert m, "corpus-discover target not found"
        recipe = m.group(1)
        assert "corpus_filter.py" not in recipe, \
            "corpus-discover must not run corpus_filter.py; filtering belongs in corpus-extend/corpus-filter"


# ---------------------------------------------------------------------------
# Contract output variables
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# DVC YAML cmd sanity
# ---------------------------------------------------------------------------

class TestDvcYamlCmds:
    """Each stage cmd must be a valid single-line shell command (no embedded newlines)."""

    def test_no_newlines_in_cmds(self):
        """YAML >- with extra-indented lines preserves newlines, breaking shell commands."""
        dvc_path = os.path.join(os.path.dirname(__file__), "..", "dvc.yaml")
        with open(dvc_path) as f:
            dvc = yaml.safe_load(f)
        for name, spec in dvc["stages"].items():
            cmd = spec.get("cmd", "")
            assert "\n" not in cmd, (
                f"Stage '{name}' cmd contains newlines — "
                f"YAML >- preserves them for extra-indented lines. "
                f"Put each command on one line."
            )


# ---------------------------------------------------------------------------
# Contract output variables
# ---------------------------------------------------------------------------

class TestContractVariables:
    def test_unified_variable_declared(self):
        """Makefile must declare UNIFIED path variable."""
        mk = read_makefile()
        assert re.search(r"^UNIFIED\s*:?=", mk, re.MULTILINE), \
            "UNIFIED variable not declared"

    def test_enriched_variable_declared(self):
        """Makefile must declare ENRICHED path variable."""
        mk = read_makefile()
        assert re.search(r"^ENRICHED\s*:?=", mk, re.MULTILINE), \
            "ENRICHED variable not declared"

    def test_extended_variable_declared(self):
        """Makefile must declare EXTENDED path variable."""
        mk = read_makefile()
        assert re.search(r"^EXTENDED\s*:?=", mk, re.MULTILINE), \
            "EXTENDED variable not declared"


# ---------------------------------------------------------------------------
# Artifact dependency checks (now in dvc.yaml, not Makefile recipes)
# ---------------------------------------------------------------------------

def read_dvc_yaml():
    with open(DVC_YAML) as f:
        return yaml.safe_load(f)


class TestFailFastChecks:
    def test_corpus_enrich_checks_for_unified(self):
        """dvc.yaml join_enrichments stage must declare unified_works.csv as a dependency.

        Previously the Makefile corpus-enrich recipe contained a fail-fast check.
        Now DVC owns the dependency graph: the contract is expressed in dvc.yaml
        deps, which DVC enforces before running the stage.
        """
        dvc = read_dvc_yaml()
        assert "join_enrichments" in dvc.get("stages", {}), \
            "join_enrichments stage missing from dvc.yaml"
        deps = dvc["stages"]["join_enrichments"].get("deps", [])
        dep_paths = [str(d) for d in deps]
        assert any("unified_works.csv" in p for p in dep_paths), \
            "dvc.yaml join_enrichments stage must list unified_works.csv in deps"

    def test_join_depends_on_all_enrichment_stamps(self):
        """join_enrichments must depend on all 4 enrichment stamp files.

        Without stamp dependencies, `dvc repro join_enrichments` could run
        before enrichment stages populate their caches. See #428.
        """
        dvc = read_dvc_yaml()
        deps = [str(d) for d in dvc["stages"]["join_enrichments"].get("deps", [])]
        expected_stamps = [".dois.stamp", ".abstracts.stamp",
                          ".language.stamp", ".summaries.stamp"]
        for stamp in expected_stamps:
            assert any(stamp in d for d in deps), \
                f"join_enrichments must depend on {stamp}"

    def test_corpus_extend_checks_for_enriched(self):
        """dvc.yaml extend stage must declare enriched_works.csv as a dependency.

        Previously the Makefile corpus-extend recipe contained a fail-fast check.
        Now DVC owns the dependency graph: the contract is expressed in dvc.yaml
        deps, which DVC enforces before running the stage.
        """
        dvc = read_dvc_yaml()
        assert "extend" in dvc.get("stages", {}), "extend stage missing from dvc.yaml"
        deps = dvc["stages"]["extend"].get("deps", [])
        dep_paths = [str(d) for d in deps]
        assert any("enriched_works.csv" in p for p in dep_paths), \
            "dvc.yaml extend stage must list enriched_works.csv in deps"

    def test_corpus_filter_checks_for_extended(self):
        """dvc.yaml filter stage must declare extended_works.csv as a dependency.

        Previously the Makefile corpus-filter recipe contained a fail-fast check.
        Now DVC owns the dependency graph: the contract is expressed in dvc.yaml
        deps, which DVC enforces before running the stage.
        """
        dvc = read_dvc_yaml()
        assert "filter" in dvc.get("stages", {}), "filter stage missing from dvc.yaml"
        deps = dvc["stages"]["filter"].get("deps", [])
        dep_paths = [str(d) for d in deps]
        assert any("extended_works.csv" in p for p in dep_paths), \
            "dvc.yaml filter stage must list extended_works.csv in deps"


# ---------------------------------------------------------------------------
# Per-deliverable render rules (#217, tickets 0226 + 0237)
# ---------------------------------------------------------------------------

def read_paths_mk():
    p = os.path.join(os.path.dirname(__file__), "..", "paths.mk")
    with open(p) as f:
        return f.read()


class TestPerDeliverableIncludes:
    """Since 0226 each deliverable is a folder-scoped Quarto project, and since
    0237 each owns a render-only .mk that depends on its OWN includes (not the
    retired PROJECT_INCLUDES union). The per-doc include sets live in paths.mk."""

    def test_citation_coverage_in_techrep_includes(self):
        """tab_citation_coverage.md is included transitively via citation-quality.md."""
        paths = read_paths_mk()
        m = re.search(r"^TECHREP_INCLUDES\s*:=\s*(.*?)(?=\n\S|\n\n)", paths,
                       re.MULTILINE | re.DOTALL)
        assert m, "TECHREP_INCLUDES not found in paths.mk"
        assert "tab_citation_coverage.md" in m.group(1), \
            "TECHREP_INCLUDES must list tab_citation_coverage.md (transitive dep of citation-quality.md)"

    def test_project_includes_union_retired(self):
        """The PROJECT_INCLUDES union model is retired (0237): no render rule uses it.

        Each render .mk depends on its own doc's includes, so no `.mk` may still
        reference $(PROJECT_INCLUDES).
        """
        root = os.path.join(os.path.dirname(__file__), "..")
        # A live use ($(PROJECT_INCLUDES)) or definition (PROJECT_INCLUDES :=/=),
        # not an incidental mention in a comment.
        use_or_def = re.compile(r"\$\(PROJECT_INCLUDES\)|^\s*PROJECT_INCLUDES\s*:?=", re.MULTILINE)
        offenders = []
        # Shared discovery (ticket 0248): all_makefiles() now also covers
        # scripts/analysis/*.mk, closing the gap where relocated fragments (0239)
        # went unscanned for a lingering $(PROJECT_INCLUDES) reference.
        for mkpath in all_makefiles():
            with open(mkpath) as f:
                if use_or_def.search(f.read()):
                    offenders.append(os.path.relpath(mkpath, root))
        assert not offenders, \
            f"PROJECT_INCLUDES is retired; still used/defined in: {offenders}"

    def test_manuscript_pdf_rule_lives_in_manuscript_mk(self):
        """The manuscript render rule lives in deliverables/manuscript/manuscript.mk (tickets 0131, 0226).

        The manuscript writing workpackage builds clean-room from committed
        deliverables. It no longer depends on PROJECT_INCLUDES (the union of every
        doc's includes, some of which are other workpackages' deliverables) —
        instead the manuscript is its own Quarto project
        (deliverables/manuscript/_quarto.yml), whose folder-scoped discovery sees
        only the manuscript-workpackage docs, so the rule needs only the
        manuscript's own committed inputs. The top-level Makefile must NOT
        redefine the rule.
        """
        mk = read_makefile()
        assert not re.search(r"^deliverables/manuscript/manuscript\.pdf\s*:", mk, re.MULTILINE), \
            "manuscript.pdf rule must live in manuscript.mk, not the top-level Makefile"
        mk_path = os.path.join(os.path.dirname(__file__), "..", "deliverables", "manuscript", "manuscript.mk")
        with open(mk_path) as f:
            wp = f.read()
        m = re.search(r"^deliverables/manuscript/manuscript\.pdf\s*:(.*?)$", wp, re.MULTILINE)
        assert m, "manuscript.pdf target not found in manuscript.mk"
        assert "PROJECT_INCLUDES" not in wp, \
            "manuscript.mk must not couple to PROJECT_INCLUDES (it is its own Quarto project)"

    def test_techrep_pdf_rule_lives_in_render_mk(self):
        """technical-report.pdf lives in its render .mk and depends on TECHREP_INCLUDES (0237)."""
        mk = read_makefile()
        assert not re.search(
            r"^deliverables/technical-report/technical-report\.pdf\s*:", mk, re.MULTILINE
        ), "technical-report.pdf rule must live in its render .mk, not the top-level Makefile"
        render_path = os.path.join(
            os.path.dirname(__file__), "..", "deliverables", "technical-report",
            "technical-report.mk",
        )
        with open(render_path) as f:
            wp = f.read()
        m = re.search(
            r"^deliverables/technical-report/technical-report\.pdf\s*:(.*?)$",
            wp, re.MULTILINE,
        )
        assert m, "technical-report.pdf target not found in technical-report.mk"
        assert "TECHREP_INCLUDES" in m.group(1), \
            "technical-report.pdf must depend on $(TECHREP_INCLUDES)"


# ---------------------------------------------------------------------------
# Manuscript archive checksums (#219)
# ---------------------------------------------------------------------------

class TestManuscriptArchiveChecksums:
    """Manuscript archive must ship checksums for inputs and output PDF."""

    @staticmethod
    def _read_manuscript_build_script():
        script = os.path.join(os.path.dirname(__file__), "..",
                              "build",
                              "build_manuscript_archive.sh")
        with open(script) as f:
            return f.read()

    def test_archive_manuscript_generates_checksums(self):
        """Manuscript archive build script must produce a checksums file."""
        script = self._read_manuscript_build_script()
        assert "md5sum" in script, \
            "build_manuscript_archive.sh must run md5sum to generate checksums"

    def test_archive_manuscript_includes_pdf(self):
        """Manuscript archive build script must copy the built PDF into the archive."""
        script = self._read_manuscript_build_script()
        assert "manuscript.pdf" in script, \
            "build_manuscript_archive.sh must include the built manuscript.pdf"
