"""Tests for #54: Split corpus_filter into extend mode and filter mode.

Tests verify:
- --extend mode: reads input, adds flag/protection columns, writes output with SAME row count
- --filter mode: reads extended artifact, applies policy, output rows <= input rows
- --works-input / --works-output CLI args accepted
- Row-count invariant: extend rows == input rows
- Row-count invariant: filter rows <= extend rows
- Backward-compat: --apply still works as combined extend+filter

CLI flag presence is checked via source inspection (no subprocess).
Extend/filter mode tests that run corpus_filter via subprocess are marked @integration.
"""

import argparse
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
import yaml

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
HARVEST_DIR = os.path.join(SCRIPTS_DIR, "harvest")
PYTHON = sys.executable
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
DVC_YAML = os.path.join(os.path.dirname(__file__), "..", "dvc.yaml")
FILTER_YAML = os.path.join(
    os.path.dirname(__file__), "..", "config", "corpus_filter.yaml")


def run_script(*args, cwd=None):
    """Run corpus_filter.py with args, return (returncode, stdout+stderr)."""
    result = subprocess.run(
        [PYTHON, os.path.join(HARVEST_DIR, "corpus_filter.py"), *args],
        capture_output=True, text=True, cwd=cwd or os.path.dirname(SCRIPTS_DIR)
    )
    return result.returncode, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# CLI argument presence (source inspection, no subprocess)
# ---------------------------------------------------------------------------

def _read_script(script_name):
    """Read script source text for flag inspection."""
    path = os.path.join(HARVEST_DIR, script_name)
    with open(path) as f:
        return f.read()


class TestCLIArgs:
    @pytest.fixture(autouse=True, scope="class")
    def _load_source(self, request):
        request.cls._source = _read_script("corpus_filter.py")

    def _has_flag(self, flag):
        return f'"{flag}"' in self._source or f"'{flag}'" in self._source

    def test_accepts_extend_flag(self):
        assert self._has_flag("--extend"), "corpus_filter.py must accept --extend"

    def test_accepts_filter_flag(self):
        assert self._has_flag("--filter"), "corpus_filter.py must accept --filter"

    def test_accepts_works_input(self):
        assert self._has_flag("--works-input"), "corpus_filter.py must accept --works-input"

    def test_accepts_works_output(self):
        assert self._has_flag("--works-output"), "corpus_filter.py must accept --works-output"

    def test_works_input_default_for_extend(self):
        """--extend mode default input should be enriched_works.csv."""
        assert "enriched_works.csv" in self._source, \
            "corpus_filter.py --works-input default should reference enriched_works.csv"

    def test_works_input_default_for_filter(self):
        """--filter mode default input should be extended_works.csv."""
        assert "extended_works.csv" in self._source, \
            "corpus_filter.py --works-input default should reference extended_works.csv"


