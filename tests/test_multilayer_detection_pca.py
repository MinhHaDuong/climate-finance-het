"""Tests for #96: Document seed axis PCA decomposition in companion paper.

Sections 5.3 and 5.4 of multilayer-detection.qmd must contain prose
(not [TO WRITE] placeholders) presenting bimodality results and
the PCA decomposition of the seed axis.
"""

import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")

COMPANION = os.path.join(ROOT, "deliverables", "multilayer", "multilayer-detection.qmd")


def read(path):
    with open(path) as f:
        return f.read()


def extract_section(text, heading):
    """Extract text from a ### heading to the next ### or ## heading."""
    pattern = rf"(### {re.escape(heading)}.*?)(?=\n### |\n## |\Z)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else ""


SECTION_53 = "5.3 The efficiency--accountability axis"


class TestSection53:
    """§5.3 must have prose, and must not re-assert the bimodality claim.

    The positive pins this class used to carry ("must present ΔBIC evidence for
    bimodality") were removed under ticket 0345. They violated the project's CI
    polarity rule — positive phrasings break on every legitimate rewrite — and
    in this case they pinned a claim the dip test contradicts. What remains is
    the mechanical placeholder check plus a negative guard.
    """

    def test_no_to_write_placeholder(self):
        text = read(COMPANION)
        section = extract_section(text, SECTION_53)
        assert section, "§5.3 heading not found in multilayer-detection.qmd"
        assert "[TO WRITE" not in section, "§5.3 still contains [TO WRITE] placeholder"

    def test_does_not_claim_bimodality(self):
        """Ticket 0345. Dip p = 1.0 at n ~ 30k; §5.3 must not assert two modes."""
        text = read(COMPANION)
        section = extract_section(text, SECTION_53)
        assert section, "§5.3 heading not found in multilayer-detection.qmd"
        # Only assertive forms. "not two camps" is the correct reading and must
        # stay sayable, so the guard names the words a correct §5.3 cannot use
        # rather than every word that touches the idea.
        offender = re.search(r"bimodal|two clusters|two populations|two distinct",
                             section, re.IGNORECASE)
        assert not offender, (
            f"§5.3 asserts {offender.group(0)!r}, which the dip test does not "
            "support - the axis is a continuum (ticket 0345)"
        )

    def test_reports_the_dip_test(self):
        """The section's load-bearing evidence must not silently disappear."""
        text = read(COMPANION)
        section = extract_section(text, SECTION_53)
        assert "bim_dip_p_embedding" in section, (
            "§5.3 must report the dip-test p-value; without it the section "
            "states a negative conclusion with no evidence behind it"
        )

    def test_statistics_are_vars_driven(self):
        """No hand-typed statistic: every number resolves through a meta var."""
        text = read(COMPANION)
        section = extract_section(text, SECTION_53)
        body = re.sub(r"\{\{<[^>]*>\}\}", "", section)      # drop meta refs
        body = re.sub(r"§?\d\.\d", "", body)                 # drop section numbers
        body = re.sub(r"\b(19|20)\d{2}\b", "", body)         # drop years
        stray = re.findall(r"\d+\.\d+|\b\d{3,}\b", body)
        assert not stray, (
            f"§5.3 hardcodes {stray} - statistics must come from "
            "compute_vars.py, or they rot at the next corpus rebuild"
        )


class TestSection54:
    """§5.4 The divide as PC2, not PC1 must have prose."""

    def test_no_to_write_placeholder(self):
        text = read(COMPANION)
        section = extract_section(text, "5.4 The divide as PC2, not PC1")
        assert section, "§5.4 heading not found in multilayer-detection.qmd"
        assert "[TO WRITE" not in section, "§5.4 still contains [TO WRITE] placeholder"

    def test_mentions_pc1_orthogonal(self):
        text = read(COMPANION)
        section = extract_section(text, "5.4 The divide as PC2, not PC1")
        assert "PC1" in section, "§5.4 must discuss PC1's orthogonality to seed axis"

    def test_mentions_pc2_alignment(self):
        text = read(COMPANION)
        section = extract_section(text, "5.4 The divide as PC2, not PC1")
        assert "PC2" in section, "§5.4 must discuss PC2's alignment with seed axis"

    def test_mentions_variance(self):
        text = read(COMPANION)
        section = extract_section(text, "5.4 The divide as PC2, not PC1")
        assert "variance" in section or "var_pct" in section, (
            "§5.4 must report explained variance"
        )

    def test_mentions_erratum(self):
        """The ticket requires documenting the corrected values."""
        text = read(COMPANION)
        section = extract_section(text, "5.4 The divide as PC2, not PC1")
        assert (
            "earlier" in section.lower()
            or "previous" in section.lower()
            or "corrected" in section.lower()
            or "erratum" in section.lower()
        ), "§5.4 must note the correction of earlier reported values"
