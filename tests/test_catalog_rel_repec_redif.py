"""Ticket 1810: the ReDIF parser and the mirror table builder."""

import json
import os

import _redif
import catalog_rel_repec_redif as cat
import pandas as pd
import pytest

pytestmark = pytest.mark.domain_corpus

# Shapes copied from the mirror (2026-10-01): AEA article with a DOI in a Note,
# World Bank paper with a multi-line abstract, a series template.
ARTICLE = """Template-Type: ReDIF-Article 1.0
Author-Name: Angus Deaton
Title: Price Indexes, Inequality, and the Measurement of World Poverty
Abstract: I discuss the measurement of world poverty
and inequality.
Purpose: this line opens with a colon word but is not an attribute
https://example.org/not-an-attribute stays in the abstract
Journal: American Economic Review
Pages: 5-34
Volume: 100
Issue: 1
Year: 2010
Note: DOI: 10.1257/aer.100.1.5
Classification-JEL: C43, D31, I31
Handle: RePEc:aea:aecrev:v:100:y:2010:i:1:p:5-34
Template-Type: ReDIF-Article 1.0
Author-Name: Timothy G. Conley
Author-Name: Christopher R. Udry
Title: Learning about a New Technology: Pineapple in Ghana
Year: 2010
Handle: RePEc:aea:aecrev:v:100:y:2010:i:1:p:35-69
"""

PAPER = """Template-type: ReDIF-Paper 1.0
Author-Name: Larsen, Bjorn
Title: World fossil fuel subsidies and global carbon emissions

Abstract: Larsen and Shah present evidence on fossil fuel subsidies.

Keywords: Environmental Economics&Policies,Carbon Policy and Trading
Number: 1002
Creation-Date: 1992-10-31
File-URL: https://doi.org/10.1596/1813-9450-1002
Handle: RePEc:wbk:wbrwps:1002
"""

SERIES = """Template-Type: ReDIF-Series 1.0
Name: Policy Research Working Paper Series
Type: ReDIF-Paper
Handle: RePEc:wbk:wbrwps
"""

BOOK = """﻿Template-Type: ReDIF-Book 1.0
Editor-Name: Schneider
Title: Macht und ökonomisches Gesetz
Classification-JEL: None
Year: 20210430
Handle: RePEc:dah:svssvs:1
"""


def test_templates_and_continuations():
    tpls = list(_redif.iter_templates(ARTICLE))
    assert len(tpls) == 2
    a = _redif.to_row(tpls[0])
    assert a["title"] == "Price Indexes, Inequality, and the Measurement of World Poverty"
    assert a["abstract"].startswith("I discuss the measurement of world poverty and inequality.")
    assert "Purpose: this line" in a["abstract"] and "https://example.org" in a["abstract"]
    assert a["doi"] == "10.1257/aer.100.1.5"
    assert a["jel"] == "C43; D31; I31"
    assert a["year"] == "2010" and a["journal"] == "American Economic Review"
    assert a["series_handle"] == "repec:aea:aecrev"
    b = _redif.to_row(tpls[1])
    assert b["authors"] == "Timothy G. Conley; Christopher R. Udry"
    assert b["doi"] == "" and b["abstract"] == ""


def test_paper_year_doi_and_series_name():
    (t,) = list(_redif.iter_templates(PAPER))
    r = _redif.to_row(t, {"repec:wbk:wbrwps": "Policy Research Working Paper Series"})
    assert r["template_type"] == "redif-paper"
    assert r["year"] == "1992"
    assert r["doi"] == "10.1596/1813-9450-1002"
    assert r["journal"] == "Policy Research Working Paper Series"
    assert r["abstract"] == "Larsen and Shah present evidence on fossil fuel subsidies."
    (s,) = list(_redif.iter_templates(SERIES))
    assert _redif.series_of(s) == ("repec:wbk:wbrwps", "Policy Research Working Paper Series")


def test_book_with_bom_editor_and_compact_year():
    raw = BOOK.encode("utf-8")
    assert _redif.looks_like_redif(raw)
    text, enc = _redif.decode(raw)
    (t,) = list(_redif.iter_templates(text))
    r = _redif.to_row(t)
    assert (enc, r["year"], r["authors"], r["jel"]) == ("utf-8", "2021", "Schneider", "")


