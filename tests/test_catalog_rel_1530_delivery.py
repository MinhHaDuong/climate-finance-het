"""The 1530 search runs convert into a delivery that meets the intake contract."""

import csv
import gzip
import json
import os

import catalog_rel_1530_delivery as cd
import pytest
import qa_rel_intake as ric

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = ["query_id", "kind", "stratum", "language", "theme", "platform", "run_at",
       "filter", "n_expected", "n_received", "completed", "stop_reason"]


def _hit(wid, qid, **kw):
    base = {"openalex_id": wid, "doi": f"10.5555/{wid.lower()}", "title": f"T {wid}",
            "year": 2020, "date": "2020-01-01", "language": "es", "type": "article",
            "cited_by_count": 3, "journal": "J", "countries": ["BR", "AR"],
            "abstract": "", "query_id": qid, "in_corpus": False, "icf_term": True}
    base.update(kw)
    return base


def _run_dir(tmp_path, name, registry, hits):
    d = tmp_path / name
    d.mkdir()
    with open(d / "registry.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=REG)
        w.writeheader()
        for r in registry:
            w.writerow({k: r.get(k, "") for k in REG})
    with gzip.open(d / "results.jsonl.gz", "wt", encoding="utf-8") as fh:
        for h in hits:
            fh.write(json.dumps(h) + "\n")
    return d


def _reg(qid, completed="True", stop=""):
    return {"query_id": qid, "kind": "q", "platform": "openalex",
            "run_at": "2026-09-29T14:28:48+00:00", "filter": f"search:{qid}",
            "n_expected": "2", "n_received": "2", "completed": completed, "stop_reason": stop}


def test_five_record_run_yields_a_contract_valid_delivery(tmp_path):
    f = _run_dir(tmp_path, "20260929f", [_reg("Q1"), _reg("Q2", "False", "rate_limited")], [
        _hit("W1", "Q1"), _hit("W2", "Q1", in_corpus=True, doi=None),
        _hit("W3", "Q2", title=""), _hit("W1", "Q2")])
    g = _run_dir(tmp_path, "20260929g", [_reg("G1")], [_hit("W2", "G1"), _hit("W4", "G1")])
    out = tmp_path / "t1530-sud-openalex" / "2026-09-29"
    rc = cd.main(["--run-dir", str(f), "--run-dir", str(g), "--output-dir", str(out),
                  "--config", os.path.join(ROOT, "config", "rel_pool.yaml"),
                  "--delivered-at", "2026-09-30T00:00:00Z"])
    assert rc == 0
    assert ric.check_delivery(str(out)) == []
    with open(out / "records.csv", encoding="utf-8") as fh:
        recs = {r["record_id"]: r for r in csv.DictReader(fh)}
    assert sorted(recs) == ["W1", "W2", "W4"], "one row per work, in-corpus works kept"
    assert recs["W1"]["query_id"] == "Q1" and recs["W1"]["query_ids_all"] == "Q1;Q2"
    assert recs["W1"]["affiliation_countries"] == "BR; AR"
    assert recs["W2"]["lane_status"] == "in_refined_v2" and recs["W2"]["doi"] == ""
    with open(out / "excluded.csv", encoding="utf-8") as fh:
        exc = sorted((r["record_id"], r["reason"]) for r in csv.DictReader(fh))
    assert exc == [("W1", "duplicate_in_lane"), ("W2", "duplicate_in_lane"),
                   ("W3", "not_retrievable")]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["coverage"] == "incomplete"
    assert {"unit": "Q2", "reason": "rate_limited"} in manifest["incomplete"]
    with open(out / "registry.csv", encoding="utf-8") as fh:
        reg = {r["query_id"]: r for r in csv.DictReader(fh)}
    assert reg["Q1"]["query"] == "search:Q1" and reg["Q2"]["completed"] == "false"
    # immutable once written
    assert cd.main(["--run-dir", str(f), "--output-dir", str(out)]) == 1


def test_failing_conversion_leaves_nothing_behind(tmp_path):
    # An unfinished query without stop_reason violates the registry contract.
    f = _run_dir(tmp_path, "20260929f", [_reg("Q1", "False", "")], [_hit("W1", "Q1")])
    out = tmp_path / "intake" / "t1530-sud-openalex" / "2026-09-29"
    (tmp_path / "intake").mkdir()
    rc = cd.main(["--run-dir", str(f), "--output-dir", str(out),
                  "--config", os.path.join(ROOT, "config", "rel_pool.yaml")])
    assert rc == 1
    assert not out.exists() and not out.parent.exists()
    assert os.listdir(tmp_path / "intake") == []


def test_delivery_carries_slim_authors_and_fills_only_blank_cells_from_the_backfill(tmp_path):
    hits = [_hit("W1", "Q1", first_author="Kept, A.", all_authors=["Kept, A.", "Two, B."],
                 host_org_name="Wiley", host_org_id="P1", issn=["1111-2222"]),
            _hit("W2", "Q1")]
    d = _run_dir(tmp_path, "20260929f", [_reg("Q1")], hits)
    bf = tmp_path / "bf"
    bf.mkdir()
    with gzip.open(bf / "backfill.jsonl.gz", "wt", encoding="utf-8") as fh:
        for rec in ({"openalex_id": "W1", "first_author": "Backfill, Z.",
                     "all_authors": ["Backfill, Z."], "host_org_name": "Other",
                     "issn": ["9999-9999"], "source_type": "journal"},
                    {"openalex_id": "W2", "first_author": "Filled, C.",
                     "all_authors": ["Filled, C."], "host_org_name": "Routledge",
                     "host_org_id": "P2", "issn": []}):
            fh.write(json.dumps(rec) + "\n")
    out = tmp_path / "t1530-sud-openalex" / "2026-09-29"
    rc = cd.main(["--run-dir", str(d), "--backfill", str(bf), "--output-dir", str(out),
                  "--config", os.path.join(ROOT, "config", "rel_pool.yaml"),
                  "--delivered-at", "2026-09-30T00:00:00Z"])
    assert rc == 0 and ric.check_delivery(str(out)) == []
    with open(out / "records.csv", encoding="utf-8") as fh:
        recs = {r["record_id"]: r for r in csv.DictReader(fh)}
    w1, w2 = recs["W1"], recs["W2"]
    assert (w1["first_author"], w1["all_authors"]) == ("Kept, A.", "Kept, A.; Two, B.")
    assert (w1["host_org_name"], w1["issn"], w1["source_type"]) == ("Wiley", "1111-2222", "journal")
    assert (w2["first_author"], w2["host_org_name"], w2["host_org_id"]) == (
        "Filled, C.", "Routledge", "P2")


def test_a_regenerated_delivery_names_what_it_supersedes_and_what_changed(tmp_path):
    d = _run_dir(tmp_path, "20260929f", [_reg("Q1")], [_hit("W1", "Q1")])
    out = tmp_path / "t1530-sud-openalex" / "2026-10-09"
    rc = cd.main(["--run-dir", str(d), "--output-dir", str(out),
                  "--config", os.path.join(ROOT, "config", "rel_pool.yaml"),
                  "--supersedes", "2026-09-29", "--note", "Regenerated with the backfill.",
                  "--delivered-at", "2026-10-09T00:00:00Z"])
    assert rc == 0 and ric.check_delivery(str(out)) == []
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["supersedes"] == "2026-09-29"
    assert manifest["notes"].endswith(" Regenerated with the backfill.")
    assert manifest["notes"].startswith("Final 1530 search")
