"""Ticket 0340 — standing guard: every generated Markdown row is whole.

Three emitters have now shipped the same defect: a free-text value carrying a
raw ``|`` interpolated into a pipe table, where the renderer does not error —
it drops the overflowing cell and shifts every later value one column left.
Ticket 0325 fixed the deposited codebook, 0339 fixed both venue tables. Each
was caught by a person reading the output, never by a test.

A per-PR review gate cannot catch the fourth, so this guard is deliberately not
written against a list of the three known artifacts. It reads the build itself:
every Make rule target ending in ``.md`` is a generated Markdown artifact, and
each one present on disk has its pipe tables parsed and its rows counted
against the header. A new emitter is covered the moment its Make rule exists,
with no edit here — the auto-discovery lesson from tickets 0222 and 0248.

The hazard of a discovery-driven guard is that it passes by finding nothing, or
by finding only files whose tables are well-formed for reasons unrelated to it
working. Three assertions close that off: discovery is pinned to a floor and to
a named always-tracked artifact, the parser is exercised against a malformed
fixture that must fail, and the tree-wide sweep asserts it actually parsed rows.

Adherence tier: the guard reads files and runs nothing.
"""

import re

import pytest
from _markdown_table import markdown_text_cell
from _mk_discovery import (
    REPO_ROOT,
    generated_markdown_targets,
    makefile_constants,
    rule_targets,
)

# Mechanical contract gate (`make lint` / `pytest -m adherence`).
pytestmark = pytest.mark.adherence

# Discovered once at import: ten rule targets today, five of them built on a
# checkout without corpus data. Absent ones are skipped, not failed.
GENERATED = generated_markdown_targets()

# Present in every checkout — git-tracked, built with no Phase-1 data, and one
# of the three artifacts still emitted as a pipe table through the escaper.
# Pins discovery against a Makefile refactor that silently stops resolving
# table targets. Was codebook.md until ticket 0354 retired it; the escaper's
# shipped subject moved here, and the escaped-pipe payload did not survive the
# move (see test_parser_reads_a_real_shipped_table below).
CANONICAL = "deliverables/_shared/tables/tab_retrieval_protocol.md"

_SEPARATOR_CELL = re.compile(r"^:?-+:?$")


def split_row(line: str) -> list[str]:
    """Cells of a pipe-table row, honouring ``\\|`` escapes.

    A hand scan rather than ``re.split(r"(?<!\\\\)\\|", …)``: the lookbehind
    reads ``\\\\|`` — an escaped backslash followed by a live delimiter — as an
    escaped pipe, because it cannot count the run. CommonMark's rule is that a
    backslash escapes exactly the next character, which is what this loop does,
    so a value ending in a backslash is parsed the way the renderer parses it.

    The leading and trailing empty fields produced by the row's outer pipes are
    dropped. Only an *empty* field is dropped, so a genuinely blank first or
    last cell survives: ``| a | b ||`` keeps its three cells.
    """
    text = line.strip()
    cells: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            buf.append(text[i:i + 2])
            i += 2
        elif text[i] == "|":
            cells.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(text[i])
            i += 1
    cells.append("".join(buf))
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return cells


def unresolved_markdown(target: str) -> bool:
    """True when `target` mentions `.md` but did not flatten to a plain path.

    `expand_vars` resolves a bare `$(NAME)`, so anything built with a Make list
    function survives with its syntax attached. Each form leaves a different
    wreck and all of them are caught by the same test:

        $(foreach m,$(METHODS),… tab_$(m).md …)  ->  '…tab_$(m).md'
        $(addprefix DIR/,a.md b.md)              ->  'DIR/,a.md'  and  'b.md)'
        $(TABLES) where TABLES := a.md b.md      ->  'a.md b.md'

    The second form is why a bare "contains `$`" test is not enough: the `$`
    lands on a *different* whitespace token than the `.md` does.

    The third is the dangerous one, because it looks clean from every angle a
    character test can reach — no Make syntax survives, and the token still ends
    in `.md`. Only its *shape* betrays it: a path is one whitespace-free token,
    so a target that does not survive `str.split` is a list wearing a filename.
    `rule_targets` now expands before it splits and no longer produces this, and
    the check stays because the guarantee belongs here: whatever future resolver
    hands a list to a caller expecting a path fails loudly rather than skipping.
    """
    return ".md" in target and (
        bool(set("$%(),") & set(target))
        or target.split() != [target]
        or not target.endswith(".md"))


