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


pytestmark = pytest.mark.wp_jetp

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


def web_copy(entry, page, label="Web Archive copy"):
    """The Web Archive anchor the page draws beside a PDF's publisher link, as
    (href, text), from the served capture table (ticket 0925); [] where none."""
    capture = next((c for c in served("web-archive")["captures"]
                    if c["url"] == entry["url"] and c["outcome"] in ("captured", "reused")), None)
    if capture is None:
        return []
    stamp = re.search(r"/web/([0-9]{14})/", capture["capture_url"]).group(1)
    href = capture["capture_url"].replace(f"/web/{stamp}/", f"/web/{stamp}id_/", 1)
    return [(href + (f"#page={page}" if page else ""), label + " ↗")]


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
        ("short", "Size"), ("wide", "Document rows and statements · relied on by")]
    assert "<th>Publisher&#39;s page · what we read</th>" in head, head


# Ticket 1210, author's decisions of 2026-09-25. documents.json stays one row
# per retrieval attempt; the page groups them, one row per document.

def attempts_by_document():
    """Each document's attempts in time order, and its best one: the latest
    collected attempt if any, otherwise the latest attempt — computed here from
    the served table, independently of the renderer."""
    grouped = {}
    for entry in registry():
        grouped.setdefault(entry["id"], []).append(entry)
    out = {}
    for source_id, attempts in grouped.items():
        attempts.sort(key=lambda r: (r["collected_on"] or "", int(r["row_key"].rsplit(":", 1)[1])))
        collected = [r for r in attempts if r["status"] == "collected"]
        out[source_id] = ((collected or attempts)[-1], attempts)
    return out


def document_rows(results, source_id=None):
    """The table rows of a Documents page, or those of one document: a search
    also matches the documents whose identifier extends the one searched."""
    return [chunk for chunk in re.split(r"(?=<tr>)", results) if chunk.startswith("<tr>")
            and (source_id is None or f"<code>{source_id}</code>" in chunk)]


def attempts_summary(row):
    match = re.search(r'<details class="attempts"[^>]*><summary>([^<]*)</summary>', row)
    return unescape(match.group(1)) if match else None


def test_the_documents_page_shows_one_row_per_document_on_its_best_attempt() -> None:
    expected = attempts_by_document()
    assert any(len(a) > 1 for _, a in expected.values()), "no document has several attempts"

    rendered = render("documents", {}, "documentRows(documentsData.documents)"
                      ".map((r) => [r.id, r.row_key, r.attempts.map((a) => a.row_key)])")

    assert rendered["eval"] == [
        [source_id, best["row_key"], [a["row_key"] for a in attempts]]
        for source_id, (best, attempts) in expected.items()]
    # The count line counts documents, not attempts.
    count = rendered["elements"]["documents-count"]["textContent"]
    assert count.startswith(f"{len(expected)} of {len(expected)} documents"), count


def test_a_blocked_then_collected_document_is_one_row_with_its_attempts_folded() -> None:
    best, attempts = attempts_by_document()["idn-cipp-2023"]
    assert [a["status"] for a in attempts] == ["blocked", "blocked", "collected"]

    results = render("documents", {"documents-search": "idn-cipp-2023"})["elements"][
        "documents-results"]["innerHTML"]

    rows = document_rows(results, "idn-cipp-2023")
    assert len(rows) == 1, len(rows)
    row = rows[0]
    assert f'data-document-id="{best["row_key"]}"' in row
    assert f'data-sha256="{best["sha256"]}"' in row
    assert attempts_summary(row) == (
        "3 attempts: 403 on 11 Sept 20:39, 403 on 11 Sept 20:42, collected on 24 Sept 20:22")
    # Nothing hidden: every attempt is listed under the fold, by its row key.
    assert re.findall(r'data-attempt="([^"]+)"', row) == [a["row_key"] for a in attempts]


def test_a_document_read_once_gets_no_attempts_fold() -> None:
    once = next(best for best, attempts in attempts_by_document().values()
                if len(attempts) == 1 and best["sha256"])
    results = render("documents", {"documents-search": once["id"]})["elements"][
        "documents-results"]["innerHTML"]
    row = next(r for r in document_rows(results, once["id"]))
    assert attempts_summary(row) is None


