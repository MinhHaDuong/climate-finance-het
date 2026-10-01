# REL "Sud et langues": southern sources outside OpenAlex

Run date: 2026-09-30 UTC, on doudou. Ticket 1653, child of 0700, sequel to
1530 (the OpenAlex pass of the same stratum). The lexicon is the 1530 one,
`config/rel_sud_search.yaml`: four themes (T1 international climate finance;
T2 instruments, private finance, international carbon; T3 adaptation and
forest; T4 loss and damage, justice, accounting) in ten languages. Every
source reuses it; no source got its own vocabulary.

Code: `scripts/catalog_rel_sud_sources.py` (runner) and the adapters of
`scripts/rel_sud_sources/`. Delivery: `scripts/catalog_rel_1653_delivery.py`.
Source status, machine-readable: `config/rel_sud_sources_status.yaml`.
Run directories and raw exports sit on doudou under
`~/data/projets/climate-finance-het/rel_sud/2026-09-30/`, fingerprinted in
`MANIFEST.sha256` there. The delivery to the pool (ticket 1655) is
`data/rel_intake/t1653-sud-hors-openalex/2026-09-30/`, tracked by DVC.

Ticket 1790 (2026-09-30 and the night to 10-01) retried every blocked source
under the author's rule "If you can't Playwright it, it's dead", read the dead
sources' copies held by aggregators, and delivered what it recovered as
`data/rel_intake/t1790-sud-playwright/2026-09-30/` (section
[Ticket 1790](#ticket-1790-browser-attempts-aggregators-second-delivery)).

## Harvest and listing routes: the lexicon match is the query

Three kinds of route ran. A **search** route (`api`) sends the lexicon to the
server and delivers every record the server returned, deduplicated in lane by
record id; a full-text hit with no lexicon phrase in its title or abstract is
delivered too (GARUDA: 13,169 unique records of 18,987 rows; Redalyc: all 4,450
unique full-text hits, of which 245 carry a title/abstract match; 694 of
the 8,185 rows do). A
**harvest** route (`oai-pmh`: SciELO, CyberLeninka, AJOL) and a **listing**
route (`listing`: a whole working-paper series or catalogue) have no
server-side search: the adapter reads the set or the listing whole, the raw
harvest is archived in the run's `raw/`, and the local match of the same 1530
lexicon on title and abstract selects the candidates.

Decision of the team lead, 2026-09-30: for these routes the local lexicon
match is the query. The delivered registry's `query` names the set or
listing and adds "candidates selected by local 1530 lexicon match on
title+abstract, languages X"; `n_received` is the number of records that
query returned (the matches), `n_expected` the number harvested or listed.
Rejected alternative: delivering the roughly 70,000 unmatched harvested
SciELO, CyberLeninka and listing records to the ICF screen. They were not
retrieved by any query of the protocol, only read in order to run one; the
raw harvest stays archived.

`matched_terms` travels with every delivered record, and `lane_status`
(`lexicon_match` / `no_lexicon_match`) repeats it, as information only.

## Query register

Dates are 2026-09-30 UTC for every row. Counts: n_expected is what the server
announced (search) or what was harvested/listed (harvest, listing);
n_received is what the query returned as defined above (rows, before in-lane
deduplication); n_kept is the unique records in `records.csv`.

| Source | Route | Endpoint | Query form | Queries (complete) | n_expected | n_received | n_kept | Run directory |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Redalyc | api | `www.redalyc.org/service/r2020/getArticles/` | lexicon string of a language x theme sent verbatim (`"financiamiento climático" OR ...`), es/pt/en | 12 (12) | 8,185 | 8,185 | 4,450 | `t1653-latam/` |
| CLACSO | api | `biblioteca-repositorio.clacso.edu.ar/server/api/discover/search/objects` | `query=<lexicon string>&dsoType=ITEM`, es/pt | 8 (8) | 719 | 719 | 410 | `t1653-latam-dspace-b/` |
| Ipea (TD) | api | `repositorio.ipea.gov.br/server/api/discover/search/objects`, collection hdl 11058/17462 | same, pt/en | 8 (8) | 135 | 135 | 87 | `t1653-latam/` |
| UWI | api | `uwispace.sta.uwi.edu/server/api/discover/search/objects` | same, en | 4 (4) | 50 | 50 | 46 (30 keyed by their Handle) | `t1653-latam-dspace-b/` |
| SciELO | oai-pmh | `<collection>/oai/scielo-oai.php` (mex, ven, bol, cri, pry) | `ListRecords metadataPrefix=oai_dc set=<ISSN>` per social-science journal, lexicon es/pt/en | 216 (212) | 69,283 | 26 | 26 | `t1653-latam-scielo-b/` |
| GARUDA | api | `garuda.kemdiktisaintek.go.id/documents` | `select=<title\|abstract>&q=<phrase>&from=1990&to=2026`, one query per phrase and field (server matches all words), id/en | 116 (107) | 97,342 | 18,987 | 13,169 | `t1653-asia/garuda/` |
| CyberLeninka | oai-pmh | `cyberleninka.ru/oai` | `ListRecords set=repec`; `ListSets` for journal sets, lexicon ru/en on titles | 2 (0) | 9,830 | 0 | 0 | `t1653-asia/cyberleninka-b/`, `-c/` |
| AJOL | oai-pmh | `www.ajol.info/index.php/<journal>/oai` | `ListRecords metadataPrefix=oai_dc`, per journal of five subject categories | 16 (0) | 0 | 0 | 0 | `t1653-africa-sasia/ajol/` |
| ERSA | listing | `econrsa.org/wp-json/wp/v2/publications?publication-types=7139` | every page of the working-paper series, lexicon en | 1 (1) | 973 | 1 | 1 | `t1653-africa-sasia/series-c/listing/` |
| CPD | listing | `cpd.org.bd/wp-json/wp/v2/publication` | every publication, all types, lexicon en/bn on title, excerpt and body | 1 (1) | 705 | 18 | 18 | `t1653-africa-sasia/series-c/listing/` |
| South Centre | listing | `www.southcentre.int/category/research-papers/feed/` | `?paged=1..N` RSS, lexicon en/fr/es/pt on title, subtitle, tags and body | 1 (1) | 267 | 4 | 4 | `t1653-africa-sasia/series-c/listing/` |
| ADB EWP | listing | `ideas.repec.org/s/ris/adbewp.html` | RePEc series pages, then each paper page, lexicon en | 1 (1) | 861 | 5 | 5 | `t1653-africa-sasia/series-c/listing/` |
| CEEW | listing | `www.ceew.in/sitemap.xml` | every publication page of the sitemap, lexicon en/hi on title and Overview | 1 (0) | 706 | 54 | 52 | `t1653-africa-sasia/ceew/` |

SciELO's four incomplete sets: `cri 0379-3982` (bad xml) and three `pry`
journals (RuntimeError); they stay recorded as incomplete, not rerun. GARUDA's
nine incomplete queries stopped at the server's 1,000-record page cap.

Two fixes made during integration changed which run is authoritative:

- The DSpace adapter read the year from `dc.date.issued` only; CLACSO keeps it
  in plain `dc.date` on many items. CLACSO and UWI were rerun with the
  fallback (`t1653-latam-dspace-b/`, same queries, same counts as the lane's
  run in `t1653-latam/`, which is superseded for these two sources).
- Listing adapters used to yield only lexicon matches, so their listings were
  not archived and the registry read complete with received below expected.
  They now yield every listed item under route `listing`, a harvest route of
  the runner. ERSA, CPD, South Centre and ADB were rerun
  (`t1653-africa-sasia/series-c/listing/`, full listings archived, every
  query complete, the same matches as the lane's `series-b/` run, which is
  superseded; ADB now reads all 861 paper pages). The CEEW rerun
  (`series-c/ceew/`) was stopped by the agent harness's two-hour limit after
  619 of 706 pages, before its registry row was written: the lane's run
  `t1653-africa-sasia/ceew/` stayed authoritative for 1653 (54 matches, 13
  pages failed, full listing not archived), and the partial rerun is kept as
  an archive only (`README-incomplete.txt`). Ticket 1790 superseded both
  with a reread of every page the site serves (693 of 706; 13 stale
  sitemap entries answer 404) and a year fix (section Ticket 1790).

GARUDA's query form carries `from=1990&to=2026`. Whether the server's year
filter drops records without a year was not probed. Such records may be
missing from its hits, and the delivery does not record them as a gap.

### Code of record and code on `main`

The runs above were made on 2026-09-30 by the lane code, plus the two fixes
just described. The code merged afterwards, in PRs #1622, #1624 and #1625 (a
split of #1619 for review), is stricter. None of these changes alters a
delivered record, so the runs were not repeated:

- More failure modes now end a query as incomplete. These include a non-OAI
  page, a repeated resumption token, a missing result count or page count,
  an empty listing, a WordPress listing short of its total, an AJOL category
  that cannot be read, and an adapter exception.
- The matcher now compares text in NFC. It gives Cyrillic phrases word
  boundaries.
- The sentinel matcher now reads bracketed text as a note and matches
  fragments as whole words.
- AJOL applies no year window. CEEW excludes robots-disallowed paths and
  pages without a title. GARUDA counts records once by id.

The class-b sentinel result is the same under the merged sentinel matcher (S43
found, nine missed). The registry's completion flags were set by the code of
record. They have not been re-evaluated under the new guards. GARUDA, for
example, now judges completion on distinct record ids rather than on rows.

## Source status

As of 2026-10-01, after ticket 1790. `dead`: the author's rule of 2026-09-30,
"If you can't Playwright it, it's dead": one attempt in headless Chromium,
within robots.txt and the terms, no CAPTCHA solved, no account; no attempt
where robots.txt or the terms forbid robots. No human chases a closed
archive.

| Source | Stratum | Status | Reason | Ticket 1790 |
| --- | --- | --- | --- | --- |
| Redalyc | LAC | run | undocumented JSON service of the site's article finder, robots.txt allows; the documented OAI (775,205 records, no subject sets) would take about 5.5 h | use of the undocumented service `www.redalyc.org/service/r2020/getArticles/` approved by the author (2026-09-30) |
| CLACSO | LAC | run | DSpace 7 discovery, crawl-delay 10 s; old site HTTP 526 | |
| Ipea | LAC | run | DSpace 7 discovery on the TD collection | |
| UWI | LAC | run | DSpace 7 discovery | |
| SciELO | LAC | partial | search.scielo.org robots Disallow: / and Bunny Shield 403; ArticleMeta has no text search; OAI on social-science journal sets | Argentina recovered (plain HTTP answered again: 47 journals, 41 complete, 6 lost to HTTP 500). Dead: Brazil (OAI 404, `/oai` 502, the same in Chromium), Chile and Peru (robots.txt Disallow: / for all but named search engines, re-read 2026-09-30), Colombia (TCP timeout, in Chromium too), Cuba (scielo.sld.cu does not resolve) |
| USP repository | Pacific | dead | robots Disallow /cgi/ (oai2, search, export); Cloudflare 403 on every path; not in OpenAIRE | no attempt (robots); CORE and OpenAlex copies read, see below |
| GARUDA | SE Asia | run | HTML search, no OAI or JSON API, robots.txt 404 | |
| SINTA | SE Asia | not needed | robots.txt 403; GARUDA covers it | |
| CyberLeninka | Russia | dead | /search and /api/ robots-disallowed; oai_dc titles only; set repec is not economics (9,830 received, 0 matched); captcha after about 980 pages | reCAPTCHA on the first request of 1790 (OAI ListSets, about 20:30 UTC), not solved; CORE and OpenAlex copies read |
| eLIBRARY | Russia | dead | agreement.asp forbids robots and automated search or download; no OAI; API by contract only | no attempt (terms); its open-access part overlaps CyberLeninka |
| CNKI | China | dead | cnki.net redirects to oversea.cnki.net, robots Disallow: /; no OAI, no public API | no attempt (robots); no aggregator holds it |
| Wanfang | China | dead | no OAI; open-platform API behind registration; no robots.txt | slider CAPTCHA on the first search page in Chromium, not solved |
| AJOL | Africa | run | per-journal OAI, robots allows `/index.php/<journal>/oai`; AWS WAF JavaScript challenge after a few plain requests (1653: no record) | recovered through Chromium: 232 journals of the five 1653 categories, all complete, 36,207 records read, 66 matches |
| Shodhganga | South Asia | dead | robots Disallow: / (Crawl-delay 600); OAI and REST 404 (DSpace 5.3) | no attempt (robots); OpenAlex copy read (CORE holds nothing) |
| ERSA | Africa | run | WordPress REST listing of 973 working papers; not in RePEc | |
| CPD | South Asia | run | WordPress REST listing of 705 publications; en/bn lexicon | |
| South Centre | Global South | run | REST 401 except /search; category RSS feed, crawl-delay 10 s | |
| ADB EWP | Asia-Pacific | run | adb.org Cloudflare 403 (robots.txt included); RePEc listing and paper pages on IDEAS | |
| CEEW | South Asia | partial | no API or feed; search and paged listings robots-disallowed; sitemap pages at crawl-delay 10 s | listing reread and archived: 693 of 706 pages; the 13 others are stale sitemap entries that redirect to a 404 page (list in `t1790-ceew/missing-pages.txt`) |

## Strata left incomplete

As of 2026-10-01:

- **Russia**: eLIBRARY and CyberLeninka dead. Their OpenAlex copy (the
  CyberLeninka source) gave 29 hits; CORE's 400 CyberLeninka outputs matched
  nothing.
- **China**: CNKI and Wanfang dead, no aggregator copy. The zh stratum of
  the 1530 OpenAlex pass is the only route (0 records outside OpenAlex).
- **Pacific**: USP repository dead; its CORE copy (9,889 outputs, 32
  matches) and OpenAlex repository source stand in; the OpenAlex institution
  route (USP-affiliated works anywhere) is reported apart and is no repository
  surrogate.
- **Africa**: AJOL recovered for the five categories chosen in 1653; its
  other categories were never in the query.
- **South Asia**: Shodhganga dead; its OpenAlex copy gave 8 hits. CPD and
  CEEW are institute catalogues.
- **LAC**: SciELO partial: Argentina, Mexico, Venezuela, Bolivia, Costa Rica
  and Paraguay read; Brazil, Chile, Peru, Colombia and Cuba dead.

Each delivery's `manifest.json` declares `coverage: incomplete` and lists the
dead and partial sources, with their reasons. `needs_human` is empty in the
1790 delivery: no human errand remains.

## Translation status

The zh, ru, hi, bn, id and ar query strings were machine-drafted in 1530. On
2026-09-30 (ticket 1790, author decision) two decorrelated strong models
reviewed each of the 24 strings for fluency and search effectiveness: Claude
Opus 5.5, whose verdict was written first, and
`google/gemini-3.1-pro-preview` through OpenRouter. A string changed only
where both objected. No human reader has reviewed them. The es, pt, fr and en
strings were read by the assistant only. Per-string status:
`config/rel_sud_sources_status.yaml` (`translation_review`); prompts, both
answers and checksums:
`~/data/projets/climate-finance-het/rel_sud/2026-09-30/t1790-reader-review/`.

| Language | ok | fixed | disputed (unchanged) |
| --- | --- | --- | --- |
| zh | T1, T2, T4 | T3: 森林融资 → 林业融资 | |
| ru | T1 | | T2, T4 (Opus: nominative forms only); T3 (Gemini: финансирование лесов a calque) |
| hi | T1-T4 | | |
| bn | T2-T4 | | T1 (Opus: genitive জলবায়ু অর্থায়নের missing) |
| id | T1-T4 | | |
| ar | T1-T4 | | |

The fixed zh T3 string was rerun on OpenAlex only, since no zh source outside
OpenAlex is reachable and no 1653 source used zh: 651 works (1530 run of record:
646), 6 absent from the 1530 delivery (4 carrying 林业融资, 2 indexed after
2026-09-29). They go to the pool as `data/rel_intake/t1790-reader-reruns/2026-09-30/`.
The old string stays under `revisions` in `config/rel_sud_search.yaml`.

## Class-b sentinels

`sentinel_report` of `scripts/catalog_rel_sud_sources.py` over every
delivered record (title fragments or DOI), written to the delivery's
`sentinels.csv`.

| Sentinel | Region, language | Title | Result | Diagnosis |
| --- | --- | --- | --- | --- |
| S08 | Global, en | Seeing Double: Decoding the additionality of climate finance (2023) | missed | CARE Denmark and CARE Climate Justice Center report, published on careclimatechange.org (checked 2026-09-30); a Northern NGO's grey literature, held by no source of this lane |
| S24 | LAC, es | Análisis del financiamiento climático internacional en ALC, desde un enfoque de justicia climática y financiera | missed | Latindadd report (latindadd.org/informes/analisis-del-financiamiento, checked 2026-09-30); NGO grey literature, not in CLACSO or Redalyc, held by no source of this lane |
| S28 | Africa, en | Landscape of Climate Finance in Africa (2022) | missed | Climate Policy Initiative report on climatepolicyinitiative.org; no African source of this lane indexes CPI reports |
| S35 | South Asia, en | Climate Change Finance, Analysis of a Recent OECD Report: Some Credible Facts Needed (2015) | missed | India Ministry of Finance, Department of Economic Affairs discussion paper on dea.gov.in; no government-publication source in scope |
| S36 | South Asia, hi | जलवायु कार्रवाई के लिए निजी वित्त ... (2023) | missed | the Hindi version is on ORF Hindi; CEEW holds only the English original, delivered as "The Myth of Mobilising Private Finance for Climate Action and Pivoting to Scale" (2023) |
| S39 | Bangladesh, en | Operationalizing the Loss and Damage Fund: learning from the intended beneficiaries (2023) | missed | SEI / ICCCAD publication on sei.org; neither is a source of this lane (CEEW's "Operationalising the Loss and Damage Fund to Address Climate Impacts" is a different work) |
| S43 | Indonesia, id | Kerjasama Indonesia-Norwegia dalam konservasi hutan ... REDD+ (2017) | **found** | GARUDA `garuda:689770`, WANUA 3(1) 2017, four queries (id T3 and en T3, title and abstract) |
| S45 | Vietnam, vi | Thúc đẩy tài chính khí hậu tại Việt Nam: thực trạng và khuyến nghị (2023) | missed | thitruongtaichinhtiente.vn; no Vietnamese source and no vi lexicon in scope |
| S58 | Pacific, en | Pacific Climate Change Financing Assessment (framework, Nauru case) (2012-2014) | missed | Pacific Islands Forum Secretariat report (reliefweb, pacificdata, unfccc); no automated Pacific source |
| S59 | Pacific, en | Pacific Regional Climate Finance Access and Mobilisation Strategy 2025-2030 (2026) | missed | forumsec.org; same Pacific gap |

The integrator checked the locations of S08 and S24 on 2026-09-30. The other
diagnoses are the lanes'. S43 and the CEEW English original of S36 were
verified in the delivered records.

One of ten sentinels was found. Most misses are institutional grey
literature (CARE, Latindadd, CPI, DEA, SEI, PIFS) that none of the scholarly
or series sources indexes. One more is in a language (vi) with no source at
all.

## Delivery

`data/rel_intake/t1653-sud-hors-openalex/2026-09-30/`, written by
`scripts/catalog_rel_1653_delivery.py` (the invocation is in the
manifest's `producer.runs`), DVC-tracked and pushed to padme.
`uv run python scripts/qa_rel_intake.py` on it: `OK`, exit 0.

| File | Content |
| --- | --- |
| `records.csv` | 18,268 records: GARUDA 13,169; Redalyc 4,450; CLACSO 410; Ipea 87; CEEW 52; UWI 46; SciELO 26; CPD 18; ADB 5; South Centre 4; ERSA 1. 12,574 carry a DOI, 5,664 a year but no DOI, 30 only a Handle URL. 1,564 carry a lexicon phrase in title or abstract. |
| `registry.csv` | 387 query rows with route, endpoint, run directory, `n_announced`, `n_harvested`, `n_delivered` |
| `excluded.csv` | 9,914 `duplicate_in_lane`; 2 `no_dedup_key` (see below) |
| `manifest.json` | `coverage: incomplete`, eleven incomplete units, nine `needs_human` items |
| `sentinels.csv` | the class-b sentinel table above |

Identifiers were completed without inventing any:

- 7 DOIs were read from a record's URL (`info:doi/...`).
- The CLACSO rerun with the `dc.date` fallback gives a year to 85 CLACSO
  records that had neither year nor DOI in the lane's run
  (`t1653-latam/` vs `t1653-latam-dspace-b/`). These records carry no
  `lane_note` of their own: their year is the source's `dc.date`.
- 102 GARUDA years come from each record's detail page ("Publish Date"),
  archived with the run in `t1653-asia/garuda/year_enrichment.csv` and cited
  in each record's `lane_note`.

No year was taken from a title.

**Keys.** 30 UWI DSpace items hold no publication year: their metadata has
only deposit dates, and `dc.identifier.other` values such as 1953 look like
CERIS record numbers, not years. Their Handle URL (`hdl.handle.net/2139/…`)
is their key, as the contract allows.

Two CEEW pages have neither a date nor a persistent URL. They are listed in
`excluded.csv` as `no_dedup_key`, with their URL. The pool merge takes them
in as title-only works.

A source DOI carried by records whose titles name different works is not
used as a key. It is blanked in `doi` and kept in `lane_note`. This affects
41 records under 9 DOIs:

- Redalyc issue-level DOIs, one of them on 17 unrelated articles;
- GARUDA template DOIs ending in `p%p`, or truncated ones such as `10.21082/bul`;
- one Spanish/English pair, whose titles are translations.

The lane deduplicates by record id only. The same article under two GARUDA
ids, or on two platforms, is left to the pool's DOI and title joins.

## Ticket 1790: browser attempts, aggregators, second delivery

The author decided on 2026-09-30 that no human will chase closed archives:
each blocked source was tried once in an automated browser (Playwright,
headless Chromium), and what still failed is declared dead in
`config/rel_sud_sources_status.yaml` (`status: dead`, `tried_1790`).
Limits kept: robots.txt re-read for every path on 2026-09-30, sources whose
robots.txt or terms forbid robots (eLIBRARY, CNKI, Shodhganga, the USP OAI
and search paths) not attempted, no CAPTCHA solved, no account created, the
lane's User-Agent (`ClimateFinancePipeline/1.0`) on every request, crawl
delay respected and 8 s between AJOL requests. Long runs ran detached on
doudou, with logs and launch scripts in their run directories.

Code: the runner takes `--browser` (adapters with a `GET` fetch through
`rel_sud_sources/_browser.py`, which runs an AWS WAF JavaScript challenge in
the page and retries once) and `--set KEY=VALUE` (AJOL `deadline`, SciELO
`scielo_collections`). CEEW reads failed pages a second time and reads the
display year after the page heading: the first 1790 rerun showed that the
year was read after the `<head>` title, in the menu, and fell back to the
upload timestamp. 7 of the 52 CEEW years delivered by 1653 differ from the
reread, which gives the page's display date on the three checked ("Harnessing
the Power Shift": 2010, delivered as 2021). The 1790 delivery carries the corrected CEEW records;
the 7 old ones will not join them by title and year.

Aggregators (scope added by the MOE with the author's approval,
2026-09-30), for the dead sources:

- **BASE**: dead. The API answers "Access denied for IP address" (access by
  IP registration through a form), and robots.txt closes the web search.
- **CORE** API v3 (registered key): `search/works` refuses a provider filter,
  `search/outputs?q=repositories.id:<provider>` accepts one; phrase search
  is loose, so each provider is read whole and the lexicon is matched
  locally, as for a harvest.
- **OpenAlex**, restricted to the source standing for a dead platform: 32
  lexicon queries (4 targets x 2 languages x 4 themes), the 1530 year
  window. Spend at most 0.032 USD of the shared daily dollar (budget headers
  0.4639 then 0.4318 USD remaining, 20:47-21:03 UTC; another user of the key
  may account for part of it). No source stands for CNKI or Wanfang, and
  works cannot be filtered by the country of their source.

### Query register (ticket 1790)

Dates 2026-09-30 UTC (AJOL until 2026-10-01 01:13, CEEW until 01:22).
n_expected: harvested or listed (harvest, listing) or announced (search);
n_received: matches (harvest, listing) or hits (search); delivered: unique
records in `records.csv`. Pool columns from `make rel-pool` on 2026-10-01
(works in the catalogue / in another lane only / new to the pool).

| Source | Route | Query | Queries (complete) | n_expected | n_received | delivered | Pool | Run directory |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AJOL | oai-pmh, Chromium | `ListRecords oai_dc` per journal of five categories, lexicon en/fr/pt/ar | 232 (232) | 36,207 | 66 | 66 | 14 / 10 / 42 | `t1790-ajol/run/` |
| SciELO Argentina | oai-pmh | `ListRecords oai_dc set=<ISSN>`, social-science journals, lexicon es/pt/en | 47 (41) | 13,473 | 3 | 3 | 0 / 2 / 1 | `t1790-scielo/run/` |
| CEEW | listing | sitemap publication pages, lexicon en/hi | 1 (0: 13 stale pages) | 706 listed, 693 read | 53 | 51 + 2 `no_dedup_key` | 0 / 43 / 10 | `t1790-ceew/run-b/` |
| USP repository via CORE | listing | `repositories.id:373`, lexicon en/fr | 1 (1) | 9,889 | 32 | 32 | 4 / 11 / 17 | `t1790-aggregators/core/` |
| CyberLeninka via CORE | listing | `repositories.id:1252`, lexicon ru/en | 1 (1) | 400 | 0 | 0 | 0 / 0 / 0 | `t1790-aggregators/core/` |
| Shodhganga via CORE | listing | `repositories.id:8818` | 1 (1) | 0 | 0 | 0 | | `t1790-aggregators/core/` |
| Shodhganga via OpenAlex | api | `locations.source.id:S4377209701`, en/hi | 8 (8) | 8 | 8 | 8 | 6 / 0 / 2 | `t1790-aggregators/openalex/` |
| CyberLeninka via OpenAlex | api | `locations.source.id:S4306401404`, ru/en | 8 (8) | 29 | 29 | 26 | 2 / 16 / 8 | `t1790-aggregators/openalex/` |
| USP repository via OpenAlex | api | `locations.source.id:S4306402186`, en/fr | 8 (8) | 5 | 5 | 5 | 0 / 5 / 0 | `t1790-aggregators/openalex/` |
| USP via OpenAlex institution | api | `authorships.institutions.id:I44666525`, en/fr | 8 (8) | 35 | 35 | 28 | 11 / 17 / 0 | `t1790-aggregators/openalex/` |

Run directories are under `~/data/projets/climate-finance-het/rel_sud/2026-09-30/`
on doudou, each fingerprinted by its `MANIFEST.sha256`; the probes (robots.txt
readings, Chromium attempts, the CyberLeninka captcha page, the Wanfang
screenshot, the BASE refusal) are in `t1790-probes/` and
`t1790-cyberleninka/`.

### Delivery

`data/rel_intake/t1790-sud-playwright/2026-09-30/`, a lane directory of its
own so the t1653 pointer the pool merge reads is untouched; written by
`scripts/catalog_rel_1653_delivery.py export --lane t1790-sud-playwright
--ticket 1790` (invocation in `producer.runs`), DVC-tracked and pushed to
padme; `qa_rel_intake.py`: `OK`, exit 0. `records.csv` holds 219 records (AJOL 66, OpenAlex 67,
CEEW 51, CORE 32, SciELO 3); 10 `duplicate_in_lane` and 2 `no_dedup_key`
in `excluded.csv` (the two undated CEEW pages of 1653: CEEW's 53
matches are 51 rows of `records.csv` plus these 2 rows of `excluded.csv`).
Two source DOIs shared by
differently titled records are kept in `lane_note` only (an AJOL issue DOI;
one article under two titles in CORE and OpenAlex). In the pool (merge
report, by delivery): the 219 records plus the 2 title-only rows of `excluded.csv` fall in 209 works,
since several routes found the same work: 34 in the catalogue, 95 in another
lane only, 80 new. The per-route pool columns above count a work once per
route that found it (and the CEEW row includes its 2 title-only pages), so
they sum to more (37 / 104 / 80). No class-b sentinel
found.

