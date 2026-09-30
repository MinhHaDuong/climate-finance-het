"""The causal-map query matrix, its EconLit twins and the metered run (ticket 1652)."""

import csv
import gzip
import json
import os
import types

import catalog_rel_causal_search as rc
import pytest

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(__file__))
ALLOWED = {"TI", "AB", "SU", "KW", "DE", "CC", "PT", "DT"}


def _cfgs():
    return rc.load_configs(os.path.join(ROOT, "config", "rel_causal_search.yaml"),
                           os.path.join(ROOT, "config", "rel_causal_families.yaml"),
                           os.path.join(ROOT, "config", "rel_causal_sentinels.csv"))


def _matrix():
    search, fams, sent = _cfgs()
    return (search, fams, sent) + rc.build_matrix(search, fams, sent)


def test_priority_families_have_every_formulation_and_three_languages():
    _, fams, sent, specs, _ = _matrix()
    have = {(s["question"], s["formulation"], s["language"]) for s in specs}
    for name, f in fams["families"].items():
        if not f["group"]:
            assert (name, "IO", "en") in have, name
            continue
        for form in ("IM", "IO", "SY", "CS"):
            assert (name, form, "en") in have, (name, form)
        for lang in ("fr", "es"):
            assert (name, "IM", lang) in have and (name, "IO", lang) in have, (name, lang)
        if any(s["family"] == name and s["set"] == "tuning" and s["openalex_id"] for s in sent):
            assert (name, "SI", "any") in have, name


def test_search_ids_are_unique_and_every_block_is_expanded():
    _, _, _, specs, rows = _matrix()
    ids = [r["search_id"] for r in rows]
    assert len(ids) == len(set(ids))
    for s in specs:
        assert "{" not in s["query_string"] and "," not in s["query_string"], s["search_id"]


def test_holdout_sentinels_never_enter_a_query():
    _, _, sent, specs, _ = _matrix()
    holdouts = {s["openalex_id"] for s in sent if s["set"] == "holdout" and s["openalex_id"]}
    for s in specs:
        assert not holdouts & set(s["filter"].replace(",", "|").replace(":", "|").split("|"))


def test_sentinels_are_fixed_with_a_set_and_a_verified_identifier():
    _, fams, sent, _, _ = _matrix()
    questions = set(fams["families"]) | set(fams["themes"])
    for s in sent:
        assert s["family"] in questions, s["sentinel"]
        assert s["set"] in {"tuning", "holdout", "other-source"}, s["sentinel"]
        if s["set"] != "other-source":
            assert s["doi"].startswith("10.") and s["openalex_id"].startswith("W"), s["sentinel"]


def test_non_english_rows_accept_their_language_or_a_null_tag():
    _, _, _, specs, _ = _matrix()
    for s in specs:
        if s["language"] in {"fr", "es"}:
            assert f"language:{s['language']}|null" in s["filter"]
        elif s["language"] == "en":
            assert "language:" not in s["filter"]


def test_budget_stop_cuts_from_the_end_priority_english_first():
    _, _, _, specs, _ = _matrix()
    ranks = [rc._order(s) for s in specs]
    assert ranks == sorted(ranks)
    assert specs[0]["group"] == 1 and specs[0]["language"] == "en"


def test_every_openalex_row_has_a_well_formed_econlit_twin():
    _, _, _, specs, rows = _matrix()
    by_id = {r["search_id"]: r for r in rows}
    for s in specs:
        twin = by_id[s["search_id"]]["econlit_string"]
        assert twin, s["search_id"]
        assert rc.econlit_problems(twin, ALLOWED) == [], (s["search_id"], twin)
        assert twin.endswith("AND DT 199001-202612")
    econ_only = [r for r in rows if r["platform"] == "econlit"]
    assert {r["formulation"] for r in econ_only} == {"JEL", "WP"}
    for r in econ_only:
        assert rc.econlit_problems(r["econlit_string"], ALLOWED) == [], r["search_id"]


def test_econlit_twin_searches_each_and_group_in_the_text_fields():
    econ = {"text_fields": ["TI", "AB"], "date": "DT 199001-202612"}
    spec = {"formulation": "IM", "question": "x",
            "query_string": '("a b" OR "c") AND ("d (e)" OR "f")'}
    assert rc.econlit_twin(spec, econ) == (
        '(TI ("a b" OR "c") OR AB ("a b" OR "c")) AND '
        '(TI ("d (e)" OR "f") OR AB ("d (e)" OR "f")) AND DT 199001-202612')


