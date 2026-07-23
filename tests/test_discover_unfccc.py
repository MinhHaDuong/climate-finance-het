"""Tests for discover_unfccc.py — CDX-based candidate discovery for the
UNFCCC key-documents layer (ticket 0304).

The discovery script enumerates candidate documents from the Wayback CDX
index (the unfccc.int Drupal facet search sits behind an Incapsula JS
challenge, so the polite facet crawl decided in the ticket is impossible
from a headless pipeline; the CDX index over the same stable URL patterns
is the recorded substitute — candidates are still verified live at harvest).

No network: CDX responses are monkeypatched fixtures.
"""

import json
import os
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, os.path.join(SCRIPTS_DIR, "harvest"))

import discover_unfccc as du


class TestSymbolConstruction:
    def test_old_style_addendum(self):
        sym = du.decision_symbol("cop", 2009, "11a01.pdf")
        assert sym == "FCCC/CP/2009/11/Add.1"

    def test_old_style_cmp(self):
        assert du.decision_symbol("cmp", 2005, "08a01.pdf") == \
            "FCCC/KP/CMP/2005/8/Add.1"

    def test_new_style_cma(self):
        assert du.decision_symbol("cma", 2021, "cma2021_10a01E.pdf") == \
            "FCCC/PA/CMA/2021/10/Add.1"

    def test_inc_symbol(self):
        assert du.inc_symbol("15.pdf") == "A/AC.237/15"
        assert du.inc_symbol("91a01.pdf") == "A/AC.237/91/Add.1"
        assert du.inc_symbol("18p2a01.pdf") == "A/AC.237/18 (Part II)/Add.1"


class TestCdxParsing:
    def test_filters_junk_and_dedupes(self):
        rows = [
            "http://unfccc.int:80/resource/docs/2015/cop21/eng/10a01.pdf",
            "https://unfccc.int/resource/docs/2015/cop21/eng/10a01.pdf",
            "http://unfccc.int/resource/docs/2015/cop21/eng/10a01.pdf.46X",
            "http://unfccc.int/resource/docs/2015/cop21/eng/l09.pdf",
            "https://unfccc.int/resource/docs/2015/cop21/eng/10a02.pdf",
        ]
        files = du.extract_files(rows, du.OLD_DECISION_FILE)
        assert files == ["10a01.pdf", "10a02.pdf"]

    def test_enb_english_issues(self):
        rows = [
            "http://enb.iisd.org:80/download/pdf/enb12459e.pdf",
            "https://enb.iisd.org/download/pdf/enb12459f.pdf",
            "https://enb.iisd.org/download/pdf/enb12120eRev1.pdf",
            "https://enb.iisd.org/download/pdf/enb12459e.pdf?x=1",
        ]
        files = du.extract_files(rows, du.ENB_FILE)
        assert files == ["enb12120eRev1.pdf", "enb12459e.pdf"]


class TestCandidates:
    def test_decision_candidate_record(self):
        c = du.decision_candidate("cop", 21, 2015, "10a01.pdf")
        assert c["symbol"] == "FCCC/CP/2015/10/Add.1"
        assert c["doc_class"] == "decision"
        assert c["year"] == 2015
        assert c["url"].endswith("/resource/docs/2015/cop21/eng/10a01.pdf")
        assert "twenty-first session" in c["title"]

    def test_ordinal(self):
        assert du.ordinal(1) == "first"
        assert du.ordinal(21) == "twenty-first"
        assert du.ordinal(29) == "twenty-ninth"


class TestMainWritesJsonl(object):
    def test_end_to_end_with_mocked_cdx(self, tmp_path, monkeypatch):
        def fake_cdx(url_pattern):
            if "resource/docs/a/" in url_pattern:
                return ["https://unfccc.int/resource/docs/a/15.pdf"]
            if "cop21" in url_pattern:
                return ["https://unfccc.int/resource/docs/2015/cop21/eng/10a01.pdf"]
            if "enb12" in url_pattern:
                return ["https://enb.iisd.org/download/pdf/enb12663e.pdf"]
            return []

        monkeypatch.setattr(du, "cdx_urls", fake_cdx)
        out = tmp_path / "cand.jsonl"
        du.main(["--output", str(out), "--series", "inc", "enb"])
        recs = [json.loads(line) for line in out.read_text().splitlines()]
        symbols = {r["symbol"] for r in recs}
        assert "A/AC.237/15" in symbols
        assert any(r["series"] == "enb" for r in recs)
        for r in recs:
            assert r["url"].startswith("http")
            assert r["doc_class"] in ("decision", "inc", "negotiation_record")
