"""Undated works must not be ranked on an invented publication year (ticket 0402).

`build_het_core.py` scores the corpus and writes `het_mostcited_50.csv`, which
`summarize_core_venues.py` and `export_core_venues_markdown.py` carry into the
published `tab_core_venues_top10.md`. So the age term in that score reaches a
table in the paper.

Found by the ticket-0354 wrap-up sweep for the silent-coercion class: this is the
same class one step worse — the deposit gate emptied an unparseable value, this
fabricated one.
"""

import re

import numpy as np
import pandas as pd
import pytest
from analysis.build_het_core import citations_per_year, parse_years


class TestParseYears:
    def test_blank_year_stays_undated(self):
        """The defect, at its source: a missing year must not become a number."""
        out = parse_years(pd.Series(["2001", "", "  ", "1998"]))
        assert out.isna().tolist() == [False, True, True, False]
        assert out.dropna().tolist() == [2001, 1998]

    def test_non_numeric_year_is_refused(self):
        """Blank is a gap; 'n.d.' is a fault. They are not the same input."""
        with pytest.raises((ValueError, TypeError)):
            parse_years(pd.Series(["2001", "n.d."]))


class TestCitationsPerYear:
    def _rate(self, cited, years):
        return citations_per_year(
            pd.Series(cited, dtype=float),
            parse_years(pd.Series(years)),
            current_year=2026,
        )

    def test_undated_work_does_not_outrank_a_dated_peer(self):
        """The ranking consequence, stated as a comparison.

        Two works, eight citations each: one published in 1995, one undated.
        Under the old imputation the undated work was treated as six years old
        and scored ~5x the rate of the 31-year-old one, purely because its year
        was missing.
        """
        rate = self._rate([8.0, 8.0], ["1995", ""])
        dated, undated = rate.iloc[0], rate.iloc[1]
        assert undated <= dated, (
            f"undated work scores {undated} against {dated} for the same "
            "citation count — a missing year must not be an advantage"
        )

    def test_undated_work_forfeits_only_the_age_term(self):
        assert self._rate([8.0], [""]).tolist() == [0.0]

    def test_dated_rate_is_citations_over_age(self):
        assert self._rate([62.0], ["2010"]).tolist() == [62.0 / 16]

    def test_age_floor_keeps_the_current_year_finite(self):
        """A work published this year divides by 1, not 0."""
        assert np.isfinite(self._rate([5.0], ["2026"]).iloc[0])
        assert self._rate([5.0], ["2026"]).tolist() == [5.0]


@pytest.mark.adherence
class TestNoYearImputationSurvives:
    """The call sites, not just the helpers.

    The helpers above are correct by construction; what regressed once and could
    regress again is `main()` reaching for a literal year instead of them. Read
    the source rather than run the pipeline: this needs no corpus and no
    subprocess, and the defect is lexically stable.
    """

    def _source(self):
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts", "analysis", "build_het_core.py",
        )
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_no_literal_year_is_substituted_for_a_missing_one(self):
        src = self._source()
        offenders = re.findall(r"fillna\(\s*(1[89]\d\d|2[01]\d\d)\s*\)", src)
        assert not offenders, (
            f"build_het_core.py substitutes literal year(s) {offenders} for a "
            "missing publication year. That value feeds cit_per_year, hence the "
            "score, hence which works reach the published venues table — use "
            "parse_years/citations_per_year, which leave an unknown age unknown."
        )

    def test_main_scores_through_the_helper(self):
        src = self._source()
        assert "citations_per_year(" in src, (
            "the age-normalised term must be computed by citations_per_year, so "
            "the undated-work policy lives in one place"
        )
        assert "parse_years(" in src, "years must be parsed by parse_years"
