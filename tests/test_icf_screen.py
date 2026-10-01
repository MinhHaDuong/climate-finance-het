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


def test_every_pool_work_key_kind_is_accepted(table):
    keys = ["openalex:W9", "doi:10.1/x", "url:hdl:2139/1", "url:repo.org:hdl:1/2", "title:t|2020"]
    ics.append_rows(table, [_row(k) for k in keys])
    assert [r["work_key"] for r in ics.read_table(table)] == keys


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


# ── Version-2 answers and the dimensions table (ticket 1840) ──


V2 = ics.V2_FIELDS
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_t1530_stage2_prompt_hash_is_frozen():
    """The 4,752 t1530 Opus rows carry this hash: the import must keep reading the v1 file."""
    import yaml

    with open(os.path.join(ROOT, "config", "rel_screen.yaml"), encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    v1 = os.path.join(ROOT, cfg["t1530_stage2_prompt"])
    assert ics.stage2_prompt_sha256(v1) == (
        "8ff53ea8c818c2d88542a06f62e24613c9446691b8298452e407d8114e51a93d")
    assert ics.stage2_answer_fields(v1) == ics.V1_FIELDS
    current = os.path.join(ROOT, cfg["stage2"]["prompt"])
    assert os.path.abspath(current) != os.path.abspath(v1)
    assert ics.stage2_answer_fields(current) == V2


def test_v2_wrapper_keeps_the_v1_icf_instructions():
    """The ICF label stays comparable: the v1 ICF paragraph is in v2 word for word."""
    def block(name):
        with open(os.path.join(ROOT, "config", name), encoding="utf-8") as fh:
            return fh.read().split("```")[1]
    v1, v2 = block("rel_sud_stage2_prompt.md"), block("rel_stage2_prompt_v2.md")
    icf_part = v1.split("\nWrite one line per record")[0]
    assert v2.startswith(icf_part)


def test_parse_v2_answers_and_vocabularies():
    ids = ["a", "b", "c"]
    lines = ["1|icf|research|BR|yes|economics|empirical|CDM additionality | Brazil\n",
             "2|aux|research|CN|no|data_science|method|forecasts CER prices\n",
             "3|out|other|?|na|na|na|\n"]
    answers, faults = ics.parse_stage2_answers(lines, ids, V2)
    assert faults == []
    assert answers["a"] == {"label": "icf", "doc": "research", "studied": "BR", "contrib": "yes",
                            "field": "economics", "ctype": "empirical",
                            "why": "CDM additionality | Brazil"}
    assert (answers["b"]["contrib"], answers["b"]["field"]) == ("no", "data_science")
    assert answers["c"]["contrib"] == answers["c"]["ctype"] == "na"
    odd, _ = ics.parse_stage2_answers(["1|icf|research|BR|maybe|astrology|empirical|x\n"],
                                      ["a"], V2)
    assert (odd["a"]["contrib"], odd["a"]["field"], odd["a"]["ctype"]) == (
        "unknown", "unknown", "empirical")


def test_v2_parser_refuses_a_v1_line_and_v1_parser_is_unchanged():
    _, faults = ics.parse_stage2_answers(["1|icf|research|BR|GCF readiness\n"], ["a"], V2)
    assert any("not n|label|doc|studied|contrib" in f for f in faults)
    old, faults = ics.parse_stage2_answers(["1|icf|research|BR|a|b|c|d\n"], ["a"])
    assert faults == [] and old["a"]["why"] == "a|b|c|d" and "contrib" not in old["a"]


def _dim(wk="openalex:W1", run_id="r1", **kw):
    row = {"work_key": wk, "stage": "2", "labeller": "llm", "model": "opus",
           "prompt_sha256": "abc", "run_id": run_id, "machine": "doudou", "contrib": "yes",
           "field": "economics", "contrib_type": "policy", "labelled_at": "2026-10-01",
           "source": "c.opus.txt"}
    row.update(kw)
    return row


def test_dimensions_table_has_the_icf_screen_guards(tmp_path):
    t = str(tmp_path / "rel_screen" / "rel_dimensions.csv")
    S = ics.DIMENSIONS
    assert ics.append_rows(t, [_dim()], schema=S) == 1
    with open(t, encoding="utf-8") as fh:
        assert next(csv.reader(fh)) == S.columns
    with pytest.raises(ics.IcfScreenError, match="already in the table"):
        ics.append_rows(t, [_dim()], schema=S)
    with pytest.raises(ics.IcfScreenError, match="refused"):
        ics.append_rows(t, [_dim("openalex:W2", contrib="maybe")], schema=S)
    assert ics.append_new(t, [_dim(), _dim(run_id="r2")], schema=S) == (1, 1)
    with pytest.raises(ics.IcfScreenError, match="header"):
        ics.read_table(t)  # the icf_screen schema does not read a dimensions table
    data = open(t, "rb").read()
    with open(t, "wb") as fh:
        fh.write(data[:-5])
    with pytest.raises(ics.IcfScreenError, match="truncated"):
        ics.read_table(t, schema=S)