# ---------------------------------------------------------------------------
# Extend mode: row-count invariant (subprocess integration tests)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestExtendMode:
    @pytest.fixture
    def enriched_csv(self, tmp_path):
        """Build a minimal enriched works CSV with 10 rows."""
        df = pd.DataFrame({
            "source_id": [f"s{i}" for i in range(10)],
            "doi": [f"10.1/{i}" if i % 2 == 0 else None for i in range(10)],
            "title": [f"Paper about climate finance {i}" for i in range(10)],
            "year": [2010 + (i % 15) for i in range(10)],
            "source": ["openalex"] * 10,
            "cited_by_count": [i * 10 for i in range(10)],
            "source_count": [1] * 10,
            "abstract": [f"Abstract about carbon tax and climate policy {i}" for i in range(10)],
            "type": ["article"] * 10,
            "language": ["en"] * 10,
            "first_author": [f"Author{i}" for i in range(10)],
            "from_openalex": [1] * 10,
            "from_semanticscholar": [0] * 10,
            "from_istex": [0] * 10,
            "from_bibcnrs": [0] * 10,
            "from_scispace": [0] * 10,
            "from_grey": [0] * 10,
            "from_teaching": [0] * 10,
        })
        path = tmp_path / "enriched_works.csv"
        df.to_csv(path, index=False)
        return path

    def test_extend_mode_row_count_invariant(self, tmp_path, enriched_csv):
        """--extend must write same number of rows as input (no filtering)."""
        input_df = pd.read_csv(enriched_csv)
        output_path = tmp_path / "extended_works.csv"

        rc, out = run_script(
            "--extend",
            "--works-input", str(enriched_csv),
            "--works-output", str(output_path),
            "--skip-llm", "--skip-citation-flag",
        )
        assert rc == 0, f"--extend failed:\n{out}"
        assert output_path.exists(), f"--extend did not produce {output_path}\n{out}"

        output_df = pd.read_csv(output_path)
        assert len(output_df) == len(input_df), (
            f"--extend changed row count: {len(input_df)} in → {len(output_df)} out. "
            f"Extend mode must not filter rows."
        )

    def test_extend_mode_adds_flag_columns(self, tmp_path, enriched_csv):
        """--extend output must include flag and protection columns."""
        output_path = tmp_path / "extended_works.csv"
        rc, out = run_script(
            "--extend",
            "--works-input", str(enriched_csv),
            "--works-output", str(output_path),
            "--skip-llm", "--skip-citation-flag",
        )
        assert rc == 0, f"--extend failed:\n{out}"
        assert output_path.exists()

        output_df = pd.read_csv(output_path)
        for col in ("protected", "protect_reason", "action"):
            assert col in output_df.columns, \
                f"--extend output missing column: {col}"

    def test_extend_mode_no_flags_column(self, tmp_path, enriched_csv):
        """--extend output must NOT contain a derived 'flags' column.

        The flags list is derived from boolean columns and should only
        appear as a serialized pipe-string in corpus_audit.csv.
        """
        output_path = tmp_path / "extended_works.csv"
        rc, out = run_script(
            "--extend",
            "--works-input", str(enriched_csv),
            "--works-output", str(output_path),
            "--skip-llm", "--skip-citation-flag",
        )
        assert rc == 0, f"--extend failed:\n{out}"
        output_df = pd.read_csv(output_path)
        assert "flags" not in output_df.columns, \
            "--extend output must not contain derived 'flags' column"

    def test_extend_mode_does_not_remove_rows(self, tmp_path, enriched_csv):
        """--extend output must contain all original source_id values."""
        input_df = pd.read_csv(enriched_csv)
        output_path = tmp_path / "extended_works.csv"
        rc, _ = run_script(
            "--extend",
            "--works-input", str(enriched_csv),
            "--works-output", str(output_path),
            "--skip-llm", "--skip-citation-flag",
        )
        assert rc == 0
        output_df = pd.read_csv(output_path)
        input_ids = set(input_df["source_id"])
        output_ids = set(output_df["source_id"])
        assert input_ids == output_ids, \
            f"--extend dropped source_ids: {input_ids - output_ids}"


