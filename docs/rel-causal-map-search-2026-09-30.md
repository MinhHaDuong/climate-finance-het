# REL causal-map lane: OpenAlex and EconLit searches, 2026-09-30

Ticket 1652, child of 0700. Protocol rows "Carte causale" and "OpenAlex et
EconLit" of `conception/rel-audit-finalisation-corpus.md`, outside the Sud
stratum (1530, 1653). Harvest before filtering: this lane delivers candidates
with provenance; it does not decide ICF inclusion (1655 screens the whole pool
once). Every count below is read from the archived outputs of the final pass
(review round 2 of PR #1609); derived quantities are labelled as such.

Archive (outside the repo): `~/data/projets/climate-finance-het/rel_causal/2026-09-30/`
on padme, copied to doudou at the same path. `MANIFEST.sha256` covers the raw
runs, judge labels, hand validation, configs and logs (the manifest file itself
hashes to `58f60b02631d4771d8c4c937a7a30aeee529ddac43b7d14136e594f60e68b511`);
`MANIFEST_analysis.sha256` covers yields, sentinel recall and the delivery.
Both manifests verify on doudou after the copy.

## Families of the causal map

`config/rel_causal_families.yaml` groups the 126 arcs of Annex A of
`conception/carte-causale-icf-co2.md` into 22 mechanism families, each arc in
exactly one family (`tests/test_rel_causal_families.py` parses Annex A and fails
on an unassigned, duplicated or unknown arc). The expectation of each family was
recorded before any search.

| Group | Families (arcs) |
|---|---|
| 1: routing to grid, cost of capital, private investment, capacity; debt and spending substitution | grid (2), cost_of_capital (5), private_mobilisation (5), implementation_capacity (9), debt (4), fiscal_substitution (4) |
| 2: emissions outside electricity; induced land effects | construction_emissions (3), end_use_efficiency (4), land_spillovers (7) |
| 3: comparators and leakage | fossil_finance (4), carbon_credits (4), forest_leakage (3) |
| Not priority, empirical | allocation (10), measurement (7), donor_additionality (4), growth_scale (7), policy_channel (3), renewable_deployment (4), redd_results_payments (8) |
| Not priority, theoretical a priori | confounding (9), physical_identities (17), deforestation_drivers (3) |

Map-free themes, searched so that the map does not hide what it does not draw:
total effect (a path, not an arc), transport and other sectors, adaptation,
forest beyond the drawn paths, loss and damage, justice, critical approaches,
accounting categories and governance, private finance, international carbon
markets.

## Query matrix

`config/rel_causal_search.yaml`, fixed before the run; the exact strings of every
row are in the archive (`runs/*/registry.csv`, `runs/openalex_20260930/matrix.csv`)
and in the delivery registry.

- Priority families: intervention + mediator (IM), intervention + outcome (IO),
  synonyms (SY) and country/sector (CS) in English; IM and IO in French and
  Spanish; sentinel identifiers (SI) as a citation search on the family's tuning
  sentinels (OpenAlex `cites:`). Other families: one English IO string (SI when a
  tuning sentinel exists). Themes: one English string each; the Sud lane already
  ran French, Spanish and other-language theme strings.
- 132 OpenAlex rows (12 families x 8 strings, 10 other families, 10 themes, 16
  citation searches); every row has an EconLit twin, plus 22 JEL rows and 12
  working-paper rows written for EconLit only (166 EconLit strings).
- Sentinels: `config/rel_causal_sentinels.csv`, 49 works fixed before the run,
  17 tuning, 31 hold-out, 1 without DOI. Hold-outs never enter a query (a test
  enforces it). Seeds: works named in the causal map (Kretschmer et al. 2013,
  Kim 2018, Roopsind et al. 2019, Kling et al. 2018, Toetzke et al. 2022,
  Zoungrana et al. 2024, West et al. 2023, Stadelmann et al. 2011, the aid-growth
  papers), others from knowledge and a pre-run OpenAlex title probe, and six Sud
  sentinels for the themes. Every DOI resolved to its title in OpenAlex before the
  run; two DOIs recalled from memory were wrong and corrected (Steffen and
  Schmidt 2018 ends in `-3`; Pfeiffer and Mulder 2013 is `eneco.2013.07.005`).
  No sentinel was found for grid, fiscal substitution or construction emissions.

## Runs

| Run | Rows | Received | Complete as the run recorded it | Stopped |
|---|---|---|---|---|
| OpenAlex a, full matrix, cap 800 records | 132 | 34,183 | 100 | 26 record cap, 6 HTTP 500 |
| OpenAlex b, the 6 HTTP 500 rows, cap 800 | 6 | 4,222 | 2 | 4 record cap |
| OpenAlex c, 12 capped priority rows, uncapped | 12 | 11,484 | 10 | 2 HTTP 500 |
| OpenAlex d, the 3 truncated construction_emissions rows, uncapped (round 2) | 3 | 3,841 | 3 | none |
| bibCNRS EDS, EconLit strings on RePEc and ECONIS, cap 500 | 308 | 11,352 | 304 | 4 record cap |

A row searched in several runs keeps the **union** of its retrievals (one record
per raw platform id). Counts are distinct platform ids, not rows: OpenAlex
repeats some works across cursor pages. A row is complete when its runs
together received every announced id, or when some run reached the end of the
cursor with every announced id. A cursor that ended after serving the announced
number of rows, but fewer distinct ids, is **cursor exhausted**: the search
cannot return more, so the row counts as complete, and the registry names the
state (`cursor_state`, `cursor_note`). One row is in that state:
construction_emissions-SY (run d: 1,946 rows, 1,940 distinct ids of 1,944
announced; 1,941 with run a). A cursor that ended with fewer rows than
announced is a **short cursor**, and the row stays incomplete. The first version of the
fetcher recorded a short cursor as complete (run c:
construction_emissions-SY, 193 of 1,944; run a: fiscal_substitution-IO, 658 of
659); run d finished the first, and the merged registry marks the second
incomplete.

In the delivered registry, **20 of the 132 OpenAlex rows are incomplete**: 19
stopped by the 800-record cap (broad synonym, country/sector, IM, IO and theme
strings whose announced counts run to thousands: two IM strings,
carbon_credits-IM and implementation_capacity-IM; carbon_credits-SY announced
66,426) and 1 short cursor (fiscal_substitution-IO, 658 of 659). The rows that
hit HTTP 500 in run a were rerun in run b, up to the cap; of the two that hit
it in run c, construction_emissions-IM was finished by run d, but
implementation_capacity-IM (run c stopped at 400 of 2,631) was not rerun and
keeps the 800 records of run a. The cap is a budget choice, not saturation. 4 of the 308 EDS rows are capped at 500
(allocation-IO and private_finance-TH, on both providers).

**OpenAlex spend** (sum of `x-ratelimit-cost-usd`, measured): pre-run budget and
sentinel probes 0.054 USD, run a 0.224, b 0.022, c 0.062, d 0.021: **0.383 USD**,
under the lane cap of 0.40. The shared daily remaining never fell below 0.60 USD,
so the 0.30 floor was not reached. A search page costs 0.001 USD, a `cites:`
page 0.0001.

## Yield

Works are joined by DOI, then OpenAlex id, then normalised title and year. EDS
returns DOIs cut short (for 528 of the 552 title-and-year twins of an OpenAlex
work, the EDS DOI is a strict prefix of the OpenAlex one), so an EDS DOI joins
only when another record carries the same DOI; otherwise it is kept as a hint
(`doi_eds_hint` and `lane_note`). The title-and-year join never fuses two
records whose DOIs disagree, an EDS DOI agreeing with a DOI only when equal or
a strict prefix: 92 EDS records whose DOI disagrees with a same-title,
same-year record (a working paper and its article, two IMF country reports)
are works of their own, and carry that DOI in `doi`. The first delivery fused
them (ticket 1755). The yield tables below are those of the first delivery; the
corrected keys move the lane totals by under 1% (OpenAlex 30,157 unique works,
21,629 absent from all three; EDS 7,690 and 6,210), archived in
`analysis_1755/`. "Absent" is tested against the refined corpus
(`refined_works.csv`), the raw merged pool (`unified_works.csv`) and the Sud
search results (runs f and g of 1530). The conservation check of the yield
script confirms that all 38,567 distinct raw ids retrieved reach the delivery.

| Lane | Raw hits | Unique works | Absent from all three | Not found by the other lane | Judge-relevant | of which absent from all three |
|---|---|---|---|---|---|---|
| OpenAlex | 42,090 | 30,145 | 21,620 | 27,112 | 8,009 | 3,754 |
| bibCNRS EDS | 11,352 | 7,629 | 6,157 | 4,596 | 1,801 | 1,024 |

By formulation (OpenAlex; "only" = works no other formulation of the lane
retrieved):

| Formulation | Unique works | Absent from all three | Only this formulation | Judge-relevant | Relevant, only this formulation |
|---|---|---|---|---|---|
| IM en | 7,773 | 5,916 | 5,005 | 2,210 | 1,083 |
| IO en | 8,571 | 4,538 | 4,860 | 2,955 | 1,428 |
| SY en | 6,392 | 5,659 | 5,481 | 977 | 577 |
| CS en | 3,911 | 2,851 | 2,916 | 866 | 495 |
| SI (citations) | 2,431 | 1,903 | 1,967 | 563 | 293 |
| TH en | 6,501 | 2,640 | 3,947 | 2,772 | 1,419 |
| IM fr / IO fr | 97 / 35 | 79 / 15 | 89 / 30 | 27 / 23 | 23 / 20 |
| IM es / IO es | 765 / 110 | 708 / 58 | 740 / 84 | 52 / 36 | 47 / 30 |

Every formulation adds works no other formulation found, including the French
and Spanish strings (138 judge-relevant works between them, 120 found by no
other formulation) and the citation searches (293). EDS JEL rows returned
nothing: RePEc and ECONIS records in EDS carry no `CC` field. Per-family and
per-search yields: `analysis/yield_by_question.csv`, `analysis/yield_by_search.csv`.

### The family-relevance judge

"Relevant" = the record addresses the mechanism of the family whose search
retrieved it, with international climate, energy or forest finance or aid as the
treatment. This is a family-relevance judgment for lane yield, **not** the ICF
inclusion screen. Model: Claude Haiku 4.5 (the first 575 pairs through
OpenRouter, then `claude-haiku-4-5` through the Anthropic API after OpenRouter
refused with HTTP 402); prompt `config/rel_causal_judge.yaml` (SHA-256 in
`judge/judge_runs.jsonl`). The final pass has **46,121 (work, family) pairs, all
labelled: 11,920 relevant, 25,350 not, 8,851 unsure**. `judge/labels.jsonl` holds
50,895 labels because the pair id carries the work key, and the join fixes of
round 2 changed some keys; labels of superseded keys stay in the file unused.
Tokens through the Anthropic API: 6.50 M in, 0.49 M out, about 9 USD at list
prices (derived, not a billed amount).

**Validation.** A blind stratified sample of 60 pairs (25 judged relevant, 25
not, 10 unsure; seed 1652; drawn from the first labelling) was read by hand, by
the executing agent (Claude Opus), not by the author: `hand_validation/`.
Agreement 37 of 60. The judge's "not" is reliable: 24 of 25 confirmed, none of
them relevant by hand. Its "relevant" is generous: 12 of 25 confirmed, 5 unsure
by hand, 8 not (typically a REDD+ or climate-finance paper that does not address
the family's mechanism). Its "unsure" is mostly "not" (8 of 10). **Read every
judge-relevant count in this report as an upper bound; the sample suggests about
half are relevant to the mechanism** (derived from 25 records, wide interval).
The outcomes below rest on reading, not on these counts.

## Sentinel recall

| Set | Sentinels | Found by any search | Found by own family | OpenAlex | EDS | In refined corpus |
|---|---|---|---|---|---|---|
| Tuning | 17 | 17 | 17 | 14 | 13 | 10 |
| Hold-out | 31 | 28 | 21 | 28 | 11 | 16 |
| Other source (no DOI) | 1 | 0 | 0 | 0 | 0 | 0 |

Missed hold-outs: C09 (debt-for-climate swaps for small islands: the debt strings
pair climate finance with debt terms, the paper says neither "climate finance"
nor "cost of debt"), C13 (hydropower dams and deforestation in Brazil: no
international-finance term), C15 (Banking on coal: "Chinese overseas
investments" is not in the fossil-finance block). They are reported, not used to
change a query. Seven hold-outs were found only under another family's strings.
Tuning sentinels are found by the text strings, not by their own citation
search.

## Outcomes per family

The corpus keyword probe redoes the protocol's indicative co-occurrence count
per family: a short climate-finance term set AND the family's mediator phrases,
English, on titles and abstracts of the refined corpus
(`analysis/family_outcome_inputs.csv`). "Recognised" = the share of the
judge-relevant works already in the refined corpus that the probe matches;
"absent" = the share of judge-relevant works not in the refined corpus. Both
rest on judge counts, so they are indicative. The outcome of each family was
decided after reading its most-cited judge-relevant candidates.

Rule for the labels, applied to every empirical family where relevant works were
read: **present, largely recognised** when the probe recognises more than half of
the in-corpus relevant works; **present, not recognised by keywords**
otherwise. In both cases the lane found relevant works the corpus lacks.

| Family | Group | Probe hits (refined) | Judge-relevant | Recognised | Absent | Outcome | Evidence read |
|---|---|---|---|---|---|---|---|
| grid | 1 | 30 | 123 | 30% | 81% | present, not recognised | World Bank/GEF solar home systems (Martinot et al. 2001), World Bank off-grid solar lending, energy aid to SIDS and Pacific; electrification and off-grid only: no study found for the integration arc Reseau -> Prod_zero |
| cost_of_capital | 1 | 83 | 590 | 31% | 74% | present, not recognised | Schmidt 2014, Ameli et al. 2021, Polzin et al. 2019 review; C03 on ICF and cost of capital |
| private_mobilisation | 1 | 103 | 595 | 29% | 70% | present, not recognised | renewable PPP determinants, mobilisation studies; C04, C05 |
| implementation_capacity | 1 | 327 | 789 | 33% | 51% | present, not recognised | Kim 2018, absent from refined and unified; disbursement panels (C07) |
| debt | 1 | 39 | 389 | 30% | 81% | present, not recognised (partly non-ICF) | Kling et al. 2018 and 2021 (vulnerability -> cost of capital, not ICF-treated); debt-for-climate swaps; Chinese finance and debt; no estimate of ICF loans' effect on sovereign debt among the candidates read |
| fiscal_substitution | 1 | 26 | 354 | 28% | 88% | present, not recognised (general aid only) | aid fungibility literature (Pack and Pack 1990, 1993; Feyzioglu et al. 1998; Remmer 2004), absent from refined; no climate-finance-specific fungibility study found |
| construction_emissions | 2 | 94 | 272 | 59% (of 51) | 81% | no ICF study found after complete searches; adjacent non-ICF evidence | all IM, IO, SY, CS strings now run to the end (run d). Read: materials embodied in 540 Belt and Road projects (Environ. Sci. Technol. 2024, doi 10.1021/acs.est.4c04142: construction materials of internationally financed projects, not ICF, no emissions estimate); BRI trade-embodied GHG (doi 10.1080/20964129.2020.1761888: trade, not construction); CPEC-driven cement capacity in Pakistan (doi 10.1080/23311916.2020.1810383: economics of cement plants); CDM and large dams in Cambodia (political economy). The recognised share rests on 51 in-corpus works, all general climate-finance papers |
| end_use_efficiency | 2 | 102 | 384 | 36% | 71% | present, not recognised | Kretschmer et al. 2013; energy aid and CO2 intensity (C12, absent); efficiency financing in developing countries |
| land_spillovers | 2 | 209 | 102 | 21% | 86% | present, not recognised (weak) | roads and deforestation (Congo Basin, BR-163), BRI environmental impacts, conservation aid and deforestation in SSA; hold-out C13 missed |
| fossil_finance | 3 | 30 | 165 | 0% | 93% | present, not recognised | Chinese and bilateral overseas coal finance (Steffen and Schmidt 2018, "new coal champion", "carbon lock-in") |
| carbon_credits | 3 | 120 | 1,564 | 1% | 51% | present, not recognised | West et al. 2020 and 2023, Calel et al., Probst et al. 2024; the literature does not say "climate finance", so the probe misses it |
| forest_leakage | 3 | 82 | 788 | 4% | 76% | present, not recognised | Alix-Garcia et al. 2012 (slippage), Atmadja and Verchot 2012, REDD+ leakage reviews |
| allocation | 0 | 463 | 337 | 52% | 48% | present, largely recognised | Betzold and Weiler 2017, Weiler et al. 2018 |
| measurement | 0 | 393 | 291 | 61% | 35% | present, largely recognised | Toetzke et al. 2022, Michaelowa and Michaelowa 2011 |
| donor_additionality | 0 | 174 | 206 | 33% | 39% | present, not recognised | Stadelmann et al. 2011 |
| growth_scale | 0 | 852 | 166 | 67% | 80% | present, largely recognised (general aid only) | aid-growth papers of the map; no ICF-specific growth study among those read |
| policy_channel | 0 | 319 | 241 | 60% | 37% | present, largely recognised | ICF and NDCs (C34) |
| renewable_deployment | 0 | 44 | 88 | 54% | 68% | present, largely recognised | CDM and renewable deployment, Chinese official finance for renewables, Pfeiffer and Mulder 2013 |
| redd_results_payments | 0 | 95 | 575 | 2% | 78% | present, not recognised | Roopsind et al. 2019, absent from refined; Amazon Fund studies |
| confounding | 0 | 672 | 163 | 92% | 53% | theoretical arc, not meant for direct evidence | candidates are allocation-determinant and general climate-finance papers |
| physical_identities | 0 | 4 | 10 | 25% | 20% | theoretical arc, not meant for direct evidence | panels on "load capacity factor", carbon-credit datasets |
| deforestation_drivers | 0 | 8 | 246 | 4% | 79% | theoretical arc, not meant for direct evidence | large drivers literature framed for REDD+ (Hosonuma et al. 2012) without ICF as treatment |

Judge-relevant counts are upper bounds (see the judge validation). The share of
judge-relevant works absent from the refined corpus is above one half for 17 of
the 22 families; the exceptions are allocation, measurement, donor_additionality,
policy_channel and physical_identities. Themes (both lanes): every map-free theme
returned judge-labelled works absent from the refined corpus, for example forest
beyond the map 476 of 621, private finance 148 of 227, loss and damage 126 of
291, adaptation 219 of 400 but only 28 absent from all three reference sets,
since the Sud lane already harvested adaptation.

## EconLit

**Access.** Automated Janus login to bib.cnrs.fr works without MFA (domains
INSHS and INEE) and the bibCNRS article-search API runs end to end, with RIS
export available. EconLit is **not licensed** for these profiles: database codes
`ecn`/`eoh` return 0 hits where HAL returns 4,209 on the same restriction, the
EconLit content-provider filter is rejected ("Invalid Content Provider"; HAL,
ECONIS and RePEc accepted), EconLit is absent from the profile's 232 providers and
from the 152 bibCNRS databases, the EBSCOhost route through the proxy gives
"Authentication Error Code 108", and ProQuest EconLit is not licensed either. Ovid
was not tried. Access through bibCNRS is impossible for this account; the manual
export is ticket 1743.

**Adaptation.** Every OpenAlex row has an EconLit twin in EBSCOhost syntax: each
boolean group searched in `TI`, `AB`, `SU` and `KW`, date limiter `DT
199001-202612`; SI twins search the tuning sentinels' titles (EconLit has no
citation index); 22 JEL rows (`CC` codes with wildcard, for example `CC Q54*`,
AND the family's mediator group) and 12 working-paper rows (`PT "Working
Paper"`). Syntax verified by the probe against the AEA and EBSCO guides; a test
checks every string (balanced parentheses and quotes, allowed field codes).
Export: RIS, one file per search id. The 166 strings are archived in the
registry as "not run: not licensed via bibCNRS (2026-09-30)".

**Substitute run.** The same strings (all but the 12 working-paper rows, which a
RePEc restriction makes redundant) were replayed through bibCNRS EDS against the
RePEc and ECONIS content providers (`scripts/catalog_rel_causal_eds.py`), the
working-paper indexes that profile carries; the date stays in the query text
(`DT 1990-2026`) because the API ignored its limiter parameter. 308 searches (154
per provider), 304 complete, 4 capped; 11,352 records (RePEc 6,120, ECONIS
5,232), 7,629 works, of which 4,596 were not retrieved by the OpenAlex lane and
1,024 judge-relevant works are absent from all three reference sets. The live
parser accepted every twin; the 44 JEL searches return 0 there (no `CC` field in
these records), which is a property of RePEc and ECONIS in EDS, not a test of
EconLit. EDS list records rarely carry an abstract, so their judge labels lean
to "unsure".

## Delivery to the pool (1655)

**Replacement delivery (ticket 1755):**
`data/rel_intake/t1652-causal-econlit/2026-09-30b/`, whose manifest supersedes
`2026-09-30`. It is regenerated from the same archived runs and judge labels,
with no new retrieval: **34,842 records**, 18,584 `duplicate_in_lane`, 16
`not_retrievable` (still 53,442 retrievals). The 117 more works come from the
split title groups above; 130 records have a family without relevance label,
because the judge ran on the fused keys (no new judge call was made). Every EDS DOI of every retrieval survives, in
`doi_eds_hint` of the kept record and in the exclusion note of each duplicate;
the manifest `notes` say how to read them. `registry.csv` adds `cursor_state`
and `cursor_note`. The pool reads only the replacement. The paragraphs below
describe the first delivery.

In the intake-contract format of `docs/rel-intake-contract.md` (ticket 1730,
PR #1604): `data/rel_intake/t1652-causal-econlit/2026-09-30/` (`records.csv`,
`registry.csv`, `excluded.csv`, `manifest.json`), tracked by DVC
(`data/rel_intake/t1652-causal-econlit.dvc`, pushed to the padme remote from
padme). **34,725 records** (one per work, OpenAlex retrieval preferred), 18,701
further retrievals listed as `duplicate_in_lane`, 16 untitled works as
`not_retrievable`; 34,725 + 18,701 + 16 = 53,442 retrievals, which is every
record of every run after the union of reruns. `scripts/qa_rel_intake.py` from
`main` passes. Extra columns carry families, formulations, every search id and
the family-relevance labels as information, never as a filter; `lane_status`
and `in_*` take any retrieval of the work into account. Coverage is `incomplete`
(20 OpenAlex rows, 4 EDS rows, the 166 unrun EconLit strings); `needs_human`
lists EconLit access. `producer.commit` is the commit that generated the
delivery. The per-retrieval table with archive path and manifest hash is
`analysis/delivery.csv` in the archive.

1,108 title-and-year keys still carry more than one record, all within one
platform and with distinct identifiers (versions, repeated generic titles);
1655 merges them by its own rule (DOI, OpenAlex id, then title and year).

## Limits

- The 800-record cap leaves 19 OpenAlex rows incomplete, and one row ended on a
  short cursor; broad strings (carbon-credit synonyms, themes) were not
  paginated to the end within the 0.40 USD cap.
- The relevance judge over-labels "relevant" (about half confirmed on 25
  records); every judge-relevant count is an upper bound.
- French and Spanish strings were written by the assistant and not read by a
  native speaker; they return few works outside Spanish-language repositories.
- The EDS substitute covers RePEc and ECONIS, not EconLit's journal coverage.
  EDS DOIs are often truncated and are delivered as hints, except the 92 that
  disagree with a same-title, same-year record's DOI.
