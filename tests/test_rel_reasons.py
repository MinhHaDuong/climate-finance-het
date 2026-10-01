"""REL exclusions by reason: ICF, discipline, seriousness (ticket 1843)."""

import csv
import json

import _icf_screen as ics
import _rel_reasons as rr
import _rel_view as rv
import corpus_rel_view as crv
import pytest
from test_corpus_rel_view import RULE, WINDOW, _lab, _work

pytestmark = pytest.mark.domain_corpus

SRULE = {"exclude": ["hijacked", "kanalregisteret"], "ngo_research_in_b": True,
         "unknown_venue": "keep", "tiers": ["A", "B"], "drop_publishers": []}


def _dim(wk, contrib, stage="2", model="m", run_id="r", field="economics"):
    return {"work_key": wk, "stage": stage, "labeller": "llm", "model": model,
            "prompt_sha256": "p", "run_id": run_id, "machine": "padme", "contrib": contrib,
            "field": field, "contrib_type": "empirical", "labelled_at": "2026-10-01",
            "source": "s"}


def _ven(wk, tier="A", flags="", ngo_not_b=None, publisher=""):
    return {"work_key": wk, "tier": tier, "tier_ngo_in_b": tier,
            "tier_ngo_not_b": tier if ngo_not_b is None else ngo_not_b,
            "flags": flags, "publisher_flag": publisher, "venue_key": f"v:{wk}"}


# W1 included; W2 ICF out; W3 ICF pending; W4 discipline no; W5 no dimension row;
# W6 tier C; W7 Kanalregisteret level X; W8 discipline no AND tier C (order rule).
POOL = [_work(f"openalex:W{i}", oas=f"W{i}") for i in range(1, 9)]
LABELS = [_lab("openalex:W1", "2", "icf"), _lab("openalex:W2", "2", "out"),
          _lab("openalex:W3", "1", "icf")] + [
          _lab(f"openalex:W{i}", "2", "icf") for i in range(4, 9)]
DIMS = [_dim("openalex:W1", "yes"), _dim("openalex:W4", "no", field="data_science"),
        _dim("openalex:W6", "yes"), _dim("openalex:W7", "yes"),
        _dim("openalex:W8", "no", field="finance")]
VENUES = {f"openalex:W{i}": _ven(f"openalex:W{i}") for i in range(1, 9)}
VENUES["openalex:W6"] = _ven("openalex:W6", tier="C")
VENUES["openalex:W7"] = _ven("openalex:W7", flags="kanalregisteret:123[issn]")
VENUES["openalex:W8"] = _ven("openalex:W8", tier="C")


def _rows(pool=POOL, labels=LABELS, dims=DIMS, venues=VENUES, srule=SRULE):
    rows, _ = rv.build_view(pool, labels, WINDOW, RULE)
    summary = rr.assign(rows, pool, dims, venues, srule)
    return rows, summary


def _reasons(rows):
    return {r["work_key"]: r["rel_reason"] for r in rows}


def test_each_work_gets_one_reason():
    rows, _ = _rows()
    assert _reasons(rows) == {
        "openalex:W1": "included", "openalex:W2": "icf_excluded",
        "openalex:W3": "icf_pending", "openalex:W4": "discipline_excluded",
        "openalex:W5": "discipline_pending", "openalex:W6": "seriousness_excluded",
        "openalex:W7": "seriousness_excluded", "openalex:W8": "discipline_excluded"}
    by = {r["work_key"]: r for r in rows}
    assert by["openalex:W6"]["rel_reason_detail"] == "tier_c"
    assert by["openalex:W7"]["rel_reason_detail"] == "registry:kanalregisteret"
    assert by["openalex:W2"]["rel_reason_detail"] == "out"
    assert by["openalex:W1"]["rel_final"] == "true"
    assert {r["rel_final"] for r in rows if r["work_key"] != "openalex:W1"} == {"false"}


def test_order_rule_discipline_before_seriousness():
    # Red test of the order: W8 fails discipline and seriousness; it is counted
    # once, by discipline, the earlier reason. Seriousness-first would give
    # seriousness_excluded.
    rows, _ = _rows()
    w8 = next(r for r in rows if r["work_key"] == "openalex:W8")
    assert w8["rel_reason"] == "discipline_excluded"
    assert w8["seriousness"] == "tier_c"  # still recorded, never counted
    counts = rr.reason_counts(rows)
    assert counts["works"]["seriousness_excluded"] == 2
    assert counts["works"]["discipline_excluded"] == 2


