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

"Every" is load-bearing, and was once only nearly true: until ticket 0352 the
SCRIPTS array was captured with a non-greedy `SCRIPTS=\\((.*?)\\)`, which ended
at the first `)` in the block — a parenthesis in an ordinary comment truncated
the list and the guard stayed green over the prefix it had read. The array is
now delimited by a line-anchored `)`, and the parser asserts one path per entry
line so a regression cannot quietly shrink it again.
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
#
# Both boundaries are load-bearing, and are the same defect class as ticket 0352
# moved from the block level to the token level. Without the lookbehind,
# `../scripts/utils.py` and `old_scripts/utils.py` both yield `scripts/utils.py`,
# so a wrong path would resolve against the real file and the guard would pass on
# a `cp` that cannot work. Without the lookahead, `scripts/utils.pyc` does the
# same. Either way the guard checks something other than what the array says.
SCRIPT_PATH_RE = re.compile(r"(?<![\w/.-])scripts/(?:[\w-]+/)*[\w.-]+\.py(?![\w.])")


def _read(path):
    with open(path) as f:
        return f.read()


def _strip_inline_comment(line):
    """The line's content before any `#` comment, whitespace-trimmed.

    Shared by every parser here: a path named inside a comment is documentation,
    not an entry, and reading it as one lets a commented-out path stand in for a
    genuinely absent file.
    """
    return line.split("#", 1)[0].strip()


# The array is shell source with one entry per line and its terminator alone on
# a line, so the block is delimited by a line-anchored `)` rather than by
# counting brackets. Simpler than bracket nesting and sufficient for this shape;
# an unanchored `SCRIPTS=\((.*?)\)` ends the block at the first `)` *anywhere* —
# a paren inside a comment truncated the list silently (ticket 0352).
SCRIPTS_ARRAY_RE = re.compile(
    r"^SCRIPTS=\([ \t]*$(?P<body>.*?)^\)[ \t]*$", re.DOTALL | re.MULTILINE
)

# Any declaration that contributes entries to SCRIPTS, including the append form
# `SCRIPTS+=(`. Counting with SCRIPTS_ARRAY_RE alone would miss an appended
# second array entirely — the parser reads the first block, the append is never
# seen, and the "exactly one array" check it should have tripped never fires.
SCRIPTS_DECL_RE = re.compile(r"^SCRIPTS[ \t]*\+?=[ \t]*\(", re.MULTILINE)


def _parse_scripts_array(content):
    """Repo-relative scripts/ paths inside a shell SCRIPTS=( ... ) array.

    Takes the build script's *content* rather than reading it, so the parser can
    be exercised against fixtures independently of the real array.

    Every non-comment line of the block must carry exactly one scripts/*.py
    path. That per-line invariant is what stops a future parser regression from
    silently shrinking the list: a truncated parse drops entry lines and paths
    together, but any mismatch between them fails loudly here.
    """
    blocks = SCRIPTS_ARRAY_RE.findall(content)
    assert blocks, (
        "build_analysis_archive.sh must declare a SCRIPTS=( ... ) array of the "
        "scripts it copies into the archive, opened by a line `SCRIPTS=(` and "
        "closed by a line holding only `)`"
    )
    # Otherwise entries outside the first block are parsed by neither this nor
    # the line scan, which both take the first match — a silent blind spot of
    # the 0352 kind. Counted over declarations, not blocks, so `SCRIPTS+=(`
    # trips it too.
    decls = SCRIPTS_DECL_RE.findall(content)
    assert len(decls) == 1, (
        "expected exactly one SCRIPTS array declaration, found "
        f"{len(decls)} — entries outside the first are silently unchecked"
    )
    paths = []
    for line in blocks[0].splitlines():
        entry = _strip_inline_comment(line)
        if not entry:
            continue
        found = SCRIPT_PATH_RE.findall(entry)
        assert len(found) == 1, (
            "every entry line of the SCRIPTS array must name exactly one "
            f"scripts/*.py path, got {found} from: {line.strip()!r}"
        )
        paths.append(found[0])
    assert paths, "SCRIPTS=( ... ) array holds no scripts/*.py paths"
    return paths


def _archive_script_paths():
    """Repo-relative scripts/ paths the build script copies into the archive."""
    return _parse_scripts_array(_read(BUILD_SCRIPT))


def _entry_lines_by_line_scan(content):
    """Entry lines of the SCRIPTS array, counted without the parser's regex.

    Deliberately a second, independent implementation: a ratchet that measured
    the array with the very regex under test would shrink along with it and
    report nothing.

    Lines are right-stripped so the two implementations agree on what delimits
    the block — SCRIPTS_ARRAY_RE tolerates trailing whitespace on `SCRIPTS=(`
    and `)`, and a scan that did not would raise ValueError on a file the parser
    reads fine. Loud rather than silent, but a false alarm all the same.
    """
    lines = [ln.rstrip() for ln in content.splitlines()]
    start = lines.index("SCRIPTS=(")
    end = start + 1 + lines[start + 1:].index(")")
    return [ln for ln in lines[start + 1:end] if _strip_inline_comment(ln)]


def _makefile_script_paths():
    """scripts/*.py paths the archived Makefile invokes as recipe prerequisites.

    Comments are stripped first: a `# … scripts/x.py …` example must not be read
    as a real prerequisite. Inline comments count — stripping only whole-line
    ones left `foo: bar  # see scripts/x.py` readable as a prerequisite, the same
    "documentation parsed as data" class ticket 0352 closed for the array.
    """
    lines = [_strip_inline_comment(ln) for ln in _read(MAKEFILE_ANALYSIS).splitlines()]
    paths = SCRIPT_PATH_RE.findall("\n".join(lines))
    assert paths, "Makefile.analysis-manuscript references no scripts/*.py paths"
    return paths