# ---------------------------------------------------------------------------
# Filter mode: reduction behavior (subprocess integration tests)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestFilterMode:
    @pytest.fixture
    def extended_csv(self, tmp_path):
        """Build a minimal extended works CSV (has flag columns, some flagged)."""
        df = pd.DataFrame({
            "source_id": [f"s{i}" for i in range(10)],
            "doi": [f"10.1/{i}" for i in range(10)],
            "title": [f"Climate finance paper {i}" for i in range(10)],
            "year": [2010 + i for i in range(10)],
            "source": ["openalex"] * 10,
            "cited_by_count": [i * 5 for i in range(10)],
            "source_count": [1] * 10,
            "abstract": ["Some abstract about climate policy"] * 10,
            "type": ["article"] * 10,
            "language": ["en"] * 10,
            "first_author": [f"Author{i}" for i in range(10)],
            "from_openalex": [1] * 10,
            "from_semanticscholar": [0] * 10,
            "from_istex": [0] * 10,
            "from_bibcnrs": [0] * 10,
            "from_scispace": [0] * 10,
            "from_grey": [0] * 10,
            "from_teaching": [0] * 10,
            # Flag 3 rows as noise (boolean columns only, no derived 'flags')
            "missing_metadata": [True, True, True] + [False] * 7,
            "no_abstract_irrelevant": [False] * 10,
            "title_blacklist": [False] * 10,
            "protected": [False, False, False] + [False] * 7,
            "protect_reason": [""] * 10,
            "action": ["keep"] * 10,
        })
        path = tmp_path / "extended_works.csv"
        df.to_csv(path, index=False)
        return path

    def test_filter_mode_reduces_rows(self, tmp_path, extended_csv):
        """--filter must produce fewer rows when flagged rows exist."""
        input_df = pd.read_csv(extended_csv)
        output_path = tmp_path / "refined_works.csv"

        rc, out = run_script(
            "--filter",
            "--works-input", str(extended_csv),
            "--works-output", str(output_path),
        )
        assert rc == 0, f"--filter failed:\n{out}"
        assert output_path.exists(), f"--filter did not produce {output_path}\n{out}"

        output_df = pd.read_csv(output_path)
        assert len(output_df) < len(input_df), (
            f"--filter did not remove any rows: "
            f"{len(input_df)} in → {len(output_df)} out. "
            f"Expected < {len(input_df)} since 3 rows are flagged."
        )

    def test_filter_mode_rows_lte_extend(self, tmp_path, extended_csv):
        """--filter output row count <= --extend input row count."""
        input_df = pd.read_csv(extended_csv)
        refined_path = tmp_path / "refined_works.csv"
        rc, out = run_script(
            "--filter",
            "--works-input", str(extended_csv),
            "--works-output", str(refined_path),
        )
        assert rc == 0, f"--filter failed:\n{out}"
        assert refined_path.exists()
        output_df = pd.read_csv(refined_path)
        assert len(output_df) <= len(input_df), \
            f"filter output ({len(output_df)}) > extend input ({len(input_df)})"

    def test_filter_mode_produces_audit(self, tmp_path, extended_csv):
        """--filter must also produce corpus_audit.csv."""
        refined_path = tmp_path / "refined_works.csv"
        # Run with --audit-output to test configurable audit path
        rc, out = run_script(
            "--filter",
            "--works-input", str(extended_csv),
            "--works-output", str(refined_path),
        )
        assert rc == 0, f"--filter failed:\n{out}"
        # corpus_audit.csv should appear next to refined
        audit_path = tmp_path / "corpus_audit.csv"
        # Either in tmp_path or next to refined - check output for file path
        assert "audit" in out.lower() or audit_path.exists() or \
               any("audit" in f for f in os.listdir(tmp_path)), \
            f"--filter did not produce corpus_audit.csv. Output:\n{out}"


# ---------------------------------------------------------------------------
# Flag 6 must reflect THIS run, never the previous one (ticket 0314)
# ---------------------------------------------------------------------------


class TestFlag6NotCarriedOver:
    """The ``llm_irrelevant`` column round-trips through extended_works.csv.

    That is how the 2026-07-24 skip stayed silent: the column arrived already
    populated from the prior pass, so the presence-only apply gate was
    satisfied and the summary reported a count that no scoring in this run had
    produced. Seeding the column from this run's scoring makes the state
    honest — a run that scores nothing reports nothing.
    """

    def _run_flagging(self, df, monkeypatch, yields):
        sys.path.insert(0, SCRIPTS_DIR)
        sys.path.insert(0, HARVEST_DIR)
        import corpus_filter

        monkeypatch.setattr(
            corpus_filter, "flag_llm_irrelevant_streaming",
            lambda *a, **k: iter(yields),
        )
        monkeypatch.setattr(
            corpus_filter, "detect_near_duplicate_groups",
            lambda d: pd.Series("", index=d.index),
        )
        from filter_flags import _load_config

        args = argparse.Namespace(
            skip_llm=False, skip_citation_flag=True, cheap=False,
        )
        config = _load_config(
            os.path.join(FIXTURE_DIR, "corpus_filter_test.yaml")
        )
        flagged, _has_embeddings = corpus_filter.run_flagging(
            df, args, config, None, None, None, False
        )
        return flagged

    def test_stale_flag6_column_is_not_reported_as_this_runs_result(
        self, monkeypatch
    ):
        """Input carries llm_irrelevant=True; this run scores nothing."""
        df = pd.read_csv(os.path.join(FIXTURE_DIR, "filter_fixture.csv"))
        df["llm_irrelevant"] = True
        out = self._run_flagging(df, monkeypatch, yields=[])
        assert not out["llm_irrelevant"].fillna(False).any(), (
            "stale Flag 6 values from a previous pass survived a run that "
            "scored nothing"
        )


