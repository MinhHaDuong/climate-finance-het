"""The REL window extends collection without moving existing analyses."""

import pandas as pd
import pytest
import yaml
from pipeline_loaders import (
    classify_rel_review_works,
    load_analysis_config,
    load_collect_config,
    load_rel_review_config,
    select_rel_review_works,
)

pytestmark = pytest.mark.wp_corpus


def test_windows_and_dvc_dependencies():
    assert load_collect_config()["year_max"] == 2026
    assert load_analysis_config()["periodization"]["year_max"] == 2024
    assert load_rel_review_config()["last_complete_year"] == 2025
    assert load_rel_review_config()["partial_year"] == 2026
    with open("dvc.yaml", encoding="utf-8") as f:
        stages = yaml.safe_load(f)["stages"]
    for stage in ("enrich_embeddings", "extend"):
        assert "config/corpus_collect.yaml" in stages[stage]["deps"]


def test_rel_includes_2025_and_pre_cutoff_2026_articles_and_working_papers():
    works = pd.DataFrame([
        {"title": "Earlier study", "year": 2024, "type": "article",
         "publication_date": "2024-06-01"},
        {"title": "Journal study", "year": 2025, "type": "article",
         "publication_date": "2025-05-01"},
        {"title": "Recent working paper", "year": 2026, "type": "working-paper",
         "publication_date": "2026-09-15"},
        {"title": "Year-only working paper", "year": 2026,
         "type": "working-paper", "publication_date": None},
        {"title": "Future 2026 journal", "year": 2026, "type": "article",
         "publication_date": "2026-12-01"},
        {"title": "Future 2027 journal", "year": 2027, "type": "article",
         "publication_date": "2027-01-01"},
    ])
    selected = select_rel_review_works(works)
    assert selected["title"].tolist() == [
        "Earlier study", "Journal study", "Recent working paper",
    ]
    assert selected["rel_year_status"].tolist() == [
        "complete", "complete", "partial",
    ]
    assert selected["rel_date_precision"].tolist() == [
        "full_date", "full_date", "full_date",
    ]
    assert set(selected["rel_search_date"]) == {"2026-09-28"}
    classified = classify_rel_review_works(works)
    assert classified["rel_disposition"].tolist() == [
        "include", "include", "include", "quarantine_unverified_partial_date",
        "exclude_future_date", "exclude_future_date",
    ]


def test_rel_accepts_canonical_year_only_schema():
    works = pd.DataFrame({"title": ["Paper", "Later"], "year": [2026, 2027]})
    selected = select_rel_review_works(works)
    assert selected.empty  # queued for date verification


def test_mixed_date_precision_does_not_hide_future_publications():
    works = pd.DataFrame({
        "title": ["Year only", "Before cutoff", "After cutoff", "Bad date"],
        "year": [2026] * 4,
        "publication_date": ["2026", "2026-09-01", "2026-12-01", "unknown"],
    })
    selected = select_rel_review_works(works)
    assert selected["title"].tolist() == ["Before cutoff"]
    assert selected["rel_date_precision"].tolist() == ["full_date"]


def test_phase1_embedding_and_semantic_filter_include_2026():
    from harvest.corpus_filter import _flag5_subset
    from harvest.enrich_embeddings import select_works_to_embed

    works = pd.DataFrame({
        "title": ["Older", "Current", "Future"],
        "year": [2025, 2026, 2027],
        "abstract": ["A" * 60] * 3,
    })
    assert select_works_to_embed(works)["year"].tolist() == [2025, 2026]
    _, flagged = _flag5_subset(works)
    assert flagged["year"].tolist() == [2025, 2026]


def test_existing_analysis_corpus_stays_at_2024(monkeypatch):
    import pipeline_loaders

    works = pd.DataFrame({
        "title": ["Earlier", "Recent", "Current"],
        "year": [2024, 2025, 2026],
    })
    monkeypatch.setattr(pipeline_loaders, "load_refined_works", lambda: works)
    analyzed, embeddings = pipeline_loaders.load_analysis_corpus(
        with_embeddings=False)
    assert analyzed["year"].tolist() == [2024]
    assert embeddings is None
