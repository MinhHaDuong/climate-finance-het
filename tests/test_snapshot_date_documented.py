"""Each deliverable states the corpus snapshot its numbers come from.

The expected date is per-document because the documents are not on the same
corpus. The data paper moved to corpus v2 (rebuilt 2026-07-24, ticket 0288);
the multilayer paper and the corpus report still describe v1 (2026-03-26).
A single shared constant silently asserted they were in step, and went red
the moment the data paper was refreshed — which is the failure this file
exists to catch, so the fix is per-document dates, not a looser check.

These literals are hand-maintained: the snapshot date lives in prose, and CI
has no corpus data to read it from (data/catalogs/ is DVC-managed). Deriving
it from the corpus artifact is ticket 0319.
"""

from pathlib import Path

import pytest

SNAPSHOT_DATES = {
    "deliverables/data-paper/data-paper.qmd": "2026-07-24",
    "deliverables/multilayer/multilayer-detection.qmd": "2026-03-26",
    "deliverables/corpus-report/corpus-report.qmd": "2026-03-26",
}


@pytest.mark.parametrize("path,expected", sorted(SNAPSHOT_DATES.items()))
def test_snapshot_date_documented(path, expected):
    text = Path(path).read_text()
    assert expected in text, (
        f"Snapshot date {expected} not found in {Path(path).name}. "
        f"If the document was rebuilt on a newer corpus, update its entry in "
        f"SNAPSHOT_DATES — do not delete the check."
    )