def has_delimiter(line: str) -> bool:
    """True when `line` carries an unescaped ``|`` — i.e. it is row-shaped.

    Weaker than ``len(split_row(line)) > 1``, and deliberately so. A value torn
    by a raw newline leaves a remainder holding the row's *closing* pipe and
    nothing else, which splits to one cell: row-shaped to a reader, invisible to
    a two-cell test. This is the predicate the :func:`scan` docstring has always
    described — "any line that carries an unescaped ``|``".
    """
    i = 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            i += 2
        elif line[i] == "|":
            return True
        else:
            i += 1
    return False


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(_SEPARATOR_CELL.match(c.strip()) for c in cells)


def scan(text: str) -> tuple[list[tuple[int, list[str], list[tuple[int, list[str]]]]],
                             list[int], list[int], int | None]:
    """`(tables, orphan row lines, torn row lines, unclosed fence line)`.

    A table is a pipe row immediately followed by a delimiter row, which is the
    rule GFM itself applies. Fenced blocks are skipped: ``tab_variables.md``
    ships a raw-LaTeX ``longtable`` inside a ``` fence, and its column
    specifications are not Markdown.

    Each table's ``rows`` carries the delimiter row first, then the body rows.
    The delimiter is included deliberately — GFM requires it to declare the same
    column count as the header, so a mismatch there is the same defect one line
    higher.

    The other three return values exist because a *silent* end-of-table is the
    way this parser could be blind to exactly the defect it hunts:

    - **Orphans.** A raw newline inside a value ends the table at that line, so
      every row below it belongs to no table and would never be width-checked.
      ``markdown_text_cell`` folds a newline to a space, but a hand-written
      table has no escaper in front of it, so the hole stays reachable.
      Any line outside a fence that carries an unescaped ``|`` and no
      table claimed is reported.
    - **Torn rows.** The orphan rule needs the remainder to still carry a pipe,
      and when the newline lands in the *last* column it does not: the row above
      counts its declared cells and passes, and the tail below holds no
      delimiter at all. So a table body that ends on a non-blank line rather
      than on a blank one, EOF or a fence is reported at that line. This is a
      contract on *generated* output — an emitter writes a blank line after a
      table — and it is deliberately strict about what may abut a table body,
      because a torn Markdown description can begin with anything, ``#``
      included, and a block-start exemption would reopen the hole it closes.
    - **Unclosed fence.** One stray fence swallows the rest of the file, and
      the sweep would read it as clean.

    The orphan rule is a contract on *generated* output, where every pipe is a
    delimiter an emitter wrote. It reads a whole line rather than only a line
    opening with ``|``, since GFM's outer pipes are optional and a row that
    dropped them would otherwise be invisible to both checks at once.

    Hand-authored prose does not satisfy that contract: five ``_includes/*.md``
    carry an ordinary sentence or an HTML comment with a pipe in it. That is
    the evidence ticket 0368's third action needs before extending the sweep
    to them.
    """
    lines = text.splitlines()
    tables: list[tuple[int, list[str], list[tuple[int, list[str]]]]] = []
    claimed: set[int] = set()
    row_shaped: list[int] = []
    torn: list[int] = []
    fence_opened_at: int | None = None
    fence: tuple[str, int] = ("", 0)
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        # CommonMark closes a fence only with its own character *and* a run at
        # least as long as the opener's. Both halves are load-bearing: one
        # shared toggle lets a ``` inside a ~~~ block reopen the document, and
        # a fixed length of three lets a ``` close a ```` one. Either way the
        # parser resumes mid-code-block, which is silent in both directions:
        # a table it never sees, and prose it reports as an orphan.
        if stripped.startswith(("```", "~~~")):
            char = stripped[0]
            run = len(stripped) - len(stripped.lstrip(char))
            if fence_opened_at is None:
                fence_opened_at, fence = i + 1, (char, run)
            elif char == fence[0] and run >= fence[1]:
                fence_opened_at, fence = None, ("", 0)
            i += 1
            continue
        if fence_opened_at is not None:
            i += 1
            continue
        if has_delimiter(stripped):
            row_shaped.append(i + 1)
        if ("|" not in stripped or i + 1 >= len(lines)
                or not _is_separator(split_row(lines[i + 1]))):
            i += 1
            continue
        header = split_row(stripped)
        rows = [(i + 2, split_row(lines[i + 1]))]
        claimed |= {i + 1, i + 2}
        j = i + 2
        while j < len(lines) and lines[j].strip() and "|" in lines[j]:
            if lines[j].strip().startswith(("```", "~~~")):
                break
            rows.append((j + 1, split_row(lines[j])))
            claimed.add(j + 1)
            j += 1
        # The body loop stops on EOF, a blank line, a fence, or a line with no
        # pipe. Only the last of those is anomalous in generated output, and it
        # is the signature of a value torn by a raw newline in the last column.
        if (j < len(lines) and lines[j].strip() and "|" not in lines[j]
                and not lines[j].strip().startswith(("```", "~~~"))):
            torn.append(j + 1)
        tables.append((i + 1, header, rows))
        i = j
    return tables, sorted(set(row_shaped) - claimed), torn, fence_opened_at


