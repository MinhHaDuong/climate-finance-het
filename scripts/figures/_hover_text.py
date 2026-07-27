"""Plotly hover-box text for the interactive corpus figure (ticket 0341).

The hover box is raw HTML: the `<b>`, `<br>` and `<i>` tags are deliberate
markup that Plotly renders. Everything interpolated into it is free
bibliographic text, so it is escaped first — an `&` in a journal name
("Energy Research & Social Science") or a `<` in a title would otherwise
corrupt the box. Same convention, same `html_mod` alias, as the sibling
HTML figure scripts `plot_genealogy_html.py` and `plot_alluvial_html.py`.

Lives in its own module because `plot_interactive_corpus.py` runs its whole
pipeline at module scope, so a builder defined there could not be imported
by a test without executing that pipeline.
"""

import html as html_mod


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
        f"<b>{html_mod.escape(str(title))}</b>",
        f"{html_mod.escape(str(first_author))} ({int(year)})",
        html_mod.escape(str(journal)),
        f"Cited by: {int(cited_by_count)}",
    ]
    if cited_in_manuscript:
        lines.append("<i>Cited in manuscript</i>")
    if istex_url:
        lines.append(f"ISTEX PDF: {html_mod.escape(str(istex_url))}")
    return "<br>".join(lines)
