"""Path-resolution guard for the reproducibility archives (tickets 0261, 0292).

The older archive guards (`test_archive_checksums.py::TestArchiveScripts`,
`test_script_hygiene.py::TestArchiveBitInvariance`) only assert that a script's
*basename string* appears in the build script / Makefile. They pass regardless
of which directory the file actually lives in, so the epic-0240 reorg — which
moved figure/analysis entry points into `scripts/{figures,analysis}/` — left
`build_analysis_archive.sh` copying `scripts/compute_clusters.py` from a path
that no longer exists, and no test caught it (the repo has no CI).

These guards have teeth: they resolve every script path the archive tooling will
actually `cp`/invoke to a real file on disk. Point any listed path at a moved or
missing file and the guard fails — so the next mover cannot silently strand the
archive.

Ticket 0292 widened the coverage from the analysis script's `SCRIPTS` array to
every input all three archive scripts copy. The 0226 reorg had broken the
manuscript and data paper scripts the same way — they assembled a `content/`
tree and copied a root `_quarto.yml` that no longer exists — and only the
analysis script was guarded, which is why the breakage went unseen.

Two kinds of input need different proof of life:

- **Tracked assets** (the manuscript source, the bibliography) exist on disk in
  any checkout, so existence is the check.
- **Generated artifacts** (`fig_bars.png`, `tab_languages.md`) are gitignored
  regenerables, absent from a fresh checkout and rebuilt by `make`. Requiring
  them on disk would make this guard fail for anyone who has not run the full
  pipeline, so the check is that a Make rule still names them.

Ticket 0384 scoped the second half per archive. Matching against every Makefile
in the repo at once resolves any archive's artifact for any archive, so the
manuscript array could name the data paper's `fig_bars.png` — four characters
from its own `fig_bars_v1.png` — and stay green. Existence on disk cannot
separate them either: on a machine that has run the pipeline, both are there.
What does separate them is ownership. `paths.mk` declares one figure list and
one include list per document, and `tests/test_deliverable_artifacts.py` keeps
both honest against each `.qmd`'s real include closure, so a document archive
may ship only the shared artifacts of the document it packages.

So the invariant has two halves:

- a **shared render artifact** (under `deliverables/_shared/figures`, `tables`
  or `_includes`) declared by a document archive must appear in that document's
  own `paths.mk` artifact set;
- every **other** declared input must exist on disk or be named by a Make rule.

Ownership applies to the declared input array, which is the document's render
manifest. The literal `cp` payload outside it — data products, the reviewer
Makefile, the reference PDF — is not part of any document's include closure, so
it gets the second half only.
"""

import functools
import os
import re

import pytest
from _mk_discovery import all_makefiles, makefile_constants

pytestmark = pytest.mark.adherence

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD_DIR = os.path.join(REPO, "build")
MAKEFILE_ANALYSIS = os.path.join(
    REPO, "build", "templates", "Makefile.analysis-manuscript"
)

BUILD_SCRIPTS = {
    "analysis": os.path.join(BUILD_DIR, "build_analysis_archive.sh"),
    "manuscript": os.path.join(BUILD_DIR, "build_manuscript_archive.sh"),
    "datapaper": os.path.join(BUILD_DIR, "build_datapaper_archive.sh"),
}

# Each archive script declares its inputs in one named bash array, so the array
# is both the manifest and the archive layout. Keeping the name here means a
# renamed array fails loudly rather than silently guarding nothing.
INPUT_ARRAYS = {
    "analysis": "SCRIPTS",
    "manuscript": "MANUSCRIPT_FILES",
    "datapaper": "DATAPAPER_FILES",
}

