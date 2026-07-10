"""Guard the bib DOI↔title accuracy class (ticket 0164).

Two layers:

* Fast unit tests pin the matching logic — subtitle-truncation tolerance,
  LaTeX-accent folding, corporate-author skipping — so the audit's false-positive
  suppressions cannot silently regress. These run in ``make check-fast``.

* One ``@slow`` test runs the live Crossref audit over the whole bib and asserts
  that no DOI-bearing entry resolves to the wrong paper (or fails to resolve),
  except the entries explicitly allowlisted below. It skips when Crossref is
  unreachable so an offline ``make check`` still passes.

The author-name sub-class is deliberately *advisory* (see ``qa_bib_doi``): first
-author surname matching is too noisy (compound surnames, name order) to gate CI.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# qa_bib_doi imports bibtexparser, which lives in the Phase-1 `corpus`
# dependency-group (not installed on Phase-2/3 hosts like doudou). Skip the whole
# module cleanly there instead of erroring collection.
pytest.importorskip("bibtexparser")

from qa_bib_doi import (
    author_mismatch,
    first_author_surname,
    normalize_title,
    run_audit,
    suspects,
    title_ratio,
)

# DOI-bearing entries whose Crossref title does NOT match — each a known
# LLM-fabricated identifier awaiting an author judgment call. Empty since 0188
# resolved the last three (manne → 1992 MIT Press book, no DOI; atwoli → BMJ
# 10.1136/bmj.n1734; min → real 2021 techfore DOI). A new key here means a new
# defect; the gate below is now unallowlisted.
KNOWN_WRONG_PAPER: dict[str, str] = {}


def test_subtitle_truncation_is_a_match():
    """Crossref dropping a subtitle must not read as a wrong paper."""
    bib = "Climate Finance Shadow Report 2023: Assessing the Delivery"
    crossref = "Climate Finance Shadow Report 2023"
    assert title_ratio(bib, crossref) == 1.0


def test_period_subtitle_truncation_is_a_match():
    bib = "Optimalite, equite et prix du carbone. A propos de Hotelling"
    crossref = "Optimalite, equite et prix du carbone"
    assert title_ratio(bib, crossref) == 1.0


def test_short_generic_prefix_is_not_a_full_match():
    """A short bib title prefixing an unrelated longer one must not read as 1.0,
    or a wrong DOI on a generic title would pass the hard WRONG_PAPER gate."""
    assert title_ratio("Climate Policy", "Climate Policy in the EU") < 1.0


def test_genuinely_different_titles_score_low():
    ratio = title_ratio("Buying Greenhouse Insurance",
                        "A comparison of aggregate energy demand models")
    assert ratio < 0.6


def test_latex_accent_folds_in_surname():
    assert first_author_surname(r"Barab{\'a}si, Albert-L{\'a}szl{\'o}") == "barabasi"


def test_corporate_author_yields_no_surname():
    """A braced organisation author has no personal surname to compare."""
    assert first_author_surname("{Nature Climate Change}") == ""


def test_normalize_title_strips_latex_and_case():
    assert normalize_title("Latent {Dirichlet} Allocation") == "latent dirichlet allocation"


def test_short_surname_swap_is_flagged():
    """'li' vs 'lin' are different authors — the old substring test hid this
    (ticket 0196: surname-token equality, not containment)."""
    assert author_mismatch("li", "lin")


def test_identical_surnames_not_flagged():
    assert not author_mismatch("buchner", "buchner")


def test_latex_accent_surnames_fold_equal():
    """Accent/LaTeX-only differences are not an author mismatch."""
    assert not author_mismatch(r"Barab{\'a}si", "barabasi")


def test_missing_surname_is_not_a_mismatch():
    """A corporate author (no surname) or an authorless Crossref record: skip."""
    assert not author_mismatch("", "smith")
    assert not author_mismatch("smith", "")


def test_dropped_particle_is_not_a_mismatch():
    """'First Last' bib order keeps only the trailing token ('berg'); Crossref
    keeps the particle ('van der berg'). The shared tail matches — no false flag
    (ticket 0196 gaze finding: don't turn the tightening into particle noise)."""
    assert not author_mismatch("berg", "van der berg")
    assert not author_mismatch("van der berg", "berg")


def test_genuinely_different_surnames_are_flagged():
    assert author_mismatch("smith", "jones")


@pytest.mark.slow
def test_every_bib_doi_resolves_to_the_right_paper():
    """Live Crossref audit: no entry's DOI points at the wrong paper.

    Skips if Crossref is broadly unreachable (offline CI).
    """
    rows = run_audit(delay=0.1)
    checked = [r for r in rows if r["verdict"] != "NO_DOI"
               and r["verdict"] != "SKIP_REGISTRAR"]
    errors = [r for r in checked if r["verdict"] == "NETWORK_ERROR"]
    if not checked or len(errors) > 0.1 * len(checked):
        pytest.skip(f"Crossref unreachable ({len(errors)}/{len(checked)} errored)")

    offenders = {r["key"] for r in suspects(rows)} - set(KNOWN_WRONG_PAPER)
    assert not offenders, (
        "bib DOIs resolving to the wrong paper (not in the 0188 allowlist): "
        f"{sorted(offenders)}"
    )