def test_the_status_filter_counts_documents_on_their_best_attempt() -> None:
    expected = attempts_by_document()
    blocked = sorted(i for i, (best, _) in expected.items() if best["status"] == "blocked")
    # The fixture only bites if some document was blocked before it was collected.
    assert any(any(a["status"] == "blocked" for a in attempts) and best["status"] == "collected"
               for best, attempts in expected.values())

    elements = render("documents", {"documents-filter-status": "blocked"})["elements"]

    count = elements["documents-count"]["textContent"]
    assert count.startswith(f"{len(blocked)} of {len(expected)} documents"), count
    shown = re.findall(r"<code>([^<]+)</code></td>", elements["documents-results"]["innerHTML"])
    assert len(blocked) <= 50 and sorted(shown) == blocked
    assert "idn-cipp-2023" not in shown


# Ticket 1290, author's decision of 2026-09-25 ("Titles now"): a Documents row
# names the document by its title, from the ledger's documents table served as
# data/ledger-documents.json, with the identifier kept on a second line.

def document_cell(row):
    """The first cell of a Documents row: (title or None, identifier)."""
    cell = re.match(r"<tr><td>(.*?)</td>", row, re.DOTALL).group(1)
    title = re.search(r"<span data-document-title>([^<]*)</span>", cell)
    ident = re.search(r"<code>([^<]*)</code>$", cell)
    return (unescape(title.group(1)) if title else None, unescape(ident.group(1)))


def test_a_document_titled_only_in_the_ledger_shows_its_title_above_its_identifier() -> None:
    # Positive control: no country view names idn-cipp-2023, so only the
    # ledger's documents table can title it.
    assert not any("idn-cipp-2023" in served(code)["sources"] for code in COUNTRIES)
    titles = {r["document_id"]: r["title"] for r in served("ledger-documents")["documents"]}
    assert titles["idn-cipp-2023"] == "Comprehensive Investment and Policy Plan"

    for source_id in ("idn-cipp-2023", "sen-offgrid-mini-grid-2025"):
        results = render("documents", {"documents-search": source_id})["elements"][
            "documents-results"]["innerHTML"]
        rows = document_rows(results, source_id)
        assert len(rows) == 1, len(rows)
        assert document_cell(rows[0]) == (titles[source_id], source_id)


def test_every_document_row_shows_its_ledger_title() -> None:
    titles = {r["document_id"]: r["title"] for r in served("ledger-documents")["documents"]}
    shown = render("documents", {}, "documentRows(documentsData.documents)"
                   ".map((r) => documentName(r))")["eval"]
    ids = list(attempts_by_document())
    assert len(shown) == len(ids)
    assert [document_cell(f"<tr><td>{cell}</td>") for cell in shown] == [
        (titles[i], i) for i in ids]


def test_the_search_matches_a_title() -> None:
    elements = render("documents", {"documents-search": "solution mini-grid"})["elements"]
    shown = re.findall(r"<code>([^<]+)</code></td>", elements["documents-results"]["innerHTML"])
    assert "sen-offgrid-mini-grid-2025" in shown, shown
    assert "Search document titles" in render("documents")["main"]


def test_an_untitled_document_falls_back_to_its_identifier_and_titles_are_escaped(tmp_path) -> None:
    site = tmp_path / "site"
    shutil.copytree(SITE, site, ignore=shutil.ignore_patterns("documents"))
    view = site / "data/ledger-documents.json"
    payload = json.loads(view.read_text())
    payload["documents"] = [
        dict(r, title='<img src=x onerror="alert(1)"> & Co') if r["document_id"] == "idn-cipp-2023"
        else r for r in payload["documents"] if r["document_id"] != "sen-offgrid-mini-grid-2025"]
    view.write_text(json.dumps(payload))

    def cell(source_id):
        results = render("documents", {"documents-search": source_id}, site=site)["elements"][
            "documents-results"]["innerHTML"]
        row = document_rows(results, source_id)[0]
        return re.match(r"<tr><td>(.*?)</td>", row, re.DOTALL).group(1)

    assert cell("sen-offgrid-mini-grid-2025") == "<code>sen-offgrid-mini-grid-2025</code>"
    escaped = cell("idn-cipp-2023")
    assert "<img" not in escaped
    assert document_cell(f"<tr><td>{escaped}</td>") == (
        '<img src=x onerror="alert(1)"> & Co', "idn-cipp-2023")


