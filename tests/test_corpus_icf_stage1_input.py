"""Stage-1 input of the ICF screen: unscreened pool works, lane order (ticket 1733)."""

import csv
import json

import _icf_screen as ics
import _rel_view as rv
import corpus_icf_stage1_input as si
import corpus_rel_sud_screen as sc
import pytest

pytestmark = pytest.mark.domain_corpus

PRIORITY = ["catalogue", "t1530", "t1651", "t1653", "t1652", "t1650"]


def _work(key, sources, title="A title", **kw):
    w = {f: "" for f in rv.POOL_FIELDS}
    w.update(work_key=key, sources=sources, title=title, year="2020", language="es",
             journal="J", abstract="Resumen", affiliation_countries="MX; BR")
    w.update(kw)
    return w


def test_lane_of_takes_the_highest_priority_source():
    assert si.lane_of("t1650-sommaires;t1530-sud-openalex", PRIORITY) == "t1530"
    assert si.lane_of("catalogue;t1650-sommaires", PRIORITY) == "catalogue"
    assert si.lane_of("t1653-scielo", PRIORITY) == "t1653"
    assert si.lane_of("t16500-x", PRIORITY) == "t16500-x", "a prefix needs the dash"
    assert si.lane_of("t9999-new;t1650-sommaires", PRIORITY) == "t1650"


def test_select_keeps_unscreened_orders_by_lane_and_counts_skips():
    pool = [_work("openalex:W5", "t1650-sommaires"),
            _work("openalex:W4", "t1652-causal-econlit"),
            _work("doi:10.1/b", "t1530-sud-openalex;t1650-sommaires"),
            _work("doi:10.1/a", "t1530-sud-openalex"),
            _work("openalex:W1", "catalogue"),
            _work("openalex:W2", "catalogue"),
            _work("title:x|2020", "t1650-sommaires", title=" "),
            _work("openalex:W9", "t9999-new")]
    view = [{"work_key": p["work_key"], "status": "unscreened"} for p in pool]
    view[5]["status"] = "stage1_out"
    picked, per_lane, skipped = si.select(pool, view, PRIORITY)
    assert [r["work_key"] for _, r in picked] == [
        "openalex:W1", "doi:10.1/a", "doi:10.1/b", "openalex:W4", "openalex:W5", "openalex:W9"]
    assert per_lane == {"catalogue": 1, "t1530": 2, "t1652": 1, "t1650": 1, "t9999-new": 1}
    assert skipped == {"t1650": 1}
    rec = picked[0][1]
    assert rec["countries"] == ["MX", "BR"]
    assert set(rec) == {"work_key", "openalex_id", "doi", "title", "year", "language", "journal",
                        "countries", "abstract"}


def test_run_writes_the_screener_input_from_pool_and_table(tmp_path):
    pool = [_work("openalex:W1", "catalogue", openalex_id="W1", all_openalex_ids="W1"),
            _work("openalex:W2", "t1650-sommaires", openalex_id="W2", all_openalex_ids="W2")]
    pool_path = tmp_path / "pool.csv"
    with open(pool_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rv.POOL_FIELDS)
        w.writeheader()
        w.writerows(pool)
    table = str(tmp_path / "rel_screen" / "icf_screen.csv")
    ics.append_rows(table, [{"work_key": "openalex:W1", "openalex_id": "W1", "stage": "1",
                             "labeller": "llm", "model": "qwen", "prompt_sha256": "p",
                             "run_id": "r", "machine": "padme", "label": "out",
                             "doc_type": "research", "labelled_at": "2026-09-30",
                             "source": "s"}], new_table=True)
    out = tmp_path / "in" / "screen_input.jsonl"
    summary = si.run(str(pool_path), table, str(out), PRIORITY)
    (rec,) = [json.loads(x) for x in open(out, encoding="utf-8")]
    assert rec["work_key"] == "openalex:W2"
    assert summary["works"] == 1 and summary["per_lane"] == {
        "t1650": {"works": 1, "skipped_no_title": 0}}
    assert json.loads((tmp_path / "in" / "screen_input.summary.json").read_text()) == summary
    # the screener reads it under --id-field work_key
    assert [r["work_key"] for r in sc.select_records(str(out), set(), 0, 7, "work_key")] == [
        "openalex:W2"]
