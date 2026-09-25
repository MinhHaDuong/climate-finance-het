"""Blocked sources: browser-session retry and manual-download pickup (ticket 0926)."""

import csv
import logging
import os
import sqlite3
from pathlib import Path

import pytest
from jetp import _firefox
from jetp.build_evidence_layer import refresh_collection
from jetp.corpus_collect_downloads import collect_downloads
from jetp.corpus_harvest_documents import (
    COLLECTION_METHODS,
    MANIFEST_FIELDS,
    _append_manifest,
    browser_session,
    harvest_registry,
)
from test_jetp_documents import FakeResponse, FakeSession, _source, _write_registry

ROOT = Path(__file__).resolve().parents[1]
SECRET = "cookie-value-that-must-never-be-logged"


pytestmark = pytest.mark.wp_jetp

def _manifest_row(source_id, status, url, **extra):
    row = dict.fromkeys(MANIFEST_FIELDS, "")
    row.update(source_id=source_id, country="VNM", retrieved_at="2026-09-01T00:00:00Z",
               status=status, final_url=url, **{"collection_method": "script", **extra})
    return row


def _registry(tmp_path):
    registry = tmp_path / "sources.csv"
    _write_registry(registry, [
        _source(source_id="vnm-blocked", url="https://walled.example.test/plan.pdf"),
        _source(source_id="vnm-done", url="https://open.example.test/done.pdf"),
        _source(source_id="vnm-error", url="https://down.example.test/x.pdf"),
    ])
    manifest = tmp_path / "manifest.csv"
    _append_manifest(manifest, [
        _manifest_row("vnm-blocked", "blocked", "https://walled.example.test/plan.pdf",
                      http_status="403", error="HTTP 403"),
        _manifest_row("vnm-done", "collected", "https://open.example.test/done.pdf",
                      sha256="a" * 64, size_bytes="9",
                      storage_path="objects/aa/" + "a" * 64 + ".pdf"),
        _manifest_row("vnm-error", "fetch_error", "https://down.example.test/x.pdf"),
    ])
    return registry, manifest


def test_retry_targets_only_blocked_sources_and_records_the_browser_method(tmp_path):
    registry, manifest = _registry(tmp_path)
    session = FakeSession([FakeResponse(200, b"%PDF-1.7\nok",
                                        {"Content-Type": "application/pdf"},
                                        url="https://walled.example.test/plan.pdf")])
    seen, waits = [], []

    def factory(urls):
        seen.append(urls)
        return session

    rows = harvest_registry(registry, manifest, tmp_path / "store",
                            retrieved_at="2026-09-24T20:00:00Z", session_factory=factory,
                            statuses={"blocked"}, collection_method="browser-session",
                            delay=2.5, sleep=waits.append)
    assert [r["source_id"] for r in rows] == ["vnm-blocked"]
    # The session is built for the hosts about to be contacted, and only them.
    assert seen == [["https://walled.example.test/plan.pdf"]]
    assert rows[0]["status"] == "collected"
    assert rows[0]["collection_method"] == "browser-session"
    with manifest.open(newline="", encoding="utf-8") as stream:
        written = list(csv.DictReader(stream))
    assert written[-1]["collection_method"] == "browser-session"
    assert waits == []  # one request, no pause before it


def test_the_retry_paces_its_requests(tmp_path):
    registry, manifest = _registry(tmp_path)
    session = FakeSession([FakeResponse(403), FakeResponse(403)])
    waits = []
    rows = harvest_registry(registry, manifest, tmp_path / "store", session=session,
                            statuses={"blocked", "fetch_error"}, delay=2.5,
                            sleep=waits.append)
    assert [r["source_id"] for r in rows] == ["vnm-blocked", "vnm-error"]
    assert waits == [2.5]
    # A default run is the script under its own name.
    assert {r["collection_method"] for r in rows} == {"script"}


def test_a_login_page_served_with_200_is_not_the_document(tmp_path):
    """The replayed session reached dgMarket's login form on 2026-09-24; that
    page must not be recorded as the attachment list it stands in for."""
    registry = tmp_path / "sources.csv"
    _write_registry(registry, [_source(url="https://example.test/list",
                                       expected_format="html")])
    login = (b"<!DOCTYPE html><html><head><title>Please login - Agence Fran\xc3\xa7aise"
             b" de D\xc3\xa9veloppement - dgMarket</title></head></html>")
    rows = harvest_registry(registry, tmp_path / "manifest.csv", tmp_path / "store",
                            session=FakeSession([FakeResponse(200, login)]))
    assert rows[0]["status"] == "invalid_content"
    assert rows[0]["error"] == "login or challenge page, not the document"
    assert not (tmp_path / "store").exists()


def test_a_title_that_merely_contains_sign_is_kept(tmp_path):
    # The JICA press release "Signing of Japanese ODA Loan Agreement…" is a
    # document, not a sign-in form.
    registry = tmp_path / "sources.csv"
    _write_registry(registry, [_source(url="https://example.test/p",
                                       expected_format="html")])
    page = (b"<!DOCTYPE html><html><head><title>Signing of Japanese ODA Loan "
            b"Agreement with Indonesia</title></head></html>")
    rows = harvest_registry(registry, tmp_path / "manifest.csv", tmp_path / "store",
                            session=FakeSession([FakeResponse(200, page)]))
    assert rows[0]["status"] == "collected"