def test_the_documents_page_renders_without_the_titles_view(tmp_path) -> None:
    # A site missing the view still lists every document, by identifier.
    site = tmp_path / "site"
    shutil.copytree(SITE, site, ignore=shutil.ignore_patterns("documents"))
    (site / "data/ledger-documents.json").unlink()
    elements = render("documents", {}, site=site)["elements"]
    n = len(attempts_by_document())
    assert elements["documents-count"]["textContent"].startswith(f"{n} of {n} documents")
    assert "data-document-title" not in elements["documents-results"]["innerHTML"]


def test_a_document_gone_before_collection_says_so_and_is_dead_since_the_first_404() -> None:
    # The author's mock: the publisher link is dead since our own first 404
    # (13 Sep), not since the link check that confirmed it (24 Sep); no copy,
    # said plainly; both attempts folded.
    source_id = "sen-offgrid-mini-grid-2025"
    best, attempts = attempts_by_document()[source_id]
    assert [a["error"] for a in attempts] == ["HTTP 404", "HTTP 404"]
    checks = {c["url"]: c for c in served("publisher-links")["checks"]}
    assert checks[best["url"]]["outcome"] == "dead"
    assert checks[best["url"]]["dead_since"] > "2026-09-13"

    results = render("documents", {"documents-search": source_id})["elements"][
        "documents-results"]["innerHTML"]

    rows = document_rows(results, source_id)
    assert len(rows) == 1, len(rows)
    row = rows[0]
    text = unescape(re.sub(r"<[^>]+>", "", row))
    assert 'data-dead-since="2026-09-13"' in row
    assert "publisher link dead (404) since 13 Sept 2026" in text
    assert "No copy: the file was already gone when we tried to collect it." in text
    assert "Collected " not in text
    assert attempts_summary(row) == "2 attempts: 404 on 13 Sept 08:46, 404 on 13 Sept 09:14"


DEAD_SINCE = """(() => {
  const url = "https://p.example/x.pdf";
  const attempt = (n, at, status, error, sha256 = null) =>
    ({ id: "x", row_key: "x:" + n, url, collected_on: at, status, error, sha256 });
  const cases = {
    earlier_404: [[attempt(1, "2026-09-13T08:46:00Z", "missing", "HTTP 404")],
                  { outcome: "dead", dead_since: "2026-09-24", http_status: "404" }],
    earlier_check: [[attempt(1, "2026-09-13T08:46:00Z", "missing", "HTTP 410")],
                    { outcome: "dead", dead_since: "2026-09-10", http_status: "410" }],
    reset_by_success: [[attempt(1, "2026-09-01T00:00:00Z", "missing", "HTTP 404"),
                        attempt(2, "2026-09-05T00:00:00Z", "collected", null, "aa"),
                        attempt(3, "2026-09-20T00:00:00Z", "missing", "HTTP 404")],
                       { outcome: "dead", dead_since: "2026-09-24", http_status: "404" }],
    forbidden_is_not_gone: [[attempt(1, "2026-09-13T08:46:00Z", "blocked", "HTTP 403")],
                            { outcome: "dead", dead_since: "2026-09-24", http_status: "404" }],
    unreachable: [[attempt(1, "2026-09-13T08:46:00Z", "missing", "HTTP 404")],
                  { outcome: "unreachable", dead_since: null, http_status: null }],
    alive: [[attempt(1, "2026-09-13T08:46:00Z", "missing", "HTTP 404")],
            { outcome: "alive", dead_since: null, http_status: "200" }],
  };
  return Object.fromEntries(Object.entries(cases).map(([name, [attempts, check]]) => {
    linkChecks = { [url]: { url, checked_at: "2026-09-24T15:00:00Z", ...check } };
    goneAttempts = indexGone(attempts);
    return [name, deadSince({ url })];
  }));
})()"""


