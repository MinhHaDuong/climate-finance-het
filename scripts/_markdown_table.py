"""Markdown pipe-table cell escaping: shared library module.

A raw ``|`` ends a table cell, and a Markdown renderer does not error on the
overflow — it drops it. Every emitter that builds a pipe table by string
interpolation therefore needs the same escaping, and this module is its single
home (tickets 0325, 0339).

It lives in a neutral flat ``_``-module so the emitters can move by phase while
the shared helper stays on the flat library surface (the ``_venue_naming.py``
pattern, ticket 0254). ``pipeline_text.py`` was the other candidate and is the
wrong one: it normalises *corpus* text (encoding artifacts, DOIs, language
codes) and pulls in pandas, ftfy and langdetect for it. Escaping markup is a
different concern with no dependencies at all.

Two functions, because the callers hold two different input contracts:

``markdown_cell``
    The input **is** Markdown — a curated description authored in-repo, whose
    backticks are intentional code spans. Used by the deposit codebook.
``markdown_text_cell``
    The input is plain text with no markup intent — a journal name out of the
    bibliographic corpus. Used by the venue-table emitters.

Collapsing them into one function is the trap this split avoids: a journal name
that happens to contain two backticks is not a code span, and applying the
Markdown-aware rule to it would silently typeset half the name as code.
"""

# The pipe is escaped everywhere; GFM honours ``\|`` inside a code span too, so
# that one rule holds throughout. The backslash needs the opposite treatment on
# each side of a span boundary — CommonMark reads it as an escape in prose but
# literally inside code — so prose and code are escaped separately.
_GFM_TEXT = str.maketrans({"\\": r"\\", "|": r"\|"})
_GFM_CODE = str.maketrans({"|": r"\|"})

# Plain text: no character carries markup intent, so the backtick is escaped
# rather than opening a span. Scoped to the three characters that change the
# rendering on their own; emphasis and link syntax need a matched pair and are
# deliberately left alone, so an ordinary venue name keeps its punctuation and
# regenerating a shipped table stays a no-op.
_GFM_LITERAL = str.maketrans({"\\": r"\\", "|": r"\|", "`": r"\`"})

# Translation is single-pass: a sequential replace loop would re-escape the
# backslashes its own earlier substitutions introduced.


def _split_spans(text: str) -> list[str]:
    """Split Markdown on backticks; odd indices are code-span interiors."""
    parts = text.split("`")
    if len(parts) % 2 == 0:
        raise ValueError(f"unbalanced backtick in description: {text!r}")
    return parts


def markdown_cell(text: str) -> str:
    """Markdown description → a Markdown pipe-table cell.

    A raw ``|`` ends the cell, so the codebook's reconstruction recipe used to
    be published cut in half. Escaping both sides of a span boundary blindly
    would corrupt any description documenting a regex or a path; escaping
    neither reintroduces the cell split, one layer down, for a value that
    already contains ``\\|``.

    Raises ``ValueError`` on an unbalanced backtick, and deliberately keeps
    doing so: the input is Markdown authored in this repo, where an odd
    backtick is a typo whose intent is genuinely ambiguous — guessing would
    either escape a real code span or typeset prose as code. Free text from the
    corpus must not take this path; see ``markdown_text_cell``.
    """
    return "`".join(
        part.translate(_GFM_CODE) if i % 2 else part.translate(_GFM_TEXT)
        for i, part in enumerate(_split_spans(text))
    )


def markdown_text_cell(text: str) -> str:
    """Plain text → a Markdown pipe-table cell, rendered literally.

    For values with no markup intent — a journal name straight out of
    ``refined_works.csv``, where ten entries are bilingual names joined with a
    literal ``|``. Every escapable character is escaped uniformly, including
    the backtick, so nothing in the value is read as syntax.

    Never raises. These emitters feed a rendered manuscript, and a bibliographic
    string is not a contract the build may reject: inheriting ``markdown_cell``'s
    ValueError would turn one odd backtick in a corpus record — a character with
    no meaning there — into a failed manuscript build.
    """
    return str(text).translate(_GFM_LITERAL)
