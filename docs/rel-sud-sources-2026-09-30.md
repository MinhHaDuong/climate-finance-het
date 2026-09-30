# REL "Sud et langues": southern sources outside OpenAlex

Run date: 2026-09-30 UTC, on doudou. Ticket 1653, child of 0700, sequel to
1530 (the OpenAlex pass of the same stratum). The lexicon is the 1530 one,
`config/rel_sud_search.yaml`: four themes (T1 international climate finance;
T2 instruments, private finance, international carbon; T3 adaptation and
forest; T4 loss and damage, justice, accounting) in ten languages. Every
source reuses it; no source got its own vocabulary.

Code: `scripts/catalog_rel_sud_sources.py` (runner) and the adapters of
`scripts/rel_sud_sources/`. Delivery: `scripts/export_rel_sud_sources_intake.py`.
Source status, machine-readable: `config/rel_sud_sources_status.yaml`.
Run directories and raw exports sit on doudou under
`~/data/projets/climate-finance-het/rel_sud/2026-09-30/`, fingerprinted in
`MANIFEST.sha256` there. The delivery to the pool (ticket 1655) is
`data/rel_intake/t1653-sud-hors-openalex/2026-09-30/`, tracked by DVC.

## Harvest and listing routes: the lexicon match is the query

Three kinds of route ran. A **search** route (`api`) sends the lexicon to the
server and delivers every record the server returned, deduplicated in lane by
record id; a full-text hit with no lexicon phrase in its title or abstract is
delivered too (GARUDA: 13,169 unique records of 18,987 rows; Redalyc: all 4,450
unique full-text hits, of which 694 carry a title/abstract match). A
**harvest** route (`oai-pmh`: SciELO, CyberLeninka, AJOL) and a **listing**
route (`listing`: a whole working-paper series or catalogue) have no
server-side search: the adapter reads the set or the listing whole, the raw
harvest is archived in the run's `raw/`, and the local match of the same 1530
lexicon on title and abstract selects the candidates.

Decision of the team lead, 2026-09-30: for these routes the local lexicon
match **is** the query. The delivered registry's `query` names the set or
listing and adds "candidates selected by local 1530 lexicon match on
title+abstract, languages X"; `n_received` is the number of records that
query returned (the matches), `n_expected` the number harvested or listed.
Rejected alternative: delivering the roughly 70,000 unmatched harvested
SciELO, CyberLeninka and listing records to the ICF screen. They were not
retrieved by any query of the protocol, only read in order to run one; the
raw harvest stays archived should the pool want them later.

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
| UWI | api | `uwispace.sta.uwi.edu/server/api/discover/search/objects` | same, en | 4 (4) | 50 | 50 | 16 (+30 without key) | `t1653-latam-dspace-b/` |
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
  `t1653-africa-sasia/ceew/` stays authoritative (54 matches, 13 pages
  failed, full listing not archived), and the partial rerun is kept as an
  archive only (`README-incomplete.txt`).

## Source status