def test_dead_since_is_the_earliest_evidence_and_unreachable_is_never_dead() -> None:
    assert render("documents", {}, DEAD_SINCE)["eval"] == {
        "earlier_404": "2026-09-13",
        "earlier_check": "2026-09-10",
        # A later collection proves the file was back: the run restarts.
        "reset_by_success": "2026-09-20",
        "forbidden_is_not_gone": "2026-09-24",
        # Our own 404s never make a link dead that the check could not reach
        # or found alive: the check states the link's present condition.
        "unreachable": None,
        "alive": None,
    }


def test_no_row_carries_a_byte_identity_note_and_methods_explains_the_fingerprint() -> None:
    # Author's decision, 2026-09-25: the per-row notes were a recurring false
    # alarm. Said once, on the Methods page.
    rendered = render("documents", {}, "documentsData.documents.map((r) => sourceLinks(r, null, ''))")
    html = "".join(rendered["eval"]) + json.dumps(rendered["elements"])
    assert "web-archive" in html, "no Web Archive copy rendered; the check would pass vacuously"
    for phrase in ("data-identity", "byte-identical", "compare the SHA-256",
                   "Our SHA-256 lets you check", "No fingerprint is recorded"):
        assert phrase not in html, phrase
    methods = unescape(render("methods")["main"])
    section = re.search(r'<section data-method="fingerprints">(.*?)</section>', methods, re.DOTALL)
    assert section, "the Methods page has no fingerprint section"
    assert "SHA-256" in section.group(1) and "Web Archive" in section.group(1)


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
        ("#document-rows/VNM?row=22", "vnm-rmp-2023:annex-I.1:022"),
        (rmp["url"] + "#page=156", "publisher's page ↗"),
        *web_copy(rmp, 156),
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
        ("#document-rows/VNM?row=22", "vnm-rmp-2023:annex-I.1:022"),
        (rmp["url"] + "#page=156", "publisher's page ↗"),
        *web_copy(rmp, 156),
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

    rendered = render("document-rows/VNM?row=22")

    assert rendered["elements"]["inventory-count"]["textContent"].startswith("1 of 1 ")
    results = rendered["elements"]["inventory-results"]["innerHTML"]
    assert 'data-inventory-row="vnm-rmp-2023:annex-I.1:022"' in results
    assert "<details open>" in results
    # The way back to the whole export is one link away.
    assert 'href="#document-rows/VNM"' in rendered["main"]


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

    rendered = render("document-rows/SEN?row=1", staged=every_copy())

    results = rendered["elements"]["inventory-results"]["innerHTML"]
    hrefs = [href for href, _ in anchors(results) if href.startswith(annexes["local_path"])]
    assert hrefs == [annexes["local_path"] + "#page=13"], hrefs
    public = render("document-rows/SEN?row=1")["elements"]["inventory-results"]["innerHTML"]
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
STEPS = ["Documents", "Document rows", "Statements", "Projects", "Funding", "Organisations"]
TRAIL_ROUTES = ("documents", "document-rows", "document-rows/VNM", "statements", "statements/ZAF",
                "projects", "project/" + BAC_AI, "funding", "funding/VNM", "organisations")

# The framework's names, the retired terms of docs/jetp-language.md and the
# words docs/jetp-observatory-presentation.md keeps off the pages.  A word
# inside a string the served JSON carries (a document's title, an analyst's
# note, a column name) is the data's, not the page's, and is not counted.
FORBIDDEN = re.compile(
    r"ontolog|evidence|model|layer|reconcil|\bD[1-4]\b|\bstages?\b|\beditions?\b"
    r"|\bfacts?\b|\bclaims?\b|\bdeals?\b|\bplayers?\b|\bsources\b|\bentities\b|\brecords\b",
    re.IGNORECASE,
)
ROUTES = ("overview", "the-paper-trail", "about", "who-we-are", "glossary", "documents", "document-rows", "statements", "projects",
          "funding", "organisations", "counts", "methods", "release-history",
          "non-jetp-energy-operations", *(f"funding/{code}" for code in COUNTRIES),
          "document-rows/VNM", "statements/ZAF", "project/" + BAC_AI)


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
    "the-paper-trail": list(zip(STEPS, ["#documents", "#document-rows", "#statements", "#projects",
                                        "#funding", "#organisations"])),
    "the-tallies": [("Counts", "#counts"), ("Non-JETP energy operations", "#non-jetp-energy-operations")],
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


