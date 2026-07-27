"""Unit coverage for the shared pipe-table escaper (ticket 0339).

The rendered-page oracles in `test_rendered_venue_table_fidelity.py` are the
ones that prove the escaping *works*; they need pandoc and skip without it, so
these fast-tier tests keep the rule itself covered on any machine.

`markdown_cell`'s own rule is pinned in `test_variables_table.py`, next to the
codebook contract it serves. What is pinned here is the plain-text sibling and,
above all, the boundary between the two — the reason there are two functions.
"""

import os

import pytest
from _markdown_table import markdown_cell, markdown_text_cell

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")

# (emitter, the expression it interpolates as a free-text cell)
EMITTERS = [
    ("figures/export_tab_venues.py", "r['journal']"),
    ("figures/export_core_venues_markdown.py", "venue"),
]


class TestPlainTextEscaping:
    """`markdown_text_cell`: the value carries no markup intent."""

    def test_pipe_is_escaped_so_it_cannot_end_the_cell(self):
        assert markdown_text_cell("A | B") == r"A \| B"

    def test_backslash_is_escaped_before_the_pipe_it_would_absorb(self):
        """A value already containing `\\|` splits the cell if only `|` is escaped:
        its own backslash eats the new escape and the pipe goes live again."""
        assert markdown_text_cell(r"a \| b") == r"a \\\| b"

    def test_backtick_is_escaped_rather_than_opening_a_span(self):
        assert markdown_text_cell("`code`") == r"\`code\`"

    def test_trailing_backslash_is_escaped(self):
        assert markdown_text_cell("a\\") == "a\\\\"

    def test_paired_markup_is_left_alone(self):
        """Pins the documented scope limit.

        Emphasis and link syntax need a matched pair, so they cannot truncate a
        cell. Widening the rule to all CommonMark ASCII punctuation would be
        equally correct to a renderer and would churn every shipped table row
        (`Well\\-known Journal`), breaking the no-op regeneration this ticket
        verified.
        """
        assert markdown_text_cell("*em* _x_") == "*em* _x_"
        assert markdown_text_cell("[link](u)") == "[link](u)"

    def test_ordinary_venue_name_is_untouched(self):
        """Why regenerating the shipped tables stays a no-op."""
        name = "Wiley Interdisciplinary Reviews Climate Change"
        assert markdown_text_cell(name) == name


class TestContractBoundary:
    """The two functions differ by input contract, not by error policy."""

    def test_free_text_never_raises_on_an_odd_backtick(self):
        """A stray backtick in a bibliographic record is a character, not a typo.

        Inheriting `markdown_cell`'s ValueError here would let one such
        character fail a manuscript build.
        """
        assert markdown_text_cell("Journal of ` Studies") == r"Journal of \` Studies"

    def test_authored_markdown_still_rejects_an_odd_backtick(self):
        """The raise is right where the input *is* Markdown: an unbalanced
        backtick is an authoring typo whose intent cannot be guessed."""
        with pytest.raises(ValueError, match="unbalanced backtick"):
            markdown_cell("a `dangling span")

    def test_balanced_backticks_are_a_code_span_only_for_authored_markdown(self):
        """The case a mere non-raising variant would still get wrong.

        Two backticks in a journal name are two characters; in a codebook
        description they delimit a code span, which is escaped by the other
        rule. One function cannot serve both.
        """
        payload = "a `b | c` d"
        assert markdown_cell(payload) == r"a `b \| c` d"
        assert markdown_text_cell(payload) == r"a \`b \| c\` d"


class TestLineBreaks:
    """A newline cannot be escaped — a pipe-table row is line-delimited."""

    def test_newline_is_folded_to_a_space(self):
        assert markdown_text_cell("Revue\ninternationale") == "Revue internationale"
        assert markdown_text_cell("Revue\r\ninternationale") == "Revue  internationale"

    def test_ordinary_whitespace_runs_survive(self):
        """Only line breaks are touched; collapsing runs would churn shipped rows."""
        assert markdown_text_cell("A  B\tC") == "A  B\tC"


@pytest.mark.parametrize("script,expression", EMITTERS)
def test_emitter_escapes_its_free_text_cell(script, expression):
    """Fast-tier backstop for the rendered oracles, which need pandoc.

    `test_rendered_venue_table_fidelity.py` is the real proof, but it is
    `integration`-tiered and skips wholesale where pandoc is absent — leaving
    this escaping with no coverage at all on such a machine, in a repo with no
    CI. Source inspection needs nothing installed, so it still fails if an
    emitter interpolates the venue raw again.
    """
    with open(os.path.join(SCRIPTS_DIR, script), encoding="utf-8") as handle:
        source = handle.read()
    rows = [line for line in source.splitlines()
            if not line.strip().startswith("#")
            and "|" in line and expression in line]
    assert rows, f"{script}: no table row interpolating {expression} — has it moved?"
    for line in rows:
        assert f"markdown_text_cell({expression})" in line, \
            f"{script}: free-text cell interpolated unescaped:\n{line}"
