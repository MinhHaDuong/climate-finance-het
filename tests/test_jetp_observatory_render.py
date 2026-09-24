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

import csv
import json
import os
import re
import shutil
import subprocess
import tempfile
from functools import cache
from html import unescape
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


def render(route, state=None, expression=None, site=SITE, staged=None):
    """The elements app.js wrote for one route, with a reader's inputs preset.

    ``staged`` is the list of archived copies the server holds, served as
    ``documents/index.json`` (ticket 0915): None renders the public site, which
    holds none, whatever happens to be staged in this checkout.
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the render harness needs it")
    env = dict(os.environ)
    env.pop("JETP_RENDER_STAGED", None)
    with tempfile.TemporaryDirectory() as scratch:
        if staged is not None:
            index = Path(scratch) / "index.json"
            index.write_text(json.dumps({"objects": sorted(staged)}))
            env["JETP_RENDER_STAGED"] = str(index)
        completed = subprocess.run(
            [node, str(HARNESS), str(site), route, json.dumps(state or {}),
             *([expression] if expression else [])],
            capture_output=True, text=True, check=True, timeout=60, env=env,
        )
    return json.loads(completed.stdout)


def served(name):
    return json.loads((SITE / "data" / f"{name}.json").read_text())


@cache
def registry():
    return served("documents")["documents"]


def entry_of(row_key):
    return next(d for d in registry() if d["row_key"] == row_key)


def every_copy():
    """The local preview with every archived copy the registry names staged."""
    return {d["local_path"] for d in registry() if d["local_path"]}


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


def documents_row(source_id, row_key, staged=None):
    """One Documents-page row, found by the search field and the row key.

    The fold-outs arrive after the page's own draw: the renderer fills a
    placeholder by id once the country's stage-two views have loaded, and the
    stub DOM keeps that fill on the element rather than inside the results
    block.  Splice each filled placeholder back where the browser shows it.
    """
    rendered = render("documents", {"documents-search": source_id}, staged=staged)
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


def test_a_failed_attempt_shows_a_short_label_with_the_full_message_in_its_title() -> None:
    # PR #1459 cold read: collector messages run to 300 characters of host
    # names and URLs, which broke mid-token and set the rows' height.  The
    # fold-out column is the wide one; short labels do not wrap.
    failed = next(d for d in registry()
                  if d["error"] and len(d["error"]) > 100 and not d["local_path"])
    results = render("documents", {"documents-search": failed["id"]})["elements"][
        "documents-results"]["innerHTML"]
    row = next(chunk for chunk in re.split(r"(?=<tr>)", results)
               if f"<code>{failed['id']}</code>" in chunk)
    label = re.search(r'<span class="note" data-collection-error title="([^"]*)">([^<]*)</span>', row)
    assert label, row[:500]
    assert unescape(label.group(1)) == failed["error"]
    assert unescape(label.group(2)) == failed["error"].split(":")[0].strip()[:24]
    head = render("documents")["elements"]["documents-results"]["innerHTML"].split("</thead>")[0]
    assert [(w, unescape(t)) for w, t in re.findall(r'<th class="col-(\w+)">([^<]+)</th>', head)] == [
        ("short", "Size"), ("wide", "Entries and items on the record · relied on by")]
    # One column carries the publisher's page, what was read and, where
    # served, the archived copy (ticket 0915): it wraps, so it fits at 1280 px.
    assert "<th>Publisher&#39;s page · what we read</th>" in head, head


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

    row = documents_row(RMP, RMP + ":1", staged=every_copy())

    archived = [href for href, text in anchors(row) if "Open archived copy" in text]
    assert archived == [rmp["local_path"] + "#page=155"], archived
    # The publisher serves a PDF, so its page takes the same fragment.
    publisher = [href for href, text in anchors(row) if text.startswith("Publisher's page")]
    assert publisher == [rmp["url"] + "#page=155"], publisher
    items = re.findall(r"<li>.*?</li>", row, re.DOTALL)
    assert len(items) == len(linked["m1a"])
    assert anchors(items[21]) == [
        ("#entries/VNM?row=22", "vnm-rmp-2023:annex-I.1:022"),
        (rmp["url"] + "#page=156", "publisher's page ↗"),
        (rmp["local_path"] + "#page=156", "archived copy ↗"),
    ], anchors(items[21])


def test_the_public_site_links_the_rmp_to_its_publisher_at_the_same_pages() -> None:
    # Ticket 0915: with no copy served, the same row and the same position
    # open the publisher's PDF at the pages the archived copy would open, and
    # no link points into documents/.
    rmp = entry_of(RMP + ":1")

    row = documents_row(RMP, RMP + ":1")

    assert "documents/" not in "".join(href for href, _ in anchors(row))
    assert [href for href, text in anchors(row) if text.startswith("Publisher's page")] == [
        rmp["url"] + "#page=155"]
    items = re.findall(r"<li>.*?</li>", row, re.DOTALL)
    assert anchors(items[21]) == [
        ("#entries/VNM?row=22", "vnm-rmp-2023:annex-I.1:022"),
        (rmp["url"] + "#page=156", "publisher's page ↗"),
    ], anchors(items[21])
    # The fingerprint of the bytes read stays on the row.
    assert f'data-sha256="{rmp["sha256"]}"' in row


def test_a_document_without_a_page_gets_no_fragment() -> None:
    entry = entry_of(ZAF_REGISTER + ":1")
    linked = climb(ZAF_REGISTER, "ZAF")
    assert not any(r["pdf_page"] for r in linked["m1a"] + linked["ledger"])

    row = documents_row(ZAF_REGISTER, ZAF_REGISTER + ":1", staged=every_copy())

    archived = [href for href, text in anchors(row) if "Open archived copy" in text]
    assert archived == [entry["local_path"]], archived
    publisher = [href for href, text in anchors(row) if text.startswith("Publisher's page")]
    assert publisher == [entry["url"]], publisher


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

    rendered = render("entries/VNM?row=22")

    assert rendered["elements"]["inventory-count"]["textContent"].startswith("1 of 1 ")
    results = rendered["elements"]["inventory-results"]["innerHTML"]
    assert 'data-inventory-row="vnm-rmp-2023:annex-I.1:022"' in results
    assert "<details open>" in results
    # The way back to the whole export is one link away.
    assert 'href="#entries/VNM"' in rendered["main"]


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


def test_a_senegal_annex_row_opens_the_archived_annexes_at_its_own_page() -> None:
    # Ticket 0861: the Senegal annexes print their page numbers at the foot
    # of each page, and on the archived file (dcd4fd92…) printed page N is
    # PDF page N — Annex 2, printed pp. 13-15, sits on PDF pages 13-15; the
    # main plan's quick-win table, printed p. 33, on PDF page 33 of 97c36b24….
    # So row 1 of Annex 2 opens the archived annexes at page 13.
    rows = positions("SEN")
    assert rows[0]["source_row_id"] == "sen-annex-received-01"
    annexes = entry_of("sen-investment-plan-annexes-mirror:1")

    rendered = render("entries/SEN?row=1", staged=every_copy())

    results = rendered["elements"]["inventory-results"]["innerHTML"]
    hrefs = [href for href, _ in anchors(results) if href.startswith(annexes["local_path"])]
    assert hrefs == [annexes["local_path"] + "#page=13"], hrefs
    public = render("entries/SEN?row=1")["elements"]["inventory-results"]["innerHTML"]
    assert [href for href, _ in anchors(public) if href.startswith(annexes["url"])] == [
        annexes["url"] + "#page=13"]
    assert not [href for href, _ in anchors(public) if href.startswith("documents/")]


def test_every_senegal_row_names_a_pdf_page_and_no_other_non_rmp_country_does() -> None:
    # Ticket 0861, verification 1: the 49 Senegal rows carry a PDF page; the
    # Indonesian and South African rows carry none — their locators name a
    # table row or an HTML snapshot, and no page is invented for them.
    sen = positions("SEN")
    assert len(sen) == 49 and all(r["pdf_page"] for r in sen)
    assert not any(r["pdf_page"] for code in ("IDN", "ZAF") for r in positions(code))


# Ticket 0881: the pages are organised by the four objects of
# docs/jetp-language.md (O, D, E, M) without ever naming them, in the newsroom
# vocabulary of docs/jetp-observatory-presentation.md.

# Author, 2026-09-23 (fourth batch): the header holds three sections as tabs;
# the paper trail's steps sit in a second bar, the last three as parallel
# siblings, and About's pages in the same bar as plain siblings.
NAVIGATION = ["The paper trail", "The tallies", "About"]
ABOUT = ["Glossary", "Methods", "Who we are"]
STEPS = ["Documents", "Entries", "On the record", "Projects", "Funding", "Who's who"]
TRAIL_ROUTES = ("documents", "entries", "entries/VNM", "on-the-record", "on-the-record/ZAF",
                "projects", "project/" + BAC_AI, "funding", "funding/VNM", "whos-who")

# The framework's names, the retired terms of docs/jetp-language.md and the
# words docs/jetp-observatory-presentation.md keeps off the pages.  A word
# inside a string the served JSON carries (a document's title, an analyst's
# note, a column name) is the data's, not the page's, and is not counted.
FORBIDDEN = re.compile(
    r"ontolog|evidence|model|layer|reconcil|\bD[1-4]\b|\bstages?\b|\beditions?\b"
    r"|\bfacts?\b|\bclaims?\b|\bdeals?\b|\bplayers?\b|\bsources\b|\bentities\b|\brecords\b",
    re.IGNORECASE,
)
ROUTES = ("overview", "the-paper-trail", "about", "who-we-are", "glossary", "documents", "entries", "on-the-record", "projects",
          "funding", "whos-who", "counts", "methods", "release-history",
          "comparisons", *(f"funding/{code}" for code in COUNTRIES),
          "entries/VNM", "on-the-record/ZAF", "project/" + BAC_AI)


def text_of(html):
    return unescape(re.sub(r"<[^>]+>", " ", html))


@cache
def data_strings():
    """Every string the served JSON carries that holds a forbidden word, keys
    included, with the two transformations the renderer applies to a value
    before showing it (underscores to spaces, Markdown paragraphs)."""
    found = set()

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                found.add(key)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str):
            found.update({value, value.replace("_", " ")})
            # titleBlock() splits a description after its first sentence.
            split = re.match(r"^(.+?[.!?])\s+(.+)$", value, re.DOTALL)
            if split:
                found.update(split.groups())
            found.update(p.removeprefix("## ").replace("\n", " ")
                         for p in re.split(r"\n\n+", value))

    for path in (SITE / "data").rglob("*.json"):
        walk(json.loads(path.read_text()))
    # A bare word ("evidence", a key of reviewed-evidence.json) or a short
    # phrase is not a proper name: excusing it would excuse the page copy's
    # own use of it. What is excused is a title, a note, an identifier.
    excused = {s for s in found if FORBIDDEN.search(s) and len(s) >= 12
               and not re.fullmatch(r"[A-Za-z]+", s)}
    # A term's label is the ledger's own defined word, which the Glossary and
    # every link to it must print verbatim, however short ("edition of").
    terms = json.loads((SITE / "data/ontology/terms.json").read_text())
    label = terms["fields"].index("label")
    excused.update(row[label] for row in terms["rows"] if FORBIDDEN.search(row[label]))
    return sorted(excused, key=len, reverse=True)


def page_copy(html):
    text = text_of(html)
    for value in data_strings():
        if value in text:
            text = text.replace(value, " ")
    return text


def nav_html():
    index = (SITE / "index.html").read_text()
    return re.search(r"<nav[^>]*>.*?</nav>", index, re.DOTALL).group(0)


# Each header tab links to its section's landing page: a landing page at the
# section's slug, or, for The tallies, its first page (fifth batch).
LANDINGS = {"The paper trail": "the-paper-trail", "The tallies": "counts", "About": "about"}
SECTION_KEYS = ("the-paper-trail", "the-tallies", "about")
SUB_PAGES = {
    "the-paper-trail": list(zip(STEPS, ["#documents", "#entries", "#on-the-record", "#projects",
                                        "#funding", "#whos-who"])),
    "the-tallies": [("Counts", "#counts"), ("Comparisons", "#comparisons")],
    "about": [("Glossary", "#glossary"), ("Methods", "#methods"), ("Who we are", "#who-we-are")],
}


def test_the_navigation_follows_glossary_paper_trail_numbers_and_methods() -> None:
    nav = nav_html()
    tabs = re.findall(r'<a href="#([^"]+)" data-section="([^"]+)"[^>]*>([^<]+)</a', nav)
    assert [unescape(label) for *_, label in tabs] == NAVIGATION, tabs
    assert [s for _, s, _ in tabs] == list(SECTION_KEYS)
    assert {unescape(label): href for href, _, label in tabs} == LANDINGS
    # Organised by the objects, which stay in the attributes: nothing for M.
    assert re.findall(r'data-object="([^"]+)"', nav) == ["D", "E", "about"]
    assert 'data-object="M"' not in nav


def test_each_header_tab_has_a_disclosure_of_its_pages() -> None:
    # A disclosure, not a menu widget: a button with aria-expanded controlling
    # a list of links, closed until opened.
    nav = nav_html()
    assert 'role="menu' not in nav
    for section in SECTION_KEYS:
        button = re.search(rf'<button[^>]*id="toggle-{section}"[^>]*>', nav, re.DOTALL).group(0)
        assert 'aria-expanded="false"' in button and f'aria-controls="menu-{section}"' in button
        assert re.search(rf'<ul id="menu-{section}" class="menu" hidden>', nav)
    # One collapsible nav at phone width, with its own disclosure button.
    assert re.search(r'id="nav-toggle"[^>]*aria-expanded="false"[^>]*aria-controls="section-list"',
                     re.sub(r"\s+", " ", nav))
    # app.js fills each list with the section's pages, in order; the paper
    # trail's six steps in trail order.
    elements = render("overview")["elements"]
    for section, pages in SUB_PAGES.items():
        menu = elements[f"menu-{section}"]["innerHTML"]
        links = [(unescape(label), href) for href, label in
                 re.findall(r'<a href="([^"]+)" data-sub="[^"]+">([^<]+)</a>', menu)]
        assert links == pages, (section, links)


def test_a_header_disclosure_toggles_aria_expanded_and_one_menu_is_open_at_a_time() -> None:
    probe = ("[...['the-paper-trail', 'the-tallies', 'about'].map((s) => ["
             "document.getElementById('toggle-' + s).getAttribute('aria-expanded'), "
             "document.getElementById('menu-' + s).getAttribute('hidden')])]")
    opened = render("overview", {}, f"(openMenu('about'), {probe})")["eval"]
    assert opened == [["false", ""], ["false", ""], ["true", None]], opened
    switched = render("overview", {}, f"(openMenu('about'), openMenu('the-tallies'), {probe})")["eval"]
    assert switched == [["false", ""], ["true", None], ["false", ""]], switched
    closed = render("overview", {}, f"(openMenu('about'), closeMenus(), {probe})")["eval"]
    assert closed == [["false", ""], ["false", ""], ["false", ""]], closed


# Author's cold read, 2026-09-23: addresses match labels, and the addresses of
# earlier previews — deep links and queries included — forward to them.
FORWARDS = {
    "countries": "funding",
    "country/VNM": "funding/VNM",
    "evidence": "on-the-record",
    "numbers": "counts",
    "by-the-numbers": "counts",
    "counts-and-totals": "counts",
    "the-tallies": "counts",
    "comparison": "comparisons",
    "historical-comparison": "comparisons",
    "comparison?country=IDN": "comparisons?country=IDN",
    "how-we-did-this": "methods",
    "editions": "release-history",
    "inventory/VNM": "entries/VNM",
    "inventory/VNM?row=22": "entries/VNM?row=22",
    "inventory/ZAF?tab=record": "on-the-record/ZAF",
}
OLD_ADDRESS = re.compile(r'href="#(?:(?:countries|evidence|numbers|by-the-numbers|counts-and-totals'
                         r'|the-tallies|comparison|historical-comparison|how-we-did-this|editions)'
                         r'(?=["?])|(?:country|inventory)/)')


# Author's cold read, third batch (2026-09-23), as revised: "The tallies" is
# one table, a row per computed figure, grouped by country, then two
# numbered figures; it no longer repeats the landing page's stat grid.
TALLY_COLUMNS = ["What it is", "Value", "Unit", "What it covers", "As of", "Computed from"]


def test_the_tallies_are_one_table_grouped_by_country_then_numbered_figures() -> None:
    main = render("the-tallies")["main"]
    assert main.count("<table") == 1
    table = re.search(r'<table class="counts">.*?</table>', main, re.DOTALL).group(0)
    head = re.search(r"<thead>(.*?)</thead>", table, re.DOTALL).group(1)
    assert [unescape(th) for th in re.findall(r">([^<]+)</th>", head)] == TALLY_COLUMNS
    groups = re.findall(r'<tbody data-country="([A-Z]{3})">(.*?)</tbody>', table, re.DOTALL)
    assert [code for code, _ in groups] == list(COUNTRIES)
    for code, body in groups:
        rows = re.findall(r'<tr data-computed-figure="[^"]+" data-country="([A-Z]{3})">(.*?)</tr>',
                          body, re.DOTALL)
        assert rows and {c for c, _ in rows} == {code}, code
        assert all(len(re.findall(r"<td", cells)) == len(TALLY_COLUMNS) for _, cells in rows)
    # Values are the countries' own, never summed: the VNM named-project row
    # is the country view's count.
    vnm = dict(groups)["VNM"]
    named = re.search(r'data-computed-figure="Named projects"[^>]*>(.*?)</tr>', vnm, re.DOTALL).group(1)
    expected = next(c for c in served("overview")["countries"] if c["code"] == "VNM")["named"]
    assert f'<td class="num">{expected}</td>' in named, named
    assert 'href="#projects?country=VNM">Computed from' in named
    # No second homepage: neither the stat grid nor the card panels.
    assert 'class="metrics"' not in main and 'class="stat' not in main and 'class="panel"' not in main
    captions = re.findall(r'<figure class="counts-figure" data-figure="(\d)"><figcaption><strong>'
                          r'(Figure \d\.)</strong>(.*?)</figcaption>', main, re.DOTALL)
    assert [(n, f) for n, f, _ in captions] == [("1", "Figure 1."), ("2", "Figure 2.")]
    assert all("Our calculation" in caption for *_, caption in captions)
    assert 'href="#release-history"' in main


def test_the_homepage_keeps_its_stat_grid_under_the_tallies() -> None:
    main = render("overview")["main"]
    aside = re.search(r'<aside class="evidence-box">.*?</aside>', main, re.DOTALL).group(0)
    assert '<p class="eyebrow">The tallies</p>' in aside
    assert '<a href="#counts">The tallies</a>' in aside
    assert aside.count('class="stat computed"') == 4


@pytest.mark.parametrize("route", ["whos-who", "documents", "project/" + BAC_AI])
def test_no_fold_out_summary_repeats_its_count(route) -> None:
    html = "".join(el["innerHTML"] for el in render(route)["elements"].values())
    summaries_ = [unescape(s) for s in re.findall(r"<summary>([^<]*)</summary>", html)]
    assert summaries_, route
    for summary in summaries_:
        numbers = re.findall(r"\d[\d,]*", summary)
        assert len(numbers) == len(set(numbers)), summary


def test_the_glossary_group_headings_are_sub_heading_size() -> None:
    css = (SITE / "styles.css").read_text()
    rule = re.search(r"\[data-glossary-group\] h2 \{(.*?)\}", css, re.DOTALL).group(1)
    size = int(re.search(r"(\d+)px", rule).group(1))
    h3 = int(re.search(r"^h3 \{\s*font-size: (\d+)px", css, re.MULTILINE).group(1))
    assert size == h3, (size, h3)


GLOSSARY_THEMES = ["What we track", "How documents are read", "Statuses", "Measures", "Relations"]


def glossary_groups(main):
    return re.findall(r'data-glossary-group="([^"]+)"><h2>[^<]*</h2>(.*?)</section>', main, re.DOTALL)


def glossary_entries(html):
    """(term key, label) of each Glossary entry, in page order."""
    return re.findall(r'<dt id="term-[^"]*" data-term="([^"]+)"[^>]*><span class="term-label">([^<]*)</span>', html)


def test_the_glossary_is_grouped_by_theme_and_alphabetical_within_each_group() -> None:
    groups = glossary_groups(render("glossary")["main"])
    assert [unescape(g) for g, _ in groups] == GLOSSARY_THEMES
    for group, body in groups:
        labels = [unescape(label) for _, label in glossary_entries(body)]
        assert len(labels) >= 3 and labels == sorted(labels, key=str.casefold), (group, labels)


@pytest.mark.parametrize(("old", "new"), FORWARDS.items())
def test_an_old_address_forwards_to_its_new_name(old, new) -> None:
    forwarded = render(old, {}, "location.hash")
    assert forwarded["eval"] == "#" + new
    assert forwarded["main"] == render(new)["main"]


@pytest.mark.parametrize("route", ["projects?country=IDN", "project/" + BAC_AI, "documents",
                                   "overview", "entries/SEN?row=1", "methods",
                                   "glossary", "release-history", "about", "who-we-are"])
def test_an_address_that_kept_its_name_does_not_move(route) -> None:
    assert render(route, {}, "location.hash")["eval"] == "#" + route


def test_the_pages_emit_only_the_new_addresses() -> None:
    assert not OLD_ADDRESS.search((SITE / "index.html").read_text())
    for route in ROUTES:
        html = "".join(el["innerHTML"] for el in render(route)["elements"].values())
        assert not OLD_ADDRESS.search(html), (route, OLD_ADDRESS.search(html).group(0))


def step_bar(route):
    return render(route)["elements"].get("step-bar", {}).get("innerHTML", "")


def test_a_page_of_the_paper_trail_shows_its_step_and_links_to_its_neighbours() -> None:
    # The sub-bar is the position indicator (ticket 0881's test, as the
    # author reshaped it on 2026-09-23): the selected tab is the step, and the
    # tabs beside it are the neighbouring steps, each keeping the country.
    bar = step_bar("entries/VNM")
    links = re.findall(r'<li><a href="([^"]+)" data-sub="[^"]+" data-step="(D\d)"'
                       r'( aria-current="page")?>([^<]+)</a></li>', bar)
    assert [unescape(label) for *_, label in links] == STEPS, links
    assert [(href, step) for href, step, current, _ in links if current] == [("#entries/VNM", "D2")]
    hrefs = {unescape(label): href for href, _, _, label in links}
    assert hrefs["Documents"] == "#documents?country=VNM"
    assert hrefs["On the record"] == "#on-the-record/VNM"
    # Six plain sibling tabs: no separator, no grouping of the last three.
    assert "›" not in bar and "siblings" not in bar and bar.count("<li>") == 6
    # The scope is a chip; removing it opens the same step, unscoped.
    chip = re.search(r'<span class="scope-chip">([^<]+)<a href="([^"]+)"', bar)
    assert chip and chip.group(1).strip() == "Viet Nam" and chip.group(2) == "#entries", bar


@pytest.mark.parametrize("route", TRAIL_ROUTES)
def test_a_trail_page_carries_no_second_position_indicator(route) -> None:
    # The step bar replaces the eyebrow, the trail block and the in-page tabs.
    main = render(route)["main"]
    assert 'class="eyebrow"' not in main.split("</div>", 1)[0]
    assert 'class="trail"' not in main and 'role="tablist"' not in main
    assert 'aria-current="page"' in step_bar(route)


@pytest.mark.parametrize(("route", "section"), [
    ("documents", "the-paper-trail"), ("project/" + BAC_AI, "the-paper-trail"),
    ("counts", "the-tallies"), ("comparisons", "the-tallies"), ("glossary", "about")])
def test_every_sub_bar_is_the_same_component(route, section) -> None:
    # Sixth batch: one markup and one class for the three sections' sub-bars,
    # plain tabs, no separators; the country chip is the paper trail's alone.
    bar = step_bar(route)
    assert bar.startswith(f'<ul class="sub-tabs" data-sub-bar="{section}"><li><a href="#'), bar
    tabs = re.findall(r"<li><a [^>]+>([^<]+)</a></li>", bar)
    assert [unescape(t) for t in tabs] == [label for label, _ in SUB_PAGES[section]]
    assert "›" not in bar and "<ol" not in bar
    assert bar.count('aria-current="page"') == 1


@pytest.mark.parametrize("route", ["overview"])
def test_no_second_bar_outside_the_paper_trail_and_about(route) -> None:
    assert step_bar(route) == ""


def test_the_paper_trail_landing_shows_its_steps_with_none_current() -> None:
    bar = step_bar("the-paper-trail")
    assert 'data-step="D1"' in bar and 'aria-current' not in bar


@pytest.mark.parametrize(("route", "current"), [
    ("about", None), ("glossary", "Glossary"), ("methods", "Methods"),
    ("who-we-are", "Who we are"), ("release-history", "Methods")])
def test_about_pages_show_the_about_sub_bar_as_plain_siblings(route, current) -> None:
    bar = step_bar(route)
    links = re.findall(r'<a href="#([^"]+)" data-sub="[^"]+"[^>]*?( aria-current="page")?>([^<]+)</a>', bar)
    assert [unescape(label) for *_, label in links] == ABOUT, bar
    assert [unescape(label) for _, mark, label in links if mark] == ([current] if current else [])
    # Plain siblings: one list item, so no arrow separates them.
    assert bar.count("<li>") == 3 and 'data-sub-bar="about"' in bar and "›" not in bar
    assert "data-step" not in bar
    # The release history is in no bar.
    assert "release-history" not in bar


def test_methods_is_canonical_and_nothing_forwards_in_a_circle() -> None:
    assert render("methods", {}, "location.hash")["eval"] == "#methods"
    for old in ("methods", "how-we-did-this", *FORWARDS):
        chain = render("overview", {}, f"(() => {{ let h = {json.dumps(old)}, seen = []; "
                                       "while (h !== null && seen.length < 5) { seen.push(h); h = forwardOf(h); } "
                                       "return seen; })()")["eval"]
        assert len(chain) <= 2, (old, chain)


# The author's own text for Who we are (supplied 2026-09-23, from his
# homepage bio), kept as written: the page carries these paragraphs, these
# two links, and nothing else about him — no phone, postal or e-mail address.
WHO_WE_ARE = [
    "The JETP Observatory is a research project of Minh Ha-Duong, Directeur de Recherche at CNRS, "
    "working at CIRED (Centre international de recherche sur l'environnement et le développement) "
    "near Paris.",
    "He works on energy, climate change, society, economics and uncertainty. He was a lead author of "
    "the IPCC's Fourth and Fifth Assessment Reports, founded the Vietnam Initiative for the Energy "
    "Transition (VIET) in 2018, and set up the Clean Energy and Sustainable Development lab at the "
    "University of Science and Technology of Hanoi in 2014.",
    "The observatory reads what the four partnerships and their funders publish, archives every "
    "document it relies on, and shows how each figure was reached. Its data and code are open.",
    "Homepage: https://minh.haduong.com · ORCID: https://orcid.org/0000-0001-9988-2100",
]


def test_who_we_are_is_the_authors_text_and_nothing_else() -> None:
    main = render("who-we-are")["main"]
    paragraphs = [re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", p))).strip()
                  for p in re.findall(r"<p[^>]*>(.*?)</p>", main, re.DOTALL)]
    assert paragraphs == WHO_WE_ARE, paragraphs
    assert re.findall(r'href="(https?://[^"]+)"', main) == [
        "https://minh.haduong.com", "https://orcid.org/0000-0001-9988-2100"]
    assert "placeholder" not in main and "@" not in text_of(main)


@pytest.mark.parametrize("route", ["documents", "on-the-record", "entries", "whos-who",
                                   "the-tallies", "methods"])
def test_the_title_block_is_one_sentence_with_the_rest_folded(route) -> None:
    head = re.search(r'<div class="page-head">(.*?)</div>', render(route)["main"], re.DOTALL).group(1)
    lede = re.search(r'<p class="lede">(.*?)</p>', head, re.DOTALL).group(1)
    assert len(re.findall(r"[.!?](\s|$)", lede)) == 1, lede
    if "<details" in head:
        assert re.search(r'<details class="about"><summary>About this page</summary>', head)


def test_a_country_read_from_the_address_cannot_inject_markup_into_the_step_bar() -> None:
    # PR #1459 review: #projects?country=… reached the trail's href unescaped.
    payload = '"><img src=x onerror=alert(1)>'
    bar = step_bar("projects?country=" + payload)
    assert "<img" not in bar, bar
    # An unknown country is no country: the bar falls back to the whole site.
    assert 'href="#entries"' in bar and 'href="#on-the-record"' in bar, bar
    assert "scope-chip" not in bar
    # And the links are escaped even for a code the site knows, so the guard
    # is not the escaping's only line of defence (round 2 of the review).
    known = json.dumps(payload)
    escaped = render("overview", {}, f"overview.countries.push({{code: {known}, name: {known}}}), "
                                     f"subBar('the-paper-trail', 'entries', {known})")["eval"]
    assert "<img" not in escaped and "&lt;img" in escaped, escaped


def test_an_item_on_the_record_reads_according_to_its_publisher_with_the_date() -> None:
    rendered = render("on-the-record/VNM")
    results = rendered["elements"]["observations-results"]["innerHTML"]
    sources = served("VNM")["sources"]
    row = next(r for r in observations("VNM")
               if sources[r["source_id"]].get("publisher") and sources[r["source_id"]].get("date"))
    source = sources[row["source_id"]]
    item = next(chunk for chunk in re.split(r"(?=<tr>)", results) if row["link_id"] in chunk)
    said = re.sub(r"\s+", " ", text_of(item))
    assert f"According to {source['publisher']}, " in said, said
    day, year = int(source["date"][8:]), source["date"][:4]
    assert re.search(rf"According to [^,]+, {day} \w+ {year}", said), said


def test_a_count_on_the_viet_nam_page_is_marked_computed_with_its_unit() -> None:
    main = render("funding/VNM")["main"]
    assert "named projects" in re.findall(r'<div class="metric computed" data-unit="([^"]+)"', main)
    metric = re.search(r'<div class="metric computed" data-unit="named projects">.*?</div>',
                       main, re.DOTALL).group(0)
    assert "Our calculation" in text_of(metric)
    # Its pair: the publisher's headline is marked as published.
    callout = re.search(r'<div class="callout published">.*?</div>', main, re.DOTALL).group(0)
    assert "As published" in text_of(callout)
    assert "Counted by us" not in main
    assert 'href="#projects?country=VNM"' in metric


@pytest.mark.parametrize("route", ROUTES)
def test_the_page_copy_names_no_framework_and_no_retired_term(route) -> None:
    rendered = render(route)
    html = "".join(el["innerHTML"] for el in rendered["elements"].values())
    words = sorted({m.group(0).lower() for m in FORBIDDEN.finditer(page_copy(html))})
    assert not words, (route, words)


def test_the_static_shell_names_no_framework_and_no_retired_term() -> None:
    shell = re.sub(r"<script.*?</script>", "", (SITE / "index.html").read_text(), flags=re.DOTALL)
    meta = " ".join(re.findall(r'content="([^"]+)"', shell))
    words = sorted({m.group(0).lower() for m in FORBIDDEN.finditer(text_of(shell) + " " + meta)})
    assert not words, words



# --- The Glossary, generated from the ontology tables (ticket 0882) -----------
#
# A fixture ledger gives the cases the real one does not have yet: a reworded
# term, a status crosswalk row (the crosswalks are written in ticket 0876).
# Its five tables go through the same builder as the shipped views, into a
# copy of the site, and the shipped app.js renders them.

ZAF_PUBLISHER = "zaf-jet-pmu"


def _term(list_name, term_id, definition, row=1, kind="value", supersedes=None, **extra):
    return {"term_row_id": f"{list_name}.{term_id}.{row}", "term_id": term_id, "kind": kind,
            "list": list_name, "label": term_id.replace("_", " "), "definition": definition,
            "mapping_relation": "local", "recorded_at": f"2026-0{row}-01",
            "decided_by": "fixture", "status": "accepted", "supersedes": supersedes, **extra}


GLOSSARY_FIXTURE = {
    "terms": [
        _term("class", "agreement", "A financing arrangement.", kind="class"),
        _term("class", "project", "A project, programme or component.", kind="class"),
        _term("relation", "finances", "An agreement finances a project.", kind="relation",
              domain="agreement", range="project"),
        _term("axis", "delivery", "The IATI activity status axis."),
        _term("delivery", "closed", "The activity is closed.", external_scheme="IATI",
              external_uri="https://iatistandard.org/en/iati-standard/203/codelists/activitystatus/",
              mapping_relation="closeMatch"),
        _term("mapping_relation", "closeMatch", "Close enough to substitute in most uses."),
        _term("mapping_relation", "local", "Defined for this ledger only."),
        _term("line_classification", "named_item", "A line that names one item."),
        _term("line_classification", "named_item",
              "A line whose publisher names the one item it states.", row=2,
              supersedes="line_classification.named_item.1"),
        _term("money", "signed", "The agreement is signed."),
        _term("measure", "amount", "A sum as its document prints it."),
        dict(_term("measure", "withdrawn_idea", "Never accepted."), status="rejected"),
    ],
    "status_crosswalk": [
        {"crosswalk_row_id": "cw-zaf-d", "publisher_id": ZAF_PUBLISHER,
         "own_status": "D. Completed", "axis": "delivery", "shared_status": "closed",
         "recorded_at": "2026-01-01", "decided_by": "fixture", "status": "accepted"},
    ],
}


@cache
def glossary_site():
    """A copy of the site whose ontology views are built from the fixture."""
    import tempfile

    from jetp import _ledger_headers as ledger_headers
    from jetp.build_ontology_views import write_views

    base = Path(tempfile.mkdtemp(prefix="glossary-0882-"))
    site, ledger = base / "site", base / "ledger"
    shutil.copytree(SITE, site, ignore=shutil.ignore_patterns("documents"))
    schema = ledger_headers.load_schema()
    for table, rows in GLOSSARY_FIXTURE.items():
        path = ledger_headers.table_path(ledger, table)
        path.parent.mkdir(parents=True, exist_ok=True)
        header = schema.header(table)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(header)
            writer.writerows([[row.get(c) or "" for c in header] for row in rows])
    write_views(ledger, site / "data/ontology")
    return site


def fixture_glossary(route="glossary"):
    return render(route, site=glossary_site())["main"]


def entry_of_term(main, key):
    """The <dt>…</dd> pair of one Glossary entry."""
    match = re.search(rf'<dt id="term-[^"]*" data-term="{re.escape(key)}".*?</dd>', main, re.DOTALL)
    assert match, key
    return match.group(0)


def test_every_ontology_table_is_served_one_file_each_with_its_columns_verbatim() -> None:
    from jetp import _ledger_headers as ledger_headers
    from jetp._ontology import ontology_as_of

    schema = ledger_headers.load_schema()
    current = ontology_as_of()
    for table in ledger_headers.ONTOLOGY_TABLES:
        view = served(f"ontology/{ledger_headers.file_stem(table)}")
        assert view["fields"] == schema.header(table), table
        rows, _ = ledger_headers.read_table(ledger_headers.LEDGER_DIR, table, schema)
        # Every row, superseded ones included, as the CSV holds it.
        assert view["rows"] == [list(row) for row in rows], table
        assert view["in_force"] == [row[view["key"]] for row in current[table]], table
    # A table with no row yet is served, empty, not left out.
    assert served("ontology/perimeters")["rows"] == []


def test_the_glossary_renders_each_term_in_force_with_its_definition() -> None:
    main = fixture_glossary()
    in_force = [t for t in GLOSSARY_FIXTURE["terms"]
                if t["status"] == "accepted" and t["term_row_id"] != "line_classification.named_item.1"]
    keys = [key for key, _ in glossary_entries(main)]
    assert sorted(keys) == sorted(f"{t['list']}/{t['term_id']}" for t in in_force)
    for term in in_force:
        entry = text_of(entry_of_term(main, f"{term['list']}/{term['term_id']}"))
        assert term["definition"] in entry, term
    assert "Never accepted." not in main


def test_a_superseded_term_appears_only_in_its_successors_history() -> None:
    main = fixture_glossary()
    old = "A line that names one item."
    assert text_of(main).count(old) == 1
    entry = entry_of_term(main, "line_classification/named_item")
    history = re.search(r'<details class="term-history">.*?</details>', entry, re.DOTALL)
    assert history and old in text_of(history.group(0)), entry


def test_a_relation_shows_what_it_connects() -> None:
    entry = entry_of_term(fixture_glossary(), "relation/finances")
    assert re.search(r"data-domain>.*?agreement.*?</span>", entry), entry
    assert re.search(r"data-range>.*?project.*?</span>", entry), entry
    # The classes it connects are terms too, and link to their entries.
    assert 'href="#glossary?term=class%2Fagreement"' in entry


def test_an_external_mapping_shows_its_scheme_and_skos_relation() -> None:
    entry = entry_of_term(fixture_glossary(), "delivery/closed")
    assert 'href="https://iatistandard.org/' in entry and "IATI" in text_of(entry)
    assert 'href="#glossary?term=mapping_relation%2FcloseMatch"' in entry


def test_a_zaf_status_links_to_its_definition_through_the_crosswalk() -> None:
    rendered = render("entries/ZAF", site=glossary_site())
    results = rendered["elements"]["inventory-results"]["innerHTML"]
    assert re.search(r'<a href="#glossary\?term=delivery%2Fclosed"[^>]*>(<span class="pill">)?'
                     r"D\. Completed", results), results[:2000]
    # The link opens the entry, which shows the definition and the words
    # mapped to it, the publisher's own word among them.
    main = render("glossary?term=delivery%2Fclosed", site=glossary_site())["main"]
    entry = entry_of_term(main, "delivery/closed")
    assert "data-targeted" in entry
    assert "The activity is closed." in text_of(entry)
    crosswalk = re.search(r"<p data-crosswalk>.*?</p>", entry, re.DOTALL).group(0)
    assert "D. Completed" in text_of(crosswalk) and ZAF_PUBLISHER in text_of(crosswalk)


def test_a_status_on_the_record_links_to_its_term() -> None:
    rendered = render("on-the-record/ZAF")
    results = rendered["elements"]["observations-results"]["innerHTML"]
    assert re.search(r'<dt>financial_status</dt><dd><a href="#glossary\?term=money%2Fsigned"',
                     results), results[:2000]


def test_the_shipped_glossary_shows_as_many_entries_as_terms_in_force() -> None:
    from jetp._ontology import ontology_as_of

    current = ontology_as_of()["terms"]
    keys = [key for key, _ in glossary_entries(render("glossary")["main"])]
    assert len(keys) == len(set(keys)) == len(current)


def test_no_hand_written_definition_remains_on_the_glossary() -> None:
    renderer = (SITE / "app.js").read_text()
    assert 'data-glossary="handwritten"' not in renderer
    assert "const GLOSSARY = [" not in renderer
    main = render("glossary")["main"]
    terms = served("ontology/terms")
    definitions = {row[terms["fields"].index("definition")] for row in terms["rows"]}
    for dd in re.findall(r'<p class="term-definition">(.*?)</p>', main, re.DOTALL):
        assert unescape(dd) in definitions, dd
    assert main.count('class="term-definition"') == len(glossary_entries(main))


# Ticket 0915: one site, two audiences. The public bundle is the tracked tree,
# which cannot hold documents/; the local preview is the same tree with the
# archived copies staged and their index served. Links are additive: the
# publisher's page always, the archived copy only where the index lists it.

def test_every_registry_row_links_to_its_publisher_with_what_was_read() -> None:
    # One process, the renderer's own functions over every collection attempt.
    expression = ("documentsData.documents.map((r) => "
                  "[publisherLink(r, null, ''), collectedFacts(r), archivedLink(r)])")

    rendered = render("documents", {}, expression)["eval"]

    assert len(rendered) == len(registry())
    for entry, (publisher, facts, archived) in zip(registry(), rendered, strict=True):
        origin = re.match(r"https?://([^/?#]+)", entry["url"] or "")
        assert origin, (entry["row_key"], "no http(s) address recorded")
        host = origin.group(1)
        assert [(unescape(href), text) for href, text in anchors(publisher)] == [
            (entry["url"], f"Publisher's page — {host} ↗")], (entry["row_key"], publisher)
        if entry["sha256"]:
            assert f'data-sha256="{entry["sha256"]}"' in facts, entry["row_key"]
        else:
            # A failed attempt says so beside the publisher's page it names.
            assert "data-collection-error" in facts, (entry["row_key"], facts)
        assert entry["collected_on"][:4] in facts
        assert archived == "", entry["row_key"]


PUBLIC_ROUTES = ("documents", "entries/ZAF", "entries/IDN", "entries/VNM", "entries/SEN",
                 "on-the-record", "on-the-record/ZAF", "on-the-record/IDN",
                 "project/" + BAC_AI)


@pytest.mark.parametrize("route", PUBLIC_ROUTES)
def test_the_public_site_links_to_no_archived_copy(route) -> None:
    rendered = render(route)
    html = rendered["main"] + "".join(e["innerHTML"] for e in rendered["elements"].values())
    assert 'href="documents/' not in html, route
    assert 'data-link="archived"' not in html, route
    assert 'data-link="publisher"' in html, route


def test_the_preview_links_only_the_copies_its_index_lists() -> None:
    # Two rows whose copies are both in the registry; only one is staged.
    rmp, register = entry_of(RMP + ":1"), entry_of(ZAF_REGISTER + ":1")
    staged = {rmp["local_path"]}
    assert register["local_path"] and register["local_path"] not in staged

    rendered = render("documents", {}, "[documentHref(%s), documentHref(%s)]"
                      % (json.dumps(rmp), json.dumps(register)), staged=staged)

    assert rendered["eval"] == [rmp["local_path"], None]


def test_an_unfingerprinted_row_reaches_the_publisher_but_no_other_attempts_bytes() -> None:
    # Review of PR #1488: a ledger row with no sha256 resolves through its
    # source id for the publisher's link only; even with every copy staged it
    # shows neither an archived link nor another attempt's fingerprint.
    rmp = entry_of(RMP + ":1")
    row = {"locator": "Annex I.1", "source_id": RMP, "sha256": None, "pdf_page": 156,
           "event_id": "fixture"}

    html = render("documents", {}, f"observationEvidence({json.dumps(row)})",
                  staged=every_copy())["eval"]

    assert [(unescape(h), t) for h, t in anchors(html)] == [
        (rmp["url"] + "#page=156", f"Publisher's page — {rmp['url'].split('/')[2]} ↗")], html
    assert "data-sha256" not in html and 'data-link="archived"' not in html