# ---------------------------------------------------------------------------
# Flag 5 joins embeddings by work key, never by row position (ticket 0336)
# ---------------------------------------------------------------------------


def _import_corpus_filter():
    sys.path.insert(0, SCRIPTS_DIR)
    sys.path.insert(0, HARVEST_DIR)
    import corpus_filter

    return corpus_filter


def _works_frame(n=4, first_year=2010):
    """Works frame whose rows all qualify for the Flag 5 subset."""
    return pd.DataFrame({
        "doi": [f"10.1/work{i}" for i in range(n)],
        "source_id": [f"W{i:04d}" for i in range(n)],
        "title": [f"Work {i}" for i in range(n)],
        "year": [first_year + i for i in range(n)],
        "abstract": [f"Abstract number {i} " + "x" * 60 for i in range(n)],
    })


def _write_npz(tmp_path, keys, dim=8, name="embeddings.npz"):
    """Embeddings cache keyed like enrich_embeddings.py writes it.

    Vector i is filled with the constant i so a joined row can be traced back
    to the key it came from.
    """
    vectors = np.stack([
        np.full(dim, float(i), dtype=np.float32) for i in range(len(keys))
    ])
    path = tmp_path / name
    np.savez_compressed(
        path,
        vectors=vectors,
        keys=np.array(list(keys), dtype=object),
        model=np.array("test-model"),
        text_fields=np.array("title+abstract+keywords"),
    )
    return str(path), vectors


