"""Tests for export_language_table.py — ticket #402, 0367.

Verifies that:
- normalise_language handles common edge cases correctly
- the data paper includes the language table
- the script is importable and the normalise function works
- a pipe-bearing language code survives rendering (ticket 0367 sweep)
"""

import os
import subprocess
import sys
from html import escape

import pytest
from _gfm_render import cell_texts, render_gfm, require_pandoc, row_with
from _source_roots import source_root_env

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "figures"))  # 0255: moved figures entry points

ROOT = os.path.join(os.path.dirname(__file__), "..")
REPO_ROOT = os.path.abspath(ROOT)
DATA_PAPER = os.path.join(ROOT, "deliverables", "data-paper", "data-paper.qmd")
SCRIPT = os.path.join(ROOT, "scripts", "figures", "export_language_table.py")


def read(path):
    with open(path) as f:
        return f.read()


# --- Unit tests for normalise_language ---

def test_plain_code_unchanged():
    from export_language_table import normalise_language
    assert normalise_language("en") == "en"


def test_locale_normalised_underscore():
    from export_language_table import normalise_language
    assert normalise_language("en_US") == "en"


def test_locale_normalised_hyphen():
    from export_language_table import normalise_language
    assert normalise_language("zh-CN") == "zh"


def test_none_returns_unknown():
    import pandas as pd
    from export_language_table import normalise_language
    assert normalise_language(pd.NA) == "unknown"
    assert normalise_language(float("nan")) == "unknown"


def test_empty_string_returns_unknown():
    """Empty string has no language — treated as unknown."""
    from export_language_table import normalise_language
    assert normalise_language("") == "unknown"


def test_uppercase_lowercased():
    from export_language_table import normalise_language
    assert normalise_language("FR") == "fr"


def test_iso639_3_code_with_no_two_letter_equivalent_is_unknown():
    """`arz` (Egyptian Arabic) and `sco` (Scots) have no ISO 639-1 code. The
    table files them under Unclassified, so the prose counts must too — while
    each side held its own normaliser they did not, and the non-English layer
    printed 2,063 against the table's 2,061 (PR #1141)."""
    from export_language_table import normalise_language
    assert normalise_language("arz") == "unknown"
    assert normalise_language("sco") == "unknown"


def test_prose_counts_bucket_codes_exactly_as_the_table_does():
    """One normaliser, not two look-alikes.

    The table and `compute_vars` each counted languages with their own copy of
    the logic, and the copies drifted. Pinning the shared symbol identity is
    what keeps a future edit to one from silently moving only one number.
    """
    from export_language_table import normalise_language
    from pipeline_text import normalize_lang_display

    codes = ["en", "EN", "en_US", "zh-CN", "pt", "eng", "arz", "sco", "und", ""]
    assert [normalise_language(c) for c in codes] == [
        normalize_lang_display(c) for c in codes
    ]

    compute_vars = read(
        os.path.join(ROOT, "scripts", "analysis", "compute_vars.py")
    )
    assert "normalize_lang_display" in compute_vars, (
        "compute_vars must bucket languages through the shared normaliser, "
        "not a local re-implementation"
    )


# --- Integration: data paper includes the language table ---

def test_data_paper_includes_language_table():
    text = read(DATA_PAPER)
    assert "tables/tab_languages.md" in text, (
        "data-paper.qmd must include tables/tab_languages.md"
    )


def test_data_paper_references_tbl_languages():
    text = read(DATA_PAPER)
    assert "@tbl-languages" in text, (
        "data-paper.qmd must reference @tbl-languages"
    )


def test_script_exists():
    assert os.path.isfile(SCRIPT), f"Missing script: {SCRIPT}"


# --- Ticket 0367 sweep: the language table has the same interpolation shape ---

# `normalize_lang` returns any two-character value unchanged, so a malformed
# `language` field in the corpus reaches both the Code column raw and the
# Language column upper-cased. Neither is curated in-repo, which is what makes
# this the same defect class as the corpus-sources table.
PIPE_CODE = "a|"
# MIN_COUNT in the emitter: below it a language is folded into the "Other" row
# and never gets a cell of its own.
ENOUGH_ROWS = 250


