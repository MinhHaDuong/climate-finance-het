"""Contracts for the versioned JETP document corpus (ticket 0716)."""

import csv
import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import requests
from jetp.corpus_harvest_documents import harvest_registry, load_registry
from jetp.schemas import validate_event_record, validate_implementation_event_record

REGISTRY_FIELDS = [
    "source_id",
    "country",
    "authority_category",
    "publisher",
    "source_type",
    "title",
    "published_date",
    "url",
    "project_id",
    "expected_format",
    "priority",
    "active",
    "notes",
]


def _write_registry(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=REGISTRY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _source(**overrides: str) -> dict[str, str]:
    row = {
        "source_id": "vnm-rmp",
        "country": "VNM",
        "authority_category": "national_government",
        "publisher": "Government of Viet Nam",
        "source_type": "investment_plan",
        "title": "Resource Mobilisation Plan",
        "published_date": "2023-12-01",
        "url": "https://example.test/rmp.pdf",
        "project_id": "",
        "expected_format": "pdf",
        "priority": "1",
        "active": "true",
        "notes": "",
    }
    row.update(overrides)
    return row


@dataclass
class FakeResponse:
    status_code: int
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    url: str = "https://example.test/rmp.pdf"

    def iter_content(self, chunk_size: int):
        del chunk_size
        yield self.body

    def close(self) -> None:
        return None


class FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_registry_rejects_country_outside_the_four_jetps(tmp_path):
    registry = tmp_path / "sources.csv"
    _write_registry(registry, [_source(country="DEU")])

    with pytest.raises(ValueError, match="country"):
        load_registry(registry)


def test_canonical_registry_has_a_plan_document_for_each_jetp_country():
    registry = Path(__file__).parents[1] / "data" / "jetp" / "sources.csv"
    rows = load_registry(registry)
    plan_types = {"investment_plan", "implementation_plan"}

    covered = {
        row["country"]
        for row in rows
        if row["source_type"] in plan_types
        and row["expected_format"] == "pdf"
        and row["active"] == "true"
    }

    assert covered == {"ZAF", "IDN", "VNM", "SEN"}


def test_event_schema_rejects_unknown_financial_status():
    event = {
        "country": "VNM",
        "scope": "jetp_strict",
        "financial_status": "money_somewhere",
        "amount_original": "67",
        "currency_original": "EUR",
    }

    with pytest.raises(ValueError, match="financial_status"):
        validate_event_record(event)


def test_implementation_event_schema_keeps_physical_status_separate():
    event = {
        "country": "IDN",
        "implementation_status": "retired",
        "capacity_mw": "660",
    }
    validate_implementation_event_record(event)

    event["implementation_status"] = "money_committed"
    with pytest.raises(ValueError, match="implementation_status"):
        validate_implementation_event_record(event)


def test_canonical_implementation_events_reference_known_objects():
    data = Path(__file__).parents[1] / "data" / "jetp"
    with (data / "implementation-events.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        events = list(csv.DictReader(stream))
    with (data / "projects.csv").open(newline="", encoding="utf-8") as stream:
        project_ids = {row["project_id"] for row in csv.DictReader(stream)}
    with (data / "sources.csv").open(newline="", encoding="utf-8") as stream:
        source_ids = {row["source_id"] for row in csv.DictReader(stream)}

    assert len({row["implementation_event_id"] for row in events}) == len(events)
    assert {row["project_id"] for row in events} <= project_ids
    assert {row["source_id"] for row in events} <= source_ids
    for event in events:
        validate_implementation_event_record(event)


def test_harvest_versions_changed_content_and_uses_conditional_get(tmp_path):
    registry = tmp_path / "sources.csv"
    manifest = tmp_path / "manifest.csv"
    store = tmp_path / "documents"
    _write_registry(registry, [_source()])
    first = FakeResponse(
        200,
        b"%PDF-1.7 first version",
        {"Content-Type": "application/pdf", "ETag": '"v1"'},
    )
    second = FakeResponse(
        200,
        b"%PDF-1.7 second version",
        {"Content-Type": "application/pdf", "ETag": '"v2"'},
    )

    harvest_registry(
        registry,
        manifest,
        store,
        retrieved_at="2026-09-11T21:00:00Z",
        session=FakeSession([first]),
    )
    session = FakeSession([second])
    harvest_registry(
        registry,
        manifest,
        store,
        retrieved_at="2026-09-12T21:00:00Z",
        session=session,
    )

    rows = _read_manifest(manifest)
    assert [row["status"] for row in rows] == ["collected", "collected"]
    assert rows[0]["sha256"] != rows[1]["sha256"]
    assert len(list(store.glob("objects/*/*.pdf"))) == 2
    assert session.calls[0][1]["headers"]["If-None-Match"] == '"v1"'
    assert b"\r\n" not in manifest.read_bytes()


def test_not_modified_reuses_prior_object_without_body_download(tmp_path):
    registry = tmp_path / "sources.csv"
    manifest = tmp_path / "manifest.csv"
    store = tmp_path / "documents"
    _write_registry(registry, [_source()])
    first_session = FakeSession(
        [
            FakeResponse(
                200,
                b"%PDF-1.7 stable",
                {"Content-Type": "application/pdf", "ETag": '"stable"'},
            )
        ]
    )
    harvest_registry(
        registry,
        manifest,
        store,
        retrieved_at="2026-09-11T21:00:00Z",
        session=first_session,
    )
    second_session = FakeSession([FakeResponse(304)])
    harvest_registry(
        registry,
        manifest,
        store,
        retrieved_at="2026-09-12T21:00:00Z",
        session=second_session,
    )

    rows = _read_manifest(manifest)
    assert rows[-1]["status"] == "not_modified"
    assert rows[-1]["sha256"] == rows[0]["sha256"]
    assert len(list(store.glob("objects/*/*.pdf"))) == 1
    assert second_session.calls[0][1]["headers"]["If-None-Match"] == '"stable"'


def test_harvest_can_target_one_registered_source(tmp_path):
    registry = tmp_path / "sources.csv"
    manifest = tmp_path / "manifest.csv"
    store = tmp_path / "documents"
    _write_registry(
        registry,
        [
            _source(source_id="vnm-rmp"),
            _source(source_id="sen-plan", country="SEN"),
        ],
    )

    harvest_registry(
        registry,
        manifest,
        store,
        source_ids={"sen-plan"},
        retrieved_at="2026-09-11T21:00:00Z",
        session=FakeSession([FakeResponse(200, b"%PDF-1.7 Senegal")]),
    )

    assert [row["source_id"] for row in _read_manifest(manifest)] == ["sen-plan"]


def test_harvest_rejects_unknown_target_source(tmp_path):
    registry = tmp_path / "sources.csv"
    manifest = tmp_path / "manifest.csv"
    _write_registry(registry, [_source()])

    with pytest.raises(ValueError, match="unknown source_id"):
        harvest_registry(
            registry,
            manifest,
            tmp_path / "documents",
            source_ids={"not-registered"},
            session=FakeSession([]),
        )


@pytest.mark.parametrize(
    ("response", "expected_status"),
    [
        (FakeResponse(403), "blocked"),
        (FakeResponse(404), "missing"),
        (
            FakeResponse(200, b"<html>login</html>", {"Content-Type": "text/html"}),
            "invalid_content",
        ),
        (requests.ConnectionError("offline"), "fetch_error"),
    ],
)
def test_failures_are_explicit_and_never_stored(response, expected_status, tmp_path):
    registry = tmp_path / "sources.csv"
    manifest = tmp_path / "manifest.csv"
    store = tmp_path / "documents"
    _write_registry(registry, [_source()])

    harvest_registry(
        registry,
        manifest,
        store,
        retrieved_at="2026-09-11T21:00:00Z",
        session=FakeSession([response]),
    )

    rows = _read_manifest(manifest)
    assert rows[0]["status"] == expected_status
    assert rows[0]["storage_path"] == ""
    assert list(store.glob("objects/**/*")) == []


@pytest.mark.integration
def test_cli_harvests_from_a_local_http_server(tmp_path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"%PDF-1.7 local fixture"
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("ETag", '"fixture"')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    registry = tmp_path / "sources.csv"
    manifest = tmp_path / "manifest.csv"
    store = tmp_path / "documents"
    url = f"http://127.0.0.1:{server.server_port}/report.pdf"
    _write_registry(registry, [_source(url=url)])
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "scripts:libs/openalex-corpus/src"
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/jetp/corpus_harvest_documents.py",
                "--input",
                str(registry),
                "--output",
                str(manifest),
                "--storage-root",
                str(store),
                "--retrieved-at",
                "2026-09-11T21:00:00Z",
            ],
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

    assert result.returncode == 0, result.stderr
    rows = _read_manifest(manifest)
    assert rows[0]["status"] == "collected"
    assert (store / rows[0]["storage_path"]).read_bytes().startswith(b"%PDF-")
