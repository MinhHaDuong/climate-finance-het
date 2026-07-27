"""Free bibliographic text is HTML-escaped before it reaches hover markup (ticket 0341).

`plot_interactive_corpus.py` builds Plotly hover boxes as raw HTML: the
`<b>`, `<br>` and `<i>` tags are deliberate markup. Title, first author and
journal are free bibliographic text, and an `&` ("Energy Research & Social
Science") or a `<` corrupts the box the same way an unescaped `|` corrupts a
pipe-table cell. The two sibling HTML figure scripts (`plot_genealogy_html.py`,
`plot_alluvial_html.py`) already call `html_mod.escape()` on every free-text
field; these tests pin the third script onto the same convention.

The builder lives in `scripts/figures/_hover_text.py` rather than inline in the
plotting script: `plot_interactive_corpus.py` runs its whole pipeline at module
scope (it calls `parse_args()` and reads the DVC-gated corpus on import), so an
inline function cannot be imported by a test without executing the pipeline.
"""

import os
import sys

BASE = os.path.join(os.path.dirname(__file__), "..")
SCRIPTS_DIR = os.path.join(BASE, "scripts")
FIGURES_DIR = os.path.join(SCRIPTS_DIR, "figures")
sys.path.insert(0, FIGURES_DIR)


def _read_figure_script(name):
    with open(os.path.join(FIGURES_DIR, name), encoding="utf-8") as f:
        return f.read()


class TestEscaping:
    """Free-text values are escaped; structural tags are not."""

    def test_ampersand_in_journal_is_escaped(self):
        """"Energy Research & Social Science" is an ordinary journal name."""
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="Green bonds",
            first_author="Smith",
            year=2019,
            journal="Energy Research & Social Science",
            cited_by_count=120,
        )
        assert "Energy Research &amp; Social Science" in out
        assert "Research & Social" not in out

    def test_ampersand_in_title_is_escaped(self):
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="Risk & return",
            first_author="Smith",
            year=2019,
            journal="Nature",
            cited_by_count=1,
        )
        assert "Risk &amp; return" in out
        assert "Risk & return" not in out

    def test_angle_brackets_in_title_are_escaped(self):
        """A `<` in a title must not be read as the start of a tag."""
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="Warming <2C pathways",
            first_author="Smith",
            year=2019,
            journal="Nature",
            cited_by_count=1,
        )
        assert "Warming &lt;2C pathways" in out
        assert "<2C" not in out

    def test_angle_brackets_in_author_are_escaped(self):
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="Green bonds",
            first_author="<script>alert(1)</script>",
            year=2019,
            journal="Nature",
            cited_by_count=1,
        )
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_double_quote_is_left_literal(self):
        """`&quot;` would reach the tooltip verbatim — Plotly cannot decode it.

        Plotly runs its own `convertEntities` over hover text rather than
        handing it to the browser's HTML parser, and its named-entity table
        is `mu amp lt gt nbsp times plusmn deg`. `quot` is absent, so an
        escaped double quote renders as the six literal characters. 23 of the
        2,644 core titles carry one (`Assessing "Dangerous Climate Change"`),
        so escaping quotes here would be a regression, not a hardening.
        """
        from _hover_text import build_hover_text

        out = build_hover_text(
            title='Assessing "Dangerous Climate Change"',
            first_author="Hansen",
            year=2008,
            journal="Open Atmospheric Science Journal",
            cited_by_count=1000,
        )
        assert '<b>Assessing "Dangerous Climate Change"</b>' in out
        assert "&quot;" not in out

    def test_apostrophe_is_left_literal(self):
        """Plotly *would* decode `&#x27;`, but a literal quote is simpler."""
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="The world's carbon markets",
            first_author="O'Neill",
            year=2015,
            journal="Nature",
            cited_by_count=10,
        )
        assert "The world's carbon markets" in out
        assert "O'Neill" in out
        assert "&#x27;" not in out

    def test_ampersand_still_escaped_alongside_quotes(self):
        """Relaxing `quote` must not relax the three entities Plotly decodes."""
        from _hover_text import build_hover_text

        out = build_hover_text(
            title='"Risk" & <reward>',
            first_author="A",
            year=2000,
            journal="J",
            cited_by_count=1,
        )
        assert '<b>"Risk" &amp; &lt;reward&gt;</b>' in out

    def test_structural_tags_survive_unescaped(self):
        """The `<b>`/`<br>` template markup is intentional and must stay markup."""
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="Risk & return",
            first_author="Smith",
            year=2019,
            journal="Energy Research & Social Science",
            cited_by_count=120,
        )
        assert out.startswith("<b>")
        assert "</b>" in out
        assert "<br>" in out
        assert "&lt;b&gt;" not in out
        assert "&lt;br&gt;" not in out

    def test_istex_url_escaped_and_only_present_when_given(self):
        from _hover_text import build_hover_text

        without = build_hover_text(
            title="T", first_author="A", year=2000, journal="J", cited_by_count=1
        )
        assert "ISTEX PDF:" not in without

        with_url = build_hover_text(
            title="T",
            first_author="A",
            year=2000,
            journal="J",
            cited_by_count=1,
            istex_url="https://api.istex.fr/document/AB/fulltext/pdf?a=1&b=2",
        )
        assert "ISTEX PDF: https://api.istex.fr/document/AB/fulltext/pdf?a=1&amp;b=2" in with_url