def test_year_rejects_long_numbers():
    assert _redif.find_year({"year": ["19945"]}) == ""
    assert _redif.find_year({"creation-date": ["2013-06"]}) == "2013"


def test_decode_falls_back_and_sniff_rejects_html():
    text, enc = _redif.decode("Title: Café".encode("cp1252"))
    assert enc == "cp1252" and text.endswith("Café")
    assert _redif.looks_like_redif("Template-Type: ReDIF-Paper 1.0\n".encode("utf-16"))
    assert not _redif.looks_like_redif(b"<html><body>Template-Type: no</body></html>")


def test_build_table_dedups_handles_and_names_series(tmp_path):
    root = tmp_path / "RePEc"
    (root / "wbk" / "wbrwps").mkdir(parents=True)
    (root / "aea" / "aecrev").mkdir(parents=True)
    (root / "wbk" / "wbkseri.rdf").write_text(SERIES, encoding="utf-8")
    (root / "wbk" / "wbrwps" / "1002.rdf").write_text(PAPER, encoding="utf-8")
    (root / "wbk" / "wbrwps" / "1002.rdf~").write_text(PAPER, encoding="utf-8")
    (root / "wbk" / "wbrwps" / "paper.pdf").write_bytes(b"%PDF-1.4 Template-Type: ReDIF-Paper")
    (root / "aea" / "aecrev" / "AER_1.redif").write_text(ARTICLE, encoding="utf-8")
    out = tmp_path / "out" / "redif.parquet"
    assert cat.main(["--mirror", str(root), "--output", str(out), "--jobs", "1"]) == 0
    d = pd.read_parquet(out)
    assert sorted(d.handle) == sorted(["RePEc:wbk:wbrwps:1002",
                                       "RePEc:aea:aecrev:v:100:y:2010:i:1:p:5-34",
                                       "RePEc:aea:aecrev:v:100:y:2010:i:1:p:35-69"])
    wb = d[d.handle == "RePEc:wbk:wbrwps:1002"].iloc[0]
    assert wb.source_file == os.path.join("wbk", "wbrwps", "1002.rdf")
    assert wb.journal == "Policy Research Working Paper Series"
    counts = json.loads((tmp_path / "out" / "redif.counts.json").read_text())["counts"]
    assert counts["duplicate_handle"] == 1
    assert counts["rows"] == 3 and counts["rows:redif-article"] == 2
    assert counts["templates:redif-series"] == 1
    dups = pd.read_csv(tmp_path / "out" / "redif.duplicates.csv")
    assert dups.source_file.tolist() == [os.path.join("wbk", "wbrwps", "1002.rdf~")]


def test_rsync_counts(tmp_path):
    log = tmp_path / "r.log"
    log.write_text(".d..t...... ./\n>f+++++++++ a/x.rdf\n>f.st...... a/y.rdf\n>f..t...... a/z.rdf\n"
                   "*deleting   a/old.rdf\n*deleting   a/olddir/\ncd+++++++++ b/\n\n"
                   "sent 1 bytes  received 2 bytes  3.00 bytes/sec\ntotal size is 10  speedup is 1.00\n")
    c = cat.rsync_counts(str(log))
    assert (c["new_files"], c["updated_files"], c["updated_size_and_time"], c["updated_time_only"],
            c["deleted"], c["deleted_dirs"], c["new_dirs"], c["finished"]) == (1, 2, 1, 1, 1, 1, 1, True)
    log.write_text(">f+++++++++ a/x.rdf\n")
    assert cat.rsync_counts(str(log))["finished"] is False


def test_clean_replaces_surrogates():
    assert cat.clean("a\udc92b") == "a\ufffdb"
    assert cat.clean("Café") == "Café"
    assert cat.clean("x\ud800y") == "x?y"