def pipe_tables(text: str) -> list[tuple[int, list[str], list[tuple[int, list[str]]]]]:
    """The tables :func:`scan` found. See it for the parsing rule."""
    return scan(text)[0]


def malformed_rows(text: str) -> list[str]:
    """Everything wrong with `text`'s pipe tables. Empty is clean.

    Three defects, not one. A width mismatch is the shipped one; an orphan row
    and an unclosed fence are the two ways this parser could report a clean
    file while never looking at the rows that matter.
    """
    tables, orphans, torn, unclosed = scan(text)
    problems = [
        f"line {lineno}: {len(cells)} cells, header at line {header_line} "
        f"declares {len(header)} — {'|'.join(cells)[:120]}"
        for header_line, header, rows in tables
        for lineno, cells in rows
        if len(cells) != len(header)
    ]
    problems += [
        f"line {lineno}: a table row belonging to no table — the table above it "
        "ended early, most likely on a raw newline inside a value, leaving every "
        "row below unchecked"
        for lineno in orphans
    ]
    problems += [
        f"line {lineno}: text abutting the table above with no delimiter in it "
        "— the last cell of the row above was torn by a raw newline, so the "
        "rest of that value and every row below it went unchecked"
        for lineno in torn
    ]
    if unclosed is not None:
        problems.append(
            f"line {unclosed}: unclosed code fence — the parser sees no table "
            "below it, so the rest of the file would pass unread"
        )
    return problems


# ---------------------------------------------------------------------------
# The guard is not vacuous: the parser fails on a malformed table
# ---------------------------------------------------------------------------

# The shipped defect, verbatim: the codebook's reconstruction recipe before
# ticket 0325 escaped it. The raw pipe splits the Description cell in two, so
# the row declares three cells against a two-cell header.
_UNESCAPED = (
    "| Variable | Description |\n"
    "|:---------|:------------|\n"
    "| `is_flagged` | Recipe: df[~df['is_flagged'] | df['is_protected']] |\n"
)

_ESCAPED = _UNESCAPED.replace("is_flagged'] |", r"is_flagged'] \|")


def test_parser_flags_an_unescaped_pipe():
    """Red case: without this the whole sweep could pass by never failing."""
    offenders = malformed_rows(_UNESCAPED)
    assert offenders, "an unescaped pipe split a cell and the parser missed it"
    assert "3 cells" in offenders[0], offenders


def test_parser_accepts_the_escaped_form():
    """Green case: the fix ticket 0325 shipped must read as a whole row."""
    assert not malformed_rows(_ESCAPED)


