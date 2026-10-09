"""REL index evidence and mu_venue (ticket 2042): parsers, rule, red tests, switch, log."""

import hashlib
import os

import _rel_venue_registries as rvr
import _rel_venues as rv
import corpus_rel_venues as crv
import pytest
import test_rel_venues as tv
import yaml

pytestmark = pytest.mark.domain_corpus

PARAMS = rv.evidence_params(tv.TIERS_CFG)
PARAMS_HALF = dict(PARAMS, other_c=0.5)  # the open option: an unlisted C `other` is unknown
SCOPUS_HEAD = ["Sourcerecord ID", "Source Title", "ISSN", "EISSN", "Active or Inactive", "Coverage", "Source Type"]
SCOPUS_SOURCES = [
    ["1", "Revista Listada", "24681357", "", "Active", "2015-2025", "Journal"],
    ["2", "Academy of Management Annals", "19416520", "19416067", "Active", "2015-2025", "Journal"],
    ["3", "A Proceedings", "11112222", "", "Active", "2015-2025", "Conference Proceeding"],
]


# ── Parsers: what each index lists, and for which years ──


def test_kanal_lists_only_approved_years_without_projection(tmp_path):
    p = tmp_path / "k.csv"
    p.write_text('"Tidsskrift id","Original tittel","Print ISSN","Online ISSN","Nivå 2027","Nivå 2026","Nivå 2025","Nivå 2024"\n'
                 '"1","A","1111-1119","","","X","1","1"\n"2","B","2222-2228","","","0","",""\n', encoding="utf-8")
    rows, entries = rvr.parse_kanal_listed(str(p))
    assert rows == 2 and [e["entry_id"] for e in entries] == ["1"]
    assert entries[0]["spans"] == ((2024, 2025),)  # the X year of 2026 is not a listing


def test_scopus_sources_coverage_spans_and_types(tmp_path):
    p = str(tmp_path / "s.xlsx")
    tv.write_xlsx(p, {"Scopus Sources Aug. 2026": [SCOPUS_HEAD, *SCOPUS_SOURCES,
                                                   ["4", "Old", "33334444", "", "Inactive", "1999-2001; 2005", "Journal"]]})
    _, entries = rvr.parse_scopus_listed(p)
    assert {e["entry_id"]: e["spans"] for e in entries} == {
        "1": ((2015, 2025),), "2": ((2015, 2025),), "4": ((1999, 2001), (2005, 2005))}
    assert rvr.coverage_spans("2026; 2023-2024") == ((2023, 2024), (2026, 2026))


def test_doaj_span_runs_from_added_year_to_the_year_before_withdrawal(tmp_path):
    p = str(tmp_path / "d.xlsx")
    tv.write_xlsx(p, {
        "Added": [["Journal Title", "ISSN", "Date Added"], ["Kept", "1010-1014", "43000"],
                  ["Dropped", "2020-2026", "42000"]],
        "Withdrawn": [["Journal Title", "ISSN", "Date Removed (dd/mm/yyyy)", "Reason"],
                      ["Dropped", "2020-2026", "42800", "Ceased publishing"]]})
    _, entries = rvr.parse_doaj_listed([p], 2026)
    spans = {e["title"]: e["spans"] for e in entries}
    assert spans["Kept"] == ((2017, 2026),) and spans["Dropped"] == ((2014, 2016),)


def test_hits_are_evaluated_at_the_publication_year():
    e = {"registry": "scopus", "entry_id": "1", "spans": ((2015, 2025),)}
    assert rv.hits_text(rv.hits_at([e], -1, 2020)) == "scopus:1[2015-2025]"
    assert rv.hits_at([e], -1, 2010) == [] and rv.hits_at([e], -1, None) == []
    assert rv.hits_text(rv.hits_at([], 0, None)) == "university_press:0[*]"


# ── The rule ─────────────────────────────────────────────


def test_absence_from_every_index_is_never_zero_unless_positively_unserious():
    for tier, rule, expected in [("A", "journal", 1), ("B", "b_series", 1), ("unknown", "no_venue", 0.5),
                                 ("C", "other", 0), ("C", "repository", 0), ("C", "nonresearch", 0)]:
        assert rv.mu_venue(tier, rule, [], False, PARAMS)[0] == expected, (tier, rule)