class TestFlag5EmbeddingKeyJoin:
    """Flag 5 died silently because two independently-filtered frames were
    assumed to align by row position (ticket 0336).

    ``enrich_embeddings.py`` embeds every titled work in the periodization
    window; ``load_embeddings`` rebuilds a narrower abstract-bearing subset.
    The row sets diverged (38,736 vectors vs 33,057 rows on the 2026-07-27
    corpus), the length check failed, and the flag was skipped on every run
    behind a ``log.warning``. The vectors carry a ``keys`` array, so the join
    is available — and a join cannot go out of alignment.
    """

    def test_evaluates_when_row_sets_differ(self, tmp_path):
        """More vectors than subset rows: the flag must still evaluate."""
        cf = _import_corpus_filter()
        df = _works_frame(n=3)
        # Embed the 3 works plus 4 works that are not in this frame, in an
        # order that does not match df — exactly the production condition.
        keys = ["10.1/other0", "10.1/work2", "10.1/other1",
                "10.1/work0", "10.1/other2", "10.1/work1", "10.1/other3"]
        path, vectors = _write_npz(tmp_path, keys)

        embeddings, emb_df, has_embeddings = cf.load_embeddings(
            df, embeddings_path=path)

        assert has_embeddings, (
            "Flag 5 was skipped although every work in the frame has an "
            "embedding — the row sets merely differ in size"
        )
        assert len(embeddings) == len(emb_df) == 3
        # Each row must carry ITS OWN vector, not the one at its position.
        for i, key in enumerate(emb_df["doi"]):
            expected = vectors[keys.index(key)]
            assert np.array_equal(embeddings[i], expected), (
                f"row {i} ({key}) got the wrong vector — the join fell back "
                "to positional alignment"
            )

    def test_partial_coverage_above_the_floor_keeps_the_covered_rows(self, tmp_path):
        """Works without a vector are dropped, the rest still evaluate."""
        cf = _import_corpus_filter()
        df = _works_frame(n=4)
        path, _ = _write_npz(tmp_path, ["10.1/work0", "10.1/work3"])

        embeddings, emb_df, has_embeddings = cf.load_embeddings(
            df, embeddings_path=path, min_coverage=0.4)

        assert has_embeddings
        assert len(embeddings) == len(emb_df) == 2
        assert set(emb_df["doi"]) == {"10.1/work0", "10.1/work3"}

    def test_empty_key_in_the_cache_is_not_handed_out(self, tmp_path):
        """An empty key identifies nothing and would collide two works onto one
        vector. It must not match anybody."""
        cf = _import_corpus_filter()
        df = _works_frame(n=2)
        df["doi"] = ""
        df["source_id"] = ""
        df["title"] = ""
        path, _ = _write_npz(tmp_path, ["", "10.1/unrelated"])

        with pytest.raises(RuntimeError, match="(?i)coverage|no work in common"):
            cf.load_embeddings(df, embeddings_path=path)

    def test_falls_back_to_source_id_when_doi_is_absent(self, tmp_path):
        """work_key() keys on source_id for DOI-less works; so must the join."""
        cf = _import_corpus_filter()
        df = _works_frame(n=2)
        df.loc[0, "doi"] = None
        path, _ = _write_npz(tmp_path, ["W0000", "10.1/work1"])

        embeddings, emb_df, has_embeddings = cf.load_embeddings(
            df, embeddings_path=path)

        assert has_embeddings
        assert len(emb_df) == 2, "the DOI-less work lost its embedding"

    def test_year_window_still_bounds_the_subset(self, tmp_path):
        """Out-of-window works stay out even when they have a vector."""
        cf = _import_corpus_filter()
        df = _works_frame(n=2)
        df.loc[1, "year"] = 1789
        path, _ = _write_npz(tmp_path, ["10.1/work0", "10.1/work1"])

        _embeddings, emb_df, has_embeddings = cf.load_embeddings(
            df, embeddings_path=path)

        assert has_embeddings
        assert list(emb_df["doi"]) == ["10.1/work0"]


