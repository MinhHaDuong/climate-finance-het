"""REL south sources outside OpenAlex (ticket 1653): provenance and honest flags."""

import csv
import gzip
import json
import os
import types

import catalog_rel_sud_sources as runner
import pytest
from rel_sud_sources import common

pytestmark = pytest.mark.domain_corpus

OAI_PAGE1 = b"""<?xml version="1.0"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
<ListRecords>
<record><header><identifier>oai:x:1</identifier></header><metadata>
<oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Financiamiento clim\xc3\xa1tico en Am\xc3\xa9rica Latina</dc:title>
<dc:creator>Doe, J.</dc:creator><dc:date>2019-05-01</dc:date>
<dc:identifier>https://x.org/1</dc:identifier>
<dc:identifier>https://doi.org/10.1234/ABC.1</dc:identifier>
</oai_dc:dc></metadata></record>
<resumptionToken completeListSize="2">tok</resumptionToken>
</ListRecords></OAI-PMH>"""

OAI_PAGE2 = b"""<?xml version="1.0"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
<ListRecords>
<record><header><identifier>oai:x:2</identifier></header><metadata>
<oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Soil moisture of maize</dc:title><dc:date>2001</dc:date>
</oai_dc:dc></metadata></record>
<resumptionToken/>
</ListRecords></OAI-PMH>"""


def fake_get(pages):
    it = iter(pages)

    def get(url, params=None, delay=0):
        return types.SimpleNamespace(status_code=200, content=next(it))
    return get


def test_oai_reader_follows_tokens_and_reports_completion():
    match = common.term_matcher(["financiamiento climático", "REDD"])
    events = list(common.oai_list_records("http://x", get=fake_get([OAI_PAGE1, OAI_PAGE2])))
    assert events[0] == ("meta", 2)
    assert events[-1] == ("end", "")
    recs = [common.dc_to_record(v, match) for k, v in events if k == "dc"]
    assert recs[0]["doi"] == "10.1234/abc.1"
    assert recs[0]["year"] == 2019
    assert recs[0]["matched_terms"] == "financiamiento climático"
    assert recs[1]["matched_terms"] == ""


def test_oai_error_is_incomplete_and_no_records_match_is_complete():
    err = b'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><error code="badArgument"/></OAI-PMH>'
    none = b'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><error code="noRecordsMatch"/></OAI-PMH>'
    assert list(common.oai_list_records("u", get=fake_get([err])))[-1] == ("end", "oai error: badArgument")
    assert list(common.oai_list_records("u", get=fake_get([none]))) == [("meta", 0), ("end", "")]


def test_oai_reader_removes_characters_xml_forbids():
    """One U+FFFE in an abstract used to end the whole set with 'bad xml'."""
    dirty = OAI_PAGE2.replace(b"Soil moisture", "Soil\ufffe moisture".encode("utf-8"))
    events = list(common.oai_list_records("u", get=fake_get([OAI_PAGE1, dirty])))
    assert events[-1] == ("end", "")
    titles = [v["title"] for k, v in events if k == "dc"]
    assert titles[1] == ["Soil moisture of maize"]


def test_oai_reader_takes_an_explicit_getter_and_oai_get_sends_no_mailto(monkeypatch):
    import inspect

    import openalex_corpus.crawl as crawl

    param = inspect.signature(common.oai_list_records).parameters["get"]
    assert param.default is inspect.Parameter.empty
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    sent = []

    def fake_requests_get(url, params=None, headers=None, timeout=None):
        sent.append(dict(params or {}))
        return types.SimpleNamespace(status_code=200, content=OAI_PAGE2, headers={})

    monkeypatch.setattr(crawl.requests, "get", fake_requests_get)
    events = list(common.oai_list_records("https://oai", delay=0, get=common.oai_get))
    assert events[-1] == ("end", "")
    assert sent == [{"verb": "ListRecords", "metadataPrefix": "oai_dc"}]


def test_latin_terms_need_word_boundaries():
    match = common.term_matcher(["REDD", "气候融资"])
    assert match("REDDITO agricolo") == []
    assert match("redd+ in Peru") == ["REDD"]
    assert match("中国气候融资研究") == ["气候融资"]