def _cookie_profile(tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    db = sqlite3.connect(profile / "cookies.sqlite")
    db.execute("CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT, path TEXT,"
               " expiry INTEGER, isSecure INTEGER)")
    db.executemany("INSERT INTO moz_cookies VALUES (?, ?, ?, ?, ?, ?)", [
        (".walled.example.test", "cf_clearance", SECRET, "/", 4102444800000, 1),
        ("unrelated.example.org", "session", "other", "/", 4102444800, 1),
    ])
    db.commit()
    db.close()
    (profile / "compatibility.ini").write_text(
        "[Compatibility]\nLastVersion=156.0.1_20260921121718/20260921121718\n")
    return profile


def test_cookies_are_loaded_for_the_contacted_hosts_only(tmp_path):
    jar = _firefox.load_cookies(_cookie_profile(tmp_path), {"walled.example.test"})
    cookies = list(jar)
    assert [(c.domain, c.name) for c in cookies] == [(".walled.example.test", "cf_clearance")]
    assert cookies[0].expires == 4102444800  # milliseconds read as seconds


def test_a_session_cookie_is_kept_without_expiry(tmp_path):
    # Firefox writes expiry 0 for a cookie that lives as long as the browser
    # session; read as a timestamp it would be long expired and never sent.
    profile = _cookie_profile(tmp_path)
    db = sqlite3.connect(profile / "cookies.sqlite")
    db.execute("INSERT INTO moz_cookies VALUES ('walled.example.test', 'sid', 'x', '/', 0, 1)")
    db.commit()
    db.close()
    jar = _firefox.load_cookies(profile, {"walled.example.test"})
    session = next(c for c in jar if c.name == "sid")
    assert session.expires is None and not session.is_expired()


def test_the_browser_session_never_logs_a_cookie(tmp_path, caplog):
    profile = _cookie_profile(tmp_path)
    # The pipeline logger does not propagate to the root, so listen on it.
    pipeline = logging.getLogger("pipeline")
    pipeline.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.DEBUG, logger="pipeline"):
            session = browser_session(profile, ["https://walled.example.test/plan.pdf"])
    finally:
        pipeline.removeHandler(caplog.handler)
    assert session.cookies.get("cf_clearance") == SECRET
    assert session.headers["User-Agent"].endswith("Firefox/156.0")
    # Positive control first: the probe saw the session's own log line.
    assert "1 cookies" in caplog.text
    assert SECRET not in caplog.text


def _places(profile, downloads):
    db = sqlite3.connect(profile / "places.sqlite")
    db.executescript("""
        CREATE TABLE moz_places (id INTEGER PRIMARY KEY, url TEXT);
        CREATE TABLE moz_anno_attributes (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE moz_annos (id INTEGER PRIMARY KEY, place_id INTEGER,
                                anno_attribute_id INTEGER, content TEXT);
        INSERT INTO moz_anno_attributes VALUES (1, 'downloads/destinationFileURI');
        INSERT INTO moz_anno_attributes VALUES (2, 'downloads/metaData');
    """)
    known = downloads / "Plan d'investissement (1).pdf"
    stray = downloads / "holiday.pdf"
    db.executemany("INSERT INTO moz_places VALUES (?, ?)", [
        (1, "https://walled.example.test/plan.pdf#page=2"),
        (2, "https://elsewhere.example.test/holiday.pdf"),
    ])
    db.executemany("INSERT INTO moz_annos VALUES (?, ?, ?, ?)", [
        (1, 1, 1, known.as_uri()),
        (2, 1, 2, '{"state":1}'),
        (3, 2, 1, stray.as_uri()),
    ])
    db.commit()
    db.close()
    return known, stray


def test_a_download_from_a_known_address_is_matched_and_a_stray_file_is_not(tmp_path):
    """Positive control of the pickup, and its negative twin (exit criterion 2)."""
    registry, manifest = _registry(tmp_path)
    profile = _cookie_profile(tmp_path)
    downloads = tmp_path / "Téléchargements"
    downloads.mkdir()
    known, stray = _places(profile, downloads)
    known.write_bytes(b"%PDF-1.7\nthe plan")
    stray.write_bytes(b"%PDF-1.7\nnot ours")
    orphan = downloads / "no-origin.pdf"
    orphan.write_bytes(b"%PDF-1.7\n?")
    os.utime(known, (1790000000, 1790000000))
    before = sorted((p.name, p.read_bytes()) for p in downloads.iterdir())

    origins = _firefox.download_origins(profile)
    assert origins[known] == "https://walled.example.test/plan.pdf#page=2"
    rows, skipped = collect_downloads(registry, manifest, tmp_path / "store",
                                      downloads, origins)

    assert [r["source_id"] for r in rows] == ["vnm-blocked"]
    row = rows[0]
    assert row["status"] == "collected"
    assert row["collection_method"] == "browser-manual"
    assert row["retrieved_at"] == "2026-09-21T14:13:20Z"
    assert (tmp_path / "store" / row["storage_path"]).read_bytes() == b"%PDF-1.7\nthe plan"
    assert {p.name: reason for p, reason in skipped} == {
        "holiday.pdf": "origin matches no uncollected source",
        "no-origin.pdf": "no download origin recorded by Firefox",
    }
    with manifest.open(newline="", encoding="utf-8") as stream:
        written = list(csv.DictReader(stream))
    assert [r["source_id"] for r in written].count("vnm-blocked") == 2
    assert all(r["final_url"] != stray.as_uri() for r in written)
    # The author's downloads are read, never moved or renamed.
    assert sorted((p.name, p.read_bytes()) for p in downloads.iterdir()) == before


