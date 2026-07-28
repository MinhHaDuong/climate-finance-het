"""Unit coverage for the shared pipe-table escaper (ticket 0339).

The rendered-page oracles in `test_rendered_venue_table_fidelity.py` are the
ones that prove the escaping *works*; they need pandoc and skip without it, so
these fast-tier tests keep the rule itself covered on any machine.

`markdown_cell`'s own rule is pinned in `test_variables_table.py`, next to the
codebook contract it serves. What is pinned here is the plain-text sibling and,
above all, the boundary between the two — the reason there are two functions.

Ticket 0376 adds one rendered class at the bottom of this module rather than in
a fidelity suite: what it pins is the *character set* — a property of the
escaper itself — against the reader the build really uses.
"""

import os

import pytest
from _markdown_table import markdown_cell, markdown_text_cell

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
