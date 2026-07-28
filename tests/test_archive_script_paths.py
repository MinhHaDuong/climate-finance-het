"""Path-resolution guard for the reproducibility archives (tickets 0261, 0292, 0352).

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

"Every" is load-bearing, and was once only nearly true: until ticket 0352 each
array was captured with a non-greedy `<ARRAY>=\\((.*?)\\)`, which ended at the
first `)` in the block — a parenthesis in an ordinary comment truncated the list
and the guard stayed green over the prefix it had read. Every array is now
delimited by a line-anchored `)`, and the parser asserts one path per entry line
so a regression cannot quietly shrink it again. The three build scripts used to
carry a "keep the array free of parentheses" warning to work around this; that
warning was a tripwire depending on the next editor reading a comment, which is
the exact failure mode these guards exist to remove, and it is gone.

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
#
# Both boundaries are load-bearing, and are the same defect class as ticket 0352
# moved from the block level to the token level. Without the lookbehind,
# `../scripts/utils.py` and `old_scripts/utils.py` both yield `scripts/utils.py`,
# so a wrong path would resolve against the real file and the guard would pass on
# a `cp` that cannot work. Without the lookahead, `scripts/utils.pyc` does the
# same. Either way the guard checks something other than what the source says.
SCRIPT_PATH_RE = re.compile(r"(?<![\w/.-])scripts/(?:[\w-]+/)*[\w.-]+\.py(?![\w.])")

# A repo-relative path as written in a bash array or a literal `cp` source.
# Anything with a shell variable or a glob resolves at run time and cannot be
# checked statically, so those simply do not match. The token runs to the end of
# the path: requiring a trailing `\.\w+` extension instead would truncate
# `build/templates/Makefile.analysis-manuscript` at `.analysis`, since `\w`
# excludes the hyphen — a false positive, not a finding.
#
# The leading lookbehind is the 0352 token-boundary fix: without it
# `../scripts/utils.py` and `old_scripts/utils.py` each yield the bare
# `scripts/utils.py`, which resolves against the real file, so an entry the
# archive's `cp` cannot use would pass. Trailing greediness gives the other
# boundary for free — `scripts/utils.pyc` yields itself, not `scripts/utils.py`,
# and then fails the existence check as it should.
REPO_PATH_RE = re.compile(
    r"(?<![\w./-])(?:deliverables|scripts|config|build|libs)/[\w./-]+"
)


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


def _array_block_re(array):
    """Regex capturing the body of an `<array>=( ... )` block.

    The arrays are shell source with one entry per line and the terminator alone
    on a line, so the block is delimited by a line-anchored `)` rather than by
    counting brackets. Simpler than bracket nesting and sufficient for this
    shape; an unanchored `<array>=\\((.*?)\\)` ends the block at the first `)`
    *anywhere* — a paren inside a comment truncated the list silently (0352).

    It also fails *loudly* (no match at all) if an array's shape ever changes,
    where a bracket counter would keep quietly returning something.
    """
    return re.compile(
        rf"^{array}=\([ \t]*$(?P<body>.*?)^\)[ \t]*$", re.DOTALL | re.MULTILINE
    )


def _array_decl_re(array):
    """Regex matching any declaration that contributes entries to `array`.

    Includes the append form `<array>+=(`. Counting with the block regex alone
    would miss an appended second array entirely — the parser reads the first
    block, the append is never seen, and the "exactly one array" check it should
    have tripped never fires.
    """
    return re.compile(rf"^{array}[ \t]*\+?=[ \t]*\(", re.MULTILINE)


def _parse_input_array(content, array):
    """Repo-relative paths inside a shell `<array>=( ... )` declaration.

    Takes the build script's *content* rather than reading it, so the parser can
    be exercised against fixtures independently of the real arrays.

    Every non-comment line of the block must carry exactly one repo-relative
    path. That per-line invariant is what stops a future parser regression from
    silently shrinking the list: a truncated parse drops entry lines and paths
    together, but any mismatch between them fails loudly here.
    """
    blocks = _array_block_re(array).findall(content)
    assert blocks, (
        f"the build script must declare a {array}=( ... ) array of the inputs "
        f"it copies into the archive, opened by a line `{array}=(` and closed "
        "by a line holding only `)`"
    )
    # Otherwise entries outside the first block are parsed by neither this nor
    # the line scan, which both take the first match — a silent blind spot of
    # the 0352 kind. Counted over declarations, not blocks, so `<array>+=(`
    # trips it too.
    decls = _array_decl_re(array).findall(content)
    assert len(decls) == 1, (
        f"expected exactly one {array} array declaration, found "
        f"{len(decls)} — entries outside the first are silently unchecked"
    )
    paths = []
    for line in blocks[0].splitlines():
        entry = _strip_inline_comment(line)
        if not entry:
            continue
        found = REPO_PATH_RE.findall(entry)
        assert len(found) == 1, (
            f"every entry line of the {array} array must name exactly one "
            f"repo-relative path, got {found} from: {line.strip()!r}"
        )
        paths.append(found[0])
    assert paths, f"{array}=( ... ) array holds no repo-relative paths"
    return paths


def _entry_lines_by_line_scan(content, array):
    """Entry lines of an `<array>=( ... )` block, counted without the parser's regex.

    Deliberately a second, independent implementation: a ratchet that measured
    an array with the very regex under test would shrink along with it and
    report nothing.

    Lines are right-stripped so the two implementations agree on what delimits
    the block — the block regex tolerates trailing whitespace on `<array>=(` and
    `)`, and a scan that did not would raise ValueError on a file the parser
    reads fine. Loud rather than silent, but a false alarm all the same.
    """
    lines = [ln.rstrip() for ln in content.splitlines()]
    start = lines.index(f"{array}=(")
    end = start + 1 + lines[start + 1:].index(")")
    return [ln for ln in lines[start + 1:end] if _strip_inline_comment(ln)]


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
    return _parse_input_array(_read(BUILD_SCRIPTS[archive]), INPUT_ARRAYS[archive])


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

    Comments are stripped first: a `# … scripts/x.py …` example must not be read
    as a real prerequisite. Inline comments count — stripping only whole-line
    ones left `foo: bar  # see scripts/x.py` readable as a prerequisite, the same
    "documentation parsed as data" class ticket 0352 closed for the arrays.
    """
    lines = [_strip_inline_comment(ln) for ln in _read(MAKEFILE_ANALYSIS).splitlines()]
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


