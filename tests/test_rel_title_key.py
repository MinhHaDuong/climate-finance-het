"""The REL title key (ticket 2047): every observed string of the 2044 audit is a test."""

import unicodedata

import _rel_toc_core as toc
import pytest
from _rel_title_key import title_key, title_words

pytestmark = pytest.mark.domain_corpus


@pytest.mark.parametrize("raw, words", [
    ("Emerging markets&rsquo; carbon pricing", "emerging markets carbon pricing"),
    ("Emerging markets’ carbon pricing", "emerging markets carbon pricing"),
    ("Post-Kyoto", "post kyoto"),
    ("Post Kyoto", "post kyoto"),
    ("Post–Kyoto", "post kyoto"),          # en dash
    ("Post—Kyoto", "post kyoto"),          # em dash
    ("Post‐Kyoto", "post kyoto"),          # Unicode hyphen
    ("<i>Climate</i> finance", "climate finance"),
    ("&lt;i&gt;Climate&lt;/i&gt; finance", "climate finance"),
    ('CO<sub>2</sub> and <mml:math display="inline"><mml:mi>x</mml:mi></mml:math> markets',
     "co2 and x markets"),
    ("When p<q and q>r", "when p q and q r"),   # not a tag: text survives
    ("a < b and c > d", "a b and c d"),
    ("China’s climate funds", "chinas climate funds"),
    ("China's climate funds", "chinas climate funds"),
    ("China´s climate funds", "chinas climate funds"),   # acute accent as apostrophe
    ("China′s climate funds", "chinas climate funds"),   # prime
    ("China¡¯s climate funds", "china s climate funds"),  # GBK mojibake: punctuation
    ("the bank?s role", "the bank s role"),      # lost apostrophe: punctuation
    ("What? Why", "what why"),
    ("cli­mate finance", "climate finance"),  # soft hyphen splits no word
    ("cli​mate finance", "climate finance"),  # zero-width space: deleted
    ("ＣＬＩＭＡＴＥ finance", "climate finance"),  # full-width
    ("Review of the 2008 UNFCCC meeting in Poznań", "review of the 2008 unfccc meeting in poznan"),
    ("Straße", "strasse"),                       # casefold: accepted
    ("  Climate   finance:  a review ", "climate finance a review"),
    ("́abc", "abc"),                        # leading combining mark: no crash
    ("", ""),
    (None, ""),
])
def test_observed_strings(raw, words):
    assert title_words(raw) == words
    assert title_key(raw) == words.replace(" ", "")


@pytest.mark.parametrize("a, b", [
    ("Post-Kyoto", "Postkyoto"), ("meta-governance", "metagovernance"),
    ("Trade-Offs", "Tradeoffs"), ("Re-examining", "Reexamining"), ("U.S. aid", "US aid"),
    ("The 2°C target", "The 2C target"), ("the bank?s role", "The Bank's role"),
    ("China¡¯s rise", "China’s rise"), ("EU´s policy", "EU's policy"),
    ("Editor?s Note", "Editor′s Note"),
])
def test_v1_joins_the_v2_key_keeps(a, b):
    """Pairs utils.normalize_title already joined (review of PR 1735): the new key
    must not split them. ``ARTISANSâ€™`` against ``Artisans’`` is listed, not fixed."""
    assert title_key(a) == title_key(b)


def test_composed_and_decomposed_forms_share_one_key():
    nfc = unicodedata.normalize("NFC", "légitimité")
    nfd = unicodedata.normalize("NFD", "légitimité")
    assert nfc != nfd
    assert title_key(nfc) == title_key(nfd) == title_key("legitimite") == "legitimite"


# Pairs of distinct titles, one character apart where the script allows it.
DISTINCT = [
    "气候融资", "气候金融", "气候融资与发展",                     # Chinese
    "がくしゅう", "かくしゅう",                                   # Japanese, dakuten
    "기후 금융", "기후 재정",                                     # Korean
    "Климатическое финансирование", "Климатическое финансирования",  # Russian
    "Мой мир", "Мои мир",                                         # й (и + breve) is not и
    "تمويل المناخ", "تمويل التنمية", "تمويل المناخي",             # Arabic
    "हिंदी", "हिदी",                                              # Devanagari, a mark
]


def test_distinct_non_latin_titles_never_share_a_key():
    keys = [title_key(t) for t in DISTINCT]
    assert all(keys), "no title loses all its letters"
    assert len(set(keys)) == len(DISTINCT)


def test_toc_lane_uses_the_same_definition():
    """One definition for the pool and the TOC lane, not a fifth copy."""
    assert toc.normalize_title is title_words
