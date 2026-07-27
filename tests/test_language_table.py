"""Tests for export_language_table.py — ticket #402.

Verifies that:
- normalise_language handles common edge cases correctly
- the data paper includes the language table
- the script is importable and the normalise function works
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "figures"))  # 0255: moved figures entry points

ROOT = os.path.join(os.path.dirname(__file__), "..")
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
