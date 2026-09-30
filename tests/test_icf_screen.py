"""The icf_screen table only grows: append-only writer guards (ticket 1732)."""

import csv
import json
import os

import _icf_screen as ics
import pytest

pytestmark = pytest.mark.domain_corpus


def _row(wk="openalex:W1", stage="1", model="m", run_id="r1", label="icf", **kw):
    row = {"work_key": wk, "openalex_id": wk.split(":", 1)[1] if wk.startswith("openalex:") else "",
           "stage": stage, "labeller": "llm", "model": model, "prompt_sha256": "abc",
           "run_id": run_id, "machine": "padme", "label": label, "doc_type": "research",
           "labelled_at": "2026-09-29", "source": "x.jsonl"}
    row.update(kw)
    return row


@pytest.fixture
def table(tmp_path):
    return str(tmp_path / "rel_screen" / "icf_screen.csv")


def test_append_creates_then_grows(table):
    assert ics.append_rows(table, [_row()]) == 1
    assert ics.append_rows(table, [_row("openalex:W2"), _row(stage="2")]) == 2
    rows = ics.read_table(table)
    assert [r["work_key"] for r in rows] == ["openalex:W1", "openalex:W2", "openalex:W1"]
    with open(table, encoding="utf-8") as fh:
        assert next(csv.reader(fh)) == ics.COLUMNS
    entries = [json.loads(x) for x in open(ics.manifest_path(table), encoding="utf-8")]
    assert [e["rows_total"] for e in entries] == [1, 3]
    assert rows[0]["label_id"] == ics.label_id(rows[0]) != rows[2]["label_id"]


def test_rewrite_mode_is_refused(table):
    for mode in ("w", "w+", "r+", "a+"):
        with pytest.raises(ics.IcfScreenError, match="append-only"):
            ics._open(table, mode)


def test_duplicate_key_is_refused_and_nothing_written(table):
    ics.append_rows(table, [_row()])
    size = len(open(table, "rb").read())
    with pytest.raises(ics.IcfScreenError, match="already in the table"):
        ics.append_rows(table, [_row("openalex:W9"), _row(label="out")])
    assert len(open(table, "rb").read()) == size, "a refused batch writes no byte"
    with pytest.raises(ics.IcfScreenError, match="already in the table"):
        ics.append_rows(table, [_row("openalex:W5"), _row("openalex:W5")])


def test_same_work_other_run_or_stage_is_a_new_label(table):
    ics.append_rows(table, [_row(), _row(run_id="r2"), _row(model="m2"), _row(stage="audit")])
    assert len(ics.read_table(table)) == 4


def test_truncated_table_is_detected(table):
    ics.append_rows(table, [_row(), _row("openalex:W2")])
    data = open(table, "rb").read()
    with open(table, "wb") as fh:  # the defect the guard exists for: a rewrite
        fh.write(data[: len(data) - 20])
    with pytest.raises(ics.IcfScreenError, match="is truncated: "):
        ics.read_table(table)
    with pytest.raises(ics.IcfScreenError, match="is truncated: "):
        ics.append_rows(table, [_row("openalex:W3")])


def test_rewritten_row_and_unrecorded_append_are_detected(table):
    ics.append_rows(table, [_row(), _row("openalex:W2")])
    data = open(table, "rb").read()
    with open(table, "wb") as fh:
        fh.write(data.replace(b",icf,", b",out,", 1))
    with pytest.raises(ics.IcfScreenError, match="recorded rows were rewritten"):
        ics.read_table(table)
    with open(table, "wb") as fh:
        fh.write(data + b"extra\n")
    with pytest.raises(ics.IcfScreenError, match="without a manifest entry"):
        ics.read_table(table)


def test_table_without_manifest_is_refused(table):
    ics.append_rows(table, [_row()])
    os.remove(ics.manifest_path(table))
    with pytest.raises(ics.IcfScreenError, match="together"):
        ics.read_table(table)


@pytest.mark.parametrize("bad", [
    {"label": "maybe"}, {"stage": "3"}, {"labeller": "robot"}, {"doc_type": ""},
    {"model": ""}, {"work_key": "W1"}, {"prompt_sha256": ""},
])
def test_invalid_rows_are_refused(table, bad):
    with pytest.raises(ics.IcfScreenError, match="refused"):
        ics.append_rows(table, [_row(**bad)])


def test_append_new_is_idempotent(table):
    rows = [_row(), _row("openalex:W2")]
    assert ics.append_new(table, rows) == (2, 0)
    assert ics.append_new(table, rows) == (0, 2)
    assert len(ics.read_table(table)) == 2


def test_parse_stage2_answers():
    ids = ["a", "b", "c"]
    lines = ["1|icf|research|BR|CDM in Brazil | projects\n", "2|out|weird|?|\n", "\n"]
    answers, faults = ics.parse_stage2_answers(lines, ids)
    assert answers["a"] == {"label": "icf", "doc": "research", "studied": "BR",
                            "why": "CDM in Brazil | projects"}
    assert answers["b"]["doc"] == "unknown"
    assert faults == ["1 of 3 records unanswered"]
    _, faults = ics.parse_stage2_answers(["1|icf|research|?|\n", "1|out|research|?|\n",
                                          "4|icf|research|?|\n", "junk\n"], ids)
    assert any("twice" in f for f in faults) and any("n=4" in f for f in faults)
    assert any("not n|label" in f for f in faults)


def test_format_stage2_record_matches_1530_layout():
    rec = {"language": "zh", "year": 2008, "journal": "", "countries": ["CN", "FR"],
           "title": "T" * 300, "abstract": ""}
    text = ics.format_stage2_record(3, rec, 220, 650)
    assert text == (f"3. [zh | 2008 | ? | affiliations: CN, FR]\n   Title: {'T' * 220}\n"
                    "   Abstract: (no abstract)\n")


def test_missing_dvc_tracked_table_is_not_forked(tmp_path, table):
    """A fresh checkout has data/rel_screen.dvc but no table: never start a new one."""
    (tmp_path / "rel_screen.dvc").write_text("outs:\n- path: rel_screen\n")
    with pytest.raises(ics.IcfScreenError, match="dvc checkout"):
        ics.append_rows(table, [_row()])
    with pytest.raises(ics.IcfScreenError, match="dvc checkout"):
        ics.append_new(table, [_row()])
    assert not os.path.exists(table) and not os.path.exists(ics.manifest_path(table))
    assert ics.append_new(table, [_row()], new_table=True) == (1, 0)
    assert ics.append_rows(table, [_row("openalex:W2")]) == 1, "an existing table grows"


def test_require_table_names_the_fetch(tmp_path, table):
    with pytest.raises(ics.IcfScreenError, match="missing"):
        ics.require_table(table)
    ics.append_rows(table, [_row()])
    ics.require_table(table)