class TestStructure:
    """The builder reproduces the four-line hover box the script used to build inline."""

    def test_line_order_and_content(self):
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="Green bonds",
            first_author="Smith",
            year=2019,
            journal="Nature",
            cited_by_count=120,
        )
        assert out.split("<br>") == [
            "<b>Green bonds</b>",
            "Smith (2019)",
            "Nature",
            "Cited by: 120",
        ]

    def test_numeric_fields_render_as_integers(self):
        """Production feeds floats, not ints — the `int()` coercion is load-bearing.

        `year` and `cited_by_count` come off a pandas frame through
        `pd.to_numeric`, so they arrive as float64. Without the coercion the
        tooltip reads `Zomer (2008.0)` and `Cited by: 1140.0` on every point,
        and every other test in this file would still pass: they all pass
        plain int literals.
        """
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="Land suitability for the CDM",
            first_author="Zomer",
            year=2008.0,
            journal="Agriculture Ecosystems & Environment",
            cited_by_count=1140.0,
        )
        assert "Zomer (2008)" in out
        assert "Cited by: 1140" in out
        assert "2008.0" not in out
        assert "1140.0" not in out

    def test_numpy_scalars_render_as_integers(self):
        """The real call sites pass numpy scalars from `DataFrame.iterrows()`."""
        import numpy as np
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="T",
            first_author="A",
            year=np.float64(1997),
            journal="J",
            cited_by_count=np.int64(52),
        )
        assert "A (1997)" in out
        assert "Cited by: 52" in out
        assert "1997.0" not in out

    def test_cited_in_manuscript_appends_italic_line(self):
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="Green bonds",
            first_author="Smith",
            year=2019,
            journal="Nature",
            cited_by_count=120,
            cited_in_manuscript=True,
        )
        assert out.split("<br>")[-1] == "<i>Cited in manuscript</i>"

    def test_istex_line_last_after_manuscript_marker(self):
        from _hover_text import build_hover_text

        out = build_hover_text(
            title="Green bonds",
            first_author="Smith",
            year=2019,
            journal="Nature",
            cited_by_count=120,
            cited_in_manuscript=True,
            istex_url="https://api.istex.fr/document/AB/fulltext/pdf",
        )
        lines = out.split("<br>")
        assert lines[-2] == "<i>Cited in manuscript</i>"
        assert lines[-1] == "ISTEX PDF: https://api.istex.fr/document/AB/fulltext/pdf"


class TestAllHtmlFigureScriptsEscape:
    """Source-level ratchet against the three defect sites returning verbatim.

    Scope, stated precisely because the class name is broader than what these
    greps can prove: they check that each HTML-emitting figure script *reaches*
    an escaping path, and that the exact interpolations this ticket removed are
    absent. They do not prove any script escapes every sink — a grep cannot.
    A regression reformatted on the way back in (`row.title_short`, or the
    field hoisted to a local) would slip past them.

    The behavioural guarantee lives in `TestEscaping` and `TestStructure`,
    which exercise the shipped builder. This class only stops a verbatim
    revert, which is the cheap failure mode worth a mechanical guard.
    """

    HTML_FIGURE_SCRIPTS = (
        "plot_genealogy_html.py",
        "plot_alluvial_html.py",
        "plot_interactive_corpus.py",
    )

    def test_each_script_reaches_escaping(self):
        offenders = []
        for name in self.HTML_FIGURE_SCRIPTS:
            src = _read_figure_script(name)
            if "html_mod.escape" not in src and "build_hover_text" not in src:
                offenders.append(name)
        assert not offenders, (
            f"HTML-emitting figure scripts with no escaping path: {offenders}"
        )

    def test_plotly_sinks_never_escape_quotes(self):
        """`quote=False` at every Plotly sink, and only at the Plotly sinks.

        Plotly's `convertEntities` cannot decode `&quot;`, so the default
        `quote=True` would corrupt tooltips. The two sibling scripts keep the
        default deliberately — they emit SVG for the browser's own parser —
        so this guard covers the Plotly-fed files only.
        """
        for name in ("_hover_text.py", "plot_interactive_corpus.py"):
            for lineno, line in enumerate(_read_figure_script(name).splitlines(), 1):
                if "html_mod.escape(" not in line or line.lstrip().startswith("#"):
                    continue
                assert "quote=False" in line, (
                    f"{name}:{lineno} escapes quotes; Plotly renders "
                    f"&quot; literally (see _hover_text module docstring): {line.strip()}"
                )

    def test_helper_uses_the_sibling_escape_convention(self):
        with open(os.path.join(FIGURES_DIR, "_hover_text.py"), encoding="utf-8") as f:
            src = f.read()
        assert "import html as html_mod" in src
        assert "html_mod.escape" in src

    def test_interactive_corpus_no_raw_free_text_interpolation(self):
        """The three defect sites are gone: no raw row field inside hover markup."""
        src = _read_figure_script("plot_interactive_corpus.py")
        for field in ("title_short", "first_author", "journal_short"):
            assert f"{{row['{field}']}}" not in src, (
                f"{field} is still interpolated unescaped into hover markup"
            )

    def test_interactive_corpus_legend_label_is_escaped(self):
        """The legend is the same sink as the hover box.

        Plotly renders the trace `name` as HTML too, and the cluster label is
        free text from the generated cluster_labels.json — so an `&` in a
        label corrupts the legend entry exactly as it corrupted the hover box.
        """
        src = _read_figure_script("plot_interactive_corpus.py")
        assert 'name=f"C{cid}: {label}"' not in src, (
            "cluster label interpolated unescaped into the Plotly legend name"
        )
