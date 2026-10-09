"""The REL title key: one normalizer for the REL title joins (tickets 2047, 1650).

``title_words`` is the normalized title as words; ``title_key`` is the same
string without its spaces, what two titles must share to be one title. The
pool dedup version 2 (``_rel_pool_dedup``) joins on ``title_key`` and tests
generic titles on ``title_words``; the table-of-contents lane
(``_rel_toc_core``) uses ``title_words``, whose patterns need words. Pool
dedup version 1, still the default, keeps ``utils.normalize_title``.

Steps of ``title_words``, in order:

1. HTML entities unescaped (``&rsquo;`` is ``’``), then markup tags stripped
   (``<i>Climate</i>`` is ``Climate``). A tag is ``<`` + a name + only
   ``name="value"`` attributes, so ``When p<q and q>r`` is text;
2. apostrophes deleted before any Unicode normalization (``China’s``,
   ``China's``, ``China´s``, ``China′s`` are ``chinas``; NFKC would turn
   ``´`` into a space and a combining accent). Mojibake is not repaired:
   ``bank?s`` and ``China¡¯s`` reach the key of ``Bank's`` only because
   their stand-ins are punctuation; ``ARTISANSâ€™`` does not;
3. Unicode NFKC then casefold, so the composed and decomposed forms of
   ``légitimité`` are one string and compatibility forms (ligatures ``ﬁ``,
   full-width letters) fold. Casefold turns ``ß`` into ``ss``, accepted;
4. accents folded on Latin letters only: a combining mark is dropped when its
   base letter is Latin (``Poznań`` is ``poznan``, ``Côte`` is ``cote``), or
   when no letter or digit carries it. Accepted consequences: Spanish ``ñ``
   and ``n``, Vietnamese tones, German ``ü`` and ``u`` fold together. Marks
   on any other script are kept (``й`` stays ``й``, ``が`` stays ``が``).
   Decided by measurement on the pool of 2026-10-09 (ticket 2047 log);
5. format characters deleted (a soft hyphen or a zero-width space splits no
   word); letters, marks and digits kept; every other character becomes a
   space: hyphens and dashes, punctuation, symbols (so ``$100`` and ``€100``
   share a key, accepted);
6. whitespace collapsed and trimmed.

``title_key`` then drops the spaces, so ``Post-Kyoto``, ``Post Kyoto`` and
``Postkyoto`` share a key, as do ``U.S.`` and ``US``, ``2°C`` and ``2C``.
Two titles that differ only in where the words split share a key too; the
2047 log gives the merges this makes on the pool, all read.

No transliteration: two titles in Chinese, Russian or Arabic share a key only
when they are the same letters. Standard library only.
"""

import html
import re
import unicodedata

# A tag: "<" or "</", a name (``i``, ``mml:math``), only name="value"
# attributes, then ">" or "/>"; anything else is text.
_TAG = re.compile(r"</?[A-Za-z][\w:.-]*"
                  r"(?:\s+[\w:.-]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s<>\"']+))*\s*/?>")
# Apostrophes and their stand-ins: ' ‘ ’ ‛ ʼ ′ ` ´
_APOSTROPHE = re.compile("['‘’‛ʼ′`´]")
_SPACE = re.compile(r"\s+")


def _is_latin(c):
    return unicodedata.name(c, "").startswith("LATIN ")


def _fold_latin_accents(t):
    """Drop combining marks on Latin letters, and marks with no letter or digit
    to carry them (a leading mark, or the stray accent NFKC leaves after a
    space for ``¯``); keep marks on every other script."""
    out, base = [], ""
    for c in unicodedata.normalize("NFD", t):
        if unicodedata.combining(c):
            if base and unicodedata.category(base)[0] in "LN" and not _is_latin(base):
                out.append(c)
            continue
        base = c
        out.append(c)
    return unicodedata.normalize("NFC", "".join(out))


def _char(c):
    cat = unicodedata.category(c)
    if cat[0] in "LMN":
        return c
    if cat == "Cf":
        return ""
    return " "


def title_words(title):
    """The normalized title as space-separated words; ``""`` if none."""
    if not isinstance(title, str) or not title:
        return ""
    t = _APOSTROPHE.sub("", _TAG.sub("", html.unescape(title)))
    t = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", t).casefold())
    t = _fold_latin_accents(t)
    return _SPACE.sub(" ", "".join(_char(c) for c in t)).strip()


def title_key(title):
    """The normalized title two records must share to be one title; ``""`` if none."""
    return title_words(title).replace(" ", "")
