"""The REL south search plan: 76 stratum runs, honest completion flags."""

import csv
import gzip
import json
import os
import types

import catalog_rel_sud_search as rs
import pytest
import yaml

pytestmark = pytest.mark.domain_corpus

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


def test_only_english_stratum_runs_are_filtered_by_affiliation_country():
    for s in rs.plan_queries(_cfg()):
        if s["kind"] == "q":
            has_country = "country_code" in s["filter"]
            assert has_country == (s["language"] == "en"), s["query_id"]


def test_both_unicode_spellings_and_yo_variant_are_sent():
    bn = "জলবায়ু অর্থায়ন"
    assert "য়" in "".join(rs.spelling_variants(bn))
    assert len(rs.spelling_variants(bn)) == 2
    assert "Зеленый климатический фонд" in rs.spelling_variants("Зелёный климатический фонд")
    assert rs.spelling_variants("climate finance") == ["climate finance"]
    q = rs.expand_query('"a" OR "Зелёный"')
    assert q == '"a" OR "Зелёный" OR "Зеленый"'


def test_stratum_queries_carry_the_spelling_variants():
    filt = {s["query_id"]: s["filter"] for s in rs.plan_queries(_cfg())}
    assert "য়" in filt["Q-south_asia-bn-T1"]
    assert "Зеленый климатический фонд" in filt["Q-russia-ru-T1"]


def test_non_english_runs_accept_the_language_or_a_null_tag_and_english_runs_none():
    for s in rs.plan_queries(_cfg()):
        if s["kind"] != "q":
            continue
        if s["language"] == "en":
            assert "language:" not in s["filter"], s["query_id"]
        else:
            assert f"language:{s['language']}|null" in s["filter"], s["query_id"]


def test_gap_fill_run_is_global_english_without_country_or_language_filter():
    g = [s for s in rs.plan_queries(_cfg()) if s["kind"] == "g"]
    assert len(g) == 1
    assert "country_code" not in g[0]["filter"] and "language:" not in g[0]["filter"]
    assert '"aid for adaptation"' in g[0]["filter"]


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


class _Resp:
    def __init__(self, status=200, body=None, bad=False):
        self.status_code, self._body, self._bad = status, body, bad

    def json(self):
        if self._bad:
            raise ValueError("not json")
        return self._body


def _page(n, ids, cursor):
    return _Resp(body={"meta": {"count": n, "next_cursor": cursor},
                       "results": [{"id": f"https://openalex.org/W{i}"} for i in ids]})


def _run_fetch(monkeypatch, pages, cap=0):
    it = iter(pages)
    calls = []

    def fake_get(url, params=None, delay=0):
        calls.append(params["cursor"])
        return next(it)

    monkeypatch.setattr(rs, "polite_get", fake_get)
    items = list(rs.fetch({"filter": "x"}, None, cap, 0))
    return items, calls


def test_fetch_follows_the_cursor_across_pages_and_ends_complete(monkeypatch):
    items, calls = _run_fetch(monkeypatch, [_page(3, [1, 2], "c2"), _page(3, [3], None)])
    assert [k for k, _ in items] == ["meta", "work", "work", "work", "end"]
    assert items[-1] == ("end", "") and calls == ["*", "c2"]


def test_fetch_cap_stops_a_longer_query_but_not_one_that_ends_exactly_at_the_cap(monkeypatch):
    items, _ = _run_fetch(monkeypatch, [_page(9, [1, 2], "c2")], cap=2)
    assert items[-1] == ("end", "record cap")
    items, _ = _run_fetch(monkeypatch, [_page(2, [1, 2], None)], cap=2)
    assert items[-1] == ("end", "")


def test_fetch_ends_the_query_on_429_http_error_and_bad_body(monkeypatch):
    assert _run_fetch(monkeypatch, [_Resp(status=429)])[0][-1][1].startswith("rate limited")
    assert _run_fetch(monkeypatch, [_Resp(status=500)])[0][-1] == ("end", "http 500")
    assert _run_fetch(monkeypatch, [_Resp(bad=True)])[0][-1] == ("end", "error: bad body")
    assert _run_fetch(monkeypatch, [_Resp(body={"nothing": 1})])[0][-1] == ("end", "error: bad body")


def test_run_refuses_an_output_directory_that_already_holds_a_registry(tmp_path):
    (tmp_path / "registry.csv").write_text("query_id\n", encoding="utf-8")
    args = types.SimpleNamespace(output_dir=str(tmp_path), corpus=None, only="e",
                                 cap=0, delay=0, dry_run=False)
    assert rs.run(_cfg(), args, None) == 2
    assert (tmp_path / "registry.csv").read_text(encoding="utf-8") == "query_id\n"


def test_term_flag_needs_word_boundaries_for_latin_terms_only():
    pattern = rs.icf_flag_pattern(_cfg())
    assert pattern.search("Norway REDD+ payments") and pattern.search("气候融资的研究")
    assert not pattern.search("shredded paper and redden")