def test_parser_flags_a_delimiter_row_of_the_wrong_width():
    """The delimiter is width-checked, not merely used to recognise the table.

    Without this the `rows` docstring's promise is untested: deleting the
    delimiter from the checked rows leaves every other assertion green.
    """
    offenders = malformed_rows(
        "| A | B | C |\n|:--|:--|\n| 1 | 2 | 3 |\n")
    assert offenders and "line 2" in offenders[0], offenders


def test_parser_flags_rows_orphaned_by_a_raw_newline():
    """A newline inside a value ends the table; the break itself must be named.

    A newline can reach a hand-edited table even though every live emitter
    folds them. Both documents below carry the same
    defect, and the short one is why this test asserts twice. It used to append
    the synthetic `| x | y | z |` row and assert only on that, so it passed for
    a reason unrelated to its name: strip the trailing row and the same broken
    input read as clean. A newline landing in the *last* column leaves a
    remainder carrying no delimiter at all — one cell, claimed by no table and
    shaped like no row, so it entered neither the width check nor the orphan
    set. Pinning the break line makes the trailing row optional evidence.
    """
    torn = (
        "| A | B |\n"
        "|:--|:--|\n"
        "| ok | first\n"
        "second\n"
    )
    offenders = malformed_rows(torn)
    assert offenders, "the last column's newline tore the row and nothing fired"
    assert "line 4" in " ".join(offenders), offenders

    below = malformed_rows(torn + "| x | y | z |\n")
    assert "line 4" in " ".join(below), below
    assert "line 5" in " ".join(below), below


def test_a_torn_last_cell_is_caught_across_a_blank_line():
    """A paragraph break in the last cell must be named, not read as clean.

    A paragraph break inside a hand-written description emits a blank line
    mid-table: the row above it still counts its declared cells and passes, the
    table ends on the blank, and the tail of the description lands below as
    prose carrying the row's closing pipe. That remainder is a single cell,
    which is precisely what a width check cannot see. (The emitter that once
    passed newlines through, `markdown_cell`, is deleted; the parser hole it
    exposed stays covered.)
    """
    description = "first para\n\nsecond para"
    doc = (
        "| Variable | Description |\n"
        "|:--|:--|\n"
        f"| `x` | {description} |\n"
    )
    offenders = malformed_rows(doc)
    assert offenders, "a paragraph break inside the last cell read as clean"
    assert "line 5" in " ".join(offenders), offenders


def test_parser_flags_an_unclosed_fence():
    """One stray fence swallows the rest of the file, tables included."""
    offenders = malformed_rows(
        "```\nnot markdown\n\n| A | B |\n|:--|:--|\n| 1 | 2 | 3 |\n")
    assert offenders and "unclosed code fence" in offenders[0], offenders


def test_a_fence_closes_only_on_its_own_marker():
    """A ``` inside a ~~~ block must not reopen the document.

    One shared toggle would end the tilde block early, so a malformed row after
    it reads as clean — and, in the other direction, code inside the block gets
    reported as an orphan.
    """
    document = (
        "~~~\n"
        "```\n"
        "| A | B | C |\n"
        "~~~\n"
        "| A | B |\n"
        "|:--|:--|\n"
        "| 1 | 2 | 3 |\n"
    )
    offenders = malformed_rows(document)
    assert len(offenders) == 1, offenders
    assert "line 7" in offenders[0], offenders


def test_a_shorter_run_does_not_close_a_longer_fence():
    """```` opens a block that ``` cannot close; the table below it is real.

    The balanced form is the dangerous one: the fence closes early, the parser
    resumes inside the block, and it reports nothing at all — no table, no
    orphan, no unclosed fence. A length-blind marker match reads this document
    as clean while its one table is malformed.
    """
    document = (
        "````\n"
        "```\n"
        "````\n"
        "| A | B |\n"
        "|:--|:--|\n"
        "| 1 | 2 | 3 |\n"
    )
    offenders = malformed_rows(document)
    assert len(offenders) == 1, offenders
    assert "line 6" in offenders[0], offenders


