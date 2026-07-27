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
    """Exit criterion 0341: all three HTML-emitting figure scripts escape free text.

    A negative ratchet, not a positive phrasing pin: each script either escapes
    in its own source (`html_mod.escape`, the convention the two siblings
    established) or delegates to the escaping builder. Stripping escaping from
    any of the three fails this test.
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
