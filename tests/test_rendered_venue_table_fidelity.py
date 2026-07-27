"""Ticket 0339: the venue tables must survive rendering, not just linting.

Both venue emitters build a Markdown pipe table by interpolating a **journal
name** — free text straight from the bibliographic corpus. `refined_works.csv`
really carries the dangerous character: ten `journal` values are bilingual
names joined with a literal `|`. A Markdown renderer does not error on the
overflowing cell, it silently drops it, so the defect is invisible to any
assertion made on the emitted source. Hence the oracle here is the rendered
page: each emitter is run for real on a fixture whose venue carries a pipe, its
output is read back through the reader Quarto uses (ticket 0376), and the row
must still have its declared cells with the venue name whole.

Running the real scripts (rather than re-deriving a row here) is deliberate:
the escaping helper has its own unit coverage, and a test that only called the
helper would pass even if an emitter stopped calling it.
"""

import os
import subprocess
import sys
from html import escape

import pytest
from _qmd_render import cell_texts, render_qmd, require_pandoc, row_with
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


@pytest.mark.integration
def test_manuscript_venue_table_keeps_a_pipe_bearing_venue_whole(tmp_path):
    """`export_tab_venues.py` feeds @tbl-venues in the rendered manuscript.

    Its journal column is raw `refined_works.csv` text with no canonicalisation,
    so an unescaped pipe splits the row and the reader drops the overflow — the table
    then publishes a truncated venue name against the wrong numbers.
    """
    require_pandoc()
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

    row = row_with(render_qmd(markdown, tmp_path), NEEDLE)
    assert cell_texts(row) == [
        "Efficiency", escape(PIPE_VENUE, quote=False), "2", "0", "2",
    ], f"the venue split the row:\n{row}"


@pytest.mark.integration
def test_core_venue_table_keeps_a_pipe_bearing_venue_whole(tmp_path):
    """`export_core_venues_markdown.py` has the same shape one layer down.

    `canonical_venue()` returns the raw journal string when no curation rule
    matches, so an uncurated bilingual name reaches the cell unchanged.
    """
    require_pandoc()
    core = tmp_path / "het_mostcited_50.csv"
    core.write_text(
        "journal\n"
        f'"{PIPE_VENUE}"\n'
        f'"{PIPE_VENUE}"\n',
        encoding="utf-8")
    output = str(tmp_path / "tab_core_venues_top10.md")

    markdown = _run_emitter(
        "export_core_venues_markdown.py", output, ["--core", str(core)])

    row = row_with(render_qmd(markdown, tmp_path), NEEDLE)
    assert cell_texts(row) == [
        escape(PIPE_VENUE, quote=False), "2", "Journal",
    ], f"the venue split the row:\n{row}"
