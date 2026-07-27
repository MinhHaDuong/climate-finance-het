"""Tests for #423: Language enrichment — OpenAlex backfill + local detection.

Verifies:
- normalize_lang converts ISO 639-3, full names, and regional codes to 2-letter ISO 639-1
- detect_language returns 2-letter codes for known texts
- is_valid_iso639_1 rejects nonsensical codes
- Cache round-trip (load_cache / save_cache) preserves data
- OpenAlex batch query builds correct filter strings
- Pipeline integration: enrich_language stage exists in dvc.yaml
"""

import os
import sys
import tempfile

import pandas as pd
import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
HARVEST_DIR = os.path.join(SCRIPTS_DIR, "harvest")
sys.path.insert(0, HARVEST_DIR)


# ---------- language normalization ----------

class TestNormalizeLang:
    """normalize_lang must map various code formats to 2-letter ISO 639-1."""

    def test_iso639_3_to_2(self):
        from enrich_language import normalize_lang
        assert normalize_lang("eng") == "en"
        assert normalize_lang("fra") == "fr"
        assert normalize_lang("deu") == "de"

    def test_already_two_letter(self):
        from enrich_language import normalize_lang
        assert normalize_lang("en") == "en"
        assert normalize_lang("fr") == "fr"

    def test_full_name(self):
        from enrich_language import normalize_lang
        assert normalize_lang("english") == "en"
        assert normalize_lang("french") == "fr"

    def test_regional_suffix_stripped(self):
        from enrich_language import normalize_lang
        assert normalize_lang("en_US") == "en"
        assert normalize_lang("en_gb") == "en"

    def test_null_returns_none(self):
        from enrich_language import normalize_lang
        assert normalize_lang(None) is None
        assert normalize_lang("") is None
        assert normalize_lang("nan") is None

    def test_unknown_returns_none(self):
        from enrich_language import normalize_lang
        assert normalize_lang("und") is None
        assert normalize_lang("unknown") is None

    def test_unrecognized_string_returns_none(self):
        """Unknown strings must return None, not a truncated guess."""
        from enrich_language import normalize_lang
        assert normalize_lang("basque") is None  # not "ba" (Bashkir)
        assert normalize_lang("xyzzy") is None

    def test_iso639_3_miscellaneous_returns_none(self):
        """ISO 639-3 special codes must not be truncated to valid 2-letter codes."""
        from enrich_language import normalize_lang
        assert normalize_lang("mis") is None  # miscellaneous, not "mi" (Māori)
        assert normalize_lang("mul") is None  # multilingual
        assert normalize_lang("zxx") is None  # no linguistic content


# ---------- ISO 639-1 validation ----------

class TestIsValidIso639_1:
    """is_valid_iso639_1 must accept real 2-letter language codes and reject nonsense."""

    def test_valid_codes(self):
        from enrich_language import is_valid_iso639_1
        for code in ("en", "fr", "de", "es", "zh", "ar", "ja", "pt"):
            assert is_valid_iso639_1(code), f"{code} should be valid"

    def test_invalid_codes(self):
        from enrich_language import is_valid_iso639_1
        for code in ("xx", "zz", "qq", "a1"):
            assert not is_valid_iso639_1(code), f"{code} should be invalid"

    def test_none_and_empty(self):
        from enrich_language import is_valid_iso639_1
        assert not is_valid_iso639_1(None)
        assert not is_valid_iso639_1("")


# ---------- local language detection ----------

class TestDetectLanguage:
    """detect_language uses langdetect on text and returns a 2-letter code."""

    def test_english(self):
        from enrich_language import detect_language
        text = ("Climate finance refers to local, national, or transnational financing "
                "that seeks to support mitigation and adaptation actions.")
        assert detect_language(text) == "en"

    def test_french(self):
        from enrich_language import detect_language
        text = ("La finance climatique concerne le financement des actions de lutte "
                "contre le changement climatique au niveau local et international.")
        assert detect_language(text) == "fr"

    def test_short_text_returns_none(self):
        from enrich_language import detect_language
        assert detect_language("Hi") is None
        assert detect_language("") is None
        assert detect_language(None) is None


# ---------- cache round-trip ----------

class TestCacheRoundTrip:
    """load_cache / save_cache must preserve key-value data."""

    def test_round_trip(self):
        from unittest.mock import patch

        from enrich_language import load_cache, save_cache
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("enrich_language.CACHE_DIR", tmpdir):
                data = {"10.1234/abc": "en", "10.5678/def": "fr"}
                save_cache("test_lang", data)
                loaded = load_cache("test_lang")
                assert loaded == data

    def test_empty_cache(self):
        from unittest.mock import patch

        from enrich_language import load_cache
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("enrich_language.CACHE_DIR", tmpdir):
                loaded = load_cache("test_lang")
                assert loaded == {}


