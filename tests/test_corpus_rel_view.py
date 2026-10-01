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
OLD_RULE = rv.screen_rule({"stage1_exit_labels": ["out", "aux"], "stage2_labels": ["icf", "unsure"],
                           "stage2_unsure_in_rel": True})  # stage 1 before 2026-09-30

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
    assert {k: v for k, v in RULE.items() if k != "stage1_joint"} == {
        "stage1_exit_labels": ["out"], "stage2_labels": ["aux", "icf", "unsure"],
        "stage2_unsure_in_rel": True}
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


def test_rule_requires_the_unsure_exit():
    with pytest.raises(ics.IcfScreenError, match="stage2_unsure_in_rel"):
        rv.screen_rule({"stage1_exit_labels": ["out"], "stage2_labels": ["icf", "unsure", "aux"]})


def test_stage2_unsure_stays_in_rel_flagged():
    # Author decision 2026-09-30 (recall first): unsure after stage 2 stays, flagged.
    labs = [_lab("openalex:W5", "1", "icf"), _lab("openalex:W5", "2", "unsure")]
    kept = rv.work_status(labs, RULE)
    assert (kept["status"], kept["rel_included"], kept["rel_flag"]) == (
        "unsure_unresolved", "true", "unsure")
    dropped = rv.work_status(labs, {**RULE, "stage2_unsure_in_rel": False})
    assert (dropped["rel_included"], dropped["rel_flag"]) == ("false", "")
    icf = rv.work_status([_lab("openalex:W1", "2", "icf")], RULE)
    assert (icf["rel_included"], icf["rel_flag"]) == ("true", "")


def _gs_pair():
    # The 1651 pattern: Gavard-Schoch working paper (SSRN 2021) -> article (2026),
    # each record pointing at the other by lane record id.
    wp = _work("openalex:W31", oas="W31", year="2021", dois="10.2139/ssrn.3799872",
               version_hint="1651-GS02")
    wp.update(doc_type="report", journal="SSRN Electronic Journal",
              member_record_ids="openalex:W31;t1651-gavard-schoch/2026-09-30:1651-GS01")
    art = _work("openalex:W72", oas="W72", year="2026", dois="10.1017/s1355770x26100679",
                version_hint="1651-GS01")
    art.update(doc_type="journalArticle",
               member_record_ids="t1651-gavard-schoch/2026-09-30:1651-GS02")
    return [wp, art]


def test_version_families_prefer_the_published_article():
    fams, summary = rv.version_families(_gs_pair() + [_work("openalex:W9", oas="W9")])
    assert [f["family_id"] for f in fams] == ["openalex:W72", "openalex:W72", "openalex:W9"]
    assert fams[0]["family_first_year"] == "2021" and fams[0]["family_size"] == 2
    assert summary == {"families": 2, "multi_work_families": 1,
                       "works_in_multi_work_families": 2, "families_with_mixed_final_labels": 0,
                       "version_hints_unresolved": 0, "version_hints_unresolved_by_cause": {}}


def test_representative_is_an_included_member():
    # ICF working paper + article judged aux at stage 2: the family stands for
    # the included working paper, and the family is counted as mixed.
    pool = _gs_pair()
    labels = [_lab("openalex:W31", "2", "icf"), _lab("openalex:W72", "2", "aux")]
    rows, summary = rv.build_view(pool, labels, WINDOW, RULE)
    assert {r["family_id"] for r in rows} == {"openalex:W31"}
    assert summary["families"]["families_with_mixed_final_labels"] == 1


def test_two_articles_tie_break_on_year_then_work_key():
    a = _work("openalex:W2", oas="W2", year="2020", version_hint="W1")
    b = _work("openalex:W1", oas="W1", year="2020")
    c = _work("openalex:W3", oas="W3", year="2019", version_hint="W1")
    for w in (a, b, c):
        w["doc_type"] = "journal-article"
    fams, _ = rv.version_families([a, b])
    assert fams[0]["family_id"] == "openalex:W1"          # same year: smallest work_key
    fams, _ = rv.version_families([a, b, c])
    assert fams[0]["family_id"] == "openalex:W3"          # earliest year first


def test_hint_forms_resolve():
    target = _work("doi:10.5/art", dois="10.5/art;10.5/alias", oas="W40")
    hints = ["10.5/ART", "https://doi.org/10.5/art", "doi:10.5/alias",
             "W40", "https://openalex.org/W40", "10.9/none 10.5/alias"]
    pool = [target] + [_work(f"openalex:W{i}", oas=f"W{i}", version_hint=h)
                       for i, h in enumerate(hints, 1)]
    fams, summary = rv.version_families(pool)
    assert {f["family_id"] for f in fams} == {"doi:10.5/art"}
    assert summary["version_hints_unresolved_by_cause"] == {"doi_not_in_pool": 1}