def test_icf_before_discipline():
    # An ICF-excluded work with a contrib "no" row stays an ICF exclusion.
    dims = DIMS + [_dim("openalex:W2", "no")]
    rows, _ = _rows(dims=dims)
    assert _reasons(rows)["openalex:W2"] == "icf_excluded"


def test_counts_sum_to_pool_and_order_is_fixed():
    rows, _ = _rows()
    counts = rr.reason_counts(rows)
    assert list(counts["works"]) == rr.REASONS
    assert sum(counts["works"].values()) == len(POOL)
    assert sum(counts["families"].values()) == len(POOL)


def test_discipline_pending_is_explicit_and_broken_down_by_seriousness():
    pool = POOL + [_work("openalex:W9", oas="W9")]
    labels = LABELS + [_lab("openalex:W9", "2", "icf")]
    venues = dict(VENUES, **{"openalex:W9": _ven("openalex:W9", tier="C")})
    rows, _ = _rows(pool=pool, labels=labels, venues=venues)
    counts = rr.reason_counts(rows)
    assert counts["works"]["discipline_pending"] == 2   # W5, W9
    assert counts["discipline_pending_by_seriousness"] == {"pass": 1, "tier_c": 1}
    w9 = next(r for r in rows if r["work_key"] == "openalex:W9")
    assert w9["rel_final"] == "false" and w9["contrib"] == ""


def test_no_dimension_table_makes_every_icf_work_pending():
    rows, _ = _rows(dims=[])
    reasons = _reasons(rows)
    assert {k for k, v in reasons.items() if v == "discipline_pending"} == {
        f"openalex:W{i}" for i in (1, 4, 5, 6, 7, 8)}


def test_discipline_unsure_is_kept_and_flagged():
    dims = [d for d in DIMS if d["work_key"] != "openalex:W1"] + [_dim("openalex:W1", "unsure")]
    rows, _ = _rows(dims=dims)
    w1 = next(r for r in rows if r["work_key"] == "openalex:W1")
    assert (w1["rel_reason"], w1["discipline_flag"]) == ("included", "unsure")


def test_forward_row_joining_the_deciding_label_wins():
    # Deciding stage-2 label is run r2; its dimension row says yes. A catch-up
    # row (later in the table) says no, and an older stage-2 run says no.
    labels = [_lab("openalex:W1", "2", "icf", run_id="r1"),
              _lab("openalex:W1", "2", "icf", run_id="r2")]
    dims = [_dim("openalex:W1", "no", run_id="r1"), _dim("openalex:W1", "yes", run_id="r2"),
            _dim("openalex:W1", "no", stage="catchup", run_id="c1")]
    rows, summary = _rows(pool=POOL[:1], labels=labels, dims=dims)
    assert (rows[0]["contrib"], rows[0]["discipline_source"]) == ("yes", "stage2")
    assert summary["dimension_rows_unused"] == 2


def test_empty_stage2_run_never_matches_an_empty_dimension_run():
    # A work with no stage-2 label (ICF from stage 1 under another rule) must not
    # pick up a stage-2 dimension row whose run_id is blank.
    row = {"stage2_model": "", "stage2_run_id": ""}
    win, unused, _ = rr.discipline_of(row, [_dim("openalex:W1", "no", model="", run_id="")])
    assert win is None and unused == 1


def test_disagreeing_candidate_rows_are_counted():
    labels = [_lab("openalex:W1", "2", "icf", run_id="v1")]
    dims = [_dim("openalex:W1", "yes", stage="catchup", run_id="c1"),
            _dim("openalex:W1", "no", stage="catchup", run_id="c2")]
    _, summary = _rows(pool=POOL[:1], labels=labels, dims=dims)
    assert summary["works_with_disagreeing_dimension_rows"] == 1


def test_catchup_row_used_when_no_forward_row_last_one_wins():
    labels = [_lab("openalex:W1", "2", "icf", run_id="v1")]
    dims = [_dim("openalex:W1", "yes", stage="catchup", run_id="c1"),
            _dim("openalex:W1", "no", stage="catchup", run_id="c2"),
            _dim("openalex:W1", "yes", stage="audit", model="fable")]
    rows, summary = _rows(pool=POOL[:1], labels=labels, dims=dims)
    assert (rows[0]["contrib"], rows[0]["discipline_source"]) == ("no", "catchup")
    assert rows[0]["rel_reason"] == "discipline_excluded"
    assert summary["dimension_rows_unused"] == 2


def test_dimension_rows_match_by_member_openalex_id():
    pool = [_work("openalex:W1", oas="W1;W10")]
    labels = [_lab("openalex:W10", "2", "icf")]
    rows, _ = _rows(pool=pool, labels=labels, dims=[_dim("openalex:W10", "no")])
    assert rows[0]["rel_reason"] == "discipline_excluded"