# Author's cold read, third batch (2026-09-23), as revised: "The tallies" is
# one table, a row per computed figure, grouped by country, then two
# numbered figures; it no longer repeats the landing page's stat grid.
TALLY_COLUMNS = ["What it is", "Value", "Unit", "What it covers", "As of", "Computed from"]


def test_the_tallies_are_one_table_grouped_by_country_then_numbered_figures() -> None:
    main = render("counts")["main"]
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


@pytest.mark.parametrize("route", ["organisations", "documents", "project/" + BAC_AI])
def test_no_fold_out_summary_repeats_its_count(route) -> None:
    html = "".join(el["innerHTML"] for el in render(route)["elements"].values())
    # A counted fold-out, not the attempts line of ticket 1210: "2 attempts:
    # 404 on 13 Sep 08:46, 404 on 13 Sep 09:14" repeats a status by design.
    summaries_ = [unescape(s) for s in re.findall(r"<details(?! class=\"attempts\")[^>]*><summary>([^<]*)</summary>", html)]
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


@cache
def internal_keys():
    """The page keys app.js keeps apart from their public addresses."""
    return tuple(render("overview", {}, "Object.keys(CANONICAL)")["eval"])


def test_an_internal_page_key_is_not_an_address() -> None:
    # The site was never published, so no earlier address is kept (author,
    # 2026-09-24): an internal key opens what any unknown address opens.
    unknown = render("no-such-page")["main"]
    assert internal_keys()
    for key in internal_keys():
        assert render(key)["main"] == unknown, key


def test_an_unknown_address_says_so_and_every_page_still_opens() -> None:
    # Author, 2026-09-24: an unknown address opened Methods, so a reader who
    # followed a stale link landed on a real page with no sign of the miss.
    unknown = render("no-such-page", {}, "document.title")
    assert "This page is not in the snapshot." in unknown["main"]
    assert unknown["eval"].startswith("Page not found")
    for route in ROUTES:
        assert "This page is not in the snapshot." not in render(route)["main"], route
    assert '<div class="method-list">' in render("methods")["main"]


def test_the_pages_link_to_no_internal_key() -> None:
    keys = set(internal_keys())
    for html, where in [((SITE / "index.html").read_text(), "index.html"),
                        *(("".join(el["innerHTML"] for el in render(r)["elements"].values()), r)
                          for r in ROUTES)]:
        targets = {re.split(r"[/?]", href, maxsplit=1)[0] for href in re.findall(r'href="#([^"]*)"', html)}
        assert not targets & keys, (where, targets & keys)


def step_bar(route):
    return render(route)["elements"].get("step-bar", {}).get("innerHTML", "")


def test_a_page_of_the_paper_trail_shows_its_step_and_links_to_its_neighbours() -> None:
    # The sub-bar is the position indicator (ticket 0881's test, as the
    # author reshaped it on 2026-09-23): the selected tab is the step, and the
    # tabs beside it are the neighbouring steps, each keeping the country.
    bar = step_bar("document-rows/VNM")
    links = re.findall(r'<li><a href="([^"]+)" data-sub="[^"]+" data-step="(D\d)"'
                       r'( aria-current="page")?>([^<]+)</a></li>', bar)
    assert [unescape(label) for *_, label in links] == STEPS, links
    assert [(href, step) for href, step, current, _ in links if current] == [("#document-rows/VNM", "D2")]
    hrefs = {unescape(label): href for href, _, _, label in links}
    assert hrefs["Documents"] == "#documents?country=VNM"
    assert hrefs["Statements"] == "#statements/VNM"
    # Six plain sibling tabs: no separator, no grouping of the last three.
    assert "›" not in bar and "siblings" not in bar and bar.count("<li>") == 6
    # The scope is a chip; removing it opens the same step, unscoped.
    chip = re.search(r'<span class="scope-chip">([^<]+)<a href="([^"]+)"', bar)
    assert chip and chip.group(1).strip() == "Viet Nam" and chip.group(2) == "#document-rows", bar


