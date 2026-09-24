"""Link rot (ticket 0925): Web Archive copies, publisher link checks, and what the page shows.

Three parts, each with its own table beside the collection registry:

- ``scripts/jetp/corpus_web_archive_capture.py`` fills ``web-archive-captures.csv``:
  reuse a recent snapshot, else ask Save Page Now, record every failure,
  never block, resume where it stopped;
- ``scripts/jetp/corpus_check_publisher_links.py`` fills
  ``publisher-link-checks.csv``: alive, dead (404/410, host gone) or
  unreachable, with the date a dead run began;
- ``scripts/jetp/build_link_views.py`` serves each as its own view, which
  app.js joins to ``documents.json`` on the address.

No test here touches the Internet Archive or a publisher: the services are
fakes, and the positive control's dead link is a local server that answers
404 — a deliberately dead URL in a fixture, checked by the real checker.
"""

import csv
import http.server
import json
import re
import shutil
import threading

import pytest
import requests
from jetp import (
    build_link_views,
    corpus_check_publisher_links,
    corpus_web_archive_capture,
)
from jetp.corpus_web_archive_capture import Unreachable, Wayback
from test_jetp_observatory_render import SITE, anchors, render

RMP = "vnm-rmp-2023"


# --- fakes -----------------------------------------------------------------


class Response:
    def __init__(self, status=200, payload=None, headers=None, text=""):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no JSON")
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeHttp:
    """Answers (method, url-prefix) with a queue of responses or exceptions."""

    def __init__(self, routes):
        self.routes = {k: list(v) for k, v in routes.items()}
        self.calls = []
        self.headers = {}

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs.get("params") or kwargs.get("data")))
        for (m, prefix), queue in self.routes.items():
            if m == method and url.startswith(prefix):
                answer = queue.pop(0) if len(queue) > 1 else queue[0]
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError(f"unexpected {method} {url}")

    def head(self, url, **kwargs):
        return self.request("HEAD", url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)


def closest(timestamp, status="200"):
    return Response(payload={"archived_snapshots": {"closest": {
        "available": True, "status": status, "timestamp": timestamp,
        "url": f"http://web.archive.org/web/{timestamp}/x"}}})


NONE = Response(payload={"archived_snapshots": {}})
DOC = {"source_id": "doc-a", "url": "https://publisher.example/a.pdf",
       "collected_at": "2026-09-12T08:35:00Z"}


def wayback(routes, **kwargs):
    sleeps = []
    service = Wayback(session=FakeHttp(routes), sleep=sleeps.append, **kwargs)
    return service, sleeps


# --- capture ----------------------------------------------------------------


def test_a_common_crawl_record_is_not_a_publisher_page_and_is_never_captured() -> None:
    service, _ = wayback({})
    row = corpus_web_archive_capture.capture_one(
        dict(DOC, url="https://data.commoncrawl.org/crawl-data/x.warc.gz"), service, 365)
    assert row["outcome"] == "not_applicable"
    assert service.http.calls == []


def test_a_snapshot_within_the_window_is_reused_and_nothing_is_requested() -> None:
    service, _ = wayback({("GET", corpus_web_archive_capture.AVAILABILITY): [closest("20260110101010")]})
    row = corpus_web_archive_capture.capture_one(DOC, service, 365)
    assert row["outcome"] == "reused"
    assert row["capture_url"] == "https://web.archive.org/web/20260110101010/" + DOC["url"]
    assert row["captured_at"] == "2026-01-10T10:10:10Z"
    assert all(method == "GET" for method, _, _ in service.http.calls)


