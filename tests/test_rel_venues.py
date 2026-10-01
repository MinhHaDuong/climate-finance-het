"""REL venue tiers and registry flags (ticket 1841): parsers, rules, determinism."""

import csv
import hashlib
import json
import os
import re
import zipfile
from xml.sax.saxutils import escape

import _rel_venue_registries as rvr
import _rel_venues as rv
import corpus_rel_venues as crv
import pytest
import yaml
from _xlsx_rows import read_sheet, sheet_names

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIERS_CFG = yaml.safe_load(open(os.path.join(ROOT, "config", "rel_venue_tiers.yaml"), encoding="utf-8"))
REG_CFG = yaml.safe_load(open(os.path.join(ROOT, "config", "rel_venue_registries.yaml"), encoding="utf-8"))
TIERS = rv.compile_tiers(TIERS_CFG)


# ── Fixtures: registry files in their real formats ───────


def _col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def write_xlsx(path, sheets):
    """A minimal .xlsx (inline strings) with ``{sheet name: rows}``."""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        wb = ['<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
        rels = ['<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for n, (name, rows) in enumerate(sheets.items(), 1):
            wb.append(f'<sheet name="{escape(name)}" sheetId="{n}" r:id="rId{n}"/>')
            rels.append(f'<Relationship Id="rId{n}" Target="worksheets/sheet{n}.xml"/>')
            xml = ['<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
            for i, row in enumerate(rows, 1):
                cells = "".join(f'<c r="{_col(j)}{i}" t="inlineStr"><is><t>{escape(str(v))}</t></is></c>'
                                for j, v in enumerate(row) if v != "")
                xml.append(f'<row r="{i}">{cells}</row>')
            xml.append("</sheetData></worksheet>")
            z.writestr(f"xl/worksheets/sheet{n}.xml", "".join(xml))
        z.writestr("xl/workbook.xml", "".join(wb) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels) + "</Relationships>")


SCOPUS_HEAD = ["Sourcerecord ID", "Source Title", "ISSN", "EISSN", "Publisher", "Indexation Change", "Year"]
# Real rows of the August 2026 list (pull 2026-10-01).
SCOPUS_ROWS = [
    ["21100897507", "Academic Journal of Interdisciplinary Studies", "22813993", "22814612",
     "Richtmann Publishing Ltd", "Discontinuation", "2024"],
    ["18665", "ABB Review", "10133119", "", "A B B Corporate Management Services AG",
     "Journal change policy", "2018"],
]


def write_registries(day):
    os.makedirs(day, exist_ok=True)
    head = ["Tidsskrift id", "Original tittel", "Print ISSN", "Online ISSN", "Nivå 2027", "Nivå 2026", "Nivå 2025"]
    with open(os.path.join(day, "kanalregisteret_851.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(head)
        w.writerow(["1", "Doubtful Journal of Economics", "1111-1119", "", "", "X", "1"])
        w.writerow(["2", "Cleared Journal of Finance", "2222-2228", "", "1", "X", "1"])
        w.writerow(["3", "Plain Journal", "3333-3337", "", "", "1", "1"])
    write_xlsx(os.path.join(day, "scopus_source_list.xlsx"), {
        "Scopus Sources Aug. 2026": [["Sourcerecord ID"]],
        "Discontinued Titles Aug. 2026": [["Status"], SCOPUS_HEAD] + SCOPUS_ROWS})
    write_xlsx(os.path.join(day, "doaj_changelog_2014_2024.xlsx"), {
        "Added": [["Journal Title", "ISSN", "Date Added"], ["Readmitted Review", "4444-4446", "45500"]],
        "Withdrawn": [["note"], ["Journal Title", "ISSN", "Date Removed (dd/mm/yyyy)", "Reason"],
                      ["Bad Practice Letters", "5555-5552", "45321", "Journal not adhering to Best practice"],
                      ["Readmitted Review", "4444-4446", "45000", "Journal not adhering to best practice"],
                      ["Gone Quarterly", "6666-6664", "45000", "Ceased publishing"]]})
    write_xlsx(os.path.join(day, "doaj_changelog_current.xlsx"), {
        "Added": [["Journal Title", "ISSN", "Date Added"]],
        "Withdrawn": [["Journal Title", "ISSN", "Date Removed (dd/mm/yyyy)", "Reason"],
                      ["Tecnura", "2248-7638", "25-September-2026", "Journal not adhering to Best practice"]]})
    with open(os.path.join(day, "hijacked_journal_checker.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["First created", "", "", "", "", "", ""])
        w.writerow(["", "Hijacked Journal Title", "URL (Hijacked)", "ISSN (Hijacked)", "Original journal",
                    "ISSN (Original)", " URL (Original Journal)"])
        w.writerow(["1", "Academy of Management Annals", "https://aomannals.com/", "1941-6520, 1941-6067",
                    "Academy of Management Annals", "1941-6520,  1941-6067", "https://journals.aom.org"])
    with open(os.path.join(day, "MANIFEST.sha256"), "w", encoding="utf-8") as fh:
        for n in sorted(os.listdir(day)):
            if n != "MANIFEST.sha256":
                fh.write(f"{hashlib.sha256(open(os.path.join(day, n), 'rb').read()).hexdigest()}  {n}\n")


@pytest.fixture
def registries(tmp_path):
    day = tmp_path / "archive" / str(REG_CFG["use"])
    write_registries(str(day))
    return str(tmp_path / "archive")


# ── Parsers ──────────────────────────────────────────────


def test_xlsx_reader_reads_inline_and_ragged_rows(tmp_path):
    p = tmp_path / "x.xlsx"
    write_xlsx(p, {"S1": [["a", "", "c"], ["d"]], "S2": [["z"]]})
    assert sheet_names(p) == ["S1", "S2"]
    assert read_sheet(p, "S1") == [["a", "", "c"], ["d"]]


def test_issn_normalisation():
    assert rvr.norm_issn("22813993") == "2281-3993"
    assert rvr.norm_issn("1941-606x") == "1941-606X"
    assert rvr.issns_in("1941-6520,  1941-6067") == ("1941-6067", "1941-6520")
    assert rvr.issns_in("0002-8282; 1944-7981") == ("0002-8282", "1944-7981")
    assert rvr.norm_issn("2026") == ""


def test_kanalregisteret_lists_every_journal_with_an_x_year_and_its_levels(registries):
    day = os.path.join(registries, str(REG_CFG["use"]))
    rows, entries = rvr.parse_kanalregisteret(os.path.join(day, "kanalregisteret_851.csv"), "u{id}")
    assert rows == 3
    assert [(e["entry_id"], e["issns"], e["entry_url"]) for e in entries] == [
        ("1", ("1111-1119",), "u1"), ("2", ("2222-2228",), "u2")]
    assert entries[1]["levels"] == {2025: "1", 2026: "X", 2027: "1"}
    assert entries[1]["reason"] == "Nivå 2025 1, 2026 X, 2027 1"


def test_kanal_level_is_the_level_of_the_work_year():
    levels = {2018: "1", 2019: "1", 2026: "X", 2027: "1"}
    assert rvr.level_at(levels, 2026) == "X"
    assert rvr.level_at(levels, 2019) == "1"
    assert rvr.level_at(levels, 2027) == "1"
    assert rvr.level_at(levels, 2010) == "1"   # before the register: nearest year, 2018
    assert rvr.level_at(levels, 2030) == "1"   # after: nearest year, 2027
    assert rvr.level_at({2025: "1", 2027: "X"}, 2026) == "1"  # blank year, tie: the earlier
    assert rvr.level_at(levels, None) is None


def test_scopus_keeps_discontinuations_not_policy_changes(registries):
    day = os.path.join(registries, str(REG_CFG["use"]))
    rows, entries = rvr.parse_scopus_discontinued(os.path.join(day, "scopus_source_list.xlsx"))
    assert rows == 2
    assert [(e["entry_id"], e["issns"]) for e in entries] == [("21100897507", ("2281-3993", "2281-4612"))]


def test_doaj_practice_reasons_minus_readmissions(registries):
    day = os.path.join(registries, str(REG_CFG["use"]))
    files = [os.path.join(day, f) for f in REG_CFG["registries"]["doaj_withdrawn"]["files"]]
    rows, entries = rvr.parse_doaj_withdrawn(files, REG_CFG["registries"]["doaj_withdrawn"]["reason_pattern"])
    assert rows == 4
    assert sorted(e["entry_id"] for e in entries) == ["2248-7638", "5555-5552"]


def test_doaj_dates_both_logs():
    assert rvr.parse_doaj_date("45321.0").isoformat() == "2024-01-30"
    assert rvr.parse_doaj_date("28-September-2026").isoformat() == "2026-09-28"


def test_hijacked_entries_are_domains(registries):
    day = os.path.join(registries, str(REG_CFG["use"]))
    rows, entries = rvr.parse_hijacked(os.path.join(day, "hijacked_journal_checker.csv"))
    assert rows == 1 and entries[0]["domain"] == "aomannals.com"


# ── Flags: the red test replays a known flagged ISSN ─────


def _index(registries):
    return crv.load_registries(registries, REG_CFG)


def test_known_scopus_discontinued_issn_is_flagged(registries):
    idx = _index(registries)
    flags = idx.venue_flags(["2281-3993"], "Academic Journal of Interdisciplinary Studies")
    assert [(f["registry"], f["entry_id"], f["match"]) for f in flags] == [
        ("scopus_discontinued", "21100897507", "issn")]
    assert flags[0]["pull_date"] == str(REG_CFG["use"])
    assert idx.venue_flags(["0002-8282"], "American Economic Review") == []


def test_title_match_only_without_issn(registries):
    idx = _index(registries)
    assert [f["match"] for f in idx.venue_flags([], "Bad Practice Letters")] == ["title"]
    assert idx.venue_flags(["9999-9993"], "Bad Practice Letters") == []


def test_hijacked_flags_the_clone_not_the_victim(registries):
    idx = _index(registries)
    assert idx.venue_flags(["1941-6520"], "Academy of Management Annals") == []
    assert [f["registry"] for f in idx.work_flags("https://www.aomannals.com/article/1")] == ["hijacked"]
    assert idx.work_flags("https://journals.aom.org/doi/10.5465/x") == []


def test_tampered_registry_file_is_refused(registries):
    day = os.path.join(registries, str(REG_CFG["use"]))
    with open(os.path.join(day, "kanalregisteret_851.csv"), "a", encoding="utf-8") as fh:
        fh.write('"4","Extra","","","","X",""\n')
    with pytest.raises(RuntimeError, match="sha256"):
        _index(registries)


# ── Tier rules ───────────────────────────────────────────


def _v(**kw):
    base = {"key": "k", "name": "", "hosts": [], "source_id": "", "source_type": "", "issns": [],
            "repec": "", "repec_template": "", "record_prefixes": [], "toc_journal": False,
            "declared_journal": False}
    base.update(kw)
    return base


@pytest.mark.parametrize("venue, expected", [
    (_v(repec="repec:nbr:nberwo", name="NBER Working Papers"), ("B", "b_series", "nber")),
    (_v(name="World Bank Economic Review", source_type="journal", hosts=["Oxford University Press"]),
     ("A", "journal", "")),
    (_v(name="Policy Research Working Paper", source_type="journal", hosts=["World Bank"]),
     ("B", "b_series", "world_bank")),
    (_v(name="SSRN Electronic Journal", source_type="repository", hosts=["RELX Group (Netherlands)"]),
     ("C", "repository", "")),
    (_v(name="RePEc: Research Papers in Economics", source_type="repository",
        hosts=["Federal Reserve Bank of St. Louis"]), ("C", "repository", "")),
    (_v(name="The World Bank Open Knowledge Repository (World Bank)", source_type="repository"),
     ("B", "b_institution", "world_bank")),
    (_v(name="World Bank, Washington, DC eBooks", source_type="ebook platform"),
     ("B", "b_institution", "world_bank")),
    (_v(name="Cambridge University Press eBooks", source_type="ebook platform"), ("C", "other", "")),
    (_v(repec="repec:gam:jeners", repec_template="redif-article", name="Energies"), ("A", "journal", "")),
    (_v(repec="repec:pra:mprapa", name="MPRA Paper"), ("C", "repository", "")),
    (_v(name="Revista de Economia", declared_journal=True), ("A", "journal", "")),
    (_v(name="Some Department Working Papers", repec="repec:xyz:wpaper"), ("C", "other", "")),
    (_v(name="Relatório", record_prefixes=["ipea"]), ("B", "b_institution", "ipea")),
    (_v(name="TERI Policy Brief", source_type="other"), ("B", "b_institution", "teri")),
])
def test_tier_rule_order(venue, expected):
    assert rv.assign_tier(venue, TIERS) == expected


def test_publisher_flag_by_host_and_repec():
    assert rv.publisher_flag(_v(hosts=["Multidisciplinary Digital Publishing Institute"]), TIERS) == "mdpi"
    assert rv.publisher_flag(_v(repec="repec:gam:jeners"), TIERS) == "mdpi"
    assert rv.publisher_flag(_v(hosts=["Frontiers Media"]), TIERS) == "frontiers"
    assert rv.publisher_flag(_v(hosts=["Hindawi Publishing Corporation"]), TIERS) == "hindawi"
    assert rv.publisher_flag(_v(hosts=["Elsevier BV"]), TIERS) == ""


def test_b_list_is_well_formed():
    ids = [e["id"] for e in TIERS_CFG["b_list"]]
    assert len(ids) == len(set(ids))
    cats = {"igo", "central_bank", "public", "network", "think_tank", "university_centre", "ngo_research"}
    assert {e["category"] for e in TIERS_CFG["b_list"]} <= cats
    assert {e["region"] for e in TIERS_CFG["b_list"]} <= {"north", "south", "global"}
    assert sum(e["region"] == "south" for e in TIERS_CFG["b_list"]) >= 15
    for e in TIERS_CFG["b_list"]:
        assert any(e.get(k) for k in ("repec", "series", "names", "record_prefix", "openalex", "issn")), e["id"]


def test_repec_from_landing_urls():
    assert rv.repec_from_url("https://ideas.repec.org/p/nbr/nberwo/12345.html") == "repec:nbr:nberwo"
    assert rv.repec_from_url("https://econpapers.repec.org/RePEc:cpr:ceprdp:999") == "repec:cpr:ceprdp"
    assert rv.repec_handle("RePEc:wbk:wbrwps") == "repec:wbk:wbrwps"


# ── End to end: resolution and determinism ──────────────


OA_COLS = ["openalex_id", "status", "work_type", "location", "source_id", "source_name", "source_type",
           "issn_l", "issns", "host_org_id", "host_org_name", "host_lineage_names", "is_in_doaj", "landing_url"]


def _write(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def _inputs(tmp_path, extra_oa=(), extra_pool=(), extra_recs=None):
    oa = [
        {"openalex_id": "W1", "status": "found", "source_id": "S10", "source_name": "Energies",
         "source_type": "journal", "issn_l": "1996-1073", "issns": "1996-1073",
         "host_org_name": "Multidisciplinary Digital Publishing Institute", "landing_url": "https://www.mdpi.com/x"},
        {"openalex_id": "W2", "status": "found", "source_id": "S20", "source_name": "Academic Journal of Interdisciplinary Studies",
         "source_type": "journal", "issn_l": "2281-3993", "issns": "2281-3993;2281-4612", "host_org_name": "Richtmann"},
        {"openalex_id": "W3", "status": "found", "source_id": "S30", "source_name": "RePEc: Research Papers in Economics",
         "source_type": "repository", "host_org_name": "Federal Reserve Bank of St. Louis",
         "landing_url": "https://ideas.repec.org/p/nbr/nberwo/1.html"},
        {"openalex_id": "W4", "status": "found", "source_id": "S40", "source_name": "Academy of Management Annals",
         "source_type": "journal", "issn_l": "1941-6520", "issns": "1941-6520", "landing_url": "https://aomannals.com/a"},
        {"openalex_id": "W5", "status": "not_found"},
        {"openalex_id": "W6", "status": "found", "source_id": "S60", "source_name": "Oxfam Policy & Practice",
         "source_type": "other", "host_org_name": "Oxfam GB"},
    ]
    oa = oa + list(extra_oa)
    pool_cols = ["work_key", "openalex_id", "all_openalex_ids", "year", "journal", "doc_type", "sources",
                 "member_record_ids"]
    pool = [
        {"work_key": "openalex:W1", "openalex_id": "W1", "all_openalex_ids": "W1", "journal": "Energies",
         "sources": "catalogue", "member_record_ids": "openalex:W1"},
        {"work_key": "openalex:W2", "openalex_id": "W2", "all_openalex_ids": "W2", "sources": "t1530-sud-openalex",
         "member_record_ids": "t1530-sud-openalex/d:W2"},
        {"work_key": "openalex:W3", "openalex_id": "W3", "all_openalex_ids": "W3", "sources": "catalogue",
         "member_record_ids": "openalex:W3"},
        {"work_key": "openalex:W4", "openalex_id": "W4", "all_openalex_ids": "W4", "sources": "catalogue",
         "member_record_ids": "openalex:W4"},
        {"work_key": "openalex:W6", "openalex_id": "W6", "all_openalex_ids": "W6", "sources": "catalogue",
         "member_record_ids": "openalex:W6"},
        {"work_key": "url:repec1", "journal": "Energies", "doc_type": "article", "sources": "t1810-repec-local",
         "member_record_ids": "t1810-repec-local/d:oai:1"},
        {"work_key": "url:ipea1", "journal": "Texto para Discussão", "sources": "t1653-sud-hors-openalex",
         "member_record_ids": "t1653-sud-hors-openalex/d:ipea:hdl:1"},
        {"work_key": "doi:10.1/toc", "journal": "Some Journal", "sources": "t1650-sommaires",
         "member_record_ids": "t1650-sommaires/d:doi:10.1/toc"},
        {"work_key": "title:x|2020", "sources": "t1652-causal-econlit", "member_record_ids": "t1652-causal-econlit/d:z"},
        {"work_key": "title:y|2020", "journal": "Revista Andina de Economia", "doc_type": "Academic Journal",
         "sources": "t1652-causal-econlit", "member_record_ids": ""},
    ]
    pool = pool + list(extra_pool)
    rec_cols = ["record_id", "issn", "journal_key", "series_handle", "template_type", "url"]
    intake = tmp_path / "intake"
    for lane, recs in {
        "t1530-sud-openalex": [{"record_id": "W2"}],
        "t1810-repec-local": [{"record_id": "oai:1", "series_handle": "RePEc:gam:jeners",
                               "template_type": "redif-article"}],
        "t1653-sud-hors-openalex": [{"record_id": "ipea:hdl:1"}],
        "t1650-sommaires": [{"record_id": "doi:10.1/toc", "issn": "5555-5552", "journal_key": "sj"}],
        "t1652-causal-econlit": [{"record_id": "z"}],
        **(extra_recs or {}),
    }.items():
        _write(str(intake / lane / "d" / "records.csv"), rec_cols, recs)
    _write(str(tmp_path / "oa.csv"), OA_COLS, oa)
    _write(str(tmp_path / "pool.csv"), pool_cols, pool)
    _write(str(tmp_path / "toc.csv"), ["journal_key", "publisher"], [{"journal_key": "sj", "publisher": "P"}])
    return str(intake)


def _run(tmp_path, registries, out, extra=(), **inputs):
    intake = _inputs(tmp_path, **inputs)
    return crv.main(["--pool", str(tmp_path / "pool.csv"), "--intake-dir", intake,
                     "--oa-cache", str(tmp_path / "oa.csv"), "--toc-manifest", str(tmp_path / "toc.csv"),
                     "--archive-root", registries, "--output-dir", str(out), *extra])


def test_end_to_end_resolution_tiers_flags(tmp_path, registries):
    assert _run(tmp_path, registries, tmp_path / "out") == 0
    works = rv.load_work_venues(str(tmp_path / "out" / "rel_work_venues.csv"))
    got = {k: (r["venue_key"], r["venue_resolution"], r["tier"], r["flags"], r["publisher_flag"])
           for k, r in works.items()}
    assert got == {
        "openalex:W1": ("openalex:S10", "openalex", "A", "", "mdpi"),
        "openalex:W2": ("openalex:S20", "openalex", "A", "scopus_discontinued:21100897507[issn]", ""),
        "openalex:W3": ("repec:nbr:nberwo", "repec", "B", "", ""),
        "openalex:W4": ("openalex:S40", "openalex", "A", "hijacked:1[domain]", ""),
        "openalex:W6": ("openalex:S60", "openalex", "B", "", ""),
        "url:repec1": ("openalex:S10", "repec_journal_name_to_openalex", "A", "", "mdpi"),
        "url:ipea1": ("prefix:ipea", "record_prefix", "B", "", ""),
        "doi:10.1/toc": ("issn:5555-5552", "toc_issn", "A", "doaj_withdrawn:5555-5552[issn]", ""),
        "title:x|2020": ("none", "none", "unknown", "", ""),
        "title:y|2020": ("name:revista andina de economia", "name", "A", "", ""),
    }
    assert works["openalex:W2"]["flagged"] is True and works["openalex:W2"]["tier_included"] is True
    counts = json.load(open(tmp_path / "out" / "rel_venue_counts.json", encoding="utf-8"))
    assert counts["works_by_lane"]["(all)"]["tier"] == {"A": 6, "B": 3, "unknown": 1}
    assert counts["works_by_lane"]["(all)"]["no_venue"] == 1
    assert counts["works_by_lane"]["t1810-repec-local"]["publisher_flag"] == {"mdpi": 1}


def test_outputs_are_byte_identical_on_rerun(tmp_path, registries):
    names = ["rel_venues.csv", "rel_work_venues.csv", "rel_venue_counts.json", "rel_venue_counts.md"]
    _run(tmp_path, registries, tmp_path / "a")
    _run(tmp_path, registries, tmp_path / "b")
    for n in names:
        assert (tmp_path / "a" / n).read_bytes() == (tmp_path / "b" / n).read_bytes(), n


# ── Switches (pending author decisions) ──────────────────


def _cfg_copy(tmp_path, name, change):
    """A copy of ``config/<name>`` with ``change(cfg)`` applied; its path."""
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config", name), encoding="utf-8"))
    change(cfg)
    path = tmp_path / name
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return str(path)


def test_switches_are_pending_with_the_recommended_defaults():
    assert REG_CFG["exclusion"]["status"] == "pending"
    assert sorted(REG_CFG["exclusion"]["exclude"]) == ["hijacked", "kanalregisteret"]
    assert set(REG_CFG["exclusion"]["exclude"]) <= set(REG_CFG["registries"])
    assert TIERS_CFG["ngo_research_in_b"] == {"status": "pending", "value": True}
    assert {e["id"] for e in TIERS_CFG["b_list"] if e["category"] == "ngo_research"} == {"oxfam", "germanwatch"}


def test_default_exclusion_keeps_every_flag_and_excludes_only_hard_hits(tmp_path, registries):
    _run(tmp_path, registries, tmp_path / "out")
    works = rv.load_work_venues(str(tmp_path / "out" / "rel_work_venues.csv"))
    got = {k: (r["flagged"], r["excluded"], r["excluded_by"], r["included"]) for k, r in works.items()
           if r["flagged"]}
    assert got == {
        "openalex:W2": (True, False, "", True),            # Scopus discontinued: flag only
        "openalex:W4": (True, True, "hijacked", False),    # hijacked clone: excluded
        "doi:10.1/toc": (True, False, "", True),           # DOAJ withdrawal: flag only
    }
    counts = json.load(open(tmp_path / "out" / "rel_venue_counts.json", encoding="utf-8"))
    assert counts["works_by_lane"]["(all)"]["excluded"] == 1
    assert counts["switches"]["exclude"] == ["hijacked", "kanalregisteret"]


def test_exclusion_follows_the_switch_not_a_fixed_list(tmp_path, registries):
    """Red test: a build that hard-coded the default would keep W4 excluded."""
    reg = _cfg_copy(tmp_path, "rel_venue_registries.yaml",
                    lambda c: c["exclusion"].update(exclude=["scopus_discontinued", "doaj_withdrawn"]))
    _run(tmp_path, registries, tmp_path / "out", ["--registries", reg])
    works = rv.load_work_venues(str(tmp_path / "out" / "rel_work_venues.csv"))
    assert {k for k, r in works.items() if r["excluded"]} == {"openalex:W2", "doi:10.1/toc"}
    assert works["openalex:W4"]["flags"] == "hijacked:1[domain]" and not works["openalex:W4"]["excluded"]
    venues = {r["venue_key"]: r for r in csv.DictReader(open(tmp_path / "out" / "rel_venues.csv", encoding="utf-8"))}
    assert venues["openalex:S20"]["excluded_by"] == "scopus_discontinued"


def test_ngo_switch_selects_the_tier_and_both_tiers_are_written(tmp_path, registries):
    _run(tmp_path, registries, tmp_path / "on")
    on = rv.load_work_venues(str(tmp_path / "on" / "rel_work_venues.csv"))
    assert (on["openalex:W6"]["tier"], on["openalex:W6"]["b_id"]) == ("B", "oxfam")
    assert (on["openalex:W6"]["tier_ngo_in_b"], on["openalex:W6"]["tier_ngo_not_b"]) == ("B", "C")
    # Red test: switching off must move the Oxfam work to C and nothing else.
    tiers = _cfg_copy(tmp_path, "rel_venue_tiers.yaml", lambda c: c["ngo_research_in_b"].update(value=False))
    _run(tmp_path, registries, tmp_path / "off", ["--tiers", tiers])
    off = rv.load_work_venues(str(tmp_path / "off" / "rel_work_venues.csv"))
    assert (off["openalex:W6"]["tier"], off["openalex:W6"]["b_id"]) == ("C", "")
    assert not off["openalex:W6"]["included"]
    assert {k for k in on if on[k]["tier"] != off[k]["tier"]} == {"openalex:W6"}
    counts = json.load(open(tmp_path / "off" / "rel_venue_counts.json", encoding="utf-8"))
    assert counts["works_by_lane"]["(all)"]["ngo_switch_moves"] == 1


def test_enrich_stops_before_the_budget_floor():
    import enrich_rel_venues_openalex as enr
    assert not enr._below_floor("0.8482", 0.005, 0.2)
    assert enr._below_floor("0.2040", 0.005, 0.2)
    assert enr._below_floor("?", 0.005, 0.2)  # unreadable header: never spend blind


# ── Review fixes (PR 1657) ───────────────────────────────


def test_manifest_must_cover_every_configured_registry_file(registries):
    day = os.path.join(registries, str(REG_CFG["use"]))
    path = os.path.join(day, "MANIFEST.sha256")
    lines = open(path, encoding="utf-8").read().splitlines()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(x for x in lines if "kanalregisteret" not in x) + "\n")
    with pytest.raises(RuntimeError, match="does not cover"):
        _index(registries)


def test_a_title_match_never_excludes():
    title = {"registry": "doaj_withdrawn", "entry_id": "x", "match": "title"}
    issn = {"registry": "doaj_withdrawn", "entry_id": "y", "match": "issn"}
    assert rv.exclusion_of([title], ["doaj_withdrawn"]) == ""
    assert rv.exclusion_of([title, issn], ["doaj_withdrawn"]) == "doaj_withdrawn"


def test_a_hijacked_hit_stays_on_the_work_not_the_venue(tmp_path, registries):
    _run(tmp_path, registries, tmp_path / "out")
    venues = {r["venue_key"]: r for r in csv.DictReader(open(tmp_path / "out" / "rel_venues.csv", encoding="utf-8"))}
    # The venue carries no flag; it only counts its one excluded work.
    assert (venues["openalex:S40"]["flags"], venues["openalex:S40"]["n_works_excluded"]) == ("", "1")
    works = rv.load_work_venues(str(tmp_path / "out" / "rel_work_venues.csv"))
    assert works["openalex:W4"]["excluded"]


@pytest.mark.parametrize("venue, expected", [
    (_v(name="Diwan: Jurnal Bahasa dan Sastra Arab", source_type="other"), ("C", "other", "")),
    (_v(name="DIW Discussion Papers", source_type="other"), ("B", "b_series", "diw")),
    (_v(name="Academe", source_type="other"), ("C", "other", "")),
    (_v(name="Infectious Diseases Reports", source_type="other"), ("C", "other", "")),
    (_v(name="Banca d'Italia Occasional Papers", source_type="other"), ("B", "b_institution", "banca_italia")),
    # French elision: fold() strips the apostrophe, so "l'OFCE" folds to "lofce".
    (_v(name="Revue de l'OFCE", source_type="journal"), ("B", "b_series", "pse_ofce")),
    (_v(name="Les rapports de l'ADEME", source_type="other"), ("B", "b_institution", "public_agencies")),
    (_v(name="Études de l'IDDRI", source_type="other"), ("B", "b_institution", "iddri")),
])
def test_b_patterns_match_whole_words_of_the_folded_name(venue, expected):
    """Red test: bare 'diw', 'ademe', 'iseas' matched inside Diwan, Academe, Diseases;
    word-bounded 'ofce' then missed "l'OFCE" (round 3)."""
    assert rv.assign_tier(venue, TIERS) == expected


def test_b_patterns_are_word_bounded_and_survive_folding():
    for e in TIERS_CFG["b_list"]:
        for p in (e.get("names") or []) + (e.get("series") or []):
            assert not re.fullmatch(r"[a-z0-9-]+", p), (e["id"], p)  # bare token: substring hits
            assert not re.search(r"[,'’]", p), (e["id"], p)  # fold() strips these: never matches


def test_enrich_loop_stops_at_the_floor(tmp_path, monkeypatch):
    import enrich_rel_venues_openalex as enr
    pool = tmp_path / "pool.csv"
    pool.write_text("work_key,all_openalex_ids\n" + "".join(f"w{i},W{i}\n" for i in range(1, 251)), encoding="utf-8")
    budgets = iter(["0.2003", "0.2000", "0.1999", "0.1998"])

    def fake_fetch(ids, api_key):
        return {i: {"openalex_id": i, "status": "found"} for i in ids}, next(budgets)

    monkeypatch.setattr(enr, "fetch_batch", fake_fetch)
    monkeypatch.setattr(enr, "read_credential", lambda *a: "")
    out = tmp_path / "cache.csv"
    assert enr.main(["--pool", str(pool), "--output", str(out), "--checkpoint-every", "1", "--workers", "1"]) == 0
    # probe 0.2003, wave 1 leaves 0.2000, wave 2 would go below 0.2: one wave of 100 ids.
    assert len(enr.load_cache(str(out))) == 100


@pytest.mark.integration
def test_outputs_do_not_depend_on_the_hash_seed(tmp_path, registries):
    import subprocess
    import sys
    intake = _inputs(tmp_path)
    # Positive control: the two seeds do reorder a set of strings.
    probe = "print(list({'alpha', 'beta', 'gamma', 'delta', 'epsilon'}))"
    orders = {seed: subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=True,
                                   env=dict(os.environ, PYTHONHASHSEED=seed)).stdout for seed in ("0", "1")}
    assert orders["0"] != orders["1"]
    digests = []
    for seed in ("0", "1"):
        out = tmp_path / f"seed{seed}"
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=os.pathsep.join(
            [os.path.join(ROOT, "scripts"), os.path.join(ROOT, "libs", "openalex-corpus", "src")]))
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "corpus_rel_venues.py"),
                        "--pool", str(tmp_path / "pool.csv"), "--intake-dir", intake,
                        "--oa-cache", str(tmp_path / "oa.csv"), "--toc-manifest", str(tmp_path / "toc.csv"),
                        "--archive-root", registries, "--output-dir", str(out)], check=True, env=env)
        digests.append({n: hashlib.sha256((out / n).read_bytes()).hexdigest()
                        for n in sorted(os.listdir(out))})
    assert digests[0] == digests[1] and len(digests[0]) == 4


# ── Panel fixes (PR 1657, top-level review) ──────────────


def test_kanal_x_flags_only_the_works_of_an_x_year(tmp_path, registries):
    """Red test: the latest-level rule flagged the venue's works of every year."""
    oa = [{"openalex_id": w, "status": "found", "source_id": "S70", "source_name": "Doubtful Journal of Economics",
           "source_type": "journal", "issn_l": "1111-1119", "issns": "1111-1119"} for w in ("W71", "W72", "W73")]
    pool = [{"work_key": f"openalex:{w}", "openalex_id": w, "all_openalex_ids": w, "year": y, "sources": "catalogue",
             "member_record_ids": f"openalex:{w}"} for w, y in (("W71", "2025"), ("W72", "2026"), ("W73", ""))]
    _run(tmp_path, registries, tmp_path / "out", extra_oa=oa, extra_pool=pool)
    works = rv.load_work_venues(str(tmp_path / "out" / "rel_work_venues.csv"))
    # Journal 1 is level 1 in 2025 and X in 2026; an undated work gets no level.
    assert {w: works[f"openalex:{w}"]["flags"] for w in ("W71", "W72", "W73")} == {
        "W71": "", "W72": "kanalregisteret:1[issn]", "W73": ""}
    assert [w for w in ("W71", "W72", "W73") if works[f"openalex:{w}"]["excluded"]] == ["W72"]
    venues = {r["venue_key"]: r for r in csv.DictReader(open(tmp_path / "out" / "rel_venues.csv", encoding="utf-8"))}
    v = venues["openalex:S70"]
    assert v["flags"] == "kanalregisteret:1[issn]" and v["n_works_excluded"] == "1"
    assert "Nivå 2025 1, 2026 X" in v["flag_details"]


def test_hijacked_check_reads_sourceless_rows_and_member_urls(tmp_path, registries):
    """Replay of openalex:W3176977668: a cache row with a clone landing page and no
    source was never checked; nor were member-record URLs of non-OpenAlex lanes."""
    oa = [{"openalex_id": "W3176977668", "status": "found", "work_type": "article",
           "landing_url": "https://www.aomannals.com/article/7"}]
    pool = [{"work_key": "openalex:W3176977668", "openalex_id": "W3176977668", "all_openalex_ids": "W3176977668",
             "year": "2021", "sources": "catalogue", "member_record_ids": "openalex:W3176977668"},
            {"work_key": "url:clone", "year": "2022", "sources": "t1790-sud-playwright",
             "member_record_ids": "t1790-sud-playwright/d:pw:1"}]
    recs = {"t1790-sud-playwright": [{"record_id": "pw:1", "url": "https://aomannals.com/vol3/x.pdf"}]}
    _run(tmp_path, registries, tmp_path / "out", extra_oa=oa, extra_pool=pool, extra_recs=recs)
    works = rv.load_work_venues(str(tmp_path / "out" / "rel_work_venues.csv"))
    for k in ("openalex:W3176977668", "url:clone"):
        assert (works[k]["tier"], works[k]["flags"], works[k]["excluded"]) == ("unknown", "hijacked:1[domain]", True), k


def test_no_venue_switch_keeps_or_drops_the_unknown_tier(tmp_path, registries):
    _run(tmp_path, registries, tmp_path / "out")
    path = str(tmp_path / "out" / "rel_work_venues.csv")
    kept = rv.load_work_venues(path)
    assert kept["title:x|2020"]["unknown"] and kept["title:x|2020"]["included"]
    dropped = rv.load_work_venues(path, no_venue="exclude")
    assert not dropped["title:x|2020"]["included"]
    assert {k for k in kept if kept[k]["included"] != dropped[k]["included"]} == {"title:x|2020"}
    assert TIERS_CFG["no_venue"] == {"status": "pending", "value": "keep_flagged"}
    assert rv.unknown_switch(TIERS_CFG) == "keep_flagged"
    with pytest.raises(ValueError):
        rv.unknown_switch({"no_venue": {"value": "drop"}})


def test_unknown_exclusion_registry_is_refused(registries):
    cfg = dict(REG_CFG, exclusion={"status": "pending", "exclude": ["kanalregister"]})
    with pytest.raises(ValueError, match="unknown registries"):
        crv.load_registries(registries, cfg)


@pytest.mark.parametrize("venue, expected", [
    (_v(name="REPeC", source_type="journal"), ("A", "journal", "")),
    (_v(name="Compra Journal of Economics", source_type="journal"), ("A", "journal", "")),
    (_v(name="Research Papers in Economics and Finance", source_type="journal"), ("A", "journal", "")),
    (_v(name="RePEc: Research Papers in Economics", source_type="repository"), ("C", "repository", "")),
    (_v(name="MPRA Paper", source_type="other"), ("C", "repository", "")),
    (_v(repec="repec:wop:pennin", name="Center for Financial Institutions Working Papers"), ("C", "other", "")),
    (_v(repec="repec:wop:iasawp", name="Working Papers"), ("B", "b_series", "iiasa")),
    (_v(repec="repec:cam:camdae", name="Cambridge Working Papers in Economics"), ("C", "other", "")),
    (_v(repec="repec:een:ccepwp", name="CCEP Working Papers"), ("B", "b_series", "ccep_anu")),
    (_v(repec="repec:ctl:louvde", repec_template="redif-article", name="Journal of Demographic Economics"),
     ("A", "journal", "")),
])
def test_repository_names_and_shared_repec_archives(venue, expected):
    assert rv.assign_tier(venue, TIERS) == expected


def test_b_institution_by_its_own_site_for_unresolved_and_c_works(tmp_path, registries):
    """WRI, SEI, Oxfam... reports sat in tier unknown: no venue, but a landing page on the institution's site."""
    oa = [{"openalex_id": "W81", "status": "found", "landing_url": "https://files.wri.org/d8/s3fs-public/x.pdf"},
          {"openalex_id": "W82", "status": "found", "landing_url": "https://policy-practice.oxfam.org/resources/y"},
          {"openalex_id": "W83", "status": "found", "source_id": "S83", "source_type": "repository",
           "source_name": "Zenodo", "landing_url": "https://zenodo.org/records/1"},
          {"openalex_id": "W84", "status": "found", "landing_url": "https://notwri.org/z"}]
    pool = [{"work_key": f"openalex:{w}", "openalex_id": w, "all_openalex_ids": w, "year": "2020",
             "sources": "catalogue", "member_record_ids": f"openalex:{w}"} for w in ("W81", "W82", "W83", "W84")]
    _run(tmp_path, registries, tmp_path / "out", extra_oa=oa, extra_pool=pool)
    works = rv.load_work_venues(str(tmp_path / "out" / "rel_work_venues.csv"))
    got = {w: (works[f"openalex:{w}"]["tier"], works[f"openalex:{w}"]["tier_rule"], works[f"openalex:{w}"]["b_id"],
               works[f"openalex:{w}"]["tier_ngo_not_b"]) for w in ("W81", "W82", "W83", "W84")}
    assert got == {
        "W81": ("B", "b_domain", "wri", "B"),
        "W82": ("B", "b_domain", "oxfam", "unknown"),   # NGO series: the other setting leaves it unresolved
        "W83": ("C", "repository", "", "C"),            # Zenodo is nobody's own site
        "W84": ("unknown", "no_venue", "", "unknown"),  # notwri.org is not under wri.org
    }


def test_bndes_repository_is_b():
    assert rv.assign_tier(_v(name="BNDES (The National Development Bank)", source_type="repository"), TIERS) == (
        "B", "b_institution", "bndes")


def test_b_domains_name_existing_entries():
    with pytest.raises(ValueError, match="not in b_list"):
        rv.compile_tiers(dict(TIERS_CFG, b_domains={"no_such_entry": ["x.org"]}))