def test_registry_switch_and_title_matches():
    v = _ven("x", flags="scopus_discontinued:1[issn];doaj_withdrawn:2[title]")
    assert rr.seriousness_of(v, SRULE) == ""
    wide = dict(SRULE, exclude=SRULE["exclude"] + ["scopus_discontinued", "doaj_withdrawn"])
    assert rr.seriousness_of(v, wide) == "registry:scopus_discontinued"  # title never excludes
    assert rr.seriousness_of(_ven("x", flags="hijacked:h[domain]"), SRULE) == "registry:hijacked"


def test_registry_reason_comes_before_tier_c():
    v = _ven("x", tier="C", flags="kanalregisteret:1[issn]")
    assert rr.seriousness_of(v, SRULE) == "registry:kanalregisteret"


def test_ngo_switch_and_tier_and_publisher_settings():
    ngo = _ven("x", tier="B", ngo_not_b="C")
    assert rr.seriousness_of(ngo, SRULE) == ""
    assert rr.seriousness_of(ngo, dict(SRULE, ngo_research_in_b=False)) == "tier_c"
    assert rr.seriousness_of(_ven("x", tier="B"), dict(SRULE, tiers=["A"])) == "tier_c"
    mdpi = _ven("x", publisher="mdpi")
    assert rr.seriousness_of(mdpi, SRULE) == ""
    assert rr.seriousness_of(mdpi, dict(SRULE, drop_publishers=["mdpi"])) == "publisher:mdpi"


def test_unknown_tier_is_kept_flagged_by_default_never_tier_c():
    v = _ven("x", tier="unknown")
    assert rr.seriousness_of(v, SRULE) == ""
    assert rr.seriousness_of(v, dict(SRULE, unknown_venue="exclude")) == "tier_unknown"
    venues = dict(VENUES, **{"openalex:W1": _ven("openalex:W1", tier="unknown")})
    rows, _ = _rows(venues=venues)
    w1 = next(r for r in rows if r["work_key"] == "openalex:W1")
    assert (w1["rel_reason"], w1["seriousness_flag"]) == ("included", "unknown_venue")
    table = {r["scenario"]: r for r in rr.sensitivity(rows, venues, SRULE)}
    assert table["default"]["included_works"] == 1
    assert table["unknown_venue_flipped"]["included_works"] == 0


def test_switch_c_value_is_checked(monkeypatch):
    monkeypatch.setattr(rr.rvn, "unknown_switch", lambda cfg: cfg["c"], raising=False)
    assert rr.seriousness_rule({}, {"c": "exclude"})["unknown_venue"] == "exclude"
    with pytest.raises(ValueError, match="switch"):
        rr.seriousness_rule({}, {"c": "drop"})


def test_missing_venue_row_is_refused():
    venues = {k: v for k, v in VENUES.items() if k != "openalex:W5"}
    with pytest.raises(ValueError, match="rel-venues"):
        _rows(venues=venues)


def _family_pool():
    # A working paper (tier B, included) and its article (tier C venue).
    wp = _work("openalex:W31", oas="W31", year="2021", version_hint="W72")
    wp["doc_type"] = "report"
    art = _work("openalex:W72", oas="W72", year="2022")
    art["doc_type"] = "journal-article"
    return [wp, art]


def test_family_counts_once_and_any_passing_member_keeps_it():
    pool = _family_pool()
    labels = [_lab("openalex:W31", "2", "icf"), _lab("openalex:W72", "2", "icf")]
    dims = [_dim("openalex:W31", "yes"), _dim("openalex:W72", "yes")]
    venues = {"openalex:W31": _ven("openalex:W31", tier="B"),
              "openalex:W72": _ven("openalex:W72", tier="C")}
    rows, _ = _rows(pool=pool, labels=labels, dims=dims, venues=venues)
    assert {r["rel_family_id"] for r in rows} == {"openalex:W31"}
    counts = rr.reason_counts(rows)
    assert counts["families"]["included"] == 1
    assert sum(counts["families"].values()) == 1
    assert counts["works"]["seriousness_excluded"] == 1


def test_family_prefers_the_article_among_included_members():
    pool = _family_pool()
    labels = [_lab("openalex:W31", "2", "icf"), _lab("openalex:W72", "2", "icf")]
    dims = [_dim("openalex:W31", "yes"), _dim("openalex:W72", "yes")]
    venues = {k: _ven(k) for k in ("openalex:W31", "openalex:W72")}
    rows, _ = _rows(pool=pool, labels=labels, dims=dims, venues=venues)
    assert {r["rel_family_id"] for r in rows} == {"openalex:W72"}


