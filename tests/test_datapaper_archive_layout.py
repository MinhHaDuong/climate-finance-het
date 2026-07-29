"""Layout guard for the data paper Zenodo archive (ticket 0280, remark ED-04).

The editor asked that the Zenodo package distinguish raw data inputs (the
per-source catalogs such as ``bibcnrs_works.csv``) from the final data
products of the paper (``climate_finance_corpus.csv``, ``embeddings.npz``,
``citations.csv``, and the descriptor ``datapackage.json``). The build script
must stage that split reproducibly — ``data/inputs/`` vs ``data/products/`` — and the README
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
MAKEFILE_DATAPAPER = os.path.join(REPO, "build", "templates", "Makefile.datapaper")

PRODUCTS = [
    "climate_finance_corpus.csv", "embeddings.npz", "citations.csv",
    "datapackage.json",
    # The per-work keep/remove/dedup audit trail §3's refined-subset rule
    # points at — makes the subset reconstructible (author, 2026-07-29).
    "corpus_audit.csv",
    # The retrieval-protocol appendix §2.1 points referees at (ticket 0329).
    "tab_retrieval_protocol.csv", "tab_retrieval_protocol.md",
    # The reranker human-validation evidence §2.3 quotes AUC = 0.818 from
    # (ticket 0372): per-quintile rates + the two sample sheets + the
    # weak-label calibration set.
    "tab_reranker_validation.csv", "reranker_hitl_stratified.csv",
    "reranker_hitl_review.csv", "reranker_calibration.csv",
    # The per-stratum removal ablation §2.3's bias paragraph points at
    # (ticket 0337).
    "tab_filter_ablation.csv",
]

# The correspondence that describes the deposit to the editor (ticket 0403).
# These are outside the vars-driven-prose rule — the filenames in them are
# literals, and the ed04 record description is pasted into the live Zenodo
# record by hand.
SUBMISSION_DOCS = [
    os.path.join(REPO, "deliverables", "data-paper", "revision-rdj26561", name)
    for name in ("ed04-zenodo-restructure-upload.md",
                 "summary-of-revisions.md",
                 "response-letter.md")
]

# Deliberate exceptions: a product name a document may mention although the
# build does not ship it, each with the reason. Empty by design — an entry here
# is a claim that prose may outrun the build, which wants justifying.
# `test_prose_allowlist_entries_are_earned` rejects one that has become
# redundant, so it cannot rot into a mute skip (the pattern
# config/unrendered-artifacts.txt uses).
PROSE_PRODUCT_ALLOWLIST: dict[str, str] = {}

# Extensions a deposited product can carry. Anything else in a products
# sentence (a directory, a command, a section reference) is not a candidate.
_PRODUCT_EXT = r"\.(?:csv|json|npz|tar\.gz|md)"
_PATHISH = re.compile(r"[\w./-]+" + _PRODUCT_EXT + r"\b")
_BACKTICKED = re.compile(r"`([^`]+)`")


def _read(path):
    with open(path) as f:
        return f.read()


def shipped_products(build_script_text=None):
    """Product basenames the build script actually stages into data/products/.

    Derived rather than restated: `PRODUCTS` above is the pinned expectation and
    `test_products_list_matches_the_build_script` holds the two together, so the
    build script stays the single authority on what the deposit contains.
    """
    sh = build_script_text if build_script_text is not None else _read(BUILD_SCRIPT)
    names = set()
    for line in sh.splitlines():
        if "data/products" not in line:
            continue
        # `cp SRC "$TMP/data/products/"` names the file in SRC; an emitter names
        # it in --output. Both are path-ish tokens on the staging line.
        names.update(os.path.basename(m.group(0)) for m in _PATHISH.finditer(line))
    return names


def products_named_in(text):
    """Filenames a document presents as contents of the deposit.

    Scoped to a window, because these documents name plenty of files that are
    not deposit products (scripts, configs, catalogs). The window opens on a
    `data/products/` mention and closes at the end of that paragraph, which is
    how all three documents enumerate the deposit: a `data/products/` clause
    followed by a backticked list. Only backticked, path-ish tokens with a
    product extension count.
    """
    lines = text.splitlines()
    found = set()
    for i, line in enumerate(lines):
        if "data/products" not in line:
            continue
        last_stem = None
        for j in range(i, len(lines)):
            if j > i and not lines[j].strip():
                break
            for token in _BACKTICKED.findall(lines[j]):
                matches = [os.path.basename(m.group(0)) for m in _PATHISH.finditer(token)]
                if matches:
                    found.update(matches)
                    last_stem = re.sub(_PRODUCT_EXT + r"$", "", matches[-1])
                elif last_stem and re.fullmatch(_PRODUCT_EXT, token):
                    found.add(last_stem + token)
    return found


class TestRenderRuleTracksTheIncludeClosure:
    """The archived render rule's shared tables must equal the tables the paper
    includes (ticket 0384, gap 5).

    The build script stages tables by discovering the paper's own
    `{{< include >}}` directives, so staging cannot go stale. The Makefile's
    prerequisite list is hand-kept and did: it named four tables where the
    paper includes five, so editing `tab_corpus_flow.md` gave Make no reason to
    re-render. The archive still shipped the file, which is why nothing failed
    — only staleness detection broke.
    """

    def _included_tables(self):
        return set(
            re.findall(r"\{\{<\s*include\s+\S*tables/(\S+\.md)", _read(QMD))
        )

    def _render_rule_tables(self):
        return set(
            re.findall(r"\$\(SHARED\)/tables/(\S+\.md)", _read(MAKEFILE_DATAPAPER))
        )

    def test_render_rule_lists_every_included_table(self):
        missing = self._included_tables() - self._render_rule_tables()
        assert not missing, (
            "Makefile.datapaper's render rule omits tables data-paper.qmd "
            f"includes, so Make cannot see them go stale: {sorted(missing)}"
        )

    def test_render_rule_lists_no_table_the_paper_dropped(self):
        extra = self._render_rule_tables() - self._included_tables()
        assert not extra, (
            "Makefile.datapaper's render rule requires tables the paper no "
            f"longer includes, forcing needless rebuilds: {sorted(extra)}"
        )


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

    def test_descriptors_are_emitted_then_validated(self):
        """The descriptors are generated into products/, not copied in.

        Order is the guarantee: emitted from the CSV just written, then
        validated against it, before anything is packaged (ticket 0354).
        """
        sh = _read(BUILD_SCRIPT)
        emit = sh.index("export_datapackage.py")
        validate = sh.index("frictionless validate")
        tar = sh.index("tar czf")
        assert emit < validate < tar, (
            "emit -> validate -> package, so an invalid deposit cannot be shipped"
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
    """Ticket 0327, gap 5: the corpus grew from six sources to eight and the
    deposit title, the related-dataset entry, the suggested citation and §3
    kept the v1.0 wording.

    Writing "eight" was the wrong repair. A count in the title goes stale at
    every harvest, which is how "six" survived into v2 in the first place, so
    the count left the title entirely (author, 2026-07-27): both the paper and
    the deposit are now titled "A Curated Multi-Source Corpus…". The number
    lives in the prose, where `{{< meta corpus_sources >}}` keeps it current.
    This guard therefore rejects *any* spelled-out cardinality, not just the
    stale one.

    Scope is deliberately the data paper and the deposit metadata only. The
    Œconomia manuscript and the Gide slides say "six sources" *correctly* —
    manuscript-vars.yml is pinned to the v1.0 corpus, which had six.
    """

    COUNTED = (
        "six sources",
        "Six Sources",
        "six per-source",
        "Six sources",
        "eight sources",
        "Eight Sources",
        "eight per-source",
        "Eight sources",
    )

    @pytest.mark.parametrize("path", [QMD, README])
    def test_source_cardinality_is_not_spelled_out(self, path):
        text = _read(path)
        for phrase in self.COUNTED:
            assert phrase not in text, (
                f"{os.path.basename(path)} spells out a source count "
                f"({phrase!r}). The title carries no number; the prose gets it "
                "from {{< meta corpus_sources >}} (ticket 0327)"
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


class TestSubmissionProseNamesOnlyShippedProducts:
    """A submission document must not promise a deposit file the build drops.

    Ticket 0403. Retiring `codebook.md` (ticket 0354) left it named in three
    documents that describe the deposit to the editor, including the record
    description pasted into Zenodo. Nothing caught them: `PRODUCTS` guards the
    build side (build script, archive README, data-paper.qmd) while the
    `revision-rdj26561/` correspondence sat outside every check.

    `TestDepositCountsTrackTheCorpus` set the precedent for the deposit's
    hand-pasted *counts*. This is the same argument for its filenames.

    Not the same guard as ticket 0387 (prose naming a script that no longer
    exists). That one must separate a real signal from prose that legitimately
    names files yet to be created; here the authority is a closed set — what the
    build stages — so the check is exact and needs no heuristics.
    """

    def test_products_list_matches_the_build_script(self):
        """PRODUCTS is an expectation pinned to the authority, not a second one."""
        assert set(PRODUCTS) == shipped_products(), (
            "PRODUCTS and the build script disagree on what the deposit ships; "
            f"only in PRODUCTS: {sorted(set(PRODUCTS) - shipped_products())}, "
            f"only in the build script: {sorted(shipped_products() - set(PRODUCTS))}"
        )

    @pytest.mark.parametrize("path", SUBMISSION_DOCS, ids=os.path.basename)
    def test_document_names_only_shipped_products(self, path):
        named = products_named_in(_read(path))
        assert named, (
            f"{os.path.basename(path)} names no deposit product at all. Either it "
            "stopped describing the deposit, or its `data/products/` enumeration "
            "moved out of the paragraph this parses — the guard has gone blind, "
            "which is the failure mode a subset check cannot report on its own."
        )
        unshipped = sorted(named - shipped_products() - set(PROSE_PRODUCT_ALLOWLIST))
        assert not unshipped, (
            f"{os.path.basename(path)} presents {unshipped} as deposit contents, "
            "but the build script does not stage them into data/products/. "
            "Either the file was retired (fix the prose) or the build lost it."
        )

    def test_prose_allowlist_entries_are_earned(self):
        for name, reason in PROSE_PRODUCT_ALLOWLIST.items():
            assert reason.strip(), f"{name} is allowlisted without a reason"
            assert name not in shipped_products(), (
                f"{name} is shipped by the build, so its allowlist entry is "
                "redundant — drop it")

    def test_a_retired_product_is_caught(self):
        """Red-proof, kept: the codebook.md case, on a synthetic document.

        Pinned against a synthetic text rather than by mutating the real files,
        so the check that the guard *can* fail travels with the guard.
        """
        doc = (
            "**ED-04 (Zenodo package structure).** The deposit contains\n"
            "`data/inputs/` with the catalogs, and `data/products/` with the\n"
            "paper's outputs (`climate_finance_corpus.csv`, `codebook.md`,\n"
            "`embeddings.npz`); `code/` holds the pipeline source.\n"
        )
        named = products_named_in(doc)
        assert "climate_finance_corpus.csv" in named, "the real products must parse"
        assert sorted(named - shipped_products()) == ["codebook.md"]

    def test_a_split_extension_shorthand_is_expanded(self):
        """Red-proof for the `` `stem.csv`/`.md` `` shorthand (ed04 writes
        `tab_retrieval_protocol.csv`/`.md`): the bare-extension token expands
        against the preceding stem, and the function returns the set — the
        2026-07-27 patch that added this branch dropped the return statement,
        which blinded the whole guard (three docs reported as naming nothing)
        and broke its own self-test with a TypeError."""
        doc = (
            "The `data/products/` folder ships\n"
            "`tab_retrieval_protocol.csv`/`.md` for the appendix.\n"
        )
        named = products_named_in(doc)
        assert named == {"tab_retrieval_protocol.csv", "tab_retrieval_protocol.md"}
