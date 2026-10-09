"""REL fuzzy membership and exclusion reasons: seriousness, ICF, discipline (ticket 1843)."""

import csv
import itertools
import json

import _icf_screen as ics
import _rel_reasons as rr
import _rel_view as rv
import corpus_rel_view as crv
import pytest
import yaml
from test_corpus_rel_view import ROOT, RULE, WINDOW, _lab, _work

pytestmark = pytest.mark.domain_corpus

# The decided seriousness facet (2026-10-01): hijacked journals exclude, Kanal X
# and Scopus/DOAJ only flag; NGO research in B; unknown venue kept at 0.5.
SRULE = {"exclude": ["hijacked"], "ngo_research_in_b": True, "no_venue": "keep_flagged",
         "nonresearch": "to_c", "alpha": 0.5,
         "tier_mu": {"A": 1.0, "B": 1.0, "C": 0.0, "unknown": 0.5},
         "tiers": ["A", "B"], "drop_publishers": []}
MRULE = {"status": "proposed", "icf": {"icf": 1.0, "unsure": 0.5, "aux": 0.0, "out": 0.0},
         "discipline": {"yes": 1.0, "unsure": 0.5, "no": 0.0}, "family": "max"}


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
# W6 tier C; W7 hijacked clone; W8 discipline no AND tier C (order rule).
POOL = [_work(f"openalex:W{i}", oas=f"W{i}") for i in range(1, 9)]
LABELS = [_lab("openalex:W1", "2", "icf"), _lab("openalex:W2", "2", "out"),
          _lab("openalex:W3", "1", "icf")] + [
          _lab(f"openalex:W{i}", "2", "icf") for i in range(4, 9)]
DIMS = [_dim("openalex:W1", "yes"), _dim("openalex:W4", "no", field="data_science"),
        _dim("openalex:W6", "yes"), _dim("openalex:W7", "yes"),
        _dim("openalex:W8", "no", field="finance")]
VENUES = {f"openalex:W{i}": _ven(f"openalex:W{i}") for i in range(1, 9)}
VENUES["openalex:W6"] = _ven("openalex:W6", tier="C")
VENUES["openalex:W7"] = _ven("openalex:W7", flags="hijacked:h1[domain];kanalregisteret:9[issn]")
VENUES["openalex:W8"] = _ven("openalex:W8", tier="C")


def _rows(pool=POOL, labels=LABELS, dims=DIMS, venues=VENUES, srule=SRULE):
    rows, _ = rv.build_view(pool, labels, WINDOW, RULE)
    summary = rr.assign(rows, pool, dims, venues, srule, MRULE)
    return rows, summary


def _reasons(rows):
    return {r["work_key"]: r["rel_reason"] for r in rows}


def _by(rows):
    return {r["work_key"]: r for r in rows}


def test_each_work_gets_one_reason():
    rows, _ = _rows()
    assert _reasons(rows) == {
        "openalex:W1": "included", "openalex:W2": "icf_excluded",
        "openalex:W3": "icf_pending", "openalex:W4": "discipline_excluded",
        "openalex:W5": "discipline_pending", "openalex:W6": "seriousness_excluded",
        "openalex:W7": "seriousness_excluded", "openalex:W8": "seriousness_excluded"}
    by = _by(rows)
    assert by["openalex:W6"]["rel_reason_detail"] == "tier_c"
    assert by["openalex:W7"]["rel_reason_detail"] == "registry:hijacked"  # Kanal X only flags
    assert by["openalex:W2"]["rel_reason_detail"] == "out"
    assert (by["openalex:W1"]["rel_final"], by["openalex:W1"]["mu"]) == ("true", "1")
    assert {r["rel_final"] for r in rows if r["work_key"] != "openalex:W1"} == {"false"}


def test_order_rule_seriousness_first_by_cost():
    # Red test of the order: W8 fails seriousness and discipline; evaluation is
    # cheapest first and stops at the first 0, so it is a seriousness exclusion
    # and discipline is not graded. Discipline-first would give discipline_excluded.
    rows, _ = _rows()
    w8 = _by(rows)["openalex:W8"]
    assert (w8["rel_reason"], w8["mu_facet"]) == ("seriousness_excluded", "seriousness")
    assert (w8["mu_seriousness"], w8["mu_icf"], w8["mu_discipline"]) == ("0", "", "")
    assert w8["contrib"] == "no"  # still recorded on the row, never counted
    counts = rr.reason_counts(rows)
    assert counts["works"]["seriousness_excluded"] == 3
    assert counts["works"]["discipline_excluded"] == 1


