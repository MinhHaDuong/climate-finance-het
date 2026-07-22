"""Tests for catalog_keydocs.py — the curated UNFCCC / OECD DAC key-documents
importer (ticket 0288, corpus v2 layer).

Covers:
- seed loading and validation (required fields, doc_class enums, unique symbols)
- the no-DOI dedup-by-design guard: a seed entry carrying a `doi:` key is
  rejected, so an OECD work already in the corpus via its 10.1787 DOI cannot
  be re-added through this layer
- record building (WORKS_COLUMNS mapping, abstract_provenance flag)
- abstract-equivalent derivation (executive-summary heuristic, lead fallback)
- text extraction with OCR fallback wiring (subprocess mocked; the real OCR
  path is exercised by an integration test that skips when ocrmypdf is absent)
- the real seed files: parse, validate, and overlap with grey_sources.yaml
  only on identical normalized title+year (so catalog_merge collapses them)

No network: fetching is monkeypatched throughout.
"""

import os
import re
import sys

import pandas as pd
import pytest
import yaml

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, os.path.join(SCRIPTS_DIR, "harvest"))

import catalog_keydocs as ck
from utils import WORKS_COLUMNS

BASE = os.path.join(os.path.dirname(__file__), "..")
UNFCCC_SEED = os.path.join(BASE, "config", "unfccc_sources.yaml")
OECD_SEED = os.path.join(BASE, "config", "oecd_dac_sources.yaml")
GREY_SEED = os.path.join(BASE, "config", "grey_sources.yaml")


def _entry(**over):
    e = {
        "symbol": "FCCC/CP/2009/11/Add.1",
        "title": "Report of the Conference of the Parties on its fifteenth session",
        "year": 2009,
        "body": "UNFCCC Conference of the Parties",
        "doc_class": "decision",
        "language": "en",
        "url": "https://example.org/doc.pdf",
        "provenance": "test",
    }
    e.update(over)
    return e


def _write_seed(tmp_path, entries):
    path = tmp_path / "seed.yaml"
    path.write_text(yaml.safe_dump({"documents": entries}))
    return str(path)


class TestLoadSeed:
    def test_loads_valid_entries(self, tmp_path):
        path = _write_seed(tmp_path, [_entry()])
        entries = ck.load_seed(path, "unfccc")
        assert len(entries) == 1
        assert entries[0]["symbol"] == "FCCC/CP/2009/11/Add.1"

    def test_missing_required_field_rejected(self, tmp_path):
        bad = _entry()
        del bad["title"]
        path = _write_seed(tmp_path, [bad])
        with pytest.raises(ValueError, match="title"):
            ck.load_seed(path, "unfccc")

    def test_unknown_doc_class_rejected(self, tmp_path):
        path = _write_seed(tmp_path, [_entry(doc_class="blogpost")])
        with pytest.raises(ValueError, match="doc_class"):
            ck.load_seed(path, "unfccc")

    def test_duplicate_symbol_rejected(self, tmp_path):
        path = _write_seed(tmp_path, [_entry(), _entry()])
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            ck.load_seed(path, "unfccc")

    def test_doi_key_rejected_dedup_by_design(self, tmp_path):
        """An entry with a DOI must be refused: DOI'd works (e.g. OECD
        10.1787 publications already in the corpus via OpenAlex) enter
        through the academic-source path, never through this layer."""
        path = _write_seed(
            tmp_path,
            [_entry(symbol="DCD/DAC(2016)3/FINAL", doi="10.1787/9789264249424-en",
                    doc_class="statistical_directive")],
        )
        with pytest.raises(ValueError, match="doi"):
            ck.load_seed(path, "oecd")


