"""Local evaluation of the REL boolean query strings (ticket 1810).

The REL lanes wrote their queries for OpenAlex ``title_and_abstract.search``:
quoted phrases and bare words joined by ``AND``/``OR``/``NOT`` with
parentheses. This module evaluates the same strings on a local table, so the
RePEc mirror lane replays them verbatim.

Matching: text and phrase are case- and accent-folded and every character
that is not a letter or a digit becomes a space; a phrase then matches on word
boundaries, and its last word also matches with a trailing ``s`` (a light
plural: OpenAlex stems, this does not). A phrase written in a script without
word spaces (CJK, Thai) matches as a substring.

Evaluation is set-based: each distinct phrase is looked up once over the whole
table (``phrase_hits``), then every query combines those index sets. That is
what makes several hundred queries over millions of records affordable.
"""

import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass

_TOKEN = re.compile(r'\s*(?:(\()|(\))|"([^"]*)"|(\bAND\b|\bOR\b|\bNOT\b)|([^\s()"]+))')
_NOSPACE_SCRIPT = re.compile(r"[぀-ヿ㐀-鿿豈-﫿฀-๿가-힯]")


def fold(text: str) -> str:
    """Case- and accent-folded, punctuation to spaces, single-spaced, padded.

    Combining marks are dropped (accents) except after a base letter of the
    Indic and South-East Asian blocks (U+0900-U+109F), where vowel signs and
    viramas are part of the word: dropping them would split ``जलवायु`` into
    fragments and lose its word boundaries."""
    t = unicodedata.normalize("NFKD", (text or "").casefold())
    out = []
    base = " "
    for c in t:
        if unicodedata.category(c) in ("Mn", "Mc", "Me"):
            if "ऀ" <= base <= "႟":
                out.append(c)
            continue
        base = c
        out.append(c if c.isalnum() else " ")
    return " " + " ".join("".join(out).split()) + " "


def phrase_needles(phrase: str) -> tuple[str, ...]:
    """The substrings whose presence in a ``fold``-ed text means a match."""
    core = fold(phrase).strip()
    if not core:
        return ()
    if _NOSPACE_SCRIPT.search(core):
        return (core,)
    return (f" {core} ", f" {core}s ")


def matches(folded_text: str, phrase: str) -> bool:
    return any(n in folded_text for n in phrase_needles(phrase))


@dataclass(frozen=True)
class Node:
    op: str                      # "PHRASE", "AND", "OR", "NOT"
    phrase: str = ""
    kids: tuple["Node", ...] = ()


def tokenize(query: str) -> list[tuple[str, str]]:
    """``(``, ``)``, ``AND``/``OR``/``NOT`` and ``("P", phrase)`` tokens."""
    toks: list[tuple[str, str]] = []
    pos = 0
    q = query.strip()
    while pos < len(q):
        m = _TOKEN.match(q, pos)
        if not m or m.end() == pos:
            raise ValueError(f"cannot parse query at {pos}: {q[pos:pos + 30]!r}")
        pos = m.end()
        paren, close, quoted, op, word = m.groups()
        if paren or close:
            toks.append((paren or close, ""))
        elif quoted is not None:
            toks.append(("P", quoted))
        else:
            toks.append((op, "") if op else ("P", word))
    return toks


def parse(query: str) -> Node:
    """AST of a query; ``AND`` binds tighter than ``OR``, adjacency is ``AND``."""
    toks = tokenize(query)
    i = 0

    def peek() -> str:
        return toks[i][0] if i < len(toks) else ""

    def expr() -> Node:
        nonlocal i
        kids = [term()]
        while peek() == "OR":
            i += 1
            kids.append(term())
        return kids[0] if len(kids) == 1 else Node("OR", kids=tuple(kids))

    def term() -> Node:
        nonlocal i
        kids = [factor()]
        while peek() in ("AND", "NOT", "P", "("):
            if peek() == "AND":
                i += 1
            kids.append(factor())
        return kids[0] if len(kids) == 1 else Node("AND", kids=tuple(kids))

    def factor() -> Node:
        nonlocal i
        t = peek()
        if t == "NOT":
            i += 1
            return Node("NOT", kids=(factor(),))
        if t == "(":
            i += 1
            n = expr()
            if peek() != ")":
                raise ValueError(f"unbalanced parentheses in {query!r}")
            i += 1
            return n
        if t == "P":
            i += 1
            return Node("PHRASE", phrase=toks[i - 1][1])
        raise ValueError(f"unexpected token {t!r} in {query!r}")

    node = expr()
    if i != len(toks):
        raise ValueError(f"trailing tokens in {query!r}")
    return node


def phrases(node: Node) -> set[str]:
    if node.op == "PHRASE":
        return {node.phrase}
    out: set[str] = set()
    for k in node.kids:
        out |= phrases(k)
    return out


def evaluate(node: Node, hits: Callable[[str], set[int]], universe: Callable[[], set[int]]) -> set[int]:
    """Indices matching ``node``, given the index set of each phrase."""
    if node.op == "PHRASE":
        return hits(node.phrase)
    if node.op == "OR":
        out: set[int] = set()
        for k in node.kids:
            out |= evaluate(k, hits, universe)
        return out
    if node.op == "AND":
        pos = [k for k in node.kids if k.op != "NOT"]
        neg = [k.kids[0] for k in node.kids if k.op == "NOT"]
        cur = evaluate(pos[0], hits, universe) if pos else set(universe())
        for k in pos[1:]:
            if not cur:
                break
            cur &= evaluate(k, hits, universe)
        for k in neg:
            cur -= evaluate(k, hits, universe)
        return cur
    if node.op == "NOT":
        return set(universe()) - evaluate(node.kids[0], hits, universe)
    raise ValueError(node.op)


def phrase_hits(folded_texts: list[str], phrase_list: Iterable[str], offset: int = 0) -> dict[str, list[int]]:
    """For each phrase, the (offset-shifted) indices of the texts it matches."""
    out: dict[str, list[int]] = {}
    for p in phrase_list:
        needles = phrase_needles(p)
        out[p] = [i + offset for i, t in enumerate(folded_texts)
                  if any(n in t for n in needles)] if needles else []
    return out


def jel_match(codes: Iterable[str], groups: list[list[str]]) -> bool:
    """True when every OR-group has a code starting with one of its prefixes."""
    cs = [c.strip().upper() for c in codes if c.strip()]
    return all(any(c.startswith(str(p).upper()) for c in cs for p in g) for g in groups)