# The `paths.mk` artifact sets that own each document archive's shared render
# inputs. Naming the variables here rather than deriving them means a renamed
# list fails loudly — `_owned_artifacts` asserts each one still exists — instead
# of quietly shrinking the ownership set to nothing.
#
# The analysis archive maps to no document: it ships the pipeline itself, and
# its guarded array holds only `scripts/` entry points, so no include closure
# describes it. `None` marks that absence, distinct from an empty set.
ARCHIVE_ARTIFACT_VARS = {
    "manuscript": ("MANUSCRIPT_FIGS", "MANUSCRIPT_INCLUDES"),
    "datapaper": ("DATAPAPER_FIGS", "DATAPAPER_INCLUDES"),
    "analysis": None,
}

# Where Phase 2 writes the artifacts a document renders. A declared input under
# one of these is owned by exactly one deliverable; anything else in
# `deliverables/_shared/` (the bibliography, the CSL) is a tracked asset no
# `paths.mk` list describes, so it stays on the existence check.
SHARED_ARTIFACT_DIRS = (
    "deliverables/_shared/figures/",
    "deliverables/_shared/tables/",
    "deliverables/_shared/_includes/",
)

# `$PROJ_ROOT/` and `${PROJ_ROOT}/` — the one shell variable in these scripts
# that is statically resolvable, since every build script defines it as the repo
# root. Stripping it before the run-time-token filter is what brings the two
# tracked retrieval-protocol tables the data paper deposits under the guard.
PROJ_ROOT_PREFIX_RE = re.compile(r"^\$\{?PROJ_ROOT\}?/")

# scripts/<optional-subdirs>/<name>.py — matches both flat (scripts/utils.py)
# and reorg'd (scripts/figures/plot_fig1_bars.py) entry points.
SCRIPT_PATH_RE = re.compile(r"scripts/(?:[\w-]+/)*[\w.-]+\.py")

# A repo-relative path as written in a bash array or a literal `cp` source.
# Anything with a shell variable or a glob resolves at run time and cannot be
# checked statically, so those simply do not match. The token runs to the end of
# the path: requiring a trailing `\.\w+` extension instead would truncate
# `build/templates/Makefile.analysis-manuscript` at `.analysis`, since `\w`
# excludes the hyphen — a false positive, not a finding.
REPO_PATH_RE = re.compile(r"(?:deliverables|scripts|config|build|libs)/[\w./-]+")


def _read(path):
    with open(path) as f:
        return f.read()


@functools.lru_cache(maxsize=1)
def _makefile_text():
    """Concatenated text of every Makefile that could declare an archive input.

    Enumerated through the shared helper (ticket 0248) so this guard cannot
    silently narrow its coverage when a fragment moves. Cached: the union is
    ~107 KB and every parametrized case re-reads it otherwise.
    """
    return "\n".join(p.read_text() for p in all_makefiles())


def _owned_artifacts(archive):
    """The shared render artifacts this archive's document owns, or None.

    None means no document owns the archive — the analysis one — in which case
    the ownership half of the invariant does not apply.
    """
    names = ARCHIVE_ARTIFACT_VARS[archive]
    if names is None:
        return None
    constants = makefile_constants()
    owned = set()
    for name in names:
        assert name in constants, (
            f"paths.mk no longer defines {name}; the {archive} archive's "
            "ownership scope would silently shrink to nothing"
        )
        owned.update(constants[name].split())
    return owned


def _declared_inputs(archive):
    """Repo-relative paths inside the build script's declared input array."""
    content = _read(BUILD_SCRIPTS[archive])
    array = INPUT_ARRAYS[archive]
    # Non-greedy up to the first ")" — the arrays are documented to hold no
    # parentheses precisely so this stays correct.
    m = re.search(rf"{array}=\((.*?)\)", content, re.DOTALL)
    assert m, (
        f"{os.path.basename(BUILD_SCRIPTS[archive])} must declare a "
        f"{array}=( ... ) array of the inputs it copies into the archive"
    )
    body = "\n".join(
        ln for ln in m.group(1).splitlines() if not ln.lstrip().startswith("#")
    )
    paths = REPO_PATH_RE.findall(body)
    assert paths, f"{array}=( ... ) array holds no repo-relative paths"
    return paths


