"""What the observatory renders, from the shipped app.js against the shipped JSON.

The data tests (``test_jetp_observatory_facts.py`` and its siblings) guard
what the generator writes; these guard what the reader sees, which is where
ticket 0856 found the two stage-two products added into one figure while the
data underneath kept them apart.  ``tests/_jetp_observatory_render.js`` runs
app.js in Node against a stub DOM and prints the HTML it wrote; no browser,
one process per route, well inside the fast-tier budget.  The Chromium recipe
(``tests/browser/jetp_observatory.py``) remains the check that a browser does
the right thing with that HTML.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables/jetp-observatory"
HARNESS = ROOT / "tests/_jetp_observatory_render.js"

ZAF_REGISTER = "zaf-jet-investment-register-q1-2026"
RMP = "vnm-rmp-2023"
BAC_AI = "vnm-project-bac-ai-pumped-hydro"


def render(route, state=None):
    """The elements app.js wrote for one route, with a reader's inputs preset."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the render harness needs it")
    completed = subprocess.run(
        [node, str(HARNESS), str(SITE), route, json.dumps(state or {})],
        capture_output=True, text=True, check=True, timeout=60,
    )
    return json.loads(completed.stdout)


def documents_row(source_id, row_key):
    """One Documents-page row, found by the search field and the row key."""
    rendered = render("documents", {"documents-search": source_id})
    results = rendered["elements"]["documents-results"]["innerHTML"]
    rows = [chunk for chunk in re.split(r"(?=<tr>)", results)
            if f'data-document-id="{row_key}"' in chunk]
    assert len(rows) == 1, len(rows)
    return rows[0]


def extracted_foldouts(row):
    """(product, count) of each extracted fold-out, in the order rendered."""
    return re.findall(r'data-extracted-product="([^"]+)" data-extracted-count="(\d+)"', row)


def summaries(row):
    return re.findall(r"<summary>([^<]*)</summary>", row)


def test_the_documents_page_shows_one_extracted_summary_per_product_never_a_sum() -> None:
    index = json.loads((SITE / "data/documents.json").read_text())["by_source_id"]
    products = {}
    for reference in index[ZAF_REGISTER]["extracted"]:
        products[reference["product"]] = products.get(reference["product"], 0) + 1
    # The fixture is only worth its name if the two products are both there.
    assert set(products) == {"ledger", "m1a"}, products

    row = documents_row(ZAF_REGISTER, ZAF_REGISTER + ":1")

    # One fold-out per product, keyed on the product and carrying its own
    # count — the distinguishing feature, not the label's wording.
    assert extracted_foldouts(row) == [
        ("ledger", str(products["ledger"])), ("m1a", str(products["m1a"])),
    ]
    total = str(sum(products.values()))
    assert not [s for s in summaries(row) if total in s], summaries(row)


def test_a_document_with_one_product_gets_one_fold_out() -> None:
    index = json.loads((SITE / "data/documents.json").read_text())["by_source_id"]
    products = {reference["product"] for reference in index[RMP]["extracted"]}
    assert products == {"m1a"}, products

    row = documents_row(RMP, RMP + ":1")

    assert extracted_foldouts(row) == [("m1a", str(len(index[RMP]["extracted"])))]


def anchors(html):
    """(href, text) of every anchor, in order."""
    return re.findall(r'<a href="([^"]*)"[^>]*>([^<]*)<', html)


def test_the_rmp_opens_at_its_first_extracted_page_and_each_position_at_its_own() -> None:
    # Ticket 0857, recipe VN step 1: from the Documents page, the RMP 2023
    # opens at printed page 139, PDF page 155, the first page any of its 279
    # extracted positions names; position 22 (KN Tri An) opens at its own
    # page 156 and links to its own inventory row, not to the whole list.
    registry = json.loads((SITE / "data/documents.json").read_text())
    index = registry["by_source_id"]
    rmp = next(d for d in registry["documents"] if d["row_key"] == RMP + ":1")
    positions = [r for r in index[RMP]["extracted"] if r["product"] == "m1a"]
    pages = sorted({r["pdf_page"] for r in positions if "pdf_page" in r})
    assert pages and pages[0] == 155, pages[:3]
    assert positions[21]["source_row_id"] == "vnm-rmp-2023:annex-I.1:022"

    row = documents_row(RMP, RMP + ":1")

    archived = [href for href, text in anchors(row) if "Open archived copy" in text]
    assert archived == [rmp["local_path"] + "#page=155"], archived
    items = re.findall(r"<li>.*?</li>", row)
    assert len(items) == len(positions)
    assert anchors(items[21]) == [
        ("#inventory/VNM?row=22", "vnm-rmp-2023:annex-I.1:022"),
        (rmp["local_path"] + "#page=156", "PDF page 156 ↗"),
    ], anchors(items[21])


def test_a_document_without_a_page_gets_no_fragment() -> None:
    registry = json.loads((SITE / "data/documents.json").read_text())
    entry = next(d for d in registry["documents"] if d["row_key"] == ZAF_REGISTER + ":1")
    assert not any("pdf_page" in r for r in registry["by_source_id"][ZAF_REGISTER]["extracted"])

    row = documents_row(ZAF_REGISTER, ZAF_REGISTER + ":1")

    archived = [href for href, text in anchors(row) if "Open archived copy" in text]
    assert archived == [entry["local_path"]], archived


def test_the_inventory_page_opens_on_the_row_the_documents_page_cites() -> None:
    payload = json.loads((SITE / "data/m1a/VNM.json").read_text())
    rows = [dict(zip(payload["fields"], values)) for values in payload["rows"]]
    assert rows[21]["source_row_id"] == "vnm-rmp-2023:annex-I.1:022"

    rendered = render("inventory/VNM?row=22")

    assert rendered["elements"]["inventory-count"]["textContent"].startswith("1 of 1 ")
    results = rendered["elements"]["inventory-results"]["innerHTML"]
    assert 'data-inventory-row="vnm-rmp-2023:annex-I.1:022"' in results
    assert "<details open>" in results
    # The way back to the whole export is one link away.
    assert 'href="#inventory/VNM"' in rendered["main"]


def test_a_fact_page_lists_the_observations_view_rows_addressed_to_it() -> None:
    # Ticket 0855: the fold-out is the observations view filtered on the
    # project, fetched by the page, not a copy carried by the country view.
    served = [row for row in json.loads((SITE / "data/observations/VNM.json").read_text())
              if row["project_id"] == BAC_AI]
    assert served, "Bac Ai has no ledger row; the fixture is gone"

    section = render("project/" + BAC_AI)["elements"]["project-evidence-rows"]["innerHTML"]

    assert re.findall(r'data-evidence-count="([^"]+)"', section) == [str(len(served))]
    assert re.findall(r'data-evidence-row="([^"]+)"', section) == [
        row.get("event_id") or row.get("implementation_event_id") or row["link_id"]
        for row in served
    ]