def _fake_adapter(route, records, end=""):
    def fetch(spec, delay):
        yield ("meta", len(records))
        for r in records:
            yield ("work", common.empty_record(**r))
        yield ("end", end)
    return types.SimpleNamespace(
        SOURCE={"name": "fake", "route": route, "endpoint": "http://fake"},
        plan=lambda cfg: [{"query_id": "F-1", "query_string": '"climate finance"'}],
        fetch=fetch)


def _run(tmp_path, mod, cap=0):
    os.makedirs(tmp_path / "raw")
    with open(tmp_path / "registry.csv", "w", newline="") as r, \
            open(tmp_path / "candidates.csv", "w", newline="") as c:
        reg = csv.DictWriter(r, runner.REGISTRY_FIELDS)
        cand = csv.DictWriter(c, runner.CANDIDATE_FIELDS)
        reg.writeheader()
        cand.writeheader()
        runner.run_source(mod, {}, str(tmp_path), reg, cand, cap, 0)
    with open(tmp_path / "registry.csv") as fh:
        regrows = list(csv.DictReader(fh))
    with open(tmp_path / "candidates.csv") as fh:
        cands = list(csv.DictReader(fh))
    with gzip.open(tmp_path / "raw" / "fake.jsonl.gz", "rt") as fh:
        raw = [json.loads(line) for line in fh]
    return regrows, cands, raw


def test_harvest_route_keeps_only_matches_and_archives_everything(tmp_path):
    mod = _fake_adapter("oai-pmh", [{"title": "a", "matched_terms": "REDD"}, {"title": "b"}])
    regrows, cands, raw = _run(tmp_path, mod)
    assert len(raw) == 2 and len(cands) == 1
    assert regrows[0]["n_received"] == "2" and regrows[0]["n_matched"] == "1"
    assert regrows[0]["completed"] == "True"
    c = cands[0]
    assert c["source"] == "fake" and c["query_string"] == '"climate finance"'
    assert c["export_file"] == "raw/fake.jsonl.gz" and c["run_at"]


def test_search_route_keeps_all_and_a_cap_or_error_is_incomplete(tmp_path):
    mod = _fake_adapter("api", [{"title": "a"}, {"title": "b"}], end="http 503")
    regrows, cands, _ = _run(tmp_path, mod)
    assert len(cands) == 2
    assert regrows[0]["completed"] == "False" and regrows[0]["stop_reason"] == "http 503"


def test_cap_stops_and_flags(tmp_path):
    mod = _fake_adapter("api", [{"title": "a"}, {"title": "b"}])
    regrows, _, _ = _run(tmp_path, mod, cap=1)
    assert regrows[0]["stop_reason"] == "record cap" and regrows[0]["completed"] == "False"


def test_sentinel_matching_by_fragments_and_doi():
    sentinels = [
        {"sentinel": "S43", "class": "b", "doi": "",
         "title": "Kerjasama Indonesia-Norwegia dalam konservasi hutan ... REDD+ (Kalimantan Tengah)"},
        {"sentinel": "S99", "class": "b", "doi": "10.1/x", "title": "Nothing like it"},
        {"sentinel": "S01", "class": "c", "doi": "", "title": "ignored class"},
    ]
    rows = [
        {"source": "garuda", "query_id": "G1", "doi": "",
         "title": "Kerjasama Indonesia–Norwegia dalam Konservasi Hutan melalui skema REDD+ "
                  "di Kalimantan Tengah"},
        {"source": "x", "query_id": "X1", "doi": "10.1/X", "title": "Other"},
        {"source": "y", "query_id": "Y1", "doi": "", "title": "Kerjasama Indonesia"},
    ]
    rep = {r["sentinel"]: r for r in runner.sentinel_report(sentinels, rows)}
    assert set(rep) == {"S43", "S99"}
    assert rep["S43"]["found"] and rep["S43"]["sources"] == "garuda"
    assert rep["S99"]["query_ids"] == "X1"


def test_existing_registry_is_refused(tmp_path):
    (tmp_path / "registry.csv").write_text("x")
    assert runner.main(["--output-dir", str(tmp_path)]) == 2