def test_a_row_without_outer_pipes_is_not_invisible():
    """GFM's outer pipes are optional, so a row that drops them still counts.

    This is the hole where the parser's two checks miss each other: table
    detection needs only a `|` somewhere, while orphan detection used to need a
    *leading* `|`. A row between those two rules belonged to no table and
    entered no orphan set, so the document read as clean.
    """
    document = (
        "| A | B |\n"
        "|:--|:--|\n"
        "| ok | fine\n"
        "\n"
        "x | y | z\n"
    )
    offenders = malformed_rows(document)
    assert offenders and "line 5" in " ".join(offenders), offenders


@pytest.mark.parametrize("payload", [
    "a | b",                                  # the bare pipe, prose
    r"a \| b",                                # a value already carrying an escape
    "Revista de Economía | Economics Review",  # the bilingual venue name, 0339
    "two\nlines",                             # a quoted CSV field's newline
    "`code | span`",                          # a pipe inside a code span
])
def test_escaped_free_text_keeps_the_row_whole(payload):
    """Ties the guard to the escaper: whatever `markdown_text_cell` emits passes.

    Without this the guard and the fix could drift — the parser could grow a
    rule the emitter does not honour, and the tree would still be green because
    no shipped value exercises it.
    """
    doc = f"| Key | Value |\n|:--|:--|\n| probe | {markdown_text_cell(payload)} |\n"
    assert not malformed_rows(doc), payload


def test_parser_reads_a_real_shipped_table():
    """Real-world positive: the parser reads a deposited table's true shape.

    The counterpart to the fixture above — a parser that simply never reports a
    mismatch would pass the tree sweep too. This one asserts the cell count it
    reads on a shipped file, so an over-eager escape rule fails here.

    Narrower than it was. Until ticket 0354 this read codebook.md's `is_flagged`
    row, which carried a genuine ``\\|`` from the filter recipe and so pinned the
    escape path against a *deposited* artifact. That row now lives in a LaTeX
    longtable (tab_variables.md) and in datapackage.json, neither a pipe table,
    and no shipped Markdown table carries an escaped pipe any more. The escape
    itself stays covered by the fixture tests on ``markdown_text_cell`` output; what
    is lost is the real-file half of that pair.
    """
    path = REPO_ROOT / CANONICAL
    if not path.is_file():
        pytest.skip(f"{CANONICAL} not built on this machine")
    tables = pipe_tables(path.read_text(encoding="utf-8"))
    assert tables, f"no pipe table found in {CANONICAL}"
    for _, header, rows in tables:
        for _, cells in rows:
            assert len(cells) == len(header), (CANONICAL, header, cells)


# ---------------------------------------------------------------------------
# The sweep over every generated Markdown artifact the build declares
# ---------------------------------------------------------------------------


def test_discovery_reads_the_build_not_a_list():
    """Discovery is alive: a Makefile refactor that breaks it fails loudly.

    Without a floor, a resolver that stops expanding `$(VAR)` targets — or a
    relocation of the tables out of the rules this parses — would silently
    reduce the sweep below to zero parametrized cases and stay green.
    """
    assert len(GENERATED) >= 5, (
        "Makefile discovery found only "
        f"{len(GENERATED)} generated Markdown targets: {sorted(GENERATED)}. "
        "Either the tables moved out of the build or the rule/variable parsing "
        "in tests/_mk_discovery.py stopped resolving them."
    )
    assert CANONICAL in GENERATED, (
        f"{CANONICAL} is git-tracked and built by a Make rule, so discovery "
        f"must find it; it found {sorted(GENERATED)}"
    )


