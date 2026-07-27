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

So the invariant is: *every declared archive input either exists on disk or is
named by a Make rule.* A renamed or moved asset satisfies neither and fails.
"""

import os
import re

import pytest
from _mk_discovery import all_makefiles

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


def _makefile_text():
    """Concatenated text of every Makefile that could declare an archive input.

    Enumerated through the shared helper (ticket 0248) so this guard cannot
    silently narrow its coverage when a fragment moves.
    """
    return "\n".join(p.read_text() for p in all_makefiles())


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


def _unresolvable(paths, makefile_text):
    """Paths that neither exist on disk nor are named by a Make rule.

    `exists` rather than `isfile`: the analysis archive copies the bundled
    `libs/openalex-corpus` package directory wholesale.
    """
    return sorted({
        p for p in paths
        if not os.path.exists(os.path.join(REPO, p))
        and not _named_by_make(p, makefile_text)
    })


class TestArchiveScriptPathsResolve:
    """Every path the archive tooling names must resolve to a real file."""

    @pytest.mark.parametrize("archive", sorted(BUILD_SCRIPTS))
    def test_declared_inputs_resolve(self, archive):
        """Each path in a build script's input array must exist or be built.

        Red before ticket 0261: the analysis loop copied
        `scripts/compute_clusters.py`, but the file lives at
        `scripts/analysis/compute_clusters.py` post-reorg.
        """
        missing = _unresolvable(_declared_inputs(archive), _makefile_text())
        assert not missing, (
            f"build_{archive}_archive.sh declares inputs that neither exist on "
            f"disk nor are produced by any Make rule (moved or renamed?): {missing}"
        )

    @pytest.mark.parametrize("archive", sorted(BUILD_SCRIPTS))
    def test_literal_cp_sources_resolve(self, archive):
        """Each literal `cp` source outside the array must exist or be built.

        Red before ticket 0292: build_manuscript_archive.sh copied a root
        `_quarto.yml` retired by the 0226 deliverables/ reorg, so the script
        died before writing a tarball.
        """
        missing = _unresolvable(_literal_cp_sources(archive), _makefile_text())
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
