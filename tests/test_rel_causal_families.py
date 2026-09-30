"""The causal-map families partition the 126 arcs of Annex A (ticket 1652)."""

import os

import catalog_rel_causal_search as rc
import pytest
import yaml

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(__file__))


def _families():
    with open(os.path.join(ROOT, "config", "rel_causal_families.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_annex_a_has_the_announced_126_arcs():
    arcs = rc.parse_annex_arcs()
    assert len(arcs) == 126
    assert len(set(arcs)) == 126
    assert ("ICF", "ICF_decl") in arcs and ("Invest_prive", "Cap_charbon") in arcs


def test_every_arc_is_in_exactly_one_family():
    assert rc.partition_problems(_families()["families"], rc.parse_annex_arcs()) == []


def test_partition_check_catches_unassigned_duplicated_and_unknown_arcs():
    fams = {k: dict(v, arcs=list(v["arcs"])) for k, v in _families()["families"].items()}
    arcs = rc.parse_annex_arcs()
    fams["grid"]["arcs"].remove("Reseau -> Prod_zero")
    fams["debt"]["arcs"].append("ICF_E -> WACC")
    fams["fossil_finance"]["arcs"].append("ICF -> CO2_elec")
    problems = rc.partition_problems(fams, arcs)
    assert "unassigned arc Reseau -> Prod_zero" in problems
    assert any(p.startswith("duplicated arc ICF_E -> WACC") for p in problems)
    assert "unknown arc ICF -> CO2_elec in fossil_finance" in problems


def test_three_priority_groups_and_a_priori_expectations_are_recorded():
    fams = _families()["families"]
    assert {f["group"] for f in fams.values()} == {0, 1, 2, 3}
    for name, f in fams.items():
        assert f["a_priori"] in {"empirical", "theoretical"}, name
        assert f["kind"] in {"mechanism", "identity", "confounding", "intermediate"}, name
        assert f["mechanism"].strip(), name
        # a theoretical family is never a priority family, and names its kind
        if f["a_priori"] == "theoretical":
            assert f["group"] == 0 and f["kind"] != "mechanism", name
    assert {n for n, f in fams.items() if f["a_priori"] == "theoretical"} == {
        "confounding", "physical_identities", "deforestation_drivers"}


def test_map_free_themes_cover_the_protocol_list():
    themes = _families()["themes"]
    for t in ("adaptation", "forest_beyond_map", "loss_and_damage", "justice",
              "critical_approaches", "accounting_governance", "private_finance",
              "carbon_markets"):
        assert t in themes