def _unresolvable(paths, *, owned_by=None):
    """Paths the named archive may not legitimately declare.

    `owned_by` is the archive's shared-artifact ownership set, or None when no
    ownership applies. It is keyword-only on purpose: it replaced a positional
    `makefile_text` parameter, and a stale call site passing the Makefile blob
    positionally bound a ~107 KB string to it and stayed green — the ownership
    branch never fired for the `scripts/` paths that call site used, so the
    misbinding was inert until the fixture grew a shared artifact. Keyword-only
    makes that a `TypeError` at the call, which no fixture change can defer.

    A path under `SHARED_ARTIFACT_DIRS` is judged by
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


def _fixture_paren_comment(array):
    """An array shaped like the real ones, whose last entry hides behind a paren.

    The entry sits below a comment containing a parenthesis and names a file that
    does not exist. A parser that stops at the first `)` never sees that entry,
    so the existence guard passes on a list it only read the prefix of (0352).
    """
    return f"""\
{array}=(
    scripts/utils.py
    # Shared helpers the two venue emitters import (added by ticket 0339).
    scripts/no_such_helper_below_a_paren_comment.py
)
"""


def _fixture_path_in_comment(array):
    """A comment naming a path is documentation, not an entry.

    It must not be copied into the archive, and must not stand in for a
    truly-listed path.
    """
    return f"""\
{array}=(
    scripts/utils.py
    # Superseded by scripts/no_such_commented_out_helper.py — do not ship.
)
"""


ALL_ARRAYS = sorted(INPUT_ARRAYS.values())


class TestInputArrayParser:
    """The parser must read the whole array, whatever punctuation appears in it."""

    @pytest.mark.parametrize("array", ALL_ARRAYS)
    def test_reads_entries_below_a_parenthesis_bearing_comment(self, array):
        """An ordinary comment with a paren in it must not end the array.

        Red before ticket 0352: `<array>=\\((.*?)\\)` is non-greedy, so the
        capture stopped at the `)` of "(added by ticket 0339)" and every entry
        below it went unread — silently, with the guard still green. Ticket 0292
        parameterised that same regex over three build scripts, so the fixture
        is parameterised over all three array names too.
        """
        paths = _parse_input_array(_fixture_paren_comment(array), array)
        assert "scripts/no_such_helper_below_a_paren_comment.py" in paths, (
            "the parser stopped early: entries below a comment containing a "
            f"parenthesis were not read (got {paths})"
        )

    @pytest.mark.parametrize("array", ALL_ARRAYS)
    def test_existence_guard_catches_a_missing_path_below_such_a_comment(self, array):
        """The asymmetry that makes the fixture a test: the truncating parser
        passes it because it never sees the bad path, the correct one fails."""
        missing = _unresolvable(
            _parse_input_array(_fixture_paren_comment(array), array)
        )
        assert missing == ["scripts/no_such_helper_below_a_paren_comment.py"], (
            "a nonexistent script listed below a parenthesis-bearing comment "
            f"must be reported as missing, got {missing}"
        )

    @pytest.mark.parametrize("array", ALL_ARRAYS)
    def test_paths_named_only_in_comments_are_not_entries(self, array):
        """Otherwise a commented-out path could mask a genuinely absent entry."""
        paths = _parse_input_array(_fixture_path_in_comment(array), array)
        assert paths == ["scripts/utils.py"], (
            f"comment text was parsed as an array entry: {paths}"
        )

    @pytest.mark.parametrize("archive", sorted(BUILD_SCRIPTS))
    def test_real_array_parses_to_its_full_length(self, archive):
        """Every non-comment line of each real array must yield exactly one path.

        Guards against a future parser regression silently shrinking a list:
        a prefix-only parse fails this even when every path it did read exists.
        """
        content = _read(BUILD_SCRIPTS[archive])
        array = INPUT_ARRAYS[archive]
        paths = _parse_input_array(content, array)
        entry_lines = _entry_lines_by_line_scan(content, array)
        assert len(paths) == len(entry_lines), (
            f"parsed {len(paths)} paths from {len(entry_lines)} entry lines — "
            f"the parser is reading only part of the {array} array"
        )

    @pytest.mark.parametrize("bad", ["../scripts/utils.py", "old_scripts/utils.py"])
    def test_a_path_is_not_matched_inside_a_longer_path(self, bad):
        """A near-miss entry must not resolve against the real file it contains.

        `../scripts/utils.py` and `old_scripts/utils.py` are paths the archive
        `cp` cannot use, but a boundary-less `scripts/…` pattern reads the real
        `scripts/utils.py` out of both — the guard would then check a file the
        array never named. Same silent-subset class as the truncating parse.
        """
        with pytest.raises(AssertionError):
            _parse_input_array(f"SCRIPTS=(\n    {bad}\n)\n", "SCRIPTS")

    @pytest.mark.parametrize("bad", ["scripts/utils.pyc", "scripts/utils.py.bak"])
    def test_an_entry_parses_to_the_whole_token_not_a_prefix(self, bad):
        """Neither `scripts/utils.pyc` nor `scripts/utils.py.bak` is the real file.

        Ticket 0292 widened the token pattern past a fixed extension — it has to
        match `build/templates/Makefile.analysis-manuscript` and the bundled
        `libs/openalex-corpus` directory — so the check is not that these are
        rejected but that they are read *whole*. Truncated to `scripts/utils.py`
        they would resolve against the real file and pass; read whole they fail
        the existence check, which is the correct verdict.
        """
        paths = _parse_input_array(f"SCRIPTS=(\n    {bad}\n)\n", "SCRIPTS")
        assert paths == [bad], f"entry truncated to a shorter real path: {paths}"
        assert _unresolvable(paths) == [bad]

    @pytest.mark.parametrize("array", ALL_ARRAYS)
    def test_a_second_array_declaration_is_rejected(self, array):
        """Entries outside the first block are read by no parser here.

        The append form is the trap: `<array>+=(` does not open a block that the
        block regex matches, so counting blocks would report one and the
        appended paths would go unchecked in silence.
        """
        appended = (
            f"{array}=(\n    scripts/utils.py\n)\n"
            f"{array}+=(\n    scripts/no_such_appended_helper.py\n)\n"
        )
        with pytest.raises(AssertionError, match=f"exactly one {array} array"):
            _parse_input_array(appended, array)

    def test_trailing_whitespace_on_the_delimiters_is_tolerated_by_both(self):
        """The regex and the line scan must agree on what delimits the block."""
        padded = "SCRIPTS=(  \n    scripts/utils.py\n)  \n"
        assert _parse_input_array(padded, "SCRIPTS") == ["scripts/utils.py"]
        assert _entry_lines_by_line_scan(padded, "SCRIPTS") == ["    scripts/utils.py"]

    def test_real_array_includes_the_shared_venue_helpers(self):
        """Both helpers sit below the comment that used to truncate the parse."""
        paths = _declared_inputs("analysis")
        for helper in ("scripts/_venue_naming.py", "scripts/_markdown_table.py"):
            assert helper in paths, (
                f"{helper} is imported by the archived venue emitters but the "
                "guard does not see it in the SCRIPTS array"
            )

    @pytest.mark.parametrize("archive", sorted(BUILD_SCRIPTS))
    def test_no_stale_keep_free_of_parentheses_warning(self, archive):
        """The workaround the fixed parser retires must not creep back.

        Each build script carried a "keep the array free of parentheses" comment
        while the guard truncated at the first `)`. Re-adding one would mean the
        parser had regressed — and, worse, would tell the next editor to work
        around a constraint that no longer exists (ticket 0352).
        """
        text = _read(BUILD_SCRIPTS[archive])
        assert "free of parentheses" not in text, (
            f"build_{archive}_archive.sh still warns editors to keep its input "
            "array free of parentheses; the parser no longer requires that"
        )


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
