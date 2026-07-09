"""Contract tests for the shared openalex-corpus conventions.

This is the coverage that did not exist on the cross-repo contract before
ticket 0170: the canonical-text convention both climate-finance-het and
polycentric_activity depend on. Behaviour here is frozen — a change that
alters any of these outputs breaks a consuming pipeline and must be deliberate.
"""

import pandas as pd
from openalex_corpus import (
    build_text,
    is_boilerplate_abstract,
    normalize_doi,
    reconstruct_abstract,
)


class TestReconstructAbstract:
    def test_orders_words_by_position(self):
        idx = {"climate": [0], "finance": [1], "matters": [2]}
        assert reconstruct_abstract(idx) == "climate finance matters"

    def test_repeated_word_at_multiple_positions(self):
        idx = {"the": [0, 2], "green": [1], "bond": [3]}
        assert reconstruct_abstract(idx) == "the green the bond"

    def test_empty_and_none(self):
        assert reconstruct_abstract(None) == ""
        assert reconstruct_abstract({}) == ""


class TestNormalizeDoi:
    def test_strips_url_prefixes(self):
        assert normalize_doi("https://doi.org/10.1/AbC") == "10.1/abc"
        assert normalize_doi("http://dx.doi.org/10.2/X") == "10.2/x"
        assert normalize_doi("doi:10.3/Y") == "10.3/y"

    def test_lowercases_and_trims(self):
        assert normalize_doi("  10.4/Foo  ") == "10.4/foo"

    def test_list_takes_first(self):
        assert normalize_doi(["10.5/a", "10.6/b"]) == "10.5/a"

    def test_none_and_empty_list(self):
        assert normalize_doi(None) == ""
        assert normalize_doi([]) == ""


class TestIsBoilerplateAbstract:
    def test_too_short(self):
        assert is_boilerplate_abstract("tiny") is True
        assert is_boilerplate_abstract(None) is True

    def test_known_phrases(self):
        assert is_boilerplate_abstract("International audience") is True
        assert is_boilerplate_abstract("info:eu-repo/semantics/openAccess xxxxx") is True

    def test_title_duplication(self):
        title = "Green bonds and the cost of capital"
        assert is_boilerplate_abstract(title, title=title) is True

    def test_real_abstract_passes(self):
        real = ("This paper examines how climate finance crystallized as an "
                "economic object between 2007 and 2014.")
        assert is_boilerplate_abstract(real) is False


class TestBuildText:
    def test_title_abstract_keywords(self):
        row = pd.Series({
            "title": "Green bonds",
            "abstract": "A study of green bond markets and their pricing dynamics.",
            "keywords": "finance;climate",
        })
        out = build_text(row)
        assert out == ("Green bonds. A study of green bond markets and their "
                       "pricing dynamics.. finance, climate")

    def test_boilerplate_abstract_dropped(self):
        row = pd.Series({
            "title": "Green bonds",
            "abstract": "International audience",
            "keywords": None,
        })
        assert build_text(row) == "Green bonds"

    def test_missing_abstract_and_keywords(self):
        row = pd.Series({"title": "Solo title", "abstract": None, "keywords": None})
        assert build_text(row) == "Solo title"