def test_icf_before_discipline():
    rows, _ = _rows(dims=DIMS + [_dim("openalex:W2", "no")])
    assert _reasons(rows)["openalex:W2"] == "icf_excluded"


def test_na_never_attains_the_minimum():
    # contrib na is the answer for a work labelled out: ICF gives 0 first.
    rows, _ = _rows(dims=DIMS + [_dim("openalex:W2", "na")])
    w2 = _by(rows)["openalex:W2"]
    assert (w2["mu_facet"], w2["mu_discipline"]) == ("icf", "")


def test_counts_sum_to_pool_and_order_is_fixed():
    rows, _ = _rows()
    counts = rr.reason_counts(rows)
    assert counts["facet_order"] == ["seriousness", "icf", "discipline"]
    assert list(counts["works"]) == rr.REASONS
    assert sum(counts["works"].values()) == len(POOL)
    assert sum(counts["families"].values()) == len(POOL)


def test_discipline_pending_is_explicit():
    rows, _ = _rows()
    w5 = _by(rows)["openalex:W5"]
    assert (w5["rel_final"], w5["mu"], w5["mu_complete"]) == ("false", "1", "false")
    assert rr.reason_counts(rows)["discipline_pending_by_tier_works"] == {"A": 1}


def test_no_dimension_table_makes_every_icf_work_pending():
    rows, _ = _rows(dims=[])
    reasons = _reasons(rows)
    assert {k for k, v in reasons.items() if v == "discipline_pending"} == {
        "openalex:W1", "openalex:W4", "openalex:W5"}


def test_discipline_unsure_is_kept_and_flagged_at_half_membership():
    dims = [d for d in DIMS if d["work_key"] != "openalex:W1"] + [_dim("openalex:W1", "unsure")]
    rows, _ = _rows(dims=dims)
    w1 = _by(rows)["openalex:W1"]
    assert (w1["rel_reason"], w1["discipline_flag"], w1["mu"], w1["mu_facet"]) == (
        "included", "unsure", "0.5", "discipline")


def _with_abstracts(blank):
    """POOL with an abstract on every work except those in ``blank`` (whitespace counts as blank)."""
    return [dict(w, abstract="   " if w["work_key"] in blank else "An abstract.") for w in POOL]


def test_no_abstract_facet_keeps_the_work_in_rel_outside_the_synthesis_tier():
    # Author decision 2026-10-07 (tickets 1733, 1843): a work with no abstract
    # (blank after trimming, the rule of the 1842 catch-up build) counts in the
    # bibliometric analysis only. The facet never moves mu or rel_final; it
    # splits the REL set into the synthesis tier and the bibliometric-only rest.
    pool = _with_abstracts({"openalex:W1", "openalex:W5", "openalex:W2"})
    rows, _ = _rows(pool=pool)
    by = _by(rows)
    assert _reasons(rows) == _reasons(_rows()[0])  # reasons unchanged by the facet
    assert by["openalex:W1"]["abstract_flag"] == "no_abstract"
    assert (by["openalex:W1"]["rel_final"], by["openalex:W1"]["rel_use"]) == (
        "true", "bibliometric_only")
    assert by["openalex:W3"]["abstract_flag"] == ""
    assert by["openalex:W2"]["rel_use"] == ""  # not in REL: no use
    rows2, _ = _rows(pool=_with_abstracts(set()))
    assert _by(rows2)["openalex:W1"]["rel_use"] == "synthesis"


def test_no_abstract_counts_by_reason():
    pool = _with_abstracts({"openalex:W1", "openalex:W5", "openalex:W2"})
    counts = rr.reason_counts(_rows(pool=pool)[0])
    assert counts["no_abstract_by_reason_works"] == {
        "discipline_pending": 1, "icf_excluded": 1, "included": 1}
    assert counts["included_by_use_works"] == {"bibliometric_only": 1}
    assert counts["no_abstract_note"] == rr.NO_ABSTRACT_NOTE


def _crisp(status, contrib, tier, flags):
    """The crisp rules before the fuzzy model (1830 decisions, 2026-10-01 switches)."""
    if "hijacked" in flags or tier == "C":
        return False
    if status not in ("icf", "unsure_unresolved"):
        return False
    return contrib in ("yes", "unsure", "na", "unknown")


