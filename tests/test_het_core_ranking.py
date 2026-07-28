"""Undated works must not be ranked on an invented publication year (ticket 0402).

`build_het_core.py` scores the corpus and writes `het_mostcited_50.csv`, which
`summarize_core_venues.py` and `export_core_venues_markdown.py` turn into
`tab_core_venues_top10.md`. That table is rendered by no document — it has a Make
rule and no consumer — so the defect this pins reached no published number. What
it did reach is the selection: 43 of the 1000 chosen works swapped when it was
fixed.

Found by the ticket-0354 wrap-up sweep for the silent-coercion class: this is the
same class one step worse — the deposit gate emptied an unparseable value, this
fabricated one.
"""

import ast
import os

import numpy as np
import pandas as pd
import pytest
from analysis.build_het_core import citations_per_year, parse_years

YEAR_MIN, YEAR_MAX = 1800, 2100


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
    regress again is `main()` reaching for a literal year instead of them.

    Read the syntax tree, not the text. The first version of this guard grepped
    for `fillna(2020)` and a review reproduced the bypass live: `fillna(2020.0)`,
    `fillna(value=2020)`, `fillna(CURRENT_YEAR)` and an `np.where` all
    reintroduced the defect with the guard still green. A regex over source text
    cannot cover the ways one expression can be written; the AST collapses them.
    """

    def _tree(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts", "analysis", "build_het_core.py",
        )
        with open(path, encoding="utf-8") as f:
            return ast.parse(f.read()), f.name

    @staticmethod
    def _is_year_like(node):
        """A literal year, or the module's own CURRENT_YEAR."""
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return YEAR_MIN <= float(node.value) <= YEAR_MAX
        return isinstance(node, ast.Name) and node.id == "CURRENT_YEAR"

    def test_no_year_is_substituted_for_a_missing_one(self):
        """No `fillna` anywhere may supply a year-shaped value.

        Positional or keyword, int or float, literal or CURRENT_YEAR — every
        spelling reaches the same AST shape, so one check covers them all.
        """
        tree, _ = self._tree()
        offenders = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "fillna"):
                continue
            supplied = list(node.args) + [kw.value for kw in node.keywords]
            for arg in supplied:
                if self._is_year_like(arg):
                    offenders.append((node.lineno, ast.unparse(node)[:70]))
        assert not offenders, (
            "build_het_core.py substitutes a year-shaped value for a missing "
            f"publication year at {offenders}. That value feeds cit_per_year, "
            "hence the score, hence which works the ranking selects — use "
            "parse_years/citations_per_year, which leave an unknown age unknown."
        )

    def test_year_num_is_only_ever_parse_years(self):
        """Closes the np.where route: nothing else may produce `year_num`.

        A guard on `fillna` alone still lets
        `df["year_num"] = np.where(df["year"] == "", 2020, ...)` through, so the
        column's provenance is pinned instead of one function's absence.
        """
        tree, _ = self._tree()
        bad = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {ast.unparse(t) for t in targets}
            if not any("year_num" in n for n in names):
                continue
            value = node.value
            ok = (isinstance(value, ast.Call)
                  and isinstance(value.func, ast.Name)
                  and value.func.id == "parse_years")
            if not ok:
                bad.append((node.lineno, ast.unparse(node)[:70]))
        assert not bad, (
            "`year_num` must come from parse_years and nothing else, so the "
            f"undated-work policy has one home; found {bad}"
        )

    def test_main_scores_through_the_helper(self):
        tree, _ = self._tree()
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        assert "citations_per_year" in called, (
            "the age-normalised term must be computed by citations_per_year, so "
            "the undated-work policy lives in one place")
        assert "parse_years" in called, "years must be parsed by parse_years"
