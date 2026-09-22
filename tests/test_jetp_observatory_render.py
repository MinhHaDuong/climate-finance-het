"""What the observatory renders, from the shipped app.js against the shipped JSON.

The data tests (``test_jetp_observatory_facts.py`` and its siblings) guard
what the generator writes; these guard what the reader sees, which is where
ticket 0856 found the two stage-two products added into one figure while the
data underneath kept them apart.  ``tests/_jetp_observatory_render.js`` runs
app.js in Node against a stub DOM and prints the HTML it wrote; no browser,
one process per route, well inside the fast-tier budget.  The Chromium recipe
(``tests/browser/jetp_observatory.py``) remains the check that a browser does
the right thing with that HTML.

The climb, document → what cites it, is a join the page makes at read time
on the served tables (ticket 0858): ``m1a/<CODE>.json`` and
``observations/<CODE>.json`` filtered on ``source_id``, the country views'
project sources and the reviewed records' proofs.  So what a Documents row
must show is computed here from those same tables, never from an index in
``documents.json`` — there is none.
"""

import json
import re
import shutil
import subprocess
from functools import cache
from pathlib import Path

import pytest
from jetp._m1a_document_links import pdf_page_of

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables/jetp-observatory"
HARNESS = ROOT / "tests/_jetp_observatory_render.js"
PRE_COMMIT = ROOT / ".githooks/pre-commit"

ZAF_REGISTER = "zaf-jet-investment-register-q1-2026"
RMP = "vnm-rmp-2023"
BAC_AI = "vnm-project-bac-ai-pumped-hydro"
COUNTRIES = ("ZAF", "IDN", "VNM", "SEN")


def render(route, state=None, expression=None):
    """The elements app.js wrote for one route, with a reader's inputs preset."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the render harness needs it")
    completed = subprocess.run(
        [node, str(HARNESS), str(SITE), route, json.dumps(state or {}),
         *([expression] if expression else [])],
        capture_output=True, text=True, check=True, timeout=60,
    )
    return json.loads(completed.stdout)


def served(name):
    return json.loads((SITE / "data" / f"{name}.json").read_text())


@cache
def registry():
    return served("documents")["documents"]


def entry_of(row_key):
    return next(d for d in registry() if d["row_key"] == row_key)


@cache
def positions(code):
    """The M1a rows of one country, each with its rank in the export and the
    page its locator names — read by the Python reference, so the page the
    renderer's port derives is checked against it on the real rows."""
    payload = served(f"m1a/{code}")
    rows = [dict(zip(payload["fields"], values)) for values in payload["rows"]]
    return [dict(row, row=i, pdf_page=pdf_page_of(row["evidence_locator"]))
            for i, row in enumerate(rows, 1)]


@cache
def observations(code):
    return served(f"observations/{code}")


@cache
def projects():
    return [p for code in COUNTRIES for p in served(code)["projects"]]


def climb(source_id, code):
    """What the join must show for one source: its two stage-two products and
    the facts relying on it, as four separate lists."""
    return {
        "m1a": [r for r in positions(code) if r["source_id"] == source_id],
        "ledger": [r for r in observations(code) if r["source_id"] == source_id],
        "projects": [p for p in projects() if source_id in p["sources"]],
        "reviewed": [r for r in served("reviewed-evidence")["records"]
                     if any(e["source_id"] == source_id for e in r["evidence"])],
    }


def documents_row(source_id, row_key):
    """One Documents-page row, found by the search field and the row key.

    The fold-outs arrive after the page's own draw: the renderer fills a
    placeholder by id once the country's stage-two views have loaded, and the
    stub DOM keeps that fill on the element rather than inside the results
    block.  Splice each filled placeholder back where the browser shows it.
    """
    rendered = render("documents", {"documents-search": source_id})
    results = rendered["elements"]["documents-results"]["innerHTML"]
    rows = [chunk for chunk in re.split(r"(?=<tr>)", results)
            if f'data-document-id="{row_key}"' in chunk]
    assert len(rows) == 1, len(rows)
    row = rows[0]
    for element_id in re.findall(r'<span id="([^"]+)"', row):
        filled = rendered["elements"].get(element_id, {}).get("innerHTML")
        if filled:
            row = re.sub(rf'(<span id="{re.escape(element_id)}"[^>]*>).*?</span>',
                         lambda m: m.group(1) + filled + "</span>", row, count=1,
                         flags=re.DOTALL)
    return row


def extracted_foldouts(row):
    """(product, count) of each extracted fold-out, in the order rendered."""
    return re.findall(r'data-extracted-product="([^"]+)" data-extracted-count="(\d+)"', row)