| Source | Stratum | Status | Reason | Human action |
| --- | --- | --- | --- | --- |
| Redalyc | LAC | run | undocumented JSON service of the site's article finder, robots.txt allows; the documented OAI (775,205 records, no subject sets) would take about 5.5 h | |
| CLACSO | LAC | run | DSpace 7 discovery, crawl-delay 10 s; old site HTTP 526 | |
| Ipea | LAC | run | DSpace 7 discovery on the TD collection | |
| UWI | LAC | run | DSpace 7 discovery | |
| SciELO | LAC | partial | search.scielo.org robots Disallow: / and Bunny Shield 403; ArticleMeta has no text search; OAI on social-science journal sets of mex, ven, bol, cri, pry only; Brazil OAI 404/502, Argentina and Colombia time out, Cuba refused, Chile and Peru robots-disallowed | SciELO OAI access or dump for Brazil, Chile, Peru, Argentina, Colombia, Cuba |
| USP repository | Pacific | impossible | robots Disallow /cgi/ (oai2, search, export); Cloudflare 403 on every path; CORE v3 HTTP 500; not in OpenAIRE | allowlist or OAI dump from the USP library |
| GARUDA | SE Asia | run | HTML search, no OAI or JSON API, robots.txt 404 | |
| SINTA | SE Asia | not needed | robots.txt 403; GARUDA covers it | |
| CyberLeninka | Russia | partial (substitute for eLIBRARY) | /search and /api/ robots-disallowed; oai_dc titles only; set repec is not economics (9,830 received, 0 matched); captcha after about 980 pages blocked ListSets | permission, allowlist or dump from skynet@cyberleninka.ru |
| eLIBRARY | Russia | impossible | agreement.asp forbids robots and automated search or download; no OAI; API by contract only | API contract (api@elibrary.ru) or manual export of the 4 ru queries |
| CNKI | China | impossible | cnki.net redirects to oversea.cnki.net, robots Disallow: /; no OAI, no public API | bibCNRS institutional access, manual export of the 4 zh queries |
| Wanfang | China | impossible | undocumented internal JavaScript API (not used); no OAI; open-platform API behind registration | registration or subscription, or manual export |
| AJOL | Africa | impossible at scale | AWS WAF JavaScript challenge after 6-10 requests even at 4 s; site-level OAI empty; search and API robots-disallowed; no record received (logs `t1653-africa-sasia/ajol-*.log`) | allowlist or dump from support@ajol.info |
| Shodhganga | South Asia | impossible | robots Disallow: / (Crawl-delay 600); OAI and REST 404 (DSpace 5.3) | INFLIBNET OAI access or export, or BASE API after IP registration |
| ERSA | Africa | run | WordPress REST listing of 973 working papers; not in RePEc | |
| CPD | South Asia | run | WordPress REST listing of 705 publications; en/bn lexicon | |
| South Centre | Global South | run | REST 401 except /search; category RSS feed, crawl-delay 10 s | |
| ADB EWP | Asia-Pacific | run | adb.org Cloudflare 403 (robots.txt included); RePEc listing and paper pages on IDEAS | |
| CEEW | South Asia | partial | no API or feed; search and paged listings robots-disallowed; sitemap pages at crawl-delay 10 s; 13 of 706 pages failed; full listing not archived (rerun cut short) | |

The human actions are gathered in ticket 1790 (`Label: needs-human`).

## Strata left incomplete

- **Russia**: eLIBRARY impossible, CyberLeninka blocked (0 records).
- **China**: CNKI and Wanfang impossible (0 records).
- **Pacific**: USP repository impossible and no automated Pacific source.
- **Africa**: AJOL blocked; ERSA and South Centre are series, not a journal
  platform.
- **South Asia**: Shodhganga impossible; CPD and CEEW are institute
  catalogues.
- **LAC**: SciELO partial, Brazil, Argentina, Colombia, Cuba, Chile and Peru
  not reached.

The delivery's `manifest.json` declares `coverage: incomplete` and lists each
of these units with its reason.

## Translation status

The zh, ru, hi, bn, id and ar query strings were machine-drafted in 1530 and
no competent reader has reviewed them: status **non résolu** (exit criterion
3). The es, pt, fr and en strings were read by the assistant only, not by a
human reader. Ticket 1790 asks for readers.

## Class-b sentinels

`sentinel_report` of `scripts/catalog_rel_sud_sources.py` over every
delivered record (title fragments or DOI), written to the delivery's
`sentinels.csv`.

