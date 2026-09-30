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


def test_existing_registry_is_refused(tmp_path):
    (tmp_path / "registry.csv").write_text("x")
    assert runner.main(["--output-dir", str(tmp_path)]) == 2
