"""NaN in pandas rows must not become the literal text 'nan' (ticket 0550)."""

import re

import numpy as np
import pandas as pd
import pipeline_text
import pytest
from analysis.build_het_core import text_blob
from figures import plot_genealogy_html

pytestmark = pytest.mark.wp_corpus

def test_text_or_empty_handles_missing_scalars():
    assert [pipeline_text.text_or_empty(v) for v in (None, np.nan, pd.NA, "nan", "None")] == [""] * 5
    assert pipeline_text.text_or_empty("  A title  ") == "A title"


def test_text_blob_does_not_embed_nan():
    row = pd.DataFrame({"title": ["Climate finance", np.nan], "abstract": [None, "finance"], "keywords": [np.nan, None]}).iloc[1]
    assert text_blob(row) == " finance "


def test_written_genealogy_html_does_not_show_nan(tmp_path):
    source = tmp_path / "lineages.csv"
    pd.DataFrame({"doi": ["10.1/example"], "lineage": [0], "x": [0.5], "y": [0.5], "year": [2020], "cited_by_count": [1], "title": [np.nan], "first_author": [np.nan]}).to_csv(source, index=False)
    model = plot_genealogy_html.load_model(source)
    output = tmp_path / "genealogy.html"
    plot_genealogy_html.render_html(*model, [], output)
    assert not re.search(r"\bnan\b", output.read_text(), flags=re.IGNORECASE)