| Sentinel | Region, language | Title | Result | Diagnosis |
| --- | --- | --- | --- | --- |
| S08 | Global, en | Seeing Double: Decoding the additionality of climate finance (2023) | missed | CARE Denmark and CARE Climate Justice Center report, published on careclimatechange.org (checked 2026-09-30); a Northern NGO's grey literature, held by no source of this lane |
| S24 | LAC, es | Análisis del financiamiento climático internacional en ALC, desde un enfoque de justicia climática y financiera | missed | not in CLACSO or Redalyc; likely NGO grey literature outside any repository searched |
| S28 | Africa, en | Landscape of Climate Finance in Africa (2022) | missed | Climate Policy Initiative report on climatepolicyinitiative.org; no African source of this lane indexes CPI reports |
| S35 | South Asia, en | Climate Change Finance, Analysis of a Recent OECD Report: Some Credible Facts Needed (2015) | missed | India Ministry of Finance, Department of Economic Affairs discussion paper on dea.gov.in; no government-publication source in scope |
| S36 | South Asia, hi | जलवायु कार्रवाई के लिए निजी वित्त ... (2023) | missed | the Hindi version is on ORF Hindi; CEEW holds only the English original, delivered as "The Myth of Mobilising Private Finance for Climate Action and Pivoting to Scale" (2023) |
| S39 | Bangladesh, en | Operationalizing the Loss and Damage Fund: learning from the intended beneficiaries (2023) | missed | SEI / ICCCAD publication on sei.org; neither is a source of this lane (CEEW's "Operationalising the Loss and Damage Fund to Address Climate Impacts" is a different work) |
| S43 | Indonesia, id | Kerjasama Indonesia-Norwegia dalam konservasi hutan ... REDD+ (2017) | **found** | GARUDA `garuda:689770`, WANUA 3(1) 2017, four queries (id T3 and en T3, title and abstract) |
| S45 | Vietnam, vi | Thúc đẩy tài chính khí hậu tại Việt Nam: thực trạng và khuyến nghị (2023) | missed | thitruongtaichinhtiente.vn; no Vietnamese source and no vi lexicon in scope |
| S58 | Pacific, en | Pacific Climate Change Financing Assessment (framework, Nauru case) (2012-2014) | missed | Pacific Islands Forum Secretariat report (reliefweb, pacificdata, unfccc); no automated Pacific source |
| S59 | Pacific, en | Pacific Regional Climate Finance Access and Mobilisation Strategy 2025-2030 (2026) | missed | forumsec.org; same Pacific gap |

S08's location was checked by the integrator on 2026-09-30; the other
diagnoses are the lanes', and S43 and the CEEW English original of S36 were
verified in the delivered records. One of ten found. The misses are mostly institutional grey literature
(CARE, CPI, DEA, SEI, PIFS) that none of the scholarly or series sources
indexes, plus one language (vi) with no source at all.

## Delivery

`data/rel_intake/t1653-sud-hors-openalex/2026-09-30/`, written by
`scripts/export_rel_sud_sources_intake.py` (the invocation is in the
manifest's `producer.runs`), DVC-tracked and pushed to padme.
`uv run python scripts/qa_rel_intake.py` on it: `OK`, exit 0.

| File | Content |
| --- | --- |
| `records.csv` | 18,238 records: GARUDA 13,169; Redalyc 4,450; CLACSO 410; Ipea 87; CEEW 52; SciELO 26; CPD 18; UWI 16; ADB 5; South Centre 4; ERSA 1. 12,615 carry a DOI, the other 5,623 a year. 1,564 carry a lexicon phrase in title or abstract. |
| `registry.csv` | 387 query rows with route, endpoint, run directory, `n_announced`, `n_harvested`, `n_delivered` |
| `excluded.csv` | 9,914 `duplicate_in_lane`; 32 `not_retrievable` (see below) |
| `manifest.json` | `coverage: incomplete`, eleven incomplete units, nine `needs_human` items |
| `sentinels.csv` | the class-b sentinel table above |

Identifiers were completed without inventing any: 7 DOIs read from a
record's URL (`info:doi/...`), 80 CLACSO years from `dc.date` (rerun), 102
GARUDA years from each record's detail page ("Publish Date",
`t1653-asia/garuda/year_enrichment.csv`). No year was taken from a title.

**Records without any dedup key.** 32 records carry no DOI, OpenAlex id or
publication year anywhere in their source: 30 UWI DSpace items (real items,
the discovery query asks `dsoType=ITEM`, whose metadata holds only deposit
dates; `dc.identifier.other` values such as 1953 look like CERIS record
numbers, not years) and 2 CEEW pages without a date. The checker refuses
such a row in `records.csv`, and the pool merge (1731) aborts on a failing
delivery. They are therefore listed in `excluded.csv` as `not_retrievable`,
with their Handle URL and OAI identifier (UWI) or stable URL (CEEW). This
bends that reason, which the contract defines for items without title-level
metadata: these have titles, archived with the run. The MOE has asked 1655 to
let the contract accept a persistent identifier as dedup key; when it does,
a new delivery moves them back to `records.csv`.
