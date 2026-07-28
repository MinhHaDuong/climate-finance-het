"""Genealogy artifacts are byte-reproducible without pinning PYTHONHASHSEED (0591).

The genealogy chain builds its citation edge list and its backbone paper list as
Python ``set`` objects, then iterates them to draw. Set iteration order over
strings follows the interpreter's hash seed, so two runs of the same code on the
same inputs produced different bytes unless ``PYTHONHASHSEED`` happened to be
pinned — which the Makefile does globally, hiding the defect from every
``make``-driven run and surfacing it only in a refactor byte-compare
(ticket 0571, PR #1269).

These tests deliberately run each producer under *two different* hash seeds.
Pinning the seed to a single value, as ``tests/test_determinism.py`` does, would
make them pass against the defect.
"""

import filecmp
import os
import subprocess
import sys

import pytest
from _source_roots import source_root_env

SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)

# Two arbitrary, different seeds. Any pair works; fixed values keep failures
# reproducible.
SEED_A = "1"
SEED_B = "12345"

N_PAPERS = 60


def _dois():
    return [f"10.1000/paper{i:03d}" for i in range(N_PAPERS)]


def _citation_rows():
    """Deterministic edge list dense enough that set order is observable.

    Every paper cites a handful of lower-numbered ones, which keeps the graph a
    DAG in publication order and produces both within-lineage and cross-lineage
    edges under the lineage assignment below.
    """
    dois = _dois()
    rows = []
    for i, source in enumerate(dois):
        for step in (1, 3, 7, 11):
            j = i - step
            if j >= 0:
                rows.append((source, dois[j], 1990 + j % 30))
    return rows


def _write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(",".join(header) + "\n")
        for row in rows:
            fh.write(",".join(str(c) for c in row) + "\n")


def _write_citations(data_dir):
    _write_csv(
        os.path.join(data_dir, "catalogs", "refined_citations.csv"),
        ["source_doi", "ref_doi", "ref_year", "ref_title", "ref_first_author"],
        [(s, r, y, f"Ref title {r}", f"Author{r[-3:]}") for s, r, y in _citation_rows()],
    )


def _write_lineages(path):
    """A tab_lineages.csv covering all three bands with position jitter."""
    rows = []
    for i, doi in enumerate(_dois()):
        lineage = i % 3
        year = 1990 + (i % 30)
        x = (year - 1990) / 29
        y = (lineage + 0.5) / 3 + 0.02 * ((i % 5) - 2)
        rows.append(
            (
                doi,
                lineage,
                f"Band{lineage}",
                False,
                f"Author{i:03d}",
                year,
                # Deliberate ties in cited_by_count: a tie-break that falls
                # through to set order is exactly the defect under test.
                100 + (i % 4) * 50,
                f"Title {i:03d}",
                round(x, 6),
                round(y, 6),
            )
        )
    _write_csv(
        path,
        ["doi", "lineage", "lineage_name", "peripheral", "first_author",
         "year", "cited_by_count", "title", "x", "y"],
        rows,
    )


def _write_model_inputs(data_dir):
    """refined_works + semantic_clusters + tab_pole_papers for analyze_genealogy."""
    abstract = "Synthetic abstract padded well past the fifty character floor."
    _write_csv(
        os.path.join(data_dir, "catalogs", "refined_works.csv"),
        ["doi", "title", "year", "cited_by_count", "abstract", "first_author"],
        [
            (doi, f"Title {i:03d}", 1990 + (i % 30), 100 + (i % 4) * 50,
             abstract, f"Author{i:03d}")
            for i, doi in enumerate(_dois())
        ],
    )
    derived = os.path.join(data_dir, "derived", "tables")
    _write_csv(
        os.path.join(derived, "semantic_clusters.csv"),
        ["doi", "semantic_cluster"],
        [(doi, i % 4) for i, doi in enumerate(_dois())],
    )
    _write_csv(
        os.path.join(derived, "tab_pole_papers.csv"),
        ["doi", "axis_score"],
        [(doi, round(-1.0 + 2.0 * (i % 7) / 6, 4)) for i, doi in enumerate(_dois())],
    )


def _run(script, args, data_dir, seed):
    env = source_root_env(
        {
            **os.environ,
            "CLIMATE_FINANCE_DATA": data_dir,
            "PYTHONHASHSEED": seed,
            "SOURCE_DATE_EPOCH": "0",
            "MPLBACKEND": "Agg",
        }
    )
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, script), *args],
        capture_output=True, text=True, env=env, timeout=300,
    )
    assert result.returncode == 0, (
        f"{script} failed under PYTHONHASHSEED={seed}:\n{result.stderr}"
    )


def _run_under_both_seeds(script, out_name, extra_args, tmp_path, data_dir):
    """Run ``script`` once per seed into its own dir; return the two outputs."""
    produced = []
    for seed in (SEED_A, SEED_B):
        out_dir = tmp_path / f"seed{seed}"
        out_dir.mkdir()
        out_path = out_dir / out_name
        _run(script, ["--output", str(out_path), *extra_args], data_dir, seed)
        assert out_path.exists(), f"{script} wrote no {out_name}"
        produced.append(out_path)
    return produced


@pytest.mark.integration
class TestGenealogyHashSeedIndependence:
    """Same code, same inputs, different hash seed → identical bytes."""

    @pytest.fixture
    def fixture_root(self, tmp_path):
        data_dir = tmp_path / "data"
        _write_citations(str(data_dir))
        _write_model_inputs(str(data_dir))
        lineages = tmp_path / "tab_lineages.csv"
        _write_lineages(str(lineages))
        return str(data_dir), str(lineages)

    def test_html_renderer(self, tmp_path, fixture_root):
        data_dir, lineages = fixture_root
        p1, p2 = _run_under_both_seeds(
            "figures/plot_genealogy_html.py", "fig_genealogy.html",
            ["--lineages", lineages], tmp_path, data_dir,
        )
        assert filecmp.cmp(str(p1), str(p2), shallow=False), (
            "fig_genealogy.html differs between hash seeds — a set is being "
            "iterated into the output"
        )

    def test_png_renderer(self, tmp_path, fixture_root):
        data_dir, lineages = fixture_root
        p1, p2 = _run_under_both_seeds(
            "figures/plot_genealogy.py", "fig_genealogy.png",
            ["--lineages", lineages], tmp_path, data_dir,
        )
        assert filecmp.cmp(str(p1), str(p2), shallow=False), (
            "fig_genealogy.png differs between hash seeds — a set is being "
            "iterated into the output"
        )

    def test_lineage_model(self, tmp_path, fixture_root):
        """The upstream model table is the renderers' input — pin it too."""
        data_dir, _ = fixture_root
        p1, p2 = _run_under_both_seeds(
            "analysis/analyze_genealogy.py", "tab_lineages.csv",
            [], tmp_path, data_dir,
        )
        assert filecmp.cmp(str(p1), str(p2), shallow=False), (
            "tab_lineages.csv differs between hash seeds — layout jitter or row "
            "order is following set iteration order"
        )
