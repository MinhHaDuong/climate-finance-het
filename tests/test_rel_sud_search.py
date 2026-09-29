"""The REL south search plan: 76 stratum runs, honest completion flags."""

import csv
import gzip
import json
import os
import types

import pytest
import rel_sud_search as rs
import yaml

pytestmark = pytest.mark.wp_corpus

ROOT = os.path.dirname(os.path.dirname(__file__))


def _cfg():
    with open(os.path.join(ROOT, "config", "rel_sud_search.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_plan_has_76_stratum_runs_and_every_query_is_defined():
    specs = rs.plan_queries(_cfg())
    assert sum(s["kind"] == "q" for s in specs) == 76
    assert len({s["query_id"] for s in specs}) == len(specs)
    for s in specs:
        if s["kind"] != "e":
            search = s["filter"].split(",publication_year")[0].split(":", 1)[-1]
            assert "," not in search


def test_filter_carries_language_and_affiliation_countries():
    f = rs.build_filter('"a"', 1990, 2026, language="es", countries=["AR", "BR"])
    assert "language:es" in f
    assert "authorships.institutions.country_code:AR|BR" in f


def _args(tmp_path):
    return types.SimpleNamespace(output_dir=str(tmp_path), corpus=None, only="e",
                                 cap=0, delay=0, dry_run=False)


def test_rate_limit_leaves_query_incomplete_and_stops_later_ones(tmp_path, monkeypatch):
    def fake_fetch(spec, api_key, cap, delay):
        yield ("meta", 3)
        yield ("work", {"id": "https://openalex.org/W1", "display_name": "Climate finance"})
        yield ("end", "rate limited or budget exhausted")

    monkeypatch.setattr(rs, "fetch", fake_fetch)
    rs.run(_cfg(), _args(tmp_path), None)
    rows = list(csv.DictReader(open(tmp_path / "registry.csv", encoding="utf-8")))
    assert rows[0]["completed"] == "False" and rows[0]["n_received"] == "1"
    assert all(r["completed"] == "False" for r in rows)
    assert rows[1]["stop_reason"] == "not run"


def test_corpus_match_and_term_flag_on_written_results(tmp_path, monkeypatch):
    corpus = tmp_path / "refined.csv"
    corpus.write_text("source,source_id,doi\nopenalex,W1,\nistex,x,10.1/known\n",
                      encoding="utf-8")

    def fake_fetch(spec, api_key, cap, delay):
        yield ("meta", 3)
        yield ("work", {"id": "https://openalex.org/W1", "display_name": "Other"})
        yield ("work", {"id": "https://openalex.org/W2", "doi": "https://doi.org/10.1/KNOWN",
                        "display_name": "Financiamento climático no Sul"})
        yield ("work", {"id": "https://openalex.org/W3", "display_name": "Unrelated"})
        yield ("end", "")

    monkeypatch.setattr(rs, "fetch", fake_fetch)
    args = _args(tmp_path)
    args.corpus = str(corpus)
    rs.run(_cfg(), args, None)
    with gzip.open(tmp_path / "results.jsonl.gz", "rt", encoding="utf-8") as fh:
        first = [json.loads(line) for line in fh][:3]
    assert [w["in_corpus"] for w in first] == [True, True, False]
    assert [w["icf_term"] for w in first] == [False, True, False]
