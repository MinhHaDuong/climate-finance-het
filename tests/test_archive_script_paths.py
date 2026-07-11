"""Path-resolution guard for the analysis reproducibility archive (ticket 0261).

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
"""

import os
import re

import pytest

pytestmark = pytest.mark.adherence

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD_SCRIPT = os.path.join(REPO, "build", "build_analysis_archive.sh")
MAKEFILE_ANALYSIS = os.path.join(
    REPO, "build", "templates", "Makefile.analysis-manuscript"
)

# scripts/<optional-subdirs>/<name>.py — matches both flat (scripts/utils.py)
# and reorg'd (scripts/figures/plot_fig1_bars.py) entry points.
SCRIPT_PATH_RE = re.compile(r"scripts/(?:[\w-]+/)*[\w.-]+\.py")


def _read(path):
    with open(path) as f:
        return f.read()


def _archive_script_paths():
    """Repo-relative scripts/ paths inside the build script's SCRIPTS=( ... ) array."""
    content = _read(BUILD_SCRIPT)
    m = re.search(r"SCRIPTS=\((.*?)\)", content, re.DOTALL)
    assert m, (
        "build_analysis_archive.sh must declare a SCRIPTS=( ... ) array of the "
        "scripts it copies into the archive"
    )
    paths = SCRIPT_PATH_RE.findall(m.group(1))
    assert paths, "SCRIPTS=( ... ) array holds no scripts/*.py paths"
    return paths


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


class TestArchiveScriptPathsResolve:
    """Every script path the archive tooling names must resolve to a real file."""

    def test_build_script_paths_exist(self):
        """Each path in the build script's cp list must point at an existing file.

        Red before ticket 0261: the loop copied `scripts/compute_clusters.py`,
        but the file lives at `scripts/analysis/compute_clusters.py` post-reorg.
        """
        missing = [
            p for p in _archive_script_paths()
            if not os.path.isfile(os.path.join(REPO, p))
        ]
        assert not missing, (
            "build_analysis_archive.sh lists scripts that do not exist at the "
            f"path it will cp (moved or deleted?): {sorted(missing)}"
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
        copied = set(_archive_script_paths())
        invoked = set(_makefile_script_paths())
        not_shipped = invoked - copied
        assert not not_shipped, (
            "Makefile.analysis-manuscript invokes scripts the build script does "
            f"not copy into the archive: {sorted(not_shipped)}"
        )
