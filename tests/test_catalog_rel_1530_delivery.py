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
