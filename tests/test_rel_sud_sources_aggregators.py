"""REL south sources, aggregator routes for dead sources (ticket 1790): canned answers.

CORE is read whole per data provider (a listing route: the local lexicon
selects); OpenAlex is searched with the lexicon restricted to the source that
stands for a dead platform (a search route: every work is kept).
"""

import json

import catalog_rel_sud_sources as runner
import pytest
from rel_sud_sources import _core as core
from rel_sud_sources import _openalex_targeted as oat
from rel_sud_sources._common import HARVEST_ROUTES

pytestmark = pytest.mark.domain_corpus

LEXICON = {
    "en": {"T1": '"climate finance"'},
    "fr": {"T1": '"finance climat"'},
    "ru": {"T1": '"климатическое финансирование"'},
    "hi": {"T1": '"जलवायु वित्त"'},
}
CFG = {"lexicon": LEXICON}


class Resp:
    def __init__(self, body, status=200):
        self.status_code, self._body = status, body

    def json(self):
        return json.loads(json.dumps(self._body))


def output(i, title, abstract="", year="2018"):
    return {"id": i, "title": title, "abstract": abstract, "yearPublished": year,
            "authors": [{"name": "Kumar, A."}], "identifiers": {"doi": None},
            "sourceFulltextUrls": [f"https://repository.usp.ac.fj/id/eprint/{i}/"],
            "language": None, "documentType": "", "tags": ["Thesis"], "doi": ""}


def test_core_reads_a_provider_whole_and_marks_lexicon_matches():
    pages = {0: {"totalHits": 3, "results": [output(1, "Climate finance readiness in Fiji"),
                                             output(2, "Teaching discipline")]},
             2: {"totalHits": 3, "results": [output(3, "", "no title")]}}
    calls = []

    def get(url, params=None, delay=0):
        calls.append(params)
        return Resp(pages[params["offset"]])

    spec = core.plan(CFG)[0]
    evs = list(core.fetch(spec, 0, get=get))
    assert evs[0] == ("meta", 3)
    recs = [v for k, v in evs if k == "work"]
    assert [r["record_id"] for r in recs] == ["1", "2"]  # a titleless output is not a record
    assert recs[0]["matched_terms"] == "climate finance" and recs[1]["matched_terms"] == ""
    assert recs[0]["url"] == "https://repository.usp.ac.fj/id/eprint/1/" and recs[0]["year"] == 2018
    assert evs[-1] == ("end", "")
    assert calls[0]["q"] == "repositories.id:373"


def test_core_empty_provider_is_complete_and_a_lost_page_is_not():
    empty = list(core.fetch(core.plan(CFG)[2], 0,
                            get=lambda u, params=None, delay=0: Resp({"totalHits": 0,
                                                                      "results": []})))
    assert empty == [("meta", 0), ("end", "")]

    def get(url, params=None, delay=0):
        if params["offset"] == 0:
            return Resp({"totalHits": 5, "results": [output(1, "A"), output(2, "B")]})
        return Resp({}, status=500)

    evs = list(core.fetch(core.plan(CFG)[0], 0, get=get))
    assert evs[-1] == ("end", "http 500 at offset 2")


def test_core_is_a_harvest_route_and_openalex_a_search_route():
    assert core.SOURCE["route"] in HARVEST_ROUTES
    assert oat.SOURCE["route"] not in HARVEST_ROUTES
    assert {"core", "openalex"} <= set(runner.discover())


def test_openalex_targeted_plan_restricts_each_lexicon_string_to_the_source():
    specs = oat.plan(CFG)
    shodh = [s for s in specs if s["query_id"].startswith("A-openalex-shodhganga-")]
    assert [s["query_id"] for s in shodh] == ["A-openalex-shodhganga-en-T1",
                                              "A-openalex-shodhganga-hi-T1"]
    assert shodh[0]["filter"] == ('locations.source.id:S4377209701,'
                                  'title_and_abstract.search:"climate finance",'
                                  'publication_year:1990-2026')


def test_openalex_targeted_keeps_every_work_and_notes_the_match(monkeypatch):
    work = {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/x",
            "display_name": "Carbon trading in Russia", "publication_year": 2012,
            "language": "en", "type": "article", "authorships": [],
            "primary_location": {"source": {"display_name": "CyberLeninka"}}}
    monkeypatch.setattr(oat, "oa_fetch", lambda spec, key, cap, delay: iter(
        [("meta", 1), ("work", work), ("end", "")]))
    spec = oat.plan(CFG)[0]
    evs = list(oat.fetch(spec, 0, api_key="k"))
    (rec,) = [v for k, v in evs if k == "work"]
    assert rec["record_id"] == "W1" and rec["doi"] == "10.1/x"
    assert rec["url"] == "https://openalex.org/W1" and rec["matched_terms"] == ""
    assert evs[-1] == ("end", "")
