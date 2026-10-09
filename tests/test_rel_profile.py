"""REL minimum metadata profile: the DataCite mandatory set (ticket 2043)."""

import _rel_profile as rp
import _rel_reasons as rr
import _rel_view as rv
import pytest
from test_corpus_rel_view import RULE, WINDOW, _lab, _work
from test_rel_reasons import MRULE, SRULE, _by, _dim, _ven

pytestmark = pytest.mark.domain_corpus

PROFILE = rp.load_profile()


def _rec(**kw):
    """A work carrying all six properties, the publisher through its DOI prefix."""
    base = {"doi": "10.1016/j.x.2020.1", "title": "Climate finance", "year": "2020",
            "first_author": "A. Author", "doc_type": "article", "member_record_ids": ""}
    return {**base, **kw}


def test_complete_record_passes():
    assert rp.missing_fields(_rec(), PROFILE) == []


@pytest.mark.parametrize("change, field", [
    ({"doi": "", "all_dois": ""}, "identifier"),
    ({"first_author": "", "all_authors": ""}, "creator"),
    ({"title": "  "}, "title"),
    ({"title": "..."}, "title"),
    ({"doi": "10.2139/ssrn.123"}, "publisher"),
    ({"year": ""}, "publicationYear"),
    ({"year": "20x0"}, "publicationYear"),
    ({"doc_type": ""}, "resourceType"),
])
def test_each_field_fails_alone(change, field):
    """Positive control: removing one property fails exactly that property."""
    rec = _rec(**change)
    if field == "identifier":
        rec["host_org_name"] = "Elsevier"  # keep the publisher so only the identifier goes
    assert rp.missing_fields(rec, PROFILE) == [field]


def test_chapter_publisher_only_from_doi_prefix():
    rec = _rec(doi="10.4324/9781003467632-8", doc_type="book-chapter")
    assert rp.publisher_of(rec, PROFILE) == ("Routledge", "doi_prefix")
    assert rp.missing_fields(rec, PROFILE) == []


def test_platform_prefix_alone_is_not_a_publisher():
    """The wrong implementation counts the SSRN registrant as a publisher."""
    for doi in ("10.2139/ssrn.5850462", "10.5281/zenodo.18012887", "10.6084/m9.figshare.30015124",
                "10.2307/jj.18377014.8", "10.48550/arxiv.2502.07541"):
        rec = _rec(doi=doi)
        assert rp.publisher_of(rec, PROFILE) == ("", "unresolved"), doi
        assert rp.missing_fields(rec, PROFILE) == ["publisher"], doi


def test_unlisted_prefix_and_journal_name_are_not_a_publisher():
    rec = _rec(doi="10.99999/abc", journal="Some Journal")
    assert rp.publisher_of(rec, PROFILE)[0] == ""


def test_host_organization_comes_first_and_rescues_a_platform_prefix():
    rec = _rec(doi="10.2139/ssrn.1", host_org_name="Elsevier BV")
    assert rp.publisher_of(rec, PROFILE) == ("Elsevier BV", "host_org")
    both = _rec(doi="10.1016/j.x", host_org_name="Some Press")
    assert rp.publisher_of(both, PROFILE) == ("Some Press", "host_org")


def test_second_doi_of_the_work_resolves_the_publisher():
    rec = _rec(doi="10.2139/ssrn.1", all_dois="10.2139/ssrn.1;10.1111/abc.12")
    assert rp.publisher_of(rec, PROFILE) == ("Wiley", "doi_prefix")


