"""AI-tell checks judge the author's prose, not the reference list."""

import importlib.util
import os

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "qa_word_count",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts",
        "qa",
        "qa_word_count.py",
    ),
)
qa_word_count = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(qa_word_count)


BODY = "The corpus assembles works on climate finance from eight sources.\n\n"

# Buchner et al. 2013 as pdftotext renders it: the title carries a blacklisted
# word, and the URL slug carries it again, lowercase and hyphenated.
REFS = (
    "References\n\n"
    "Buchner, Barbara, Morgan Herve-Mignucci, Chiara Trabacchi, Jane Wilkinson,\n"
    "Martin Stadelmann, Rodney Boyd, Federico Mazza, Valerio Micale, and Dario\n"
    "Abramskiehn. 2013. The Global Landscape of Climate Finance 2013. Climate\n"
    "Policy Initiative. https://www.climatepolicyinitiative.org/publication/"
    "global-landscapeof-climate-finance-2013/.\n"
)


class TestStripReferences:
    def test_drops_everything_from_the_heading_on(self):
        assert qa_word_count.strip_references(BODY + REFS) == BODY

    def test_accepts_bibliography_as_the_heading(self):
        text = BODY + REFS.replace("References", "Bibliography", 1)
        assert qa_word_count.strip_references(text) == BODY

    def test_passes_text_through_when_no_reference_section(self):
        assert qa_word_count.strip_references(BODY) == BODY

    def test_only_strips_at_a_line_start(self):
        """"...in the references" mid-sentence must not truncate the paper."""
        text = "We list every source in the References section below.\n"
        assert qa_word_count.strip_references(text) == text


class TestAiTellsIgnoreCitedWorks:
    def test_a_cited_title_does_not_trip_the_blacklist(self):
        """The old 'Global Landscape' carve-out missed the lowercase URL slug."""
        findings = qa_word_count.check_ai_tells(BODY + REFS)
        assert not [f for f in findings if "landscape" in f.lower()], findings

    def test_the_same_word_in_the_body_still_trips(self):
        """Stripping references must not disarm the check for authored prose."""
        findings = qa_word_count.check_ai_tells(
            "This paper surveys the climate finance landscape.\n\n" + REFS
        )
        assert [f for f in findings if "landscape" in f.lower()], findings

    def test_em_dash_density_ignores_the_reference_list(self):
        refs_with_dashes = REFS.replace("2013.", "2013 --- reprinted --- again ---")
        findings = qa_word_count.check_ai_tells(BODY + refs_with_dashes)
        assert not [f for f in findings if "EM-DASH" in f], findings


class TestEmDashDensity:
    """The old check split on "\\n\\n", which pdfplumber almost never emits."""

    def _prose(self, n_words, n_dashes):
        return " ".join(["word"] * n_words) + " " + " ".join(["— and"] * n_dashes)

    def test_a_long_clean_document_does_not_fire(self):
        """Three dashes across 2,000 words is sparse, not dense."""
        findings = qa_word_count.check_ai_tells(self._prose(2000, 3))
        assert not [f for f in findings if "EM-DASH" in f], findings

    def test_a_dash_ridden_document_fires(self):
        findings = qa_word_count.check_ai_tells(self._prose(200, 20))
        assert [f for f in findings if "EM-DASH" in f], findings

    def test_table_placeholder_dashes_are_not_prose(self):
        """"Other (40 languages) — 771" is notation; a dash before a number."""
        table = "Other (40 languages) — 771 2.3\nUnclassified — 1358 4.1\nTotal — 33344\n"
        findings = qa_word_count.check_ai_tells(table * 4)
        assert not [f for f in findings if "EM-DASH" in f], findings


@pytest.mark.parametrize("word", ["landscape", "delve", "tapestry"])
def test_blacklist_still_covers_its_vocabulary(word):
    """Guard against the strip accidentally emptying the check."""
    if word not in qa_word_count.BLACKLISTED_WORDS:
        pytest.skip(f"{word} not in this project's blacklist")
    findings = qa_word_count.check_ai_tells(f"We {word} into the data.\n")
    assert [f for f in findings if word in f.lower()], findings