@pytest.mark.integration
def test_pipe_bearing_language_code_keeps_its_four_cells(tmp_path):
    """A malformed two-letter code must not shift the counts one column left."""
    require_pandoc()
    enriched = tmp_path / "enriched_works.csv"
    enriched.write_text(
        "language\n" + f'"{PIPE_CODE}"\n' * ENOUGH_ROWS, encoding="utf-8")
    output = tmp_path / "tab_languages.md"

    subprocess.run(
        [sys.executable, SCRIPT, "--input", str(enriched), "--output", str(output)],
        cwd=REPO_ROOT, env=source_root_env(), capture_output=True,
        text=True, check=True)

    flat = render_gfm(output.read_text(encoding="utf-8"), tmp_path)
    row = row_with(flat, escape(PIPE_CODE.upper(), quote=False))

    assert cell_texts(row) == [
        escape(PIPE_CODE.upper(), quote=False),
        escape(PIPE_CODE, quote=False),
        f"{ENOUGH_ROWS}",
        "100.0",
    ], f"the language code split the row:\n{row}"


@pytest.mark.integration
def test_total_row_keeps_its_emphasis(tmp_path):
    """`**Total**` is authored markup, not corpus text — escaping must spare it.

    The escaper touches the backslash, the pipe and the backtick; the asterisk
    carries no meaning on its own. Pinning this is what stops a later widening
    of the character set from publishing a literal `\\*\\*Total\\*\\*`.
    """
    require_pandoc()
    enriched = tmp_path / "enriched_works.csv"
    enriched.write_text("language\n" + "en\n" * ENOUGH_ROWS, encoding="utf-8")
    output = tmp_path / "tab_languages.md"

    subprocess.run(
        [sys.executable, SCRIPT, "--input", str(enriched), "--output", str(output)],
        cwd=REPO_ROOT, env=source_root_env(), capture_output=True,
        text=True, check=True)

    flat = render_gfm(output.read_text(encoding="utf-8"), tmp_path)
    row = row_with(flat, "Total")

    assert "<strong>" in row, f"the Total row lost its emphasis:\n{row}"
    assert cell_texts(row) == ["Total", "", f"{ENOUGH_ROWS}", "100.0"], (
        f"the Total row lost a cell:\n{row}"
    )


@pytest.mark.integration
def test_shipped_language_names_are_untouched_by_the_escaper(tmp_path):
    """Escaping must be a no-op on every name the table actually emits.

    The sibling pin for the corpus-sources table (ticket 0367). A fix that
    churns `tab_languages.md` on the next regeneration is a failed fix: a diff
    on every row hides the one row that changed for a real reason. No
    `LANGUAGE_NAMES` value carries an escapable character today, so the emitted
    table must carry no backslash at all — and the Total row's `**` must be the
    only asterisks in it.
    """
    require_pandoc()
    from export_language_table import LANGUAGE_NAMES

    enriched = tmp_path / "enriched_works.csv"
    enriched.write_text(
        "language\n" + "".join(f"{code}\n" * ENOUGH_ROWS for code in LANGUAGE_NAMES),
        encoding="utf-8")
    output = tmp_path / "tab_languages.md"

    subprocess.run(
        [sys.executable, SCRIPT, "--input", str(enriched), "--output", str(output)],
        cwd=REPO_ROOT, env=source_root_env(), capture_output=True,
        text=True, check=True)

    emitted = output.read_text(encoding="utf-8")

    assert "\\" not in emitted, (
        "escaping churned a shipped language name — regenerating the table "
        f"would rewrite rows that did not change:\n{emitted}"
    )
    assert emitted.count("*") == 4, (
        "the only emphasis in the table is the Total row's `**…**`:\n{}".format(emitted)
    )
    for name in LANGUAGE_NAMES.values():
        assert f"| {name} |" in emitted, f"name {name!r} was rewritten by the escaper"