def test_econlit_checker_rejects_bad_strings():
    assert "unbalanced parentheses" in rc.econlit_problems('TI ("a" OR "b"', ALLOWED)
    assert "odd number of quotes" in rc.econlit_problems('TI ("a OR "b")', ALLOWED)
    assert "field code XX not allowed" in rc.econlit_problems('XX ("a")', ALLOWED)
    assert rc.econlit_problems('(CC Q54* OR CC F350) AND PT "Working Paper"', ALLOWED) == []


def test_sentinel_titles_lose_ebsco_wildcards():
    assert rc._clean_title('Do Carbon Offsets Offset Carbon?') == "Do Carbon Offsets Offset Carbon"
    assert rc._clean_title('A "Green Fix"*#') == "A Green Fix"


def test_meter_stops_on_lane_cap_and_on_daily_floor():
    m = rc.Meter(0.002, 0.30)
    m.observe({"X-RateLimit-Cost-USD": "0.001", "X-RateLimit-Remaining-USD": "0.9"})
    assert m.stop_reason() == ""
    m.observe({"x-ratelimit-cost-usd": "0.001", "x-ratelimit-remaining-usd": "0.8"})
    assert m.stop_reason().startswith("budget: lane cap")
    m = rc.Meter(1.0, 0.30)
    m.observe({"x-ratelimit-cost-usd": "0.001", "x-ratelimit-remaining-usd": "0.29"})
    assert m.stop_reason().startswith("budget: daily remaining")


def _args(tmp_path):
    return types.SimpleNamespace(output_dir=str(tmp_path / "run"), corpus=None, cap=None,
                                 delay=0, dry_run=False)


def test_budget_stop_leaves_later_queries_unrun_and_econlit_rows_marked(tmp_path):
    search, fams, sent = _cfgs()
    calls = []

    def fake_fetch(spec, api_key, cap, delay, meter):
        calls.append(spec["search_id"])
        yield ("page", 0.001)
        yield ("meta", 1)
        yield ("work", {"id": "https://openalex.org/W1", "doi": None, "display_name": "t"})
        yield ("end", "" if len(calls) < 2 else "budget: lane cap 0.4 USD reached")

    assert rc.run(search, fams, sent, _args(tmp_path), None, fetch=fake_fetch) == 0
    run_dir = tmp_path / "run"
    with open(run_dir / "registry.csv", encoding="utf-8") as fh:
        reg = list(csv.DictReader(fh))
    oa = [r for r in reg if r["platform"] == "openalex"]
    assert len(calls) == 2
    assert oa[0]["completed"] == "True" and oa[0]["cost_usd"] == "0.001"
    assert oa[1]["completed"] == "False" and oa[1]["stop_reason"].startswith("budget")
    assert all(r["stop_reason"].startswith("not run (budget") for r in oa[2:])
    el = [r for r in reg if r["platform"] == "econlit"]
    assert el and all(r["stop_reason"] == rc.ECONLIT_NOT_RUN for r in el)
    with gzip.open(run_dir / "results.jsonl.gz", "rt", encoding="utf-8") as fh:
        recs = [json.loads(line) for line in fh]
    assert [r["search_id"] for r in recs] == calls
    assert (run_dir / "matrix.csv").exists() and (run_dir / "spend.json").exists()
    # a second run into the same directory is refused
    assert rc.run(search, fams, sent, _args(tmp_path), None, fetch=fake_fetch) == 2


class _Resp:
    def __init__(self, body, cost="0.001", remaining="0.9", status=200):
        self.status_code, self._body = status, body
        self.headers = {"x-ratelimit-cost-usd": cost, "x-ratelimit-remaining-usd": remaining}

    def json(self):
        return self._body


def test_fetch_metered_reads_headers_and_stops_before_overspending(monkeypatch):
    pages = [_Resp({"meta": {"count": 400, "next_cursor": "c2"},
                    "results": [{"id": f"W{i}"} for i in range(200)]}, remaining="0.31"),
             _Resp({"meta": {"count": 400, "next_cursor": None},
                    "results": [{"id": f"W{i}"} for i in range(200)]}, remaining="0.29")]
    monkeypatch.setattr(rc, "polite_get", lambda url, params=None, delay=0: pages.pop(0))
    meter = rc.Meter(1.0, 0.30)
    out = list(rc.fetch_metered({"filter": "x"}, None, 0, 0, meter))
    assert out[-1] == ("end", "")  # the last page was already paid for and read
    assert meter.requests == 2 and abs(meter.spent - 0.002) < 1e-9
    pages[:] = [_Resp({"meta": {"count": 400, "next_cursor": "c2"},
                       "results": [{"id": "W1"}]}, remaining="0.29")]
    meter = rc.Meter(1.0, 0.30)
    out = list(rc.fetch_metered({"filter": "x"}, None, 0, 0, meter))
    assert out[-1][1].startswith("budget: daily remaining")