def test_duplicate_handle_keeps_the_fuller_copy(tmp_path):
    root = tmp_path / "RePEc"
    (root / "eee" / "jdevec").mkdir(parents=True)
    bare = "Template-Type: ReDIF-Article 1.0\nTitle: T\nYear: 2001\nHandle: RePEc:eee:jdevec:v:1:y:2001:i:1:p:1\n"
    full = bare.replace("Year: 2001", "Year: 2001\nAbstract: An abstract.")
    (root / "eee" / "jdevec" / "a.rdf").write_text(bare, encoding="utf-8")
    (root / "eee" / "jdevec" / "b.rdf").write_text(full, encoding="utf-8")
    out = tmp_path / "o" / "t.parquet"
    assert cat.main(["--mirror", str(root), "--output", str(out), "--jobs", "1"]) == 0
    d = pd.read_parquet(out)
    assert d.abstract.tolist() == ["An abstract."]
    dups = pd.read_csv(tmp_path / "o" / "t.duplicates.csv")
    assert dups.source_file.tolist() == [os.path.join("eee", "jdevec", "a.rdf")]


def test_template_type_tolerates_suffix_typos():
    assert _redif.template_type({"template-type": ["ReDIF-Paper: 1.0"]}) == "redif-paper"
    assert _redif.template_type({"template-type": ["ReDIF-Article1.0"]}) == "redif-article"
    assert _redif.template_type({"template-type": ["ReDIF-Person 1.0"]}) == "redif-person"


@pytest.mark.parametrize("raw,want", [
    ("RePEc:zbw:hwware:26096 #END 46 #BEGIN 47", "RePEc:zbw:hwware:26096"),
    ("RePEc: rsp: wpaper: wp48", "RePEc:rsp:wpaper:wp48"),
    ("RePEc:aud:audfin:v:20:y:2018:i:Special 12:p:827", "RePEc:aud:audfin:v:20:y:2018:i:Special12:p:827"),
    ("RePEc:aen:eeepjl:eeep10-2-von der Fehr", "RePEc:aen:eeepjl:eeep10-2-vonderFehr"),
    ("Repec:sos:sosjrn:170307਀", "RePEc:sos:sosjrn:170307"),
    ("repec:aea:aecrev:v:100:y:2010:i:1:p:5-34", "RePEc:aea:aecrev:v:100:y:2010:i:1:p:5-34"),
    ("not a handle", ""),
    ("RePEc:aea:aecrev", ""),
])
def test_norm_handle(raw, want):
    assert _redif.norm_handle(raw) == want


def test_inner_spaces_keep_distinct_works_apart_and_continuations_out():
    a = _redif.norm_handle("RePEc:aud:audfin:v:20:y:2018:i:Special 12:p:827")
    b = _redif.norm_handle("RePEc:aud:audfin:v:20:y:2018:i:Special 12:p:1016")
    assert a != b
    text = ("Template-Type: ReDIF-Article 1.0\nTitle: T\n"
            "Handle: RePEC: srs: jaes: v:10:y:2015:i:1(31)_Spring2015:p:20-33\nThe article template\n")
    (t,) = list(_redif.iter_templates(text))
    assert _redif.to_row(t)["handle"] == "RePEc:srs:jaes:v:10:y:2015:i:1(31)_Spring2015:p:20-33"


def test_to_row_keeps_the_raw_handle_when_normalised():
    tpl = {"template-type": ["ReDIF-Paper 1.0"], "title": ["T"],
           "handle": ["RePEc:zbw:hwware:26096 #END 46"]}
    r = _redif.to_row(tpl)
    assert r["handle"] == "RePEc:zbw:hwware:26096"
    assert r["handle_raw"] == "RePEc:zbw:hwware:26096 #END 46"
    assert _redif.to_row({"handle": ["RePEc:aaa:bbb:1"]})["handle_raw"] == ""
    assert r["handle_valid"] == "1"
    # malformed at source (empty series code): kept, flagged
    bad = _redif.to_row({"handle": ["RePEc:bre::node_10366"]})
    assert (bad["handle"], bad["handle_valid"]) == ("RePEc:bre::node_10366", "0")


def test_mixed_encoding_file_keeps_its_utf8_lines():
    raw = ("Title: Café “climate”\n".encode("utf-8") + "Abstract: café\n".encode("cp1252")
           + "Title: Ünïcode\n".encode("utf-8"))
    text, enc = _redif.decode(raw)
    assert enc == "mixed"
    assert text.splitlines() == ["Title: Café “climate”", "Abstract: café", "Title: Ünïcode"]
    assert _redif.decode("Title: café".encode("cp1252"))[1] == "cp1252"