def test_sici_dois_keep_their_semicolon():
    # The 1650 pattern: a SICI DOI holds ";2-8"; its tail must not become a bare
    # record id that links two unrelated works of the same lane.
    a = _work("openalex:W1", oas="W1", version_hint="10.1002/(sici)a>3.3.co;2-8")
    a["member_record_ids"] = "t1650-sommaires/2026-09-30:2-8"
    b = _work("openalex:W2", oas="W2", dois="10.1002/(sici)b>3.0.co;2-8")
    b["member_record_ids"] = "t1650-sommaires/2026-09-30:x"
    c = _work("openalex:W3", oas="W3", dois="10.1002/(sici)a>3.3.co;2-8;10.9/c")
    assert rv.split_hints("10.1/a;2-8;10.2/b 10.3/c") == ["10.1/a;2-8", "10.2/b", "10.3/c"]
    fams, summary = rv.version_families([a, b, c])
    assert fams[0]["family_id"] == fams[2]["family_id"] != fams[1]["family_id"]
    assert summary["version_hints_unresolved"] == 0


def test_bare_record_ids_are_namespaced_by_lane():
    hinting = _work("openalex:W1", oas="W1", version_hint="R1")
    hinting["member_record_ids"] = "tA/2026-09-30:R0"
    same_lane = _work("openalex:W2", oas="W2")
    same_lane["member_record_ids"] = "tA/2026-09-30:R1"
    other_lane = _work("openalex:W3", oas="W3")
    other_lane["member_record_ids"] = "tB/2026-09-30:R1"
    fams, _ = rv.version_families([other_lane, hinting, same_lane])
    assert fams[1]["family_id"] == fams[2]["family_id"] != fams[0]["family_id"]
    both = _work("openalex:W4", oas="W4", version_hint="R1")
    both["member_record_ids"] = "tA/2026-09-30:R4;tB/2026-09-30:R4"
    fams, summary = rv.version_families([other_lane, both, same_lane])
    assert summary["version_hints_unresolved_by_cause"] == {"ambiguous": 1}
    assert fams[1]["family_size"] == 1
    lost = _work("openalex:W5", oas="W5", version_hint="R9")
    lost["member_record_ids"] = "tA/2026-09-30:R5"
    assert rv.version_families([lost, other_lane])[1]["version_hints_unresolved_by_cause"] == {
        "record_not_in_lane": 1}


def test_version_hint_by_doi_and_unresolved_hint():
    a = _work("openalex:W1", oas="W1", year="2019", version_hint="10.5/ART")
    a["doc_type"] = "preprint"
    b = _work("doi:10.5/art", dois="10.5/art", year="2020")
    b["doc_type"] = "journal-article"
    c = _work("openalex:W3", oas="W3", version_hint="1999-NOPE")
    fams, summary = rv.version_families([a, b, c])
    assert fams[0]["family_id"] == fams[1]["family_id"] == "doi:10.5/art"
    assert summary["version_hints_unresolved"] == 1


def test_rel_counts_in_works_and_families():
    pool = _gs_pair()
    labels = [_lab("openalex:W31", "2", "icf"), _lab("openalex:W72", "2", "unsure")]
    rows, summary = rv.build_view(pool, labels, WINDOW, RULE)
    counts = crv.make_counts(rows, summary, WINDOW, {}, RULE)
    rel = counts["rel"]
    assert rel["included_works"] == 2 and rel["included_families"] == 1
    assert rel["included_unsure_flagged_works"] == 1
    # W72 (2026) is partial year: in window only the working paper counts.
    assert rel["included_research_in_window_works"] == 1
    assert rel["included_research_in_window_families"] == 1
    assert counts["families"]["multi_work_families"] == 1
    assert "families" not in counts["labels"]


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
    venues = tmp_path / "rel_work_venues.csv"
    with open(venues, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["work_key", "tier", "tier_ngo_in_b", "tier_ngo_not_b", "flags",
                    "flagged", "excluded", "publisher_flag"])
        w.writerows([p["work_key"], "A", "A", "A", "", "false", "false", ""] for p in POOL)
    return str(pool), table


SRULE = {"exclude": ["hijacked"], "ngo_research_in_b": True, "no_venue": "keep_flagged",
         "nonresearch": "to_c", "alpha": 0.5,
         "tier_mu": {"A": 1.0, "B": 1.0, "C": 0.0, "unknown": 0.5},
         "tiers": ["A", "B"], "drop_publishers": []}