@pytest.mark.parametrize("route", TRAIL_ROUTES)
def test_a_trail_page_carries_no_second_position_indicator(route) -> None:
    # The step bar replaces the eyebrow, the trail block and the in-page tabs.
    main = render(route)["main"]
    assert 'class="eyebrow"' not in main.split("</div>", 1)[0]
    assert 'class="trail"' not in main and 'role="tablist"' not in main
    assert 'aria-current="page"' in step_bar(route)


@pytest.mark.parametrize(("route", "section"), [
    ("documents", "the-paper-trail"), ("project/" + BAC_AI, "the-paper-trail"),
    ("counts", "the-tallies"), ("non-jetp-energy-operations", "the-tallies"), ("glossary", "about")])
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


@pytest.mark.parametrize("route", ["documents", "statements", "document-rows", "organisations",
                                   "counts", "methods"])
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
    assert 'href="#document-rows"' in bar and 'href="#statements"' in bar, bar
    assert "scope-chip" not in bar
    # And the links are escaped even for a code the site knows, so the guard
    # is not the escaping's only line of defence (round 2 of the review).
    known = json.dumps(payload)
    escaped = render("overview", {}, f"overview.countries.push({{code: {known}, name: {known}}}), "
                                     f"subBar('the-paper-trail', 'entries', {known})")["eval"]
    assert "<img" not in escaped and "&lt;img" in escaped, escaped


def test_an_item_on_the_record_reads_according_to_its_publisher_with_the_date() -> None:
    rendered = render("statements/VNM")
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
    # The Viet Nam count perimeter is now named; its observations follow in 0877.
    assert [row[1] for row in served("ontology/perimeters")["rows"]] == [
        "vnm-jetp-portfolio-2025"]


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
    rendered = render("document-rows/ZAF", site=glossary_site())
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
    rendered = render("statements/ZAF")
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


def test_funding_shows_financial_statements_instead_of_project_preview() -> None:
    rendered = render("funding/SEN")
    main = rendered["main"]
    table = rendered["elements"]["funding-statements-results"]["innerHTML"]
    assert "Inside the portfolio" not in main
    assert "Financing statements in the documents" in main
    assert "Financing needs stated in the documents" in main
    for heading in ("Reported milestone", "Original amount", "Funder · instrument",
                    "Date and its role", "Document and location"):
        assert f"<th>{heading}</th>" in table
    assert 'id="funding-statements-filter-status"' in main
    assert 'id="funding-statements-filter-funder"' in main
    assert "Document published" in table or "Event " in table
    assert "Publisher's document" in unescape(table)


def test_organisation_combines_roles_and_discloses_more_project_names() -> None:
    expression = """(() => {
      projects.splice(0, projects.length, ...[1,2,3,4,5].map(n => ({
        id: 'p' + n, name: 'Project ' + n, country: 'SEN',
        funders: ['Same Name'], operator: 'Same Name'
      })));
      partyNames.names = [];
      const rows = organisationIndex();
      return { length: rows.length, roles: rows[0].roles,
        projects: rows[0].projects.length, html: organisationProjects(rows[0]) };
    })()"""
    result = render("organisations", expression=expression)["eval"]
    assert result["length"] == 1
    assert result["roles"] == ["Funder", "Operator"]
    assert result["projects"] == 5
    assert result["html"].count('href="#project/') == 5
    assert "and 2 more" in result["html"]
    assert result["html"].index("Project 3") < result["html"].index("<details>")


def test_document_description_links_urls_without_interpreting_markup() -> None:
    actual = render("document-rows/ZAF?row=1")["elements"]["inventory-results"]["innerHTML"]
    assert 'target="_blank" rel="noopener noreferrer"' in actual
    assert "w05.international.gc.ca" in actual
    html = render("overview", expression="linkedDescription('Go https://example.org/a, then http://example.net/b. <img src=x onerror=alert(1)> javascript:evil')")["eval"]
    assert html.count('target="_blank" rel="noopener noreferrer"') == 2
    assert '</a>,' in html and '</a>.' in html
    assert '&lt;img src=x onerror=alert(1)&gt;' in html
    assert 'href="javascript:' not in html


