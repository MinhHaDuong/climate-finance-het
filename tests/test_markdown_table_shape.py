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
from _markdown_table import markdown_cell, markdown_text_cell
from _mk_discovery import (
    REPO_ROOT,
    generated_markdown_targets,
    makefile_constants,
    rule_targets,
)

# Mechanical contract gate (`make lint` / `pytest -m adherence`).
pytestmark = pytest.mark.adherence

# Discovered once at import: eight rule targets today, four of them built on a
# checkout without corpus data. Absent ones are skipped, not failed.
GENERATED = generated_markdown_targets()

# Present in every checkout — git-tracked, and the artifact whose split cell
# ticket 0325 fixed. Pins discovery against a Makefile refactor that silently
# stops resolving table targets.
CANONICAL = "deliverables/_shared/tables/codebook.md"

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


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(_SEPARATOR_CELL.match(c.strip()) for c in cells)


def scan(text: str) -> tuple[list[tuple[int, list[str], list[tuple[int, list[str]]]]],
                             list[int], int | None]:
    """`(tables, orphan row lines, unclosed fence line)`.

    A table is a pipe row immediately followed by a delimiter row, which is the
    rule GFM itself applies. Fenced blocks are skipped: ``tab_variables.md``
    ships a raw-LaTeX ``longtable`` inside a ``` fence, and its column
    specifications are not Markdown.

    Each table's ``rows`` carries the delimiter row first, then the body rows.
    The delimiter is included deliberately — GFM requires it to declare the same
    column count as the header, so a mismatch there is the same defect one line
    higher.

    The other two return values exist because a *silent* end-of-table is the
    way this parser could be blind to exactly the defect it hunts:

    - **Orphans.** A raw newline inside a value ends the table at that line, so
      every row below it belongs to no table and would never be width-checked.
      ``markdown_text_cell`` folds a newline to a space, but ``markdown_cell``
      — the codebook path — does not, so the hole is reachable from a shipped
      emitter. Any line that opens with ``|`` and no table claimed is reported.
    - **Unclosed fence.** One stray fence swallows the rest of the file, and
      the sweep would read it as clean.
    """
    lines = text.splitlines()
    tables: list[tuple[int, list[str], list[tuple[int, list[str]]]]] = []
    claimed: set[int] = set()
    row_shaped: list[int] = []
    fence_opened_at: int | None = None
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith(("```", "~~~")):
            fence_opened_at = None if fence_opened_at else i + 1
            i += 1
            continue
        if fence_opened_at is not None:
            i += 1
            continue
        if stripped.startswith("|"):
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
        tables.append((i + 1, header, rows))
        i = j
    return tables, sorted(set(row_shaped) - claimed), fence_opened_at


def pipe_tables(text: str) -> list[tuple[int, list[str], list[tuple[int, list[str]]]]]:
    """The tables :func:`scan` found. See it for the parsing rule."""
    return scan(text)[0]


def malformed_rows(text: str) -> list[str]:
    """Everything wrong with `text`'s pipe tables. Empty is clean.

    Three defects, not one. A width mismatch is the shipped one; an orphan row
    and an unclosed fence are the two ways this parser could report a clean
    file while never looking at the rows that matter.
    """
    tables, orphans, unclosed = scan(text)
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
    """A newline inside a value ends the table; the rows below must not vanish.

    `markdown_cell` — the codebook path — does not fold newlines, so this hole
    is reachable from a shipped emitter. The malformed row here is two lines
    past the break: before orphan reporting, this document read as clean.
    """
    document = (
        "| A | B |\n"
        "|:--|:--|\n"
        "| ok | first\n"
        "second\n"
        "| x | y | z |\n"
    )
    offenders = malformed_rows(document)
    assert offenders, "every row below the break went unchecked"
    assert "line 5" in " ".join(offenders), offenders


def test_parser_flags_an_unclosed_fence():
    """One stray fence swallows the rest of the file, tables included."""
    offenders = malformed_rows(
        "```\nnot markdown\n\n| A | B |\n|:--|:--|\n| 1 | 2 | 3 |\n")
    assert offenders and "unclosed code fence" in offenders[0], offenders


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


def test_markdown_cell_output_keeps_the_row_whole():
    """The codebook path: Markdown input whose code span carries a live pipe."""
    recipe = "df[~df['is_flagged'] | df['is_protected']]"
    doc = f"| Variable | Description |\n|:--|:--|\n| x | {markdown_cell(recipe)} |\n"
    assert not malformed_rows(doc)


def test_parser_reads_the_real_escaped_codebook_row():
    """Real-world positive: `is_flagged` legitimately carries a `\\|`.

    The counterpart to the fixture — a parser that simply never reports a
    mismatch would pass the tree sweep too. This one asserts the cell count it
    reads on a shipped file, so an over-eager escape rule fails here.
    """
    path = REPO_ROOT / CANONICAL
    if not path.is_file():
        pytest.skip(f"{CANONICAL} not built on this machine")
    rows = [
        cells
        for _, _, rows in pipe_tables(path.read_text(encoding="utf-8"))
        for _, cells in rows
        if "is_flagged" in "".join(cells)
    ]
    assert rows, "no is_flagged row in the codebook"
    assert all(len(cells) == 5 for cells in rows), rows
    assert any(r"\|" in "".join(cells) for cells in rows), \
        "the is_flagged recipe lost its escaped pipe"


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


def test_makefile_constants_reads_exported_assignments():
    """`export NAME := value` is an assignment, and five of them exist here.

    Missing one is worse than it looks: a target referencing it resolves to a
    literal `$(NAME)/…` path, which is never on disk — so the sweep skips it
    silently instead of checking it.
    """
    constants = makefile_constants()
    assert "SOURCE_DATE_EPOCH" in constants, sorted(constants)[:20]


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
        "scripts/_markdown_table.py (markdown_text_cell / markdown_cell):\n  "
        + "\n  ".join(offenders)
    )


def test_the_sweep_actually_parsed_rows():
    """Anti-vacuity: the sweep above passes trivially if it parsed nothing.

    Every artifact could be absent (a fresh clone without corpus data still has
    four git-tracked ones), or the table detector could fail to recognise a
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
        "fewer than three generated pipe-table artifacts parsed; codebook.md, "
        "tab_venues.md and tab_venues_fr.md are git-tracked and should always "
        f"be present and parsed. Parsed: {rows_per_artifact}"
    )
    assert sum(with_tables.values()) >= 30, (
        f"the sweep parsed only {sum(with_tables.values())} table rows — the "
        f"table detector is not seeing them: {rows_per_artifact}"
    )