def test_a_download_of_the_wrong_format_is_reported_not_ingested(tmp_path):
    registry, manifest = _registry(tmp_path)
    profile = _cookie_profile(tmp_path)
    downloads = tmp_path / "dl"
    downloads.mkdir()
    known, _ = _places(profile, downloads)
    known.write_bytes(b"<html>challenge page</html>")
    rows, skipped = collect_downloads(registry, manifest, tmp_path / "store", downloads,
                                      _firefox.download_origins(profile))
    assert rows == []
    assert [reason for _, reason in skipped] == ["vnm-blocked: expected PDF magic bytes"]


def test_refreshing_the_collection_tables_from_the_committed_manifest_is_a_no_op(tmp_path):
    """After a collection round the ledger's two tables follow the manifest;
    on the committed manifest the refresh must reproduce them byte for byte."""
    refresh_collection(ROOT / "data/jetp", tmp_path)
    for name in ("retrievals.csv", "snapshots.csv"):
        assert (tmp_path / name).read_bytes() == (ROOT / "data/jetp" / name).read_bytes(), name


def test_a_new_manifest_row_reaches_the_retrievals_table(tmp_path):
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    for name in ("manifest.csv", "retrievals.csv", "snapshots.csv"):
        (ledger / name).write_bytes((ROOT / "data/jetp" / name).read_bytes())
    with (ledger / "retrievals.csv").open(newline="", encoding="utf-8") as stream:
        before = len(list(csv.DictReader(stream)))
    _append_manifest(ledger / "manifest.csv", [_manifest_row(
        "idn-cipp-portal", "blocked", "https://jetp-id.org/cipp",
        http_status="403", error="HTTP 403", collection_method="browser-manual")])
    refresh_collection(ledger, ledger)
    with (ledger / "retrievals.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == before + 1
    # The new attempt follows the manifest's other rows; the local research
    # records stay, after them.
    assert (rows[-3]["document_id"], rows[-3]["collection_method"]) == (
        "idn-cipp-portal", "browser-manual")
    assert [r["collection_method"] for r in rows[-2:]] == ["local-record"] * 2


def test_a_snapshot_no_retrieval_cites_is_dropped_by_the_refresh(tmp_path):
    # The 0926 run first recorded dgMarket's login page, then withdrew that
    # manifest row; its snapshot must not outlive it in the ledger.
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    for name in ("manifest.csv", "retrievals.csv", "snapshots.csv"):
        (ledger / name).write_bytes((ROOT / "data/jetp" / name).read_bytes())
    orphan = "f" * 64
    with (ledger / "snapshots.csv").open("a", encoding="utf-8") as stream:
        stream.write(f"{orphan},objects/ff/{orphan}.html,10,text/html\n")
    refresh_collection(ledger, ledger)
    assert orphan not in (ledger / "snapshots.csv").read_text(encoding="utf-8")
    assert (ledger / "snapshots.csv").read_bytes() == (
        ROOT / "data/jetp/snapshots.csv").read_bytes()


def test_every_committed_snapshot_is_yielded_by_a_retrieval():
    with (ROOT / "data/jetp/retrievals.csv").open(newline="", encoding="utf-8") as stream:
        cited = {r["sha256"] for r in csv.DictReader(stream) if r["sha256"]}
    with (ROOT / "data/jetp/snapshots.csv").open(newline="", encoding="utf-8") as stream:
        snapshots = {r["sha256"] for r in csv.DictReader(stream)}
    assert snapshots - cited == set()


def test_the_committed_registry_records_how_every_collected_row_was_obtained():
    """Exit criterion 3, on the committed manifest and its ledger table."""
    with (ROOT / "data/jetp/manifest.csv").open(newline="", encoding="utf-8") as stream:
        manifest = list(csv.DictReader(stream))
    assert all(row["collection_method"] in COLLECTION_METHODS for row in manifest)
    with (ROOT / "data/jetp/retrievals.csv").open(newline="", encoding="utf-8") as stream:
        retrievals = list(csv.DictReader(stream))
    collected = [r for r in retrievals if r["status"] == "collected"]
    assert collected and all(r["collection_method"] for r in collected)
