"""Unit coverage for the shared pipe-table escaper (ticket 0339).

The rendered-page oracles in `test_rendered_venue_table_fidelity.py` are the
ones that prove the escaping *works*; they need pandoc and skip without it, so
these fast-tier tests keep the rule itself covered on any machine.

What is pinned here is the plain-text escaper and, above all, the boundary with
its sibling — the reason the module splits at all. Ticket 0530 adds the second
sibling, `markdown_verbatim_cell`, at the bottom.

Ticket 0376 adds one rendered class at the bottom of this module rather than in
a fidelity suite: what it pins is the *character set* — a property of the
escaper itself — against the reader the build really uses.
"""

import os

import pytest
from _markdown_table import markdown_text_cell, markdown_verbatim_cell

TESTS_DIR = os.path.dirname(__file__)
SCRIPTS_DIR = os.path.join(TESTS_DIR, "..", "scripts")
BIBLIOGRAPHY = os.path.join(
    TESTS_DIR, "..", "deliverables", "_shared", "bibliography", "main.bib")

# A key that really resolves in that bibliography. A resolving key is the
# stronger fixture: an unresolvable one renders visible broken-citation garbage,
# which an author would catch, while this one renders a plausible-looking
# reference to a work the row never meant to cite.
LIVE_KEY = "stern2007"

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
    """Free text is data, not markup this repo authored."""

    def test_free_text_never_raises_on_an_odd_backtick(self):
        """A stray backtick in a bibliographic record is a character, not a typo.

        Raising here would let one such character fail a manuscript build.
        """
        assert markdown_text_cell("Journal of ` Studies") == r"Journal of \` Studies"

    def test_balanced_backticks_are_characters_not_a_span(self):
        """Two backticks in a journal name are two characters, never a code
        span — the value carries no markup intent."""
        assert markdown_text_cell("a `b | c` d") == r"a \`b \| c\` d"


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


# --- Ticket 0376: the character set must match the reader that renders ---

ROW_MARK = "ROWMARK"


def _one_row_table(value: str) -> str:
    """A minimal pipe table whose single body row carries `value`.

    The second cell is a fixed sentinel so `row_with` has an unambiguous needle
    that no test value can perturb.
    """
    return f"| Value | Mark |\n|---|---|\n| {value} | {ROW_MARK} |\n"


def _rendered_value(value: str, tmp_path, bibliography: str | None = None) -> str:
    """`value` as the reader renders it into a cell, tags stripped."""
    from _qmd_render import cell_texts, render_qmd, row_with

    flat = render_qmd(_one_row_table(value), tmp_path, bibliography)
    return cell_texts(row_with(flat, ROW_MARK))[0]


class TestReaderExtensionCharacters:
    """`@`, `~` and `^` are live syntax in the reader Quarto uses.

    `markdown` carries `+citations +subscript +superscript`; `gfm` carries none
    of them. The escaper and its oracle were both calibrated to `gfm`, so a
    corpus value carrying one of these characters rendered as markup in a
    published table and no test could see it.

    Each case is paired with an unescaped control. Without the control a test
    passes vacuously the day someone points the oracle back at `gfm` — which is
    precisely the regression this ticket exists to prevent.
    """

    @pytest.mark.integration
    def test_citation_key_reaches_the_page_as_text(self, tmp_path):
        """The carrier of record: journal names come straight from the corpus,
        where an `@` is far likelier than in a hand-edited source label."""
        from _qmd_render import require_pandoc
        require_pandoc()
        value = f"Grey lit @{LIVE_KEY} set"

        assert _rendered_value(value, tmp_path, BIBLIOGRAPHY) != value, (
            "control failed: an unescaped citation key rendered literally, so "
            "this test cannot see the defect — has the oracle's reader changed?"
        )
        assert _rendered_value(
            markdown_text_cell(value), tmp_path, BIBLIOGRAPHY) == value

    @pytest.mark.integration
    def test_tilde_and_caret_reach_the_page_as_text(self, tmp_path):
        """`CO~2~` is an entirely plausible string in this corpus, and it
        renders as `CO<sub>2</sub>` unescaped."""
        from _qmd_render import require_pandoc
        require_pandoc()
        value = "CO~2~ at x^2^"

        assert _rendered_value(value, tmp_path) == "CO2 at x2", (
            "control failed: subscript/superscript did not fire, so this test "
            "cannot see the defect — has the oracle's reader changed?"
        )
        assert _rendered_value(markdown_text_cell(value), tmp_path) == value


