"""Precision panel for dedup step 5 (ticket 2048): sampling, blind prompt, cap, analysis.

No network: the readers are fakes.
"""

import json
import re

import pytest
import rel_dedup_panel as rp

pytestmark = pytest.mark.domain_corpus


def _rec(title="Aid and growth in Africa", year="2010", author="Smith, John", doi=""):
    return {"record_id": f"l/1:{title}{year}", "title": title, "year": year, "first_author": author,
            "journal": "J", "doi": doi, "openalex_id": "", "doc_type": "", "abstract": "x" * 900}


@pytest.mark.parametrize("a, b, stratum", [
    ("Gavard, Claire", "Claire Gavard", "agree"), ("GAVARD C", "C. Gavard", "agree"),
    ("Müller, B.", "Benito Muller", "agree"), ("Rajan, Raghuram", "Acharya, Viral V.", "disagree"),
    ("", "Smith, J.", "missing"), ("J. K.", "Smith", "missing")])
def test_author_stratum(a, b, stratum):
    assert rp.author_stratum(a, b) == stratum


def test_allocation_takes_short_cells_whole_and_spreads_the_rest():
    alloc = rp.allocate({"a": 3, "b": 100, "c": 100}, 51)
    assert alloc == {"a": 3, "b": 24, "c": 24}
    assert sum(rp.allocate({"a": 5, "b": 5}, 400).values()) == 10


def test_draw_is_stratified_and_seeded():
    cands = [{"pair_id": f"P{i}", "gap": i % 7 - 1, "author": rp.AUTHOR_STRATA[i % 3]}
             for i in range(2100)]
    s1, cells = rp.draw(cands, 210)
    s2, _ = rp.draw(cands, 210)
    assert [c["pair_id"] for c in s1] == [c["pair_id"] for c in s2] and len(s1) == 210
    assert all(v["sampled"] == 10 for v in cells.values()) and len(cells) == 21


def test_prompt_is_blind_and_complete():
    item = {"pair_id": "P1", "wp": _rec(doi="10.2139/ssrn.1"), "pub": _rec(year="2013", doi="10.1/a")}
    text = rp.prompt(item)
    assert re.search(r"working|preprint|gap|window|rule|published", text, re.I) is None
    assert "10.2139/ssrn.1" in text and "10.1/a" in text and "2013" in text
    assert "x" * rp.ABSTRACT_CHARS in text and "x" * (rp.ABSTRACT_CHARS + 1) not in text
    orders = {rp.prompt({**item, "pair_id": f"P{i}"}).index("10.2139") < rp.prompt(
        {**item, "pair_id": f"P{i}"}).index("10.1/a") for i in range(20)}
    assert orders == {True, False}, "the working paper is not always record A"


@pytest.mark.parametrize("text, verdict", [
    ('{"verdict": "same", "reason": "r"}', "same"), ('ok\n{"verdict": "Cannot tell"}', "cannot_tell"),
    ('{"verdict": "maybe"}', None), ("no json", None)])
def test_parse_verdict(text, verdict):
    assert rp.parse_verdict(text)[0] == verdict


def test_wilson_majority_kappa():
    lo, hi = rp.wilson(8, 10)
    assert round(lo, 3) == 0.490 and round(hi, 3) == 0.943
    assert rp.majority(["same", "same", "different"]) == "same"
    assert rp.majority(["same", "different", "cannot_tell"]) == "no_majority"
    assert rp.fleiss_kappa([["same"] * 3, ["different"] * 3]) == 1.0


def _panel_dir(tmp_path, n=6):
    items = [{"pair_id": f"P{i}", "gap": i % 3, "author": "agree", "wp": _rec(year="2010"),
              "pub": _rec(year=str(2010 + i % 3))} for i in range(n)]
    (tmp_path / "sample.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
    ctrl = [{"pair_id": "CONTROL+", "expect": "same", "wp": _rec(), "pub": _rec()},
            {"pair_id": "CONTROL-", "expect": "different", "wp": _rec(), "pub": _rec("Other", "1999")}]
    (tmp_path / "controls.jsonl").write_text("".join(json.dumps(c) + "\n" for c in ctrl))
    (tmp_path / "sample_meta.json").write_text(json.dumps(
        {"cells": {f"{g}|agree": {"population": 10, "sampled": 2} for g in range(3)}}))
    return items


def fake(verdicts, usage=(400, 50)):
    """A reader answering ``verdicts[year]`` when a record has that year, else
    ``same``; the negative control (title ``Other``) is read ``different``."""
    def reader(text):
        hits = [v for y, v in verdicts.items() if f"Year: {y}" in text]
        v = "different" if "Title: Other" in text else (hits[0] if hits else "same")
        return json.dumps({"verdict": v, "reason": "fake"}), {
            "input_tokens": usage[0], "output_tokens": usage[1], "tier": "standard"}, ""
    return reader


def test_run_and_analyze_with_three_fake_readers(tmp_path):
    _panel_dir(tmp_path)
    readers = {"anthropic": fake({}), "openai": fake({}), "mistral": fake({"2012": "different"})}
    status = rp.run_panel(str(tmp_path), 10.0, list(readers), workers=2, readers=readers)
    assert {status[v] for v in readers} == {"completed"}
    s = rp.analyze(str(tmp_path))
    assert s["pairs_read_by_all"] == 6 and s["overall_sample_share"]["precision"] == 1.0
    assert s["agreement"]["unanimous"] == 4
    calls = [json.loads(x) for x in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert len(calls) == 3 * (6 + 2) and all(c["usd"] > 0 for c in calls)


def test_false_merges_are_listed(tmp_path):
    _panel_dir(tmp_path)
    readers = {v: fake({"2012": "different"}) for v in ("anthropic", "openai", "mistral")}
    rp.run_panel(str(tmp_path), 10.0, list(readers), workers=1, readers=readers)
    s = rp.analyze(str(tmp_path))
    assert len(s["false_merges"]) == 2 and s["by_gap"][2]["precision"] == 0.0


def test_a_failed_control_stops_that_reader_only(tmp_path):
    _panel_dir(tmp_path)

    def wrong(text):
        return '{"verdict": "same"}', {"input_tokens": 1, "output_tokens": 1}, ""
    readers = {"anthropic": fake({}), "mistral": wrong}
    status = rp.run_panel(str(tmp_path), 10.0, list(readers), workers=1, readers=readers)
    assert status["anthropic"] == "completed"
    assert status["mistral"].startswith("stopped: control CONTROL-")


def test_two_failed_calls_stop_a_reader(tmp_path):
    _panel_dir(tmp_path)
    calls = []

    def broken(text):
        calls.append(1)
        return None, None, "HTTP 404"
    status = rp.run_panel(str(tmp_path), 10.0, ["openai"], workers=1, readers={"openai": broken})
    assert status["openai"].startswith("stopped: control CONTROL+ failed twice") and len(calls) == 2


def test_the_cap_stops_before_the_call_that_would_cross_it(tmp_path):
    _panel_dir(tmp_path, n=50)
    readers = {"anthropic": fake({}, usage=(10_000, 1_000))}
    status = rp.run_panel(str(tmp_path), 0.5, ["anthropic"], workers=1, readers=readers)
    assert status["anthropic"].startswith("stopped at the cap")
    spent = sum(json.loads(x)["usd"] for x in (tmp_path / "calls.jsonl").read_text().splitlines())
    assert spent <= 0.5 and status["spent_usd"] <= 0.5