def test_crisp_rules_are_the_alpha_cut():
    statuses = ["icf", "unsure_unresolved", "aux", "out", "stage1_out"]
    contribs = ["yes", "unsure", "no", "na", "unknown"]
    tiers = ["A", "B", "C", "unknown"]
    flags = ["", "hijacked:h[domain]", "kanalregisteret:1[issn]", "scopus_discontinued:2[issn]"]
    for status, contrib, tier, flag in itertools.product(statuses, contribs, tiers, flags):
        row = {"status": status, "contrib": contrib, "discipline_field": ""}
        ev = rr.evaluate(rr._facet_values(row, _ven("x", tier=tier, flags=flag), SRULE, MRULE),
                         SRULE["alpha"])
        assert (ev["rel_reason"] == "included") == _crisp(status, contrib, tier, flag), (
            status, contrib, tier, flag)


@pytest.mark.parametrize("values,alpha,expect", [
    # (facet values in order), alpha -> (mu, mu_facet, complete, reason)
    ([("s", 1.0, ""), ("i", None, ""), ("d", None, "")], 0.5, (1.0, "s", False, "i_pending")),
    ([("s", 0.5, ""), ("i", 1.0, ""), ("d", None, "")], 0.5, (0.5, "s", False, "d_pending")),
    ([("s", 0.5, ""), ("i", None, ""), ("d", None, "")], 0.8, (0.5, "s", True, "s_excluded")),
    ([("s", 1.0, ""), ("i", 0.5, ""), ("d", 0.5, "")], 0.5, (0.5, "i", True, "included")),
    ([("s", 1.0, ""), ("i", 0.0, "out"), ("d", 1.0, "")], 0.5, (0.0, "i", True, "i_excluded")),
])
def test_evaluate_mu_is_the_min_of_the_graded_facets(values, alpha, expect):
    ev = rr.evaluate(values, alpha)
    assert (ev["mu"], ev["mu_facet"], ev["mu_complete"], ev["rel_reason"]) == expect


def test_forward_row_joining_the_deciding_label_wins():
    labels = [_lab("openalex:W1", "2", "icf", run_id="r1"),
              _lab("openalex:W1", "2", "icf", run_id="r2")]
    dims = [_dim("openalex:W1", "no", run_id="r1"), _dim("openalex:W1", "yes", run_id="r2"),
            _dim("openalex:W1", "no", stage="catchup", run_id="c1")]
    rows, summary = _rows(pool=POOL[:1], labels=labels, dims=dims)
    assert (rows[0]["contrib"], rows[0]["discipline_source"]) == ("yes", "stage2")
    assert summary["dimension_rows_unused"] == 2


def test_empty_stage2_run_never_matches_an_empty_dimension_run():
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
    rows, _ = _rows(pool=pool, labels=labels, dims=[_dim("openalex:W10", "no")],
                    venues={"openalex:W1": _ven("openalex:W1")})
    assert rows[0]["rel_reason"] == "discipline_excluded"


def test_registry_switch_and_title_matches():
    v = _ven("x", flags="scopus_discontinued:1[issn];doaj_withdrawn:2[title]")
    assert rr.seriousness_of(v, SRULE) == (1.0, "")
    wide = dict(SRULE, exclude=SRULE["exclude"] + ["scopus_discontinued", "doaj_withdrawn"])
    assert rr.seriousness_of(v, wide) == (0.0, "registry:scopus_discontinued")
    assert rr.seriousness_of(_ven("x", flags="hijacked:h[domain]"), SRULE) == (
        0.0, "registry:hijacked")
    kanal = _ven("x", flags="kanalregisteret:1[issn]")
    assert rr.seriousness_of(kanal, SRULE) == (1.0, "")                 # flag only
    assert rr.seriousness_of(kanal, dict(SRULE, exclude=["hijacked", "kanalregisteret"]))[0] == 0


def test_registry_reason_comes_before_tier_c():
    v = _ven("x", tier="C", flags="hijacked:1[domain]")
    assert rr.seriousness_of(v, SRULE) == (0.0, "registry:hijacked")


def test_ngo_switch_and_tier_and_publisher_settings():
    ngo = _ven("x", tier="B", ngo_not_b="C")
    assert rr.seriousness_of(ngo, SRULE) == (1.0, "")
    assert rr.seriousness_of(ngo, dict(SRULE, ngo_research_in_b=False)) == (0.0, "tier_c")
    assert rr.seriousness_of(_ven("x", tier="B"), dict(SRULE, tiers=["A"])) == (0.0, "tier_b")
    mdpi = _ven("x", publisher="mdpi")
    assert rr.seriousness_of(mdpi, SRULE) == (1.0, "")
    assert rr.seriousness_of(mdpi, dict(SRULE, drop_publishers=["mdpi"])) == (
        0.0, "publisher:mdpi")