def test_an_old_or_missing_snapshot_is_replaced_by_a_save_page_now_capture() -> None:
    service, sleeps = wayback({
        ("GET", corpus_web_archive_capture.AVAILABILITY): [closest("20190101000000")],
        ("POST", corpus_web_archive_capture.SAVE): [Response(payload={"job_id": "spn2-" + "a" * 32})],
        ("GET", corpus_web_archive_capture.STATUS): [
            Response(payload={"status": "pending"}),
            Response(payload={"status": "success", "timestamp": "20260924120000"})],
    })
    row = corpus_web_archive_capture.capture_one(DOC, service, 365)
    assert row["outcome"] == "captured"
    assert row["capture_url"] == "https://web.archive.org/web/20260924120000/" + DOC["url"]
    # Paced: a pause after each lookup, the submission and each poll.
    assert len(sleeps) >= 4


def test_a_rate_limit_is_waited_out_before_the_capture_is_retried() -> None:
    service, sleeps = wayback({
        ("GET", corpus_web_archive_capture.AVAILABILITY): [NONE],
        ("POST", corpus_web_archive_capture.SAVE): [
            Response(429, headers={"Retry-After": "200"}),
            Response(302, headers={"Location": "/web/20260924120000/" + DOC["url"]})],
    }, backoff=(120,))
    row = corpus_web_archive_capture.capture_one(DOC, service, 365)
    assert row["outcome"] == "captured"
    assert 200 in sleeps  # the server's Retry-After, longer than our 120 s


def test_a_refused_capture_is_recorded_with_its_reason() -> None:
    service, _ = wayback({
        ("GET", corpus_web_archive_capture.AVAILABILITY): [NONE],
        ("POST", corpus_web_archive_capture.SAVE): [Response(payload={"job_id": "spn2-" + "b" * 32})],
        ("GET", corpus_web_archive_capture.STATUS): [
            Response(payload={"status": "error", "status_ext": "error:blocked-url"})],
    })
    row = corpus_web_archive_capture.capture_one(DOC, service, 365)
    assert (row["outcome"], row["error"]) == ("failed", "save_error: error:blocked-url")


