"""Provenance: the A.5 separation figures cited in the manuscript equal the
committed CSV (ticket 0195, follow-up to the 0161 stat-provenance audit).

The 0161 audit found the A.5 numbers (nodes, edges, within-tradition share,
null mean, z, permutation count) were hand-transcribed into the manuscript
with no committed source table. This test closes that gap: it reads the
values from ``content/tables/tab_null_separation_pre2007.csv`` and asserts
each one appears, at the precision the prose uses, in the A.5 bullet of
``content/manuscript.qmd``.

The test extracts numbers from the CSV rather than pinning literals, so a
legitimate regeneration on a frozen corpus that updates *both* the CSV and
the prose together keeps it green; only a silent drift between the two
turns it red. This is a mechanical cross-consistency guard, not a positive
prose pin (cf. the prose-polarity rule): it does not assert any particular
wording, only that the numbers the prose cites are the numbers the pipeline
committed.
"""

import os

import pandas as pd

REPO = os.path.dirname(os.path.dirname(__file__))
CSV = os.path.join(REPO, "content", "tables", "tab_null_separation_pre2007.csv")
MANUSCRIPT = os.path.join(REPO, "content", "manuscript.qmd")


def _louvain_share_row():
    """The primary A.5 statistic: within_tradition_share, louvain_anchored."""
    df = pd.read_csv(CSV)
    row = df[
        (df["labelling"] == "louvain_anchored")
        & (df["statistic"] == "within_tradition_share")
    ]
    assert len(row) == 1, (
        "expected exactly one louvain_anchored/within_tradition_share row, "
        f"got {len(row)}"
    )
    return row.iloc[0]


def _a5_bullet():
    """The manuscript's A.5 co-citation-separation bullet text."""
    with open(MANUSCRIPT, encoding="utf-8") as f:
        text = f.read()
    # The bullet begins with the bold label and runs to the next newline.
    marker = "**Co-citation community separation.**"
    start = text.find(marker)
    assert start != -1, "A.5 co-citation-separation bullet not found in manuscript"
    end = text.find("\n", start)
    return text[start:end]


def test_separation_csv_committed():
    """The A.5 source table exists and is committed (0195 exit criterion)."""
    assert os.path.exists(CSV), (
        f"{CSV} missing — A.5 figures have no committed source. "
        "Run `make separation` and commit the table."
    )


def test_a5_prose_matches_committed_csv():
    """Every figure the A.5 bullet cites equals the committed CSV value.

    Node and edge counts exact; share and null mean at two decimals; z to
    the nearest integer (the prose writes 'z ≈ N'); permutation count exact.
    """
    row = _louvain_share_row()
    bullet = _a5_bullet()

    n_nodes = int(row["n_nodes"])
    n_edges = int(row["n_edges"])
    observed = float(row["observed"])
    null_mean = float(row["null_mean"])
    z_score = float(row["z_score"])
    n_perm = int(row["n_perm"])

    checks = {
        f"{n_nodes} nodes": f"{n_nodes} nodes",
        f"{n_edges} edges": f"{n_edges} edges",
        f"share {observed:.2f}": f"{observed:.2f}",
        f"null {null_mean:.2f}": f"{null_mean:.2f}",
        f"z ≈ {round(z_score)}": f"{round(z_score)}",
        f"N = {n_perm} permutations": str(n_perm),
    }
    for label, needle in checks.items():
        assert needle in bullet, (
            f"A.5 prose does not cite the committed {label!r} "
            f"(CSV value not found in bullet). Bullet:\n{bullet}"
        )
