"""Resolve one frozen M1a inventory row to the source document it came from.

Two steps, kept apart because they fail for different reasons: collapsing the
collection registry to one entry per source identifier, and reading a page
number out of an evidence locator.  ``app.js`` carries a hand-written port of
both for the Inventories page; ``tests/test_jetp_observatory_inventories.py``
pins the strings that must stay in step.
"""

import re
from collections.abc import Iterable, Mapping

# The Viet Nam locators are the only ones that publish a PDF page, and they
# publish three numbers: ``PDF pages 156; printed pages 140; ordinal 22``.  Only
# the first addresses the archived file, so the pattern is anchored on its own
# label rather than on "the first number in the string".  ``[0-9]`` rather than
# ``\d``, which in Python matches every Unicode decimal and in JavaScript only
# ASCII: the hand-written port in ``app.js`` would then read an OCR'd fullwidth
# digit differently from this module.
PDF_PAGE = re.compile(r"PDF pages? ([0-9]+)")


def index_documents(documents: Iterable[Mapping[str, object]]) -> dict[str, dict]:
    """Collapse the collection registry to one entry per source identifier.

    A source identifier can carry several collection attempts (ticket 0853: 21
    of them do), and a row link has to open one file.  The winner is the
    attempt whose bytes are on disk — ``collected`` with a ``local_path`` —
    because it is the only one whose link resolves to a document.  Where no
    attempt was archived, the first entry is kept so the identifier still
    resolves and the page can show what the collection recorded instead.
    """
    by_id: dict[str, list[Mapping[str, object]]] = {}
    for entry in documents:
        by_id.setdefault(str(entry["id"]), []).append(entry)
    index: dict[str, dict] = {}
    for source_id, entries in by_id.items():
        archived = [entry for entry in entries if entry.get("local_path")]
        collected = [entry for entry in archived if entry.get("status") == "collected"]
        chosen = (collected or archived or entries)[0]
        index[source_id] = dict(chosen)
    return index


def resolve_document_link(
    source_id: str,
    evidence_locator: str,
    registry: Mapping[str, Mapping[str, object]],
    *,
    required: bool = True,
) -> dict[str, object]:
    """Resolve one inventory row to its document fingerprint and PDF page.

    Raises ``KeyError`` when the identifier is absent from the registry: a row
    whose source was never collected is a registry gap to repair, not a link to
    render blank.  The ledger observations view (ticket 0838) is the one caller
    that passes ``required=False``: there a never-collected source resolves to
    a null fingerprint, so the gap stays visible on the page instead of
    emptying a country.
    """
    entry = registry[source_id] if required else registry.get(source_id, {})
    match = PDF_PAGE.search(evidence_locator or "")
    return {
        "sha256": entry.get("sha256"),
        "pdf_page": int(match.group(1)) if match else None,
        "local_path": entry.get("local_path"),
    }