def _read(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_the_run_resumes_retries_failures_and_trips_its_breaker(tmp_path) -> None:
    output = tmp_path / "captures.csv"
    done = dict(source_id="doc-0", url="https://p.example/0", outcome="reused",
                capture_url="https://web.archive.org/web/20260101000000/https://p.example/0",
                captured_at="2026-01-01T00:00:00Z", attempted_at="2026-09-01T00:00:00Z", error="")
    failed = dict(done, source_id="doc-1", url="https://p.example/1", outcome="failed",
                  capture_url="", captured_at="", error="rate_limited")
    corpus_web_archive_capture.write_captures({("doc-0", done["url"]): done,
                                        ("doc-1", failed["url"]): failed}, output)
    documents = [dict(source_id=f"doc-{n}", url=f"https://p.example/{n}",
                      collected_at="2026-09-12T00:00:00Z") for n in range(4)]
    service, _ = wayback({
        ("GET", corpus_web_archive_capture.AVAILABILITY): [NONE],
        ("POST", corpus_web_archive_capture.SAVE): [requests.ConnectTimeout("down")],
    })

    rows = corpus_web_archive_capture.run(documents, output, service, breaker=1)

    saves = [c for c in service.http.calls if c[0] == "POST"]
    assert len(saves) == 1  # doc-1 tried, then the breaker: doc-2, doc-3 not asked
    assert rows[("doc-0", done["url"])] == done  # skipped, untouched
    table = {r["source_id"]: r for r in _read(output)}
    assert list(table) == ["doc-0", "doc-1", "doc-2", "doc-3"]
    assert table["doc-1"]["error"].startswith("wayback_unreachable (")
    assert {table[d]["error"] for d in ("doc-2", "doc-3")} == {"wayback_unreachable"}
    assert all(table[d]["outcome"] == "failed" for d in ("doc-1", "doc-2", "doc-3"))


def test_any_answer_from_save_page_now_resets_the_breaker(tmp_path) -> None:
    # Review of PR #1497: a rate limit proves the host answers, so it must not
    # let two non-consecutive connection failures trip a breaker of two.
    documents = [dict(source_id=f"doc-{n}", url=f"https://p.example/{n}",
                      collected_at="2026-09-12T00:00:00Z") for n in range(4)]
    down = requests.ConnectTimeout("down")
    service, _ = wayback({
        ("GET", corpus_web_archive_capture.AVAILABILITY): [NONE],
        ("POST", corpus_web_archive_capture.SAVE): [down, Response(429), down, down],
    }, backoff=())

    corpus_web_archive_capture.run(documents, tmp_path / "c.csv", service, breaker=2)

    assert sum(c[0] == "POST" for c in service.http.calls) == 4


def test_an_unreachable_lookup_still_asks_for_a_capture() -> None:
    service, _ = wayback({
        ("GET", corpus_web_archive_capture.AVAILABILITY): [requests.ConnectionError("x")],
        ("POST", corpus_web_archive_capture.SAVE): [
            Response(200, headers={"Content-Location": "/web/20260924120000/" + DOC["url"]})],
    })
    assert corpus_web_archive_capture.capture_one(DOC, service, 365)["outcome"] == "captured"


def test_the_unreachable_exception_is_what_a_dead_host_raises() -> None:
    service, _ = wayback({("POST", corpus_web_archive_capture.SAVE): [requests.ConnectTimeout("x")]})
    with pytest.raises(Unreachable):
        service.save(DOC["url"])


def test_collected_documents_are_the_retrievals_and_manifest_rows_that_kept_bytes(tmp_path) -> None:
    (tmp_path / "retrievals.csv").write_text(
        "retrieval_id,document_id,retrieved_at,status,http_status,content_type,etag,"
        "last_modified,final_url,error,sha256\n"
        "a:1,a,2026-09-02T00:00:00Z,collected,200,,,,https://p.example/a,,aa\n"
        "b:1,b,2026-09-02T00:00:00Z,blocked,403,,,,https://p.example/b,HTTP 403,\n")
    (tmp_path / "manifest.csv").write_text(
        "source_id,country,retrieved_at,status,http_status,content_type,etag,last_modified,"
        "sha256,size_bytes,storage_path,final_url,error\n"
        "a,IDN,2026-09-01T00:00:00Z,collected,200,,,,aa,1,x,https://p.example/a,\n"
        "c,IDN,2026-09-03T00:00:00Z,collected,200,,,,cc,1,x,https://p.example/c,\n")
    assert corpus_web_archive_capture.collected_documents(tmp_path) == [
        dict(source_id="a", url="https://p.example/a", collected_at="2026-09-01T00:00:00Z"),
        dict(source_id="c", url="https://p.example/c", collected_at="2026-09-03T00:00:00Z")]


# --- link check -------------------------------------------------------------


def check(routes, url, previous=None, when="2026-10-01T03:00:00Z"):
    return corpus_check_publisher_links.check_one(FakeHttp(routes), url, previous or {}, when)


def test_head_then_get_decides_alive_dead_or_unreachable() -> None:
    url = "https://p.example/x"
    assert check({("HEAD", url): [Response(200)]}, url)["outcome"] == "alive"
    refused = check({("HEAD", url): [Response(405)], ("GET", url): [Response(200)]}, url)
    assert (refused["outcome"], refused["method"]) == ("alive", "GET")
    gone = check({("HEAD", url): [Response(404)], ("GET", url): [Response(404)]}, url)
    assert (gone["outcome"], gone["dead_since"], gone["http_status"]) == ("dead", "2026-10-01", "404")
    robots = check({("HEAD", url): [Response(403)], ("GET", url): [Response(403)]}, url)
    assert (robots["outcome"], robots["dead_since"]) == ("unreachable", "")


def unresolved(host):
    return requests.ConnectionError(
        f"HTTPSConnectionPool(host='{host}', port=443): Max retries exceeded with url: / "
        f"(Caused by NameResolutionError(\"Failed to resolve '{host}'\"))")


def test_a_host_that_no_longer_resolves_is_dead() -> None:
    url = "https://gone.example/x"
    row = check({("HEAD", url): [unresolved("gone.example")],
                 ("GET", url): [unresolved("gone.example")]}, url)
    assert row["outcome"] == "dead"


def test_a_redirect_to_an_unresolvable_host_is_a_refusal_not_a_death() -> None:
    # www.unitedtractors.com answers a script with a redirect to no.access
    # (first check, 2026-09-24): the publisher is there, refusing the robot.
    url = "https://www.unitedtractors.com/en/x/"
    row = check({("HEAD", url): [unresolved("no.access")],
                 ("GET", url): [unresolved("no.access")]}, url)
    assert (row["outcome"], row["dead_since"]) == ("unreachable", "")


def test_dead_since_is_the_start_of_the_current_dead_run() -> None:
    url = "https://p.example/x"
    dead = {("HEAD", url): [Response(410)], ("GET", url): [Response(410)]}
    first = check(dead, url, when="2026-10-01T03:00:00Z")
    flaky = check({("HEAD", url): [requests.Timeout("x")], ("GET", url): [requests.Timeout("x")]},
                  url, first, when="2026-11-01T03:00:00Z")
    again = check(dead, url, flaky, when="2026-12-01T03:00:00Z")
    back = check({("HEAD", url): [Response(200)]}, url, again, when="2027-01-01T03:00:00Z")
    assert (flaky["outcome"], flaky["dead_since"]) == ("unreachable", "2026-10-01")
    assert again["dead_since"] == "2026-10-01"
    assert (back["outcome"], back["dead_since"]) == ("alive", "")


# --- served views -----------------------------------------------------------


def test_each_table_is_served_as_its_own_view_and_an_absent_table_as_empty(tmp_path) -> None:
    assert build_link_views.view(tmp_path, "web-archive") == {"captures": []}
    corpus_check_publisher_links.write_checks({"https://p.example/x": dict(
        url="https://p.example/x", checked_at="2026-10-01T03:00:00Z", method="GET",
        http_status="404", outcome="dead", dead_since="2026-10-01", error="")},
        tmp_path / "publisher-link-checks.csv")
    assert build_link_views.view(tmp_path, "publisher-links") == {"checks": [dict(
        url="https://p.example/x", checked_at="2026-10-01T03:00:00Z", method="GET",
        http_status="404", outcome="dead", dead_since="2026-10-01", error=None)]}


def test_the_committed_views_are_the_committed_tables() -> None:
    root = SITE.parents[1]
    for name in ("web-archive", "publisher-links"):
        served = json.loads((SITE / "data" / f"{name}.json").read_text())
        assert served == build_link_views.view(root / "data/jetp", name), name


def test_every_collected_document_has_a_capture_row() -> None:
    # Exit criterion 1: each collected document carries its Web Archive copy
    # or the reason there is none.
    root = SITE.parents[1]
    documents = {(d["source_id"], d["url"])
                 for d in corpus_web_archive_capture.collected_documents(root / "data/jetp")}
    rows = {(r["source_id"], r["url"]): r
            for r in _read(root / "data/jetp/web-archive-captures.csv")}
    assert documents <= set(rows)
    for key in documents:
        row = rows[key]
        assert row["outcome"] in corpus_web_archive_capture.OUTCOMES, key
        if row["outcome"] in ("captured", "reused"):
            assert re.fullmatch(r"https://web\.archive\.org/web/\d{14}/.+", row["capture_url"]), key
            assert row["capture_url"].endswith("/" + key[1]), key
        else:
            assert row["error"], key


# --- what the page shows ----------------------------------------------------


def served_entry(source_id):
    documents = json.loads((SITE / "data/documents.json").read_text())["documents"]
    return next(d for d in documents if d["id"] == source_id and d["sha256"])


class Gone(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(404 if self.path.startswith("/gone") else 200)
        self.end_headers()

    do_GET = do_HEAD

    def log_message(self, *args):
        pass


@pytest.fixture
def dead_site(tmp_path):
    """A copy of the site whose RMP entry points at a deliberately dead URL,
    checked by the real checker and served by the real view builder."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Gone)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    dead = f"http://127.0.0.1:{server.server_address[1]}/gone/rmp.pdf"
    alive = f"http://127.0.0.1:{server.server_address[1]}/alive"
    try:
        ledger = tmp_path / "ledger"
        ledger.mkdir()
        (ledger / "retrievals.csv").write_text(
            "retrieval_id,document_id,retrieved_at,status,http_status,content_type,etag,"
            "last_modified,final_url,error,sha256\n"
            f"{RMP}:1,{RMP},2026-09-12T00:00:00Z,collected,200,,,,{dead},,aa\n"
            f"x:1,x,2026-09-12T00:00:00Z,collected,200,,,,{alive},,bb\n")
        checks = ledger / "publisher-link-checks.csv"
        corpus_check_publisher_links.run(corpus_check_publisher_links.publisher_urls(ledger), checks,
                                  pace=0, checked_at="2026-10-01T03:00:00Z")
        with (ledger / "web-archive-captures.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=corpus_web_archive_capture.FIELDS)
            writer.writeheader()
            writer.writerow(dict(source_id=RMP, url=dead, outcome="captured",
                                 capture_url=f"https://web.archive.org/web/20260913000000/{dead}",
                                 captured_at="2026-09-13T00:00:00Z",
                                 attempted_at="2026-09-13T00:00:00Z", error=""))
    finally:
        server.shutdown()
    site = tmp_path / "site"
    shutil.copytree(SITE, site, ignore=shutil.ignore_patterns("documents"))
    registry = json.loads((site / "data/documents.json").read_text())
    for entry in registry["documents"]:
        if entry["id"] == RMP:
            entry["url"] = dead
    (site / "data/documents.json").write_text(json.dumps(registry))
    for name in ("web-archive", "publisher-links"):
        (site / "data" / f"{name}.json").write_text(json.dumps(build_link_views.view(ledger, name)))
    return site, dead


def test_positive_control_a_dead_publisher_link_shows_dead_since_and_the_copy_first(dead_site) -> None:
    site, dead = dead_site
    checks = json.loads((site / "data/publisher-links.json").read_text())["checks"]
    assert {c["url"]: c["outcome"] for c in checks}[dead] == "dead"

    html = render("documents", {}, f"sourceLinks(documentIndex[{json.dumps(RMP)}], 12, '')",
                  site=site)["eval"]

    assert "publisher link dead since 1 Oct 2026" in html
    links = anchors(html)
    assert [text.split(" — ")[0] for _, text in links] == ["Web Archive copy", "Publisher's page"]
    # The copy opens the archived bytes at the page; the origin is not rewritten.
    assert links[0][0] == f"https://web.archive.org/web/20260913000000id_/{dead}#page=12"
    assert links[1][0] == dead + "#page=12"


def test_positive_control_reaches_the_documents_page(dead_site) -> None:
    site, dead = dead_site
    rendered = render("documents", {"documents-search": RMP}, site=site)
    html = rendered["main"] + "".join(e["innerHTML"] for e in rendered["elements"].values())
    assert 'data-dead-since="2026-10-01"' in html
    assert 'data-identity="pdf"' in html


def test_the_shipped_site_shows_both_links_and_the_identity_note_by_type() -> None:
    captures = {c["url"]: c for c in json.loads(
        (SITE / "data/web-archive.json").read_text())["captures"]
        if c["outcome"] in ("captured", "reused")}
    if not captures:
        pytest.skip("no Web Archive copy recorded yet")
    expression = ("documentsData.documents.filter((r) => r.sha256).map((r) => "
                  "[r.url, sourceLinks(r, null, ''), identitySmall(r)])")
    rendered = render("documents", {}, expression)["eval"]
    shown = 0
    for url, html, note in rendered:
        kinds = re.findall(r'data-link="([a-z-]+)"', html)
        if url not in captures:
            assert kinds == ["publisher"] and note == "", url
            continue
        shown += 1
        assert sorted(kinds) == ["publisher", "web-archive"], url
        assert re.search(r'data-identity="(pdf|html)"', note), url
    assert shown > 0
