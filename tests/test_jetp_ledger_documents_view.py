"""The ledger's documents table served as its own view (ticket 1290).

The Documents page names a document by its title, which only the ledger's
``documents`` table holds for every document: the country views carry it
only for the sources a fact cites, and ``documents.json`` is the retrievals
table alone (ticket 0858).  One file, one table, joined by the page at read
time on the document identifier.
"""

import csv
import json
import re
from pathlib import Path

import pytest
from jetp import build_ledger_documents_view as view
from jetp._ledger_headers import load_schema

pytestmark = pytest.mark.wp_jetp

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables/jetp-observatory"
SERVED = SITE / "data/ledger-documents.json"
PRE_COMMIT = ROOT / ".githooks/pre-commit"
COLUMNS = ["document_id", "country", "document_type", "language", "title",
           "published_date", "edition_of"]


def _ledger(tmp_path, rows):
    header = ("document_id,country,document_type,language,title,url,published_date,"
              "edition_of,active,notes\n")
    (tmp_path / "documents.csv").write_text(header + "".join(rows))
    return tmp_path


def test_the_view_projects_the_reader_columns_in_key_order(tmp_path) -> None:
    ledger = _ledger(tmp_path, [
        "b-doc,SEN,report,fr,Solution Mini-Grid 2025,https://x.example/b,2025,,true,internal note\n",
        'a-doc,IDN,plan,,"Plan, <revised>",https://x.example/a,,,true,\n',
    ])
    # No retrievals table: nothing was collected.
    assert view.build(ledger) == {"documents": [
        dict(document_id="a-doc", country="IDN", document_type="plan", language=None,
             title="Plan, <revised>", published_date=None, edition_of=None,
             collection_state="not_collected"),
        dict(document_id="b-doc", country="SEN", document_type="report", language="fr",
             title="Solution Mini-Grid 2025", published_date="2025", edition_of=None,
             collection_state="not_collected"),
    ]}


def _table(ledger, name, rows):
    """Write one ledger table from dicts, under the header the DDL declares."""
    header = load_schema().header(name)
    with (ledger / f"{name.replace('_', '-')}.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def test_each_document_carries_the_state_of_our_collection_and_reading(tmp_path) -> None:
    # Ticket 1610: derived at build time from the retrievals and the lines,
    # stored nowhere. No snapshot: not collected. A snapshot and no line:
    # collected. Only the minimal line the migration minted to hold a
    # locator (docs/jetp-ledger-migration.md step 3, method=legacy_link in
    # its notes): stub. Any other line: extracted, whatever else it holds.
    # A mirror whose retrieval yielded the same bytes as the read document is
    # in the same state: a line is read from bytes, not from an identifier.
    ledger = _ledger(tmp_path, [
        f"{name},SEN,report,fr,{name},https://x.example/{name},2025,,true,\n"
        for name in ("none", "bytes", "stub", "read", "mixed", "mirror")
    ])
    digest = {name: name[0] * 64 for name in ("bytes", "stub", "read", "mixed")}
    digest["mirror"] = digest["read"]
    _table(ledger, "retrievals", [
        dict(retrieval_id="none:1", document_id="none", retrieved_at="2026-09-12T00:00:00Z",
             status="blocked", error="HTTP 403", collection_method="script"),
        *(dict(retrieval_id=f"{name}:1", document_id=name, retrieved_at="2026-09-12T00:00:00Z",
               status="collected", sha256=digest[name], collection_method="script")
          for name in digest),
    ])
    stub = dict(country="SEN", ordinal=1, classification="named_item", recorded_at="2026-09-24",
                notes="method=legacy_link; version=1; source_id=x; legacy_links=[]")
    read = dict(country="SEN", ordinal=2, classification="named_item", recorded_at="2026-09-24",
                notes="Extracted by hand from the annex")
    _table(ledger, "lines", [
        dict(stub, line_id="stub-discovery-1", sha256=digest["stub"], locator="p. 3"),
        dict(read, line_id="read-1", sha256=digest["read"], locator="p. 4"),
        dict(stub, line_id="mixed-discovery-1", sha256=digest["mixed"], locator="p. 5"),
        dict(read, line_id="mixed-2", sha256=digest["mixed"], locator="p. 6"),
    ])
    states = {row["document_id"]: row["collection_state"]
              for row in view.build(ledger)["documents"]}
    assert states == {"none": "not_collected", "bytes": "collected", "stub": "stub",
                      "read": "extracted", "mixed": "extracted", "mirror": "extracted"}


def test_the_served_view_is_the_committed_table() -> None:
    served = json.loads(SERVED.read_text())
    assert served == view.build(ROOT / "data/jetp")
    assert list(served) == ["documents"]
    assert all(list(row) == COLUMNS + ["collection_state"] for row in served["documents"])
    states = {row["collection_state"] for row in served["documents"]}
    assert states and states <= set(view.STATES), states
    with (ROOT / "data/jetp/documents.csv").open(newline="") as handle:
        titles = {r["document_id"]: r["title"] for r in csv.DictReader(handle)}
    assert {r["document_id"]: r["title"] for r in served["documents"]} == titles


def test_the_served_view_titles_every_collected_document_under_the_file_cap() -> None:
    documents = json.loads((SITE / "data/documents.json").read_text())["documents"]
    titled = {r["document_id"] for r in json.loads(SERVED.read_text())["documents"] if r["title"]}
    assert {d["id"] for d in documents} <= titled
    limit = int(re.search(r"^\s*limit=(\d+)\s*$", PRE_COMMIT.read_text(), re.MULTILINE).group(1))
    # Loaded on every route, so kept far below the hook's ceiling, not just under it.
    assert SERVED.stat().st_size <= limit // 4, SERVED.stat().st_size