def test_unknown_tier_is_half_member_kept_flagged_never_tier_c():
    v = _ven("x", tier="unknown")
    assert rr.seriousness_of(v, SRULE) == (0.5, "")
    assert rr.seriousness_of(v, dict(SRULE, no_venue="exclude")) == (0.0, "tier_unknown")
    venues = dict(VENUES, **{"openalex:W1": _ven("openalex:W1", tier="unknown")})
    rows, _ = _rows(venues=venues)
    w1 = _by(rows)["openalex:W1"]
    assert (w1["rel_reason"], w1["seriousness_flag"], w1["mu"], w1["mu_facet"]) == (
        "included", "no_venue", "0.5", "seriousness")
    table = {r["scenario"]: r for r in rr.sensitivity(rows, venues, SRULE, MRULE)}
    assert (table["default"]["included_works"], table["default"]["included_mu_weighted"]) == (
        1, "0.5")
    assert table["no_venue_flipped"]["included_works"] == 0


def test_nonresearch_switch_reads_the_tier_without_it():
    v = dict(_ven("x", tier="C"), tier_without_nonresearch="B")
    assert rr.seriousness_of(v, SRULE) == (0.0, "tier_c")
    assert rr.seriousness_of(v, dict(SRULE, nonresearch="off")) == (1.0, "")
    venues = dict(VENUES, **{"openalex:W6": dict(_ven("openalex:W6", tier="C"),
                                                 tier_without_nonresearch="B")})
    rows, _ = _rows(venues=venues)
    table = {r["scenario"]: r for r in rr.sensitivity(rows, venues, SRULE, MRULE)}
    assert table["default"]["included_works"] == 1
    assert table["nonresearch_flipped"]["included_works"] == 2


def test_ngo_row_dropped_when_the_table_was_built_without_nonresearch():
    names = [n for n, _ in rr._scenarios(dict(SRULE, nonresearch="off"))]
    assert "ngo_research_flipped" not in names and "nonresearch_flipped" not in names
    assert {"ngo_research_flipped", "nonresearch_flipped"} <= {n for n, _ in rr._scenarios(SRULE)}


