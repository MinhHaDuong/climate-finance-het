"""Ticket 0339: the venue tables must survive rendering, not just linting.

Both venue emitters build a Markdown pipe table by interpolating a **journal
name** — free text straight from the bibliographic corpus. `refined_works.csv`
really carries the dangerous character: ten `journal` values are bilingual
names joined with a literal `|`. A Markdown renderer does not error on the
overflowing cell, it silently drops it, so the defect is invisible to any
assertion made on the emitted source. Hence the oracle here is the rendered
page: each emitter is run for real on a fixture whose venue carries a pipe, its
output is read back through pandoc's GFM reader, and the row must still have
its declared cells with the venue name whole.

Running the real scripts (rather than re-deriving a row here) is deliberate:
the escaping helper has its own unit coverage, and a test that only called the
helper would pass even if an emitter stopped calling it.
"""

import os
import re
import shutil
import subprocess
import sys
from html import escape

import pytest
from _source_roots import source_root_env

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# A real shape from the corpus: a bilingual title joined with a pipe.
PIPE_VENUE = "International Development Policy | Revue internationale"
# Matched against the rendered row. Deliberately the part of the venue *before*
# the pipe, so a row that lost its overflow is still found and the assertion
# that reports the failure is the cell count, not a missing row.
NEEDLE = "International Development Policy"


def _run_emitter(script: str, output: str, extra: list[str]) -> str:
    """Run a Phase-2 emitter and return the Markdown it wrote."""
    subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "scripts", "figures", script),
         "--output", output, *extra],
        cwd=REPO_ROOT, env=source_root_env(), capture_output=True,
        text=True, check=True)
    with open(output, encoding="utf-8") as handle:
        return handle.read()


def _render_row(markdown: str, needle: str, tmp_path) -> str:
    """Render `markdown` as GFM and return the flattened <tr> holding `needle`."""
    source = tmp_path / "table.md"
    source.write_text(markdown, encoding="utf-8")
    html = subprocess.run(
        ["pandoc", "-f", "gfm", "-t", "html", str(source)],
        capture_output=True, text=True, check=True).stdout
    # pandoc wraps its output, so rows are found in the flattened document.
    flat = re.sub(r"\s+", " ", html)
    rows = re.findall(r"<tr[^>]*>.*?</tr>", flat)
    matching = [r for r in rows if needle in r]
    assert matching, f"no rendered row carries {needle!r}:\n{flat}"
    return matching[0]


def _cell_text(row: str, index: int) -> str:
    cell = re.findall(r"<td[^>]*>(.*?)</td>", row)[index]
    return re.sub(r"<[^>]+>", "", cell).strip()


@pytest.fixture(scope="module")
def pandoc():
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc not available on this machine")


@pytest.mark.integration
def test_manuscript_venue_table_keeps_a_pipe_bearing_venue_whole(pandoc, tmp_path):
    """`export_tab_venues.py` feeds @tbl-venues in the rendered manuscript.

    Its journal column is raw `refined_works.csv` text with no canonicalisation,
    so an unescaped pipe splits the row and GFM drops the overflow — the table
    then publishes a truncated venue name against the wrong numbers.
    """
    works = tmp_path / "refined_works.csv"
    works.write_text(
        "doi,journal,cited_by_count\n"
        f'10.1000/a,"{PIPE_VENUE}",100\n'
        f'10.1000/b,"{PIPE_VENUE}",100\n',
        encoding="utf-8")
    poles = tmp_path / "tab_pole_papers.csv"
    poles.write_text(
        "doi,axis_score,pole_assignment\n"
        "10.1000/a,0.9,efficiency\n"
        "10.1000/b,0.8,efficiency\n",
        encoding="utf-8")
    output = str(tmp_path / "tab_venues.md")

    markdown = _run_emitter(
        "export_tab_venues.py", output,
        ["--refined-works", str(works), "--pole-papers", str(poles),
         "--min-papers", "1"])

    row = _render_row(markdown, NEEDLE, tmp_path)
    assert row.count("<td") == 5, f"the venue split the row:\n{row}"
    assert _cell_text(row, 1) == escape(PIPE_VENUE, quote=False), \
        f"venue name altered in transit:\n{row}"


@pytest.mark.integration
def test_core_venue_table_keeps_a_pipe_bearing_venue_whole(pandoc, tmp_path):
    """`export_core_venues_markdown.py` has the same shape one layer down.

    `canonical_venue()` returns the raw journal string when no curation rule
    matches, so an uncurated bilingual name reaches the cell unchanged.
    """
    core = tmp_path / "het_mostcited_50.csv"
    core.write_text(
        "journal\n"
        f'"{PIPE_VENUE}"\n'
        f'"{PIPE_VENUE}"\n',
        encoding="utf-8")
    output = str(tmp_path / "tab_core_venues_top10.md")

    markdown = _run_emitter(
        "export_core_venues_markdown.py", output, ["--core", str(core)])

    row = _render_row(markdown, NEEDLE, tmp_path)
    assert row.count("<td") == 3, f"the venue split the row:\n{row}"
    assert _cell_text(row, 0) == escape(PIPE_VENUE, quote=False), \
        f"venue name altered in transit:\n{row}"
