"""The REL view: pool × icf_screen statuses and reproducible counts (ticket 1732)."""

import csv
import json
import os

import _icf_screen as ics
import _rel_view as rv
import corpus_rel_view as crv
import pytest
import yaml

pytestmark = pytest.mark.domain_corpus

WINDOW = {"search_date": "2026-09-28", "year_min": 1990, "last_complete_year": 2025,
          "partial_year": 2026, "require_full_date_for_partial_year": True}


def _work(key, year="2020", title=None, oas="", dois="", version_hint=""):
    return {"work_key": key, "openalex_id": key.split(":", 1)[1] if key.startswith("openalex:") else "",
            "doi": key.split(":", 1)[1] if key.startswith("doi:") else "",
            "title": title if title is not None else f"Title {key}", "year": year,
            "journal": "J", "language": "en", "abstract": "", "affiliation_countries": "",
            "doc_type": "", "version_hint": version_hint,
            "all_dois": dois, "all_openalex_ids": oas, "in_catalogue": "true", "sources": "catalogue"}


def _lab(wk, stage, label, model="m", run_id="r", doc="research", title="t|2020", **kw):
    return {"work_key": wk, "openalex_id": wk.split(":", 1)[1] if wk.startswith("openalex:") else "",
            "doi": "", "title_norm_year": title, "stage": stage, "labeller": "llm",
            "model": model, "prompt_sha256": "p", "run_id": run_id, "machine": "padme",
            "label": label, "doc_type": doc, "studied_country": "", "why": "",
            "labelled_at": "2026-09-29", "source": "s", **kw}


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "config", "rel_screen.yaml"), encoding="utf-8") as _fh:
    RULE = rv.screen_rule(yaml.safe_load(_fh))  # the rule in force (config)
OLD_RULE = rv.screen_rule({"stage1_exit_labels": ["out", "aux"],
                           "stage2_labels": ["icf", "unsure"]})  # before 2026-09-30

POOL = [
    _work("openalex:W1", oas="W1"),                     # stage-2 icf, research
    _work("openalex:W2", oas="W2"),                     # stage-1 out
    _work("openalex:W3", oas="W3"),                     # stage-1 aux, pending (rule)
    _work("openalex:W4", oas="W4"),                     # stage-1 icf, pending
    _work("openalex:W5", oas="W5;W50"),                 # stage-2 unsure, via member id W50
    _work("doi:10.1/x", dois="10.1/x"),                 # stage-2 icf institutional via doi
    _work("openalex:W7", oas="W7", year="2026"),        # stage-2 icf, partial year
    _work("openalex:W8", oas="W8", version_hint="10.9/wp"),  # icf with version hint
    _work("title:nothing|2020"),                        # unscreened
]
LABELS = [
    _lab("openalex:W1", "1", "unsure"), _lab("openalex:W1", "2", "icf"),
    _lab("openalex:W2", "1", "out"),
    _lab("openalex:W3", "1", "aux"),
    _lab("openalex:W4", "1", "icf"),
    _lab("openalex:W50", "1", "icf"), _lab("openalex:W50", "2", "unsure"),
    _lab("openalex:W99", "1", "icf", doi="10.1/x"), _lab("openalex:W99", "2", "icf", doc="institutional", doi="10.1/x"),
    _lab("openalex:W7", "2", "icf"),
    _lab("openalex:W8", "1", "icf"), _lab("openalex:W8", "2", "out", run_id="r1"),
    _lab("openalex:W8", "2", "icf", run_id="r2"),          # later label wins, conflict counted
    _lab("openalex:W8", "audit", "out", model="fable"),    # audit never sets status
    _lab("openalex:W6", "1", "out", title=""),             # labelled, not in pool, no title
    _lab("openalex:W66", "1", "out"),                      # labelled, not in pool
]


def _status(rows):
    return {r["work_key"]: r["status"] for r in rows}


def test_statuses_matching_and_latest_label():
    rows, summary = rv.build_view(POOL, LABELS, WINDOW, RULE)
    assert _status(rows) == {
        "openalex:W1": "icf", "openalex:W2": "stage1_out", "openalex:W3": "pending_stage2",
        "openalex:W4": "pending_stage2", "openalex:W5": "unsure_unresolved", "doi:10.1/x": "icf",
        "openalex:W7": "icf", "openalex:W8": "icf", "title:nothing|2020": "unscreened"}
    w8 = next(r for r in rows if r["work_key"] == "openalex:W8")
    assert w8["conflict"] == "stage2" and w8["n_audit"] == 1
    assert summary["matched_by"] == {"work_key": 10, "openalex_id": 2, "doi": 2}
    assert summary["labelled_not_in_pool_works"] == {"no_title": 1, "not_in_pool": 1}