def test_index_is_positive_evidence_and_or_combined():
    assert rv.mu_venue("unknown", "no_venue", ["scopus"], False, PARAMS) == (1.0, "index")
    assert rv.mu_venue("A", "journal", ["doaj", "scopus"], False, PARAMS) == (1.0, "tier_ab")
    assert rv.mu_venue("C", "other", ["scopus"], False, dict(PARAMS, indexes=[])) == (0.0, "unlisted")  # dropped
    assert rv.mu_venue("C", "other", [], False, PARAMS_HALF) == (0.5, "unlisted")


def test_conflict_switch_is_the_moe_default_and_flips_without_code():
    sw = tv.TIERS_CFG["venue_evidence"]["conflict_c_in_index"]
    assert sw["status"] == "MOE default, not author-decided" and sw["value"] == 0.5
    for value, expected in ((0.5, 0.5), (1.0, 1.0), (0.0, 0.0)):
        assert rv.mu_venue("C", "repository", ["scopus"], False, dict(PARAMS, conflict=value)) == (expected, "tier_c_in_index")
    assert rv.mu_venue("C", "repository", ["scopus"], False, dict(PARAMS, promote=["scopus"]))[0] == 1.0
    with pytest.raises(ValueError, match="conflict"):
        rv.evidence_params({"venue_evidence": dict(tv.TIERS_CFG["venue_evidence"],
                                                   conflict_c_in_index={"value": 0.75})})


# ── Red tests: the motivating defect, with a defective variant each ──


def _registries(tmp_path):
    day = tmp_path / "archive" / str(tv.REG_CFG["use"])
    tv.write_registries(str(day))
    tv.write_xlsx(str(day / "scopus_source_list.xlsx"), {
        "Scopus Sources Aug. 2026": [SCOPUS_HEAD, *SCOPUS_SOURCES],
        "Discontinued Titles Aug. 2026": [["Status"], tv.SCOPUS_HEAD, *tv.SCOPUS_ROWS]})
    with open(day / "MANIFEST.sha256", "w", encoding="utf-8") as fh:
        for n in sorted(os.listdir(day)):
            if n != "MANIFEST.sha256":
                fh.write(f"{hashlib.sha256((day / n).read_bytes()).hexdigest()}  {n}\n")
    return str(tmp_path / "archive")


def _oa(oid, sid, name, issn="", landing=""):
    return {"openalex_id": oid, "status": "found", "source_id": sid, "source_name": name,
            "source_type": "other", "issn_l": issn, "issns": issn, "landing_url": landing}


def _pool(oid, year):
    return {"work_key": f"openalex:{oid}", "openalex_id": oid, "all_openalex_ids": oid, "year": str(year),
            "sources": "catalogue", "member_record_ids": f"openalex:{oid}"}


EXTRA_OA = [
    {**_oa("W7", "S70", "Cuadernos de Economia Critica", "1234-5678"), "source_type": "journal"},  # serious, Spanish, in no index
    _oa("W12", "S90", "Boletin sin tipo", "1357-2468"),                   # type unknown: tier C by rule other
    _oa("W8", "S80", "Revista Listada", "2468-1357"),                     # in Scopus 2015-2025
    {**_oa("W11", "S40", "Academy of Management Annals", "1941-6520", "https://aomannals.com/b"),
     "source_type": "journal"},                                            # clone domain, ISSN in Scopus
]
EXTRA_POOL = [_pool("W7", 2020), _pool("W12", 2020), _pool("W8", 2020), dict(_pool("W9", 2010), work_key="k:old"),
              _pool("W11", 2020)]
EXTRA_OA.append(_oa("W9", "S80", "Revista Listada", "2468-1357"))  # the same venue, an older work


def _mu_rows(tmp_path, tiers=None):
    registries = _registries(tmp_path)
    out = tmp_path / "out"
    extra = ["--tiers", tiers] if tiers else []
    tv._run(tmp_path, registries, out, extra=extra, extra_oa=EXTRA_OA, extra_pool=EXTRA_POOL)
    works = rv.load_work_venues(str(out / "rel_work_venues.csv"))
    return {k: (r["mu_venue"], r["mu_rule"], r["index_hits"], r["tier"]) for k, r in works.items()}


