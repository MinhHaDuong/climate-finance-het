"""Row-to-document resolution for the explorable M1a inventories.

Pure fixtures, no subprocess: this is the fast tier.  The JS port in ``app.js``
is hand-written, so the last test pins the strings that must stay in step with
this module rather than generating one from the other.
"""

import csv
import io
import json
from pathlib import Path

import pytest
from jetp._m1a_document_links import (
    index_documents,
    resolve_document_link,
)

ROOT = Path(__file__).resolve().parents[1]

REGISTRY = {
    "source-a": {"sha256": "aa" * 32},
    "source-b": {"sha256": "bb" * 32},
}

HEADER = (
    "country,source_layer,source_id,source_row_id,label,record_type,"
    "reported_status,identity_status,evidence_locator\n"
)
FIXTURE_CSV = HEADER + (
    'VNM,rmp,source-a,22,KN Tri An Floating Solar Farm,project,2030,named,'
    '"Annex I.1; PDF pages 156; printed pages 140; ordinal 22"\n'
    'VNM,rmp,source-a,23,Grid reinforcement programme,programme,listed,named,'
    '"Appendix 3, row 4"\n'
    'SEN,annex,source-b,4,,component,unknown,unknown,'
    '"Annex 2, p. 13, row 9"\n'
)


def _rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def test_pdf_page_comes_from_the_pdf_locator_never_the_printed_page_or_ordinal() -> None:
    row = _rows(FIXTURE_CSV)[0]

    link = resolve_document_link(row["source_id"], row["evidence_locator"], REGISTRY)

    assert link["sha256"] == "aa" * 32
    assert link["pdf_page"] == 156

    # Every real locator lists the PDF page first, so a pattern weakened to
    # "pages? (number)" would still return 156 on the line above — the leftmost
    # match. Reversed, that weakened pattern returns 140; only an anchored one
    # survives both orders.
    reversed_locator = "Annex I.1; printed pages 140; PDF pages 156; ordinal 22"
    assert (
        resolve_document_link("source-a", reversed_locator, REGISTRY)["pdf_page"] == 156
    )


def test_a_locator_without_a_pdf_page_still_resolves_its_document() -> None:
    for row in _rows(FIXTURE_CSV)[1:]:
        link = resolve_document_link(
            row["source_id"], row["evidence_locator"], REGISTRY
        )
        assert link["pdf_page"] is None
        assert link["sha256"] == REGISTRY[row["source_id"]]["sha256"]


def test_every_row_resolves_exactly_once() -> None:
    rows = _rows(FIXTURE_CSV)

    resolved = [
        (
            resolve_document_link(
                row["source_id"], row["evidence_locator"], REGISTRY
            )["sha256"],
            row["source_row_id"],
        )
        for row in rows
    ]

    assert len(resolved) == 3
    assert len(set(resolved)) == 3


def test_an_unknown_source_id_is_an_error_not_a_silent_blank() -> None:
    with pytest.raises(KeyError):
        resolve_document_link("source-missing", "Appendix 3, row 4", REGISTRY)


def test_a_caller_that_opts_out_of_the_gap_check_gets_a_null_fingerprint() -> None:
    link = resolve_document_link(
        "source-missing", "PDF pages 12", REGISTRY, required=False
    )
    assert link["sha256"] is None
    assert link["local_path"] is None
    assert link["pdf_page"] == 12


def test_a_per_country_extra_column_passes_through_resolution_untouched() -> None:
    widened = FIXTURE_CSV.replace(
        "evidence_locator\n", "evidence_locator,raw_extra_field\n"
    ).replace("ordinal 22\"\n", "ordinal 22\",register value\n")

    rows = _rows(widened)

    assert rows[0]["raw_extra_field"] == "register value"
    link = resolve_document_link(
        rows[0]["source_id"], rows[0]["evidence_locator"], REGISTRY
    )
    assert link["sha256"] == "aa" * 32
    assert link["pdf_page"] == 156


def test_a_shared_source_id_resolves_to_the_collected_archived_row() -> None:
    # Ticket 0853: 21 registry ids carry more than one collection attempt.  The
    # archived copy is what a row link must open, so a collected attempt with a
    # local path wins over a later revalidation or a failed one.
    documents = [
        {"id": "source-a", "status": "blocked", "local_path": None, "sha256": None},
        {
            "id": "source-a",
            "status": "collected",
            "local_path": "documents/objects/aa/a.pdf",
            "sha256": "aa" * 32,
        },
        {
            "id": "source-a",
            "status": "not_modified",
            "local_path": "documents/objects/aa/a.pdf",
            "sha256": "aa" * 32,
        },
    ]

    index = index_documents(documents)

    assert len(index) == 1
    assert index["source-a"]["status"] == "collected"
    assert resolve_document_link("source-a", "PDF page 3", index) == {
        "sha256": "aa" * 32,
        "pdf_page": 3,
        "local_path": "documents/objects/aa/a.pdf",
    }


def test_a_registry_id_collected_but_never_archived_keeps_its_first_entry() -> None:
    index = index_documents(
        [
            {"id": "source-b", "status": "blocked", "local_path": None, "sha256": None},
            {"id": "source-b", "status": "failed", "local_path": None, "sha256": None},
        ]
    )

    assert index["source-b"]["status"] == "blocked"
    assert resolve_document_link("source-b", "Appendix 3", index)["local_path"] is None


def test_every_published_inventory_row_resolves_against_the_published_registry() -> None:
    # The fixtures above hold two registry entries; this reads the four shipped
    # companions and the shipped registry, so a source the collection never
    # recorded cannot reach the page as a row pointing at nothing. Pure file
    # reads, no subprocess: still the fast tier.
    observatory = ROOT / "deliverables" / "jetp-observatory" / "data"
    registry = index_documents(
        json.loads((observatory / "documents.json").read_text(encoding="utf-8"))[
            "documents"
        ]
    )

    resolved = 0
    for code in ("ZAF", "IDN", "VNM", "SEN"):
        payload = json.loads((observatory / "m1a" / f"{code}.json").read_text("utf-8"))
        locator = payload["fields"].index("evidence_locator")
        source = payload["fields"].index("source_id")
        for values in payload["rows"]:
            link = resolve_document_link(values[source], values[locator], registry)
            assert link["sha256"], (code, values[source])
            resolved += 1
    assert resolved == 2164


def test_the_javascript_port_keeps_the_same_contract() -> None:
    renderer = (ROOT / "deliverables" / "jetp-observatory" / "app.js").read_text(
        encoding="utf-8"
    )

    assert "PDF pages? ([0-9]+)" in renderer
    for field in (
        "source_layer",
        "record_type",
        "identity_status",
        "reported_status",
        "label",
    ):
        assert field in renderer
    assert "data/m1a/" in renderer
    assert '"m1a/" + code' in renderer or "`m1a/${code}`" in renderer
    assert "documents/" in renderer
    assert "#page=" in renderer