class TestBuildRecord:
    def test_maps_works_columns(self):
        rec = ck.build_record(
            _entry(), "unfccc",
            abstract="Decides that...", abstract_provenance="reconstructed:lead")
        for col in WORKS_COLUMNS:
            assert col in rec
        assert rec["source"] == "unfccc"
        assert rec["source_id"] == "FCCC/CP/2009/11/Add.1"
        assert rec["doi"] == ""
        assert rec["year"] == "2009"
        assert rec["journal"] == "UNFCCC Conference of the Parties"
        assert rec["abstract"] == "Decides that..."
        assert rec["abstract_provenance"] == "reconstructed:lead"
        assert "decision" in rec["categories"]

    def test_curated_abstract_used_verbatim(self):
        rec = ck.build_record(
            _entry(abstract="Hand-written summary."), "unfccc",
            abstract=None, abstract_provenance=None)
        assert rec["abstract"] == "Hand-written summary."
        assert rec["abstract_provenance"] == "curated"

    def test_keywords_not_hijacked_by_short_title(self):
        """Author rule (2026-07-22): keywords are never faked from titles —
        metadata-only records carry empty keywords, not the short_title."""
        rec = ck.build_record(
            _entry(), "unfccc", abstract=None, abstract_provenance=None)
        assert rec["keywords"] == ""
        assert rec["keywords_provenance"] == ""

    def test_keywords_carried_with_provenance(self):
        rec = ck.build_record(
            _entry(), "unfccc", abstract=None, abstract_provenance=None,
            keywords="climate finance; adaptation",
            keywords_provenance="generated:lexicon")
        assert rec["keywords"] == "climate finance; adaptation"
        assert rec["keywords_provenance"] == "generated:lexicon"


class TestDeriveKeywords:
    def test_extracted_from_first_page_block(self):
        text = (
            "OECD DEVELOPMENT CO-OPERATION DIRECTORATE\n"
            "Keywords: climate finance, Rio markers, ODA\n"
            + "Body text follows here at some length. " * 100
        )
        kw, prov = ck.derive_keywords(text)
        assert kw == "climate finance, Rio markers, ODA"
        assert prov == "extracted"

    def test_generated_from_lexicon_when_no_block(self):
        text = (
            "The Conference of the Parties decides that adaptation and "
            "long-term climate finance through the Green Climate Fund "
            "shall be scaled up. " * 30
        )
        kw, prov = ck.derive_keywords(text)
        assert prov == "generated:lexicon"
        low = kw.lower()
        assert "climate finance" in low
        assert "adaptation" in low
        assert "green climate fund" in low

    def test_keywords_block_beyond_first_page_ignored(self):
        """A 'Keywords:' line deep in the body is content, not metadata."""
        text = ("Plain opening text without lexicon terms. " * 200
                + "\nKeywords: not metadata\n")
        kw, prov = ck.derive_keywords(text)
        assert prov != "extracted"

    def test_empty_without_text(self):
        assert ck.derive_keywords("") == ("", "")


class TestDeriveAbstract:
    def test_executive_summary_section_preferred(self):
        text = (
            "UNITED NATIONS\nDistr. GENERAL\n\n"
            "Executive summary\n"
            + "The Standing Committee finds that climate finance flows "
              "reached USD 100 billion. " * 20
            + "\nI. Introduction\nLong body text follows. " * 50
        )
        abstract, method = ck.derive_abstract(text)
        assert method == "reconstructed:exec_summary"
        assert abstract.startswith("The Standing Committee finds")
        assert len(abstract.split()) <= ck.ABSTRACT_MAX_WORDS

    def test_lead_fallback_when_no_summary_section(self):
        text = "Decision 2/CP.15. The Conference of the Parties takes note. " * 40
        abstract, method = ck.derive_abstract(text)
        assert method == "reconstructed:lead"
        assert len(abstract.split()) <= ck.ABSTRACT_MAX_WORDS

    def test_masthead_boilerplate_stripped_from_lead(self):
        """UN document cover-page lines (UNITED NATIONS / Distr. GENERAL /
        symbol / date / Original: ENGLISH) must not pollute the
        abstract-equivalent — seen on the COP15 e2e run."""
        text = (
            "UNITED NATIONS\n"
            "Distr.\nGENERAL\n"
            "FCCC/CP/2009/11/Add.1\n"
            "30 March 2010\n"
            "Original: ENGLISH\n"
            "CONFERENCE OF THE PARTIES\n"
            + ("Report of the Conference of the Parties on its fifteenth "
               "session. The Conference of the Parties adopted the following "
               "decisions on long-term cooperative action and finance. " * 10)
        )
        abstract, method = ck.derive_abstract(text)
        assert method == "reconstructed:lead"
        assert not abstract.startswith("UNITED NATIONS")
        assert "Distr." not in abstract
        assert "Original: ENGLISH" not in abstract
        assert abstract.startswith("Report of the Conference")

    def test_empty_text_gives_no_abstract(self):
        abstract, method = ck.derive_abstract("")
        assert abstract == ""
        assert method == ""

    def test_mixed_case_prose_survives_masthead_strip(self):
        """The ALL-CAPS masthead branch must be case-sensitive (PR #1085
        review): under re.IGNORECASE it matched any prose line without
        digits or periods and ate decision titles and preambles."""
        text = (
            "UNITED NATIONS\n"
            "FCCC/CP/2009/11/Add.1\n"
            "Report of the Conference of the Parties\n"
            "Recalling the relevant provisions of the Convention\n"
            + "The Conference of the Parties adopted decisions on "
              "long-term finance. " * 20
        )
        abstract, method = ck.derive_abstract(text)
        assert method == "reconstructed:lead"
        assert abstract.startswith("Report of the Conference of the Parties")
        assert "Recalling the relevant provisions" in abstract


