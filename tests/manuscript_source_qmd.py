"""Shared accessors for the Quarto manuscript source (ticket 0147).

``deliverables/manuscript/manuscript.qmd`` is Quarto Markdown: a YAML front-matter block,
then prose interleaved with HTML comments, fenced code, Quarto shortcodes
(``{{< meta ... >}}``), pipe tables, and blockquotes. The prose-adherence
guards in ``test_manuscript_prose.py`` must scan authored prose only, so this
module exposes a *cleaned* view where non-prose surface is removed:

- the leading YAML front-matter (``--- ... ---``) is dropped;
- HTML comments ``<!-- ... -->`` are dropped (source-maintenance notes,
  e.g. the Phase 2→3 contract block, are not prose);
- fenced code blocks (```` ``` ... ``` ````) are dropped;
- Quarto shortcodes ``{{< ... >}}`` are dropped — the value they expand to is
  a number, not authored wording;
- pipe-table rows (lines beginning ``|``) and blockquote lines (``>``) are
  dropped: tabular and quoted material, not prose. This mirrors AEDIST's
  exclusion of ``longtable`` and ``quote`` environments, and crucially keeps
  table column-separator runs (``|:---|``) from being miscounted as em dashes.

Structural Markdown (headings ``##``, ``**bold**``, ``*emph*``, ``@refs``) is
kept intact: the guards anchor on it.
"""

import functools
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT = REPO_ROOT / "deliverables" / "manuscript" / "manuscript.qmd"

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCED_CODE_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
_SHORTCODE_RE = re.compile(r"\{\{<.*?>\}\}")
# A non-prose line: a pipe-table row or a blockquote.
_NON_PROSE_LINE_RE = re.compile(r"^\s*[|>]")
# ATX headings, levels 2–4 (## / ### / ####): "## 1. Before Climate Finance".
_HEADING_RE = re.compile(r"^(#{2,4})\s+(.*?)\s*$", re.MULTILINE)


def raw() -> str:
    """The full manuscript.qmd source, exactly as committed."""
    if not MANUSCRIPT.exists():
        pytest.skip("deliverables/manuscript/manuscript.qmd not found")
    return MANUSCRIPT.read_text(encoding="utf-8")


def strip_frontmatter(text: str) -> str:
    """Drop the leading YAML front-matter block."""
    return _FRONTMATTER_RE.sub("", text, count=1)


def strip_comments(text: str) -> str:
    """Drop HTML comments."""
    return _HTML_COMMENT_RE.sub("", text)


def clean(text: str) -> str:
    """Reduce raw .qmd to authored prose (see module docstring)."""
    text = strip_frontmatter(text)
    text = strip_comments(text)
    text = _FENCED_CODE_RE.sub("", text)
    text = _SHORTCODE_RE.sub("", text)
    return "\n".join(
        line for line in text.splitlines() if not _NON_PROSE_LINE_RE.match(line)
    )


@functools.lru_cache(maxsize=1)
def body() -> str:
    """Cleaned manuscript prose — the standard surface for prose guards."""
    return clean(raw())


def paragraphs() -> list[str]:
    """Blank-line-delimited blocks of the cleaned body, stripped, non-empty."""
    return [block.strip() for block in re.split(r"\n\s*\n", body()) if block.strip()]


def section(heading: str) -> str:
    """Cleaned text of the section whose ATX heading contains ``heading``.

    The slice runs from the matching ``##``/``###``/``####`` heading to the
    next heading of equal-or-higher level (or the end of the body), so a
    ``##`` slice contains its ``###`` subsections. Matching is by substring on
    the heading text, so "1.5 Corpus evidence" finds "### 1.5 Corpus evidence".
    """
    text = body()
    matches = list(_HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        if heading in m.group(2):
            level = len(m.group(1))
            end = len(text)
            for nxt in matches[i + 1 :]:
                if len(nxt.group(1)) <= level:
                    end = nxt.start()
                    break
            return text[m.start() : end]
    raise AssertionError(
        f"no ATX heading containing {heading!r} in manuscript.qmd; "
        f"headings present: {[m.group(2) for m in matches]}"
    )


def abstract() -> str:
    """The English ``**Abstract.**`` paragraph of the manuscript."""
    for para in paragraphs():
        if para.lstrip().startswith("**Abstract.**"):
            return para
    raise AssertionError("no **Abstract.** paragraph found in manuscript.qmd")