def test_no_markdown_target_escapes_as_an_unresolved_path():
    """A `.md` target the resolver cannot flatten must fail, never skip.

    This is the sweep's sharpest edge, because the failure is invisible. Make's
    list functions are how this repo adds a per-method artifact — `$(foreach m,
    …,$(eval …))` and `$(addprefix …)` appear thirty-odd times in
    `divergence.mk` and `zoo-figures.mk` for `.csv` and `.png`, so a templated
    `.md` is the likely shape of the fourth emitter this guard exists to catch.
    `expand_vars` resolves a bare `$(NAME)` and nothing else, so such a target
    reaches `GENERATED` carrying a literal `$(m)`, then fails `is_file()` and is
    skipped as "not built on this machine" — silently, on every run, forever.

    Rather than teach the resolver Make's function library, refuse the input:
    any target mentioning `.md` that did not flatten to a plain path fails here,
    naming itself. Whoever adds the templated emitter then extends the resolver
    deliberately instead of losing coverage without noticing.
    """
    unresolved = sorted(t for t in rule_targets() if unresolved_markdown(t))
    assert not unresolved, (
        "Make rule target(s) mentioning `.md` did not resolve to a plain path, "
        "so the sweep would skip them as absent rather than check them. Extend "
        "expand_vars() in tests/_mk_discovery.py to flatten them:\n  "
        + "\n  ".join(unresolved)
    )


@pytest.mark.parametrize("target, escapes", [
    ("deliverables/_shared/tables/tab_venues.md", False),   # a resolved target
    ("deliverables/_shared/tables/tab_div_$(m).md", True),  # $(foreach …$(eval …))
    ("deliverables/_shared/tables/,a.md", True),            # $(addprefix …) head
    ("b.md)", True),                                        # $(addprefix …) tail
    ("deliverables/_shared/tables/%.md", True),             # a pattern rule
    ("a.md b.md c.md", True),                               # $(VAR) holding a list
    ("data/derived/tables/tab_div_$(m).csv", False),        # not markdown, not ours
])
def test_unresolved_markdown_predicate(target, escapes):
    """The tree scan above is a forward-looking ratchet: today it finds nothing.

    So the predicate is pinned on synthetic inputs instead — otherwise the one
    assertion whose whole purpose is to fire on a target that does not exist yet
    would be the module's one untested line.
    """
    assert unresolved_markdown(target) is escapes


def test_a_pipe_row_pair_without_a_delimiter_is_not_a_table():
    """Constrains `_is_separator`, which gates the whole detector.

    Left unpinned, `_is_separator` could return True unconditionally and every
    other assertion in this module still passes — a mutation that turns any two
    adjacent pipe lines into a table with an arbitrary header.
    """
    assert not pipe_tables("| a | b |\n| c | d |\n")
    assert pipe_tables("| a | b |\n|:--|--:|\n| c | d |\n")


def test_rule_targets_reads_a_continued_target_list():
    """A `\\`-continued target list must not lose the targets before the colon.

    Make joins the physical lines before parsing, so every token in the list is
    a declared target. A reader that matched physical lines would keep only the
    ones on the line the colon lands on — and the loss is invisible, because an
    undiscovered target reads exactly like an artifact that was never built.
    No `.md` target is written that way today, which is the point: the sweep's
    promise is to cover the *next* emitter, wherever its rule is formatted.
    """
    targets = rule_targets()
    assert "data/derived/tables/tab_alluvial.csv" in targets, (
        "Makefile:380 declares this target before a line continuation; "
        "rule_targets() dropped it"
    )


def test_rule_targets_splits_a_variable_holding_several_paths():
    """`$(VAR):` where VAR holds a list is several targets, not one long name.

    Splitting the target list before expanding it collapses the whole value into
    one space-joined key — `Makefile:328` declares three `-vars.yml` files behind
    `$(COMPUTED_STATS)` and used to yield a single 130-character path. Nothing
    fails: the bogus key ends in `.yml`, so the Markdown sweep never looks at it.
    Written with `.md` it is worse than silent, it is *actively* reassuring —
    the key still ends in `.md`, so the unresolved-target ratchet passes, and
    `is_file()` then fails on a path that cannot exist, skipping every artifact
    behind that variable as "not built on this machine". Make expands first and
    splits after; so must this.
    """
    targets = rule_targets()
    for member in ("deliverables/_shared/technical-report-vars.yml",
                   "deliverables/data-paper/data-paper-vars.yml",
                   "deliverables/multilayer/multilayer-detection-vars.yml"):
        assert member in targets, (
            f"{member} is declared through $(COMPUTED_STATS) at Makefile:328; "
            "rule_targets() split the target list before expanding it, so all "
            "three collapsed into one space-joined key"
        )
    joined = sorted(t for t in targets if t.split() != [t])
    assert not joined, (
        "Make target(s) carrying whitespace — a variable holding several paths "
        "was expanded after the split, so it reads as one impossible path:\n  "
        + "\n  ".join(joined)
    )