# ---------- OpenAlex batch query building ----------

class TestBuildOABatch:
    """build_oa_doi_filter must create pipe-separated DOI filter strings."""

    def test_pipe_separated(self):
        from enrich_language import build_oa_doi_filter
        dois = ["10.1234/a", "10.5678/b", "10.9999/c"]
        result = build_oa_doi_filter(dois)
        assert result == "10.1234/a|10.5678/b|10.9999/c"

    def test_empty_list(self):
        from enrich_language import build_oa_doi_filter
        assert build_oa_doi_filter([]) == ""


# ---------- pass1 integration ----------

class TestPass1ApplyCache:
    """pass1_apply_cache writes language values from cache into the DataFrame."""

    def test_fills_null_language(self):
        from enrich_language import pass1_apply_cache
        df = pd.DataFrame({
            "doi": ["10.1234/a", "10.5678/b"],
            "language": [None, "en"],
        })
        cache = {"10.1234/a": "fr"}
        filled = pass1_apply_cache(df, cache)
        assert filled == 1
        assert df.loc[0, "language"] == "fr"
        # Already-set language not overwritten
        assert df.loc[1, "language"] == "en"

    def test_fills_via_source_id(self):
        """Falls back to source_id when DOI is missing."""
        from enrich_language import pass1_apply_cache
        df = pd.DataFrame({
            "doi": [None],
            "source_id": ["W12345"],
            "language": [None],
        })
        cache = {"W12345": "de"}
        filled = pass1_apply_cache(df, cache)
        assert filled == 1
        assert df.loc[0, "language"] == "de"

    def test_rejects_invalid_cache_value(self):
        """Cache values that are not valid ISO 639-1 codes should be skipped."""
        from enrich_language import pass1_apply_cache
        df = pd.DataFrame({
            "doi": ["10.1234/a"],
            "language": [None],
        })
        cache = {"10.1234/a": "xyzzy"}  # not a valid ISO code
        filled = pass1_apply_cache(df, cache)
        assert filled == 0
        assert pd.isna(df.loc[0, "language"])


# ---------- pass2 integration ----------

class TestPass2LocalDetect:
    """pass2_local_detect fills remaining nulls using langdetect."""

    def test_fills_from_abstract(self):
        from enrich_language import pass2_local_detect
        df = pd.DataFrame({
            "language": [None],
            "title": ["Climate Finance"],
            "abstract": ["Climate finance refers to local, national, or transnational "
                         "financing that seeks to support mitigation and adaptation "
                         "actions addressing climate change."],
        })
        filled = pass2_local_detect(df)
        assert filled == 1
        assert df.loc[0, "language"] == "en"

    def test_skips_already_filled(self):
        from enrich_language import pass2_local_detect
        df = pd.DataFrame({
            "language": ["fr"],
            "title": ["Some English title here about climate"],
            "abstract": ["This is an English abstract about climate change."],
        })
        filled = pass2_local_detect(df)
        assert filled == 0
        assert df.loc[0, "language"] == "fr"

    def test_replaces_invalid_code(self):
        """pass2 should replace nonsensical language codes with detected values."""
        from enrich_language import pass2_local_detect
        df = pd.DataFrame({
            "language": ["xx"],  # invalid ISO 639-1 code
            "title": ["Climate Finance"],
            "abstract": ["Climate finance refers to local, national, or transnational "
                         "financing that seeks to support mitigation and adaptation "
                         "actions addressing climate change."],
        })
        filled = pass2_local_detect(df)
        assert filled == 1
        assert df.loc[0, "language"] == "en"

    def test_uses_title_when_abstract_short(self):
        """When abstract is too short, detection falls back to title."""
        from enrich_language import pass2_local_detect
        df = pd.DataFrame({
            "language": [None],
            "title": ["Climate finance refers to local national or transnational financing"],
            "abstract": ["Short"],
        })
        filled = pass2_local_detect(df)
        assert filled == 1
        assert df.loc[0, "language"] == "en"


# ---------- pass2 cache persistence (ticket 0297) ----------