@pytest.mark.parametrize("ids, kind", [
    ("t1653-sud-hors-openalex/2026-10-01:redalyc:655868327005", "redalyc"),
    ("t1653-sud-hors-openalex/2026-10-01:garuda:366430", "garuda"),
    ("t1653-sud-hors-openalex/2026-10-01:clacso:hdl:CLACSO/180795", "clacso"),
    ("t1653-sud-hors-openalex/2026-10-01:ipea:hdl:11058/9347", "ipea"),
    ("t1790-sud-playwright/2026-09-30:ajol:oai:ajol.info:article/329316", "ajol"),
    ("t1810-repec-local/2026-10-01:RePEc:gam:jjrfmx:v:19:y:2026:i:5", "repec"),
    ("t1810-repec-local/2026-10-01:excluded:RePEc:sek:iefpro:15116716", "repec"),
    ("t1650-sommaires/2026-09-30:doi:10.1007/s10584-026-04107-6", ""),
    ("hdl:11058/9347", "hdl"),
    ("oai:hal.science:hal-01234567", "oai"),
])
def test_identifier_forms(ids, kind):
    rec = _rec(doi="", member_record_ids=ids)
    assert rp.identifier_of(rec, PROFILE) == kind


@pytest.mark.parametrize("ids", [
    "t1653-sud-hors-openalex/2026-10-01:ceew:https://www.ceew.in/publications/x",  # unregistered
    "t1653-sud-hors-openalex/2026-10-01:south_centre:https://www.southcentre.int/?p=1",
    "t1652-causal-econlit/2026-09-30b:1652:ty:some title|2020",  # a title key
    "t1653-sud-hors-openalex/2026-10-01:redalyc:not-a-number",  # registered, malformed
    "bibcnrs:1A0C5D0DEE45BFB8",
    "",
])
def test_not_an_identifier(ids):
    assert rp.identifier_of(_rec(doi="", member_record_ids=ids), PROFILE) == ""


def test_repec_handle_column_counts_and_a_bare_openalex_id_too():
    assert rp.identifier_of(_rec(doi="", repec_handle="RePEc:bap:jou:1"), PROFILE) == "repec"
    assert rp.identifier_of(_rec(doi="", openalex_id="W123"), PROFILE) == "openalex"
    assert rp.identifier_of(_rec(doi="not a doi"), PROFILE) == ""


def test_config_is_versioned_and_shipped_off():
    assert PROFILE["version"] == 1
    assert PROFILE["required"] == rp.FIELDS
    assert PROFILE["enabled"] is False  # on only after the pool carries authors
    assert PROFILE["prefixes"]["10.2139"][1] == "platform"


def test_bad_config_is_refused(tmp_path):
    bad = tmp_path / "p.yaml"
    bad.write_text("version: 1\nenabled: true\nrequired: [identifer]\n"
                   "identifier: {generic: [], platforms: {}}\n"
                   "publisher: {order: [host_org], prefix_table: config/rel_doi_prefixes.csv}\n")
    with pytest.raises(ValueError, match="unknown fields"):
        rp.load_profile(str(bad))


# ── in the view ──────────────────────────────────────────

def _view(prof_enabled, required=None):
    good = _work("openalex:W1", oas="W1")
    good.update(first_author="A", doc_type="article", host_org_name="Elsevier")
    no_author = _work("openalex:W2", oas="W2")
    no_author.update(doc_type="article", host_org_name="Elsevier")
    no_pub = _work("openalex:W3", oas="W3")
    no_pub.update(first_author="A", doc_type="article")
    pool = [good, no_author, no_pub]
    labels = [_lab(f"openalex:W{i}", "2", "icf") for i in (1, 2, 3)]
    dims = [_dim(f"openalex:W{i}", "yes") for i in (1, 2, 3)]
    venues = {f"openalex:W{i}": _ven(f"openalex:W{i}") for i in (1, 2, 3)}
    rows, _ = rv.build_view(pool, labels, WINDOW, RULE)
    prof = rp.rule(PROFILE, enabled=prof_enabled, required=required)
    rr.assign(rows, pool, dims, venues, dict(SRULE, profile=prof), MRULE, profile=PROFILE)
    return rows, venues, prof


def test_filter_off_records_the_gap_but_excludes_nothing():
    rows, _, _ = _view(False)
    by = _by(rows)
    assert {k: r["rel_reason"] for k, r in by.items()} == dict.fromkeys(by, "included")
    assert by["openalex:W2"]["profile_missing"] == "profile_missing_creator"
    assert by["openalex:W3"]["profile_missing"] == "profile_missing_publisher"
    assert by["openalex:W1"]["profile_missing"] == "" and by["openalex:W1"]["mu_profile"] == ""


