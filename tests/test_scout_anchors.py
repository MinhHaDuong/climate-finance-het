"""Guard the scout_tradition_coupling ANCHORS dict against fabricated DOIs.

The @tbl-traditions anchors carry a (doi, title) fresh-embed fallback key. A
fabricated DOI here fetches the wrong paper's metadata for the embedding
fallback -- a silent correctness defect, not just dead metadata. Ticket 0188
(#928) removed the same LLM-fabricated string from main.bib; the standing
DOI-title audit only scans main.bib, so this Python-dict instance needs its
own guard (ticket 0201).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import scout_tradition_coupling as scout

# 0188 (#928): resolves to an unrelated energy-demand paper. manne_richels1992
# is the 1992 MIT Press *book*, which has no Crossref DOI.
FABRICATED_DOI = "10.1016/0301-4215(92)90024-V"


def _iter_anchor_dois():
    """Yield (tradition, citekey, doi) over every ANCHORS entry."""
    for tradition, entries in scout.ANCHORS.items():
        for citekey, (doi, _title) in entries.items():
            yield tradition, citekey, doi


def test_no_fabricated_doi_in_anchors():
    """No ANCHORS entry may carry the known-fabricated DOI string."""
    offenders = [
        f"{tradition}.{citekey}"
        for tradition, citekey, doi in _iter_anchor_dois()
        if doi == FABRICATED_DOI
    ]
    assert not offenders, (
        f"Fabricated DOI {FABRICATED_DOI} still present in ANCHORS: {offenders}"
    )


def test_manne_richels1992_has_no_doi():
    """manne_richels1992 is a book: no DOI, full book title for fresh-embed."""
    doi, title = scout.ANCHORS["env_econ"]["manne_richels1992"]
    assert doi is None, f"manne_richels1992 should have no DOI, got {doi!r}"
    assert title == (
        "Buying Greenhouse Insurance: The Economic Costs of CO2 Emission Limits"
    ), f"manne_richels1992 title should be the full book title, got {title!r}"
