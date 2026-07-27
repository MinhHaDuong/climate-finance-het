"""Shared oracle for the pipe-table fidelity tests: render, then read back.

A Markdown renderer does not error on a cell that overflows its row — it drops
it. So the only assertion that sees the defect is one made on the *rendered*
page, and both fidelity suites (tickets 0325 and 0339) reach for the same three
steps: run the source through the reader Quarto uses, find the row, read its
cells back as text. Those steps live here rather than in each suite, so the two
agree on what "the rendered row" means.

**Why the reader is `markdown` and not `gfm` (ticket 0376).** This oracle read
`-f gfm` until it was measured against a real build. Quarto's `from:` is not a
reader name but a custom Lua reader,
``/opt/quarto/share/filters/qmd-reader.lua``, which delegates to
``readqmd.lua``; that module sets ``Extensions = pandoc.format.extensions
'markdown'`` and calls ``pandoc.read`` with ``{format = "markdown", extensions =
…}``. No ``reader-extensions:`` key appears in the ``--defaults`` YAML Quarto
hands its bundled pandoc, so the extension set is pandoc's own default for
`markdown` — the full extended reader. `markdown` carries ``+citations
+subscript +superscript``; `gfm` carries none of them, so a `gfm` oracle renders
``@key``, ``~x~`` and ``^x^`` literally and cannot see a defect the manuscript
would ship.

Pandoc's own `-f markdown` is used rather than the Lua reader itself: that
reader is the same extension set plus Quarto's shortcode and fenced-div
preprocessing, neither of which touches cell escaping, and invoking it would
hard-code a Quarto install path into the test suite.

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


def render_qmd(markdown: str, tmp_path, bibliography: str | None = None) -> str:
    """Render `markdown` through the reader Quarto uses; return flattened HTML.

    Flattened because pandoc wraps its output, so a row spans several lines and
    is not findable until the whitespace is collapsed. The source goes through a
    file rather than stdin to keep the encoding explicit.

    Pass `bibliography` to run citeproc, as every ``bibliography:``-carrying
    deliverable does. Without it a live ``@key`` still renders as a citation
    span; with it, a key that resolves renders as a formatted reference — the
    shape a reader of the published table would actually see.
    """
    source = tmp_path / "qmd_probe.md"
    source.write_text(markdown, encoding="utf-8")
    command = ["pandoc", "-f", "markdown", "-t", "html", str(source)]
    if bibliography is not None:
        command += ["--citeproc", f"--bibliography={bibliography}"]
    html = subprocess.run(
        command, capture_output=True, text=True, check=True).stdout
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

    Asserting on the whole tuple beats asserting on `row.count("<td")`: the
    reader truncates an overflowing row to the header's declared column count,
    so the count is right either way and cannot tell a split row from a whole
    one. What the split actually does is shift every later value one column left
    and drop the last — visible only by reading the values back.
    """
    return [_TAG.sub("", cell).strip() for cell in _CELL.findall(row)]
