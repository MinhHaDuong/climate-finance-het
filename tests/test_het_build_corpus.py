"""Unit tests for het_build_corpus.py (pure logic, no real network calls)."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import het_build_corpus as hbc


def test_record_from_json_reconstructs_abstract_and_keywords():
    w = {
        "id": "https://openalex.org/W123",
        "doi": "https://doi.org/10.1234/x",
        "title": "A Title",
        "publication_year": 1958,
        "abstract_inverted_index": {"Hello": [0], "world": [1]},
        "referenced_works": ["https://openalex.org/W1", "https://openalex.org/W2"],
        "concepts": [
            {"display_name": "Graph theory", "score": 0.9},
            {"display_name": "Economics", "score": 0.5},
        ],
    }
    rec = hbc.record_from_json(w)
    assert rec["openalex_id"] == "https://openalex.org/W123"
    assert rec["doi"] == "10.1234/x"
    assert rec["abstract"] == "Hello world"
    assert rec["keywords"] == "Graph theory; Economics"
    assert rec["year"] == 1958
    assert rec["referenced_works"] == ["https://openalex.org/W1", "https://openalex.org/W2"]


def test_record_from_json_handles_missing_fields():
    rec = hbc.record_from_json({"id": "https://openalex.org/W9", "display_name": "Fallback title"})
    assert rec["title"] == "Fallback title"
    assert rec["abstract"] == ""
    assert rec["keywords"] == ""
    assert rec["referenced_works"] == []


def test_cache_round_trip(tmp_path):
    path = tmp_path / "pool" / "works_cache.jsonl"
    cache = hbc.Cache(str(path))
    rec = {"openalex_id": "W1", "doi": "10.1/a", "title": "T", "abstract": "",
           "keywords": "", "year": 2000, "referenced_works": []}
    cache.put(rec)
    cache.close()

    reloaded = hbc.Cache(str(path))
    assert reloaded.get("W1") == rec
    assert reloaded.get("missing") is None


def test_cache_put_is_idempotent_on_disk(tmp_path):
    path = tmp_path / "pool" / "works_cache.jsonl"
    cache = hbc.Cache(str(path))
    rec = {"openalex_id": "W1", "doi": "", "title": "T", "abstract": "",
           "keywords": "", "year": None, "referenced_works": []}
    cache.put(rec)
    cache.put(rec)  # duplicate put must not double-append
    cache.close()

    with open(path, encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0]) == rec


def test_resolve_by_doi_returns_none_on_404(monkeypatch):
    class FakeResp:
        status_code = 404

    monkeypatch.setattr(hbc, "retry_get", lambda *a, **k: FakeResp())
    assert hbc.resolve_by_doi("10.9999/missing", delay=0.0) is None


def test_resolve_by_title_picks_best_match(monkeypatch):
    class FakeResp:
        status_code = 200

        def json(self):
            return {
                "results": [
                    {"title": "Something Unrelated", "id": "W-bad"},
                    {"title": "Maximum-Minimum Saetze ueber Graphen", "id": "W-good"},
                ]
            }

    monkeypatch.setattr(hbc, "retry_get", lambda *a, **k: FakeResp())
    rec, score = hbc.resolve_by_title("Maximum-Minimum Satze uber Graphen", delay=0.0)
    assert rec["openalex_id"] == "W-good"
    assert score > hbc.TITLE_MATCH_THRESHOLD


def test_resolve_by_title_rejects_weak_matches(monkeypatch):
    class FakeResp:
        status_code = 200

        def json(self):
            return {"results": [{"title": "Completely different paper", "id": "W-x"}]}

    monkeypatch.setattr(hbc, "retry_get", lambda *a, **k: FakeResp())
    rec, score = hbc.resolve_by_title("Maximum-Minimum Satze uber Graphen", delay=0.0)
    assert rec is None


def test_batch_resolve_skips_already_cached(tmp_path, monkeypatch):
    path = tmp_path / "pool" / "works_cache.jsonl"
    cache = hbc.Cache(str(path))
    cache.put({"openalex_id": "https://openalex.org/W1", "doi": "", "title": "cached",
               "abstract": "", "keywords": "", "year": None, "referenced_works": []})

    calls = []

    class FakeResp:
        status_code = 200

        def json(self):
            return {"results": [
                {"id": "https://openalex.org/W2", "title": "fetched", "publication_year": 2001,
                 "referenced_works": []},
            ]}

    def fake_retry_get(url, params=None, delay=0.0):
        calls.append(params["filter"])
        return FakeResp()

    monkeypatch.setattr(hbc, "retry_get", fake_retry_get)
    hbc.batch_resolve(
        ["https://openalex.org/W1", "https://openalex.org/W2"], cache, delay=0.0
    )
    assert len(calls) == 1
    assert "W1" not in calls[0]
    assert cache.get("https://openalex.org/W2")["title"] == "fetched"