def test_family_pending_member_beats_an_excluded_article():
    pool = _family_pool()
    labels = [_lab("openalex:W31", "2", "icf"), _lab("openalex:W72", "2", "out")]
    venues = {k: _ven(k) for k in ("openalex:W31", "openalex:W72")}
    rows, _ = _rows(pool=pool, labels=labels, dims=[], venues=venues)
    counts = rr.reason_counts(rows)
    assert counts["families"] == dict.fromkeys(rr.REASONS, 0) | {"discipline_pending": 1}


def test_sensitivity_rows():
    pool = POOL + [_work("openalex:W9", oas="W9"), _work("openalex:W10", oas="W10")]
    labels = LABELS + [_lab("openalex:W9", "2", "icf"), _lab("openalex:W10", "2", "icf")]
    dims = DIMS + [_dim("openalex:W9", "yes"), _dim("openalex:W10", "yes")]
    venues = dict(VENUES, **{
        "openalex:W9": _ven("openalex:W9", publisher="mdpi"),
        "openalex:W10": _ven("openalex:W10", tier="B",
                             flags="scopus_discontinued:9[issn]")})
    rows, _ = _rows(pool=pool, labels=labels, dims=dims, venues=venues)
    table = {r["scenario"]: r for r in rr.sensitivity(rows, venues, SRULE)}
    assert table["default"]["included_works"] == 3          # W1, W9, W10
    assert table["publishers_dropped"]["included_works"] == 2
    assert table["drop_mdpi"]["included_works"] == 2
    assert table["drop_frontiers"]["included_works"] == 3
    assert table["tier_a_only"]["included_works"] == 2
    assert table["registries_plus_scopus_doaj"]["included_works"] == 2
    assert table["kanalregisteret_flipped"]["exclude_registries"] == "hijacked"
    assert table["ngo_research_flipped"]["included_works"] == 3
    assert all(r["discipline_pending_works"] == 1 for r in table.values())
    assert table["default"]["included_works"] == rr.reason_counts(rows)["works"]["included"]


def _files(tmp_path, dims=DIMS):
    pool = tmp_path / "pool.csv"
    with open(pool, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rv.POOL_FIELDS)
        w.writeheader()
        w.writerows(POOL)
    table = str(tmp_path / "rs" / "icf_screen.csv")
    (tmp_path / "rs").mkdir()
    ics.append_rows(table, LABELS)
    dims_path = str(tmp_path / "rs" / "rel_dimensions.csv")
    if dims:
        ics.append_rows(dims_path, dims, schema=ics.DIMENSIONS)
    venues = str(tmp_path / "rel_work_venues.csv")
    cols = ["work_key", "lanes", "venue_key", "venue_resolution", "tier", "tier_rule", "b_id",
            "tier_ngo_in_b", "tier_ngo_not_b", "flags", "flagged", "excluded", "excluded_by",
            "publisher_flag"]
    with open(venues, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for v in VENUES.values():
            w.writerow({c: v.get(c, "") for c in cols} | {"flagged": "false",
                                                            "excluded": "false"})
    return str(pool), table, dims_path, venues


def test_run_is_byte_identical_and_hashes_its_inputs(tmp_path):
    pool, table, dims, venues = _files(tmp_path)
    for out in ("a", "b"):
        crv.run(pool, table, str(tmp_path / out), WINDOW, RULE,
                dims_path=dims, venues_path=venues, seriousness_rule=SRULE)
    for name in ("rel_view.csv", "rel_counts.json", "rel_sensitivity.csv"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    counts = json.loads((tmp_path / "a" / "rel_counts.json").read_text())
    assert set(counts["inputs"]) == {"pool", "table", "dimensions", "venues"}
    assert counts["inputs"]["dimensions"]["sha256"] == rv.sha256_file(dims)
    assert counts["inputs"]["venues"]["sha256"] == rv.sha256_file(venues)
    assert counts["reasons"]["works"]["included"] == 1
    assert counts["rule"]["seriousness"] == SRULE
    assert "over-exclu" in counts["reasons"]["discipline_note"]


def test_run_without_a_dimension_table_records_it_absent(tmp_path):
    pool, table, dims, venues = _files(tmp_path, dims=[])
    counts = crv.run(pool, table, str(tmp_path / "a"), WINDOW, RULE,
                     dims_path=dims, venues_path=venues, seriousness_rule=SRULE)
    assert counts["inputs"]["dimensions"]["sha256"] is None
    assert counts["reasons"]["works"]["included"] == 0
    assert counts["reasons"]["works"]["discipline_pending"] == 6