def summaries(row):
    return re.findall(r"<summary>([^<]*)</summary>", row)


def anchors(html):
    """(href, text) of every anchor, in order, the text stripped of its tags."""
    return [(href, re.sub(r"<[^>]+>", "", text))
            for href, text in re.findall(r'<a href="([^"]*)"[^>]*>(.*?)</a>', html)]


def test_the_documents_view_is_a_table_of_collection_attempts_under_the_committed_file_cap() -> None:
    # Ticket 0858, author's decision of 2026-09-22: one served file is one
    # table.  The climb is a read-time join on the views that already serve
    # the rows, so the registry carries no copy of them — no `by_source_id`,
    # no derived key of any kind — and stays under the ceiling the pre-commit
    # hook enforces on every committed file, read from the hook itself.
    view = SITE / "data/documents.json"
    payload = json.loads(view.read_text())
    assert set(payload) == {"documents"}, set(payload)
    assert all("row_key" in row for row in payload["documents"])

    match = re.search(r"^\s*limit=(\d+)\s*$", PRE_COMMIT.read_text(), re.MULTILINE)
    assert match, "the pre-commit hook no longer spells its file-size limit"
    assert view.stat().st_size <= int(match.group(1))


def test_the_documents_page_shows_one_extracted_summary_per_product_never_a_sum() -> None:
    linked = climb(ZAF_REGISTER, "ZAF")
    products = {"ledger": len(linked["ledger"]), "m1a": len(linked["m1a"])}
    # The fixture is only worth its name if the two products are both there.
    assert all(products.values()), products

    row = documents_row(ZAF_REGISTER, ZAF_REGISTER + ":1")

    # One fold-out per product, keyed on the product and carrying its own
    # count — the distinguishing feature, not the label's wording.
    assert extracted_foldouts(row) == [
        ("ledger", str(products["ledger"])), ("m1a", str(products["m1a"])),
    ]
    total = str(sum(products.values()))
    assert not [s for s in summaries(row) if total in s], summaries(row)


def test_a_document_with_one_product_gets_one_fold_out() -> None:
    linked = climb(RMP, "VNM")
    assert linked["m1a"] and not linked["ledger"]

    row = documents_row(RMP, RMP + ":1")

    assert extracted_foldouts(row) == [("m1a", str(len(linked["m1a"])))]


def test_a_document_nothing_was_extracted_from_gets_a_note_not_an_empty_fold_out() -> None:
    # Author's decision, 2026-09-22 (PR #1439 gate): a source that facts rely
    # on but that no ledger row nor M1a row was extracted from says so in one
    # sentence, and gets no "Extracted here · 0" fold-out — an empty list is
    # still a list, and this site never fabricates one (ticket 0839, action 6).
    def cited_only(linked):
        return (linked["projects"] or linked["reviewed"]) and not (linked["m1a"] or linked["ledger"])
    silent = sorted(d["id"] for d in registry() if d["row_key"].endswith(":1")
                    and cited_only(climb(d["id"], d["country"])))
    assert silent, "no shipped source has facts but no extracted row; the fixture is gone"
    source_id = silent[0]
    facts = climb(source_id, entry_of(source_id + ":1")["country"])

    row = documents_row(source_id, source_id + ":1")

    assert extracted_foldouts(row) == [], extracted_foldouts(row)
    assert re.search(r'<p class="note" data-extracted-count="0">[^<]+</p>', row), row
    # The facts side keeps its fold-out: the note replaces one list, not both.
    assert re.findall(r'data-facts-count="(\d+)"', row) == [
        str(len(facts["projects"]) + len(facts["reviewed"])),
    ]


def test_a_document_lists_the_same_project_under_each_of_its_sources() -> None:
    # Ticket 0839's test 3, now on the screen (ticket 0858): a project that
    # cites two collected sources is the same fact on both Documents rows —
    # the same item, structurally, not a substitute that happens to be
    # non-empty.
    collected = {d["id"] for d in registry()}
    project = next(p for p in projects()
                   if len([s for s in p["sources"] if s in collected]) >= 2)
    first, second = [s for s in project["sources"] if s in collected][:2]
    href = f'href="#project/{project["id"]}"'

    items = []
    for source_id in (first, second):
        row = documents_row(source_id, source_id + ":1")
        facts = re.search(r'<details class="foldout" data-facts-count="\d+">.*?</details>',
                          row, re.DOTALL).group(0)
        items.append([li for li in re.findall(r"<li>.*?</li>", facts, re.DOTALL) if href in li])

    assert len(items[0]) == 1 and items[0] == items[1], items
    assert project["name"] in items[0][0]