def test_config_rule_sends_stage1_aux_to_stage2_and_out_leaves():
    # Author decision 2026-09-30: only "out" leaves at stage 1.
    assert RULE == {"stage1_exit_labels": ["out"], "stage2_labels": ["aux", "icf", "unsure"]}
    aux = rv.work_status([_lab("openalex:W3", "1", "aux")], RULE)
    out = rv.work_status([_lab("openalex:W2", "1", "out")], RULE)
    assert aux["status"] == "pending_stage2" and aux["stage1_label"] == "aux"
    assert out["status"] == "stage1_out"


def test_old_rule_differs_by_exactly_the_stage1_aux_works():
    new = _status(rv.build_view(POOL, LABELS, WINDOW, RULE)[0])
    old = _status(rv.build_view(POOL, LABELS, WINDOW, OLD_RULE)[0])
    assert {k for k in new if new[k] != old[k]} == {"openalex:W3"}
    assert old["openalex:W3"] == "stage1_aux" and new["openalex:W3"] == "pending_stage2"


@pytest.mark.parametrize("cfg", [
    {"stage1_exit_labels": ["out"], "stage2_labels": ["icf", "unsure"]},          # aux has no fate
    {"stage1_exit_labels": ["out", "aux"], "stage2_labels": ["icf", "unsure", "aux"]},  # two fates
    {}])
def test_rule_must_partition_the_labels(cfg):
    with pytest.raises(ics.IcfScreenError, match="partition"):
        rv.screen_rule(cfg)


def test_counts_window_doc_type_and_version_hint():
    rows, summary = rv.build_view(POOL, LABELS, WINDOW, RULE)
    counts = crv.make_counts(rows, summary, WINDOW, {}, RULE)
    rel = counts["rel"]
    assert rel["icf_total"] == 4
    assert rel["icf_research_in_window"] == 2  # W1, W8
    assert rel["icf_institutional_in_window"] == 1
    assert rel["icf_partial_year_by_doc"] == {"research": 1}
    assert rel["icf_research_in_window_with_version_hint"] == 1
    assert rel["unsure_unresolved"] == 1 and rel["pending_stage2"] == 2  # W4, W3 (aux)
    assert counts["rule"] == RULE
    assert counts["conflicts"] == {"stage1": 0, "stage2": 1}
    assert sum(counts["status"].values()) == len(POOL)


def _files(tmp_path):
    pool = tmp_path / "pool.csv"
    with open(pool, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rv.POOL_FIELDS)
        w.writeheader()
        w.writerows(POOL)
    table = str(tmp_path / "icf_screen.csv")
    ics.append_rows(table, LABELS)
    return str(pool), table


def test_same_inputs_give_byte_identical_outputs(tmp_path):
    pool, table = _files(tmp_path)
    crv.run(pool, table, str(tmp_path / "a"), WINDOW, RULE)
    crv.run(pool, table, str(tmp_path / "b"), WINDOW, RULE)
    for name in ("rel_view.csv", "rel_counts.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    counts = json.loads((tmp_path / "a" / "rel_counts.json").read_text())
    assert counts["labels"]["rows"] == len(LABELS)
    assert counts["rule"] == RULE


def test_view_refuses_a_tampered_table(tmp_path):
    pool, table = _files(tmp_path)
    data = open(table, "rb").read()
    open(table, "wb").write(data[:-5])
    with pytest.raises(ics.IcfScreenError):
        crv.run(pool, table, str(tmp_path / "a"), WINDOW, RULE)


def test_view_reports_a_missing_table_cleanly(tmp_path):
    pool, _ = _files(tmp_path)
    missing = str(tmp_path / "none" / "icf_screen.csv")
    with pytest.raises(ics.IcfScreenError, match="missing"):
        crv.run(pool, missing, str(tmp_path / "a"), WINDOW, RULE)
    assert crv.main(["--pool", pool, "--table", missing,
                     "--output-dir", str(tmp_path / "a")]) == 1
