"""Plotly hover-box text for the interactive corpus figure (ticket 0341).

The hover box is raw HTML: the `<b>`, `<br>` and `<i>` tags are deliberate
markup that Plotly renders. Everything interpolated into it is free
bibliographic text, so it is escaped first — an `&` in a journal name
("Energy Research & Social Science") or a `<` in a title would otherwise
corrupt the box. Same convention, same `html_mod` alias, as the sibling
HTML figure scripts `plot_genealogy_html.py` and `plot_alluvial_html.py`.
`_esc` is also imported directly by `plot_interactive_corpus.py` for the one
non-hover-box sink, the Plotly legend trace name, so the escaping rule lives
in one place rather than being re-implemented at each call site.

`quote=False` is load-bearing, and is where this module must NOT follow the
siblings. They emit SVG/HTML for the browser's own parser, which knows the
full entity set. Plotly does not hand hover `text` or a trace `name` to that
parser; it runs its own `convertEntities`, whose named-entity table has eight
members — `mu amp lt gt nbsp times plusmn deg` — plus a numeric `&#…;`
branch. `quot` is not among them, so `html.escape`'s default `quote=True`
would put a literal `&quot;` in the tooltip for every title carrying a double
quote (23 of the 2,644 core rows, e.g. `Assessing "Dangerous Climate
Change"`). Apostrophes are safe either way: `html.escape` emits the numeric
`&#x27;`, which the numeric branch decodes. Leaving `"` and `'` literal is
also safe — the strings reach the page as JSON payload values, not as HTML
attribute values.

Lives in its own module because `plot_interactive_corpus.py` runs its whole
pipeline at module scope, so a builder defined there could not be imported
by a test without executing that pipeline.
"""

import html as html_mod


def _esc(value) -> str:
    """Escape `&`, `<` and `>` only — see the module docstring on `quote`."""
    return html_mod.escape(str(value), quote=False)


def build_hover_text(
    *,
    title: str,
    first_author: str,
    year: int,
    journal: str,
    cited_by_count: int,
    cited_in_manuscript: bool = False,
    istex_url: str = "",
) -> str:
    """Return the `<br>`-joined hover box for one paper, free text escaped.

    `title`, `first_author`, `journal` and `istex_url` are escaped; the
    structural tags around them are not. `year` and `cited_by_count` are
    rendered as integers and need no escaping.
    """
    lines = [
        f"<b>{_esc(title)}</b>",
        f"{_esc(first_author)} ({int(year)})",
        _esc(journal),
        f"Cited by: {int(cited_by_count)}",
    ]
    if cited_in_manuscript:
        lines.append("<i>Cited in manuscript</i>")
    if istex_url:
        lines.append(f"ISTEX PDF: {_esc(istex_url)}")
    return "<br>".join(lines)
