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
    assert view.build(ledger) == {"documents": [
        dict(document_id="a-doc", country="IDN", document_type="plan", language=None,
             title="Plan, <revised>", published_date=None, edition_of=None),
        dict(document_id="b-doc", country="SEN", document_type="report", language="fr",
             title="Solution Mini-Grid 2025", published_date="2025", edition_of=None),
    ]}


def test_the_served_view_is_the_committed_table() -> None:
    served = json.loads(SERVED.read_text())
    assert served == view.build(ROOT / "data/jetp")
    assert list(served) == ["documents"]
    assert all(list(row) == COLUMNS for row in served["documents"])
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