class TestFlag5NeverSilentlyDead:
    """A ``log.warning`` swallowing a dead flag is what hid this for months.

    ``load_embeddings`` may report "no embeddings" only for a genuine absence
    (``--cheap``, no cache file). When the cache exists and holds vectors, it
    must either return them or fail loudly.
    """

    def test_zero_key_overlap_raises_instead_of_reporting_no_embeddings(
        self, tmp_path
    ):
        cf = _import_corpus_filter()
        df = _works_frame(n=3)
        path, _ = _write_npz(tmp_path, ["10.1/nothing-in-common"])

        with pytest.raises(RuntimeError, match="(?i)no work in common|overlap"):
            cf.load_embeddings(df, embeddings_path=path)

    def test_keyless_cache_raises_instead_of_reporting_no_embeddings(
        self, tmp_path
    ):
        """A legacy cache without `keys` cannot be joined — say so, loudly."""
        cf = _import_corpus_filter()
        df = _works_frame(n=3)
        path = tmp_path / "keyless.npz"
        np.savez_compressed(path, vectors=np.zeros((5, 8), dtype=np.float32))

        with pytest.raises(RuntimeError, match="keys"):
            cf.load_embeddings(df, embeddings_path=str(path))

    def test_desynced_keys_and_vectors_raise_rather_than_IndexError(
        self, tmp_path
    ):
        """keys and vectors are positional within the cache file.

        Unequal lengths used to surface as a bare IndexError out of numpy,
        bypassing the operator-facing message every other path here gives.
        """
        cf = _import_corpus_filter()
        df = _works_frame(n=2)
        path = tmp_path / "desynced.npz"
        np.savez_compressed(
            path,
            vectors=np.zeros((1, 8), dtype=np.float32),
            keys=np.array(["10.1/work0", "10.1/work1"], dtype=object),
        )

        with pytest.raises(RuntimeError, match="(?i)keys.*vectors|inconsistent"):
            cf.load_embeddings(df, embeddings_path=str(path))

    def test_emb_df_keeps_the_works_frame_index(self, tmp_path):
        """The returned slice must carry df's index, not a fresh range.

        flag_semantic_outlier assigns distances by index; a reset index would
        silently put every distance on the wrong row.
        """
        cf = _import_corpus_filter()
        df = _works_frame(n=4)
        df.loc[1, "abstract"] = None          # drop row 1 from the subset
        path, _ = _write_npz(
            tmp_path, ["10.1/work0", "10.1/work2", "10.1/work3"])

        _embeddings, emb_df, has_embeddings = cf.load_embeddings(
            df, embeddings_path=path)

        assert has_embeddings
        assert list(emb_df.index) == [0, 2, 3]

    def test_coverage_below_the_floor_raises(self, tmp_path):
        """A 99%-dead flag is still a dead flag.

        Zero overlap already raised, but one vector out of a thousand
        candidates used to warn and proceed — scoring a rump of the corpus
        against a centroid built from that same rump (review round 2).
        """
        cf = _import_corpus_filter()
        df = _works_frame(n=10)
        path, _ = _write_npz(tmp_path, ["10.1/work0"])

        with pytest.raises(RuntimeError, match="(?i)coverage"):
            cf.load_embeddings(df, embeddings_path=path, min_coverage=0.9)

    def test_coverage_floor_comes_from_config_by_default(self):
        """The floor is a research parameter, so it lives in the config."""
        import yaml

        cfg_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "corpus_filter.yaml")
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
        floor = cfg["semantic_outlier"]["min_coverage"]
        assert 0 < floor <= 1, "min_coverage must be a fraction"

    def test_unusable_year_column_raises_instead_of_emptying_the_subset(
        self, tmp_path
    ):
        """Abstract-bearing works whose years all coerce to NaN.

        The subset empties, which used to read as "nothing to score" — the same
        silence by a different route.
        """
        cf = _import_corpus_filter()
        df = _works_frame(n=3)
        df["year"] = "n/a"
        path, _ = _write_npz(tmp_path, ["10.1/work0", "10.1/work1"])

        with pytest.raises(RuntimeError, match="(?i)year"):
            cf.load_embeddings(df, embeddings_path=path)

    def test_missing_cache_is_still_a_legitimate_skip(self, tmp_path):
        cf = _import_corpus_filter()
        df = _works_frame(n=3)
        result = cf.load_embeddings(
            df, embeddings_path=str(tmp_path / "absent.npz"))
        assert result == (None, None, False)

    def test_cheap_mode_is_still_a_legitimate_skip(self, tmp_path):
        cf = _import_corpus_filter()
        df = _works_frame(n=3)
        path, _ = _write_npz(tmp_path, ["10.1/work0"])
        result = cf.load_embeddings(df, cheap=True, embeddings_path=path)
        assert result == (None, None, False)

    def test_explicit_skip_is_a_legitimate_skip(self, tmp_path):
        """The escape hatch: turning Flag 5 off has to be asked for.

        Without it, an unusable cache would leave an operator no way to filter
        at all — with it, the only quiet five-flag run is a requested one.
        """
        cf = _import_corpus_filter()
        df = _works_frame(n=3)
        path = tmp_path / "keyless.npz"
        np.savez_compressed(path, vectors=np.zeros((5, 8), dtype=np.float32))
        result = cf.load_embeddings(df, skip=True, embeddings_path=str(path))
        assert result == (None, None, False)

    def test_abstractless_corpus_is_a_legitimate_skip(self, tmp_path):
        """No abstract anywhere: Flag 5 genuinely has nothing to score."""
        cf = _import_corpus_filter()
        df = _works_frame(n=3)
        df["abstract"] = None
        path, _ = _write_npz(tmp_path, ["10.1/work0"])
        result = cf.load_embeddings(df, embeddings_path=path)
        assert result == (None, None, False)


