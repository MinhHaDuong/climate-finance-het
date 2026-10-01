"""REL venue tiers and registry flags (ticket 1841): parsers, rules, determinism."""

import csv
import hashlib
import json
import os
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


def test_kanalregisteret_latest_level_x_only(registries):
    day = os.path.join(registries, str(REG_CFG["use"]))
    rows, entries = rvr.parse_kanalregisteret(os.path.join(day, "kanalregisteret_851.csv"), "u{id}")
    assert rows == 3
    # Journal 2 was X in 2026 but has a 2027 level: the latest level wins.
    assert [(e["entry_id"], e["issns"], e["entry_url"]) for e in entries] == [("1", ("1111-1119",), "u1")]


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


def _inputs(tmp_path):
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
    pool_cols = ["work_key", "openalex_id", "all_openalex_ids", "journal", "doc_type", "sources", "member_record_ids"]
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
    rec_cols = ["record_id", "issn", "journal_key", "series_handle", "template_type", "url"]
    intake = tmp_path / "intake"
    for lane, recs in {
        "t1530-sud-openalex": [{"record_id": "W2"}],
        "t1810-repec-local": [{"record_id": "oai:1", "series_handle": "RePEc:gam:jeners",
                               "template_type": "redif-article"}],
        "t1653-sud-hors-openalex": [{"record_id": "ipea:hdl:1"}],
        "t1650-sommaires": [{"record_id": "doi:10.1/toc", "issn": "5555-5552", "journal_key": "sj"}],
        "t1652-causal-econlit": [{"record_id": "z"}],
    }.items():
        _write(str(intake / lane / "d" / "records.csv"), rec_cols, recs)
    _write(str(tmp_path / "oa.csv"), OA_COLS, oa)
    _write(str(tmp_path / "pool.csv"), pool_cols, pool)
    _write(str(tmp_path / "toc.csv"), ["journal_key", "publisher"], [{"journal_key": "sj", "publisher": "P"}])
    return str(intake)


def _run(tmp_path, registries, out, extra=()):
    intake = _inputs(tmp_path)
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
        "title:x|2020": ("none", "none", "C", "", ""),
        "title:y|2020": ("name:revista andina de economia", "name", "A", "", ""),
    }
    assert works["openalex:W2"]["flagged"] is True and works["openalex:W2"]["tier_included"] is True
    counts = json.load(open(tmp_path / "out" / "rel_venue_counts.json", encoding="utf-8"))
    assert counts["works_by_lane"]["(all)"]["tier"] == {"A": 6, "B": 3, "C": 1}
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