def _literal_cp_sources(archive):
    """Repo-relative literal `cp` sources outside the declared array.

    The arguments are tokenised rather than pattern-matched. A path regex has to
    anchor on something, and anchoring on a leading directory misses exactly the
    defect this ticket exists for: the retired root `_quarto.yml` is a bare
    filename at the repo root, so a prefix-anchored pattern never sees it and the
    guard stays green on the original bug.

    Tokens carrying a shell variable or a glob resolve at run time against roots
    this test cannot know, so they are skipped — which also drops every
    destination, since all of them are written under "$TMP".

    `$PROJ_ROOT/` is the exception (ticket 0384): every build script defines it
    as the repo root, so the remainder is an ordinary repo-relative path. It is
    stripped before the run-time filter, which is what brings the two tracked
    retrieval-protocol tables under the guard. Destinations stay skipped —
    `$TMP` survives the strip and still carries a `$`.
    """
    text = _read(BUILD_SCRIPTS[archive]).replace("\\\n", " ")
    sources = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") or not stripped.startswith("cp "):
            continue
        for token in stripped[len("cp "):].split():
            if any(token.startswith(op) for op in (">", "|", "&", ";", "2>")):
                break  # a redirection or `|| true` — the cp arguments end here
            token = token.strip("\"'")
            if not token or token.startswith("-"):
                continue  # a cp flag, not a path
            token = PROJ_ROOT_PREFIX_RE.sub("", token)
            if "$" in token or "*" in token or "?" in token:
                continue  # resolves at run time
            sources.append(token)
    return sources


def _makefile_script_paths():
    """scripts/*.py paths the archived Makefile invokes as recipe prerequisites.

    Comment lines are stripped first: a `# … scripts/x.py …` example must not be
    read as a real prerequisite.
    """
    lines = [
        ln for ln in _read(MAKEFILE_ANALYSIS).splitlines()
        if not ln.lstrip().startswith("#")
    ]
    paths = SCRIPT_PATH_RE.findall("\n".join(lines))
    assert paths, "Makefile.analysis-manuscript references no scripts/*.py paths"
    return paths


def _named_by_make(path, makefile_text):
    """True when a Makefile names this exact path, not merely contains it.

    A plain substring test is wrong here: `_quarto.yml` occurs inside
    `deliverables/manuscript/_quarto.yml`, so a retired root-level `_quarto.yml`
    would look produced when nothing produces it — silently green on the very
    defect ticket 0292 exists for. The path must sit on its own token boundary.
    """
    pattern = rf"(?<![\w./-]){re.escape(path)}(?![\w./-])"
    return re.search(pattern, makefile_text) is not None


def _unresolvable(paths, owned_by=None):
    """Paths the named archive may not legitimately declare.

    `owned_by` is the archive's shared-artifact ownership set, or None when no
    ownership applies. A path under `SHARED_ARTIFACT_DIRS` is judged by
    membership alone — never by disk existence, which on a machine that has run
    the pipeline resolves every paper's artifacts equally and so cannot tell
    `fig_bars.png` from `fig_bars_v1.png`.

    Everything else: `exists` rather than `isfile`, because the analysis archive
    copies the bundled `libs/openalex-corpus` package directory wholesale.
    """
    makefile_text = _makefile_text()
    missing = set()
    for path in paths:
        if owned_by is not None and path.startswith(SHARED_ARTIFACT_DIRS):
            if path not in owned_by:
                missing.add(path)
            continue
        if (not os.path.exists(os.path.join(REPO, path))
                and not _named_by_make(path, makefile_text)):
            missing.add(path)
    return sorted(missing)


