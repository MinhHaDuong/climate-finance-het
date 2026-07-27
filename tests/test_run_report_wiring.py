"""catalog_merge's run report must be a declared artifact, not a side effect.

Ticket 0349. `compute_vars.dedup_stats` sources two published data-paper
numbers from the latest `catalog_merge` run report, but the DVC stage that
writes it declares only `unified_works.csv`. DVC therefore cannot tell when the
report is stale: a cache hit on `unified_works.csv` skips the stage and leaves
the report describing an older merge than the corpus in hand.

The selection was also unsafe. `sorted(glob("catalog_merge__*.json"))[-1]`
takes the lexicographically last match; run ids are UTC timestamps starting
with a digit, so any file named `catalog_merge__test*.json` sorts after every
real report and would silently become the source of both numbers. Test fixtures
with exactly that shape leak into the real corpus directory today (ticket 0346),
so this is a near-miss rather than a hypothetical.
"""

import json
import os

import pytest
import yaml
from utils import BASE_DIR

DVC_YAML = os.path.join(BASE_DIR, "dvc.yaml")
STABLE_REPORT = "data/catalogs/run_reports/catalog_merge.json"


def _stage_outs(stage_name):
    with open(DVC_YAML, encoding="utf-8") as fh:
        stages = yaml.safe_load(fh)["stages"]
    outs = []
    for entry in stages[stage_name].get("outs", []):
        outs.append(next(iter(entry)) if isinstance(entry, dict) else entry)
    return outs


@pytest.mark.adherence
def test_catalog_merge_declares_its_run_report():
    """A stage's consumed artifacts must be declared outputs."""
    outs = _stage_outs("catalog_merge")
    assert STABLE_REPORT in outs, (
        "catalog_merge writes a run report that compute_vars reads, but "
        f"declares only {outs} - dvc cannot tell when the report is stale"
    )


def test_latest_report_ignores_non_timestamp_run_ids(tmp_path, monkeypatch):
    """A stray fixture must never outrank a real timestamped report.

    This is the defect the old lexicographic sort had: 't' > '2', so
    `catalog_merge__test.json` beat every `catalog_merge__2026...json`.
    """
    monkeypatch.setattr("pipeline_loaders.CATALOGS_DIR", str(tmp_path))
    reports = tmp_path / "run_reports"
    reports.mkdir()
    real = {"doi_duplicates_removed": 833, "title_year_duplicates_removed": 159}
    (reports / "catalog_merge__20260727T132143Z.json").write_text(json.dumps(real))
    (reports / "catalog_merge__test.json").write_text(
        json.dumps({"doi_duplicates_removed": 1, "title_year_duplicates_removed": 2})
    )

    from pipeline_io import latest_run_report

    got = latest_run_report("catalog_merge")
    assert got is not None, "no report selected"
    assert got["doi_duplicates_removed"] == 833, (
        "a non-timestamp fixture outranked the real report - the published "
        "dedup counts would come from test data"
    )


def test_latest_report_prefers_the_declared_stable_file(tmp_path, monkeypatch):
    """The DVC-declared file wins when present; the archive is a fallback."""
    monkeypatch.setattr("pipeline_loaders.CATALOGS_DIR", str(tmp_path))
    reports = tmp_path / "run_reports"
    reports.mkdir()
    (reports / "catalog_merge__20260101T000000Z.json").write_text(
        json.dumps({"doi_duplicates_removed": 1})
    )
    (reports / "catalog_merge.json").write_text(
        json.dumps({"doi_duplicates_removed": 833})
    )

    from pipeline_io import latest_run_report

    assert latest_run_report("catalog_merge")["doi_duplicates_removed"] == 833


def test_latest_report_returns_none_when_absent(tmp_path, monkeypatch):
    """Absence is reported, not faked — callers decide how loud to be."""
    monkeypatch.setattr("pipeline_loaders.CATALOGS_DIR", str(tmp_path))
    (tmp_path / "run_reports").mkdir()
    from pipeline_io import latest_run_report

    assert latest_run_report("catalog_merge") is None