def test_makefile_constants_reads_exported_assignments():
    """`export NAME := value` is an assignment, and five of them exist here.

    Missing one is worse than it looks: a target referencing it resolves to a
    literal `$(NAME)/…` path, which is never on disk — so the sweep skips it
    silently instead of checking it.
    """
    constants = makefile_constants()
    assert "SOURCE_DATE_EPOCH" in constants, sorted(constants)[:20]


def test_makefile_constants_appends_on_plus_equals(tmp_path):
    """`+=` appends; first-wins would silently drop half the value.

    The build uses no `+=` today, so this is pinned on a synthetic fragment
    through the `files=` parameter rather than against the tree — which is also
    that parameter's first real caller. Every other operator keeps first-wins,
    the conservative reading when two fragments disagree.
    """
    fragment = tmp_path / "probe.mk"
    fragment.write_text(
        "TABLES := a.md\n"
        "TABLES += b.md\n"
        "PINNED := first\n"
        "PINNED := second\n",
        encoding="utf-8",
    )
    constants = makefile_constants(files=[fragment])
    assert constants["TABLES"] == "a.md b.md"
    assert constants["PINNED"] == "first"


@pytest.mark.parametrize("artifact", sorted(GENERATED))
def test_generated_markdown_rows_match_their_header(artifact):
    """Exit criterion: every row of every generated table has its declared width.

    An emitter that interpolates free text without `markdown_text_cell` fails
    here as soon as one corpus value carries a pipe — including an emitter
    nobody thought to check.
    """
    path = REPO_ROOT / artifact
    if not path.is_file():
        pytest.skip(f"{artifact} not built on this machine (corpus data absent)")
    offenders = malformed_rows(path.read_text(encoding="utf-8"))
    assert not offenders, (
        f"{artifact} (built by {GENERATED[artifact]}) has rows whose cell count "
        "differs from their header — a raw `|` in an interpolated value splits "
        "the cell and the renderer drops the overflow. Route free text through "
        "scripts/_markdown_table.py (markdown_text_cell):\n  "
        + "\n  ".join(offenders)
    )


def test_the_sweep_actually_parsed_rows():
    """Anti-vacuity: the sweep above passes trivially if it parsed nothing.

    Every artifact could be absent (a fresh clone without corpus data still has
    five git-tracked ones), or the table detector could fail to recognise a
    table and report no rows at all. Both read as green above.
    """
    rows_per_artifact = {
        artifact: sum(len(rows) for _, _, rows in pipe_tables(path.read_text(encoding="utf-8")))
        for artifact in sorted(GENERATED)
        for path in [REPO_ROOT / artifact]
        if path.is_file()
    }
    # Counted on artifacts that actually *contain* a pipe table, not merely on
    # artifacts present. `tab_variables.md` ships a raw-LaTeX longtable and
    # parses to zero tables by design; letting it satisfy a headcount would
    # leave one of three units inert and the floor softer than it reads.
    with_tables = {a: n for a, n in rows_per_artifact.items() if n}
    assert len(with_tables) >= 3, (
        "fewer than three generated pipe-table artifacts parsed; "
        "tab_retrieval_protocol.md, tab_venues.md and tab_venues_fr.md are "
        "git-tracked and should always be present and parsed. "
        f"Parsed: {rows_per_artifact}"
    )
    # 98 rows today against a floor of 30. The gap is deliberate and the floor
    # is not a row-count pin: venue and protocol row counts move with the corpus
    # and with the harvest configuration, so a tight floor would fail on a
    # legitimate regeneration. What it must catch is a detector that has gone
    # blind — which shows up as zero or near-zero, not as a 20% drift.
    assert sum(with_tables.values()) >= 30, (
        f"the sweep parsed only {sum(with_tables.values())} table rows — the "
        f"table detector is not seeing them: {rows_per_artifact}"
    )