class TestArchiveScriptPathsResolve:
    """Every path the archive tooling names must resolve to a real file."""

    @pytest.mark.parametrize("archive", sorted(BUILD_SCRIPTS))
    def test_declared_inputs_resolve(self, archive):
        """Each path in a build script's input array must exist or be built.

        Red before ticket 0261: the analysis loop copied
        `scripts/compute_clusters.py`, but the file lives at
        `scripts/analysis/compute_clusters.py` post-reorg.
        """
        missing = _unresolvable(
            _declared_inputs(archive), owned_by=_owned_artifacts(archive)
        )
        assert not missing, (
            f"build_{archive}_archive.sh declares inputs that are not this "
            "archive's to ship: a shared render artifact must be listed in the "
            "packaged document's own paths.mk set, and every other input must "
            f"exist on disk or be named by a Make rule. Offenders: {missing}"
        )

    @pytest.mark.parametrize("archive", sorted(BUILD_SCRIPTS))
    def test_literal_cp_sources_resolve(self, archive):
        """Each literal `cp` source outside the array must exist or be built.

        Red before ticket 0292: build_manuscript_archive.sh copied a root
        `_quarto.yml` retired by the 0226 deliverables/ reorg, so the script
        died before writing a tarball.
        """
        missing = _unresolvable(_literal_cp_sources(archive))
        assert not missing, (
            f"build_{archive}_archive.sh copies files that neither exist on disk "
            f"nor are produced by any Make rule: {missing}"
        )

    def test_makefile_script_paths_exist(self):
        """Each scripts/*.py the archived Makefile invokes must exist in the repo,
        so the mirrored archive tree the build script produces can build."""
        missing = [
            p for p in _makefile_script_paths()
            if not os.path.isfile(os.path.join(REPO, p))
        ]
        assert not missing, (
            "Makefile.analysis-manuscript invokes scripts that do not exist at "
            f"the named path: {sorted(missing)}"
        )

    def test_declared_shared_artifacts_belong_to_this_archive(self):
        """The manuscript array may not name another paper's shared artifact.

        Red before ticket 0384: `_named_by_make` matched against every Makefile
        in the repo at once, so any archive could name any archive's artifact
        and still resolve. `fig_bars.png` is the data paper's; the manuscript
        ships `fig_bars_v1.png`, four characters away.
        """
        foreign = "deliverables/_shared/figures/fig_bars.png"
        assert _unresolvable(
            [foreign], owned_by=_owned_artifacts("manuscript")
        ) == [foreign]

    @pytest.mark.parametrize("archive", sorted(BUILD_SCRIPTS))
    def test_scoping_does_not_reject_an_archives_own_artifacts(self, archive):
        """Scoping must stay a filter on foreign artifacts, not a new blocker.

        The companion to the test above: over-tightening the ownership check
        would fail every archive on its own inputs, which is the failure mode a
        red test on the foreign path alone cannot see.
        """
        owned = _owned_artifacts(archive)
        if owned is None:
            pytest.skip(f"the {archive} archive ships no document's render inputs")
        assert owned, f"paths.mk declares an empty artifact set for {archive}"
        assert _unresolvable(sorted(owned), owned_by=owned) == []

    def test_proj_root_prefixed_cp_sources_are_checked(self):
        """`$PROJ_ROOT/`-prefixed `cp` sources resolve statically, so check them.

        Red before ticket 0384: any token holding a `$` was dropped as
        run-time-resolved, which silently exempted the two tracked retrieval
        protocol tables the data paper deposits.
        """
        sources = _literal_cp_sources("datapaper")
        for name in ("tab_retrieval_protocol.csv", "tab_retrieval_protocol.md"):
            assert f"deliverables/_shared/tables/{name}" in sources, (
                f"{name} is a tracked file named by a statically resolvable "
                f"$PROJ_ROOT/ path, but the guard still skips it: {sources}"
            )

    def test_build_and_makefile_agree_on_entry_points(self):
        """Every entry point the archived Makefile invokes must be copied by the
        build script at the same path — otherwise the archive Makefile references
        a script the archive does not ship."""
        copied = set(_declared_inputs("analysis"))
        invoked = set(_makefile_script_paths())
        not_shipped = invoked - copied
        assert not not_shipped, (
            "Makefile.analysis-manuscript invokes scripts the build script does "
            f"not copy into the archive: {sorted(not_shipped)}"
        )