def test_a_document_shows_what_it_yielded_and_what_relies_on_it_as_lists_never_a_total() -> None:
    # Ticket 0839's test of the two lists, now on the screen (ticket 0858):
    # the register's ledger rows, its M1a rows and the facts relying on it
    # are three counts in three fold-outs, and no summary carries any sum of
    # them.
    linked = climb(ZAF_REGISTER, "ZAF")
    counts = {"ledger": len(linked["ledger"]), "m1a": len(linked["m1a"]),
              "facts": len(linked["projects"]) + len(linked["reviewed"])}
    assert all(counts.values()), counts

    row = documents_row(ZAF_REGISTER, ZAF_REGISTER + ":1")

    assert dict(extracted_foldouts(row)) == {
        "ledger": str(counts["ledger"]), "m1a": str(counts["m1a"]),
    }
    assert re.findall(r'data-facts-count="(\d+)"', row) == [str(counts["facts"])]
    sums = {str(counts["ledger"] + counts["m1a"]), str(counts["ledger"] + counts["facts"]),
            str(counts["m1a"] + counts["facts"]), str(sum(counts.values()))}
    assert not [s for s in summaries(row) if any(total in s for total in sums)], summaries(row)


def test_the_rmp_opens_at_its_first_extracted_page_and_each_position_at_its_own() -> None:
    # Ticket 0857, recipe VN step 1: from the Documents page, the RMP 2023
    # opens at printed page 139, PDF page 155, the first page any of its 279
    # extracted positions names; position 22 (KN Tri An) opens at its own
    # page 156 and links to its own inventory row, not to the whole list.
    rmp = entry_of(RMP + ":1")
    linked = climb(RMP, "VNM")
    pages = sorted({r["pdf_page"] for r in linked["m1a"] if r["pdf_page"]})
    assert pages and pages[0] == 155, pages[:3]
    assert linked["m1a"][21]["source_row_id"] == "vnm-rmp-2023:annex-I.1:022"

    row = documents_row(RMP, RMP + ":1")

    archived = [href for href, text in anchors(row) if "Open archived copy" in text]
    assert archived == [rmp["local_path"] + "#page=155"], archived
    items = re.findall(r"<li>.*?</li>", row, re.DOTALL)
    assert len(items) == len(linked["m1a"])
    assert anchors(items[21]) == [
        ("#inventory/VNM?row=22", "vnm-rmp-2023:annex-I.1:022"),
        (rmp["local_path"] + "#page=156", "PDF page 156 ↗"),
    ], anchors(items[21])


def test_a_document_without_a_page_gets_no_fragment() -> None:
    entry = entry_of(ZAF_REGISTER + ":1")
    linked = climb(ZAF_REGISTER, "ZAF")
    assert not any(r["pdf_page"] for r in linked["m1a"] + linked["ledger"])

    row = documents_row(ZAF_REGISTER, ZAF_REGISTER + ":1")

    archived = [href for href, text in anchors(row) if "Open archived copy" in text]
    assert archived == [entry["local_path"]], archived


def test_the_archived_copy_opens_at_a_first_page_only_when_every_product_agrees() -> None:
    # Ticket 0857's rule, kept where the page is now derived (ticket 0858):
    # each product's first page is the lowest its rows name, and the file
    # gets one only when every product that names a page starts at the same
    # one.  No shipped source disagrees, so the rule is exercised on fixtures
    # through the renderer's own function.
    agree = [{"product": "ledger", "pdf_page": 12}, {"product": "m1a", "pdf_page": 12},
             {"product": "m1a", "pdf_page": 30}]
    disagree = [{"product": "ledger", "pdf_page": 12}, {"product": "m1a", "pdf_page": 30}]
    silent = [{"product": "ledger", "pdf_page": None}, {"product": "m1a"}]
    cases = json.dumps([agree, disagree, silent])

    result = render("documents", {}, f"{cases}.map(firstPdfPage)")["eval"]

    assert result == [12, None, None], result


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
    served_rows = [row for row in observations("VNM") if row["project_id"] == BAC_AI]
    assert served_rows, "Bac Ai has no ledger row; the fixture is gone"

    section = render("project/" + BAC_AI)["elements"]["project-evidence-rows"]["innerHTML"]

    assert re.findall(r'data-evidence-count="([^"]+)"', section) == [str(len(served_rows))]
    assert re.findall(r'data-evidence-row="([^"]+)"', section) == [
        row.get("event_id") or row.get("implementation_event_id") or row["link_id"]
        for row in served_rows
    ]