def test_seriousness_rule_reads_the_decided_configs():
    def load(name):
        with open(f"{ROOT}/config/{name}", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    srule = rr.seriousness_rule(load("rel_venue_registries.yaml"), load("rel_venue_tiers.yaml"))
    evidence = srule.pop("evidence")  # ticket 2042; its own tests: test_rel_venue_evidence.py
    assert srule == SRULE
    assert evidence["conflict"] == 0.5 and evidence["other_c"] == 0.0  # conflict: author decision 2026-10-09


def test_membership_rule_checks_values_and_the_unsure_exit():
    cfg = {"membership": {"status": "proposed", "icf": dict(MRULE["icf"]),
                          "discipline": dict(MRULE["discipline"]),
                          "family": {"value": "max"}}}
    assert rr.membership_rule(cfg, RULE, 0.5) == MRULE
    with pytest.raises(ValueError, match="stage2_unsure_in_rel"):
        rr.membership_rule(cfg, dict(RULE, stage2_unsure_in_rel=False), 0.5)
    bad = {"membership": dict(cfg["membership"], discipline={"yes": 1, "no": 0})}
    with pytest.raises(ValueError, match="discipline"):
        rr.membership_rule(bad, RULE, 0.5)
    for facet, key, value in (("icf", "aux", 0.6), ("icf", "icf", 0.4),
                              ("discipline", "no", 0.5), ("discipline", "unsure", 0.4)):
        m = dict(cfg["membership"], **{facet: dict(cfg["membership"][facet], **{key: value})})
        with pytest.raises(ValueError, match=f"membership.{facet}"):
            rr.membership_rule({"membership": m}, RULE, 0.5)
    with pytest.raises(ValueError, match="family"):
        rr.membership_rule({"membership": dict(cfg["membership"], family={"value": "min"})},
                           RULE, 0.5)


def test_config_membership_block_parses_with_quoted_yes_no():
    with open(f"{ROOT}/config/rel_screen.yaml", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    assert rr.membership_rule(cfg, rv.screen_rule(cfg), 0.5)["discipline"]["yes"] == 1


def test_missing_venue_row_is_refused():
    venues = {k: v for k, v in VENUES.items() if k != "openalex:W5"}
    with pytest.raises(ValueError, match="rel-venues"):
        _rows(venues=venues)


def _family_pool():
    wp = _work("openalex:W31", oas="W31", year="2021", version_hint="W72")
    wp["doc_type"] = "report"
    art = _work("openalex:W72", oas="W72", year="2022")
    art["doc_type"] = "journal-article"
    return [wp, art]


def _family(dims, venues, labels=None):
    labels = labels or [_lab("openalex:W31", "2", "icf"), _lab("openalex:W72", "2", "icf")]
    return _rows(pool=_family_pool(), labels=labels, dims=dims, venues=venues)[0]


def test_family_membership_is_the_max_over_members():
    # Working paper tier B (mu 1), article tier C (mu 0): the family is in.
    rows = _family([_dim("openalex:W31", "yes"), _dim("openalex:W72", "yes")],
                   {"openalex:W31": _ven("openalex:W31", tier="B"),
                    "openalex:W72": _ven("openalex:W72", tier="C")})
    assert {r["rel_family_id"] for r in rows} == {"openalex:W31"}
    counts = rr.reason_counts(rows)
    assert counts["families"]["included"] == 1 and sum(counts["families"].values()) == 1
    assert counts["works"]["seriousness_excluded"] == 1


def test_family_prefers_the_article_at_equal_membership():
    rows = _family([_dim("openalex:W31", "yes"), _dim("openalex:W72", "yes")],
                   {k: _ven(k) for k in ("openalex:W31", "openalex:W72")})
    assert {r["rel_family_id"] for r in rows} == {"openalex:W72"}


def test_family_prefers_higher_membership_over_the_article():
    # Article from an unknown venue (0.5), working paper in B (1): the max is the WP.
    rows = _family([_dim("openalex:W31", "yes"), _dim("openalex:W72", "yes")],
                   {"openalex:W31": _ven("openalex:W31", tier="B"),
                    "openalex:W72": _ven("openalex:W72", tier="unknown")})
    assert {r["rel_family_id"] for r in rows} == {"openalex:W31"}


def test_family_pending_member_beats_an_excluded_article():
    rows = _family([], {k: _ven(k) for k in ("openalex:W31", "openalex:W72")},
                   labels=[_lab("openalex:W31", "2", "icf"), _lab("openalex:W72", "2", "out")])
    counts = rr.reason_counts(rows)
    assert counts["families"] == dict.fromkeys(rr.REASONS, 0) | {"discipline_pending": 1}


def test_mixed_family_counts_as_included_not_pending():
    # One included member, one discipline-pending member: under family MAX the
    # family is included, so it is not counted among the pending families.
    venues = {k: _ven(k) for k in ("openalex:W31", "openalex:W72")}
    rows = _family([_dim("openalex:W31", "yes"), _dim("openalex:W72", "")], venues)
    assert sorted(r["rel_reason"] for r in rows) == ["discipline_pending", "included"]
    table = {r["scenario"]: r for r in rr.sensitivity(rows, venues, SRULE, MRULE)}
    assert table["default"]["included_families"] == 1
    assert table["default"]["discipline_pending_families"] == 0
    assert table["default"]["discipline_pending_works"] == 1
    for r in rows:
        r.update(doc_type="research", rel_disposition="include", rel_year_status="complete")
    win = crv._in_window(rows)
    assert win["included_families"] == 1 and win["discipline_pending_families"] == 0
    assert win["discipline_pending_works"] == 1


def test_stage2_skip_counts_icf_pending_works_by_tier():
    pool = POOL + [_work("openalex:W9", oas="W9"), _work("openalex:W10", oas="W10")]
    labels = LABELS + [_lab("openalex:W9", "1", "aux")]
    venues = dict(VENUES, **{"openalex:W9": _ven("openalex:W9", tier="C"),
                             "openalex:W10": _ven("openalex:W10", tier="unknown")})
    rows, _ = _rows(pool=pool, labels=labels, venues=venues)
    skip = rr.stage2_skip(rows)
    assert skip["pending_stage2"] == {"by_tier": {"A": 1, "C": 1},
                                      "skippable_seriousness_0": 1, "to_screen": 1}
    assert skip["unscreened"] == {"by_tier": {"unknown": 1}, "skippable_seriousness_0": 0,
                                  "to_screen": 1}


def test_sensitivity_rows():
    pool = POOL + [_work("openalex:W9", oas="W9"), _work("openalex:W10", oas="W10")]
    labels = LABELS + [_lab("openalex:W9", "2", "icf"), _lab("openalex:W10", "2", "icf")]
    dims = DIMS + [_dim("openalex:W9", "yes"), _dim("openalex:W10", "yes")]
    venues = dict(VENUES, **{
        "openalex:W9": _ven("openalex:W9", publisher="mdpi"),
        "openalex:W10": _ven("openalex:W10", tier="B",
                             flags="scopus_discontinued:9[issn];kanalregisteret:3[issn]")})
    rows, _ = _rows(pool=pool, labels=labels, dims=dims, venues=venues)
    table = {r["scenario"]: r for r in rr.sensitivity(rows, venues, SRULE, MRULE)}
    assert table["default"]["included_works"] == 3          # W1, W9, W10
    assert table["publishers_dropped"]["included_works"] == 2
    assert table["drop_mdpi"]["included_works"] == 2
    assert table["drop_frontiers"]["included_works"] == 3
    assert table["tier_a_only"]["included_works"] == 2
    assert table["kanalregisteret_flipped"]["included_works"] == 2
    assert table["kanalregisteret_flipped"]["exclude_registries"] == "hijacked;kanalregisteret"
    assert table["registries_plus_scopus_doaj"]["included_works"] == 2
    assert table["ngo_research_flipped"]["included_works"] == 3
    assert all(r["discipline_pending_works"] == 1 for r in table.values())
    assert table["default"]["included_works"] == rr.reason_counts(rows)["works"]["included"]


def test_sensitivity_reevaluates_works_seriousness_had_stopped():
    # With MDPI dropped in the base setting, W1 stops at seriousness 0; the
    # drop_frontiers row keeps MDPI, so W1 is re-evaluated through ICF and
    # discipline and comes back.
    srule = dict(SRULE, drop_publishers=["mdpi"])
    venues = dict(VENUES, **{"openalex:W1": _ven("openalex:W1", publisher="mdpi")})
    rows, _ = _rows(venues=venues, srule=srule)
    assert _reasons(rows)["openalex:W1"] == "seriousness_excluded"
    table = {r["scenario"]: r for r in rr.sensitivity(rows, venues, srule, MRULE)}
    assert table["default"]["included_works"] == 0
    assert table["drop_frontiers"]["included_works"] == 1


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


def _run(tmp_path, out, dims, venues, pool, table):
    return crv.run(pool, table, str(tmp_path / out), WINDOW, RULE, dims_path=dims,
                   venues_path=venues, seriousness_rule=SRULE, membership=MRULE)


def test_run_is_byte_identical_and_hashes_its_inputs(tmp_path):
    pool, table, dims, venues = _files(tmp_path)
    for out in ("a", "b"):
        _run(tmp_path, out, dims, venues, pool, table)
    for name in ("rel_view.csv", "rel_counts.json", "rel_sensitivity.csv"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    counts = json.loads((tmp_path / "a" / "rel_counts.json").read_text())
    assert set(counts["inputs"]) == {"pool", "table", "dimensions", "venues"}
    assert counts["inputs"]["dimensions"]["sha256"] == rv.sha256_file(dims)
    assert counts["inputs"]["venues"]["sha256"] == rv.sha256_file(venues)
    assert counts["reasons"]["works"]["included"] == 1
    assert counts["rule"]["seriousness"] == SRULE
    assert counts["rule"]["membership"] == MRULE
    assert "over-exclu" in counts["reasons"]["discipline_note"]
    assert "stage2_skip" in counts


def test_run_without_a_dimension_table_records_it_absent(tmp_path):
    pool, table, dims, venues = _files(tmp_path, dims=[])
    counts = _run(tmp_path, "a", dims, venues, pool, table)
    assert counts["inputs"]["dimensions"]["sha256"] is None
    assert counts["reasons"]["works"]["included"] == 0
    assert counts["reasons"]["works"]["discipline_pending"] == 3


def test_run_records_the_dvc_version_of_the_append_only_tables(tmp_path):
    pool, table, dims, venues = _files(tmp_path)
    (tmp_path / "rs.dvc").write_text("outs:\n- md5: abc123.dir\n  path: rs\n")
    counts = _run(tmp_path, "a", dims, venues, pool, table)
    assert counts["inputs"]["table"]["dvc_md5"] == "abc123.dir"
    assert counts["inputs"]["dimensions"]["dvc_md5"] == "abc123.dir"
    assert "dvc_md5" not in counts["inputs"]["pool"]