def assert_serious_unindexed_journal_not_dropped(rows):
    """Red test 1: a serious non-English journal in no index must not fall below 0.5."""
    assert float(rows["openalex:W7"][0]) >= 0.5, rows["openalex:W7"]


def assert_hijacked_listed_in_an_index_stays_zero(rows):
    """Red test 2: a clone domain whose ISSN an index lists is still 0."""
    assert float(rows["openalex:W11"][0]) == 0.0, rows["openalex:W11"]


def test_serious_unindexed_journal_scores_half_not_zero(tmp_path):
    rows = _mu_rows(tmp_path)
    assert rows["openalex:W7"] == ("1", "tier_ab", "", "A")  # typed journal: tier A, no index needed
    assert_serious_unindexed_journal_not_dropped(rows)


def test_tier_c_other_is_zero_by_default_and_half_when_the_switch_is_flipped(tmp_path):
    sw = tv.TIERS_CFG["venue_evidence"]["tier_c_other_mu"]
    assert sw["value"] == 0 and sw["status"].startswith("open") and "author decision" not in sw["status"]
    base = _mu_rows(tmp_path / "a")
    assert base["openalex:W12"][:2] == ("0", "unlisted")
    path = tv._cfg_copy(tmp_path, "rel_venue_tiers.yaml",
                        lambda c: c["venue_evidence"]["tier_c_other_mu"].update(value=0.5))
    flipped = _mu_rows(tmp_path / "b", tiers=path)
    assert flipped["openalex:W12"][0] == "0.5"
    assert {k for k in base if base[k][0] != flipped[k][0]} >= {"openalex:W12", "k:old"}
    assert flipped["openalex:W7"] == base["openalex:W7"]


def test_a_withdrawn_and_relisted_journal_keeps_its_later_years(tmp_path):
    p = str(tmp_path / "d.xlsx")
    tv.write_xlsx(p, {
        "Added": [["Journal Title", "ISSN", "Date Added"], ["J", "1010-1014", "41800"], ["J", "1010-1014", "43600"]],
        "Withdrawn": [["Journal Title", "ISSN", "Date Removed (dd/mm/yyyy)", "Reason"],
                      ["J", "1010-1014", "42500", "Ceased publishing"]]})
    _, entries = rvr.parse_doaj_listed([p], 2026)
    ev = rv.IndexEvidence(entries)
    got = lambda y: bool(rv.hits_at(ev.venue_entries(["1010-1014"]), -1, y))
    assert [got(y) for y in (2014, 2016, 2017, 2019, 2021)] == [True, False, False, True, True]


def test_hijacked_domain_listed_in_an_index_stays_zero(tmp_path):
    rows = _mu_rows(tmp_path)
    assert rows["openalex:W11"][:3] == ("0", "hijacked", "scopus:2[2015-2025]")
    assert_hijacked_listed_in_an_index_stays_zero(rows)


def test_the_red_tests_fail_on_their_defective_variants(tmp_path, monkeypatch):
    real = rv.mu_venue

    def legacy_c_is_zero(tier, rule, hit, hijacked, params):  # the defect: a journal in no index is treated as C
        return real("C" if tier == "A" and not hit else tier, rule, hit, hijacked, params)

    def index_before_hijack(tier, rule, hit, hijacked, params):  # the defect: an index outranks the clone flag
        return real(tier, rule, hit, hijacked and not set(hit) & set(params["indexes"]), params)

    monkeypatch.setattr(rv, "mu_venue", legacy_c_is_zero)
    rows = _mu_rows(tmp_path / "a")
    with pytest.raises(AssertionError):
        assert_serious_unindexed_journal_not_dropped(rows)
    monkeypatch.setattr(rv, "mu_venue", index_before_hijack)
    rows = _mu_rows(tmp_path / "b")
    with pytest.raises(AssertionError):
        assert_hijacked_listed_in_an_index_stays_zero(rows)


def test_tier_c_listed_at_the_publication_year_only(tmp_path):
    rows = _mu_rows(tmp_path)
    assert rows["openalex:W8"] == ("0.5", "tier_c_in_index", "scopus:1[2015-2025]", "C")  # conflict default
    assert rows["k:old"][2] == "" and rows["k:old"][1] == "unlisted"                       # 2010: not yet covered