class TestReaderExtensionCharactersUnit:
    """The same rule without pandoc, so it stays covered on any machine.

    This repo has no CI and the rendered cases above skip wholesale where pandoc
    is absent; source-level pins need nothing installed.
    """

    def test_at_sign_is_escaped(self):
        assert markdown_text_cell(f"@{LIVE_KEY}") == rf"\@{LIVE_KEY}"

    def test_tilde_and_caret_are_escaped(self):
        assert markdown_text_cell("CO~2~ at x^2^") == r"CO\~2\~ at x\^2\^"

    def test_emphasis_stays_exempt_beside_them(self):
        """Why `~`/`^` are escaped while `*`/`_` are not.

        The exemption is not "needs a matched pair" — `~`/`^` need one too. It
        is that the emitters themselves add `**…**` *after* escaping, so
        escaping `*` would destroy markup they intend. No emitter ever adds a
        tilde or a caret.
        """
        assert markdown_text_cell("*em* _x_ ~sub~") == r"*em* _x_ \~sub\~"


class TestVerbatimCell:
    """A value a reader copies and executes must survive the reader intact.

    The reader carries `smart`, which rewrites `"` `'` `--` `...`. That is
    correct for prose and wrong for a query: it published an ISTEX search whose
    phrase delimiters no longer delimit phrases (ticket 0530). A code span
    suppresses `smart` inside it, so the fix is a construction, not an escape.
    """

    @pytest.mark.integration
    def test_straight_quotes_survive_the_reader(self, tmp_path):
        from _qmd_render import require_pandoc
        require_pandoc()
        value = '"climate finance" OR "finance climat"'

        assert _rendered_value(value, tmp_path) != value, (
            "control failed: unescaped straight quotes rendered literally, so "
            "this test cannot see the defect — has the oracle lost `smart`?"
        )
        assert _rendered_value(markdown_verbatim_cell(value), tmp_path) == value

    @pytest.mark.integration
    def test_a_backtick_in_the_value_does_not_break_the_span(self, tmp_path):
        """The defect the #1289 review found in the first fix.

        Wrapping `markdown_text_cell` output in backticks looks right and is
        not: it escapes a backtick with a backslash, which CommonMark reads
        *literally* inside a code span, so the span closes on the value's own
        backtick and the remainder leaks out as raw Markdown. Worse than the
        bug being fixed, and dormant — no ISTEX query carries a backtick today
        — which is exactly why it is pinned here rather than left to the one
        live value.
        """
        from _qmd_render import require_pandoc
        require_pandoc()
        value = 'q = `x` AND "y"'

        assert _rendered_value(f"`{markdown_text_cell(value)}`", tmp_path) != value, (
            "control failed: the naive escape-then-wrap no longer corrupts the "
            "value, so this test no longer pins the defect it was written for"
        )
        assert _rendered_value(markdown_verbatim_cell(value), tmp_path) == value

    def test_the_fence_outgrows_the_longest_backtick_run(self):
        assert markdown_verbatim_cell("a ``b`` c") == "```a ``b`` c```"

    def test_a_leading_or_trailing_backtick_is_padded(self):
        """The reader strips one leading and one trailing space from a span,
        so the padding is invisible in the output but keeps the fences apart."""
        assert markdown_verbatim_cell("`x`") == "`` `x` ``"

    @pytest.mark.integration
    def test_a_pipe_in_the_value_neither_splits_nor_escapes(self, tmp_path):
        r"""Both halves, through the renderer, because the source alone lies.

        The first draft escaped the pipe, inheriting this module's prose rule.
        Inside a span that is exactly wrong: CommonMark processes no escape
        there, so `\|` ships the backslash into the published value — a
        backslash in the middle of a regex a reader is meant to run. The span
        needs no escape, because the reader's pipe-table splitter respects it.

        A source-level assertion cannot tell these apart: `` `a \| b` `` and
        `` `a | b` `` are both plausible-looking strings, and only the render
        says which one publishes the value the emitter was given. That is why
        the escaped form got through the first round (#1289 review, round two).
        """
        from _qmd_render import require_pandoc
        require_pandoc()
        value = "(alpha|beta)+ AND \"gamma\""

        assert _rendered_value(markdown_verbatim_cell(value), tmp_path) == value

    def test_no_backslash_is_added(self):
        r"""The unit half: a span escapes nothing, so nothing is escaped."""
        assert markdown_verbatim_cell(r"(a|b) \d+") == r"`(a|b) \d+`"

    def test_an_empty_value_is_not_an_empty_span(self):
        """A bare `` renders as two literal backticks, not an empty span."""
        assert markdown_verbatim_cell("") == ""
