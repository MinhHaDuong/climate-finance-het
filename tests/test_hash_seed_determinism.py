"""Phase-2 artifacts are byte-reproducible without pinning PYTHONHASHSEED (0591).

Set iteration order over strings follows the interpreter's hash seed. Where a
producer walks a set into its output — the genealogy chain's citation edges and
backbone paper list, the venue table's journal-name union — two runs of the same
code on the same inputs produced different bytes unless ``PYTHONHASHSEED``
happened to be pinned. The Makefile pins it globally (``export PYTHONHASHSEED
:= 0``), which is why every ``make``-driven run looked deterministic and the
defect surfaced only in ticket 0571's refactor byte-compare, where it read as a
spurious regression.

These tests deliberately run each producer under *two different* hash seeds.
Pinning the seed to a single value, as ``tests/test_determinism.py`` does, would
make them pass against the defect.

Not every sweep hit earns a test here. The two `plot_fig_traditions*` renderers
carry the same defect but need a Louvain partition over a real citation graph to
reach the tied labels, which no synthetic fixture reproduces cheaply; they are
fixed by inspection and left uncovered.
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


@pytest.mark.integration
class TestVenueTableHashSeedIndependence:
    """The venue table walks a set union of journal names (0591 sweep).

    Covered here rather than in its own module because it is the same defect
    class on the same harness. It earns a test where the two traditions figures
    do not: `tab_venues.md` is git-tracked and included by the Œconomia
    manuscript, so a hash-seed flip changes which journals a published table
    names.
    """

    @pytest.fixture
    def venue_inputs(self, tmp_path):
        """Journals engineered so several tie on both total and log-odds.

        Ties are the whole point: `nlargest(5, "total")` keeps the first row
        among equals, so a tied group is what exposes an unordered walk.
        """
        works_rows = []
        poles_rows = []
        doi_n = 0
        # 12 journals in 4 tie-groups of 3, each group sharing one
        # (efficiency, accountability) count pair — hence one log_odds and one
        # total across the group.
        for group, (n_eff, n_acc) in enumerate([(9, 3), (3, 9), (6, 6), (8, 4)]):
            for member in range(3):
                journal = f"Journal of Group{group} Variant{member}"
                for pole, count in (("efficiency", n_eff), ("accountability", n_acc)):
                    for _ in range(count):
                        doi = f"10.2000/venue{doi_n:04d}"
                        doi_n += 1
                        works_rows.append((doi, journal, 100, f"Title {doi_n}"))
                        poles_rows.append((doi, 0.5 if pole == "efficiency" else -0.5, pole))
        works = tmp_path / "refined_works.csv"
        poles = tmp_path / "tab_pole_papers.csv"
        _write_csv(str(works), ["doi", "journal", "cited_by_count", "title"], works_rows)
        _write_csv(str(poles), ["doi", "axis_score", "pole_assignment"], poles_rows)
        return str(works), str(poles)

    def test_venue_table(self, tmp_path, venue_inputs):
        works, poles = venue_inputs
        p1, p2 = _run_under_both_seeds(
            "figures/export_tab_venues.py", "tab_venues.md",
            ["--refined-works", works, "--pole-papers", poles],
            tmp_path, str(tmp_path),
        )
        assert filecmp.cmp(str(p1), str(p2), shallow=False), (
            "tab_venues.md differs between hash seeds — the journal set union "
            "is being walked unordered into the table"
        )
