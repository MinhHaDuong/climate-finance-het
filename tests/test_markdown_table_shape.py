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
from _mk_discovery import REPO_ROOT, generated_markdown_targets

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


def pipe_tables(text: str) -> list[tuple[int, list[str], list[tuple[int, list[str]]]]]:
    """Every pipe table in `text` as ``(header line, header cells, rows)``.

    A table is a pipe row immediately followed by a delimiter row, which is the
    rule GFM itself applies. Fenced blocks are skipped: ``tab_variables.md``
    ships a raw-LaTeX ``longtable`` inside a ``` fence, and its column
    specifications are not Markdown.

    ``rows`` carries the delimiter row first, then the body rows. The delimiter
    is included deliberately — GFM requires it to declare the same column count
    as the header, so a mismatch there is the same defect one line higher.
    """
    lines = text.splitlines()
    tables = []
    fenced = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fenced = not fenced
            i += 1
            continue
        if fenced or "|" not in stripped:
            i += 1
            continue
        if i + 1 >= len(lines) or not _is_separator(split_row(lines[i + 1])):
            i += 1
            continue
        header = split_row(stripped)
        rows = [(i + 2, split_row(lines[i + 1]))]
        j = i + 2
        while j < len(lines) and lines[j].strip() and "|" in lines[j]:
            if lines[j].strip().startswith(("```", "~~~")):
                break
            rows.append((j + 1, split_row(lines[j])))
            j += 1
        tables.append((i + 1, header, rows))
        i = j
    return tables


def malformed_rows(text: str) -> list[str]:
    """Rows whose cell count differs from their table's header. Empty is clean."""
    return [
        f"line {lineno}: {len(cells)} cells, header at line {header_line} "
        f"declares {len(header)} — {'|'.join(cells)[:120]}"
        for header_line, header, rows in pipe_tables(text)
        for lineno, cells in rows
        if len(cells) != len(header)
    ]


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
    present = [a for a in sorted(GENERATED) if (REPO_ROOT / a).is_file()]
    assert len(present) >= 3, (
        "fewer than three generated Markdown artifacts on disk; the git-tracked "
        f"ones should always be present: {present}"
    )
    parsed = [
        (a, len(rows))
        for a in present
        for _, _, rows in pipe_tables((REPO_ROOT / a).read_text(encoding="utf-8"))
    ]
    assert sum(n for _, n in parsed) >= 30, (
        f"the sweep parsed only {sum(n for _, n in parsed)} table rows across "
        f"{len(present)} artifacts — the table detector is not seeing them: {parsed}"
    )