MRULE = {"status": "proposed", "icf": {"icf": 1.0, "unsure": 0.5, "aux": 0.0, "out": 0.0},
         "discipline": {"yes": 1.0, "unsure": 0.5, "no": 0.0}, "family": "max"}


def _run(tmp_path, pool, table, out):
    """``corpus_rel_view.run`` with no dimension table and an all-A venue table."""
    return crv.run(pool, table, str(tmp_path / out), WINDOW, RULE,
                   dims_path=str(tmp_path / "rel_dimensions.csv"),
                   venues_path=str(tmp_path / "rel_work_venues.csv"), seriousness_rule=SRULE,
                   membership=MRULE)


def test_same_inputs_give_byte_identical_outputs(tmp_path):
    pool, table = _files(tmp_path)
    _run(tmp_path, pool, table, "a")
    _run(tmp_path, pool, table, "b")
    for name in ("rel_view.csv", "rel_counts.json", "rel_sensitivity.csv"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    counts = json.loads((tmp_path / "a" / "rel_counts.json").read_text())
    assert counts["labels"]["rows"] == len(LABELS)
    assert counts["rule"] == dict(RULE, seriousness=SRULE, membership=MRULE)


def test_view_refuses_a_tampered_table(tmp_path):
    pool, table = _files(tmp_path)
    data = open(table, "rb").read()
    open(table, "wb").write(data[:-5])
    with pytest.raises(ics.IcfScreenError):
        _run(tmp_path, pool, table, "a")


def test_view_reports_a_missing_table_cleanly(tmp_path):
    pool, _ = _files(tmp_path)
    missing = str(tmp_path / "none" / "icf_screen.csv")
    with pytest.raises(ics.IcfScreenError, match="missing"):
        _run(tmp_path, pool, missing, "a")
    assert crv.main(["--pool", pool, "--table", missing,
                     "--output-dir", str(tmp_path / "a")]) == 1


# ── Design B (author decision 2026-10-01): stage 1 drops only when both say out ──

GEMMA, JEV = "google/gemma-4-26b-a4b-it", "typesafe/jev-1.13-20260917"


def _pair(llm_label, clf_label, p_out, run_id="designB-1", wk="openalex:W1", why=None):
    return [_lab(wk, "1", llm_label, model=GEMMA, run_id=run_id),
            {**_lab(wk, "1", clf_label, model=JEV, run_id=run_id),
             "why": why if why is not None else f"p_out={p_out!r}"}]


def test_config_declares_the_design_b_rule():
    assert RULE["stage1_joint"] == {"llm_models": [GEMMA], "classifier_models": [JEV],
                                    "classifier_p_out_min": 0.95}


@pytest.mark.parametrize("llm, clf, p_out, status", [
    ("out", "out", 0.97, "stage1_out"),        # both out, P above the threshold
    ("out", "out", 0.95, "stage1_out"),        # the threshold itself drops
    ("out", "out", 0.94, "pending_stage2"),    # Jev out but P(out) 0.94
    ("out", "aux", 0.40, "pending_stage2"),    # only the LLM says out
    ("aux", "out", 0.99, "pending_stage2"),    # only the classifier says out
    ("icf", "icf", 0.00, "pending_stage2"),
])
def test_design_b_drops_only_when_both_say_out(llm, clf, p_out, status):
    s = rv.work_status(_pair(llm, clf, p_out), RULE)
    assert s["status"] == status
    assert s["stage1_run_id"] == "designB-1" and s["stage1_model"] == f"{GEMMA}+{JEV}"
    assert s["stage1_joint"] == f"llm={llm};classifier={clf};p_out={p_out}"
    assert s["conflict"] == "", "the two rows of one run are one decision"


def test_design_b_disagreement_keeps_the_llm_label_but_goes_to_stage2():
    s = rv.work_status(_pair("out", "aux", 0.4), RULE)
    assert (s["stage1_label"], s["status"]) == ("out", "pending_stage2")


@pytest.mark.parametrize("labs", [
    _pair("out", "out", 0.99)[:1],                 # the LLM row alone
    _pair("out", "out", 0.99)[1:],                 # the classifier row alone
    _pair("out", "out", 0.99, why="no p here"),    # classifier row without P(out)
])
def test_half_a_design_b_decision_never_drops(labs):
    assert rv.work_status(labs, RULE)["status"] == "pending_stage2"


def test_without_the_rule_design_b_rows_drop_below_the_threshold():
    # What the rule prevents: read as two single-labeller rows, both "out",
    # the pair drops the work although Jev's P(out) is only 0.5.
    labs = _pair("out", "out", 0.5)
    assert rv.work_status(labs, {**RULE, "stage1_joint": None})["status"] == "stage1_out"
    assert rv.work_status(labs, RULE)["status"] == "pending_stage2"


QWEN_OUT = _lab("openalex:W1", "1", "out", model="qwen3.8-27b", run_id="pool-stage1")
QWEN_AUX = _lab("openalex:W1", "1", "aux", model="qwen3.8-27b", run_id="pool-stage1")


def test_a_lone_qwen_out_keeps_the_single_labeller_rule():
    assert rv.work_status([QWEN_OUT], RULE)["status"] == "stage1_out"


@pytest.mark.parametrize("labs", [
    [QWEN_OUT] + _pair("out", "aux", 0.3),     # design-B pass after a Qwen out
    _pair("out", "aux", 0.3) + [QWEN_OUT],     # Qwen out after a design-B pass
    [QWEN_AUX] + _pair("out", "out", 0.99),    # design-B drop after a Qwen pass
    _pair("out", "out", 0.99) + [QWEN_AUX],    # Qwen pass after a design-B drop
])
def test_several_stage1_verdicts_leave_only_if_all_are_out(labs):
    # Recall first (2026-10-01): one verdict that sends the work on is enough,
    # whichever came later in the table.
    s = rv.work_status(labs, RULE)
    assert s["status"] == "pending_stage2"
    assert s["conflict"] == "stage1"


@pytest.mark.parametrize("labs", [
    [QWEN_OUT] + _pair("out", "out", 0.99),
    _pair("out", "out", 0.99) + [QWEN_OUT],
])
def test_every_verdict_out_leaves_at_stage1(labs):
    s = rv.work_status(labs, RULE)
    assert s["status"] == "stage1_out" and s["conflict"] == ""


def test_the_shown_stage1_verdict_is_the_latest_that_passes():
    s = rv.work_status(_pair("out", "aux", 0.3) + [QWEN_OUT], RULE)
    assert (s["stage1_model"], s["stage1_run_id"]) == (f"{GEMMA}+{JEV}", "designB-1")


def test_p_out_just_under_the_threshold_never_rounds_onto_it():
    # 0.94995 rounded to 4 decimals would be 0.9500 and drop the work.
    assert rv.work_status(_pair("out", "out", 0.94995), RULE)["status"] == "pending_stage2"
    assert rv.work_status(_pair("out", "out", 0.95), RULE)["status"] == "stage1_out"


@pytest.mark.parametrize("why, p", [("p_out=0.97", 0.97), ("p_out=9.5e-01", 0.95),
                                    ("p_out=1e-05", 1e-05), ("p_out=9.5", None),
                                    ("p_out=nan?", None), ("P=0.99", None)])
def test_p_out_parsing(why, p):
    assert rv.p_out_of({"why": why}) == p


def test_stage2_stays_final_over_a_design_b_drop():
    s = rv.work_status(_pair("out", "out", 0.99) + [_lab("openalex:W1", "2", "icf")], RULE)
    assert (s["status"], s["rel_included"]) == ("icf", "true")


@pytest.mark.parametrize("block, match", [
    ({"llm_models": [GEMMA], "classifier_models": [GEMMA], "classifier_p_out_min": 0.95},
     "disjoint"),
    ({"llm_models": [], "classifier_models": [JEV], "classifier_p_out_min": 0.95}, "non-empty"),
    ({"llm_models": [GEMMA], "classifier_models": [JEV], "classifier_p_out_min": 1.5}, r"\(0, 1\]"),
    ({"llm_models": [GEMMA], "classifier_models": [JEV]}, r"\(0, 1\]"),
])
def test_joint_rule_is_checked(block, match):
    with pytest.raises(ics.IcfScreenError, match=match):
        rv.joint_rule(block)


def test_view_counts_design_b_decisions():
    pool = [_work("openalex:W1", oas="W1"), _work("openalex:W2", oas="W2"),
            _work("openalex:W3", oas="W3")]
    labels = (_pair("out", "out", 0.99, wk="openalex:W1")
              + _pair("out", "aux", 0.2, wk="openalex:W2")
              + [_lab("openalex:W3", "1", "out", model="qwen3.8-27b")])
    rows, summary = rv.build_view(pool, labels, WINDOW, RULE)
    assert _status(rows) == {"openalex:W1": "stage1_out", "openalex:W2": "pending_stage2",
                             "openalex:W3": "stage1_out"}
    counts = crv.make_counts(rows, summary, WINDOW, {}, RULE)
    assert counts["stage1_joint"] == {"works": 2, "stage1_out": 1, "pending_stage2": 1}
    assert counts["conflicts"]["stage1"] == 0
