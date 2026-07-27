"""Layout guard for the data paper Zenodo archive (ticket 0280, remark ED-04).

The editor asked that the Zenodo package distinguish raw data inputs (the
per-source catalogs such as ``bibcnrs_works.csv``) from the final data
products of the paper (``climate_finance_corpus.csv``, ``embeddings.npz``,
``citations.csv``, ``codebook.md``). The build script must stage that split
reproducibly — ``data/inputs/`` vs ``data/products/`` — and the README
template and paper text must describe the same layout.

Mechanical greps in the spirit of test_archive_script_paths.py: they pin the
staging paths in the build script, not the runtime tree, so they run without
corpus data.
"""

import os
import re
import subprocess
import sys

import pytest

pytestmark = pytest.mark.adherence

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD_SCRIPT = os.path.join(REPO, "build", "build_datapaper_archive.sh")
README = os.path.join(REPO, "build", "templates", "README-datapaper.md")
QMD = os.path.join(REPO, "deliverables", "data-paper", "data-paper.qmd")
GITIGNORE = os.path.join(REPO, ".gitignore")
CODEBOOK = os.path.join(REPO, "deliverables", "_shared", "tables", "codebook.md")

PRODUCTS = ["climate_finance_corpus.csv", "embeddings.npz", "citations.csv", "codebook.md"]


def _read(path):
    with open(path) as f:
        return f.read()