# A SCRIPTS array shaped like the real one, except that its last entry sits
# below a comment containing a parenthesis and names a file that does not exist.
# A parser that stops at the first `)` never sees that entry, so the existence
# guard passes on a list it only read the prefix of (ticket 0352).
FIXTURE_PAREN_COMMENT = """\
SCRIPTS=(
    scripts/utils.py
    # Shared helpers the two venue emitters import (added by ticket 0339).
    scripts/no_such_helper_below_a_paren_comment.py
)
"""

# A comment naming a path is documentation, not an entry: it must not be
# copied into the archive, and must not stand in for a truly-listed path.
FIXTURE_PATH_IN_COMMENT = """\
SCRIPTS=(
    scripts/utils.py
    # Superseded by scripts/no_such_commented_out_helper.py — do not ship.
)
"""


class TestScriptsArrayParser:
    """The parser must read the whole array, whatever punctuation appears in it."""

    def test_reads_entries_below_a_parenthesis_bearing_comment(self):
        """An ordinary comment with a paren in it must not end the array.

        Red before ticket 0352: `SCRIPTS=\\((.*?)\\)` is non-greedy, so the
        capture stopped at the `)` of "(added by ticket 0339)" and every entry
        below it went unread — silently, with the guard still green.
        """
        paths = _parse_scripts_array(FIXTURE_PAREN_COMMENT)
        assert "scripts/no_such_helper_below_a_paren_comment.py" in paths, (
            "the parser stopped early: entries below a comment containing a "
            f"parenthesis were not read (got {paths})"
        )

    def test_existence_guard_catches_a_missing_path_below_such_a_comment(self):
        """The asymmetry that makes the fixture a test: the truncating parser
        passes it because it never sees the bad path, the correct one fails."""
        missing = [
            p for p in _parse_scripts_array(FIXTURE_PAREN_COMMENT)
            if not os.path.isfile(os.path.join(REPO, p))
        ]
        assert missing == ["scripts/no_such_helper_below_a_paren_comment.py"], (
            "a nonexistent script listed below a parenthesis-bearing comment "
            f"must be reported as missing, got {missing}"
        )

    def test_paths_named_only_in_comments_are_not_entries(self):
        """Otherwise a commented-out path could mask a genuinely absent entry."""
        paths = _parse_scripts_array(FIXTURE_PATH_IN_COMMENT)
        assert paths == ["scripts/utils.py"], (
            f"comment text was parsed as an array entry: {paths}"
        )

    def test_real_array_parses_to_its_full_length(self):
        """Every non-comment line of the real array must yield exactly one path.

        Guards against a future parser regression silently shrinking the list:
        a prefix-only parse fails this even when every path it did read exists.
        """
        content = _read(BUILD_SCRIPT)
        paths = _parse_scripts_array(content)
        entry_lines = _entry_lines_by_line_scan(content)
        assert len(paths) == len(entry_lines), (
            f"parsed {len(paths)} paths from {len(entry_lines)} entry lines — "
            "the parser is reading only part of the SCRIPTS array"
        )

    @pytest.mark.parametrize("bad", ["../scripts/utils.py", "old_scripts/utils.py"])
    def test_a_path_is_not_matched_inside_a_longer_path(self, bad):
        """A near-miss entry must not resolve against the real file it contains.

        `../scripts/utils.py` and `old_scripts/utils.py` are paths the archive
        `cp` cannot use, but a boundary-less `scripts/…` pattern reads the real
        `scripts/utils.py` out of both — the guard would then check a file the
        array never named. Same silent-subset class as the truncating parse.
        """
        fixture = f"SCRIPTS=(\n    {bad}\n)\n"
        with pytest.raises(AssertionError):
            _parse_scripts_array(fixture)

    @pytest.mark.parametrize("bad", ["scripts/utils.pyc", "scripts/utils.py.bak"])
    def test_a_py_path_is_not_matched_inside_a_longer_extension(self, bad):
        """Neither `scripts/utils.pyc` nor `scripts/utils.py.bak` is the real file."""
        with pytest.raises(AssertionError):
            _parse_scripts_array(f"SCRIPTS=(\n    {bad}\n)\n")

    def test_a_second_array_declaration_is_rejected(self):
        """Entries outside the first block are read by no parser here.

        The append form is the trap: `SCRIPTS+=(` does not open a block that
        SCRIPTS_ARRAY_RE matches, so counting blocks would report one and the
        appended paths would go unchecked in silence.
        """
        appended = (
            "SCRIPTS=(\n    scripts/utils.py\n)\n"
            "SCRIPTS+=(\n    scripts/no_such_appended_helper.py\n)\n"
        )
        with pytest.raises(AssertionError, match="exactly one SCRIPTS array"):
            _parse_scripts_array(appended)

    def test_trailing_whitespace_on_the_delimiters_is_tolerated_by_both(self):
        """The regex and the line scan must agree on what delimits the block."""
        padded = "SCRIPTS=(  \n    scripts/utils.py\n)  \n"
        assert _parse_scripts_array(padded) == ["scripts/utils.py"]
        assert _entry_lines_by_line_scan(padded) == ["    scripts/utils.py"]

    def test_real_array_includes_the_shared_venue_helpers(self):
        """Both helpers sit below the comment that used to truncate the parse."""
        paths = _archive_script_paths()
        for helper in ("scripts/_venue_naming.py", "scripts/_markdown_table.py"):
            assert helper in paths, (
                f"{helper} is imported by the archived venue emitters but the "
                "guard does not see it in the SCRIPTS array"
            )


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
