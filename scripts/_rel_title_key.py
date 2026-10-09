"""The REL title key: one normalizer for the REL title joins (tickets 2047, 1650).

``title_key`` is what two titles must share to be one title. It is the title
normalizer of the pool dedup version 2 (``_rel_pool_dedup``) and of the
table-of-contents lane (``_rel_toc_core``). Pool dedup version 1, still the
default, keeps ``utils.normalize_title``.

Steps, in order:

1. HTML entities unescaped (``&rsquo;`` is ``’``), then markup tags stripped
   (``<i>Climate</i>`` is ``Climate``);
2. Unicode NFKC then casefold, so the composed and decomposed forms of
   ``légitimité`` are one string and compatibility forms (ligatures,
   full-width letters) fold;
3. accents folded on Latin letters only: a combining mark is dropped when its
   base letter is Latin (``Poznań`` is ``poznan``, ``Côte`` is ``cote``).
   Marks on any other script are kept (``й`` stays ``й``, ``が`` stays
   ``が``). Decided by measurement on the pool of 2026-10-09 (ticket 2047
   log): every title + year group that only Latin folding forms is one work
   or carries two DOIs, which the cascade never joins;
4. apostrophes deleted (``China’s`` and ``China's`` are ``chinas``) and
   format characters deleted (a soft hyphen splits no word); every other
   character that is not a letter, a mark or a digit becomes a space: hyphens
   and dashes (``Post-Kyoto`` is ``post kyoto``), punctuation, symbols;
5. whitespace collapsed and trimmed.

No transliteration: two titles in Chinese, Russian or Arabic share a key only
when they are the same letters. Standard library only.
"""

import html
import re
import unicodedata

# Tags only: "<" then a name (``i``, ``mml:math``), so "a < b" is text.
_TAG = re.compile(r"</?[A-Za-z][\w:.-]*(?:\s[^<>]*)?/?>")
# Apostrophes and their stand-ins: ' ‘ ’ ‛ ʼ ′ ` ´
_APOSTROPHES = frozenset("'‘’‛ʼ′`´")
_SPACE = re.compile(r"\s+")


def _is_latin(c):
    return unicodedata.name(c, "").startswith("LATIN ")


def _fold_latin_accents(t):
    out, base = [], ""
    for c in unicodedata.normalize("NFD", t):
        if unicodedata.combining(c):
            if not _is_latin(base):
                out.append(c)
            continue
        base = c
        out.append(c)
    return unicodedata.normalize("NFC", "".join(out))


def _char(c):
    if c in _APOSTROPHES:
        return ""
    cat = unicodedata.category(c)
    if cat[0] in "LMN":
        return c
    if cat == "Cf":
        return ""
    return " "


def title_key(title):
    """The normalized title two records must share to be one title; ``""`` if none."""
    if not isinstance(title, str) or not title:
        return ""
    t = _TAG.sub("", html.unescape(title))
    t = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", t).casefold())
    t = _fold_latin_accents(t)
    return _SPACE.sub(" ", "".join(_char(c) for c in t)).strip()
