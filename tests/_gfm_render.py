"""Shared oracle for the pipe-table fidelity tests: render, then read back.

A Markdown renderer does not error on a cell that overflows its row — it drops
it. So the only assertion that sees the defect is one made on the *rendered*
page, and both fidelity suites (tickets 0325 and 0339) reach for the same three
steps: run the source through pandoc's GFM reader, find the row, read its cells
back as text. Those steps live here rather than in each suite, so the two agree
on what "the rendered row" means.

Support module, not a test module: `tests/_*.py` is this repo's flat helper
surface (`_source_roots.py`, `_script_discovery.py`).
"""

import re
import shutil
import subprocess

import pytest

_ROW = re.compile(r"<tr[^>]*>.*?</tr>")
_CELL = re.compile(r"<td[^>]*>(.*?)</td>")
_TAG = re.compile(r"<[^>]+>")


def require_pandoc() -> None:
    """Skip the calling test where pandoc is absent."""
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc not available on this machine")


def render_gfm(markdown: str, tmp_path) -> str:
    """Render `markdown` through pandoc's GFM reader; return flattened HTML.

    Flattened because pandoc wraps its output, so a row spans several lines and
    is not findable until the whitespace is collapsed. The source goes through a
    file rather than stdin to keep the encoding explicit.
    """
    source = tmp_path / "gfm_probe.md"
    source.write_text(markdown, encoding="utf-8")
    html = subprocess.run(
        ["pandoc", "-f", "gfm", "-t", "html", str(source)],
        capture_output=True, text=True, check=True).stdout
    return re.sub(r"\s+", " ", html)


def row_with(flat: str, needle: str) -> str:
    """The rendered `<tr>` carrying `needle`, as flattened HTML.

    Ambiguity is an error, not a first-match: returning `matching[0]` silently
    lets a decoy row stand in for the one under test, and the caller then
    asserts on cells it never meant to read. The suites that use this helper are
    checking that a *specific* row survived rendering intact, so a needle that
    picks out more than one row is a defect in the test, not something to
    resolve by position.
    """
    matching = [row for row in _ROW.findall(flat) if needle in row]
    assert matching, f"no rendered row carries {needle!r}:\n{flat}"
    assert len(matching) == 1, (
        f"{needle!r} matches {len(matching)} rendered rows — pick a needle that "
        f"identifies one:\n" + "\n".join(matching)
    )
    return matching[0]


def cell_texts(row: str) -> list[str]:
    """The row's cells as plain text.

    Asserting on the whole tuple beats asserting on `row.count("<td")`: GFM
    truncates an overflowing row to the header's declared column count, so the
    count is right either way and cannot tell a split row from a whole one.
    What the split actually does is shift every later value one column left and
    drop the last — visible only by reading the values back.
    """
    return [_TAG.sub("", cell).strip() for cell in _CELL.findall(row)]
