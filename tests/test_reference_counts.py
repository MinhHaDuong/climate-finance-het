"""Tests for the per-document reference-count distribution artifact.

Ticket 0285 (split from 0277, RDJ-26561 R&R remark R1-13): the referee asks
whether per-document reference counts were recorded, predicting empty/aberrant
reference lists in OpenAlex. This artifact computes the distribution from the
shipped citation edge list.

Semantics (see ticket Plan section):
- ``refined_citations.csv`` is an edge list, one row per reference. A document
  with zero references has NO rows — so its count must come from an outer join
  onto the full DOI universe, fillna(0), never from the edge list alone.
- Documents with no DOI cannot be a ``source_doi``: they are reported separately
  ("excluded from the citation graph"), never folded into "zero references".

Tests:
1. Unit tests on synthetic frames — zero-reference documents counted (not
   dropped), no-DOI documents flagged separately, bucket totals sum to the
   DOI universe size.
2. Integration test: run the script via subprocess, validate output schema.
"""

import os
import sys

import pandas as pd
import pytest
from _source_roots import source_root_env

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, os.path.join(SCRIPTS_DIR, "analysis"))  # 0257: analysis entry points


def _metric(result: pd.DataFrame, name: str) -> float:
    """Pull a single metric value from the long-format result table."""
    rows = result[result["metric"] == name]
    assert len(rows) == 1, f"metric {name!r} appears {len(rows)} times"
    return float(rows.iloc[0]["value"])


class TestComputeReferenceCounts:
    """Unit tests for the compute_reference_counts function."""

    # Synthetic fixture shared across tests:
    #   works: three documents with DOIs (a, b, c) + one with no DOI.
    #   citations: a has 3 reference edges, b has 1, c has NONE (absent from
    #     the edge list entirely — the zero-reference document that must survive).
    WORKS = pd.DataFrame(
        {
            "doi": ["10.1/a", "10.2/b", "10.3/c", None],
            "title": ["A", "B", "C", "D"],
        }
    )
    CITATIONS = pd.DataFrame(
        {
            "source_doi": ["10.1/a", "10.1/a", "10.1/a", "10.2/b"],
            "ref_doi": ["10.9/x", "10.9/y", "10.9/z", "10.9/w"],
        }
    )

    def test_zero_reference_document_counted_not_dropped(self):
        """Document c has no edges — it appears with count 0, not dropped."""
        from compute_reference_counts import compute_reference_counts

        result = compute_reference_counts(self.WORKS, self.CITATIONS)
        # Exactly one document (c) has zero references.
        assert _metric(result, "n_zero_references") == 1
        assert _metric(result, "bucket_0") == 1

    def test_no_doi_document_flagged_separately(self):
        """The no-DOI document is excluded from the graph, not folded into zero."""
        from compute_reference_counts import compute_reference_counts

        result = compute_reference_counts(self.WORKS, self.CITATIONS)
        assert _metric(result, "n_documents_total") == 4
        assert _metric(result, "n_documents_with_doi") == 3
        assert _metric(result, "n_documents_no_doi") == 1
        # The no-DOI document must NOT inflate the zero-reference count.
        assert _metric(result, "n_zero_references") == 1

    def test_bucket_totals_sum_to_doi_universe(self):
        """The six buckets partition the DOI universe exactly."""
        from compute_reference_counts import compute_reference_counts

        result = compute_reference_counts(self.WORKS, self.CITATIONS)
        buckets = [
            "bucket_0",
            "bucket_1_5",
            "bucket_6_20",
            "bucket_21_50",
            "bucket_51_100",
            "bucket_100_plus",
        ]
        total = sum(_metric(result, b) for b in buckets)
        assert total == _metric(result, "n_documents_with_doi") == 3

    def test_counts_and_tail_statistics(self):
        """Counts [3, 1, 0] give the expected buckets and tail statistics."""
        from compute_reference_counts import compute_reference_counts

        result = compute_reference_counts(self.WORKS, self.CITATIONS)
        # a=3, b=1 both land in bucket 1-5; c=0 in bucket_0.
        assert _metric(result, "bucket_1_5") == 2
        assert _metric(result, "bucket_0") == 1
        assert _metric(result, "ref_count_max") == 3
        # median of [0, 1, 3] = 1; mean = 4/3.
        assert _metric(result, "ref_count_median") == 1
        assert abs(_metric(result, "ref_count_mean") - 4 / 3) < 1e-9
        # share of zero-reference documents = 1/3.
        assert abs(_metric(result, "share_zero_references") - 1 / 3) < 1e-9

    def test_high_tail_bucketing(self):
        """A document with >100 references lands in the 100+ tail bucket."""
        from compute_reference_counts import compute_reference_counts

        works = pd.DataFrame({"doi": ["10.1/a", "10.2/b"], "title": ["A", "B"]})
        # a has 150 edges (aberrant high tail), b has 30.
        citations = pd.DataFrame(
            {
                "source_doi": ["10.1/a"] * 150 + ["10.2/b"] * 30,
                "ref_doi": [f"10.9/{i}" for i in range(180)],
            }
        )
        result = compute_reference_counts(works, citations)
        assert _metric(result, "bucket_100_plus") == 1
        assert _metric(result, "bucket_21_50") == 1
        assert _metric(result, "ref_count_max") == 150

    def test_schema_validation(self):
        """Output passes ReferenceCountsSchema."""
        from compute_reference_counts import compute_reference_counts
        from schemas import ReferenceCountsSchema

        result = compute_reference_counts(self.WORKS, self.CITATIONS)
        ReferenceCountsSchema.validate(result)


@pytest.mark.integration
class TestReferenceCountsSubprocess:
    """Integration test: run the compute script via subprocess."""

    def test_runs_and_produces_output(self, tmp_path):
        import subprocess

        works = pd.DataFrame(
            {
                "source": ["openalex"] * 4,
                "source_id": [f"id_{i}" for i in range(4)],
                "doi": ["10.1/a", "10.2/b", "10.3/c", ""],
                "title": ["A", "B", "C", "D"],
                "year": ["2010", "2011", "2012", "2013"],
                "cited_by_count": ["10", "5", "0", "1"],
            }
        )
        citations = pd.DataFrame(
            {
                "source_doi": ["10.1/a", "10.1/a", "10.2/b"],
                "source_id": ["id_0", "id_0", "id_1"],
                "ref_doi": ["10.9/x", "10.9/y", "10.9/z"],
            }
        )
        works_csv = tmp_path / "refined_works.csv"
        citations_csv = tmp_path / "refined_citations.csv"
        works.to_csv(works_csv, index=False)
        citations.to_csv(citations_csv, index=False)

        output_csv = tmp_path / "tab_reference_counts.csv"
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                os.path.join(SCRIPTS_DIR, "analysis", "compute_reference_counts.py"),
                "--output",
                str(output_csv),
                "--input",
                str(works_csv),
                str(citations_csv),
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
            env=source_root_env(),
        )
        assert result.returncode == 0, f"Script failed:\n{result.stderr}"
        assert output_csv.exists()

        out_df = pd.read_csv(output_csv)
        assert set(out_df.columns) == {"metric", "value"}
        metrics = set(out_df["metric"])
        assert {"n_documents_with_doi", "n_zero_references", "bucket_0"} <= metrics