def test_flipping_the_conflict_switch_changes_only_the_conflict_works(tmp_path):
    base = _mu_rows(tmp_path / "a")
    path = tv._cfg_copy(tmp_path, "rel_venue_tiers.yaml",
                        lambda c: c["venue_evidence"]["conflict_c_in_index"].update(value=1.0))
    flipped = _mu_rows(tmp_path / "b", tiers=path)
    assert {k for k in base if base[k][0] != flipped[k][0]} == {"openalex:W8"}
    assert flipped["openalex:W8"][0] == "1"


# ── Counts, versions and the append-only log ─────────────


def _row(key, year, language, tier, rule, idx, hijacked=False, excluded=False):
    mu, why = rv.mu_venue(tier, rule, idx, hijacked, PARAMS_HALF)
    return {"work_key": key, "year": str(year), "language": language, "tier": tier, "tier_rule": rule,
            "_idx": idx, "_hijacked": hijacked, "excluded": "true" if excluded else "false",
            "mu_venue": f"{mu:g}", "mu_rule": why, "mu_rule_version": "v", "index_hits": "", "tier": tier}


def test_counts_report_movement_by_period_and_language_and_each_index():
    rows = [_row("a", 1995, "es", "C", "other", []), _row("b", 1995, "en", "A", "journal", []),
            _row("c", 2020, "fr", "C", "other", ["doaj"]), _row("d", 2020, "en", "C", "repository", [])]
    ev = crv.evidence_counts(rows, PARAMS_HALF, rv.tier_membership(tv.TIERS_CFG))
    assert ev["movement_vs_tier_score"]["1990-2006"]["es"]["moved"] == {"0->0.5": 1}
    assert ev["movement_vs_tier_score"]["1990-2006"]["(all)"] == {"works": 2, "moved": {"0->0.5": 1}}
    assert ev["movement_vs_tier_score"]["2015-2025"]["fr"]["moved"] == {"0->0.5": 1}
    assert ev["sensitivity"]["promote:doaj"]["mu"] == {"0": 1, "0.5": 1, "1": 2}
    assert ev["sensitivity"]["drop:doaj"]["moved_vs_decided"] == 0  # tier C other is 0.5 with or without it
    assert ev["sensitivity"]["conflict_c_in_index=0"]["moved_vs_decided"] == 1


def test_log_is_append_only_and_a_changed_row_under_one_version_is_refused(tmp_path):
    log = str(tmp_path / "log.csv")
    rows = [dict(_row("a", 2020, "en", "A", "journal", []), mu_rule_version="v1")]
    assert crv.append_mu_log(log, rows, new_table=True) == 1
    assert crv.append_mu_log(log, rows) == 0
    size = os.path.getsize(log)
    assert crv.append_mu_log(log, [dict(rows[0], mu_rule_version="v2")]) == 1  # a new version appends
    with pytest.raises(RuntimeError, match="without a new rule version"):
        crv.append_mu_log(log, [dict(rows[0], mu_venue="0")])
    assert os.path.getsize(log) > size and open(log, encoding="utf-8").read().count("v1") == 1


def test_rule_version_names_every_setting():
    a = rv.evidence_version(PARAMS, "2026-10-01")
    assert a != rv.evidence_version(dict(PARAMS, conflict=1.0), "2026-10-01")
    assert a != rv.evidence_version(dict(PARAMS, indexes=["scopus"]), "2026-10-01")
    assert a != rv.evidence_version(PARAMS, "2026-11-01")
    assert a != rv.evidence_version(dict(PARAMS, promote=["doaj"]), "2026-10-01")
    assert a != rv.evidence_version(dict(PARAMS, negative_c_rules=[]), "2026-10-01")
    assert a != rv.evidence_version(dict(PARAMS, presses=["x"]), "2026-10-01")
    assert a != rv.evidence_version(PARAMS, "2026-10-01", "3")


def test_config_lists_every_trusted_index_with_source_and_caveat():
    ti = tv.REG_CFG["trusted_indexes"]
    assert {"kanal_level1", "scopus", "doaj", "university_press", "repec_series"} <= set(ti)
    assert all(v["caveat"] and v["years"] for v in ti.values())
    assert set(PARAMS["indexes"]) <= set(rv.INDEX_IDS) and yaml  # enabled indexes are known
