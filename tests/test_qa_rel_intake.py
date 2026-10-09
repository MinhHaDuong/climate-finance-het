"""The REL intake contract checker accepts a valid delivery and names each fault."""

import csv
import json
import os

import pytest
import qa_rel_intake as ric

pytestmark = pytest.mark.domain_corpus


def _write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def _record(rid, **kw):
    base = {"record_id": rid, "query_id": "q1", "platform": "crossref",
            "retrieved_at": "2026-10-01", "title": f"Title {rid}",
            "doi": f"10.1234/{rid}", "year": "2020"}
    base.update(kw)
    return base


def _delivery(tmp_path, records=None, registry=None, excluded=None, manifest=None):
    d = tmp_path / "t1650-sommaires" / "2026-10-01"
    d.mkdir(parents=True)
    records = records if records is not None else [_record("r1"), _record("r2")]
    registry = registry if registry is not None else [{
        "query_id": "q1", "platform": "crossref", "query": "ISSN 0002-8282 2020",
        "run_at": "2026-10-01", "n_received": "3", "completed": "true"}]
    excluded = excluded if excluded is not None else [{
        "record_id": "r3", "query_id": "q1", "reason": "front_matter",
        "title": "Editorial board", "note": ""}]
    _write_csv(d / "records.csv", ric.RECORD_COLUMNS, records)
    _write_csv(d / "registry.csv", ric.REGISTRY_REQUIRED + ["filter", "n_expected", "stop_reason"],
               registry)
    _write_csv(d / "excluded.csv", ric.EXCLUDED_COLUMNS, excluded)
    m = {"lane": "t1650-sommaires", "ticket": "1650", "delivery": "2026-10-01",
         "delivered_at": "2026-10-01T12:00:00Z",
         "producer": {"script": "scripts/x.py", "commit": "abc123", "machine": "padme"},
         "counts": {"records": len(records),
                    "excluded": {"front_matter": 1} if excluded else {}},
         "coverage": "complete", "incomplete": [], "needs_human": [],
         "supersedes": None, "notes": ""}
    m.update(manifest or {})
    (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return d


def test_optional_repec_handle_column_is_checked_when_present_and_not_required():
    header = ric.RECORD_COLUMNS + ["repec_handle"]
    full = {c: "" for c in header}
    good = {**full, **_record("r1", repec_handle="RePEc:nbr:nberwo:35497")}
    bad = {**full, **_record("r2", repec_handle="edsrep.p.nbr.nberwo.35497")}
    errors = ric.check_records(header, [good, bad], {"q1"})
    assert len(errors) == 1 and "line 3" in errors[0] and "repec_handle" in errors[0]
    assert ric.check_records(ric.RECORD_COLUMNS, [{c: good[c] for c in ric.RECORD_COLUMNS}],
                             {"q1"}) == []


def test_valid_delivery_passes(tmp_path, capsys):
    d = _delivery(tmp_path)
    assert ric.check_delivery(str(d)) == []
    assert ric.main([str(d)]) == 0
    assert "OK" in capsys.readouterr().out


def test_relevance_is_never_an_exclusion_reason(tmp_path):
    d = _delivery(tmp_path, excluded=[{"record_id": "r3", "query_id": "q1",
                                       "reason": "off_topic", "title": "x", "note": ""}],
                  manifest={"counts": {"records": 2, "excluded": {"off_topic": 1}}})
    errors = ric.check_delivery(str(d))
    assert any("off_topic" in e and "relevance is never a reason" in e for e in errors)


def test_every_violation_is_reported_not_only_the_first(tmp_path):
    bad = [_record("r1", title="", doi="https://doi.org/10.1/x"),
           _record("r1", query_id="q9", retrieved_at="01/10/2026"),
           _record("r4", doi="", year="", openalex_id="")]
    d = _delivery(tmp_path, records=bad, manifest={"counts": {"records": 2,
                                                               "excluded": {"front_matter": 1}}})
    errors = ric.check_delivery(str(d))
    text = "\n".join(errors)
    for fragment in ("appears 2 times", "title is empty", "not a bare",
                     "'q9' not in registry", "not ISO 8601",
                     "needs at least one of doi, openalex_id, year",
                     "counts.records is 2, records.csv has 3 rows"):
        assert fragment in text


def test_missing_column_and_missing_file_are_named(tmp_path):
    d = _delivery(tmp_path)
    _write_csv(d / "records.csv", ["record_id", "title"], [{"record_id": "r1", "title": "t"}])
    assert any("missing column(s)" in e and "query_id" in e for e in ric.check_delivery(str(d)))
    os.remove(d / "excluded.csv")
    assert ric.check_delivery(str(d)) == ["missing file(s): excluded.csv"]


def test_incomplete_query_needs_stop_reason_and_coverage_must_agree(tmp_path):
    d = _delivery(tmp_path,
                  registry=[{"query_id": "q1", "platform": "crossref", "query": "x",
                             "run_at": "2026-10-01", "n_received": "3", "completed": "false"}],
                  manifest={"coverage": "incomplete", "incomplete": []})
    text = "\n".join(ric.check_delivery(str(d)))
    assert "needs a stop_reason" in text
    assert "coverage incomplete but nothing listed" in text


def test_manifest_must_match_directory_and_counts(tmp_path):
    d = _delivery(tmp_path, manifest={"lane": "t1651-gavard", "delivery": "2026-10-02",
                                      "producer": {"script": "s"},
                                      "counts": {"records": 2, "excluded": {}}})
    text = "\n".join(ric.check_delivery(str(d)))
    assert "differs from directory 't1650-sommaires'" in text
    assert "differs from directory '2026-10-01'" in text
    assert "producer needs script, commit and machine" in text
    assert "counts.excluded {} differs" in text


def test_excluded_record_cannot_also_be_delivered(tmp_path):
    d = _delivery(tmp_path, excluded=[{"record_id": "r1", "query_id": "q1",
                                       "reason": "front_matter", "title": "x", "note": ""}])
    assert any("is also delivered" in e for e in ric.check_delivery(str(d)))


def _no_dedup_key_delivery(tmp_path, record_id="r3", title="Climate finance in the Caribbean"):
    row = {"record_id": record_id, "query_id": "q1", "reason": "no_dedup_key",
           "title": title, "note": "https://hdl.handle.net/2139/12345"}
    return _delivery(tmp_path, excluded=[row],
                     manifest={"counts": {"records": 2, "excluded": {"no_dedup_key": 1}}})


def test_titled_record_without_dedup_key_is_a_valid_exclusion(tmp_path):
    assert ric.check_delivery(str(_no_dedup_key_delivery(tmp_path))) == []


def test_no_dedup_key_row_needs_a_title(tmp_path):
    d = _no_dedup_key_delivery(tmp_path, title="  ")
    assert ric.check_delivery(str(d)) == [
        "excluded.csv line 2: no_dedup_key row needs a title "
        "(it enters the pool as a title-only work)"]


def test_no_dedup_key_record_cannot_also_be_delivered(tmp_path):
    d = _no_dedup_key_delivery(tmp_path, record_id="r1")
    assert any("is also delivered" in e for e in ric.check_delivery(str(d)))


@pytest.mark.parametrize("excluded", [["front_matter"], 1])
def test_malformed_counts_excluded_is_a_violation_not_a_crash(tmp_path, excluded):
    d = _delivery(tmp_path, manifest={"counts": {"records": 2, "excluded": excluded}})
    assert any("counts.excluded must be an object" in e for e in ric.check_delivery(str(d)))


@pytest.mark.parametrize("coverage", [["complete"], {"a": 1}])
def test_unhashable_coverage_is_a_violation_not_a_crash(tmp_path, coverage):
    d = _delivery(tmp_path, manifest={"coverage": coverage})
    assert any("is not complete/incomplete" in e for e in ric.check_delivery(str(d)))


@pytest.mark.parametrize("name", ric.FILES)
def test_non_utf8_file_is_named_and_other_files_still_checked(tmp_path, name):
    d = _delivery(tmp_path, excluded=[{"record_id": "r3", "query_id": "q1",
                                       "reason": "off_topic", "title": "x", "note": ""}],
                  manifest={"counts": {"records": 2, "excluded": {"off_topic": 1}}})
    if name == "excluded.csv":
        _write_csv(d / "registry.csv", ["query_id"], [{"query_id": "q1"}])
    raw = (d / name).read_bytes()
    (d / name).write_bytes(raw + "Économie\n".encode("latin-1"))
    errors = ric.check_delivery(str(d))
    assert any(e.startswith(f"{name}: not UTF-8") for e in errors)
    other = "registry.csv: missing column" if name == "excluded.csv" else "off_topic"
    assert any(other in e for e in errors)


def test_utf8_bom_is_tolerated(tmp_path):
    d = _delivery(tmp_path)
    for name in ("records.csv", "registry.csv", "excluded.csv"):
        raw = (d / name).read_bytes()
        (d / name).write_bytes(b"\xef\xbb\xbf" + raw)
    assert ric.check_delivery(str(d)) == []


def test_records_header_failure_skips_the_row_count_check(tmp_path):
    d = _delivery(tmp_path)
    _write_csv(d / "records.csv", ["title"], [{"title": "t"}])
    errors = ric.check_delivery(str(d))
    assert any("records.csv: missing column(s)" in e for e in errors)
    assert not any("counts.records" in e for e in errors)


@pytest.mark.parametrize("bad", ["2026-13-45", "2026-02-30T10:00:00Z"])
def test_dates_must_be_real_calendar_days(tmp_path, bad):
    d = _delivery(tmp_path, records=[_record("r1", retrieved_at=bad), _record("r2")],
                  manifest={"delivered_at": bad})
    text = "\n".join(ric.check_delivery(str(d)))
    assert f"retrieved_at {bad!r} is not ISO 8601" in text
    assert "delivered_at is not ISO 8601" in text


@pytest.mark.parametrize("declared", [True, "2", 2.0, None])
def test_counts_records_must_be_an_integer(tmp_path, declared):
    d = _delivery(tmp_path, records=[_record("r1")],
                  manifest={"counts": {"records": declared, "excluded": {"front_matter": 1}}})
    assert any("counts.records" in e and "is not an integer" in e
               for e in ric.check_delivery(str(d)))



@pytest.mark.parametrize("url", ["https://hdl.handle.net/2139/12345",
                                 "https://repo.uwi.edu/handle/2139/7?show=full",
                                 "https://doi.org/10.1234/x", "https://openalex.org/W12"])
def test_persistent_url_is_a_dedup_key(tmp_path, url):
    rec = _record("r1", doi="", year="", url=url)
    d = _delivery(tmp_path, records=[rec, _record("r2")])
    assert ric.check_delivery(str(d)) == []


@pytest.mark.parametrize("url", ["hdl:2139/12345", "https://ceew.in/publications/x",
                                 "https://j.org/issue/5", "https://repo.org",
                                 "https://doi.org/", "https://openalex.org/authors/A1"])
def test_non_persistent_url_is_not_a_dedup_key(tmp_path, url):
    rec = _record("r1", doi="", year="", url=url)
    d = _delivery(tmp_path, records=[rec, _record("r2")])
    errors = ric.check_delivery(str(d))
    assert len(errors) == 1 and repr(url) in errors[0] and "no_dedup_key" in errors[0]


def _native_titleless_delivery(tmp_path, monkeypatch, abstract=True):
    """An operator-approved fixture with an actual immutable provider page."""
    import gzip
    import hashlib

    import _rel_titleless_intake as titleless
    native = {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1234/native",
              "title": "", "display_name": "", "publication_year": 2020,
              "abstract_inverted_index": {"Substantive": [0], "evidence": [1]} if abstract else None,
              "type": "paratext", "is_paratext": True}
    record = _record("W1", platform="openalex", platform_record_id="W1", openalex_id="W1",
                     doi="10.1234/native", title="", abstract="Substantive evidence" if abstract else "",
                     doc_type="paratext", is_paratext="true")
    d = _delivery(tmp_path, records=[record], excluded=[], registry=[{
        "query_id": "q1", "platform": "openalex", "query": "exact DOI metadata",
        "run_at": "2026-10-01", "n_received": "1", "completed": "true"}])
    _write_csv(d / "records.csv", ric.RECORD_COLUMNS + ["is_paratext"], [record])
    encoded = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    params = {"filter": "doi:10.1234/native", "per_page": 100, "cursor": "*"}
    body = {"results": [native], "meta": {"count": 1, "next_cursor": None}}
    page = {"query": params, "body": body, "status": 200, "retrieved_at": record["retrieved_at"]}
    (d / "native.json.gz").write_bytes(gzip.compress(json.dumps(page).encode(), mtime=0))
    (d / "authority.md").write_text("Approved exact titleless intake fixture")
    proof = dict(record_id="W1", query_id="q1", openalex_id="W1", doi=record["doi"],
                 native_archive_path="native.json.gz", native_compressed_sha256=digest(d / "native.json.gz"),
                 native_body_sha256=hashlib.sha256(encoded(body)).hexdigest(),
                 native_work_sha256=hashlib.sha256(encoded(native)).hexdigest(),
                 source_query_sha256=hashlib.sha256(encoded(params)).hexdigest(),
                 retrieved_at=record["retrieved_at"], source_type="openalex", native_title_empty=True)
    (d / "roster.json").write_text(json.dumps([proof]))
    m = json.loads((d / "manifest.json").read_text())
    m["native_titleless"] = {"version": 1, "basis": "native_titleless",
        "roster": {"path": "roster.json", "sha256": digest(d / "roster.json")},
        "authority": {"path": "authority.md", "sha256": digest(d / "authority.md")}}
    (d / "manifest.json").write_text(json.dumps(m))
    registry = {"approved_manifest_sha256": digest(d / "manifest.json"),
                "authority_sha256": digest(d / "authority.md"), "records": 1}
    monkeypatch.setattr(titleless, "intake_registry", lambda: registry)
    monkeypatch.setattr(titleless, "INTAKE_ROOT", tmp_path)
    return d, record


def test_native_titleless_requires_exact_approved_proof(tmp_path, monkeypatch):
    d, record = _native_titleless_delivery(tmp_path, monkeypatch)
    assert ric.check_delivery(str(d)) == []
    _write_csv(d / "records.csv", ric.RECORD_COLUMNS + ["is_paratext"], [dict(record, title="placeholder")])
    assert ric.check_delivery(str(d))
    _write_csv(d / "records.csv", ric.RECORD_COLUMNS + ["is_paratext"], [dict(record, doi="10.1234/wrong")])
    assert ric.check_delivery(str(d))


@pytest.mark.parametrize("change", [{"openalex_id": "W999"}, {"abstract": "changed source"},
                                    {"year": "0"}, {"is_paratext": "false"}, {"doc_type": "article"}])
def test_titleless_complete_fields_cannot_be_forged(tmp_path, monkeypatch, change):
    d, record = _native_titleless_delivery(tmp_path, monkeypatch)
    _write_csv(d / "records.csv", ric.RECORD_COLUMNS + ["is_paratext"], [dict(record, **change)])
    assert ric.check_delivery(str(d))


def test_titleless_native_tamper_and_unregistered_scope_fail(tmp_path, monkeypatch):
    import _rel_titleless_intake as titleless
    d, _ = _native_titleless_delivery(tmp_path, monkeypatch)
    (d / "native.json.gz").write_bytes(b"tampered")
    assert ric.check_delivery(str(d))
    monkeypatch.setattr(titleless, "intake_registry", lambda: {"approved_manifest_sha256": "0" * 64})
    assert ric.check_delivery(str(d))