class TestBuildScriptLayout:
    def test_stages_inputs_and_products_dirs(self):
        sh = _read(BUILD_SCRIPT)
        assert '"$TMP/data/inputs"' in sh, "build script must mkdir data/inputs"
        assert '"$TMP/data/products"' in sh, "build script must mkdir data/products"

    def test_products_go_to_products_dir(self):
        sh = _read(BUILD_SCRIPT)
        for name in PRODUCTS:
            # each product is written or copied into data/products/
            pattern = re.compile(r"data/products[/\"]", re.MULTILINE)
            assert pattern.search(sh)
            assert name in sh, f"{name} missing from build script"
            line = next(ln for ln in sh.splitlines() if name in ln and ("cp " in ln or "--output" in ln))
            assert "data/products" in line, f"{name} must be staged under data/products/: {line!r}"

    @pytest.mark.integration
    def test_table_discovery_finds_every_include(self):
        """Run the script's own discovery pipeline, don't just grep for it.

        The staged table list is derived from the paper's `{{< include >}}`
        directives, so the guard has to execute that derivation: a regex that
        silently misses a filename would read fine in the source and ship an
        archive that cannot render.
        """
        sh = _read(BUILD_SCRIPT)
        pipeline = next(
            ln for ln in sh.splitlines() if "grep -o" in ln and "include" in ln
        )
        # Reproduce the recipe verbatim, minus the trailing line-continuation.
        cmd = pipeline.rstrip("\\").strip() + " | sed 's|.*tables/||' | sort -u"
        found = subprocess.run(
            ["bash", "-c", cmd], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.split()

        expected = sorted(set(re.findall(
            r"\{\{<\s*include\s+\S*tables/(\S+\.md)\s*>\}\}", _read(QMD)
        )))
        assert found == expected, (
            f"discovery pipeline yields {found}, paper includes {expected}"
        )

    def test_source_catalogs_go_to_inputs_dir(self):
        sh = _read(BUILD_SCRIPT)
        line = next(ln for ln in sh.splitlines() if "_works.csv" in ln and "cp " in ln)
        assert "data/inputs" in line, f"per-source catalogs must land in data/inputs/: {line!r}"

    def test_checksums_cover_subdirectories(self):
        """md5sum over a flat * glob misses inputs/ and products/ subdirs."""
        sh = _read(BUILD_SCRIPT)
        line = next(ln for ln in sh.splitlines() if "md5sum" in ln)
        assert "find" in line or "*/" in line or "inputs" in line, (
            f"checksum generation must recurse into inputs/ and products/: {line!r}"
        )

    def test_codebook_source_exists(self):
        """codebook.md is a committed deliverable (ticket 0287) the build cp's."""
        assert os.path.isfile(CODEBOOK), (
            "deliverables/_shared/tables/codebook.md must exist (make corpus-tables "
            "generates it; it is committed like its table twins)"
        )


class TestDocsMatchLayout:
    def test_readme_documents_split(self):
        md = _read(README)
        assert "inputs/" in md and "products/" in md
        for name in PRODUCTS:
            assert name in md, f"README must list {name}"

    def test_paper_text_matches_layout(self):
        qmd = _read(QMD)
        assert "inputs/" in qmd and "products/" in qmd, (
            "data-paper.qmd Data section must describe the inputs/ vs products/ split"
        )


class TestSourceCardinality:
    """Ticket 0327, gap 5: the corpus grew from six sources to eight, but the
    deposit title, the related-dataset entry, the suggested citation and §3
    kept the v1.0 wording.

    Scope is deliberately the data paper and the deposit metadata only. The
    Œconomia manuscript and the Gide slides say "six sources" *correctly* —
    manuscript-vars.yml is pinned to the v1.0 corpus, which had six.
    """

    STALE = ("six sources", "Six Sources", "six per-source", "Six sources")

    @pytest.mark.parametrize("path", [QMD, README])
    def test_no_stale_source_cardinality(self, path):
        text = _read(path)
        for phrase in self.STALE:
            assert phrase not in text, (
                f"{os.path.basename(path)} still says {phrase!r} — the corpus "
                "has eight sources since v2 (ticket 0327)"
            )

    def test_archive_ships_every_source_catalog(self):
        """The `data/inputs/` loop is a hardcoded list; it must cover every
        source the corpus declares, or the deposit ships fewer catalogs than
        the paper claims."""
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        from utils import SOURCE_NAMES

        sh = _read(BUILD_SCRIPT)
        loop = next(ln for ln in sh.splitlines() if "for src in" in ln)
        missing = [s for s in SOURCE_NAMES if s not in loop]
        assert not missing, (
            f"build_datapaper_archive.sh stages catalogs for {loop.strip()!r}; "
            f"missing: {missing}"
        )


class TestDepositCountsTrackTheCorpus:
    """The deposit's prose is the one place the project's vars-driven-prose
    rule cannot reach: the archive README and the Zenodo record description
    are pasted by hand, so their counts are literals. Five of them had drifted
    (two by ~260 works, and the two files disagreed with each other by 6),
    which is the same defect class as ticket 0327 one layer out. Pin them to
    the generated vars instead of leaving them unwatched."""

    ED04 = os.path.join(
        REPO, "deliverables", "data-paper", "revision-rdj26561",
        "ed04-zenodo-restructure-upload.md",
    )

    def _vars(self):
        path = os.path.join(REPO, "deliverables", "data-paper", "data-paper-vars.yml")
        if not os.path.isfile(path):
            pytest.skip("data-paper-vars.yml not built here — run make stats")
        values = {}
        for line in _read(path).splitlines():
            key, _, value = line.partition(":")
            values[key.strip()] = value.strip().strip('"')
        return values

    @pytest.mark.parametrize(
        ("path", "keys"),
        [
            (README, ("corpus_raw", "corpus_with_embeddings", "cite_total_rows")),
            (ED04, ("corpus_raw", "corpus_with_embeddings")),
        ],
    )
    def test_quoted_counts_match_the_generated_vars(self, path, keys):
        values = self._vars()
        text = _read(path)
        for key in keys:
            assert values[key] in text, (
                f"{os.path.basename(path)} does not quote the current "
                f"{key} ({values[key]}); a stale count ships to the deposit"
            )

    def test_record_description_does_not_claim_unchanged_data(self):
        """The v2 harvest adds two source layers, so the archive's data files
        do change; the runbook must not tell the author otherwise."""
        assert "unchanged from the previous version" not in _read(self.ED04)


class TestGitignoreCodebookNegation:
    def test_codebook_unignored(self):
        gi = _read(GITIGNORE)
        assert "!deliverables/_shared/tables/codebook.md" in gi
