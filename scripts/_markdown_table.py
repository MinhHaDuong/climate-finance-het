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
    bibliographic corpus, a source label edited by hand, a language code the
    normaliser passed through unchanged. Used by the venue-table emitters, the
    retrieval-protocol table, and — ticket 0370 — the corpus-sources table, the
    language table and the corpus-flow ledger.

Collapsing them into one function is the trap this split avoids: a journal name
that happens to contain two backticks is not a code span, and applying the
Markdown-aware rule to it would silently typeset half the name as code.

**Which reader these rules are calibrated to (ticket 0376).** Not GFM, though
the tables look like GFM pipe tables. Quarto's ``from:`` is a custom Lua reader,
``/opt/quarto/share/filters/qmd-reader.lua``, which delegates to ``readqmd.lua``;
that module sets ``Extensions = pandoc.format.extensions 'markdown'`` and calls
``pandoc.read`` with ``{format = "markdown", extensions = …}``. No
``reader-extensions:`` key appears in the ``--defaults`` YAML Quarto hands its
bundled pandoc, so the extension set is pandoc's own default for ``markdown`` —
the full extended reader. ``pandoc --list-extensions`` gives the difference that
matters here: ``markdown`` carries ``+citations +subscript +superscript``, and
``gfm`` carries none of the three. Where ``bibliography:`` is set — every
deliverable that renders one of these tables — Quarto appends ``citeproc``
automatically, so a live ``@key`` does not merely become a span, it resolves.

A fourth extension differs the same way and is deliberately **not** escaped
here: ``smart``, which rewrites ``"`` ``'`` ``--`` ``...`` as typographic
quotes, dashes and an ellipsis. Unlike the three above it produces *correct*
output — curly quotes in a journal name or a caption are what a rendered
document should have — so escaping it would degrade every table's typography.
It is wrong only for a cell holding a value a reader will copy and execute,
where it silently rewrites the value: it published an ISTEX query whose phrase
delimiters no longer delimit phrases (ticket 0530). That is a per-cell semantic
distinction the escaper cannot see, so the emitter owns it, by wrapping such a
cell in a code span — which suppresses ``smart`` inside it — *after* escaping.

Recorded here so the next reader does not re-derive it from the documentation,
which describes neither the Lua reader nor the extension set it selects.
"""

# The pipe is escaped everywhere; the reader honours ``\|`` inside a code span
# too, so that one rule holds throughout. The backslash needs the opposite
# treatment on each side of a span boundary — CommonMark reads it as an escape
# in prose but literally inside code — so prose and code are escaped separately.
_PROSE = {"\\": r"\\", "|": r"\|"}

_MARKDOWN_TEXT = str.maketrans(_PROSE)
_MARKDOWN_CODE = str.maketrans({"|": r"\|"})

# Plain text extends the prose rule rather than restating it: no character
# carries markup intent, so the backtick is escaped rather than opening a span,
# and ``@``, ``~`` and ``^`` are escaped because the reader above reads them as
# citation, subscript and superscript syntax. ``~`` carries a fourth one that
# list does not name: ``+strikeout`` is live in this reader too, so
# ``~~struck~~`` renders ``<del>``. Verified against pandoc, not assumed. The
# escape is character-level rather than pair-aware, so it already neutralises
# both readings of the tilde — but "subscript" alone would leave a maintainer
# unaware that strikeout is covered (raised by the #1244 review panel).
#
# Emphasis and link syntax stay exempt, and the reason is not the one the
# earlier wording gave. "Changes the rendering on its own" does not separate the
# two groups: ``~`` and ``^`` need a matched pair exactly as ``*`` and ``_`` do,
# and ``CO~2~ emissions`` — an entirely plausible corpus string — renders
# ``CO<sub>2</sub> emissions`` from one cell. The real criterion is authorship:
# the emitters themselves add ``**…**`` *after* escaping, so escaping ``*``
# would destroy markup they intend, while no emitter ever adds a tilde or a
# caret. ``@`` is escaped on the same footing and needs no pair at all.
#
# The backtick's own reason is a third one worth keeping distinct: it pairs
# *across* cells — ``c`1 | MID | d`2`` swallows the middle cell into a code
# span — which is why it is escaped unconditionally rather than under the
# matched-pair reasoning. ``~`` and ``^`` do not pair across cells.
#
# CR and LF are folded to a space, not escaped: a pipe-table row is
# line-delimited, so a raw newline ends the row and no backslash can hold it.
# Only line breaks are touched — collapsing runs of ordinary whitespace would
# churn shipped rows for a defect that does not exist.
_MARKDOWN_LITERAL = str.maketrans({
    **_PROSE, "`": r"\`", "@": r"\@", "~": r"\~", "^": r"\^",
    "\n": " ", "\r": " ",
})

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
        part.translate(_MARKDOWN_CODE) if i % 2 else part.translate(_MARKDOWN_TEXT)
        for i, part in enumerate(_split_spans(text))
    )


def markdown_text_cell(text: str) -> str:
    """Plain text → a Markdown pipe-table cell, rendered literally.

    For values with no markup intent — a journal name straight out of
    ``refined_works.csv``, where ten entries are bilingual names joined with a
    literal ``|``. Every escapable character is escaped uniformly, including
    the backtick, so nothing in the value is read as syntax.

    A newline is folded to a space rather than escaped: a pipe-table row is
    line-delimited, so a raw newline ends the row outright and no backslash can
    hold it. A quoted CSV field can carry one, so this is the same defect class
    as the pipe, one level below the escaper.

    Never raises. These emitters feed a rendered manuscript, and a bibliographic
    string is not a contract the build may reject: inheriting ``markdown_cell``'s
    ValueError would turn one odd backtick in a corpus record — a character with
    no meaning there — into a failed manuscript build.
    """
    return str(text).translate(_MARKDOWN_LITERAL)
