"""OpenAlex, targeted at the copies of dead sources it indexes (ticket 1790).

The 1530 pass searched OpenAlex by stratum: affiliation country for English,
language (``lang|null``) for the other languages. Where a source is dead to
robots (author's rule, 2026-09-30), OpenAlex may still hold its records as a
source of its own, and a query restricted to that source reaches records the
stratum filters missed (a Russian journal article tagged ``en`` with no
affiliation country, a thesis without affiliation). Sources found on
2026-09-30 (``/sources?search=``):

- ``S4377209701`` Shodhganga (repository, IN, 117,659 works), for Shodhganga;
- ``S4306401404`` CyberLeninka (repository, RU, 1,220,679 works), for
  CyberLeninka and, as its open-access part, eLIBRARY;
- ``S4306402186`` USP Electronic Research Repository (313 works), and the
  institution ``I44666525`` University of the South Pacific (ROR 008stv805),
  for the USP repository.

No OpenAlex source stands for CNKI or Wanfang, and works cannot be filtered by
the country of their source (``primary_location.source.country_code`` is not
a filter): the zh stratum of 1530 is the only OpenAlex route to them.

Each query is the 1530 lexicon string of one language and theme, sent as
``title_and_abstract.search`` with the source (or institution) filter and the
1530 year window. A search route: every work returned is delivered. The
lexicon match on title and abstract is recorded in ``matched_terms`` as
information. Spend is read from the response headers by the caller's log; a
page costs 0.0001 to 0.001 USD against the shared daily budget of 1 USD.
"""

from catalog_rel_sud_search import OA_API, expand_query, slim
from catalog_rel_sud_search import fetch as oa_fetch
from pipeline_keystore import read_credential

from rel_sud_sources._common import empty_record, lexicon_terms, term_matcher

YEARS = (1990, 2026)  # as the 1530 pass (config/rel_sud_search.yaml)

# (query-id slug, OpenAlex filter, what it stands for, lexicon languages)
TARGETS = [
    ("shodhganga", "locations.source.id:S4377209701", "Shodhganga", ["en", "hi"]),
    ("cyberleninka", "locations.source.id:S4306401404",
     "CyberLeninka and the open-access part of eLIBRARY", ["ru", "en"]),
    ("usp-repository", "locations.source.id:S4306402186", "USP repository", ["en", "fr"]),
    ("usp-institution", "authorships.institutions.id:I44666525", "USP repository",
     ["en", "fr"]),
]

SOURCE = {
    "name": "openalex",
    "region": "South Asia, Russia, Pacific (by OpenAlex source)",
    "languages": sorted({lang for *_, langs in TARGETS for lang in langs}),
    "route": "api",
    "endpoint": OA_API,
    "terms": "https://openalex.org (CC0 metadata; API key, daily budget)",
}


def plan(cfg):
    specs = []
    for slug, flt, stands_for, langs in TARGETS:
        match = term_matcher(lexicon_terms(cfg["lexicon"], langs))
        for lang in langs:
            for theme, search in cfg["lexicon"][lang].items():
                f = (f"{flt},title_and_abstract.search:{expand_query(search)},"
                     f"publication_year:{YEARS[0]}-{YEARS[1]}")
                specs.append({"query_id": f"A-openalex-{slug}-{lang}-{theme}",
                              "query_string": f"filter={f} (stands in for {stands_for})",
                              "filter": f, "match": match})
    return specs


def to_record(work, match):
    s = slim(work)
    title, abstract = s["title"] or "", s["abstract"] or ""
    return empty_record(
        record_id=s["openalex_id"],
        url=f"https://openalex.org/{s['openalex_id']}",
        doi=s["doi"] or "", title=title,
        authors="; ".join(a.get("author", {}).get("display_name", "")
                          for a in work.get("authorships") or []
                          if a.get("author", {}).get("display_name")),
        year=s["year"], language=s["language"] or "", venue=s["journal"] or "",
        doc_type=s["type"] or "", abstract=abstract,
        matched_terms="; ".join(match(title + " " + abstract)))


def fetch(spec, delay, api_key=None):
    api_key = api_key or read_credential("openalex", "OPENALEX_API_KEY")
    for kind, val in oa_fetch(spec, api_key, 0, delay):
        if kind == "work":
            if (val.get("display_name") or "").strip():
                yield ("work", to_record(val, spec["match"]))
        else:
            yield (kind, val)