class TestGetDocumentText:
    def test_text_layer_used_when_present(self, tmp_path, monkeypatch):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-fake")
        monkeypatch.setattr(ck, "extract_text",
                            lambda p: "A perfectly extractable text layer. " * 30)
        text, status = ck.get_document_text(str(pdf), str(tmp_path / "doc.txt"))
        assert status == "text_layer"
        assert "extractable" in text

    def test_ocr_fallback_when_scanned(self, tmp_path, monkeypatch):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-fake")
        monkeypatch.setattr(ck, "extract_text", lambda p: "")
        ocred = "Recognized scanned text from the 1992 INC session report. " * 10
        monkeypatch.setattr(ck, "ocr_text", lambda p, t: ocred)
        text, status = ck.get_document_text(str(pdf), str(tmp_path / "doc.txt"))
        assert status == "ocr"
        assert text == ocred

    def test_needs_ocr_flag_when_tool_unavailable(self, tmp_path, monkeypatch):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-fake")
        monkeypatch.setattr(ck, "extract_text", lambda p: "")
        monkeypatch.setattr(ck, "ocr_text", lambda p, t: None)
        text, status = ck.get_document_text(str(pdf), str(tmp_path / "doc.txt"))
        assert status == "needs_ocr"
        assert text == ""

    def test_txt_cache_reused_without_reextraction(self, tmp_path, monkeypatch):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-fake")
        txt = tmp_path / "doc.txt"
        txt.write_text("cached text from a previous run")

        def boom(p):
            raise AssertionError("must not re-extract when cache exists")

        monkeypatch.setattr(ck, "extract_text", boom)
        text, status = ck.get_document_text(str(pdf), str(txt))
        assert status == "cached"
        assert text == "cached text from a previous run"

    def test_short_ocr_sidecar_does_not_poison_cache(self, tmp_path, monkeypatch):
        """ocrmypdf writes its sidecar to the cache path even when the OCR
        text is under MIN_TEXT_CHARS; a rerun must not serve that stub as
        'cached' (PR #1085 review — incremental 0304 harvest safety)."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-fake")
        txt = tmp_path / "doc.txt"
        monkeypatch.setattr(ck, "extract_text", lambda p: "")

        def stub_ocr(p, t):
            with open(t, "w", encoding="utf-8") as f:
                f.write("COVER PAGE ONLY")
            return "COVER PAGE ONLY"

        monkeypatch.setattr(ck, "ocr_text", stub_ocr)
        text, status = ck.get_document_text(str(pdf), str(txt))
        assert status == "needs_ocr"
        assert not txt.exists(), "under-threshold sidecar must be removed"
        text2, status2 = ck.get_document_text(str(pdf), str(txt))
        assert status2 == "needs_ocr", "rerun must retry OCR, not serve the stub"


class TestOcrTextUnavailable:
    def test_returns_none_when_ocrmypdf_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ck.shutil, "which", lambda name: None)
        assert ck.ocr_text(str(tmp_path / "x.pdf"), str(tmp_path / "x.txt")) is None


class TestMainEndToEnd:
    def test_metadata_only_run_writes_catalog(self, tmp_path, monkeypatch):
        """Without --fetch, main() builds the catalog from seed metadata alone
        — no network, empty abstracts unless curated."""
        seed = _write_seed(tmp_path, [
            _entry(),
            _entry(symbol="ENB/12/459", title="Summary of Copenhagen",
                   doc_class="negotiation_record",
                   abstract="Curated abstract."),
        ])
        out = tmp_path / "unfccc_works.csv"
        monkeypatch.setattr(ck, "fetch_pdf",
                            lambda *a, **k: (_ for _ in ()).throw(
                                AssertionError("no fetch in metadata-only run")))
        ck.main(["--input", seed, "--output", str(out),
                 "--source-name", "unfccc"])
        df = pd.read_csv(str(out), dtype=str, keep_default_na=False)
        assert len(df) == 2
        assert set(WORKS_COLUMNS).issubset(df.columns)
        assert "abstract_provenance" in df.columns
        assert (df["source"] == "unfccc").all()
        curated = df[df["source_id"] == "ENB/12/459"].iloc[0]
        assert curated["abstract"] == "Curated abstract."
        assert curated["abstract_provenance"] == "curated"


class TestRealSeeds:
    """The committed seed files are valid and dedup-safe against the
    existing grey seed list."""

    def test_unfccc_seed_valid(self):
        entries = ck.load_seed(UNFCCC_SEED, "unfccc")
        assert len(entries) >= 40

    def test_oecd_seed_valid(self):
        entries = ck.load_seed(OECD_SEED, "oecd")
        assert len(entries) >= 10

    def test_oecd_seed_has_no_doi_anywhere(self):
        """Non-DOI founding docs only — raw text sweep, belt and braces."""
        lines = [ln for ln in open(OECD_SEED, encoding="utf-8")
                 if not ln.lstrip().startswith("#")]
        raw = "".join(lines)
        assert "10.1787" not in raw
        assert not re.search(r"^\s*doi:", raw, re.MULTILINE)

    def test_grey_overlap_only_on_identical_title_year(self):
        """Every UNFCCC seed whose document already exists in
        grey_sources.yaml must repeat the grey title VERBATIM (same year),
        so catalog_merge title+year dedup collapses the pair into one row
        instead of duplicating the work."""
        from pipeline_text import normalize_title

        grey = yaml.safe_load(open(GREY_SEED, encoding="utf-8"))
        grey_keys = {
            (normalize_title(e["title"]), str(e["year"]))
            for e in grey if e.get("source_org", "").startswith("UNFCCC")
        }
        entries = ck.load_seed(UNFCCC_SEED, "unfccc")
        marked_overlap = [
            e for e in entries
            if "grey_sources.yaml" in e.get("provenance", "")
        ]
        assert len(marked_overlap) >= 5, \
            "the BA series overlap with grey seeds must be declared"
        for e in marked_overlap:
            key = (normalize_title(e["title"]), str(e["year"]))
            assert key in grey_keys, (
                f"{e['symbol']} claims grey overlap but its normalized "
                f"title+year does not match any grey UNFCCC seed: {key}"
            )


class TestDvcWiring:
    """The layer is a durable Phase-1 source: dvc stages produce the two
    per-source catalogs into data/catalogs/ and catalog_merge consumes them
    (catalog_files_from_dvc reads merge deps, so the merge picks them up
    with no code change)."""

    def _dvc(self):
        return yaml.safe_load(open(os.path.join(BASE, "dvc.yaml")))

    def test_stages_exist_and_write_to_catalogs(self):
        stages = self._dvc()["stages"]
        for stage, seed, out in [
            ("catalog_unfccc", "config/unfccc_sources.yaml",
             "data/catalogs/unfccc_works.csv"),
            ("catalog_oecd", "config/oecd_dac_sources.yaml",
             "data/catalogs/oecd_works.csv"),
        ]:
            assert stage in stages, f"missing dvc stage {stage}"
            st = stages[stage]
            assert seed in st["deps"], f"{stage} must depend on its seed list"
            assert "scripts/harvest/catalog_keydocs.py" in st["deps"]
            assert out in st["outs"], f"{stage} must produce {out} (Phase 1)"
            assert "--fetch" in st["cmd"], \
                f"{stage} runs the full harvest on padme"

    def test_merge_consumes_both_catalogs(self):
        deps = self._dvc()["stages"]["catalog_merge"]["deps"]
        assert "data/catalogs/unfccc_works.csv" in deps
        assert "data/catalogs/oecd_works.csv" in deps


class TestStemCollision:
    def test_stem_collision_rejected(self, tmp_path):
        """Two symbols that collapse to the same pool filename would silently
        share one cached PDF (PR #1085 review) — rejected at validation."""
        import yaml as _yaml
        e1 = _entry()
        e2 = _entry()
        e2["symbol"] = "FCCC/CP/2009/11+Add.1"  # same stem as e1 after safe_filename
        path = tmp_path / "seed.yaml"
        path.write_text(_yaml.safe_dump([e1, e2]))
        with pytest.raises(ValueError, match="stem"):
            ck.load_seed(str(path), "unfccc")
