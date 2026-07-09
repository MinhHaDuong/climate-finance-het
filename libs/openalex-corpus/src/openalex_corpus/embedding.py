"""Canonical embedding-text convention — the string that represents a work.

Model-agnostic: this decides *what text* stands for a work (title + abstract +
keywords, minus boilerplate), independent of which embedding model consumes it.
Depends on pandas only for NaN handling in ``build_text``.
"""

import pandas as pd


def is_boilerplate_abstract(abstract: object, title: str | None = None) -> bool:
    """Return True if abstract is boilerplate/junk that should be skipped.

    Detects repository metadata strings, known boilerplate phrases,
    title-as-abstract duplication, and short ALL CAPS fragments (truncated titles).
    """
    if not abstract or len(str(abstract).strip()) < 30:
        return True
    low = str(abstract).strip().lower()
    # Known boilerplate phrases (exact match after lowering)
    boilerplate = {"international audience", "editorial reviewed", "peer reviewed"}
    if low in boilerplate:
        return True
    # Repository metadata URIs
    if low.startswith("info:eu-repo/"):
        return True
    # Abstract is just the title repeated
    if title and low == str(title).strip().lower():
        return True
    # Paywall / publisher stub abstracts (#455)
    if low.startswith("no access"):
        return True
    if "10.5751/es-" in low and len(low) < 500:
        return True
    if "not available for this content" in low:
        return True
    # Short ALL CAPS text — truncated title fragments (e.g. "AZRBAYCANDA YAIL")
    stripped = str(abstract).strip()
    if len(stripped) < 50 and stripped == stripped.upper() and not stripped.islower():
        return True
    return False


def build_text(row: pd.Series) -> str:
    """Concatenate title, abstract, and keywords for embedding.

    Skips boilerplate abstracts (repository metadata, known junk phrases,
    title duplication) so they don't pollute embeddings.
    """
    title = str(row["title"])
    parts = [title]
    abstract = row.get("abstract")
    if pd.notna(abstract) and not is_boilerplate_abstract(str(abstract), title=title):
        parts.append(str(abstract))
    keywords = row.get("keywords")
    if pd.notna(keywords):
        parts.append(str(keywords).replace(";", ", "))
    return ". ".join(parts)