def test_funding_keeps_a_disbursed_event_even_if_current_view_has_none() -> None:
    expression = """(() => {
      const project = countries.SEN.projects.find(p => p.events.length);
      project.events.push({...project.events[0], status: 'Disbursed', event_id: 'test-payment'});
      const table = fundingStatements(countries.SEN, 'SEN');
      main.innerHTML = table.head;
      table.mount();
      return document.getElementById('funding-statements-results').innerHTML;
    })()"""
    assert "Disbursed" in render("funding/SEN", expression=expression)["eval"]


def test_rejected_successor_retracts_reviewed_alias(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    (ledger / "parties.csv").write_text("party_id,country\np1,SEN\n")
    (ledger / "party-names.csv").write_text(
        "name_row_id,party_id,name,form_type,status,supersedes,document_id,line_id,recorded_at\n"
        "n1,p1,Preferred,preferred,accepted,,,,\n"
        "n2,p1,Old alias,alias,accepted,,,,\n"
        "n3,p1,Withdrawn,alias,rejected,n2,,,\n"
    )
    output = tmp_path / "names.json"
    subprocess.run(["python3", str(ROOT / "scripts/jetp/build_party_names_view.py"),
                    "--ledger", str(ledger), "--output", str(output)], check=True)
    assert [row["name"] for row in json.loads(output.read_text())["names"]] == ["Preferred"]


def test_country_specific_reviewed_name_is_not_applied_elsewhere() -> None:
    expression = """(() => {
      projects.splice(0, projects.length, {
        id: 'p1', name: 'Project 1', country: 'SEN', funders: ['Local label'], operator: ''
      });
      partyNames.names = [
        {party_id: 'zaf-party', country: 'ZAF', name: 'Local label', form_type: 'alias'},
        {party_id: 'zaf-party', country: 'ZAF', name: 'Another organisation', form_type: 'preferred'}
      ];
      return organisationIndex().map(row => ({name: row.name, aliases: row.aliases}));
    })()"""
    assert render("organisations", expression=expression)["eval"] == [
        {"name": "Local label", "aliases": []}]
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


PUBLIC_ROUTES = ("documents", "document-rows/ZAF", "document-rows/IDN", "document-rows/VNM",
                 "document-rows/SEN", "statements", "statements/ZAF", "statements/IDN",
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

    publisher = [(unescape(h), t) for h, t in anchors(html) if "web.archive.org" not in h]
    assert publisher == [
        (rmp["url"] + "#page=156", f"Publisher's page — {rmp['url'].split('/')[2]} ↗")], html
    assert "data-sha256" not in html and 'data-link="archived"' not in html
    # Ticket 0925: the Web Archive copy is a copy of the address, so it is
    # shown; with no fingerprint pinned, it claims no SHA-256 check (and since
    # ticket 1210 no row carries an identity note at all).
    if web_copy(rmp, 156):
        assert 'data-link="web-archive"' in html and "SHA-256" not in html, html


def test_the_documents_page_says_how_each_copy_was_sought() -> None:
    # Ticket 0926: the registry's collection_method reaches the page, in words,
    # for a copy taken through the author's browser session and for one taken
    # by the collector under its own name; and it is a facet of the table.
    session = next(d for d in registry() if d["collection_method"] == "browser-session"
                   and d["status"] == "collected")
    script = next(d for d in registry() if d["collection_method"] == "script"
                  and d["status"] == "collected")
    for entry, words in ((session, "through the author's browser session"),
                         (script, "by the collector")):
        page = render("documents", {"documents-search": entry["id"]})["elements"]
        html = page["documents-results"]["innerHTML"]
        assert f'data-collection-method="{entry["collection_method"]}"' in html, entry["id"]
        assert words in unescape(html), entry["id"]
    assert "All collection methods" in json.dumps(render("documents")["elements"])
