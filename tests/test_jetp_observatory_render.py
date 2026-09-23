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
        ("#entries/VNM?row=22", "vnm-rmp-2023:annex-I.1:022"),
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

    rendered = render("entries/SEN?row=1")

    results = rendered["elements"]["inventory-results"]["innerHTML"]
    hrefs = [href for href, _ in anchors(results) if href.startswith(annexes["local_path"])]
    assert hrefs == [annexes["local_path"] + "#page=13"], hrefs


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

# Author's cold read, 2026-09-23: the header holds the four sections as tabs,
# the Glossary last beside How we did this; the paper trail's steps sit in a
# second bar, the last three as parallel siblings.
NAVIGATION = ["The paper trail", "By the numbers", "Glossary", "How we did this"]
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
ROUTES = ("overview", "the-paper-trail", "glossary", "documents", "entries", "on-the-record", "projects",
          "funding", "whos-who", "by-the-numbers", "how-we-did-this", "release-history",
          "historical-comparison", *(f"funding/{code}" for code in COUNTRIES),
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
    return sorted((s for s in found if FORBIDDEN.search(s) and len(s) >= 12
                   and not re.fullmatch(r"[A-Za-z]+", s)),
                  key=len, reverse=True)


def page_copy(html):
    text = text_of(html)
    for value in data_strings():
        if value in text:
            text = text.replace(value, " ")
    return text


def nav_html():
    index = (SITE / "index.html").read_text()
    return re.search(r"<nav[^>]*>.*?</nav>", index, re.DOTALL).group(0)


def test_the_navigation_follows_glossary_paper_trail_numbers_and_methods() -> None:
    nav = nav_html()
    labels = [unescape(t).strip() for t in re.findall(r">([^<>]+)<", nav) if t.strip()]
    assert labels == NAVIGATION, labels
    # Organised by the objects, which stay in the attributes: nothing for M.
    assert re.findall(r'data-object="([^"]+)"', nav) == ["D", "E", "O", "methods"]
    # Every address is its label's slug.
    for href, label in re.findall(r'<a href="#([^"]+)"[^>]*>([^<]+)<', nav):
        slug = re.sub(r"[^a-z]+", "-", unescape(label).lower().replace("'", "")).strip("-")
        assert href == slug, (href, label)
    assert 'data-object="M"' not in nav


# Author's cold read, 2026-09-23: addresses match labels, and the addresses of
# earlier previews — deep links and queries included — forward to them.
FORWARDS = {
    "countries": "funding",
    "country/VNM": "funding/VNM",
    "evidence": "on-the-record",
    "numbers": "by-the-numbers",
    "comparison": "historical-comparison",
    "comparison?country=IDN": "historical-comparison?country=IDN",
    "methods": "how-we-did-this",
    "editions": "release-history",
    "inventory/VNM": "entries/VNM",
    "inventory/VNM?row=22": "entries/VNM?row=22",
    "inventory/ZAF?tab=record": "on-the-record/ZAF",
}
OLD_ADDRESS = re.compile(r'href="#(countries|country/|evidence|numbers|comparison|methods'
                         r'|editions|inventory/)')


def test_the_glossary_is_grouped_by_theme_and_alphabetical_within_each_group() -> None:
    main = render("glossary")["main"]
    groups = re.findall(r'data-glossary-group="([^"]+)"><h2>[^<]*</h2>(.*?)</section>', main, re.DOTALL)
    assert [unescape(g) for g, _ in groups] == [
        "What we track", "How documents are read", "Statuses", "Measures", "Relations"]
    for group, body in groups:
        terms = [unescape(t) for t in re.findall(r"<dt>([^<]+)</dt>", body)]
        assert len(terms) >= 3 and terms == sorted(terms, key=str.casefold), (group, terms)


@pytest.mark.parametrize(("old", "new"), FORWARDS.items())
def test_an_old_address_forwards_to_its_new_name(old, new) -> None:
    forwarded = render(old, {}, "location.hash")
    assert forwarded["eval"] == "#" + new
    assert forwarded["main"] == render(new)["main"]


@pytest.mark.parametrize("route", ["projects?country=IDN", "project/" + BAC_AI, "documents",
                                   "overview", "entries/SEN?row=1"])
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
    # The step bar is the position indicator (ticket 0881's test, as the cold
    # read reshaped it): the current step is marked, and the neighbouring
    # steps are links in the same bar, each keeping the country.
    bar = step_bar("entries/VNM")
    links = re.findall(r'<a href="([^"]+)" data-step="(D\d)"( aria-current="page")?>([^<]+)</a>', bar)
    assert [unescape(label) for *_, label in links] == STEPS, links
    assert [(href, step) for href, step, current, _ in links if current] == [("#entries/VNM", "D2")]
    hrefs = {unescape(label): href for href, _, _, label in links}
    assert hrefs["Documents"] == "#documents?country=VNM"
    assert hrefs["On the record"] == "#on-the-record/VNM"
    assert re.search(r'<li class="siblings">(<a [^>]+>[^<]+</a>){3}</li>', bar), bar
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


@pytest.mark.parametrize("route", ["overview", "by-the-numbers", "glossary", "how-we-did-this",
                                   "historical-comparison", "the-paper-trail"])
def test_the_step_bar_is_drawn_on_trail_pages_only(route) -> None:
    assert step_bar(route) == ""


@pytest.mark.parametrize("route", ["documents", "on-the-record", "entries", "whos-who",
                                   "by-the-numbers", "how-we-did-this"])
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
                                     f"stepBar('entries', {known})")["eval"]
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