def test_filter_on_excludes_at_the_first_facet_with_a_reason_code():
    rows, _, _ = _view(True)
    by = _by(rows)
    assert by["openalex:W1"]["rel_reason"] == "included"
    assert (by["openalex:W2"]["rel_reason"], by["openalex:W2"]["rel_reason_detail"]) == (
        "profile_excluded", "profile_missing_creator")
    assert by["openalex:W3"]["rel_reason_detail"] == "profile_missing_publisher"
    assert (by["openalex:W2"]["mu_facet"], by["openalex:W2"]["mu_profile"]) == ("profile", "0")
    # the excluded work stays a row, with later facets ungraded (no model call needed)
    assert by["openalex:W2"]["mu_icf"] == "" and len(rows) == 3
    assert rr.reason_counts(rows)["works"]["profile_excluded"] == 2


def test_publisher_requirement_is_a_switch():
    rows, _, _ = _view(True, required=[f for f in rp.FIELDS if f != "publisher"])
    assert _by(rows)["openalex:W3"]["rel_reason"] == "included"
    assert _by(rows)["openalex:W2"]["rel_reason"] == "profile_excluded"


def test_sensitivity_reports_the_filter_on_and_off():
    rows, venues, prof = _view(False)
    table = {r["scenario"]: r for r in rr.sensitivity(rows, venues, dict(SRULE, profile=prof), MRULE)}
    assert table["profile_off"]["included_works"] == 3 and table["profile_off"]["profile"] == "off"
    assert table["profile_on"]["included_works"] == 1
    assert table["profile_on_publisher_optional"]["included_works"] == 2
    assert "publisher" not in table["profile_on_publisher_optional"]["profile"]
    assert table["default"]["included_works"] == 3  # configured off: counts unchanged


def test_counts_block_tallies_gaps_whatever_the_switch():
    rows, _, prof = _view(False)
    c = rp.counts(rows, prof)
    assert c["missing_by_field_works"]["creator"] == 1 and c["missing_by_field_works"]["publisher"] == 1
    assert c["excluded_works"] == 0 and c["missing_any_works"] == 2


# ── review fixes ─────────────────────────────────────────

@pytest.mark.parametrize("org", ["Zenodo", "figshare", "SSRN Electronic Journal", "SSRN",
                                 "arXiv", " JSTOR "])
def test_platform_host_organization_is_not_a_publisher(org):
    rec = _rec(doi="10.99999/x", host_org_name=org)
    assert rp.publisher_of(rec, PROFILE) == ("", "unresolved")
    assert rp.missing_fields(rec, PROFILE) == ["publisher"]


def test_real_host_organization_still_resolves():
    assert rp.publisher_of(_rec(doi="", host_org_name="Wiley"), PROFILE)[1] == "host_org"


def test_osti_is_a_platform_not_a_publisher():
    assert PROFILE["prefixes"]["10.2172"][1] == "platform"
    assert rp.publisher_of(_rec(doi="10.2172/3018336"), PROFILE) == ("", "unresolved")


def test_reason_code_follows_fixed_field_order_not_config_order():
    cell = rp.codes(["creator", "publisher"])
    shuffled = ["resourceType", "publisher", "creator"]
    assert rp.first_required_code(cell, shuffled) == "profile_missing_creator"


def test_platform_entries_are_not_covered_by_generic_forms():
    """scielo, ajol, adb_ewp stay: without them their record ids are not identifiers."""
    generic_only = dict(PROFILE, platforms={})
    for ids in ("l/d:scielo:oai:scielo:S0185-013X2024000300573",
                "l/d:ajol:oai:ajol.info:article/329316", "l/d:adb_ewp:RePEc:ris:adbewp:021837"):
        rec = _rec(doi="", member_record_ids=ids)
        assert rp.identifier_of(rec, generic_only) == ""
        assert rp.identifier_of(rec, PROFILE) != ""
