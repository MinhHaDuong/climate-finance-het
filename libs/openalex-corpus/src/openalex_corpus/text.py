"""Pure OpenAlex text conventions — no I/O, no env, stdlib only.

These functions are the model-agnostic canonical-text layer shared by any
pipeline that crawls OpenAlex and builds a text representation of a work.
They are deliberately dependency-free (no pandas, no requests) so they can be
imported in any context.
"""


def reconstruct_abstract(inverted_index: dict | None) -> str:
    """Rebuild plain text from an OpenAlex abstract_inverted_index dict."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)


def normalize_doi(doi_raw: str | list | None) -> str:
    """Normalize a DOI: handle lists, strip URL prefix, lowercase, trim."""
    if doi_raw is None:
        return ""
    if isinstance(doi_raw, list):
        if not doi_raw:
            return ""
        doi_raw = doi_raw[0]
    doi = str(doi_raw).strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/",
                   "https://dx.doi.org/", "doi:"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi.strip().lower()