class TestSkipSemanticFlagCLI:
    """`--skip-semantic-flag` is the only sanctioned way to run five flags."""

    def test_flag_is_declared(self):
        with open(os.path.join(HARVEST_DIR, "corpus_filter.py")) as f:
            src = f.read()
        assert '"--skip-semantic-flag"' in src

    def test_cheap_mode_implies_it(self):
        with open(os.path.join(HARVEST_DIR, "corpus_filter.py")) as f:
            src = f.read()
        assert "args.skip_semantic_flag = True" in src, (
            "--cheap must imply --skip-semantic-flag, or a cheap run reports "
            "'no embeddings cache' for a cache it never looked at"
        )

    def test_flag5_failure_is_not_swallowed_by_run_flagging(self):
        """run_flagging must not catch the semantic flag's own exception.

        The `except ValueError: log.warning` around Flag 5 was a second silent
        path, independent of the loader's.
        """
        import re

        with open(os.path.join(HARVEST_DIR, "corpus_filter.py")) as f:
            src = f.read()
        body = src[src.index("def run_flagging"):src.index("def main(")]
        flag5 = body[body.index("if has_embeddings:"):body.index("skip_llm =")]
        code = "\n".join(line for line in flag5.splitlines()
                         if not line.lstrip().startswith("#"))
        assert not re.search(r"except\s+\w*Error", code), (
            "Flag 5's call site swallows an exception again"
        )


class TestFlag5DiagnosticActivation:
    """Flag 5 is inert by config, not by a CLI flag (ticket 0361).

    It used to be held off by `--skip-semantic-flag` in `dvc.yaml`, which also
    switched the *computation* off: no distance column reached
    `extended_works.csv`. Diagnostic mode keeps the computation and drops only
    the removals, so the CLI flag has to go — leaving both would be two
    switches for one decision, and the CLI one wins silently.
    """

    def _semantic_block(self):
        with open(FILTER_YAML) as f:
            return yaml.safe_load(f)["semantic_outlier"]

    def test_config_declares_diagnostic_mode(self):
        assert self._semantic_block().get("mode") == "diagnostic", (
            "config/corpus_filter.yaml must state semantic_outlier.mode; "
            "activating Flag 5 as a filter needs author sign-off"
        )

    def test_config_declares_the_per_language_centroid(self):
        assert self._semantic_block().get("centroid") == "per_language", (
            "a global centroid on a 91.6%-English corpus measures 'not in "
            "English' as much as 'off topic'"
        )

    def test_config_carries_no_unused_sigma(self):
        """An unused threshold in config is a landmine.

        `sigma: 2` was calibrated on a smaller corpus under a different
        embedding model and was never validated against anything it produced.
        Diagnostic mode reads no sigma, so leaving the key would invite the
        next reader to trust it.
        """
        assert "sigma" not in self._semantic_block(), (
            "semantic_outlier.sigma is unread in diagnostic mode — remove it "
            "rather than leave an uncalibrated threshold in config"
        )

    def test_extend_no_longer_skips_the_semantic_flag(self):
        with open(DVC_YAML) as f:
            dvc = yaml.safe_load(f)
        cmd = dvc["stages"]["extend"]["cmd"]
        assert "--skip-semantic-flag" not in cmd, (
            "the extend stage still skips Flag 5 on the command line, so the "
            "diagnostic distance never reaches extended_works.csv"
        )


class TestExtendDeclaresEmbeddingsDep:
    """`extend` consumes embeddings.npz, so DVC must know it (ticket 0336).

    Without the dep, DVC never re-runs `extend` when embeddings change, so a
    Flag 5 result can go stale — or stay dead — without the DAG noticing.
    """

    def test_extend_stage_depends_on_embeddings_npz(self):
        with open(DVC_YAML) as f:
            dvc = yaml.safe_load(f)
        deps = dvc["stages"]["extend"]["deps"]
        assert "data/catalogs/embeddings.npz" in deps, (
            "extend reads embeddings.npz for Flag 5 but does not declare it "
            "as a DVC dependency"
        )