class TestPass2Persistence:
    """pass2 detections must survive the process.

    The #428 refactor made enrich_language cache-only: enrich_join applies
    the caches to the monolith. Pass 1 saved language_resolved.csv, but
    pass 2's langdetect results were only written to the in-memory frame
    and discarded on exit — so 4.1% of the corpus stayed null (ticket 0297).
    """

    def test_records_detections_in_cache(self):
        """A detection is recorded in the caller's cache dict."""
        from enrich_language import pass2_local_detect
        df = pd.DataFrame({
            "doi": ["10.1234/a"],
            "source_id": ["W001"],
            "language": [None],
            "title": ["Climate Finance"],
            "abstract": ["Climate finance refers to local, national, or transnational "
                         "financing that seeks to support mitigation and adaptation "
                         "actions addressing climate change."],
        })
        cache = {}
        filled = pass2_local_detect(df, cache)
        assert filled == 1
        assert cache == {"10.1234/a": "en"}

    def test_cache_keyed_by_source_id_without_doi(self):
        """Records without a DOI are keyed by source_id, as enrich_join looks up."""
        from enrich_language import pass2_local_detect
        df = pd.DataFrame({
            "doi": [None],
            "source_id": ["W002"],
            "language": [None],
            "title": ["Climate finance refers to local national or transnational financing"],
            "abstract": [None],
        })
        cache = {}
        pass2_local_detect(df, cache)
        assert cache == {"W002": "en"}

    def test_cache_optional(self):
        """Existing callers that pass no cache still work."""
        from enrich_language import pass2_local_detect
        df = pd.DataFrame({
            "language": [None],
            "title": ["Climate Finance"],
            "abstract": ["Climate finance refers to local, national, or transnational "
                         "financing that seeks to support mitigation and adaptation."],
        })
        assert pass2_local_detect(df) == 1

    def test_main_saves_detected_cache(self):
        """main() persists pass-2 results to the language_detected cache."""
        path = os.path.join(HARVEST_DIR, "enrich_language.py")
        with open(path) as f:
            source = f.read()
        assert 'save_cache("language_detected"' in source, (
            "pass-2 detections are computed but never persisted — "
            "enrich_join cannot apply them (ticket 0297)"
        )


# ---------- DVC pipeline integration ----------

class TestDVCStage:
    """enrich_language.py is an independent DVC stage (#428).

    Each enrichment writes to its own cache; join_enrichments.py
    assembles enriched_works.csv from all caches.
    """

    @pytest.fixture(autouse=True)
    def _load_dvc(self):
        import yaml
        dvc_path = os.path.join(os.path.dirname(__file__), "..", "dvc.yaml")
        with open(dvc_path) as f:
            self.dvc = yaml.safe_load(f)

    def test_standalone_enrich_language_stage(self):
        """Language enrichment is its own DVC stage (#428)."""
        assert "enrich_language" in self.dvc["stages"]

    def test_stage_deps_include_script(self):
        deps = self.dvc["stages"]["enrich_language"]["deps"]
        assert "scripts/harvest/enrich_language.py" in deps

    def test_stage_deps_include_unified(self):
        deps = self.dvc["stages"]["enrich_language"]["deps"]
        assert any("unified_works.csv" in d for d in deps)

    def test_stage_produces_stamp(self):
        """enrich_language writes a stamp file for DVC ordering."""
        outs = self.dvc["stages"]["enrich_language"]["outs"]
        stamp_paths = []
        for o in outs:
            if isinstance(o, dict):
                stamp_paths.extend(o.keys())
            else:
                stamp_paths.append(o)
        assert any(".language.stamp" in p for p in stamp_paths)

    def test_join_stage_depends_on_stamp(self):
        """join_enrichments depends on enrich_language stamp."""
        deps = self.dvc["stages"]["join_enrichments"]["deps"]
        assert any(".language.stamp" in str(d) for d in deps)

    def test_join_stage_produces_enriched(self):
        """join_enrichments stage produces enriched_works.csv."""
        outs = self.dvc["stages"]["join_enrichments"]["outs"]
        assert any("enriched_works.csv" in str(o) for o in outs)


# ---------- script structure ----------

class TestScriptStructure:
    """enrich_language.py follows project conventions."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        path = os.path.join(HARVEST_DIR, "enrich_language.py")
        with open(path) as f:
            self.source = f.read()

    def test_uses_get_logger(self):
        assert "get_logger" in self.source

    def test_has_argparse(self):
        assert "argparse" in self.source
        assert "ArgumentParser" in self.source

    def test_no_bare_print(self):
        """No bare print() calls — use log.info() instead."""
        import ast
        tree = ast.parse(self.source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "print":
                    pytest.fail("Found bare print() call — use log.info() instead")

    def test_imports_retry_get(self):
        assert "retry_get" in self.source

    def test_uses_enrich_cache(self):
        assert "enrich_cache" in self.source
